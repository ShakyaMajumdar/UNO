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
            connected = False

        if msg.get("category") == JOIN_GAME_MESSAGE:
            if "id_" not in msg:
                continue
            id_ = msg["id_"]

            if id_ in on_going_games_by_id:
                game = on_going_games_by_id[id_]
                player = Player(conn, False, game.id_)
                game.add_player(player)
                players_by_conn[conn] = player

                print(f"[JOIN] {addr} joining game {game.id_}", flush=True)
            else:
                send_message(conn, category=GAME_NOT_FOUND_MESSAGE)

        if msg.get("category") == CREATE_GAME_MESSAGE:
            id_ = generate_random_id(set(on_going_games_by_id))
            game = Game(id_)
            player = Player(conn, True, game.id_)
            game.add_player(player)

            on_going_games_by_id[id_] = game
            players_by_conn[conn] = player

            print(f"[CREATE] {addr} created game {game.id_}", flush=True)

        if msg.get("category") == START_GAME_MESSAGE:
            if conn not in players_by_conn:
                continue
            player = players_by_conn[conn]
            game = on_going_games_by_id[player.game_id]
            if not player.is_game_host:
                send_message(conn, status="not_host")
                continue
            game.start()
            print(f"[START] starting game {game.id_}", flush=True)

        if msg.get("category") == "!MOVE":
            if conn not in players_by_conn:
                continue
            player = players_by_conn[conn]
            game = on_going_games_by_id[player.game_id]
            update = game.update(
                player, msg["card"], msg["colour_change_to"], msg["uno_called"]
            )

            for player_ in game.players:
                send_message(player_.conn, **update)

            print(f"[PLAY] {addr} played {msg['card']} in {game.id_}", flush=True)

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
