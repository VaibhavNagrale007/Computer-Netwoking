import asyncio
import asyncudp
import aioconsole
import struct
import os
import sys
import signal
import time

# Define constants for command header fields
CMD_SETUP_CONNECTION = 0
CMD_DATA = 1
CMD_ALIVE = 2
CMD_GOODBYE = 3

delay = 100
active_sessions = {}        # stores tuple (session_id, client_address)
message_tuple = {}          # stores message for given session_id in Queue
sequence_dict = {}

# Check if the received data has the correct header structure
header_size = struct.calcsize("!HBBII")

# Function to handle incoming messages from a client
async def handle_client(session_id, server_socket):
    global timer
    # get active session data
    client_address = active_sessions[session_id]
    expected_sequence_number = 0
    while True:
        # get data from thread
        _, _, command, sequence_number, session_id, message = await message_tuple[session_id].get()

        if sequence_number > expected_sequence_number:
            # while True:
            #     print("===========================1")
            for seq in range(expected_sequence_number, sequence_number-1):
                print(f'0x{session_id:08x} [{seq}] [Lost packet]')
            expected_sequence_number = sequence_number + 1 

        # Check for duplicate packets
        elif sequence_number == expected_sequence_number-1:
            # while True:
            #     print("===========================2")
            print(f'0x{session_id:08x} [Duplicate packet] ')
            continue

        elif sequence_number < expected_sequence_number - 1:
            server_socket.sendto(struct.pack('!HBBII', 0xC461, 1, CMD_GOODBYE, sequence_number, session_id), client_address)
            # while True:
            #     print("===========================3")
            # delete proper data wrt session_id
            del active_sessions[session_id]
            # del last_activity_time[session_id]
            break

        else:
            expected_sequence_number += 1

        # Process the packet based on the command
        if command == CMD_SETUP_CONNECTION: # Reply with 0 for connection setup
            print(f"{hex(session_id)} [{sequence_number}] Session created")
            server_socket.sendto(struct.pack('!HBBII', 0xC461, 1, CMD_SETUP_CONNECTION, sequence_number, session_id), client_address)
            timer = asyncio.create_task(start_timer(server_socket, session_id))

        elif command == CMD_DATA:           # Reply with 2 for Alive
            print(f"{hex(session_id)} [{sequence_number}] {message.decode()}")
            server_socket.sendto(struct.pack('!HBBII', 0xC461, 1, CMD_ALIVE, sequence_number, session_id), client_address)
            if timer:
                timer.cancel()
            timer = asyncio.create_task(start_timer(server_socket, session_id))

        elif command == CMD_GOODBYE:        # Reply with 3 for Goodbye
            # timeout_dict[session_id].cancel()
            
            print(f"{hex(session_id)} [{sequence_number}] GOODBYE from client.")
            server_socket.sendto(struct.pack('!HBBII', 0xC461, 1, CMD_GOODBYE, sequence_number, session_id), client_address)
            
            # delete proper data wrt session_id
            del active_sessions[session_id]

            if timer:
                timer.cancel()
            # del last_activity_time[session_id]
            
            print(f"{hex(session_id)} Session closed")
            break

async def quit_server(server_socket):
    while True:
        user_input = await aioconsole.ainput()
        if user_input == 'q':
            # Send a goodbye message to all connected clients
            for session_id, client_address in active_sessions.items():
                server_socket.sendto(struct.pack('!HBBII', 0xC461, 1, CMD_GOODBYE, 0, session_id), client_address)
            
            # clear dicts
            active_sessions.clear()

            # kill process
            server_socket.close()
            myPid = os.getpid()
            os.kill(myPid, signal.SIGTERM)
            sys.exit()
            break
        time.sleep(1)

async def get_packet(server_socket):
    # global timeout_thread
    while True:
        # Receive data from the client
        data, client_address = await server_socket.recvfrom()

        # Unpack the header fields
        magic, version, command, sequence_number, session_id = struct.unpack('!HBBII', data[:header_size])

        sequence_dict[session_id] = sequence_number
        
        # Check magic and version
        if magic != 0xC461 or version != 1:
            print(f"Received packet with invalid magic or version from {client_address}. Discarding...")
            continue
        
        # Process the packet based on the session ID
        if session_id not in active_sessions:
            # Check for new connection from client
            if command != CMD_SETUP_CONNECTION or sequence_dict[session_id] != 0:
                continue

            active_sessions[session_id] = client_address

            # message_tuple stores messages and session_dict store client addres for each session id
            message_tuple[session_id] = asyncio.Queue()

            asyncio.create_task(handle_client(session_id, server_socket))
        # Inserting message to respective session_id into Queue
        await message_tuple[session_id].put((magic, version, command, sequence_dict[session_id], session_id, data[header_size:]))

async def start_timer(server_socket, session_id):
    await asyncio.sleep(delay)
    if session_id in active_sessions:
        print("Timeout occurred.")
        server_socket.sendto(struct.pack('!HBBII', 0xC461, 1, CMD_GOODBYE, sequence_dict[session_id], session_id) + 'q'.encode(), active_sessions[session_id])
        del active_sessions[session_id]

async def main():
    server_address = ('localhost', int(sys.argv[1]))
    print(f"Waiting on port {server_address[1]}...")
    server_socket = await asyncudp.create_socket(local_addr=server_address)

    quit_task = asyncio.create_task(quit_server(server_socket))
    get_tasks = asyncio.create_task(get_packet(server_socket))

    await asyncio.gather(quit_task, get_tasks)

# asyncio.run(main())
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()