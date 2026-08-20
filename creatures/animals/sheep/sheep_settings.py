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
# ---------- Шерсть (после смерти или стрижки) ----------
SHEEP_WOOL_MIN, SHEEP_WOOL_MAX = 4, 8
WOOL_LIFETIME = 360.0
WOOL_SIZE = 18
WOOL_COLOR = (250, 250, 245)
WOOL_COLOR_BORDER = (210, 210, 205)

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
SHEEP_INFO_WOOL = "Шерсть: {count}"

# ---------- ИИ: бродяжничество, выпас, водопой, паника при волках ----------
SHEEP_HUNGER_DRAIN_INTERVAL = 40.0
SHEEP_THIRST_DRAIN_INTERVAL = 18.0
SHEEP_ENERGY_DRAIN_INTERVAL_FLEE = 5.0
SHEEP_ENERGY_REGEN_INTERVAL = 9.0
SHEEP_STARVE_HP_DRAIN = 1.2
SHEEP_DEHYDRATE_HP_DRAIN = 2.5

SHEEP_WANDER_DISTANCE = (50, 140)
SHEEP_WANDER_TIMER = (3.0, 6.0)
SHEEP_GRAZE_DISTANCE = 18
SHEEP_GRAZE_RATE = 1.0
SHEEP_DRINK_DISTANCE = 32
SHEEP_DRINK_RATE = 2.2
SHEEP_HUNGER_SEEK_RATIO = 0.6
SHEEP_THIRST_SEEK_RATIO = 0.6
SHEEP_HUNGER_SATISFY_RATIO = 0.85
SHEEP_THIRST_SATISFY_RATIO = 0.85
SHEEP_FLEE_RUN_DISTANCE = 180
SHEEP_FLEE_SPEED_MULTIPLIER = 1.7