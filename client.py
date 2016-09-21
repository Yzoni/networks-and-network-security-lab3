"""
Lab 3 - Chat Room (Client)
NAME: Yorick de Boer
STUDENT ID: 10786015
DESCRIPTION:
"""
import argparse
import select
import socket
import sys
try:
    # for Python2
    from Queue import Queue
except ImportError:
    # for Python3
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
        s.connect((host, port))
        while True:
            readable_sockets, writable_sockets, exception_sockets = select.select([s], [], [], 1)
            print('looping')
            for r in readable_sockets:
                data = r.recv(1024)
                message = data.decode()
                print('Worker received: ' + message)
                receive_queue.put(message)
            if not send_queue.empty():
                message = send_queue.get().encode()
                print('Worker sending: ' + message.decode())
                s.send(message)

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

    stop_thread = False
    ui_thread = Thread(target=ui, args=(receive_q, send_q))
    work_thread = Thread(target=work, args=(receive_q, send_q, args.host, args.port))

    ui_thread.start()
    work_thread.start()
