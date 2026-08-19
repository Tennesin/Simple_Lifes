import os

WINDOW_WIDTH, WINDOW_HEIGHT = 1000, 750
WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT = WINDOW_WIDTH, WINDOW_HEIGHT
WORLD_WIDTH, WORLD_HEIGHT = 2500, 2500
FPS = 60
UI_HEIGHT = 40
PLACEMENT_CHECK_MIN_MOVE = 6
DEFAULT_SCROLL_SPEED = 25
DEFAULT_VISION_RADIUS = 900
SPIKE_NAV_BLOCK_RADIUS = 35

# ---------- Адаптивное окно под размер мира ----------
WINDOW_MIN_WIDTH = 1000
WINDOW_MIN_HEIGHT = 520
WINDOW_MAX_WIDTH = 1200
WINDOW_MAX_HEIGHT = 750
WINDOW_SCREEN_MARGIN = 80     # запас от разрешения экрана пользователя (панель задач и т.п.)

# ---------- Сворачивание правой панели (существо / кладбище) ----------
COLLAPSE_HANDLE_WIDTH = 16
COLLAPSE_HANDLE_HEIGHT = 56
COLLAPSE_HANDLE_COLOR = (80, 80, 80)
COLLAPSE_HANDLE_BORDER = (40, 40, 40)
COLLAPSE_HANDLE_ARROW_COLOR = (200, 45, 45)
COLLAPSE_HANDLE_ARROW_HOVER_COLOR = (235, 100, 100)

# ---------- Адаптивная мини-карта ----------
MINIMAP_MAX_WIDTH = 260
MINIMAP_MAX_HEIGHT = 260
MINIMAP_MIN_WIDTH = 120
MINIMAP_MIN_HEIGHT = 90

# ---------- Шрифт ----------
FONT_NAME = "georgia"
FONT_SIZE_ONSCREEN = 18   # текст прямо на чёрном поле без рамки (пауза, "Создайте или откройте мир")
FONT_SIZE_NAME = 14       # имя существа над головой (на игровом поле, их может быть много)
FONT_SIZE_PANEL = 15     # весь обычный интерфейсный текст: панели, кнопки, меню, миникарта, списки
FONT_SIZE_TITLE = 20      # заголовки экранов создания/загрузки мира
FONT_SIZE_LABEL = 18      # подписи полей ввода и пункты списка миров
FONT_SIZE_SMALL = 14      # мелкий текст: инфо о мире, ошибки, подтверждение удаления
FONT_SIZE_BUTTON = 14     # весь текст ВНУТРИ кнопок (верхняя панель, меню, действия существа)
BUTTON_HEIGHT = 28        # стандартная высота кнопки — используется и layout'ом, и Button.draw()

# ---------- Размер мира по умолчанию (используется, пока мир не создан/загружен) ----------
WORLD_DEFAULT_SIZE = (WORLD_WIDTH, WORLD_HEIGHT)
WORLD_MIN_SIZE = 750
WORLD_MAX_SIZE = 10000

# ---------- Экраны создания/загрузки мира (без tkinter) ----------
WORLD_SCREEN_MARGIN = 30
WORLD_SCREEN_BG = (12, 12, 12)
WORLD_SCREEN_PANEL_BG = (35, 35, 35)
WORLD_SCREEN_PANEL_BORDER = (90, 90, 90)
WORLD_SCREEN_TEXT = (225, 225, 225)
WORLD_SCREEN_HINT_COLOR = (140, 140, 140)
WORLD_SCREEN_ERROR_COLOR = (230, 90, 90)
WORLD_SCREEN_INPUT_BG = (22, 22, 22)
WORLD_SCREEN_INPUT_BG_FOCUS = (45, 45, 60)
WORLD_SCREEN_INPUT_BORDER = (70, 70, 70)
WORLD_SCREEN_INPUT_BORDER_FOCUS = (110, 140, 200)

WORLD_LIST_ITEM_HEIGHT = 32
WORLD_LIST_ITEM_COLOR = (45, 45, 45)
WORLD_LIST_ITEM_HOVER_COLOR = (60, 60, 60)
WORLD_LIST_ITEM_SELECTED_COLOR = (70, 95, 135)

# ---------- Куст ----------
BUSH_SPAWN_INTERVAL = 8.0
BUSH_SPAWN_RADIUS = 55
BUSH_SPAWN_ATTEMPTS = 8
BUSH_MAX_NEARBY_FRUITS = 4
BUSH_COLOR = (46, 125, 50)
BUSH_COLOR_BORDER = (24, 80, 30)

# ---------- Дерево ----------
TREE_WOOD_MIN = 15
TREE_WOOD_MAX = 55
TREE_RADIUS = 16
TREE_COLOR_TRUNK = (101, 67, 33)
TREE_COLOR_TRUNK_BORDER = (60, 40, 20)
TREE_COLOR_LEAVES = (34, 120, 40)
TREE_COLOR_LEAVES_BORDER = (20, 80, 25)

# ---------- Камень ----------
STONE_MIN_AMOUNT = 10
STONE_MAX_AMOUNT = 45
STONE_RADIUS = 14
STONE_COLOR = (140, 140, 140)
STONE_COLOR_BORDER = (90, 90, 90)
STONE_COLOR_LIGHT = (200, 200, 200)

# ---------- Трава ----------
GRASS_FOOD_MIN = 15
GRASS_FOOD_MAX = 155
GRASS_BASE_WIDTH = 20       # ширина при GRASS_FOOD_MIN
GRASS_MAX_WIDTH = 70        # ширина при GRASS_FOOD_MAX
GRASS_HEIGHT = 22
GRASS_COLOR = (60, 150, 70)
GRASS_COLOR_DARK = (40, 120, 55)
GRASS_BLADE_MIN_COUNT = 5
GRASS_BLADE_MAX_COUNT = 14
# ---------- Генерация травы (начальная + естественная) ----------
INITIAL_GRASS_COUNT = 90
NATURAL_GRASS_SPAWN_INTERVAL = (20.0, 35.0)
NATURAL_GRASS_SPAWN_CHANCE = 0.35
GRASS_MAX_TOTAL = 300

# ---------- Мясо ----------
MEAT_LIFETIME = 20.0
MEAT_COLOR = (200, 60, 60)
MEAT_COLOR_FAT = (240, 235, 220)
MEAT_COLOR_BORDER = (120, 30, 30)

# ---------- Натуральный рост деревьев и кустов ----------
NATURAL_TREE_SPAWN_INTERVAL = (25.0, 45.0)   # как часто мир "пытается" вырастить дерево
NATURAL_TREE_SPAWN_CHANCE = 0.35             # шанс успеха при попытке
NATURAL_BUSH_SPAWN_INTERVAL = (30.0, 50.0)
NATURAL_BUSH_SPAWN_CHANCE = 0.3
NATURAL_SPAWN_ATTEMPTS = 10                  # сколько случайных точек перебираем за одну попытку
TREE_MAX_TOTAL = 250                         # предохранитель от бесконечного разрастания леса
BUSH_MAX_TOTAL = 250
# ---------- Начальное заполнение только что созданного мира ----------
INITIAL_TREE_COUNT = 70
INITIAL_BUSH_COUNT = 55
INITIAL_STONE_COUNT = 50
INITIAL_SPIKE_COUNT = 20
INITIAL_RESOURCE_BASE_WORLD_AREA = WORLD_WIDTH * WORLD_HEIGHT

# ---------- Появление камней ---------
NATURAL_STONE_SPAWN_INTERVAL = (35.0, 60.0)
NATURAL_STONE_SPAWN_CHANCE = 0.25
STONE_MAX_TOTAL = 200

# ---------- Цвет фруктов ----------
FRUIT_COLOR = (255, 190, 40)
FRUIT_COLOR_BORDER = (230, 120, 15)

# ---------- Водоём (лужа/озеро) ----------
WATER_PUDDLE_CHARGE_MIN = 10
WATER_PUDDLE_CHARGE_MAX = 30
WATER_PUDDLE_CHARGE_VALUE = 10.0   # сколько единиц жажды даёт 1 заряд водоёма

# Миры
BASE_WORLDS_DIR = os.path.join(os.path.expanduser("~"), "Documents", "Simple_Lifes")
WORLD_EXTENSION = ".slw"           # Simple Lifes World — расширение папки мира
WORLD_META_FILENAME = "world.json" # файл-метка, по которому распознаётся мир
DEFAULT_WORLD_NAME = "New_World"

# Цвета
COLOR_LIGHT = (120, 200, 100)
COLOR_DARK = (80, 160, 70)
BUTTON_COLOR = (70, 130, 180)
BUTTON_HOVER = (100, 160, 210)
BUTTON_DISABLED = (100, 100, 100)
TEXT_COLOR = (255, 255, 255)
PANEL_COLOR = (50, 50, 50)
MENU_BG = (70, 70, 70)
MENU_HOVER = (100, 100, 100)
PLACEMENT_HIGHLIGHT_VALID = (0, 255, 0, 100)
PLACEMENT_HIGHLIGHT_INVALID = (255, 0, 0, 100)
CLOSE_BUTTON_COLOR = (200, 50, 50)
CLOSE_BUTTON_HOVER = (255, 80, 80)

# Панель информации о существе
INFO_PANEL_WIDTH = 335
INFO_PANEL_COLOR = (60, 60, 60)
INFO_PANEL_BORDER = (30, 30, 30)
NAME_FIELD_COLOR = (90, 90, 90)
NAME_FIELD_EDIT_COLOR = (230, 230, 230)
VISION_CIRCLE_COLOR = (255, 255, 255)
VISION_SHADOW_ALPHA = 90

INTUITIVE_DECAY_TIME = 900.0

# ---------- Перекрёстки дорог ----------
CROSSING_MERGE_RADIUS = 15        # новая точка пересечения ближе этого к уже известному перекрёстку - считаем тем же перекрёстком
LANDSCAPE_SNAP_TOLERANCE = 15    # px - в радиусе скольки пикселей примагничиваем новую точку дороги/стены/забора к уже существующей
ROAD_ENDPOINT_LINK_MARGIN = 25   # px - запас за пределами радиуса объекта, в котором конец дороги ещё считается "привязанным" к ориентиру
ROAD_CROSSING_RADIUS = 7
ROAD_CROSSING_COLOR = (250, 220, 40)
ROAD_CROSSING_COLOR_BORDER = (120, 90, 10)

# ---------- Сохранение ----------
MANUAL_SAVE_AUTOSAVE_SUPPRESS_TIME = 8.0  # после ручного сохранения автосохранение при выходе не выполняется столько секунд

# ---------- Мини-карта ----------
MINIMAP_MARGIN = 10
MINIMAP_BG_COLOR = (20, 20, 20)
MINIMAP_BORDER_COLOR = (200, 200, 200)
MINIMAP_VIEWPORT_COLOR = (60, 140, 255)

# ---------- Ландшафт: стены и заборы ----------
WALL_COLOR = (70, 70, 75)
WALL_THICKNESS = 7
WALL_VISION_BLOCK_MARGIN = 60  # запас: стена чуть за радиусом видимости всё ещё может перекрывать обзор
WALL_WELD_TOLERANCE = 14
FENCE_COLOR = (196, 154, 108)
FENCE_THICKNESS = 3
FENCE_TICK_COLOR = (60, 45, 30)
FENCE_TICK_INTERVAL = 16      # шаг между чёрточками "/" на заборе
FENCE_TICK_LENGTH = 8
LANDSCAPE_MIN_POINT_DIST = 20

# ---------- Глобальный pathfinding (A* по клеточной карте) ----------
NAV_GRID_CELL_SIZE = 30
NAV_OBSTACLE_INFLATE = 14        # было 16 — ближе к реальному физическому зазору существа,
                                  # чтобы A* не запечатывал узкие, но физически проходимые проёмы
NAV_WALL_SOFT_MARGIN = 14        # доп. "мягкая" зона за пределами NAV_OBSTACLE_INFLATE:
                                  # не блокирует клетку, но делает её дороже для A*
NAV_WALL_CLEARANCE_PENALTY = 1.6 # во сколько раз дороже шаг в "мягкой" зоне у стены
NAV_OBSTACLE_INFLATE_FALLBACK = 6   # запасной, минимальный отступ
NAV_PATH_RECALC_INTERVAL = (1.2, 1.8)
NAV_GOAL_CHANGE_THRESHOLD = 45
NAV_WAYPOINT_REACHED_DISTANCE = 18
NAV_MAX_ASTAR_NODES = 6000

# ---------- Биомы ----------
BIOME_CELL_SIZE = 75
BIOME_PLAINS = "plains"
BIOME_DESERT = "desert"
BIOME_RIVER = "river"
BIOME_SEA = "sea"
BIOME_LIST = [BIOME_PLAINS, BIOME_DESERT, BIOME_RIVER, BIOME_SEA]
BIOME_WATER_TYPES = (BIOME_RIVER, BIOME_SEA)

# ---------- Числовые коды биомов ----------
BIOME_CODE = {BIOME_PLAINS: 1, BIOME_DESERT: 2, BIOME_RIVER: 3, BIOME_SEA: 4}

BIOME_BASE_COLOR = {
    BIOME_DESERT: (214, 178, 92),
    BIOME_RIVER: (70, 150, 230),
    BIOME_SEA: (20, 60, 150),
}

# ---------- Цвета биомов на миникарте (упрощённые, без текстур) ----------
MINIMAP_BIOME_COLOR = {
    BIOME_PLAINS: (55, 110, 50),
    BIOME_DESERT: (214, 178, 92),
    BIOME_RIVER: (70, 150, 230),
    BIOME_SEA: (20, 60, 150),
}

BIOME_TEXTURE_VARIANTS = 8
BIOME_TEXTURE_DETAIL_COUNT = (3, 6)
BIOME_TEXTURE_SHADE_RANGE = (-14, 14)

# ---------- Генерация ----------
SEA_GENERATION_SEED_COUNT = (1, 2)
DESERT_GENERATION_SEED_COUNT = (2, 4)
RIVER_GENERATION_COUNT = (1, 3)
SEA_AUTOMATON_ITERATIONS = 5
DESERT_AUTOMATON_ITERATIONS = 3

# ---------- Кисть рисования биомов (регулировка радиуса - следующий шаг) ----------
BIOME_BRUSH_DEFAULT_RADIUS = 60
BIOME_BRUSH_MIN_RADIUS = 20
BIOME_BRUSH_MAX_RADIUS = 300
BIOME_BRUSH_SENSITIVITY = 1.5

# ---------- Настройки отображения (панель "Настройки" -> "Отображение") ----------
DEFAULT_DISPLAY_SETTINGS = {
    "show_creature_names": False,
    "show_status_rings": True,
    "minimap_show_fruits": True,
    "minimap_show_bushes": True,
    "minimap_show_spikes": True,
    "minimap_show_water": True,
    "minimap_show_trees": True,
    "minimap_show_stones": True,
    "minimap_show_roads": True,
}

# ---------- Экран "Настройки" (модальная панель поверх игры с затемнением фона) ----------
SETTINGS_OVERLAY_ALPHA = 150
SETTINGS_PANEL_BG = (35, 35, 35)
SETTINGS_PANEL_BORDER = (90, 90, 90)
SETTINGS_SIDEBAR_BG = (24, 24, 24)
SETTINGS_TAB_COLOR = (55, 55, 55)
SETTINGS_TAB_HOVER = (75, 75, 75)
SETTINGS_TAB_SELECTED = (70, 95, 135)