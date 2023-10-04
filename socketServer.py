import socket, threading
from typing import Union, Literal
import json

class Server:
    def __init__(
            self, 
            host: Union[str, Literal['localhost', '127.0.0.1']], 
            port: int
        ):
        self.host = host
        self.port = port
        self.connections = {}
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        print(f"Server listening on {self.host}:{self.port}")

        self.clients: list[socket.socket] = []
        self.nicknames = []

        self._connection_exceptions = (
            socket.error, 
            socket.timeout,
            ConnectionResetError,
            ConnectionAbortedError,
            OSError,
            KeyboardInterrupt)
        
        self._server_is_alive = True
        self._server_data = {
            'seed': '',
            'player_turn': '',
            'nickname': ''
        }

        threading.Thread(target=self.receive_client).start()
        # self.receive_client()

    def store_data(self, data: bytes):        
        if data.startswith(b'{INIT_DATA}'):
            data = data[len(b'{INIT_DATA}'):].decode('ascii')
            self._server_data = json.loads(data)
        
    def broadcast(self, message: bytes, sender: socket.socket, exclude_sender=True):
        if exclude_sender:
            for client in self.clients:
                if client != sender:
                    client.send(message)
        else:
            for client in self.clients:
                client.send(message)
    
    def handle_client(self, conn: socket.socket):
        while self._server_is_alive:
            try:
                message = conn.recv(1024)
                self.store_data(message)
                self.broadcast(message, conn)
            except self._connection_exceptions as e:
                print(f"An error occured! {e}")
                index = self.clients.index(conn)
                self.clients.remove(conn)
                conn.close()
                nickname = self.nicknames[index]
                self.broadcast(f'{nickname} has left the chat!'.encode('ascii'), conn)
                self.nicknames.remove(nickname)
                self._server_is_alive = False
                break
            # return

    def receive_client(self):
        while self._server_is_alive:
            client, address = self.server_socket.accept()

            client.send('NICK'.encode('ascii'))
            nickname = client.recv(1024).decode('ascii')
            self.nicknames.append(nickname)
            self.clients.append(client)

            print(f'{nickname} Connected with {address}')

            self.broadcast(f"{nickname} joined!".encode('ascii'), client)
            
            init_data = "{INIT_DATA}" + json.dumps(self._server_data)
            client.send(init_data.encode('ascii'))

            thread = threading.Thread(target=self.handle_client, args=(client,))
            thread.start()
        
    def shutdown(self):
        self._server_is_alive = False
        self.server_socket.close()
    

if __name__ == '__main__':
    server = Server('127.0.0.1', 55555)