import importlib
import pkgutil
from dataclasses import dataclass, field
from typing import Callable, Optional, Tuple, Type
from info import INFO_BTN_DRAW_ROAD, INFO_TOOL_ROAD_HINT

import creatures.races as races_package
from objects import Road
from settings import DEFAULT_DISPLAY_SETTINGS as _CORE_DISPLAY_SETTINGS

@dataclass(frozen=True)
class RenderLayer:
    """Один слой отрисовки мира, специфичный для расы."""
    key: str
    insert_after: str
    draw_fn: Callable


@dataclass(frozen=True)
class MinimapLayer:
    """Один слой отрисовки миникарты, специфичный для расы.
    draw_fn(screen, game, to_minimap, scale, display_settings) -> None"""
    key: str
    insert_after: str
    draw_fn: Callable

@dataclass(frozen=True)
class PlaceableObjectSpec:
    """Описание одного объекта, размещаемого через игровое меню 'Объект'."""
    obj_type: str
    attr: str
    cls: Type
    label: str
    placement_clearance: Optional[float] = None
    secondary_panel_attr: Optional[str] = None
    blocks_creature_spawn: bool = False
    mutual_clearance_additive: bool = False
    manually_placeable: bool = True

@dataclass(frozen=True)
class RoadNetworkSpec:
    """Описание одной дорожной сети — общая инфраструктура и для всех видов."""
    obj_type: str
    road_collection: str
    crossing_collection: str
    verify_fn: Optional[Callable] = None
    road_cls: Optional[Type] = None
    preview_color: Tuple[int, int, int] = (255, 255, 255)
    menu_label: Optional[str] = None
    menu_hint: Optional[str] = None

CORE_ROAD_NETWORK = RoadNetworkSpec(
    obj_type="road", road_collection="roads", crossing_collection="road_crossings",
    road_cls=Road, preview_color=(255, 255, 255),
    menu_label=INFO_BTN_DRAW_ROAD, menu_hint=INFO_TOOL_ROAD_HINT)

@dataclass(frozen=True)
class PlayerToolSpec:
    """Один дополнительный инструмент игрока (кнопка в меню 'Игрок' + подсказка)."""
    tool_value: str
    label: str
    hint: str

@dataclass(frozen=True)
class SecondaryPanelSpec:
    """Дополнительная боковая панель выбора (по образцу panel_cls для существ,
    но для не-существ - кладбище, и т.п.)."""
    attr_name: str
    panel_cls: Type
    is_selected_fn: Optional[Callable] = None
    popup_draw_fn: Optional[Callable] = None

@dataclass(frozen=True)
class LandmarkSpec:
    """Доп. тип ориентира расы (сверх core: костёр/вода/куст), к которому может
    быть привязан конец нарисованной дороги (endpoint linking)."""
    type_name: str
    attr: str

@dataclass(frozen=True)
class ExtraObjectCollectionSpec:
    """Коллекция объектов расы, которую движок должен уметь искать под курсором
    (find_object_at) и удалять (delete_object)."""
    attr: str
    hit_margin: float = 6.0
    on_delete: Optional[Callable] = None  # (game, obj) -> None

@dataclass(frozen=True)
class BiomeCascadeSpec:
    """Как одна коллекция объектов расы реагирует на смену биома в зоне покраски."""
    attr: str
    clear_on_flood: bool = False
    clear_on_desert: bool = False
    on_removed: Optional[Callable] = None  # (game, obj) -> None

# ---------- Core-сеть дорог — не расовая, но по форме идентична расовым ----------
    CORE_ROAD_NETWORK = RoadNetworkSpec(
    obj_type="road", road_collection="roads", crossing_collection="road_crossings",
    road_cls=Road, preview_color=(255, 255, 255))

def all_road_networks() -> Tuple[RoadNetworkSpec, ...]:
    result = [CORE_ROAD_NETWORK]
    for descriptor in all_races():
        result.extend(descriptor.road_networks)
    return tuple(result)

@dataclass(frozen=True)
class RaceDescriptor:
    """Описание одной расы существ - всё, что нужно движку, чтобы работать с ней."""

    race_name: str
    creature_cls: Type
    tick_processor_cls: Type

    loader_fn: Callable
    panel_cls: Type

    spawn_manager_cls: Optional[Type] = None
    spawn_fn: Optional[Callable] = None
    name_pools: Optional[dict] = None
    creature_placement_modes: Tuple[Tuple[str, str], ...] = field(default_factory=tuple)
    world_collections: Tuple[str, ...] = field(default_factory=tuple)
    persistence_registry: Tuple[Tuple[str, str, Type], ...] = field(default_factory=tuple)
    placeable_objects: Tuple[PlaceableObjectSpec, ...] = field(default_factory=tuple)
    render_layers: Tuple[RenderLayer, ...] = field(default_factory=tuple)
    road_networks: Tuple[RoadNetworkSpec, ...] = field(default_factory=tuple)

    # ---------- Новое: тик "неживых" объектов расы (не существ) ----------
    world_tick_fn: Optional[Callable] = None  # (game, dt) -> None
    # ---------- Дополнительное сохранение/загрузка мира, специфичное для расы ----------
    extra_world_save_fn: Optional[Callable] = None  # (game) -> None
    extra_world_load_fn: Optional[Callable] = None  # (game) -> None

    # ---------- Новое: генерализация ui.py ----------
    player_tools: Tuple[PlayerToolSpec, ...] = field(default_factory=tuple)
    display_checkboxes: Tuple[Tuple[str, str], ...] = field(default_factory=tuple)
    minimap_layers: Tuple[MinimapLayer, ...] = field(default_factory=tuple)
    object_panel_extra_fn: Optional[Callable] = None  # (obj, all_creatures) -> list[(text, color)]
    secondary_panel_specs: Tuple[SecondaryPanelSpec, ...] = field(default_factory=tuple)
    landmark_specs: Tuple[LandmarkSpec, ...] = field(default_factory=tuple)
    extra_object_collections: Tuple[ExtraObjectCollectionSpec, ...] = field(default_factory=tuple)
    biome_cascade_specs: Tuple[BiomeCascadeSpec, ...] = field(default_factory=tuple)

    # ---------- Обобщённые крючки мыши. ----------
    mouse_down_hooks: Tuple[Callable, ...] = field(default_factory=tuple)
    mouse_up_hooks: Tuple[Callable, ...] = field(default_factory=tuple)
    mouse_motion_hooks: Tuple[Callable, ...] = field(default_factory=tuple)
    mouse_wheel_hooks: Tuple[Callable, ...] = field(default_factory=tuple)

_RACES_CACHE: Optional[dict] = None

def _discover_races() -> dict:
    registry = {}
    for module_info in pkgutil.iter_modules(races_package.__path__):
        race_pkg_name = f"{races_package.__name__}.{module_info.name}"
        try:
            race_module = importlib.import_module(f"{race_pkg_name}.race")
        except ModuleNotFoundError:
            continue
        descriptor = getattr(race_module, "RACE_DESCRIPTOR", None)
        if descriptor is None:
            continue
        registry[descriptor.race_name] = descriptor
    return registry


def _races() -> dict:
    global _RACES_CACHE
    if _RACES_CACHE is None:
        _RACES_CACHE = _discover_races()
    return _RACES_CACHE


def get_race(race_name: str) -> RaceDescriptor:
    races = _races()
    try:
        return races[race_name]
    except KeyError:
        raise KeyError(
            f"Раса '{race_name}' не зарегистрирована (нет creatures/races/*/race.py "
            f"с RACE_DESCRIPTOR). Известные расы: {sorted(races.keys())}"
        )

def all_race_names() -> Tuple[str, ...]:
    return tuple(_races().keys())

def all_races() -> Tuple[RaceDescriptor, ...]:
    return tuple(_races().values())

def creature_placement_lookup():
    lookup = {}
    for descriptor in _races().values():
        for mode, _label in descriptor.creature_placement_modes:
            lookup[mode] = (descriptor.race_name, descriptor.spawn_fn)
    return lookup


# ---------- Новые агрегирующие хелперы (по аналогии с creature_placement_lookup) ----------

def all_player_tools() -> Tuple[PlayerToolSpec, ...]:
    result = []
    for descriptor in all_races():
        result.extend(descriptor.player_tools)
    return tuple(result)

def all_display_checkboxes() -> Tuple[Tuple[str, str], ...]:
    result = []
    for descriptor in all_races():
        result.extend(descriptor.display_checkboxes)
    return tuple(result)

def full_default_display_settings() -> dict:
    """Core-дефолты + дефолты чекбоксов, заявленных расами (все включены по умолчанию)."""
    merged = dict(_CORE_DISPLAY_SETTINGS)
    for key, _label in all_display_checkboxes():
        merged.setdefault(key, True)
    return merged

def all_minimap_layers() -> Tuple[MinimapLayer, ...]:
    result = []
    for descriptor in all_races():
        result.extend(descriptor.minimap_layers)
    return tuple(result)

def all_object_panel_extensions() -> Tuple[Callable, ...]:
    return tuple(d.object_panel_extra_fn for d in all_races() if d.object_panel_extra_fn is not None)

def all_secondary_panel_specs() -> Tuple[SecondaryPanelSpec, ...]:
    result = []
    for descriptor in all_races():
        result.extend(descriptor.secondary_panel_specs)
    return tuple(result)

def all_landmark_specs() -> Tuple[LandmarkSpec, ...]:
    result = []
    for descriptor in all_races():
        result.extend(descriptor.landmark_specs)
    return tuple(result)

def all_extra_object_collections() -> Tuple[ExtraObjectCollectionSpec, ...]:
    result = []
    for descriptor in all_races():
        result.extend(descriptor.extra_object_collections)
    return tuple(result)

def all_biome_cascade_specs() -> Tuple[BiomeCascadeSpec, ...]:
    result = []
    for descriptor in all_races():
        result.extend(descriptor.biome_cascade_specs)
    return tuple(result)

def all_mouse_down_hooks() -> Tuple[Callable, ...]:
    result = []
    for descriptor in all_races():
        result.extend(descriptor.mouse_down_hooks)
    return tuple(result)

def all_mouse_up_hooks() -> Tuple[Callable, ...]:
    result = []
    for descriptor in all_races():
        result.extend(descriptor.mouse_up_hooks)
    return tuple(result)

def all_mouse_motion_hooks() -> Tuple[Callable, ...]:
    result = []
    for descriptor in all_races():
        result.extend(descriptor.mouse_motion_hooks)
    return tuple(result)

def all_mouse_wheel_hooks() -> Tuple[Callable, ...]:
    result = []
    for descriptor in all_races():
        result.extend(descriptor.mouse_wheel_hooks)
    return tuple(result)

def all_extra_world_save_fns() -> Tuple[Callable, ...]:
    return tuple(d.extra_world_save_fn for d in all_races() if d.extra_world_save_fn is not None)

def all_extra_world_load_fns() -> Tuple[Callable, ...]:
    return tuple(d.extra_world_load_fn for d in all_races() if d.extra_world_load_fn is not None)