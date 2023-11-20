import socket
import threading
import sys
import datetime

def handle_client(client_con):
    try:
        # recieve here
        data_recv = client_con.recv(8192)
        # data to bytes for efficient index finding
        data = bytes(data_recv)
        
        # change the header HTTP/1.1 => HTTP/1.0 and keep-alive => close
        updated_header = data.replace(b'HTTP/1.1', b'HTTP/1.0').replace(b'keep-alive', b'close')
        
        # split payload and header
        request, headers = data.split(b'\r\n', 1)
        
        # extract Host: host: port from header
        port = 80
        host = ""
        headers_list = headers.split(b'\r\n')
        for header in headers_list:
            if header.lower().startswith(b'host:'):
                host_port = header.split(b':')
                host = host_port[1].strip()
                if(len(host_port) == 3):
                    port = int(host_port[2])

        # find HTTP method connect, get, post, etc.
        request_type = request.split(b' ')[0]
    except Exception as e:
        return
    
	# If no exception check HTTP method to call proper function
    print(f'{datetime.datetime.now().strftime("%d %b %X")} - >>> {request_type.decode()} {host.decode()} : {port}')
    if request_type == b'CONNECT':
        server_connect(port, host, client_con)
    else:
        server_notconnect(port, host, updated_header, client_con)

def server_connect(port, host, client_con):
    # create new socket for target server
    target_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        # connect to target server and send appropriate message
        target_sock.connect((host, port))
        message = "HTTP/1.0 200 OK\r\n\r\n"
        client_con.send(str.encode(message))
    except Exception as e:
        message = "HTTP/1.0 502 Bad Gateway\r\n\r\n"
        client_con.send(str.encode(message))
        target_sock.close()
        return

    # timer for client and server socket
    client_con.settimeout(0.5)
    target_sock.settimeout(0.5)
    max_bytes = 8192
    client = True

    while True:
        if client:
            try:
                # recieve data from client and send to target server
                client_result = client_con.recv(max_bytes)
                target_sock.send(client_result)
            except socket.timeout:
                # switch on timeout
                client = not client
                continue
            except Exception:
                continue
            # if no data then break
            if len(client_result) == 0:
                client_con.close()
                break
        else:
            try:
                # recieve data from target server and send to client
                server_result = target_sock.recv(max_bytes)
                client_con.send(server_result)
            except socket.timeout:
                # switch on timeout
                client = not client
                continue
            except Exception:
                continue
            # if no data then break
            if len(server_result) == 0:
                target_sock.close()
                break
    target_sock.close()

def server_notconnect(port, host, updated_header, client_con):
    # create new socket for target server
    target_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
	# connect to target server and send updated header
    target_sock.connect((host, port))
    target_sock.send(updated_header)

    # get data from target server
    max_bytes = 1024
    data_recv = target_sock.recv(max_bytes)
    data = bytes(data_recv)

    # find content length
    cont_len_index = data.find(b"Content-Length")
    cont_length = 0
    if (cont_len_index != -1):
        cont_len_end_index = data.find(b'\r\n', cont_len_index)
        cont_len_start_index = data.find(b':', cont_len_index)
        cont_length = int(data[cont_len_start_index + 1 : cont_len_end_index])
    
	# send all this content in chunks to client 
    while (cont_length > 0):
        client_con.send(data_recv)
        data_recv = target_sock.recv(max_bytes)
        cont_length -= max_bytes

    # send remaining data to client
    if (not data == None):
        client_con.send(data_recv)

    target_sock.close()

if __name__ == '__main__':
    port_tcp = sys.argv[1]
    server_ip = 'localhost'
    # creating TCP socket for proxy
    proxy_soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_soc.bind((server_ip, int(port_tcp)))
    proxy_soc.listen(200)
    print(f'{datetime.datetime.now().strftime("%d %b %H:%M:%S")} - Proxy listening on {server_ip}:{sys.argv[1]}')
    while True:
        try:
            # accept new connection
            client_con, client_addr = proxy_soc.accept()
            # create thread and start it
            client_handle = threading.Thread(target=handle_client, args=(client_con, ))
            client_handle.daemon = True
            client_handle.start()
        except (KeyboardInterrupt, SystemExit):
            proxy_soc.close()
            sys.exit()
    proxy_soc.close()
