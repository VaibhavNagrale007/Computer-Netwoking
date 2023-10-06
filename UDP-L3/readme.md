# Computer Networking Lab 3

## Overview

This assignment consists of implementing a simple client-server communication system using both multi-threading (Folder A) and asynchronous programming (Folder B). The goal is to demonstrate different approaches to handle concurrent connections and communication between clients and a server.

## Folder Structure

- **Folder A (Threading)**
  - Contains the client and server implementations using multi-threading.
  - To run the client: `./client hostname portnum`
  - To run the server: `./server portnum`

- **Folder B (Asynchronous)**
  - Contains the client and server implementations using asynchronous programming with asyncio.
  - To run the client: `./client hostname portnum`
  - To run the server: `./server portnum`

## Functionality

- **Client**
  - Users can input text messages, and send to server.
  - Also can recieve acks from server.
  - Users can exit by typing 'q' or sending an end-of-file (EOF) signal (Ctrl+D).

- **Server**
  - The server listens for incoming connections on a specified port.
  - It handles multiple client connections concurrently using either multi-threading or asynchronous programming, depending on the folder.
  - The server processes messages from clients and responds accordingly.
  - It maintains session IDs and handles timeouts.
  - Also can exit by typing 'q'.

## Implementation Details

- **Folder A (Threading)**
  - Demonstrates multi-threading to handle multiple client connections.
  - Each client connection is managed in a separate thread.
  - Threads are used to handle incoming and outgoing messages.

- **Folder B (Asynchronous)**
  - Demonstrates asynchronous programming using asyncio.
  - Uses async/await to manage multiple client connections concurrently.
  - Utilizes asyncio tasks to handle sending and receiving messages concurrently.

## Dependencies

- python3
- asyncudp
- aioconsole

## Author

- Vaibhav Nagrale 112001046
- Vinay Ingle 112001050