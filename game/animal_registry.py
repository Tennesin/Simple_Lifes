"""Упрощённый аналог race_registry.py - для животных (овцы/коровы/волки)."""

import importlib
import pkgutil
from dataclasses import dataclass
from typing import Callable, Optional, Tuple, Type

import creatures.animals as animals_package

@dataclass(frozen=True)
class AnimalDescriptor:

    animal_name: str
    animal_cls: Type

    loader_fn: Callable            # (state: dict) -> экземпляр животного
    spawn_fn: Callable             # (object_manager, wx, wy, placement_mode) -> None

    world_collection: str          # имя атрибута коллекции в мире (например "sheep")
    save_filename: str             # имя файла сохранения (например "sheep.json")

    placement_mode: str            # ключ режима размещения (для будущего меню)
    placement_label: str           # подпись кнопки размещения

    name_pools: Optional[dict] = None
    tick_fn: Optional[Callable] = None
    object_panel_extra_fn: Optional[Callable] = None  # (obj, all_creatures) -> list[(text, color)]

    # ---------- Дроп-ресурсы животного - generic по образцу world_collections/persistence_registry расы ----------
    drop_collections: Tuple[str, ...] = ()
    drop_persistence_registry: Tuple[Tuple[str, str, Type], ...] = ()

_ANIMALS_CACHE: Optional[dict] = None

def _discover_animals() -> dict:
    registry = {}
    for module_info in pkgutil.iter_modules(animals_package.__path__):
        pkg_name = f"{animals_package.__name__}.{module_info.name}"
        try:
            animal_module = importlib.import_module(f"{pkg_name}.animal")
        except ModuleNotFoundError:
            continue
        descriptor = getattr(animal_module, "ANIMAL_DESCRIPTOR", None)
        if descriptor is None:
            continue
        if descriptor.animal_name in registry:
            raise RuntimeError(
                f"Животное '{descriptor.animal_name}' зарегистрировано более одного раза "
                f"(конфликт при обработке пакета '{pkg_name}')."
            )
        registry[descriptor.animal_name] = descriptor
    return registry

def _animals() -> dict:
    global _ANIMALS_CACHE
    if _ANIMALS_CACHE is None:
        _ANIMALS_CACHE = _discover_animals()
    return _ANIMALS_CACHE

def get_animal(animal_name: str) -> AnimalDescriptor:
    animals = _animals()
    try:
        return animals[animal_name]
    except KeyError:
        raise KeyError(
            f"Животное '{animal_name}' не зарегистрировано (нет creatures/animals/*/animal.py "
            f"с ANIMAL_DESCRIPTOR). Известные животные: {sorted(animals.keys())}"
        )

def all_animal_names() -> Tuple[str, ...]:
    return tuple(_animals().keys())

def all_animals() -> Tuple[AnimalDescriptor, ...]:
    return tuple(_animals().values())

def animal_placement_lookup() -> dict:
    """placement_mode -> (animal_name, spawn_fn) - аналог creature_placement_lookup()."""
    return {
        descriptor.placement_mode: (descriptor.animal_name, descriptor.spawn_fn)
        for descriptor in all_animals()
    }

def all_animal_drop_collections() -> Tuple[str, ...]:
    result = []
    seen = set()
    for descriptor in all_animals():
        for name in descriptor.drop_collections:
            if name not in seen:
                seen.add(name)
                result.append(name)
    return tuple(result)

def all_animal_drop_persistence_entries() -> Tuple[Tuple[str, str, Type], ...]:
    entries = []
    seen_attrs = set()
    for descriptor in all_animals():
        for entry in descriptor.drop_persistence_registry:
            _filename, attr, _cls = entry
            if attr in seen_attrs:
                continue
            seen_attrs.add(attr)
            entries.append(entry)
    return tuple(entries)

def all_animal_object_panel_extensions() -> Tuple[Callable, ...]:
    return tuple(d.object_panel_extra_fn for d in all_animals() if d.object_panel_extra_fn is not None)

def all_animal_persistence_entries() -> Tuple[Tuple[str, str], ...]:
    """(save_filename, world_collection) - аналог _WORLD_OBJECT_REGISTRY."""
    return tuple((d.save_filename, d.world_collection) for d in all_animals())

def animal_classes() -> Tuple[Type, ...]:
    return tuple(d.animal_cls for d in all_animals())