import socket, threading
from typing import Union, Literal
import json


class Server:
    def __init__(self, host: Union[str, Literal["localhost", "127.0.0.1"]], port: int):
        self.host = host
        self.port = port
        self.connections = {}
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
            KeyboardInterrupt,
        )

        self._server_is_alive = True
        self._server_data = {"seed": "", "player_turn": "", "nickname": ""}

        threading.Thread(target=self.receive_client).start()

    def store_data(self, data: bytes):
        if data.startswith(b"{INIT_DATA}"):
            data = data[len(b"{INIT_DATA}") :].decode("ascii")
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
        """
        Handle the client connection.

        Parameters:
            conn (socket.socket): The socket object representing the client connection.
        """
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

                other_client_exit = (
                    "{OTHER_CLIENT_EXIT}" + f"{nickname} has left the chat!"
                )
                self.broadcast(other_client_exit.encode("ascii"), conn)

                self.nicknames.remove(nickname)
                self._server_is_alive = False
                break
            # return

    def receive_client(self):
        while self._server_is_alive:
            try:
                client, address = self.server_socket.accept()
            except OSError as e:
                print(f"An error occured! {e}")
                break

            client.send("NICK".encode("ascii"))
            nickname = client.recv(1024).decode("ascii")
            self.nicknames.append(nickname)
            self.clients.append(client)

            print(f"{nickname} Connected with {address}")

            # broadcast with a tag that a user joined
            user_joined = "{CLIENT_JOINED}" + f"{nickname} joined!"
            self.broadcast(user_joined.encode("ascii"), client)

            init_data = "{INIT_DATA}" + json.dumps(self._server_data)
            client.send(init_data.encode("ascii"))

            thread = threading.Thread(target=self.handle_client, args=(client,))
            thread.start()

    def shutdown(self):
        print("shutting down server")
        server_shutdown_msg = "{SERVER_SHUTDOWN}" + f"Server Shutting Down!"
        self.broadcast(
            server_shutdown_msg.encode("ascii"), sender=None, exclude_sender=False
        )
        self._server_is_alive = False
        self.server_socket.close()


class Client:
    def __init__(
        self,
        address: Union[str, Literal["localhost", "127.0.0.1"]],
        port: int,
        nickname="",
    ):
        self.address = address
        self.port = port
        self.nickname = nickname

        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((self.address, self.port))

        self._client_is_alive = True
        self._other_client_alive = True

        self.client_data: dict[Union[tuple[str, int], int, str, bool, list]] = {
            "card": None,  # tuple[str, int]
            "card_index": None,  # int
            "seed": None,  # int
            "player_turn": None,
            "nickname": "",
            "conn_nickname": "",
            "request": "",
            "mart": False,
        }

        self.client_init_data: dict[str, Union[int, str, None]] = {
            "seed": None,
            "player_turn": "",
            "nickname": "",
        }

        self._connection_exceptions = (
            socket.timeout,
            ConnectionResetError,
            ConnectionAbortedError,
            OSError,
        )

        self.send_nickname()
        threading.Thread(target=self.recieve).start()

    def send_nickname(self):
        try:
            message = self.client.recv(1024).decode("ascii")
            if message == "NICK":
                self.client.send(self.nickname.encode("ascii"))
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
                self.shutdown()
                break
        else:
            print("Were disconnected...")

    def process_data(self, data: bytes):
        print("in process data, data recv -->", type(data), data)
        data = data.decode("ascii")

        message_map = {
            "{INIT_DATA}": lambda d: self.client_init_data.update(json.loads(d)),
            "{CARD}": lambda d: self.client_data.__setitem__(
                "card", tuple(json.loads(d))
            ),
            "{CARD_INDEX}": lambda idx: self.client_data.__setitem__("card_index", idx),
            "{MART}": lambda _: self.client_data.__setitem__("mart", True),
            "{REQUEST}": lambda d: self.client_data.__setitem__("request", d),
            "{NICKNAME}": lambda d: self.client_data.__setitem__("conn_nickname", d),
            "{CLIENT_JOINED}": lambda _: setattr(self, "_other_client_alive", True),
            "{OTHER_CLIENT_EXIT}": lambda _: setattr(
                self, "_other_client_alive", False
            ),
            "{SERVER_SHUTDOWN}": lambda _: setattr(self, "_other_client_alive", False),
        }

        for prefix, action in message_map.items():
            if data.startswith(prefix):
                action(data[len(prefix) :])
                return

    def send_data(
        self,
        data: str | tuple,
        data_type: Literal["CARD", "CARD_INDEX", "MART", "REQUEST", "NICKNAME"],
    ):
        encoded_data = None

        if isinstance(data, str):
            if data_type in ["INIT_DATA", "MART", "REQUEST", "NICKNAME"]:
                encoded_data = f"{{{data_type}}}{data}".encode("ascii")
            else:
                encoded_data = data.encode("ascii")

        elif isinstance(data, tuple):
            if data_type == "CARD":
                encoded_data = ("{CARD}" + json.dumps(data)).encode("ascii")

        self.client.send(encoded_data) if encoded_data else None
        print("sent_data -->", encoded_data)

    def shutdown(self):
        try:
            self._client_is_alive = False
            self.client.close()
        except self._connection_exceptions as e:
            print(f"An error occured! {e}")
