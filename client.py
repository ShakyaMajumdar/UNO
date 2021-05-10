import socket
import sys
import threading
from typing import Optional

import pygame
import pygame.freetype
import pygame_widgets

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

MENU_WINDOW_SIZE = (600, 600)

MENU_BACKGROUND_IMAGE = pygame.transform.smoothscale(
    pygame.image.load("assets/gradient.png"), MENU_WINDOW_SIZE
)


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

    showing_menu: bool
    joined_game: bool
    valid_id: bool
    disconnected: bool

    font: pygame.font.Font

    def __init__(self):
        self.game_in_progress = False
        self.game_id = None
        self.hand = None
        self.opponents = []
        self.is_turn = False
        self.uncalled_uno = False
        self.drew_card_from_pile = False

        self.showing_menu = True
        self.joined_game = False
        self.valid_invite = False
        self.disconnected = False

        pygame.init()
        self.font = pygame.font.Font("assets/Girassol/Girassol-Regular.ttf", 30)

    def run(self):
        threading.Thread(target=self.server_listener).start()
        screen = pygame.display.set_mode(MENU_WINDOW_SIZE)

        def create_button_listener():
            self.showing_menu = False
            self.is_host = True
            self.username = username_textbox.getText()
            send_message(conn, category=CREATE_GAME_MESSAGE, username=self.username)

        def join_button_listener():
            self.showing_menu = False
            self.is_host = False
            self.username = "".join(username_textbox.text)

        def game_start_button_listener():
            send_message(conn, category=START_GAME_MESSAGE)

        def invite_code_listener():
            send_message(
                conn,
                category=JOIN_GAME_MESSAGE,
                id_=invite_code_textbox.getText(),
                username=self.username,
            )

        username_textbox = pygame_widgets.TextBox(
            screen,
            x=MENU_WINDOW_SIZE[0] // 2 - 100,
            y=MENU_WINDOW_SIZE[1] // 4,
            width=200,
            height=60,
            fontSize=30,
            font=self.font,
            borderColour=(0, 0, 0),
            radius=10,
            textColour=(0, 0, 0),
            borderThickness=2,
        )

        invite_code_textbox = pygame_widgets.TextBox(
            screen,
            x=MENU_WINDOW_SIZE[0] // 2 - 100,
            y=MENU_WINDOW_SIZE[1] // 4,
            width=200,
            height=60,
            fontSize=30,
            font=self.font,
            borderColour=(0, 0, 0),
            radius=10,
            textColour=(0, 0, 0),
            borderThickness=2,
            onSubmit=invite_code_listener,
        )

        join_button = pygame_widgets.Button(
            screen,
            x=MENU_WINDOW_SIZE[0] // 2 - 125,
            y=3 * MENU_WINDOW_SIZE[1] // 4,
            width=250,
            height=60,
            fontSize=60,
            font=self.font,
            borderColour=(0, 0, 0),
            radius=10,
            textColour=(0, 0, 0),
            borderThickness=2,
            onClick=join_button_listener,
            text="Join with Invite",
            textHAlign="center",
            textVAlign="center",
        )

        create_button = pygame_widgets.Button(
            screen,
            x=MENU_WINDOW_SIZE[0] // 2 - 125,
            y=MENU_WINDOW_SIZE[1] // 2,
            width=250,
            height=60,
            font=self.font,
            fontSize=60,
            borderColour=(0, 0, 0),
            radius=10,
            textColour=(0, 0, 0),
            borderThickness=2,
            onClick=create_button_listener,
            text="Create New",
            textHAlign="center",
            textVAlign="center",
        )

        game_start_button = pygame_widgets.Button(
            screen,
            x=MENU_WINDOW_SIZE[0] // 2 - 100,
            y=3 * MENU_WINDOW_SIZE[1] // 4,
            width=200,
            height=50,
            fontSize=30,
            font=self.font,
            radius=10,
            onClick=game_start_button_listener,
            text="Start Now!",
        )

        while True:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.disconnected = True
                    send_message(conn, category=DISCONNECT_MESSAGE)
                    pygame.quit()
                    sys.exit()

            if self.showing_menu:
                screen.blit(MENU_BACKGROUND_IMAGE, (0, 0))
                screen.blit(
                    self.font.render("Username", True, (0, 0, 0)),
                    (
                        MENU_WINDOW_SIZE[0] // 2 - self.font.size("Username")[0] // 2,
                        MENU_WINDOW_SIZE[1] // 4 - 50,
                    ),
                )

                username_textbox.listen(events)
                username_textbox.draw()

                join_button.listen(events)
                join_button.draw()

                create_button.listen(events)
                create_button.draw()

                pygame.display.update()
                continue

            if not self.game_in_progress:
                if self.is_host:
                    if not self.game_id:
                        continue

                    invite_code_message = f"Invite Code: {self.game_id}"
                    players_joined_message = f"Players: {len(self.opponents) + 1}/4"
                    icm_width, icm_height = self.font.size(invite_code_message)

                    screen.blit(MENU_BACKGROUND_IMAGE, (0, 0))
                    screen.blit(
                        self.font.render(invite_code_message, True, (0, 0, 0)),
                        (MENU_WINDOW_SIZE[0] // 2 - icm_width // 2, 100),
                    )
                    screen.blit(
                        self.font.render(players_joined_message, True, (0, 0, 0)),
                        (
                            MENU_WINDOW_SIZE[0] // 2
                            - self.font.size(players_joined_message)[0] // 2,
                            200,
                        ),
                    )
                    for i, player in enumerate(
                        [{"username": self.username, "is_host": True}] + self.opponents,
                        start=1,
                    ):
                        screen.blit(
                            self.font.render(
                                f"{i}. {player['username']} {'(host)' if player['is_host'] else ''}",
                                True,
                                (0, 0, 0),
                            ),
                            (100, 210 + self.font.get_linesize() * i),
                        )

                    game_start_button.listen(events)
                    game_start_button.draw()

                    pygame.display.update()
                    continue

                else:
                    screen.blit(MENU_BACKGROUND_IMAGE, (0, 0))
                    if not self.joined_game:
                        screen.blit(MENU_BACKGROUND_IMAGE, (0, 0))
                        screen.blit(
                            self.font.render("Invite Code: ", True, (0, 0, 0)),
                            (
                                MENU_WINDOW_SIZE[0] // 2
                                - self.font.size("Invite Code: ")[0] // 2,
                                100,
                            ),
                        )
                        invite_code_textbox.listen(events)
                        invite_code_textbox.draw()
                    else:
                        waiting_message = "Waiting for host to start..."
                        players_joined_message = f"Players: {len(self.opponents) + 1}/4"
                        screen.blit(
                            self.font.render(waiting_message, True, (0, 0, 0)),
                            (
                                MENU_WINDOW_SIZE[0] // 2
                                - self.font.size(waiting_message)[0] // 2,
                                100,
                            ),
                        )
                        screen.blit(
                            self.font.render(players_joined_message, True, (0, 0, 0)),
                            (
                                MENU_WINDOW_SIZE[0] // 2
                                - self.font.size(players_joined_message)[0] // 2,
                                200,
                            ),
                        )
                        for i, player in enumerate(
                            [{"username": self.username, "is_host": False}]
                            + self.opponents,
                            start=1,
                        ):
                            screen.blit(
                                self.font.render(
                                    f"{i}. {player['username']} {'(host)' if player['is_host'] else ''}",
                                    True,
                                    (0, 0, 0),
                                ),
                                (100, 210 + self.font.get_linesize() * i),
                            )

                    pygame.display.update()
                    continue

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

            pygame.display.update()

    def server_listener(self):
        while not self.disconnected:
            msg = receive_message(conn)
            if msg.get("category") == GAME_OVER_MESSAGE:
                print("ending game")
                self.game_in_progress = False
                break

            if msg.get("category") == JOIN_GAME_MESSAGE:
                self.joined_game = True
                if "username" in msg:
                    print(f"{msg.get('username')} joined")
                    self.opponents.append({"username": msg.get("username"), "is_host": False})
                else:
                    self.opponents = msg["opponents"]
                print(self.opponents)

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
                print(
                    f"{msg['player']} played {self.current_colour} {self.current_number} {self.current_effects}"
                )

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
        sys.exit()


client = Client()
client.run()
send_message(conn, category=DISCONNECT_MESSAGE)
