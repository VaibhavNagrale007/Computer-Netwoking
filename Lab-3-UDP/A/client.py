import socket
import struct
import random
import threading
import sys
import os
import signal

# Define constants for command header fields
CMD_SETUP_CONNECTION = 0
CMD_DATA = 1
CMD_ALIVE = 2
CMD_GOODBYE = 3

# Initialize the sequence number and session_id
delay = 2
sequence_number = 0
session_id = random.randint(0, 0xFFFFFFFF)

# Check if the received data has the correct header structure
header_size = struct.calcsize("!HBBII")

# Create a UDP socket
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Define the server address and port
server_address = (str(sys.argv[1]), int(sys.argv[2]))

# Function to handle sending messages to the server
def send_messages():
    global timeout_alive_thread, sequence_number,session_id
    while True:
        sequence_number += 1
        try:
            user_input = input()
        except EOFError:
            user_input = 'eof'
        # user_input = sys.stdin.readline().rstrip()
        if timeout_alive_thread.is_alive():
            timeout_alive_thread.cancel()
        timeout_alive_thread = threading.Timer(delay, handle_timeout)
        timeout_alive_thread.start()
        if user_input == 'q' or user_input == 'eof':
            # Send a goodbye message (4) to the server and exit
            client_socket.sendto(struct.pack('!HBBII', 0xC461, 1, CMD_GOODBYE, sequence_number, session_id) + user_input.encode(), server_address)
            break
        else:
            # Send a data message (2) to the server with the current sequence number
            client_socket.sendto(struct.pack('!HBBII', 0xC461, 1, CMD_DATA, sequence_number, session_id) + user_input.encode(), server_address)
        

# Function to handle receiving messages from the server
def receive_messages():
    global timeout_hello_thread, timeout_alive_thread
    while True:
        data, _ = client_socket.recvfrom(1024)
        _, _, command, _, _ = struct.unpack('!HBBII', data[:header_size])
        

        if command == CMD_SETUP_CONNECTION:
            print("HELLO from Server")
            timeout_hello_thread.cancel()
        elif command == CMD_ALIVE:
            print("ALIVE from Server")
            timeout_alive_thread.cancel()
        elif command == CMD_GOODBYE:
            print("GOODBYE from Server")
            timeout_alive_thread.cancel()
            break
        else:
            print("Unexpected response from server.")
            timeout_alive_thread.cancel()

# Send a connection setup message (0) to the server
def connect_server():
    global timeout_hello_thread, sequence_number
    timeout_hello_thread.start()
    client_socket.sendto(struct.pack('!HBBII', 0xC461, 1, CMD_SETUP_CONNECTION, sequence_number, session_id), server_address)

def handle_timeout():
    global sequence_number
    client_socket.sendto(struct.pack('!HBBII', 0xC461, 1, CMD_GOODBYE, sequence_number, session_id) + 'q'.encode(), server_address)
    client_socket.close()
    myPid = os.getpid()
    os.kill(myPid, signal.SIGTERM)
    sys.exit()

# Start threads
timeout_hello_thread = threading.Timer(delay, handle_timeout)
timeout_alive_thread = threading.Timer(delay, handle_timeout)

connection_thread = threading.Thread(target=connect_server)
connection_thread.start()
connection_thread.join()

send_thread = threading.Thread(target=send_messages, daemon=True)
receive_thread = threading.Thread(target=receive_messages)

send_thread.start()
receive_thread.start()
# timeout_thread.start()

# Wait for the threads to finish
# send_thread.join()
receive_thread.join()
# timeout_thread.join()

# Close the client socket when done
client_socket.close()
