import asyncio
import asyncudp
import aioconsole
import random
import struct
import os
import sys
import signal

# Define constants for command header fields
CMD_SETUP_CONNECTION = 0
CMD_DATA = 1
CMD_ALIVE = 2
CMD_GOODBYE = 3

# Initialize the sequence number and session_id
delay = 100
sequence_number = 0
session_id = random.randint(0, 0xFFFFFFFF)

# Check if the received data has the correct header structure
header_size = struct.calcsize("!HBBII")
# cmd = await aioconsole.ainput()

async def send_messages(client_socket, server_address):
    global sequence_number,session_id, timer
    while True:
        sequence_number += 1
        # user_input = sys.stdin.readline().rstrip()
        try:
            user_input = await aioconsole.ainput("")
        except EOFError:
            user_input = "eof"
        
        timer = asyncio.create_task(start_timer(client_socket))
        
        if user_input == 'q' or user_input == 'eof':
            # Send a goodbye message (3) to the server and exit
            client_socket.sendto(struct.pack('!HBBII', 0xC461, 1, CMD_GOODBYE, sequence_number, session_id) + user_input.encode(), server_address)
            break
        else:
            # Send a data message (2) to the server with the current sequence number
            client_socket.sendto(struct.pack('!HBBII', 0xC461, 1, CMD_DATA, sequence_number, session_id) + user_input.encode(), server_address)
        

# Function to handle receiving messages from the server
async def receive_messages(client_socket):
    global timer
    while True:
        data, _ = await client_socket.recvfrom()
        _, _, command, _, _ = struct.unpack('!HBBII', data[:header_size])
            
        if timer:
            timer.cancel()
        
        if command == CMD_SETUP_CONNECTION:
            print("HELLO from Server")
        elif command == CMD_ALIVE:
            print("ALIVE from Server")
        elif command == CMD_GOODBYE:
            print("GOODBYE from Server")
            break
        else:
            print("Unexpected response from server.")

# Send a connection setup message (0) to the server
async def connect_server(client_socket, server_address):
    global sequence_number, timer
    timer = asyncio.create_task(start_timer(client_socket))
    client_socket.sendto(struct.pack('!HBBII', 0xC461, 1, CMD_SETUP_CONNECTION, sequence_number, session_id), server_address)

async def start_timer(client_socket):
    await asyncio.sleep(delay)
    print("Timeout occurred.")
    
    client_socket.close()
    myPid = os.getpid()
    os.kill(myPid, signal.SIGTERM)
    sys.exit()

async def main():
    server_address = (str(sys.argv[1]), int(sys.argv[2]))
    client_socket = await asyncudp.create_socket(remote_addr=server_address)
    # await connect_server(client_socket, server_address)

    connect_task = asyncio.create_task(connect_server(client_socket, server_address))

    send_task = asyncio.create_task(send_messages(client_socket, server_address))
    recieve_task = asyncio.create_task(receive_messages(client_socket, ))

    await asyncio.gather(connect_task, recieve_task)
    
    # client_socket.close()

if __name__ == "__main__":
    asyncio.run(main())