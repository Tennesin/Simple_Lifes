"""Естественный рост природы: новые деревья/кусты/камни/трава и фрукты у кустов."""

import math
import random

import settings
from . import object_settings as cfg
from .object_types import object_types, create_object
from .spatial import SpatialIndex

class NaturalGrowth:

    def __init__(self, game, placement):
        self.game = game
        self.placement = placement

    def try_grow(self, obj_type):
        """Одна попытка вырастить объект типа obj_type (tree/bush/stone/grass) в случайной точке.
        Подходит ли биом, проверяет само размещение (единый источник правды - object_types)."""
        game = self.game
        if game.biome_manager.grid is None:
            return
        attr, _cls = object_types()[obj_type]
        collection = getattr(game.world, attr)
        if len(collection) >= cfg.GROWTH_LIMITS[obj_type]:
            return

        index = SpatialIndex(game)      # строится лениво, если первые точки отсеются по биому - не строится вовсе
        margin = cfg.GROWTH_WORLD_MARGIN
        for _ in range(settings.NATURAL_SPAWN_ATTEMPTS):
            wx = random.uniform(margin, settings.WORLD_WIDTH - margin)
            wy = random.uniform(margin, settings.WORLD_HEIGHT - margin)
            if self.placement.object_position_valid(wx, wy, obj_type=obj_type, index=index):
                collection.append(create_object(obj_type, wx, wy))
                return

    def try_spawn_fruit_near_bush(self, bush):
        game = self.game
        nearby = sum(
            1 for fruit in game.world.fruits
            if fruit.active and math.hypot(fruit.x - bush.x, fruit.y - bush.y) < settings.BUSH_SPAWN_RADIUS
        )
        if nearby >= settings.BUSH_MAX_NEARBY_FRUITS:
            return

        index = SpatialIndex(game)
        for _ in range(settings.BUSH_SPAWN_ATTEMPTS):
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(bush.radius + cfg.BUSH_FRUIT_MIN_GAP, settings.BUSH_SPAWN_RADIUS)
            wx = bush.x + math.cos(angle) * dist
            wy = bush.y + math.sin(angle) * dist
            if self.placement.object_position_valid(wx, wy, obj_type="fruit", index=index):
                game.world.fruits.append(create_object("fruit", wx, wy))
                return