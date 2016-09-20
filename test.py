from client import Client
from server import Server
import threading

if __name__ == '__main__':
    client = Client()
    client.start('127.0.0.1', 8080)
