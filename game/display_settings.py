"""Единая точка сборки настроек отображения (панель 'Настройки' -> 'Отображение')."""

from settings import DEFAULT_DISPLAY_SETTINGS as _CORE_DISPLAY_SETTINGS
from info import (
    INFO_SETTINGS_SHOW_NAMES, INFO_SETTINGS_SHOW_STATUS_RINGS,
    INFO_SETTINGS_MINIMAP_FRUITS, INFO_SETTINGS_MINIMAP_BUSHES,
    INFO_SETTINGS_MINIMAP_SPIKES, INFO_SETTINGS_MINIMAP_WATER,
    INFO_SETTINGS_MINIMAP_TREES, INFO_SETTINGS_MINIMAP_STONES,
    INFO_SETTINGS_MINIMAP_ROADS, INFO_SETTINGS_AUTOSAVE,
)
from game.race_registry import all_display_checkboxes
from game.animal_registry import all_animal_display_checkboxes

# ---------- Core-чекбоксы вкладки "Техническое" ----------
CORE_TECHNICAL_CHECKBOXES = (
    ("autosave_enabled", INFO_SETTINGS_AUTOSAVE),
)

def all_technical_checkbox_specs():
    """(ключ, подпись) для чекбоксов вкладки 'Техническое'."""
    return CORE_TECHNICAL_CHECKBOXES

# ---------- Core-чекбоксы вкладки "Отображение" ----------
CORE_DISPLAY_CHECKBOXES = (
    ("show_creature_names", INFO_SETTINGS_SHOW_NAMES),
    ("show_status_rings", INFO_SETTINGS_SHOW_STATUS_RINGS),
    ("minimap_show_fruits", INFO_SETTINGS_MINIMAP_FRUITS),
    ("minimap_show_bushes", INFO_SETTINGS_MINIMAP_BUSHES),
    ("minimap_show_spikes", INFO_SETTINGS_MINIMAP_SPIKES),
    ("minimap_show_water", INFO_SETTINGS_MINIMAP_WATER),
    ("minimap_show_trees", INFO_SETTINGS_MINIMAP_TREES),
    ("minimap_show_stones", INFO_SETTINGS_MINIMAP_STONES),
    ("minimap_show_roads", INFO_SETTINGS_MINIMAP_ROADS),
)

def all_display_checkbox_specs():
    """(ключ, подпись) для ВСЕХ чекбоксов панели настроек: core + расы + животные.
    Единственное место, где эти три источника сводятся вместе."""
    return CORE_DISPLAY_CHECKBOXES + all_display_checkboxes() + all_animal_display_checkboxes()

def full_default_display_settings() -> dict:
    """Стартовые значения display_settings: core-дефолты (их фактические True/False
    заданы в settings.py) + все чекбоксы рас и животных включены по умолчанию."""
    merged = dict(_CORE_DISPLAY_SETTINGS)
    for key, _label in all_display_checkboxes():
        merged.setdefault(key, True)
    for key, _label in all_animal_display_checkboxes():
        merged.setdefault(key, True)
    return merged