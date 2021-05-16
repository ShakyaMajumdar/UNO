import enum
from typing import Optional

import pygame


class Colours(enum.Enum):
    yellow = (255, 218, 34)
    red = (204, 36, 29)
    blue = (0, 113, 189)
    green = (0, 235, 78)


def load_assets() -> tuple[
    pygame.Surface,
    pygame.font.Font,
    dict[tuple[Optional[str], Optional[int], tuple[str]], pygame.Surface],
]:
    background_gradient = pygame.image.load("client/assets/gradient.png")
    girassol_font = pygame.font.Font("client/assets/fonts/Girassol-Regular.ttf", 30)
    cards_sprites = {}
    for colour in Colours:
        for number in range(10):
            cards_sprites[colour.name, number, ()] = pygame.image.load(
                f"client/assets/cards/{colour.name}_{number}.png"
            )
        for effect in ("plus_two", "reverse", "skip"):
            cards_sprites[colour.name, None, (effect,)] = pygame.image.load(
                f"client/assets/cards/{colour.name}_{effect}.png"
            )

    cards_sprites[None, None, ("colour_change",)] = pygame.image.load(
        "client/assets/cards/wild.png"
    )
    cards_sprites[None, None, ("colour_change", "+4")] = pygame.image.load(
        "client/assets/cards/plus_four.png"
    )

    return background_gradient, girassol_font, cards_sprites
