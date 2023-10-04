import socket, threading
from typing import Literal, Union
import pickle, json


class Client:
    def __init__(
            self, 
            address: Union[str, Literal['localhost', '127.0.0.1']], 
            port: int, 
            nickname = '',
            using_whot=False
        ):
        
        self.address = address
        self.port = port

        if not nickname:
            nickname = input("Choose your nickname: ")
        self.nickname = nickname

        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((self.address, self.port))

        self._client_is_alive = True

        self.client_data: dict[str, tuple|int|str|bool|list|None] = {
            'card': None, # tuple[str, int] 
            'seed': None, # int
            'player_turn': None,
            'nickname': '',
            'conn_nickname': '',
            'request': '',
            'mart': False
        }

        self.client_init_data = {
            'seed': None,
            'player_turn': '',
            'nickname': ''
        }

        self._connection_exceptions = (
            socket.timeout,
            ConnectionResetError,
            ConnectionAbortedError
        )
        self._input_exceptions = (
            KeyboardInterrupt,
            OSError,
            EOFError
        )

        self.send_nickname()
        threading.Thread(target=self.recieve).start()
        if not using_whot:
            self.write()
        # threading.Thread(target=self.write).start()

    
    def send_nickname(self):
        try:
            message = self.client.recv(1024).decode('ascii')
            if message == 'NICK':
                self.client.send(self.nickname.encode('ascii'))
        except self._connection_exceptions as e:
            print(f"An error occured! {e}")
            self.client.close()
            self._client_is_alive = False

    
    def recieve(self):
        while self._client_is_alive:
            try:
                data = self.client.recv(1024)
                self.process_data(data)

            except self._connection_exceptions as e:
                print(f"An error occured! {e}")
                self.client.close()
                self._client_is_alive = False
                break
    
    def process_data(self, data: bytes):
        if data.startswith(b'{INIT_DATA}'):
            data = data[len(b'{INIT_DATA}'):].decode('ascii')
            data = json.loads(data)
            for i in ['seed', 'player_turn', 'nickname']:
                self.client_init_data[i] = data[i]

        elif data.startswith(b'{CARD}'):
            data = data[len(b'{CARD}'):]
            pickled_data: tuple[str, int] = pickle.loads(data)
            self.client_data['card'] = pickled_data
        
        elif data.startswith(b'{MART}'):
            data = data[len(b'{MART}'):]
            self.client_data['mart'] = True
        
        elif data.startswith(b'{REQUEST}'):
            data = data[len(b'{REQUEST}'):].decode('ascii')
            self.client_data['request'] = data
        
        elif data.startswith(b'{NICKNAME}'):
            data = data[len(b'{NICKNAME}'):].decode('ascii')
            self.client_data['conn_nickname'] = data

        else:
            data = data.decode('ascii')
            print(f'recieved message in proc data: {data}')
    
    def write(self):
        while self._client_is_alive:
            message = f'{self.nickname}: {input(">>> ")}'
    
            encoded_message = message.encode('ascii')
            self.client.send(encoded_message)
    
            # Read input from the user and send messages until a specific condition is met
            # while True:
            #     user_input = input(">>> ")
            #     if user_input == "quit":
            #         self._client_is_alive = False
            #         break
            #     encoded_message = user_input.encode('ascii')
            #     self.client.send(encoded_message)
    
    def send_data(
            self, 
            data: str | tuple, 
            data_type: Literal['CARD', 'MART', 'REQUEST']
        ):
        if isinstance(data, str):
            if data_type == 'INIT_DATA':
                encoded_data = b'{INIT_DATA}' + data.encode('ascii')
            elif data_type == 'MART':
                encoded_data = b'{MART}' + data.encode('ascii')
            elif data_type == 'REQUEST':
                encoded_data = b'{REQUEST}' + data.encode('ascii')
            elif data_type == 'NICKNAME':
                encoded_data = b'{NICKNAME}' + data.encode('ascii')
            else:
                encoded_data = data.encode('ascii')

        elif isinstance(data, tuple):
            if data_type == 'CARD':
                encoded_data = b'{CARD}' + pickle.dumps(data)
        
        self.client.send(encoded_data)

    
    def shutdown(self):
        self._client_is_alive = False
        self.client.close()

        


if __name__ == '__main__':
    client = Client('localhost', 55555)
        
        
