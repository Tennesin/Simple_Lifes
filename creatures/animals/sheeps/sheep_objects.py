"""Шерсть, выпадающая с овцы после смерти или стрижки."""

import pygame

from objects import WorldObject
from .sheep_settings import WOOL_LIFETIME, WOOL_COLOR, WOOL_COLOR_BORDER, WOOL_SIZE

class Wool(WorldObject):
    """Практического применения пока нет."""

    type_name = "Шерсть"
    drop_collection_attr = "wools"

    def __init__(self, x, y, amount):
        super().__init__(x, y)
        self.amount = amount
        self.radius = WOOL_SIZE / 2
        self.lifetime = WOOL_LIFETIME

    def has_wool(self):
        return self.amount > 0

    def tick(self, dt):
        self.lifetime -= dt
        return self.lifetime <= 0

    def draw(self, screen, screen_pos):
        sx, sy = int(screen_pos[0]), int(screen_pos[1])
        half = WOOL_SIZE / 2
        rect = pygame.Rect(sx - half, sy - half, WOOL_SIZE, WOOL_SIZE)
        pygame.draw.rect(screen, WOOL_COLOR, rect)
        pygame.draw.rect(screen, WOOL_COLOR_BORDER, rect, 2)

    def to_dict(self):
        d = self._base_dict()
        d["amount"] = self.amount
        d["lifetime"] = self.lifetime
        return d

    @staticmethod
    def from_dict(data):
        wool = Wool(data["x"], data["y"], data.get("amount", 0))
        wool._apply_base(data)
        wool.lifetime = data.get("lifetime", WOOL_LIFETIME)
        return wool