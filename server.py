import argparse
import select
import socket
import sys


class Server:
    def __init__(self, port=8080):
        self.port = port
        self.inputs = []
        self.outputs = []

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            # server_socket.setblocking(False)
            server_socket.bind(('', self.port))
            server_socket.listen(5)
            self.inputs.append(server_socket)
            try:
                print('Started server')
                while True:
                    readable_sockets, writable_sockets, exception_sockets = select.select(self.inputs, self.outputs, [])
                    for r in readable_sockets:
                        print(readable_sockets)
                        if r is server_socket:
                            client_socket, client_address = r.accept()
                            print('New connection from' + str(client_address))
                            self.inputs.append(client_socket)
                            self.broadcast("Client connected: " + str(client_address), server_socket, client_socket)
                        else:
                            data = r.recv(1024).decode()
                            if data:
                                # A readable client socket has data
                                print('received ' + str(data) + ' from ' + str(r.getpeername()))
                                self.broadcast(data, server_socket, r)
                            else:
                                self.inputs.remove(r)
                                r.close()

            except KeyboardInterrupt:
                print('Stopped server')
                pass

    def broadcast(self, message, server_socket, client_socket):
        print('inputs' + str(self.inputs))
        for socket in self.inputs:
            if socket != server_socket and socket != client_socket:
                socket.send(message.encode())
                print('message sent ' + message)


# Command line parser.
if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--port', help='port to listen on', default=8080, type=int)
    args = p.parse_args(sys.argv[1:])
    server = Server(args.port)
    server.start()
