import json
import socket

FORMAT = "utf-8"
HEADER = 64


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
