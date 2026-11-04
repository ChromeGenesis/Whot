"""2-player LAN link for Whot: framed JSON messages over stdlib TCP.

Wire format: 4-byte big-endian length + utf-8 JSON {"t": <type>, "p": payload}.
Length-prefixing fixes the old protocol's fatal flaw (bare recv(1024) +
prefix matching silently drops/corrupts coalesced or split TCP segments).

Topology is unchanged: the host runs Server, both sides run Client, the
server relays every message to the *other* client. No third-party deps.

Threading: one daemon reader thread per connection. Client pushes decoded
messages into `events` (queue.Queue) and also mirrors them into the legacy
`client_data` / `client_init_data` dicts the GUI polls. GUI must drain
`events` or poll the dicts from the mainloop only.
"""

import json
import queue
import socket
import struct
import threading

HEADER = struct.Struct(">I")
RECV_TIMEOUT = 0.5


def _send_msg(conn: socket.socket, msg_type: str, payload=None) -> None:
    body = json.dumps({"t": msg_type, "p": payload}).encode("utf-8")
    conn.sendall(HEADER.pack(len(body)) + body)


def _recv_exact(conn: socket.socket, n: int) -> bytes | None:
    buf = b""
    while len(buf) < n:
        try:
            chunk = conn.recv(n - len(buf))
        except socket.timeout:
            continue
        except OSError:
            return None
        if not chunk:
            return None
        buf += chunk
    return buf


def _recv_msg(conn: socket.socket) -> dict | None:
    raw_len = _recv_exact(conn, HEADER.size)
    if raw_len is None:
        return None
    (length,) = HEADER.unpack(raw_len)
    if length <= 0 or length > 1_000_000:
        return None
    raw = _recv_exact(conn, length)
    if raw is None:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None


class Server:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self._lock = threading.Lock()
        self._clients: list[dict] = []  # {"conn", "addr", "nickname"}
        self._client_is_alive = True
        self._server_data: dict = {"seed": "", "player_turn": "",
                                   "nickname": ""}

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(2)
        self.server_socket.settimeout(RECV_TIMEOUT)
        print(f"Server listening on {self.host}:{self.port}")

        threading.Thread(target=self._accept_loop, daemon=True).start()

    # -- internals ------------------------------------------------------
    def _accept_loop(self):
        while self._client_is_alive:
            try:
                conn, addr = self.server_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._register,
                             args=(conn, addr), daemon=True).start()

    def _register(self, conn: socket.socket, addr):
        conn.settimeout(10.0)
        try:
            _send_msg(conn, "NICK")
            reply = _recv_msg(conn)
        except OSError:
            conn.close()
            return
        if not reply or reply.get("t") != "NICKNAME":
            conn.close()
            return
        nickname = str(reply.get("p") or "Guest")
        conn.settimeout(RECV_TIMEOUT)
        with self._lock:
            self._clients.append({"conn": conn, "addr": addr,
                                  "nickname": nickname})
        print(f"{nickname} connected with {addr}")
        self._broadcast({"t": "CLIENT_JOINED", "p": nickname}, exclude=conn)
        try:
            _send_msg(conn, "INIT_DATA", self._server_data)
        except OSError:
            self._drop(conn)
            return
        threading.Thread(target=self._handle,
                         args=(conn,), daemon=True).start()

    def _handle(self, conn: socket.socket):
        while self._client_is_alive:
            msg = _recv_msg(conn)
            if msg is None:
                self._drop(conn, announce=True)
                return
            if msg.get("t") == "INIT_DATA" and isinstance(msg.get("p"), dict):
                with self._lock:
                    self._server_data = msg["p"]
            self._broadcast(msg, exclude=conn)

    def _broadcast(self, msg: dict, exclude=None):
        dead = []
        with self._lock:
            targets = [c["conn"] for c in self._clients if c["conn"] is not exclude]
        for conn in targets:
            try:
                _send_msg(conn, msg.get("t", ""), msg.get("p"))
            except OSError:
                dead.append(conn)
        for conn in dead:
            self._drop(conn, announce=True)

    def _drop(self, conn: socket.socket, announce=False):
        with self._lock:
            entry = next((c for c in self._clients if c["conn"] is conn), None)
            if entry is None:
                return
            self._clients.remove(entry)
        try:
            conn.close()
        except OSError:
            pass
        if announce:
            self._broadcast({"t": "OTHER_CLIENT_EXIT",
                             "p": f"{entry['nickname']} has left!"})
        print(f"{entry['nickname']} disconnected")

    # -- public ----------------------------------------------------------
    def client_count(self) -> int:
        with self._lock:
            return len(self._clients)

    def shutdown(self):
        print("shutting down server")
        self._client_is_alive = False
        self._broadcast({"t": "SERVER_SHUTDOWN", "p": "Server shutting down!"})
        with self._lock:
            conns = [c["conn"] for c in self._clients]
            self._clients.clear()
        for conn in conns:
            try:
                conn.close()
            except OSError:
                pass
        try:
            self.server_socket.close()
        except OSError:
            pass


class Client:
    def __init__(self, address: str, port: int, nickname=""):
        self.address = address
        self.port = port
        self.nickname = nickname or "Guest"

        self.events: queue.Queue = queue.Queue()
        self.client_data: dict = {
            "card": None,
            "card_index": None,
            "seed": None,
            "player_turn": None,
            "nickname": "",
            "conn_nickname": "",
            "request": "",
            "mart": False,
        }
        self.client_init_data: dict = {
            "seed": None,
            "player_turn": "",
            "nickname": "",
        }

        self._client_is_alive = True
        self._other_client_alive = True

        try:
            self.client = socket.create_connection((address, port), timeout=8)
        except OSError as e:
            self._client_is_alive = False
            raise ConnectionRefusedError(
                f"could not connect to {address}:{port}: {e}")
        self.client.settimeout(RECV_TIMEOUT)
        threading.Thread(target=self._receive_loop, daemon=True).start()

    # -- internals ------------------------------------------------------
    def _receive_loop(self):
        while self._client_is_alive:
            msg = _recv_msg(self.client)
            if msg is None:
                self._other_client_alive = False
                self.events.put({"t": "DISCONNECTED", "p": None})
                self._client_is_alive = False
                return
            self._dispatch(msg)

    def _dispatch(self, msg: dict):
        msg_type, payload = msg.get("t"), msg.get("p")
        if msg_type == "NICK":
            try:
                _send_msg(self.client, "NICKNAME", self.nickname)
            except OSError:
                pass
        elif msg_type == "INIT_DATA" and isinstance(payload, dict):
            self.client_init_data.update(payload)
            self.events.put(msg)
        elif msg_type == "CARD":
            try:
                self.client_data["card"] = tuple(payload)
            except TypeError:
                return
            self.events.put(msg)
        elif msg_type == "CARD_INDEX":
            self.client_data["card_index"] = payload
            self.events.put(msg)
        elif msg_type == "MART":
            self.client_data["mart"] = True
            self.events.put(msg)
        elif msg_type == "REQUEST":
            self.client_data["request"] = payload or ""
            self.events.put(msg)
        elif msg_type == "NICKNAME":
            self.client_data["conn_nickname"] = payload or ""
            self.events.put(msg)
        elif msg_type == "CLIENT_JOINED":
            self._other_client_alive = True
            self.events.put(msg)
        elif msg_type in ("OTHER_CLIENT_EXIT", "SERVER_SHUTDOWN"):
            self._other_client_alive = False
            self.events.put(msg)

    # -- public ----------------------------------------------------------
    def send_data(self, data, data_type: str):
        """Send one framed message. Payload must be JSON-serializable
        (card tuples, ints, strings)."""
        try:
            _send_msg(self.client, data_type, data)
        except OSError as e:
            print(f"send failed: {e}")
        else:
            print("sent_data -->", data_type, data)

    def shutdown(self):
        self._client_is_alive = False
        try:
            self.client.close()
        except OSError as e:
            print(f"An error occured! {e}")
