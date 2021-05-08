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
SKIP_TURN_MESSAGE = "!SKIP"
UNCALLED_UNO_MESSAGE = "!CAUGHT"

SERVER = socket.gethostbyname(socket.gethostname())
ADDR = (SERVER, PORT)

conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
conn.connect(ADDR)


class Client:
    username: str
    is_host: bool

    game_in_progress: bool
    game_id: Optional[str]
    is_turn: bool
    drew_card_from_pile: bool
    uncalled_uno: bool

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
        self.is_turn = False
        self.uncalled_uno = False
        self.drew_card_from_pile = False

    def run(self):
        threading.Thread(target=self.server_listener).start()

        self.username = input("username? ")
        self.is_host = (input("create or join? ") == "create")

        if self.is_host:
            send_message(conn, category=CREATE_GAME_MESSAGE, username=self.username)
            while not self.game_id:
                pass
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

            if self.uncalled_uno:
                print("you forgot to call uno! Your new hand: ")
                print(self.hand)
                self.uncalled_uno = False

            if not self.is_turn:
                continue

            print(self.current_colour, self.current_number, self.current_effects)
            print(self.hand)

            a = input("can play? (y/n) ")
            if a == "y":
                i = int(input("enter index "))
                c = None
                if "colour_change" in self.hand[i]["effects"]:
                    c = input("change to? ")

                uno = input("call uno ")

                send_message(
                    conn,
                    category=CARD_PLAYED_MESSAGE,
                    card_index=i,
                    colour_change_to=c,
                    uno_called=uno == "y",
                )

            if a == "n":
                if not self.drew_card_from_pile:
                    send_message(conn, category=DRAW_CARD_MESSAGE)
                else:
                    send_message(conn, category=SKIP_TURN_MESSAGE)

            self.is_turn = False

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

            if msg.get("category") == CREATE_GAME_MESSAGE:
                self.game_id = msg.get("id_")

            if msg.get("category") == START_GAME_MESSAGE:
                print("starting")
                self.current_colour = msg.get("current_colour")
                self.current_number = msg.get("current_number")
                self.current_effects = msg.get("current_effects")
                self.game_in_progress = True
                self.is_turn = msg.get("is_turn")
                self.hand = msg.get("hand")

            if msg.get("category") == CARD_PLAYED_MESSAGE:
                self.current_colour = msg.get("current_colour")
                self.current_number = msg.get("current_number")
                self.current_effects = msg.get("current_effects")
                self.hand = msg.get("hand")
                self.is_turn = msg.get("is_turn")
                print(self.is_turn)
                print(f"{msg['player']} played {self.current_colour} {self.current_number} {self.current_effects}")

            if msg.get("category") == DRAW_CARD_MESSAGE:
                self.hand.append(
                    {
                        "colour": msg["colour"],
                        "number": msg["number"],
                        "effects": msg["effects"],
                    }
                )

            if msg.get("category") == UNCALLED_UNO_MESSAGE:
                self.uncalled_uno = True
                self.hand = msg["hand"]


client = Client()
client.run()
send_message(conn, category=DISCONNECT_MESSAGE)
