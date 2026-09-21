"""Константы, общие для нескольких панелей UI (не относятся к одной конкретной)."""

import info
import settings
from game.race_registry import PlayerToolSpec
from player import Player

BIOME_PREVIEW_COLOR = {
    "biome_plains": settings.COLOR_LIGHT,
    "biome_desert": settings.BIOME_BASE_COLOR[settings.BIOME_DESERT],
    "biome_river": settings.BIOME_BASE_COLOR[settings.BIOME_RIVER],
    "biome_sea": settings.BIOME_BASE_COLOR[settings.BIOME_SEA],
}

BIOME_LABELS = {
    settings.BIOME_PLAINS: info.INFO_BTN_BIOME_PLAINS,
    settings.BIOME_DESERT: info.INFO_BTN_BIOME_DESERT,
    settings.BIOME_RIVER: info.INFO_BTN_BIOME_RIVER,
    settings.BIOME_SEA: info.INFO_BTN_BIOME_SEA,
}

_CORE_OBJECT_MENU_ITEMS = (
    ("spike", info.INFO_BTN_SPIKE),
)

# ---------- Базовые инструменты игрока (core), к ним добавляются расовые ----------
_CORE_PLAYER_TOOLS = (
    PlayerToolSpec(Player.TOOL_PET, info.INFO_BTN_PET, info.INFO_TOOL_PET_HINT),
    PlayerToolSpec(Player.TOOL_HIT, info.INFO_BTN_HIT, info.INFO_TOOL_HIT_HINT),
    PlayerToolSpec(Player.TOOL_GRAB, info.INFO_BTN_GRAB, info.INFO_TOOL_GRAB_HINT),
    PlayerToolSpec(Player.TOOL_FAVORITE, info.INFO_BTN_FAVORITE, info.INFO_TOOL_FAVORITE_HINT),
)

_CORE_TOOL_HINTS = {
    "wall": info.INFO_TOOL_WALL_HINT,
    "fence": info.INFO_TOOL_FENCE_HINT,
    "biome_plains": info.INFO_TOOL_BIOME_HINT,
    "biome_desert": info.INFO_TOOL_BIOME_HINT,
    "biome_river": info.INFO_TOOL_BIOME_HINT,
    "biome_sea": info.INFO_TOOL_BIOME_HINT,
}