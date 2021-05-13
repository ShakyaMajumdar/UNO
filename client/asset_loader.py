from typing import NamedTuple

import pygame

background_gradient = pygame.image.load("client/assets/gradient.png")

pygame.font.init()
girassol_font = pygame.font.Font("client/assets/fonts/Girassol-Regular.ttf", 30)


class Colours(NamedTuple):
    YELLOW = 0xFFDA22
    RED = 0xCC241D
    BLUE = 0x0075C4
    GREEN = 0x00EB4E
