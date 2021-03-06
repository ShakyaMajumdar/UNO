import socket
import threading

from .game import Game
from .player import Player
from .utils import (
    receive_message,
    send_message,
    generate_random_id,
    generate_discriminator,
)

HEADER = 64
PORT = 5050
SERVER = socket.gethostbyname(socket.gethostname())
ADDR = (SERVER, PORT)
FORMAT = "utf-8"

DISCONNECT_MESSAGE = "!DISCONNECT"
CREATE_GAME_MESSAGE = "!CREATE"
JOIN_GAME_MESSAGE = "!JOIN"
GAME_NOT_FOUND_MESSAGE = "!INVALID_GAME"
START_GAME_MESSAGE = "!START"
CARD_PLAYED_MESSAGE = "!MOVE"
DRAW_CARD_MESSAGE = "!DRAW"
SKIP_TURN_MESSAGE = "!SKIP"
UNCALLED_UNO_MESSAGE = "!CAUGHT"


class Server:
    server: socket.socket
    on_going_games_by_id: dict[str, Game]
    players_by_conn: dict[socket.socket, Player]
    player_usernames: set[str]

    def __init__(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(ADDR)
        self.on_going_games_by_id = {}
        self.players_by_conn = {}
        self.player_usernames = set()

    def handle_client(self, conn: socket.socket, addr: tuple[str, int]):
        print(f"[NEW CONNECTION] {addr} connected.", flush=True)

        connected = True
        while connected:
            msg = receive_message(conn)
            if msg.get("category") == DISCONNECT_MESSAGE:
                if conn in self.players_by_conn:
                    player = self.players_by_conn[conn]
                    game = self.on_going_games_by_id[player.game_id]
                    for player_ in game.players:
                        send_message(
                            player_.conn,
                            category=DISCONNECT_MESSAGE,
                            player=player.username,
                        )
                    game.remove_player(player)

                    if not game.players:
                        self.on_going_games_by_id.pop(game.id_)
                    elif player.is_game_host:
                        game.players[0].is_game_host = True

                    self.players_by_conn.pop(conn)
                connected = False

            if msg.get("category") == JOIN_GAME_MESSAGE:
                if "id_" not in msg:
                    continue
                id_ = msg["id_"]

                if id_ in self.on_going_games_by_id:
                    game = self.on_going_games_by_id[id_]
                    username = (
                        msg.get("username")
                        + f"#{generate_discriminator(msg.get('username'), self.player_usernames)}"
                    )
                    self.player_usernames.add(username)
                    player = Player(username, conn, False, game.id_)
                    game.add_player(player)
                    self.players_by_conn[conn] = player

                    print(f"[JOIN] {addr} joining game {game.id_}", flush=True)

                    for player_ in game.players:
                        if player_ != player:
                            send_message(
                                player_.conn,
                                category=JOIN_GAME_MESSAGE,
                                subcategory="other",
                                username=player.username,
                            )

                    opponents = {
                        player_.username: {"is_host": player_.is_game_host}
                        for player_ in game.players
                        if player_ != player
                    }
                    send_message(
                        player.conn,
                        category=JOIN_GAME_MESSAGE,
                        subcategory="self",
                        opponents=opponents,
                        username=username,
                    )
                else:
                    send_message(conn, category=GAME_NOT_FOUND_MESSAGE)

            if msg.get("category") == CREATE_GAME_MESSAGE:
                id_ = generate_random_id(set(self.on_going_games_by_id))
                game = Game(id_)

                username = (
                    msg.get("username")
                    + f"#{generate_discriminator(msg.get('username'), self.player_usernames)}"
                )
                self.player_usernames.add(username)
                player = Player(username, conn, True, game.id_)
                game.add_player(player)

                self.on_going_games_by_id[id_] = game
                self.players_by_conn[conn] = player
                send_message(
                    conn, category=CREATE_GAME_MESSAGE, id_=id_, username=username
                )
                print(f"[CREATE] {addr} created game {game.id_}", flush=True)

            if msg.get("category") == START_GAME_MESSAGE:
                if conn not in self.players_by_conn:
                    continue
                player = self.players_by_conn[conn]
                game = self.on_going_games_by_id[player.game_id]

                if not player.is_game_host:
                    continue
                game.start()

                for player_ in game.players:
                    send_message(
                        player_.conn,
                        category=START_GAME_MESSAGE,
                        current_colour=game.current_colour,
                        current_number=game.current_number,
                        current_effects=game.current_effects,
                        is_turn=player_ == game.current_turn,
                        hand=player_.hand_json(),
                    )

                print(f"[START] starting game {game.id_}", flush=True)

            if msg.get("category") == CARD_PLAYED_MESSAGE:
                if conn not in self.players_by_conn:
                    continue
                player = self.players_by_conn[conn]
                game = self.on_going_games_by_id[player.game_id]
                if not game.current_turn == player:
                    continue

                update = game.update(
                    player,
                    msg["card_index"],
                    msg["uno_called"],
                    msg["colour_change_to"],
                )

                if update["status"] == "invalid_card":
                    send_message(conn, category=CARD_PLAYED_MESSAGE, **update)
                elif update["status"] == "uncalled_uno":
                    send_message(
                        conn, category=UNCALLED_UNO_MESSAGE, hand=player.hand_json()
                    )
                else:
                    for player_ in game.players:
                        send_message(
                            player_.conn,
                            category=CARD_PLAYED_MESSAGE,
                            player=player.username,
                            is_turn=player_ == game.current_turn,
                            hand=player_.hand_json(),
                            **update,
                        )

                print(
                    f"[PLAY] {addr} played {msg['card_index']} in {game.id_}",
                    flush=True,
                )

            if msg.get("category") == DRAW_CARD_MESSAGE:
                player = self.players_by_conn[conn]
                game = self.on_going_games_by_id[player.game_id]
                if not player.drew_from_pile:
                    card = game.draw_card()
                    player.give_card(card)
                    player.drew_from_pile = True
                    send_message(
                        conn,
                        category=DRAW_CARD_MESSAGE,
                        colour=card.colour,
                        number=card.number,
                        effects=card.effects,
                    )

            if msg.get("category") == SKIP_TURN_MESSAGE:
                player = self.players_by_conn[conn]
                game = self.on_going_games_by_id[player.game_id]
                if not player.drew_from_pile:
                    continue
                game.current_turn = next(game.turns)
                player.drew_from_pile = False
                for player_ in game.players:
                    send_message(
                        player_.conn,
                        category=SKIP_TURN_MESSAGE,
                        is_turn=player_ == game.current_turn,
                    )

        conn.close()
        print(f"[CONNECTION CLOSED] {addr} disconnected", flush=True)

    def start(self):
        self.server.listen()
        print(f"[LISTENING] server listening on {ADDR}", flush=True)
        while True:
            conn, addr = self.server.accept()
            thread = threading.Thread(target=self.handle_client, args=(conn, addr))
            thread.start()
            print(f"[ACTIVE CONNECTIONS]: {threading.activeCount() - 1}", flush=True)
