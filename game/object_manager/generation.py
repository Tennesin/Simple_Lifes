"""Стартовое наполнение только что созданного мира: ресурсы и животные."""

import random
from contextlib import contextmanager

import settings
from game.animal_registry import all_animals
from . import object_settings as cfg
from .object_types import (
    object_types, create_object, allowed_biomes, ANIMAL_BIOMES, LANDSCAPE_AFFECTING_TYPES,
)
from .spatial import SpatialIndex, EligibleCells

@contextmanager
def seeded_global_random(seed):
    """На время генерации делает глобальный random детерминированным (конструкторы деревьев,
    камней, воды, животных бросают именно его), потом возвращает прежнее состояние."""
    state = random.getstate()
    random.seed(seed)
    try:
        yield
    finally:
        random.setstate(state)

class _PointSource:
    """Выдаёт точки-кандидаты: по очереди из подходящих клеток биома (перемешанных заново
    после каждого круга), а если таких клеток нет - равномерно по всему миру."""

    def __init__(self, rng, cells, cell_size):
        self.rng = rng
        self.cells = cells
        self.cell_size = cell_size
        self._cursor = 0

    def next(self):
        rng = self.rng
        if self.cells:
            if self._cursor >= len(self.cells):
                self._cursor = 0
                rng.shuffle(self.cells)
            cx, cy = self.cells[self._cursor]
            self._cursor += 1
            size = self.cell_size
            margin = min(cfg.SCATTER_CELL_MARGIN, size / 4)
            wx = cx * size + rng.uniform(margin, size - margin)
            wy = cy * size + rng.uniform(margin, size - margin)
            return wx, wy
        margin = cfg.SCATTER_WORLD_MARGIN
        return (rng.uniform(margin, settings.WORLD_WIDTH - margin),
                rng.uniform(margin, settings.WORLD_HEIGHT - margin))

class WorldGenerator:

    def __init__(self, game, placement, manager):
        self.game = game
        self.placement = placement
        self.manager = manager      # фасад ObjectManager: его получают spawn_fn животных

    # =====================================================================
    # Публичный вход
    # =====================================================================

    def generate_resources(self, seed):
        salted = seed ^ cfg.RESOURCE_SEED_SALT
        rng = random.Random(salted)
        ratio = self._area_ratio()
        cells = EligibleCells(self.game.biome_manager.grid)
        index = SpatialIndex(self.game)
        with seeded_global_random(salted):
            for obj_type, base_count in cfg.INITIAL_RESOURCES:
                self._scatter_objects(rng, int(base_count * ratio), obj_type, cells, index)

    def generate_animals(self, seed):
        salted = seed ^ cfg.ANIMAL_SEED_SALT
        rng = random.Random(salted)
        ratio = self._area_ratio()
        cells = EligibleCells(self.game.biome_manager.grid)
        index = SpatialIndex(self.game)
        with seeded_global_random(salted):
            for descriptor in all_animals():
                count = int(descriptor.initial_count * ratio)
                if count > 0:
                    self._scatter_animals(rng, count, descriptor, cells, index)

    # =====================================================================
    # Расстановка
    # =====================================================================

    @staticmethod
    def _area_ratio():
        area = settings.WORLD_WIDTH * settings.WORLD_HEIGHT
        return max(cfg.MIN_AREA_RATIO, area / settings.INITIAL_RESOURCE_BASE_WORLD_AREA)

    def _scatter_objects(self, rng, count, obj_type, cells, index):
        if count <= 0:
            return
        game = self.game
        attr, _cls = object_types()[obj_type]
        points = _PointSource(rng, cells.shuffled(allowed_biomes(obj_type), rng), cells.cell_size)

        def is_valid(x, y):
            return self.placement.object_position_valid(x, y, obj_type=obj_type, index=index)

        def spawn(x, y):
            obj = create_object(obj_type, x, y)
            getattr(game.world, attr).append(obj)
            index.add(attr, obj)

        placed = self._scatter(count, points, is_valid, spawn)
        if placed and obj_type in LANDSCAPE_AFFECTING_TYPES:
            game.world.landscape_version += 1

    def _scatter_animals(self, rng, count, descriptor, cells, index):
        game = self.game
        attr = descriptor.world_collection
        points = _PointSource(rng, cells.shuffled(ANIMAL_BIOMES, rng), cells.cell_size)

        def is_valid(x, y):
            return self.placement.creature_position_valid(x, y, index=index)

        def spawn(x, y):
            collection = getattr(game.world, attr)
            before = len(collection)
            descriptor.spawn_fn(self.manager, x, y, descriptor.placement_mode)
            collection = getattr(game.world, attr)
            if len(collection) > before:
                index.add(attr, collection[-1])

        self._scatter(count, points, is_valid, spawn)

    @staticmethod
    def _scatter(count, points, is_valid, spawn):
        """Общий цикл: берёт точки, пока не набрано count, либо не кончились попытки, либо
        слишком много неудач подряд. Возвращает, сколько реально создано."""
        max_attempts = max(cfg.SCATTER_MIN_ATTEMPTS, count * cfg.SCATTER_ATTEMPTS_PER_ITEM)
        max_failures = max(cfg.SCATTER_MIN_FAILURES, count * cfg.SCATTER_FAILURES_PER_ITEM)
        placed = attempts = failures = 0
        while placed < count and attempts < max_attempts and failures < max_failures:
            attempts += 1
            x, y = points.next()
            if not is_valid(x, y):
                failures += 1
                continue
            failures = 0
            spawn(x, y)
            placed += 1
        return placed