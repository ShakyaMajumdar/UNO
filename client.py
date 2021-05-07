import socket
import threading
from typing import Optional

from utils import send_message, receive_message

HEADER = 64
PORT = 5050
FORMAT = "utf-8"

DISCONNECT_MESSAGE = "!DISCONNECT"
CREATE_GAME_MESSAGE = "!CREATE"
JOIN_GAME_MESSAGE = "!JOIN"
GAME_NOT_FOUND_MESSAGE = "!INVALID_GAME"
START_GAME_MESSAGE = "!START"
CARD_PLAYED_MESSAGE = "!MOVE"
DRAW_CARD_MESSAGE = "!DRAW"
GAME_OVER_MESSAGE = "!END"

SERVER = socket.gethostbyname(socket.gethostname())
ADDR = (SERVER, PORT)

conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
conn.connect(ADDR)


class Client:
    username: str
    is_host: bool

    game_in_progress: bool
    game_id: Optional[str]

    hand: Optional[list[dict]]
    opponents: list[dict]

    current_colour: Optional[str]
    current_number: Optional[int]
    current_effects: Optional[list]

    def __init__(self):
        self.game_in_progress = False
        self.game_id = None
        self.hand = None
        self.opponents = []

    def run(self):
        threading.Thread(target=self.server_listener).start()

        self.username = input("username? ")
        self.is_host = (input("create or join? ") == "create")

        if self.is_host:
            send_message(conn, category=CREATE_GAME_MESSAGE, username=self.username)
            print(self.game_id)
            input("press any key to start ")
            send_message(conn, category=START_GAME_MESSAGE)
        else:
            c = input("enter code ")
            send_message(conn, category=JOIN_GAME_MESSAGE, id_=c, username=self.username)
            print("wait for host to start")

        while not self.game_in_progress:
            pass
        print("game started")

        while self.game_in_progress:
            print(self.hand)

            a = input("can play? (y/n)")
            if a == "y":
                i = int(input("enter index"))
                c = None
                if "colour_change" in self.hand[i]["effects"]:
                    c = input("change to?")

                username = input("call uno")

                send_message(
                    conn,
                    category=CARD_PLAYED_MESSAGE,
                    card_index=i,
                    colour_change_to=c,
                    uno_called=username == "y",
                )

            if a == "n":
                send_message(conn, category=DRAW_CARD_MESSAGE)

    def server_listener(self):
        while True:
            msg = receive_message(conn)
            if msg.get("category") == GAME_OVER_MESSAGE:
                print("ending game")
                self.game_in_progress = False
                break

            if msg.get("category") == JOIN_GAME_MESSAGE:
                print(f"{msg.get('username')} joined")
                self.opponents.append({"username": msg.get("username")})

            if msg.get("category") == START_GAME_MESSAGE:
                self.hand = msg.get("hand")

            if msg.get("category") == CARD_PLAYED_MESSAGE:
                self.current_colour = msg.get("current_colour")
                self.current_number = msg.get("current_number")
                self.current_effects = msg.get("current_effects")
                # TODO do something with msg['player']

            if msg.get("category") == DRAW_CARD_MESSAGE:
                self.hand.append(
                    {
                        "colour": msg["colour"],
                        "number": msg["number"],
                        "effects": msg["effects"],
                    }
                )


client = Client()
client.run()
send_message(conn, category=DISCONNECT_MESSAGE)
