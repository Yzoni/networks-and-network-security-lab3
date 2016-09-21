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
        self.filtered_words = {}
        if cert_file and key_file:
            self.ssl = True
            self.cert_file = cert_file
            self.key_file = key_file

    def start(self):
        """

        :return:
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind(('', self.port))
            server_socket.listen(5)
            self.inputs[server_socket] = 'server'
            try:
                print('Started server')
                while True:
                    readable_sockets, writable_sockets, exception_sockets = select.select(self.inputs, [], [])
                    for r in readable_sockets:
                        if r is server_socket:
                            client_socket, client_address = r.accept()
                            if ssl:
                                client_socket = self.wrap_socket(client_socket)
                            print('New connection from' + str(client_address))
                            self.inputs[client_socket] = 'Unnamed'
                            self.broadcast("Client connected: " + str(client_address), server_socket, client_socket)
                        else:
                            # try:
                            data = r.recv(1024).decode()
                            if data:
                                print('received ' + str(data) + ' from ' + str(r.getpeername()))
                                self.parse_data(data, server_socket, r)
                            else:
                                del self.inputs[r]
                                r.close()
                            # except socket.error:
                            #     # Client socket unexpectedly closed
                            #     del self.inputs[r]
                            #     continue

            except KeyboardInterrupt:
                print('Stopped server')
                pass

    def parse_data(self, data, server_socket, client_socket):
        """
        Parse command data when message is prefixed by '/"

        :param data: message data
        :param server_socket: server socket
        :param client_socket: client socket
        :return: None
        """
        if data[0] == '/':
            command = data.split(' ', 1)[0][1:]
            parameters = data.split(' ')[1:]
            print(parameters)
            if command == 'nick':
                self.inputs[client_socket] = parameters[0]
            elif command == 'say':
                self.broadcast(' '.join(parameters), server_socket, client_socket)
            elif command == 'whisper':
                whisper_client = parameters[0]
                message = ' '.join(parameters[1:])
                sock = self.get_socket_by_nick(whisper_client)
                if sock:
                    self.whisper(message, whisper_client, client_socket)
                else:
                    self.whisper('User does not exist', client_socket, server_socket)
            elif command == 'list':
                self.whisper(self.list_clients(client_socket, server_socket), client_socket, server_socket)
            elif command == 'help' or command == '?':
                self.list_commands(client_socket, server_socket)
            elif command == 'me':
                self.whisper('me goes', server_socket, client_socket)
            elif command == 'whois':
                nick = parameters[0]
                sock = self.get_socket_by_nick(nick)
                if sock:
                    self.whisper('Name is ' + self.inputs[client_socket] + ', with ip ' + str(client_socket.getpeername()),
                                 client_socket,
                                 server_socket)
                else:
                    self.whisper('User does not exist', client_socket, server_socket)
            elif command == 'filter':
                filtered_word = parameters[0]
                self.add_filter_words(filtered_word, client_socket)
                self.whisper('Will filter word: "' + filtered_word + '"', client_socket, server_socket)
            else:
                self.whisper('Command unknown!', client_socket, server_socket)
        else:
            self.broadcast(data, server_socket, client_socket)

    def whisper(self, message, whisper_socket, send_socket):
        """
        Sends a private message to a single client

        :param message: the message to be send
        :param whisper_socket: the receiving client
        :param send_socket: the client who sends the message
        :return: None
        """
        message = '(WHISPERS) ' + self.inputs[send_socket] + ': ' + message
        print(message)
        whisper_socket.send(message.encode())

    def broadcast(self, message, server_socket, client_socket):
        """
        Broadcast a message to all clients except the server socket and the client itself

        :param message: the message to be broadcast
        :param server_socket: server socket
        :param client_socket: the sending client socket
        :return: None
        """
        message = str(self.inputs[client_socket]) + ': ' + message
        print(message)
        for s in self.inputs:
            if s != server_socket and s != client_socket:
                filtered_message = self.filter_words(message, s)
                s.send(filtered_message.encode())

    def wrap_socket(self, socket):
        """
        Wrap a socket in a TLS layer

        :param socket: the socket
        :return: ssl socket
        """
        return ssl.wrap_socket(socket,
                               server_side=True,
                               certfile=self.cert_file,
                               keyfile=self.key_file,
                               ssl_version=ssl.PROTOCOL_TLSv1)

    def list_commands(self, client_socket, server_socket):
        """
        whisper a list of commands to a client

        :param client_socket: the client to request the list
        :param server_socket: the server socket
        :return: None
        """
        commands = ['/nick <user>           - Change nickname',
                    '/say <text>            - Say to everyone',
                    '/whisper <user> <text> - Say to specific nick',
                    '/list                  - List all users',
                    '/help or /?            - List commands',
                    '/me                    - Doing something',
                    '/whois <user>          - Info of user',
                    '/filter <word>         - Filter words'
                    ]
        for c in commands:
            self.whisper(c, client_socket, server_socket)

    def list_clients(self, client_socket, server_socket):
        """
        Creates a string currently connected client nicknames

        :param client_socket: client socket
        :param server_socket: server socket
        :return: string of clients seperated by comma
        """
        clients = []
        for socket in self.inputs:
            if socket != server_socket and socket != client_socket:
                clients.append(self.inputs[socket])
        if clients:
            return ', '.join(clients)
        else:
            return 'Empty'

    def add_filter_words(self, word, client_socket):
        """
        Add a word to the filter for a client

        :param word: the new filter word
        :param client_socket: the client socket
        :return:
        """
        if client_socket in self.filtered_words:
            self.filtered_words[client_socket].append(word)
        else:
            self.filtered_words[client_socket] = [word]

    def filter_words(self, message, client_socket):
        """
        Filter a string on words from a list

        :param message: message to be filtered
        :param client_socket: for client
        :return: filtered message
        """
        try:
            resultwords  = [word for word in message.split(' ') if word.lower() not in self.filtered_words[client_socket]]
            return ' '.join(resultwords)
        except:
            return message

    def get_socket_by_nick(self, nick):
        """
        Get the socket by a nick string

        :param nick: nick to be found
        :return: socket
        """
        for s, n in self.inputs.items():
            if n == nick:
                return s
        return None

# Command line parser.
if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--port', help='port to listen on', default=8080, type=int)
    args = p.parse_args(sys.argv[1:])
    server = Server(args.port, cert_file='server.cert', key_file='server.key')
    server.start()
