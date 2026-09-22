"""Константы, общие для нескольких панелей UI (не относятся к одной конкретной)."""

import info
import settings
from game.race_registry import PlayerToolSpec
from player import Player

BIOME_PREVIEW_COLOR = {
    Player.TOOL_BIOME_PLAINS: settings.COLOR_LIGHT,
    Player.TOOL_BIOME_DESERT: settings.BIOME_BASE_COLOR[settings.BIOME_DESERT],
    Player.TOOL_BIOME_RIVER: settings.BIOME_BASE_COLOR[settings.BIOME_RIVER],
    Player.TOOL_BIOME_SEA: settings.BIOME_BASE_COLOR[settings.BIOME_SEA],
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
    Player.TOOL_WALL: info.INFO_TOOL_WALL_HINT,
    Player.TOOL_FENCE: info.INFO_TOOL_FENCE_HINT,
    Player.TOOL_BIOME_PLAINS: info.INFO_TOOL_BIOME_HINT,
    Player.TOOL_BIOME_DESERT: info.INFO_TOOL_BIOME_HINT,
    Player.TOOL_BIOME_RIVER: info.INFO_TOOL_BIOME_HINT,
    Player.TOOL_BIOME_SEA: info.INFO_TOOL_BIOME_HINT,
}