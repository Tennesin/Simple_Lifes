"""Источники кандидатов для проверок размещения.

LinearSource - без индекса: кандидаты это вся коллекция мира (для разовых проверок).
SpatialIndex - временная пространственная сетка на время генерации/роста: строится лениво,
               по одной сетке на коллекцию, при первом обращении к ней."""

from creatures.all_needed.navigation import SpatialGrid
from . import object_settings as cfg

class LinearSource:

    def __init__(self, game):
        self.game = game

    def candidates(self, attr, x, y, radius):
        return getattr(self.game.world, attr)

    def add(self, attr, obj):
        """Сообщить источнику о новом объекте, который УЖЕ добавлен в коллекцию мира."""

class SpatialIndex(LinearSource):

    def __init__(self, game):
        super().__init__(game)
        self._grids = {}

    def candidates(self, attr, x, y, radius):
        grid = self._grids.get(attr)
        if grid is None:
            grid = SpatialGrid(cell_size=cfg.INDEX_CELL_SIZE)
            grid.build(getattr(self.game.world, attr))
            self._grids[attr] = grid
        return grid.query_nearby(x, y, radius)

    def add(self, attr, obj):
        # ---------- Если сетка ещё не построена, объект попадёт в неё при построении
        # (он уже лежит в коллекции). Добавлять его сейчас = получить дубль ----------
        grid = self._grids.get(attr)
        if grid is not None:
            grid.add(obj)


class EligibleCells:
    """Клетки биомной сетки, подходящие под набор биомов (кэш на время одной генерации)."""

    def __init__(self, biome_grid):
        self.grid = biome_grid
        self._cache = {}

    @property
    def cell_size(self):
        return self.grid.cell_size if self.grid is not None else 0

    def shuffled(self, allowed_biomes, rng):
        """Свежий перемешанный список (cx, cy). Пустой, если сетки биомов нет."""
        if self.grid is None:
            return []
        key = frozenset(allowed_biomes)
        cells = self._cache.get(key)
        if cells is None:
            grid = self.grid
            cells = [
                (cx, cy)
                for cy in range(grid.rows)
                for cx in range(grid.cols)
                if grid.cells[cy * grid.cols + cx] in key
            ]
            self._cache[key] = cells
        result = list(cells)
        rng.shuffle(result)
        return result