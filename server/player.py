import socket

from .card import Card, card_list_json


class Player:
    username: str
    hand: list[Card]
    conn: socket.socket
    is_game_host: bool
    game_id: str

    drew_from_pile: bool

    def __init__(
        self, username: str, conn: socket.socket, is_game_host: bool, game_id: str
    ):
        self.username = username
        self.conn = conn
        self.hand = []
        self.is_game_host = is_game_host
        self.game_id = game_id
        self.drew_from_pile = False

    def give_card(self, card: Card) -> None:
        self.hand.append(card)

    def hand_json(self) -> list[dict]:
        return card_list_json(self.hand)

    def __repr__(self) -> str:
        return f"Player: {self.hand}"
