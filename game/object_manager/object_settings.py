"""Числовые константы пакета game/object_manager/ (README §5).
Общие константы мира лежат в settings.py - здесь только то, что относится к менеджеру объектов."""

import settings

# ---------- Поиск объекта под курсором ----------
CREATURE_PICK_RADIUS = 14          # px - на каком расстоянии от курсора существо считается "выбранным"
CIRCLE_PICK_MARGIN = 6             # px - запас при попадании по кругу объекта
POLYLINE_PICK_TOLERANCE = 8        # px - при попадании по линии (дорога/стена/забор)

# ---------- Проверки размещения ----------
WORLD_EDGE_MARGIN_CREATURE = 20    # px - ближе к краю мира существо/животное ставить нельзя
WORLD_EDGE_MARGIN_OBJECT = 10      # px - то же для объектов
CREATURE_CLEARANCE = 30            # px - минимальная дистанция между существами/животными
CREATURE_SPAWN_OBJECT_GAP = 20     # px - зазор между новым существом и водой/кустом/постройкой
FIXED_CLEARANCE_MIN = 20           # px - минимальная дистанция объекта до фруктов/шипов/существ
FOOTPRINT_EXTRA_GAP = 15           # px - запас к "занимаемому месту" уже стоящего объекта
QUERY_MARGIN = 120                 # px - запас радиуса запроса к пространственной сетке
INDEX_CELL_SIZE = 150              # px - размер клетки временной сетки на время генерации/роста

# ---------- Стартовое наполнение мира ----------
RESOURCE_SEED_SALT = 0x5BD1E995    # чтобы ресурсы и животные не повторяли последовательности друг друга
ANIMAL_SEED_SALT = 0x27D4EB2F
MIN_AREA_RATIO = 0.1               # нижняя граница коэффициента площади (крошечные миры)
SCATTER_MIN_ATTEMPTS = 50
SCATTER_ATTEMPTS_PER_ITEM = 25
SCATTER_MIN_FAILURES = 300         # подряд неудачных точек, после которых расстановка сдаётся
SCATTER_FAILURES_PER_ITEM = 5
SCATTER_CELL_MARGIN = 4            # px - отступ точки от края клетки биома
SCATTER_WORLD_MARGIN = 20          # px - отступ от края мира, если подходящих клеток нет

# (тип объекта, сколько на базовую площадь мира) - порядок расстановки важен
INITIAL_RESOURCES = (
    ("tree", settings.INITIAL_TREE_COUNT),
    ("bush", settings.INITIAL_BUSH_COUNT),
    ("stone", settings.INITIAL_STONE_COUNT),
    ("spike", settings.INITIAL_SPIKE_COUNT),
    ("grass", settings.INITIAL_GRASS_COUNT),
)

# ---------- Естественный рост ----------
GROWTH_WORLD_MARGIN = 20           # px
GROWTH_LIMITS = {
    "tree": settings.TREE_MAX_TOTAL,
    "bush": settings.BUSH_MAX_TOTAL,
    "stone": settings.STONE_MAX_TOTAL,
    "grass": settings.GRASS_MAX_TOTAL,
}
BUSH_FRUIT_MIN_GAP = 10            # px - фрукт появляется не ближе (радиус куста + это) от центра куста

# ---------- Дороги ----------
SELF_SNAP_EXCLUDE_RECENT_POINTS = 3    # последние точки рисуемой дороги не примагничиваются к ней самой
CROSSING_SEGMENT_EDGE = 0.02           # пересечение у самого конца сегмента перекрёстком не считается
CROSSING_INSERT_TOLERANCE = 6          # px - ближе к уже имеющейся точке новую точку перекрёстка не вставляем