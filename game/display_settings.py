"""Единая точка сборки настроек отображения (панель 'Настройки' -> 'Отображение')."""

import info
import settings
from game.animal_registry import all_animal_display_checkboxes
from game.race_registry import all_display_checkboxes

# ---------- Core-чекбоксы вкладки "Техническое" ----------
CORE_TECHNICAL_CHECKBOXES = (
    ("autosave_enabled", info.INFO_SETTINGS_AUTOSAVE),
)

def all_technical_checkbox_specs():
    """(ключ, подпись) для чекбоксов вкладки 'Техническое'."""
    return CORE_TECHNICAL_CHECKBOXES

# ---------- Core-числовые настройки (слайдеры) вкладки "Техническое" ----------
CORE_TECHNICAL_SLIDERS = (
    ("simulation_area_units", info.INFO_SETTINGS_SIMULATION_AREA,
     settings.SIMULATION_AREA_MIN_UNITS, settings.SIMULATION_AREA_MAX_UNITS, 1),
)

def all_technical_slider_specs():
    """(ключ, подпись, min, max, step) для числовых настроек вкладки 'Техническое'."""
    return CORE_TECHNICAL_SLIDERS

# ---------- Core-чекбоксы вкладки "Отображение" ----------
CORE_DISPLAY_CHECKBOXES = (
    ("show_creature_names", info.INFO_SETTINGS_SHOW_NAMES),
    ("show_status_rings", info.INFO_SETTINGS_SHOW_STATUS_RINGS),
    ("minimap_show_fruits", info.INFO_SETTINGS_MINIMAP_FRUITS),
    ("minimap_show_bushes", info.INFO_SETTINGS_MINIMAP_BUSHES),
    ("minimap_show_spikes", info.INFO_SETTINGS_MINIMAP_SPIKES),
    ("minimap_show_water", info.INFO_SETTINGS_MINIMAP_WATER),
    ("minimap_show_trees", info.INFO_SETTINGS_MINIMAP_TREES),
    ("minimap_show_stones", info.INFO_SETTINGS_MINIMAP_STONES),
    ("minimap_show_roads", info.INFO_SETTINGS_MINIMAP_ROADS),
)

def all_display_checkbox_specs():
    """(ключ, подпись) для ВСЕХ чекбоксов панели настроек: core + расы + животные.
    Единственное место, где эти три источника сводятся вместе."""
    return CORE_DISPLAY_CHECKBOXES + all_display_checkboxes() + all_animal_display_checkboxes()

def full_default_display_settings() -> dict:
    """Стартовые значения display_settings: core-дефолты (их фактические True/False
    заданы в settings.py) + все чекбоксы рас и животных включены по умолчанию."""
    merged = dict(settings.DEFAULT_DISPLAY_SETTINGS)
    for key, _label in all_display_checkboxes():
        merged.setdefault(key, True)
    for key, _label in all_animal_display_checkboxes():
        merged.setdefault(key, True)
    return merged