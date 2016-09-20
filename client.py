"""
Lab 3 - Chat Room (Client)
NAME: Yorick de Boer
STUDENT ID: 10786015
DESCRIPTION:
"""
import argparse
import asyncore
import socket
import sys
from queue import Queue
from threading import Thread

from gui import MainWindow


def ui(receive_queue, send_queue):
    """
    GUI loop.
    port: port to connect to.
    cert: public certificate (bonus task)
    """
    # The following code explains how to use the GUI.
    w = MainWindow()
    # update() returns false when the user quits or presses escape.

    while w.update():
        # if the user entered a line getline() returns a string.
        line = w.getline()

        if not receive_queue.empty():
            while not receive_queue.empty():
                w.writeln(receive_queue.get())
        if line:
            w.writeln('You: ' + line)
            send_queue.put(line)


def work(receive_queue, send_queue, host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        print('Connecting with ' + str((host, port)))
        try:
            s.connect(("127.0.0.1", port))
            AsyncClient(host, port, receive_queue, send_queue)
            asyncore.loop(timeout=0.5)
        except socket.error:
            print('Connection refused')


class AsyncClient(asyncore.dispatcher):
    def __init__(self, host, port, receive_queue, send_queue):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((host, port))
        self.receive_queue = receive_queue
        self.send_queue = send_queue

    def handle_connect(self):
        pass

    def handle_close(self):
        self.close()

    def handle_read(self):
        data = self.recv(1024)
        self.receive_queue.put(data.decode())

    def writable(self):
        return not self.send_queue.empty()

    def handle_write(self):
        self.send(self.send_queue.get().encode())


# Command line parser.
if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('host', default='localhost', type=str)
    p.add_argument('--port', help='port to connect to',
                   default=12345, type=int)
    p.add_argument('--cert', help='server public cert', default='')
    args = p.parse_args(sys.argv[1:])

    receive_q = Queue()
    send_q = Queue()
    ui_thread = Thread(target=ui, args=(receive_q, send_q))
    work_thread = Thread(target=work, args=(receive_q, send_q, args.host, args.port))

    try:
        ui_thread.start()
        work_thread.start()
    except:
        ui_thread.join()
        work_thread.join()
