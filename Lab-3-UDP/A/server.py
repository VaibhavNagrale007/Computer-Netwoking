import socket
import struct
import threading
import sys
import time
from queue import Queue
import os
import signal

# Define constants for command header fields
CMD_SETUP_CONNECTION = 0
CMD_DATA = 1
CMD_ALIVE = 2
CMD_GOODBYE = 3

delay = 10
active_sessions = {}        # stores tuple (session_id, client_address)
message_tuple = {}          # stores message for given session_id in Queue
# last_activity_time = {}     # stores last activity time for session_id
# storing sequence number and time wrt session_id
sequence_dict = {}
timeout_dict = {}

# Check if the received data has the correct header structure
header_size = struct.calcsize("!HBBII")

# Create a UDP socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Define the server address and port
server_address = ('', int(sys.argv[1]))

# Bind the socket to the server address
server_socket.bind(server_address)

print(f"Waiting on port {server_address[1]}...")

# Function to handle incoming messages from a client
def handle_client(session_id):
    global timeout_dict
    # get active session data
    client_address = active_sessions[session_id]
    expected_sequence_number = 0
    while True:
        # get data from thread
        _, _, command, sequence_number, session_id, message = message_tuple[session_id].get()

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
            break

        else:
            expected_sequence_number += 1

        # time.sleep(0.1)

        # Process the packet based on the command
        if command == CMD_SETUP_CONNECTION: # Reply with 0 for connection setup
            timeout_dict[session_id] = threading.Timer(delay, handle_timeout, args=(session_id, ))
            timeout_dict[session_id].start()
            print(f"{hex(session_id)} [{sequence_number}] Session created")
            server_socket.sendto(struct.pack('!HBBII', 0xC461, 1, CMD_SETUP_CONNECTION, sequence_number, session_id), client_address)

        elif command == CMD_DATA:           # Reply with 2 for Alive
            timeout_dict[session_id].cancel()
            timeout_dict[session_id] = threading.Timer(delay, handle_timeout, args=(session_id, ))
            timeout_dict[session_id].start()
            print(f"{hex(session_id)} [{sequence_number}] {message.decode()}")
            server_socket.sendto(struct.pack('!HBBII', 0xC461, 1, CMD_ALIVE, sequence_number, session_id), client_address)
            
        elif command == CMD_GOODBYE:        # Reply with 3 for Goodbye
            timeout_dict[session_id].cancel()
            
            print(f"{hex(session_id)} [{sequence_number}] GOODBYE from client.")
            server_socket.sendto(struct.pack('!HBBII', 0xC461, 1, CMD_GOODBYE, sequence_number, session_id), client_address)
            
            # delete proper data wrt session_id
            del active_sessions[session_id]
            
            print(f"{hex(session_id)} Session closed")
            break

# Function to quit the server
def quit_server():
    while True:
        user_input = sys.stdin.readline().rstrip()
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

def get_packet():
    while True:
        # Receive data from the client
        data, client_address = server_socket.recvfrom(1024) 

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

            # Created new Session and stored in dict of active_sessions
            active_sessions[session_id] = client_address

            # message_tuple stores messages and session_dict store client addres for each session id
            message_tuple[session_id] = Queue()

            # Create a thread for each new session
            session_thread = threading.Thread(target=handle_client, args=(session_id, ))
            session_thread.daemon = True
            session_thread.start()
        # Inserting message to respective session_id into Queue
        message_tuple[session_id].put((magic, version, command, sequence_dict[session_id], session_id, data[header_size:]))

def handle_timeout(session_id):
    if session_id in active_sessions:
        print(f"Timeout for {hex(session_id)}")
        server_socket.sendto(struct.pack('!HBBII', 0xC461, 1, CMD_GOODBYE, sequence_dict[session_id], session_id) + 'q'.encode(), active_sessions[session_id])
    # del active_sessions[session_id]

# Start the thread for closing server
quit_thread = threading.Thread(target=quit_server)
server_thread = threading.Thread(target=get_packet)

quit_thread.start()
server_thread.start()

# quit_thread.join()
server_thread.join()
# Close the server socket when done
server_socket.close()
