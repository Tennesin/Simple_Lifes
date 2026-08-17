"""Настройки, специфичные для овец."""

# ---------- Базовые характеристики (передаются в CreatureBase) ----------
SHEEP_HP_MAX = 60
SHEEP_HUNGER_MAX = 20
SHEEP_THIRST_MAX = 20
SHEEP_ENERGY_MAX = 80
SHEEP_VISION_RADIUS = 400
SHEEP_SPEED = 70
SHEEP_BASE_SPEED_MULTIPLIER = 1.0
SHEEP_RADIUS = 12  # для find_creature_at/find_object_at, коллизий и т.п.

# ---------- Ресурсы (появляются на теле сразу, расходуются позже при разделке/стрижке) ----------
SHEEP_MEAT_MIN, SHEEP_MEAT_MAX = 8, 14
SHEEP_WOOL_MIN, SHEEP_WOOL_MAX = 4, 8

# ---------- Внешний вид: белое овальное тело + две тонкие чёрные прямоугольные ножки ----------
SHEEP_BODY_WIDTH = 34
SHEEP_BODY_HEIGHT = 22
SHEEP_COLOR_BODY = (245, 245, 240)
SHEEP_COLOR_BODY_BORDER = (205, 205, 200)
SHEEP_COLOR_LEG = (25, 25, 25)
SHEEP_LEG_WIDTH = 4
SHEEP_LEG_HEIGHT = 10

# ---------- Текст ----------
SHEEP_KIND_NAME = "Овца"