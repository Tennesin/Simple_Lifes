import math
import random
from settings import *

class BiomeGrid:
    """Клеточная сетка биомов - хранение и запросы."""

    def __init__(self, world_w, world_h, cell_size=BIOME_CELL_SIZE):
        self.world_w = world_w
        self.world_h = world_h
        self.cell_size = cell_size
        self.cols = max(1, math.ceil(world_w / cell_size))
        self.rows = max(1, math.ceil(world_h / cell_size))
        self.cells = [BIOME_PLAINS] * (self.cols * self.rows)

    def _index(self, cx, cy):
        return cy * self.cols + cx

    def in_bounds(self, cx, cy):
        return 0 <= cx < self.cols and 0 <= cy < self.rows

    def world_to_cell(self, x, y):
        cx = max(0, min(int(x // self.cell_size), self.cols - 1))
        cy = max(0, min(int(y // self.cell_size), self.rows - 1))
        return cx, cy

    def get_at(self, x, y):
        cx, cy = self.world_to_cell(x, y)
        return self.cells[self._index(cx, cy)]

    def get_cell(self, cx, cy):
        if not self.in_bounds(cx, cy):
            return BIOME_PLAINS
        return self.cells[self._index(cx, cy)]

    def set_cell(self, cx, cy, biome_type):
        if self.in_bounds(cx, cy):
            self.cells[self._index(cx, cy)] = biome_type

    def set_at(self, x, y, biome_type):
        cx, cy = self.world_to_cell(x, y)
        self.set_cell(cx, cy, biome_type)

    def cells_in_radius(self, x, y, radius):
        c_min_x, c_min_y = self.world_to_cell(x - radius, y - radius)
        c_max_x, c_max_y = self.world_to_cell(x + radius, y + radius)
        origin_cx, origin_cy = self.world_to_cell(x, y)

        result = []
        for cy in range(c_min_y, c_max_y + 1):
            for cx in range(c_min_x, c_max_x + 1):
                if (cx, cy) == (origin_cx, origin_cy):
                    result.append((cx, cy))
                    continue
                center_x = cx * self.cell_size + self.cell_size / 2
                center_y = cy * self.cell_size + self.cell_size / 2
                if math.hypot(center_x - x, center_y - y) <= radius:
                    result.append((cx, cy))
        return result

    def paint_circle(self, x, y, radius, biome_type, skip_types=None):
        for cx, cy in self.cells_in_radius(x, y, radius):
            idx = self._index(cx, cy)
            if skip_types and self.cells[idx] in skip_types:
                continue
            self.cells[idx] = biome_type

    def is_water(self, x, y):
        return self.get_at(x, y) in BIOME_WATER_TYPES

    def find_nearest_of_type(self, x, y, biome_type, max_radius):
        cx0, cy0 = self.world_to_cell(x, y)
        cell_radius = int(max_radius / self.cell_size) + 1
        best = None
        best_dist = max_radius
        for dy in range(-cell_radius, cell_radius + 1):
            for dx in range(-cell_radius, cell_radius + 1):
                cx, cy = cx0 + dx, cy0 + dy
                if not self.in_bounds(cx, cy):
                    continue
                if self.cells[self._index(cx, cy)] != biome_type:
                    continue
                center_x = cx * self.cell_size + self.cell_size / 2
                center_y = cy * self.cell_size + self.cell_size / 2
                dist = math.hypot(center_x - x, center_y - y)
                if dist < best_dist:
                    best_dist = dist
                    best = (center_x, center_y)
        return best

    def find_nearest_land(self, x, y, max_radius):
        cx0, cy0 = self.world_to_cell(x, y)
        cell_radius = int(max_radius / self.cell_size) + 1
        best = None
        best_dist = max_radius
        for dy in range(-cell_radius, cell_radius + 1):
            for dx in range(-cell_radius, cell_radius + 1):
                cx, cy = cx0 + dx, cy0 + dy
                if not self.in_bounds(cx, cy):
                    continue
                if self.cells[self._index(cx, cy)] in BIOME_WATER_TYPES:
                    continue
                center_x = cx * self.cell_size + self.cell_size / 2
                center_y = cy * self.cell_size + self.cell_size / 2
                dist = math.hypot(center_x - x, center_y - y)
                if dist < best_dist:
                    best_dist = dist
                    best = (center_x, center_y)
        return best

    # ---------- Сериализация: RLE построчно (клеток может быть тысячи) ----------

    def to_dict(self):
        rows_encoded = []
        for row in range(self.rows):
            start = row * self.cols
            row_cells = self.cells[start:start + self.cols]
            rows_encoded.append(self._encode_row(row_cells))
        return {
            "world_w": self.world_w, "world_h": self.world_h,
            "cell_size": self.cell_size, "cols": self.cols, "rows": self.rows,
            "rows_rle": rows_encoded,
        }

    @staticmethod
    def _encode_row(row_cells):
        encoded = []
        if not row_cells:
            return encoded
        current = row_cells[0]
        count = 1
        for cell in row_cells[1:]:
            if cell == current:
                count += 1
            else:
                encoded.append([current, count])
                current = cell
                count = 1
        encoded.append([current, count])
        return encoded

    @staticmethod
    def from_dict(data):
        grid = BiomeGrid(data["world_w"], data["world_h"], cell_size=data.get("cell_size", BIOME_CELL_SIZE))
        grid.cols = data.get("cols", grid.cols)
        grid.rows = data.get("rows", grid.rows)
        cells = []
        for row_encoded in data.get("rows_rle", []):
            for biome_type, count in row_encoded:
                cells.extend([biome_type] * count)
        expected = grid.cols * grid.rows
        if len(cells) < expected:
            cells.extend([BIOME_PLAINS] * (expected - len(cells)))
        grid.cells = cells[:expected]
        return grid


class BiomeGenerator:
    """Детерминированная генерация по сиду. Использует СОБСТВЕННЫЙ random.Random,
    не трогая глобальный модуль random, которым пользуется вся остальная симуляция
    (существа, психика, размножение и т.д.) - иначе создание мира "съедало" бы
    случайные числа из общего потока."""

    def __init__(self, rng):
        self.rng = rng

    def generate(self, world_w, world_h):
        grid = BiomeGrid(world_w, world_h)
        self._generate_sea(grid)
        self._generate_rivers(grid)
        self._generate_deserts(grid)
        return grid

    # ---------- Море: зародыши у краёв + клеточный автомат ----------

    def _generate_sea(self, grid):
        seed_count = self.rng.randint(*SEA_GENERATION_SEED_COUNT)
        for _ in range(seed_count):
            edge = self.rng.choice(("top", "bottom", "left", "right"))
            cx, cy = self._random_edge_cell(grid, edge)
            blob_radius = self.rng.randint(3, max(4, min(grid.cols, grid.rows) // 6))
            for dy in range(-blob_radius, blob_radius + 1):
                for dx in range(-blob_radius, blob_radius + 1):
                    if dx * dx + dy * dy <= blob_radius * blob_radius:
                        grid.set_cell(cx + dx, cy + dy, BIOME_SEA)

        self._cellular_automaton_step(grid, BIOME_SEA, SEA_AUTOMATON_ITERATIONS,
                                      birth_threshold=4, death_threshold=3)

    def _cellular_automaton_step(self, grid, biome_type, iterations, birth_threshold, death_threshold):
        for _ in range(iterations):
            new_cells = grid.cells[:]
            for cy in range(grid.rows):
                for cx in range(grid.cols):
                    neighbors = self._count_neighbors_of_type(grid, cx, cy, biome_type)
                    idx = grid._index(cx, cy)
                    if grid.cells[idx] == biome_type:
                        if neighbors < death_threshold:
                            new_cells[idx] = BIOME_PLAINS
                    else:
                        if neighbors >= birth_threshold:
                            new_cells[idx] = biome_type
            grid.cells = new_cells

    @staticmethod
    def _count_neighbors_of_type(grid, cx, cy, biome_type):
        count = 0
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = cx + dx, cy + dy
                if not grid.in_bounds(nx, ny):
                    continue
                if grid.cells[grid._index(nx, ny)] == biome_type:
                    count += 1
        return count

    def _random_edge_cell(self, grid, edge):
        if edge == "top":
            return (self.rng.randint(0, grid.cols - 1), 0)
        if edge == "bottom":
            return (self.rng.randint(0, grid.cols - 1), grid.rows - 1)
        if edge == "left":
            return (0, self.rng.randint(0, grid.rows - 1))
        return (grid.cols - 1, self.rng.randint(0, grid.rows - 1))

    # ---------- Реки: блуждающая ломаная от края к противоположному краю ----------

    def _generate_rivers(self, grid):
        river_count = self.rng.randint(*RIVER_GENERATION_COUNT)
        for _ in range(river_count):
            self._generate_single_river(grid)

    def _generate_single_river(self, grid):
        start_edge = self.rng.choice(("top", "bottom", "left", "right"))
        opposite = {"top": "bottom", "bottom": "top", "left": "right", "right": "left"}[start_edge]

        cx, cy = self._random_edge_cell(grid, start_edge)
        end = self._random_edge_cell(grid, opposite)

        path = [(cx, cy)]
        max_steps = grid.cols + grid.rows
        for _ in range(max_steps):
            if (cx, cy) == end:
                break
            dx = 1 if end[0] > cx else (-1 if end[0] < cx else 0)
            dy = 1 if end[1] > cy else (-1 if end[1] < cy else 0)

            options = []
            if dx != 0:
                options.append((dx, 0))
            if dy != 0:
                options.append((0, dy))
            options.append((self.rng.choice((-1, 0, 1)), self.rng.choice((-1, 0, 1))))

            step = self.rng.choice(options)
            cx = max(0, min(grid.cols - 1, cx + step[0]))
            cy = max(0, min(grid.rows - 1, cy + step[1]))
            path.append((cx, cy))

        river_width = self.rng.uniform(0.6, 1.3) * grid.cell_size
        for pcx, pcy in path:
            wx = pcx * grid.cell_size + grid.cell_size / 2
            wy = pcy * grid.cell_size + grid.cell_size / 2
            grid.paint_circle(wx, wy, river_width, BIOME_RIVER, skip_types=(BIOME_SEA,))

    # ---------- Пустыня: зародыши на суше + компактный автомат, не трогающий воду ----------

    def _generate_deserts(self, grid):
        seed_count = self.rng.randint(*DESERT_GENERATION_SEED_COUNT)
        attempts = 0
        placed = 0
        while placed < seed_count and attempts < seed_count * 20:
            attempts += 1
            cx = self.rng.randint(0, grid.cols - 1)
            cy = self.rng.randint(0, grid.rows - 1)
            if grid.cells[grid._index(cx, cy)] != BIOME_PLAINS:
                continue
            blob_radius = self.rng.randint(2, max(3, min(grid.cols, grid.rows) // 8))
            for dy in range(-blob_radius, blob_radius + 1):
                for dx in range(-blob_radius, blob_radius + 1):
                    if dx * dx + dy * dy <= blob_radius * blob_radius:
                        ncx, ncy = cx + dx, cy + dy
                        if grid.in_bounds(ncx, ncy) and grid.cells[grid._index(ncx, ncy)] == BIOME_PLAINS:
                            grid.set_cell(ncx, ncy, BIOME_DESERT)
            placed += 1

        self._desert_automaton_step(grid, DESERT_AUTOMATON_ITERATIONS)

    def _desert_automaton_step(self, grid, iterations):
        """Как обычный автомат, но никогда не отжимает территорию у реки/моря."""
        for _ in range(iterations):
            new_cells = grid.cells[:]
            for cy in range(grid.rows):
                for cx in range(grid.cols):
                    idx = grid._index(cx, cy)
                    if grid.cells[idx] in BIOME_WATER_TYPES:
                        continue
                    neighbors = self._count_neighbors_of_type(grid, cx, cy, BIOME_DESERT)
                    if grid.cells[idx] == BIOME_DESERT:
                        if neighbors < 2:
                            new_cells[idx] = BIOME_PLAINS
                    else:
                        if neighbors >= 5:
                            new_cells[idx] = BIOME_DESERT
            grid.cells = new_cells

# =========================================================================
# Домен: игровая обёртка над сеткой биомов - создание/загрузка/покраска.
# =========================================================================

class BiomeManager:
    def __init__(self, game):
        self.game = game
        self.grid = None  # BiomeGrid | None

    def generate(self, world_w, world_h, seed):
        rng = random.Random(seed)
        self.grid = BiomeGenerator(rng).generate(world_w, world_h)

    def ensure_grid(self, world_w, world_h):
        if self.grid is None:
            self.grid = BiomeGrid(world_w, world_h)

    def to_dict(self):
        return self.grid.to_dict() if self.grid is not None else None

    def load_from_dict(self, data, world_w, world_h):
        if data:
            self.grid = BiomeGrid.from_dict(data)
        else:
            self.grid = BiomeGrid(world_w, world_h)

    def paint(self, wx, wy, biome_type, radius):
        if self.grid is not None:
            self.grid.paint_circle(wx, wy, radius, biome_type)