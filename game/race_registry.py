import importlib
import pkgutil
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cache

import creatures.races as races_package
import info
from creatures.all_needed.instruction import InstructionEntry
from objects import Road


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
    cls: type
    label: str
    placement_clearance: float | None = None
    secondary_panel_attr: str | None = None
    blocks_creature_spawn: bool = False
    mutual_clearance_additive: bool = False
    manually_placeable: bool = True

@dataclass(frozen=True)
class RoadNetworkSpec:
    """Описание одной дорожной сети — общая инфраструктура и для всех видов."""
    obj_type: str
    road_collection: str
    crossing_collection: str
    verify_fn: Callable | None = None
    road_cls: type | None = None
    preview_color: tuple[int, int, int] = (255, 255, 255)
    menu_label: str | None = None
    menu_hint: str | None = None

CORE_ROAD_NETWORK = RoadNetworkSpec(
    obj_type="road", road_collection="roads", crossing_collection="road_crossings",
    road_cls=Road, preview_color=(255, 255, 255),
    menu_label=info.INFO_BTN_DRAW_ROAD, menu_hint=info.INFO_TOOL_ROAD_HINT)

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
    panel_cls: type
    is_selected_fn: Callable | None = None
    popup_draw_fn: Callable | None = None

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
    on_delete: Callable | None = None  # (game, obj) -> None
    can_delete_fn: Callable | None = None  # (game, obj) -> bool;

@dataclass(frozen=True)
class BiomeCascadeSpec:
    """Как одна коллекция объектов расы реагирует на смену биома в зоне покраски."""
    attr: str
    clear_on_flood: bool = False
    clear_on_desert: bool = False
    on_removed: Callable | None = None  # (game, obj) -> None

@dataclass(frozen=True)
class RaceDescriptor:
    """Описание одной расы существ - всё, что нужно движку, чтобы работать с ней."""

    race_name: str
    creature_cls: type
    tick_processor_cls: type

    loader_fn: Callable
    panel_cls: type

    spawn_manager_cls: type | None = None
    spawn_fn: Callable | None = None
    name_pools: dict | None = None
    creature_placement_modes: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    world_collections: tuple[str, ...] = field(default_factory=tuple)
    persistence_registry: tuple[tuple[str, str, type], ...] = field(default_factory=tuple)
    placeable_objects: tuple[PlaceableObjectSpec, ...] = field(default_factory=tuple)
    render_layers: tuple[RenderLayer, ...] = field(default_factory=tuple)
    road_networks: tuple[RoadNetworkSpec, ...] = field(default_factory=tuple)

    # ---------- Новое: тик "неживых" объектов расы (не существ) ----------
    world_tick_fn: Callable | None = None  # (game, dt) -> None
    # ---------- Дополнительное сохранение/загрузка мира, специфичное для расы ----------
    extra_world_save_fn: Callable | None = None  # (game) -> None
    extra_world_load_fn: Callable | None = None  # (game) -> None

    # ---------- Новое: генерализация ui ----------
    player_tools: tuple[PlayerToolSpec, ...] = field(default_factory=tuple)
    display_checkboxes: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    minimap_layers: tuple[MinimapLayer, ...] = field(default_factory=tuple)
    object_panel_extra_fn: Callable | None = None  # (obj, all_creatures) -> list[(text, color)]
    secondary_panel_specs: tuple[SecondaryPanelSpec, ...] = field(default_factory=tuple)
    landmark_specs: tuple[LandmarkSpec, ...] = field(default_factory=tuple)
    extra_object_collections: tuple[ExtraObjectCollectionSpec, ...] = field(default_factory=tuple)
    biome_cascade_specs: tuple[BiomeCascadeSpec, ...] = field(default_factory=tuple)

    # ---------- Обобщённые крючки мыши. ----------
    mouse_down_hooks: tuple[Callable, ...] = field(default_factory=tuple)
    mouse_up_hooks: tuple[Callable, ...] = field(default_factory=tuple)
    mouse_motion_hooks: tuple[Callable, ...] = field(default_factory=tuple)
    mouse_wheel_hooks: tuple[Callable, ...] = field(default_factory=tuple)

    # ---------- Инструкция: раса документирует сама себя ----------
    instruction_title: str | None = None                  # имя в списке ("Круг"); None -> race_name
    instruction_sections: tuple = field(default_factory=tuple)
    instruction_preview_icon: str | None = None           # вариант иконки строки-заголовка
    instruction_icon_factory: Callable | None = None      # (variant_key, size) -> pygame.Surface|None

_RACES_CACHE: dict | None = None

def _discover_races() -> dict:
    registry = {}
    for module_info in pkgutil.iter_modules(races_package.__path__):
        race_pkg_name = f"{races_package.__name__}.{module_info.name}"
        try:
            race_module = importlib.import_module(f"{race_pkg_name}.race")
        except ModuleNotFoundError as error:
            if error.name != f"{race_pkg_name}.race":
                raise
            continue
        descriptor = getattr(race_module, "RACE_DESCRIPTOR", None)
        if descriptor is None:
            continue

        if descriptor.race_name in registry:
            raise RuntimeError(
                f"Раса '{descriptor.race_name}' зарегистрирована более одного раза "
                f"(конфликт при обработке пакета '{race_pkg_name}'). "
                f"race_name должен быть уникален среди всех creatures/races/*/race.py."
            )
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

def all_race_names() -> tuple[str, ...]:
    return tuple(_races().keys())

def all_races() -> tuple[RaceDescriptor, ...]:
    return tuple(_races().values())

def creature_placement_lookup():
    lookup = {}
    for descriptor in _races().values():
        for mode, _label in descriptor.creature_placement_modes:
            lookup[mode] = (descriptor.race_name, descriptor.spawn_fn)
    return lookup

# ---------- Новые агрегирующие хелперы (по аналогии с creature_placement_lookup) ----------

def all_player_tools() -> tuple[PlayerToolSpec, ...]:
    result = []
    for descriptor in all_races():
        result.extend(descriptor.player_tools)
    return tuple(result)

def all_display_checkboxes() -> tuple[tuple[str, str], ...]:
    result = []
    for descriptor in all_races():
        result.extend(descriptor.display_checkboxes)
    return tuple(result)

def all_minimap_layers() -> tuple[MinimapLayer, ...]:
    result = []
    for descriptor in all_races():
        result.extend(descriptor.minimap_layers)
    return tuple(result)

def all_object_panel_extensions() -> tuple[Callable, ...]:
    return tuple(d.object_panel_extra_fn for d in all_races() if d.object_panel_extra_fn is not None)

def all_secondary_panel_specs() -> tuple[SecondaryPanelSpec, ...]:
    result = []
    for descriptor in all_races():
        result.extend(descriptor.secondary_panel_specs)
    return tuple(result)

def all_landmark_specs() -> tuple[LandmarkSpec, ...]:
    result = []
    for descriptor in all_races():
        result.extend(descriptor.landmark_specs)
    return tuple(result)

def all_race_instruction_entries() -> tuple[InstructionEntry, ...]:
    """Готовые карточки-аккордеоны раздела 'Расы'."""
    entries = []
    for descriptor in all_races():
        if not descriptor.instruction_sections:
            continue
        entries.append(InstructionEntry(
            key=descriptor.race_name,
            title=descriptor.instruction_title or descriptor.race_name,
            sections=tuple(descriptor.instruction_sections),
            preview_icon=descriptor.instruction_preview_icon,
            icon_factory=descriptor.instruction_icon_factory,
        ))
    # ---------- Порядок pkgutil.iter_modules не гарантирован - сортируем сами ----------
    entries.sort(key=lambda e: e.title.lower())
    return tuple(entries)

def all_extra_object_collections() -> tuple[ExtraObjectCollectionSpec, ...]:
    result = []
    for descriptor in all_races():
        result.extend(descriptor.extra_object_collections)
    return tuple(result)

def all_biome_cascade_specs() -> tuple[BiomeCascadeSpec, ...]:
    result = []
    for descriptor in all_races():
        result.extend(descriptor.biome_cascade_specs)
    return tuple(result)

def all_mouse_down_hooks() -> tuple[Callable, ...]:
    result = []
    for descriptor in all_races():
        result.extend(descriptor.mouse_down_hooks)
    return tuple(result)

def all_mouse_up_hooks() -> tuple[Callable, ...]:
    result = []
    for descriptor in all_races():
        result.extend(descriptor.mouse_up_hooks)
    return tuple(result)

def all_mouse_motion_hooks() -> tuple[Callable, ...]:
    result = []
    for descriptor in all_races():
        result.extend(descriptor.mouse_motion_hooks)
    return tuple(result)

def all_mouse_wheel_hooks() -> tuple[Callable, ...]:
    result = []
    for descriptor in all_races():
        result.extend(descriptor.mouse_wheel_hooks)
    return tuple(result)

def all_extra_world_save_fns() -> tuple[Callable, ...]:
    return tuple(d.extra_world_save_fn for d in all_races() if d.extra_world_save_fn is not None)

def all_extra_world_load_fns() -> tuple[Callable, ...]:
    return tuple(d.extra_world_load_fn for d in all_races() if d.extra_world_load_fn is not None)

@cache
def all_road_networks() -> tuple[RoadNetworkSpec, ...]:
    result = [CORE_ROAD_NETWORK]
    for descriptor in all_races():
        result.extend(descriptor.road_networks)
    return tuple(result)