from dataclasses import dataclass
from typing import Optional


@dataclass
class Card:
    colour: Optional[str]
    number: Optional[int]
    effects: list[str]


def get_fresh_deck() -> list[Card]:
    deck: list[Card] = []
    for colour in ("red", "blue", "green", "yellow"):
        for number in range(10):
            for _ in range(2):
                deck.append(Card(colour, number, []))

        for effect in ("+2", "skip", "reverse"):
            for _ in range(2):
                deck.append(Card(colour, None, [effect]))

    for _ in range(4):
        deck.append(Card(None, None, ["colour change"]))

    for _ in range(4):
        deck.append(Card(None, None, ["colour change", "+4"]))

    return deck
