import itertools
import random
from typing import Optional, Union

from card import Card, get_fresh_deck
from player import Player


class OutOfCardsException(Exception):
    pass


class Game:
    draw_pile: list[Card]
    discard_pile: list[Card]
    players: list[Player]
    turns: itertools.cycle
    current_turn: Player

    current_number: Optional[int]
    current_colour: str
    current_effects: list[str]
    current_plus_amount: int

    in_progress: bool

    id_: str

    def __init__(self, _id):
        self.draw_pile = get_fresh_deck()
        self.discard_pile = []
        self.players = []
        self.id_ = _id

    def add_player(self, player: Player) -> None:
        if len(self.players) == 4:
            raise ValueError("Game full")
        self.players.append(player)
        self.turns = itertools.cycle(self.players)

    def remove_player(self, player: Player) -> None:
        if player.hand:
            random.shuffle(player.hand)
            self.draw_pile.extend(player.hand)
            player.hand = []
        self.players.remove(player)
        self.turns = itertools.cycle(self.players)

    def draw_card(self) -> Card:
        try:
            return self.draw_pile.pop()
        except IndexError:
            if self.discard_pile:
                random.shuffle(self.discard_pile)

                self.draw_pile.extend(self.discard_pile)
                self.discard_pile = []

                return self.draw_card()
            else:
                raise OutOfCardsException()

    def start(self) -> None:
        self.in_progress = True

        random.shuffle(self.draw_pile)

        for player in self.players:
            for _ in range(13):
                player.give_card(self.draw_card())

        first_card = self.draw_pile.pop()
        self.discard_pile.append(first_card)

        self.current_colour = first_card.colour
        self.current_number = first_card.number
        self.current_effects = first_card.effects
        self.current_plus_amount = 0

        self.turns = itertools.cycle(self.players)
        self.current_turn = next(self.turns)

    def update(
        self,
        player: Player,
        card_index: int,
        uno_called: bool = False,
        colour_change_to: Optional[str] = None,
    ) -> dict[str, Union[str, Player]]:

        card_played = player.hand[card_index]
        self.current_turn = next(self.turns)
        self.discard_pile.append(card_played)
        player.hand.remove(card_played)

        if not (
            card_played.colour == self.current_colour
            or (self.current_number and card_played.number == self.current_number)
            or set(card_played.effects).intersection(self.current_effects)
        ):
            return {"status": "invalid_card"}

        self.current_colour = card_played.colour
        self.current_number = card_played.number
        self.current_effects = card_played.effects

        response = {
            "current_colour": self.current_colour,
            "current_number": self.current_number,
            "current_effects": self.current_effects,
        }

        if "+2" in card_played.effects:
            self.current_plus_amount += 2
        elif "+4" in card_played.effects:
            self.current_plus_amount += 4
        else:
            for _ in range(self.current_plus_amount):
                player.give_card(self.draw_card())
            self.current_plus_amount = 0

        if "skip" in card_played.effects:
            next(self.turns)

        if "reversed" in card_played.effects:
            index = self.players.index(player)
            self.turns = itertools.cycle(
                self.players[index - 1 :: -1] + self.players[: index - 1 : -1]
            )

        if "colour_change" in card_played.effects:
            self.current_colour = colour_change_to

        if not uno_called and len(player.hand) == 1:
            for _ in range(7):
                player.give_card(self.draw_card())
            return response | {"status": "uncalled_uno"}

        if not player.hand:
            self.remove_player(player)
            self.turns = itertools.cycle(self.players)
            return response | {"status": "win", "winner": player}

        return response
