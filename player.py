from card import Card


class Player:
    hand: list[Card]

    def __init__(self):
        self.hand = []

    def give_card(self, card: Card):
        self.hand.append(card)

    def __repr__(self) -> str:
        return f"Player: {self.hand}"
