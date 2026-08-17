"""Настройки, специфичные для коров."""

# ---------- Базовые характеристики ----------
COW_HP_MAX = 90
COW_HUNGER_MAX = 28
COW_THIRST_MAX = 28
COW_ENERGY_MAX = 100
COW_VISION_RADIUS = 450
COW_SPEED = 60
COW_BASE_SPEED_MULTIPLIER = 1.0
COW_RADIUS = 16

# ---------- Ресурсы ----------
COW_MEAT_MIN, COW_MEAT_MAX = 20, 32
COW_MILK_MAX_CHARGES = 4
# ---------- Кожа (выпадает после смерти) ----------
COW_LEATHER_MIN, COW_LEATHER_MAX = 6, 10
LEATHER_LIFETIME = 45.0
LEATHER_SIZE = 20
LEATHER_COLOR = (120, 80, 45)
LEATHER_COLOR_BORDER = (80, 50, 25)

# ---------- Внешний вид: тёмно-серый прямоугольник + белые точки + 2 тонкие ножки того же цвета ----------
COW_BODY_WIDTH = 44
COW_BODY_HEIGHT = 26
COW_COLOR_BODY = (70, 70, 78)
COW_COLOR_BODY_BORDER = (40, 40, 46)
COW_COLOR_SPOTS = (235, 235, 235)
COW_SPOT_COUNT_RANGE = (3, 5)
COW_SPOT_RADIUS = 3
COW_COLOR_LEG = COW_COLOR_BODY
COW_LEG_WIDTH = 4
COW_LEG_HEIGHT = 12

# ---------- Текст ----------
COW_KIND_NAME = "Корова"