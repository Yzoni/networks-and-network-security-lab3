"""
Lab 3 - Chat Room (Server)
NAME: Yorick de Boer
STUDENT ID: 10786015
DESCRIPTION:

Everything implemented

Banned client ips go into ban.txt

Admin client ips go into admin.txt

"""

import argparse
import random
import select
import socket
import ssl
import string
import sys
import time
from enum import Enum


class Server:
    BAN_FILE = 'ban.txt'
    ADMIN_FILE = 'admin.txt'

    def __init__(self, port=8080, cert_file='', key_file=''):
        self.port = port
        self.inputs = {}
        self.filtered_words = {}
        self.admin_ip = self.read_file_to_list(self.ADMIN_FILE)
        self.ban_ip = self.read_file_to_list(self.BAN_FILE)
        if cert_file and key_file:
            self.ssl = True
            self.cert_file = cert_file
            self.key_file = key_file

    def start(self):
        """
        Main run function
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
                        if r is server_socket:  # A new client connects
                            self.connect_new_client(server_socket)
                        else:  # A message from a client is received
                            data = r.recv(1024).decode()
                            if data:
                                self.parse_data(data, server_socket, r)
                            else:
                                del self.inputs[r]
                                r.close()

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
            if command == 'nick':
                self.command_nick(client_socket, parameters[0])
            elif command == 'say':
                self.command_say(parameters, server_socket, client_socket)
            elif command == 'whisper':
                self.command_whisper(parameters[0], parameters[1:], server_socket, client_socket)
            elif command == 'list':
                self.command_list(server_socket, client_socket)
            elif command == 'help' or command == '?':
                self.command_help(server_socket, client_socket)
            elif command == 'me':
                self.command_me(server_socket, client_socket)
            elif command == 'whois':
                self.command_whois(parameters[0], server_socket, client_socket)
            elif command == 'filter':
                self.command_filter(parameters[0], server_socket, client_socket)
            elif command == 'kick':
                self.command_kick(parameters[0], server_socket, client_socket)
            elif command == 'ban':
                self.command_ban(parameters[0], server_socket, client_socket)
            else:
                self.whisper('Command unknown!', client_socket, server_socket)
        else:
            self.broadcast(data, server_socket, client_socket)

    def command_nick(self, client_socket, nick):
        self.inputs[client_socket] = nick

    def command_say(self, message, server_socket, client_socket):
        self.broadcast(' '.join(message), server_socket, client_socket)

    def command_whisper(self, whisper_client_nick, message, server_socket, client_socket):
        message = ' '.join(message)
        sock = self.get_socket_by_nick(whisper_client_nick)
        if sock:
            self.whisper(message, whisper_client_nick, client_socket)
        else:
            self.whisper('User does not exist', client_socket, server_socket)

    def command_help(self, server_socket, client_socket):
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
                    '/kick <user>           - Kick user',
                    '/ban <user>            - Ban user'
                    ]
        for c in commands:
            self.whisper(c, client_socket, server_socket)

    def command_list(self, server_socket, client_socket):
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
            self.whisper(', '.join(clients), client_socket, server_socket)
        else:
            self.whisper('Empty', client_socket, server_socket)

    def command_me(self, server_socket, client_socket):
        self.whisper(self.inputs[client_socket] + 'goes to the store.', server_socket, client_socket)

    def command_whois(self, nick, server_socket, client_socket):
        sock = self.get_socket_by_nick(nick)
        if sock:
            self.whisper('Name is ' + self.inputs[sock] + ', with ip ' + str(client_socket.getpeername()),
                         client_socket,
                         server_socket)
        else:
            self.whisper('User does not exist', client_socket, server_socket)

    def command_filter(self, word, server_socket, client_socket):
        self.add_filter_word(word, client_socket)
        self.whisper('Will filter word: "' + word + '"', client_socket, server_socket)

    def command_kick(self, nick, server_socket, client_socket):
        if self.authenticate_client(client_socket) == ClientType.admin:
            sock = self.get_socket_by_nick(nick)
            self.whisper('You have been kicked', sock, server_socket)
            self.kick_client(sock)
        else:
            self.whisper('Not authorized to run this command', client_socket, server_socket)

    def command_ban(self, nick, server_socket, client_socket):
        if self.authenticate_client(client_socket) == ClientType.admin:
            sock = self.get_socket_by_nick(nick)
            self.whisper('You have been banned!', sock, server_socket)
            self.ban_client(sock)
        else:
            self.whisper('Not authorized to run this command', client_socket, server_socket)

    def whisper(self, message, whisper_socket, send_socket):
        """
        Sends a private message to a single client

        :param message: the message to be send
        :param whisper_socket: the receiving client
        :param send_socket: the client who sends the message
        :return: None
        """
        timestamp = time.strftime("%d/%m/%Y %H:%M:%S")
        message = timestamp + ' | ' + '(WHISPERS) ' + self.inputs[send_socket] + ': ' + message
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
        timestamp = time.strftime("%d/%m/%Y %H:%M:%S")
        message = timestamp + ' | ' + str(self.inputs[client_socket]) + ': ' + message
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

    def add_filter_word(self, word, client_socket):
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
            resultwords = [word for word in message.split(' ') if
                           word.lower() not in self.filtered_words[client_socket]]
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

    def authenticate_client(self, client_socket):
        client_ip = client_socket.getpeername()[0]
        if client_ip in self.ban_ip:
            return ClientType.banned
        if client_ip in self.admin_ip:
            return ClientType.admin
        else:
            return ClientType.user

    def connect_new_client(self, server_socket):
        """
        Connects a new client

        :param server_socket: server_socket
        :return:
        """
        client_socket, client_address = server_socket.accept()
        if self.authenticate_client(client_socket) == ClientType.banned:
            client_socket.close()
            return
        if ssl:
            client_socket = self.wrap_socket(client_socket)
        print('New connection from: ' + str(client_address))
        random_name = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(5))
        self.inputs[client_socket] = random_name

        self.broadcast("Client connected: " + str(client_address), server_socket, client_socket)

    def kick_client(self, client_socket):
        del self.inputs[client_socket]
        client_socket.close()

    def ban_client(self, client_socket):
        self.ban_ip.append(client_socket.getpeername()[0])
        self.write_line_to_file(self.BAN_FILE, client_socket.getpeername()[0])
        self.kick_client(client_socket)

    def read_file_to_list(self, file_path):
        try:
            with open(file_path, 'r') as f:
                return f.read().splitlines()
        except FileNotFoundError:
            print('File could not be read, not found')
            return []

    def write_line_to_file(self, file_path, line):
        with open(file_path, 'w') as f:
            f.write(line)


class ClientType(Enum):
    admin = 0
    user = 1
    banned = 2


# Command line parser.
if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--port', help='port to listen on', default=8080, type=int)
    args = p.parse_args(sys.argv[1:])
    server = Server(args.port, cert_file='server.cert', key_file='server.key')
    server.start()
