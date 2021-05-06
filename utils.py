import json
import random
import socket
import string

FORMAT = "utf-8"
HEADER = 64


def generate_random_id(preexisting_ids: set[str]) -> str:
    id_ = ""
    while not id_ or id_ in preexisting_ids:
        id_ = "".join(random.choices(string.ascii_letters, k=6))
    return id_


def send_message(conn: socket.socket, **msg) -> None:
    message = json.dumps(msg).encode(FORMAT)
    send_length = str(len(message)).encode(FORMAT)
    send_length += b" " * (HEADER - len(send_length))
    conn.send(send_length)
    conn.send(message)


def receive_message(conn: socket.socket) -> dict:
    msg_length = conn.recv(HEADER).decode(FORMAT)
    msg = "{}"

    if msg_length:
        msg_length = int(msg_length)
        msg = conn.recv(msg_length).decode(FORMAT)

    return json.loads(msg)
