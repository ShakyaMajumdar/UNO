import os
import socket
import sys
import threading
import time
from typing import Optional

import pygame
import pygame.freetype
import pygame_widgets

from .asset_loader import load_assets
from .utils import send_message, receive_message

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

BLACK = (0, 0, 0)


class Client:
    username: str
    is_host: bool

    game_in_progress: bool
    game_id: Optional[str]
    is_turn: bool
    drew_card_from_pile: bool
    called_uno: bool
    caught: bool

    hand: Optional[list[dict]]
    opponents: list[dict]

    current_colour: Optional[str]
    current_number: Optional[int]
    current_effects: Optional[tuple[str]]

    showing_menu: bool
    joined_game: bool
    valid_id: bool
    disconnected: bool

    font: pygame.font.Font
    menu_window_size: tuple[int, int]
    game_window_size: tuple[int, int]
    menu_background: pygame.Surface
    game_background: pygame.Surface
    card_sprites: dict[tuple[Optional[str], Optional[int], tuple[str]], pygame.Surface]

    def __init__(self):
        self.game_in_progress = False
        self.game_id = None
        self.hand = None
        self.opponents = []
        self.is_turn = False
        self.called_uno = False
        self.caught = False
        self.drew_card_from_pile = False

        self.showing_menu = True
        self.joined_game = False
        self.valid_invite = False
        self.disconnected = False

        os.environ["SDL_VIDEO_CENTERED"] = "1"
        os.environ["SDL_VIDEO_WINDOW_POS"] = "0,0"
        pygame.init()

        self.menu_window_size = (600, 600)
        screen_info = pygame.display.Info()
        self.game_window_size = int(0.9 * screen_info.current_w), int(
            0.9 * screen_info.current_h
        )

        gradient, self.font, self.card_sprites = load_assets()
        self.menu_background = pygame.transform.smoothscale(
            gradient, self.menu_window_size
        )
        self.game_background = pygame.transform.smoothscale(
            gradient, self.game_window_size
        )

    def run(self):
        threading.Thread(target=self.server_listener).start()
        screen = pygame.display.set_mode(self.menu_window_size)

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
            time.sleep(0.1)

        def invite_code_listener():
            send_message(
                conn,
                category=JOIN_GAME_MESSAGE,
                id_=invite_code_textbox.getText(),
                username=self.username,
            )

        def card_click_listener(card_index):
            if not self.is_turn:
                print("not your turn")
                return
            card_played = self.hand[card_index]
            if not (
                    "colour_change" in card_played["effects"]
                    or self.current_colour == card_played["colour"]
                    or self.current_number == card_played["number"]
                    or set(self.current_effects).intersection(card_played["effects"])
            ):
                return

            send_message(
                conn,
                category=CARD_PLAYED_MESSAGE,
                card_index=card_index,
                colour_change_to=None,
                uno_called=self.called_uno,
            )

            self.hand.pop(card_index)
            self.is_turn = False
            self.drew_card_from_pile = False

        def draw_card_button_listener():
            if not self.is_turn:
                return
            if not self.drew_card_from_pile:
                send_message(conn, category=DRAW_CARD_MESSAGE)
                self.drew_card_from_pile = True

            else:
                send_message(conn, category=SKIP_TURN_MESSAGE)
                self.is_turn = False
                self.drew_card_from_pile = False

        def uno_call_button_listener():
            self.called_uno = True

        username_textbox = pygame_widgets.TextBox(
            screen,
            x=self.menu_window_size[0] // 2 - 100,
            y=self.menu_window_size[1] // 4,
            width=200,
            height=60,
            fontSize=30,
            font=self.font,
            borderColour=BLACK,
            radius=10,
            textColour=BLACK,
            borderThickness=2,
        )

        invite_code_textbox = pygame_widgets.TextBox(
            screen,
            x=self.menu_window_size[0] // 2 - 100,
            y=self.menu_window_size[1] // 4,
            width=200,
            height=60,
            fontSize=30,
            font=self.font,
            borderColour=BLACK,
            radius=10,
            textColour=BLACK,
            borderThickness=2,
            onSubmit=invite_code_listener,
        )

        join_button = pygame_widgets.Button(
            screen,
            x=self.menu_window_size[0] // 2 - 125,
            y=3 * self.menu_window_size[1] // 4,
            width=250,
            height=60,
            fontSize=60,
            font=self.font,
            borderColour=BLACK,
            radius=10,
            textColour=BLACK,
            borderThickness=2,
            onClick=join_button_listener,
            text="Join with Invite",
            textHAlign="center",
            textVAlign="center",
        )

        create_button = pygame_widgets.Button(
            screen,
            x=self.menu_window_size[0] // 2 - 125,
            y=self.menu_window_size[1] // 2,
            width=250,
            height=60,
            font=self.font,
            fontSize=60,
            borderColour=BLACK,
            radius=10,
            textColour=BLACK,
            borderThickness=2,
            onClick=create_button_listener,
            text="Create New",
            textHAlign="center",
            textVAlign="center",
        )

        game_start_button = pygame_widgets.Button(
            screen,
            x=self.menu_window_size[0] // 2 - 100,
            y=3 * self.menu_window_size[1] // 4,
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
                screen.blit(self.menu_background, (0, 0))
                screen.blit(
                    self.font.render("Username", True, BLACK),
                    (
                        self.menu_window_size[0] // 2
                        - self.font.size("Username")[0] // 2,
                        self.menu_window_size[1] // 4 - 50,
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

                    screen.blit(self.menu_background, (0, 0))
                    screen.blit(
                        self.font.render(invite_code_message, True, BLACK),
                        (self.menu_window_size[0] // 2 - icm_width // 2, 100),
                    )
                    screen.blit(
                        self.font.render(players_joined_message, True, BLACK),
                        (
                            self.menu_window_size[0] // 2
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
                                BLACK,
                            ),
                            (100, 210 + self.font.get_linesize() * i),
                        )

                    game_start_button.listen(events)
                    game_start_button.draw()

                    pygame.display.update()
                    continue

                else:
                    screen.blit(self.menu_background, (0, 0))
                    if not self.joined_game:
                        screen.blit(self.menu_background, (0, 0))
                        screen.blit(
                            self.font.render("Invite Code: ", True, BLACK),
                            (
                                self.menu_window_size[0] // 2
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
                            self.font.render(waiting_message, True, BLACK),
                            (
                                self.menu_window_size[0] // 2
                                - self.font.size(waiting_message)[0] // 2,
                                100,
                            ),
                        )
                        screen.blit(
                            self.font.render(players_joined_message, True, BLACK),
                            (
                                self.menu_window_size[0] // 2
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
                                    BLACK,
                                ),
                                (100, 210 + self.font.get_linesize() * i),
                            )

                    pygame.display.update()
                    continue

            if self.game_in_progress:
                pygame.display.set_mode(self.game_window_size)

                screen.blit(self.game_background, (0, 0))
                if self.caught:
                    print("you forgot to call uno! Your new hand: ")
                    print(self.hand)
                    self.caught = False

                card_width = 218
                card_height = 328

                current_card = self.card_sprites[
                    self.current_colour, self.current_number, self.current_effects
                ]
                screen.blit(
                    current_card,
                    (
                        (self.game_window_size[0] - card_width) // 2,
                        (self.game_window_size[1] - card_height) // 2,
                    ),
                )

                pad = max((50, 50 + card_width * (7 - len(self.hand))))
                card_sprite_allowed_width = (
                    (self.game_window_size[0] - pad - card_width) / (len(self.hand) - 1)
                    if len(self.hand) > 1
                    else card_width
                )

                for i, card in enumerate(self.hand):
                    card_sprite = self.card_sprites[
                        card["colour"], card["number"], card["effects"]
                    ]
                    start_x = int(pad / 2 + card_sprite_allowed_width * i)
                    start_y = 300
                    screen.blit(
                        card_sprite,
                        (
                            start_x,
                            start_y,
                        ),
                    )

                    card_click_button = pygame_widgets.Button(
                        screen,
                        start_x,
                        start_y,
                        card_sprite_allowed_width
                        if i < len(self.hand) - 1
                        else card_width,
                        card_height,
                        onClick=card_click_listener,
                        onClickParams=(i,),
                    )

                    card_click_button.listen(events)

                draw_card_button = pygame_widgets.Button(
                    screen,
                    x=100,
                    y=100,
                    width=200,
                    height=50,
                    fontSize=30,
                    font=self.font,
                    radius=10,
                    onClick=draw_card_button_listener,
                    text="Skip turn!" if self.drew_card_from_pile else "Draw card from deck!"
                )

                draw_card_button.draw()
                draw_card_button.listen(events)

                uno_call_button = pygame_widgets.Button(
                    screen,
                    x=600,
                    y=100,
                    width=100,
                    height=50,
                    fontSize=30,
                    font=self.font,
                    radius=10,
                    onClick=uno_call_button_listener,
                    text="Say UNO!"
                )

                uno_call_button.draw()
                uno_call_button.listen(events)

                pygame.display.update()
                continue

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

    def server_listener(self):
        while not self.disconnected:
            msg = receive_message(conn)
            if msg.get("category") == DISCONNECT_MESSAGE:
                if msg.get("username") == self.username:
                    continue
                for player in self.opponents:
                    if player["username"] == msg.get("username"):
                        self.opponents.remove(player)
                        break

            if msg.get("category") == GAME_OVER_MESSAGE:
                self.game_in_progress = False
                break

            if msg.get("category") == JOIN_GAME_MESSAGE:
                self.joined_game = True
                if "username" in msg:
                    print(f"{msg.get('username')} joined")
                    self.opponents.append(
                        {"username": msg.get("username"), "is_host": False}
                    )
                else:
                    self.opponents = msg["opponents"]

            if msg.get("category") == CREATE_GAME_MESSAGE:
                self.game_id = msg.get("id_")

            if msg.get("category") == START_GAME_MESSAGE:
                self.current_colour = msg.get("current_colour")
                self.current_number = msg.get("current_number")
                self.current_effects = tuple(msg.get("current_effects"))
                self.game_in_progress = True
                self.is_turn = msg.get("is_turn")
                self.hand = [
                    i | {"effects": tuple(i["effects"])} for i in msg.get("hand")
                ]

            if msg.get("category") == CARD_PLAYED_MESSAGE:
                self.current_colour = msg.get("current_colour")
                self.current_number = msg.get("current_number")
                self.current_effects = tuple(msg.get("current_effects"))
                self.hand = [
                    i | {"effects": tuple(i["effects"])} for i in msg.get("hand")
                ]
                self.is_turn = msg.get("is_turn")
                print(
                    f"{msg['player']} played {self.current_colour} {self.current_number} {self.current_effects}"
                )

            if msg.get("category") == DRAW_CARD_MESSAGE:
                self.hand.append(
                    {
                        "colour": msg["colour"],
                        "number": msg["number"],
                        "effects": tuple(msg["effects"]),
                    }
                )

            if msg.get("category") == SKIP_TURN_MESSAGE:
                self.is_turn = msg.get("is_turn")

            if msg.get("category") == UNCALLED_UNO_MESSAGE:
                self.caught = True
                self.hand = [
                    i | {"effects": tuple(i["effects"])} for i in msg.get("hand")
                ]
        sys.exit()
