"""Шкура, выпадающая с волка после смерти."""

import pygame

from objects import WorldObject
from .wolf_settings import HIDE_LIFETIME, HIDE_COLOR, HIDE_COLOR_BORDER, HIDE_SIZE

class Hide(WorldObject):

    type_name = "Шкура"
    drop_collection_attr = "hides"

    def __init__(self, x, y, amount):
        super().__init__(x, y)
        self.amount = amount
        self.radius = HIDE_SIZE / 2
        self.lifetime = HIDE_LIFETIME

    def has_hide(self):
        return self.amount > 0

    def tick(self, dt):
        self.lifetime -= dt
        return self.lifetime <= 0

    def draw(self, screen, screen_pos):
        sx, sy = int(screen_pos[0]), int(screen_pos[1])
        half = HIDE_SIZE / 2
        points = [(sx, sy - half), (sx + half, sy), (sx, sy + half), (sx - half, sy)]
        pygame.draw.polygon(screen, HIDE_COLOR, points)
        pygame.draw.polygon(screen, HIDE_COLOR_BORDER, points, 2)

    def to_dict(self):
        d = self._base_dict()
        d["amount"] = self.amount
        d["lifetime"] = self.lifetime
        return d

    @staticmethod
    def from_dict(data):
        hide = Hide(data["x"], data["y"], data.get("amount", 0))
        hide._apply_base(data)
        hide.lifetime = data.get("lifetime", HIDE_LIFETIME)
        return hide