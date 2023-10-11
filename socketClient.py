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
            'mart': False,
            'continue': False
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
        else:
            print('Were disconnected...')
    
    def process_data(self, data: bytes):
        print('in process data, data recv -->', type(data), data)
        data = data.decode('ascii')
        
        message_map = {
        '{INIT_DATA}': lambda d: self.client_init_data.update(json.loads(d)),
        '{CARD}': lambda d: self.client_data.__setitem__('card', tuple(json.loads(d))),
        '{MART}': lambda _: self.client_data.__setitem__('mart', True),
        '{REQUEST}': lambda d: self.client_data.__setitem__('request', d),
        '{NICKNAME}': lambda d: self.client_data.__setitem__('conn_nickname', d),
        '{CONTINUE}': lambda _: self.client_data.__setitem__('continue', True),
    }

        for prefix, action in message_map.items():
            if data.startswith(prefix):
                action(data[len(prefix):])
                return
            
    def send_data(
            self, 
            data: str | tuple, 
            data_type: Literal['CARD', 'MART', 'REQUEST', 'NICKNAME', 'CONTINUE']
        ):
        encoded_data = None

        if isinstance(data, str):
            if data_type in ['INIT_DATA', 'MART', 'REQUEST', 'NICKNAME', 'CONTINUE']:
                encoded_data = f'{{{data_type}}}{data}'.encode('ascii')
            else:
                encoded_data = data.encode('ascii')

        elif isinstance(data, tuple):
            if data_type == 'CARD':
                encoded_data = ('{CARD}'+ json.dumps(data)).encode('ascii')
        
        self.client.send(encoded_data) if encoded_data else None
        print('sent_data -->', encoded_data)

    
    def shutdown(self):
        self._client_is_alive = False
        self.client.close()

        

if __name__ == '__main__':
    client = Client('localhost', 55555)
        
        
