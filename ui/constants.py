"""Константы, общие для нескольких панелей UI (не относятся к одной конкретной)."""

from settings import (
    COLOR_LIGHT, BIOME_BASE_COLOR,
    BIOME_PLAINS, BIOME_DESERT, BIOME_RIVER, BIOME_SEA,
)
from info import (
    INFO_BTN_BIOME_PLAINS, INFO_BTN_BIOME_DESERT, INFO_BTN_BIOME_RIVER, INFO_BTN_BIOME_SEA,
    INFO_BTN_SPIKE,
    INFO_BTN_PET, INFO_BTN_HIT, INFO_BTN_GRAB, INFO_BTN_FAVORITE,
    INFO_TOOL_PET_HINT, INFO_TOOL_HIT_HINT, INFO_TOOL_GRAB_HINT, INFO_TOOL_FAVORITE_HINT,
    INFO_TOOL_WALL_HINT, INFO_TOOL_FENCE_HINT, INFO_TOOL_BIOME_HINT,
)
from player import Player
from game.race_registry import PlayerToolSpec

BIOME_PREVIEW_COLOR = {
    "biome_plains": COLOR_LIGHT,
    "biome_desert": BIOME_BASE_COLOR[BIOME_DESERT],
    "biome_river": BIOME_BASE_COLOR[BIOME_RIVER],
    "biome_sea": BIOME_BASE_COLOR[BIOME_SEA],
}

BIOME_LABELS = {
    BIOME_PLAINS: INFO_BTN_BIOME_PLAINS,
    BIOME_DESERT: INFO_BTN_BIOME_DESERT,
    BIOME_RIVER: INFO_BTN_BIOME_RIVER,
    BIOME_SEA: INFO_BTN_BIOME_SEA,
}

_CORE_OBJECT_MENU_ITEMS = (
    ("spike", INFO_BTN_SPIKE),
)

# ---------- Базовые инструменты игрока (core), к ним добавляются расовые ----------
_CORE_PLAYER_TOOLS = (
    PlayerToolSpec(Player.TOOL_PET, INFO_BTN_PET, INFO_TOOL_PET_HINT),
    PlayerToolSpec(Player.TOOL_HIT, INFO_BTN_HIT, INFO_TOOL_HIT_HINT),
    PlayerToolSpec(Player.TOOL_GRAB, INFO_BTN_GRAB, INFO_TOOL_GRAB_HINT),
    PlayerToolSpec(Player.TOOL_FAVORITE, INFO_BTN_FAVORITE, INFO_TOOL_FAVORITE_HINT),
)

_CORE_TOOL_HINTS = {
    "wall": INFO_TOOL_WALL_HINT,
    "fence": INFO_TOOL_FENCE_HINT,
    "biome_plains": INFO_TOOL_BIOME_HINT,
    "biome_desert": INFO_TOOL_BIOME_HINT,
    "biome_river": INFO_TOOL_BIOME_HINT,
    "biome_sea": INFO_TOOL_BIOME_HINT,
}