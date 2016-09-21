"""
Lab 3 - Chat Room (Server)
NAME: Yorick de Boer
STUDENT ID: 10786015
DESCRIPTION:
"""

import argparse
import select
import socket
import ssl
import sys


class Server:
    def __init__(self, port=8080, cert_file='', key_file=''):
        self.port = port
        self.inputs = {}
        self.outputs = []
        if cert_file and key_file:
            self.ssl = True
            self.cert_file = cert_file
            self.key_file = key_file

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind(('', self.port))
            server_socket.listen(5)
            self.inputs[server_socket] = 'server'
            try:
                print('Started server')
                while True:
                    readable_sockets, writable_sockets, exception_sockets = select.select(self.inputs, self.outputs, [])
                    for r in readable_sockets:
                        if r is server_socket:
                            client_socket, client_address = r.accept()
                            if ssl:
                                client_socket = self.wrap_socket(client_socket)
                            print('New connection from' + str(client_address))
                            self.inputs[client_socket] = 'Unnamed'
                            self.broadcast("Client connected: " + str(client_address), server_socket, client_socket)
                        else:
                            try:
                                data = r.recv(1024).decode()
                                if data:
                                    print('received ' + str(data) + ' from ' + str(r.getpeername()))
                                    self.parse_data(data, server_socket, r)
                                else:
                                    del self.inputs[r]
                                    r.close()
                            except socket.error:
                                del self.inputs[r]
                                continue

            except KeyboardInterrupt:
                print('Stopped server')
                pass

    def parse_data(self, data, server_socket, client_socket):
        print(client_socket)
        if data[0] == '/':
            command = data.split(' ', 1)[0][1:]
            parameters = data.split(' ')[1:]
            if command == 'nick':
                self.inputs[client_socket] = parameters[0]
            elif command == 'say':
                self.broadcast(' '.join(parameters), server_socket, client_socket)
            elif command == 'whisper':
                whisper_client = parameters[0]
                message = ' '.join(parameters[1:])
                found = False
                for s, n in self.inputs.items():
                    if n == whisper_client:
                        self.whisper(message, whisper_client, client_socket)
                        found = True
                if found is False:
                    self.whisper('User does not exist', client_socket, server_socket)
            elif command == 'list':
                self.whisper(self.list_clients(client_socket, server_socket), client_socket, server_socket)
            elif command == 'help' or command == '?':
                self.list_commands(client_socket, server_socket)
            elif command == 'me':
                self.whisper('me goes', server_socket, client_socket)
            elif command == 'whois':
                self.whisper('Name is ' + self.inputs[client_socket] + ', with ip ' + str(client_socket.getpeername()),
                             client_socket,
                             server_socket)
            elif command == 'filter':
                self.whisper('Command not implemented!', client_socket, server_socket)
            else:
                self.whisper('Command unknown!', client_socket, server_socket)
        else:
            self.broadcast(data, server_socket, client_socket)
        return None

    def whisper(self, message, whisper_socket, send_socket):
        whisper_socket.send(('(WHISPERS) ' + self.inputs[send_socket] + ': ' + message).encode())

    def broadcast(self, message, server_socket, client_socket):
        print('Broadcast ' + message)
        for s in self.inputs:
            if s != server_socket and s != client_socket:
                s.send(message.encode())

    def wrap_socket(self, socket):
        return ssl.wrap_socket(socket,
                               server_side=True,
                               certfile=self.cert_file,
                               keyfile=self.key_file,
                               ssl_version=ssl.PROTOCOL_TLSv1)

    def list_commands(self, client_socket, server_socket):
        commands = ['/nick <user>',
                    '/say <text>',
                    'whisper <user> <text>',
                    '/list']
        for c in commands:
            self.whisper(c, client_socket, server_socket)

    def list_clients(self, client_socket, server_socket):
        clients = ''
        for socket in self.inputs:
            if socket != server_socket and socket != client_socket:
                clients += self.inputs[socket] + ', '
        return clients


# Command line parser.
if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--port', help='port to listen on', default=8080, type=int)
    args = p.parse_args(sys.argv[1:])
    server = Server(args.port, cert_file='server.cert', key_file='server.key')
    server.start()
