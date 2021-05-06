import socket

from card import Card


class Player:
    hand: list[Card]
    conn: socket.socket
    is_game_host: bool
    game_id: str

    def __init__(self, conn, is_game_host, game_id):
        self.conn = conn
        self.hand = []
        self.is_game_host = is_game_host
        self.game_id = game_id

    def give_card(self, card: Card):
        self.hand.append(card)

    def __repr__(self) -> str:
        return f"Player: {self.hand}"
