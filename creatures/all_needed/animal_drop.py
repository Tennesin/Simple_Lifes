"""Единый ресурс, выпадающий с животного (шкура/шерсть/кожа и т.п.) -
механика идентична, различается только оформление."""

import pygame
from objects import WorldObject

class AnimalDropResource(WorldObject):
    """Наследник задаёт атрибуты класса: type_name, drop_collection_attr,
    default_lifetime, color, color_border, size, shape ('diamond'|'square')."""

    type_name = None
    drop_collection_attr = None
    default_lifetime = 30.0
    color = (200, 200, 200)
    color_border = (150, 150, 150)
    size = 18
    shape = "diamond"

    def __init__(self, x, y, amount):
        super().__init__(x, y)
        self.amount = amount
        self.radius = self.size / 2
        self.lifetime = self.default_lifetime

    def has_resource(self):
        return self.amount > 0

    def tick(self, dt):
        self.lifetime -= dt
        return self.lifetime <= 0

    def draw(self, screen, screen_pos):
        sx, sy = int(screen_pos[0]), int(screen_pos[1])
        half = self.size / 2
        if self.shape == "square":
            rect = pygame.Rect(sx - half, sy - half, self.size, self.size)
            pygame.draw.rect(screen, self.color, rect)
            pygame.draw.rect(screen, self.color_border, rect, 2)
        else:
            points = [(sx, sy - half), (sx + half, sy), (sx, sy + half), (sx - half, sy)]
            pygame.draw.polygon(screen, self.color, points)
            pygame.draw.polygon(screen, self.color_border, points, 2)

    def to_dict(self):
        d = self._base_dict()
        d["amount"] = self.amount
        d["lifetime"] = self.lifetime
        return d

    @classmethod
    def from_dict(cls, data):
        obj = cls(data["x"], data["y"], data.get("amount", 0))
        obj._apply_base(data)
        obj.lifetime = data.get("lifetime", cls.default_lifetime)
        return obj