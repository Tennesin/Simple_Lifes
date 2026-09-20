import math
import random
import settings

BIOME_RATIO_MIN = 0.05
BIOME_RATIO_MAX = 0.85
BIOME_RATIO_STEP = 0.05

DEFAULT_BIOME_RATIOS = {
    settings.BIOME_PLAINS: 0.55,
    settings.BIOME_DESERT: 0.15,
    settings.BIOME_RIVER: 0.15,
    settings.BIOME_SEA: 0.15,
}

def adjust_biome_ratio(ratios, changed_biome, new_value):
    """Меняет долю одного биома, пропорционально забирая разницу у остальных
    (не опуская их ниже BIOME_RATIO_MIN)."""
    ratios = dict(ratios)
    new_value = round(max(BIOME_RATIO_MIN, min(BIOME_RATIO_MAX, new_value)), 2)
    ratios[changed_biome] = new_value

    others = [b for b in ratios if b != changed_biome]

    for _ in range(20):
        overflow = round(sum(ratios.values()) - 1.0, 4)
        if overflow <= 1e-6:
            break
        reducible = [b for b in others if ratios[b] > BIOME_RATIO_MIN + 1e-6]
        if not reducible:
            ratios[changed_biome] = round(max(BIOME_RATIO_MIN, ratios[changed_biome] - overflow), 2)
            break
        reducible_total = sum(ratios[b] for b in reducible)
        for b in reducible:
            share = ratios[b] / reducible_total
            reduction = min(overflow * share, ratios[b] - BIOME_RATIO_MIN)
            ratios[b] = round(ratios[b] - reduction, 4)

    for b in ratios:
        ratios[b] = round(max(BIOME_RATIO_MIN, min(BIOME_RATIO_MAX, ratios[b])), 2)
    return ratios


def finalize_biome_ratios(ratios):
    """Вызывается прямо перед созданием мира: если сумма долей меньше 1.0,
    недостающее случайно раздаётся по биомам (с учётом BIOME_RATIO_MAX)."""
    ratios = dict(ratios)
    total = sum(ratios.values())
    remaining_steps = int(round((1.0 - total) / BIOME_RATIO_STEP))
    if remaining_steps <= 0:
        return ratios

    biomes = list(ratios.keys())
    guard = 0
    while remaining_steps > 0 and guard < 1000:
        guard += 1
        candidates = [b for b in biomes if ratios[b] + BIOME_RATIO_STEP <= BIOME_RATIO_MAX + 1e-6]
        if not candidates:
            break
        b = random.choice(candidates)
        ratios[b] = round(ratios[b] + BIOME_RATIO_STEP, 2)
        remaining_steps -= 1

    return ratios

class BiomeGrid:
    """Клеточная сетка биомов - хранение и запросы."""

    def __init__(self, world_w, world_h, cell_size=settings.BIOME_CELL_SIZE):
        self.world_w = world_w
        self.world_h = world_h
        self.cell_size = cell_size
        self.cols = max(1, math.ceil(world_w / cell_size))
        self.rows = max(1, math.ceil(world_h / cell_size))
        self.cells = [settings.BIOME_PLAINS] * (self.cols * self.rows)

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
            return settings.BIOME_PLAINS
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
        return self.get_at(x, y) in settings.BIOME_WATER_TYPES

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
                if self.cells[self._index(cx, cy)] in settings.BIOME_WATER_TYPES:
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
        grid = BiomeGrid(data["world_w"], data["world_h"], cell_size=data["cell_size"])
        cells = []
        for row_encoded in data["rows_rle"]:
            for biome_type, count in row_encoded:
                cells.extend([biome_type] * count)
        grid.cells = cells
        return grid

class BiomeGenerator:
    """Детерминированная генерация по сиду."""

    def __init__(self, rng):
        self.rng = rng

    def generate(self, world_w, world_h, ratios=None):
        grid = BiomeGrid(world_w, world_h)
        ratios = ratios or DEFAULT_BIOME_RATIOS
        total_cells = grid.cols * grid.rows

        sea_target = int(total_cells * ratios.get(settings.BIOME_SEA, 0.0))
        river_target = int(total_cells * ratios.get(settings.BIOME_RIVER, 0.0))
        desert_target = int(total_cells * ratios.get(settings.BIOME_DESERT, 0.0))

        self._generate_sea(grid, sea_target)
        self._generate_rivers(grid, river_target)
        self._generate_deserts(grid, desert_target)
        return grid

    # ---------- Море: зародыши у краёв + клеточный автомат ----------

    def _generate_sea(self, grid, target_cells):
        if target_cells <= 0:
            return
        seed_count = max(1, min(6, target_cells // max(1, (grid.cols + grid.rows))))
        blob_radius = max(2, int(math.sqrt(target_cells / seed_count / math.pi)))
        for _ in range(seed_count):
            edge = self.rng.choice(("top", "bottom", "left", "right"))
            cx, cy = self._random_edge_cell(grid, edge)
            for dy in range(-blob_radius, blob_radius + 1):
                for dx in range(-blob_radius, blob_radius + 1):
                    if dx * dx + dy * dy <= blob_radius * blob_radius:
                        grid.set_cell(cx + dx, cy + dy, settings.BIOME_SEA)

        self._cellular_automaton_step(grid, settings.BIOME_SEA, settings.SEA_AUTOMATON_ITERATIONS,
                                      birth_threshold=4, death_threshold=3)
        self._adjust_biome_to_target(grid, settings.BIOME_SEA, target_cells)

    def _cellular_automaton_step(self, grid, biome_type, iterations, birth_threshold, death_threshold):
        for _ in range(iterations):
            new_cells = grid.cells[:]
            for cy in range(grid.rows):
                for cx in range(grid.cols):
                    neighbors = self._count_neighbors_of_type(grid, cx, cy, biome_type)
                    idx = grid._index(cx, cy)
                    if grid.cells[idx] == biome_type:
                        if neighbors < death_threshold:
                            new_cells[idx] = settings.BIOME_PLAINS
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

    def _generate_rivers(self, grid, target_cells):
        if target_cells <= 0:
            return
        approx_river_area = max(1, (grid.cols + grid.rows) // 2)
        river_count = max(1, min(4, target_cells // approx_river_area + 1))
        for _ in range(river_count):
            self._generate_single_river(grid)
        self._adjust_biome_to_target(grid, settings.BIOME_RIVER, target_cells)

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
            grid.paint_circle(wx, wy, river_width, settings.BIOME_RIVER, skip_types=(settings.BIOME_SEA,))

    # ---------- Пустыня: зародыши на суше + компактный автомат, не трогающий воду ----------

    def _generate_deserts(self, grid, target_cells):
        if target_cells <= 0:
            return
        attempts = 0
        placed_cells = 0
        attempts_limit = max(60, (target_cells // 10) * 20 + 60)
        while placed_cells < target_cells and attempts < attempts_limit:
            attempts += 1
            cx = self.rng.randint(0, grid.cols - 1)
            cy = self.rng.randint(0, grid.rows - 1)
            if grid.cells[grid._index(cx, cy)] != settings.BIOME_PLAINS:
                continue
            blob_radius = self.rng.randint(2, max(3, min(grid.cols, grid.rows) // 8))
            for dy in range(-blob_radius, blob_radius + 1):
                for dx in range(-blob_radius, blob_radius + 1):
                    if dx * dx + dy * dy <= blob_radius * blob_radius:
                        ncx, ncy = cx + dx, cy + dy
                        if grid.in_bounds(ncx, ncy) and grid.cells[grid._index(ncx, ncy)] == settings.BIOME_PLAINS:
                            grid.set_cell(ncx, ncy, settings.BIOME_DESERT)
                            placed_cells += 1

        self._desert_automaton_step(grid, settings.DESERT_AUTOMATON_ITERATIONS)
        self._adjust_biome_to_target(grid, settings.BIOME_DESERT, target_cells)

    def _desert_automaton_step(self, grid, iterations):
        """Как обычный автомат, но никогда не отжимает территорию у реки/моря."""
        for _ in range(iterations):
            new_cells = grid.cells[:]
            for cy in range(grid.rows):
                for cx in range(grid.cols):
                    idx = grid._index(cx, cy)
                    if grid.cells[idx] in settings.BIOME_WATER_TYPES:
                        continue
                    neighbors = self._count_neighbors_of_type(grid, cx, cy, settings.BIOME_DESERT)
                    if grid.cells[idx] == settings.BIOME_DESERT:
                        if neighbors < 2:
                            new_cells[idx] = settings.BIOME_PLAINS
                    else:
                        if neighbors >= 5:
                            new_cells[idx] = settings.BIOME_DESERT
            grid.cells = new_cells

    # ---------- Точная подгонка площади биома под целевое число клеток ----------

    def _cell_neighbors(self, grid, cx, cy):
        result = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = cx + dx, cy + dy
            if grid.in_bounds(nx, ny):
                result.append(grid._index(nx, ny))
        return result

    def _adjust_biome_to_target(self, grid, biome_type, target_cells):
        current = [i for i, c in enumerate(grid.cells) if c == biome_type]
        count = len(current)

        if count < target_cells:
            self._grow_biome(grid, biome_type, current, target_cells - count)
        elif count > target_cells:
            self._shrink_biome(grid, biome_type, current, count - target_cells)

    def _grow_biome(self, grid, biome_type, current_cells, cells_needed):
        # Растёт ТОЛЬКО по клеткам-равнинам - соседние биомы (море/река/пустыня)
        # никогда не перезаписываются
        frontier = list(current_cells)
        added = 0
        guard = 0
        max_guard = max(200, cells_needed * 8)

        while added < cells_needed and guard < max_guard:
            guard += 1
            if not frontier:
                frontier = [i for i, c in enumerate(grid.cells) if c == biome_type]
                if not frontier:
                    free_cells = [i for i, c in enumerate(grid.cells) if c == settings.BIOME_PLAINS]
                    if not free_cells:
                        break
                    seed_idx = self.rng.choice(free_cells)
                    grid.cells[seed_idx] = biome_type
                    frontier = [seed_idx]
                    added += 1
                    continue

            idx = frontier[self.rng.randrange(len(frontier))]
            cx, cy = idx % grid.cols, idx // grid.cols
            neighbors = self._cell_neighbors(grid, cx, cy)
            self.rng.shuffle(neighbors)

            grew = False
            for n_idx in neighbors:
                if grid.cells[n_idx] == settings.BIOME_PLAINS:
                    grid.cells[n_idx] = biome_type
                    frontier.append(n_idx)
                    added += 1
                    grew = True
                    break
            if not grew:
                frontier.remove(idx)

    def _shrink_biome(self, grid, biome_type, current_cells, cells_to_remove):
        border = [i for i in current_cells
                  if any(grid.cells[n] != biome_type
                        for n in self._cell_neighbors(grid, i % grid.cols, i // grid.cols))]
        if not border:
            border = list(current_cells)

        removed = 0
        guard = 0
        max_guard = max(200, cells_to_remove * 8)

        while removed < cells_to_remove and guard < max_guard and border:
            guard += 1
            idx = border.pop(self.rng.randrange(len(border)))
            if grid.cells[idx] != biome_type:
                continue
            grid.cells[idx] = settings.BIOME_PLAINS
            removed += 1

            cx, cy = idx % grid.cols, idx // grid.cols
            for n_idx in self._cell_neighbors(grid, cx, cy):
                if grid.cells[n_idx] == biome_type:
                    border.append(n_idx)

# =========================================================================
# Домен: игровая обёртка над сеткой биомов - создание/загрузка/покраска.
# =========================================================================

class BiomeManager:
    def __init__(self, game):
        self.game = game
        self.grid = None  # BiomeGrid | None

    def generate(self, world_w, world_h, seed, ratios=None):
        rng = random.Random(seed)
        self.grid = BiomeGenerator(rng).generate(world_w, world_h, ratios=ratios)

    def to_dict(self):
        return self.grid.to_dict() if self.grid is not None else None

    def load_from_dict(self, data):
        self.grid = BiomeGrid.from_dict(data)

    def paint(self, wx, wy, biome_type, radius):
        if self.grid is not None:
            self.grid.paint_circle(wx, wy, radius, biome_type)