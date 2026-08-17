"""Ресурсы, выпадающие с коровы после процедуры или смерти."""

import pygame

from objects import WorldObject
from .cow_settings import LEATHER_LIFETIME, LEATHER_COLOR, LEATHER_COLOR_BORDER, LEATHER_SIZE


class Leather(WorldObject):
    """Кожа коровы."""

    type_name = "Кожа"

    def __init__(self, x, y, amount):
        super().__init__(x, y)
        self.amount = amount
        self.radius = LEATHER_SIZE / 2
        self.lifetime = LEATHER_LIFETIME

    def has_leather(self):
        return self.amount > 0

    def tick(self, dt):
        self.lifetime -= dt
        return self.lifetime <= 0

    def draw(self, screen, screen_pos):
        sx, sy = int(screen_pos[0]), int(screen_pos[1])
        half = LEATHER_SIZE / 2
        points = [(sx, sy - half), (sx + half, sy), (sx, sy + half), (sx - half, sy)]
        pygame.draw.polygon(screen, LEATHER_COLOR, points)
        pygame.draw.polygon(screen, LEATHER_COLOR_BORDER, points, 2)

    def to_dict(self):
        d = self._base_dict()
        d["amount"] = self.amount
        d["lifetime"] = self.lifetime
        return d

    @staticmethod
    def from_dict(data):
        leather = Leather(data["x"], data["y"], data.get("amount", 0))
        leather._apply_base(data)
        leather.lifetime = data.get("lifetime", LEATHER_LIFETIME)
        return leather