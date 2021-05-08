import socket
import threading

from game import Game
from player import Player
from utils import receive_message, send_message, generate_random_id

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

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(ADDR)

on_going_games_by_id: dict[str, Game] = {}
players_by_conn: dict[socket.socket, Player] = {}


def handle_client(conn: socket.socket, addr: tuple[str, int]):
    print(f"[NEW CONNECTION] {addr} connected.", flush=True)

    connected = True
    while connected:
        msg = receive_message(conn)
        if msg.get("category") == DISCONNECT_MESSAGE:
            if conn in players_by_conn:
                player = players_by_conn[conn]
                game = on_going_games_by_id[player.game_id]
                game.remove_player(player)

                if not game.players:
                    on_going_games_by_id.pop(game.id_)
                players_by_conn.pop(conn)
            connected = False

        if msg.get("category") == JOIN_GAME_MESSAGE:
            if "id_" not in msg:
                continue
            id_ = msg["id_"]

            if id_ in on_going_games_by_id:
                game = on_going_games_by_id[id_]
                player = Player(msg.get("username"), conn, False, game.id_)
                game.add_player(player)
                players_by_conn[conn] = player

                print(f"[JOIN] {addr} joining game {game.id_}", flush=True)

                for player_ in game.players:
                    send_message(player_.conn, category=JOIN_GAME_MESSAGE, username=player.username)
            else:
                send_message(conn, category=GAME_NOT_FOUND_MESSAGE)

        if msg.get("category") == CREATE_GAME_MESSAGE:
            id_ = generate_random_id(set(on_going_games_by_id))
            game = Game(id_)
            player = Player(msg.get("username"), conn, True, game.id_)
            game.add_player(player)

            on_going_games_by_id[id_] = game
            players_by_conn[conn] = player
            send_message(conn, category=CREATE_GAME_MESSAGE, id_=id_)
            print(f"[CREATE] {addr} created game {game.id_}", flush=True)

        if msg.get("category") == START_GAME_MESSAGE:
            if conn not in players_by_conn:
                continue
            player = players_by_conn[conn]
            game = on_going_games_by_id[player.game_id]

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
            if conn not in players_by_conn:
                continue
            player = players_by_conn[conn]
            game = on_going_games_by_id[player.game_id]
            if not game.current_turn == player:
                continue

            update = game.update(
                player, msg["card_index"], msg["colour_change_to"], msg["uno_called"]
            )

            if update["status"] == "invalid_card":
                send_message(conn, category=CARD_PLAYED_MESSAGE, **update)
            elif update["status"] == "uncalled_uno":
                send_message(conn, category=UNCALLED_UNO_MESSAGE, hand=player.hand_json())
            else:
                for player_ in game.players:
                    print(player_.username, player_ == game.current_turn)
                    send_message(
                        player_.conn,
                        category=CARD_PLAYED_MESSAGE,
                        player=player.username,
                        is_turn=player_ == game.current_turn,
                        hand=player_.hand_json(),
                        **update,
                    )

            print(f"[PLAY] {addr} played {msg['card_index']} in {game.id_}", flush=True)

        if msg.get("category") == DRAW_CARD_MESSAGE:
            player = players_by_conn[conn]
            game = on_going_games_by_id[player.game_id]
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
            player = players_by_conn[conn]
            game = on_going_games_by_id[player.game_id]
            if not player.drew_from_pile:
                continue
            game.current_turn = next(game.turns)
            player.drew_from_pile = False

    conn.close()
    print(f"[CONNECTION CLOSED] {addr} disconnected", flush=True)


def start():
    server.listen()
    print(f"[LISTENING] server listening on {ADDR}", flush=True)
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()
        print(f"[ACTIVE CONNECTIONS]: {threading.activeCount() - 1}", flush=True)


print("[STARTING] server starting", flush=True)
start()
