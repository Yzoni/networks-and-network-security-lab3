"""
Lab 3 - Chat Room (Client)
NAME: Yorick de Boer
STUDENT ID: 10786015
DESCRIPTION:
"""
import argparse
import select
import socket
import ssl
import sys

try:
    # for Python2
    from Queue import Queue
except ImportError:
    # for Python3
    from queue import Queue

from threading import Thread

from gui import MainWindow


class Client:
    def __init__(self, host, port, cert_file=''):
        if cert_file:
            self.ssl = True
            self.cert_file = cert_file
        self.host = host
        self.port = port
        self.receive_queue = Queue()
        self.send_queue = Queue()

    def run(self):
        ui_thread = UI(self.receive_queue, self.send_queue)
        work_thread = Worker(self.receive_queue, self.send_queue, self.host, self.port, self.cert_file)
        ui_thread.start()
        work_thread.start()

        while work_thread.is_alive():
            if not ui_thread.is_alive():
                work_thread.stop()
                break


class UI(Thread):
    def __init__(self, receive_queue, send_queue, cert_file='', group=None, target=None, name=None, args=(),
                 kwargs=None, *, daemon=None):
        if cert_file:
            self.ssl = True
            self.cert_file = cert_file
        self.receive_queue = receive_queue
        self.send_queue = send_queue
        self.go = True
        super().__init__(group, target, name, args, kwargs, daemon=daemon)

    def run(self):
        w = MainWindow()
        # update() returns false when the user quits or presses escape.

        while w.update():
            # if the user entered a line getline() returns a string.
            line = w.getline()

            if not self.receive_queue.empty():
                while not self.receive_queue.empty():
                    w.writeln(self.receive_queue.get())
            if line:
                w.writeln('You: ' + line)
                self.send_queue.put(line)

    def stop(self):
        self.go = False


class Worker(Thread):
    def __init__(self, receive_queue, send_queue, host, port, cert_file='', group=None, target=None, name=None, args=(),
                 kwargs=None, *, daemon=None):
        if cert_file:
            self.ssl = True
            self.cert_file = cert_file
        self.receive_queu = receive_queue
        self.send_queue = send_queue
        self.host = host
        self.port = port
        self.go = True
        super().__init__(group, target, name, args, kwargs, daemon=daemon)

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            print('Connecting with ' + str((self.host, self.port)))
            if ssl:
                s = self.wrap_socket(s)
            s.connect((self.host, self.port))
            while self.go:
                readable_sockets, writable_sockets, exception_sockets = select.select([s], [], [], 1)
                for r in readable_sockets:
                    data = r.recv(1024)
                    if data:
                        message = data.decode()
                    else:
                        # Stop working when server disconnects
                        self.receive_queu.put('Server disconnected')
                        s.close()
                        return
                    print('Worker received: ' + message)
                    self.receive_queu.put(message)
                if not self.send_queue.empty():
                    message = self.send_queue.get().encode()
                    print('Worker sending: ' + message.decode())
                    s.send(message)

    def stop(self):
        self.go = False

    def wrap_socket(self, socket):
        """
        Wrap the socket in a TLS layer
        :param socket: socket
        :return: ssl socket
        """
        return ssl.wrap_socket(socket,
                               ca_certs=self.cert_file,
                               cert_reqs=ssl.CERT_REQUIRED,
                               ssl_version=ssl.PROTOCOL_TLSv1)


# Command line parser.
if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('host', default='localhost', type=str)
    p.add_argument('--port', help='port to connect to',
                   default=12345, type=int)
    p.add_argument('--cert', help='server public cert', default='')
    args = p.parse_args(sys.argv[1:])

    Client(args.host, args.port, args.cert).run()
