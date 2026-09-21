"""Какие типы объектов вообще существуют и где им разрешено стоять."""

import random
from functools import cache

import settings
from game.animal_registry import all_animal_drop_collections, all_animals
from game.race_registry import all_races
from objects import Bush, Fruit, Grass, Meat, Spike, Stone, Tree, WaterPuddle

# ---------- Типы объектов ядра: obj_type -> (имя коллекции мира, класс) ----------
CORE_OBJECT_TYPES = {
    "fruit": ("fruits", Fruit),
    "spike": ("spikes", Spike),
    "water": ("water_puddles", WaterPuddle),
    "bush": ("bushes", Bush),
    "tree": ("trees", Tree),
    "stone": ("stones", Stone),
    "grass": ("grass", Grass),
    "meat": ("meats", Meat),
}

# Коллекции, до которых у любого нового объекта фиксированная дистанция (а не "по занимаемому месту")
FIXED_CLEARANCE_CORE_ATTRS = ("fruits", "spikes", "creatures")

# Коллекции ядра, рядом с которыми нельзя ставить существо
CREATURE_BLOCKING_CORE_ATTRS = ("water_puddles", "bushes")

# Типы, появление/исчезновение которых меняет карту проходимости (nav-сетку)
LANDSCAPE_AFFECTING_TYPES = ("spike",)

# ---------- Где что может стоять ----------
_DEFAULT_OBJECT_BIOMES = (settings.BIOME_PLAINS, settings.BIOME_DESERT)
_BIOMES_BY_OBJECT = {
    "stone": (settings.BIOME_PLAINS, settings.BIOME_DESERT, settings.BIOME_RIVER),
    "water": (settings.BIOME_PLAINS,),
    "bush": (settings.BIOME_PLAINS,),
    "grass": (settings.BIOME_PLAINS,),
    "tree": (settings.BIOME_PLAINS,),
}
# Существа и животные боятся только моря
ANIMAL_BIOMES = (settings.BIOME_PLAINS, settings.BIOME_DESERT, settings.BIOME_RIVER)

def allowed_biomes(obj_type):
    return _BIOMES_BY_OBJECT.get(obj_type, _DEFAULT_OBJECT_BIOMES)

# ---------- Ленивые реестры ----------

@cache
def object_types():
    """obj_type -> (имя коллекции мира, класс). Ядро + размещаемые объекты рас."""
    registry = dict(CORE_OBJECT_TYPES)
    for descriptor in all_races():
        for spec in descriptor.placeable_objects:
            registry[spec.obj_type] = (spec.attr, spec.cls)
    return registry

@cache
def _placement_clearances():
    return {
        spec.obj_type: spec.placement_clearance
        for descriptor in all_races()
        for spec in descriptor.placeable_objects
        if spec.placement_clearance is not None
    }

def placement_clearance(obj_type):
    return _placement_clearances().get(obj_type, 0)

@cache
def mutual_additive_attrs():
    """Коллекции, у которых зазоры суммируются (а не берётся максимум)."""
    return frozenset(
        spec.attr
        for descriptor in all_races()
        for spec in descriptor.placeable_objects
        if spec.mutual_clearance_additive
    )

@cache
def animal_collections():
    return tuple(descriptor.world_collection for descriptor in all_animals())

@cache
def animal_drop_attrs():
    return tuple(all_animal_drop_collections())

@cache
def creature_like_attrs():
    return ("creatures",) + animal_collections()

@cache
def fixed_clearance_attrs():
    return FIXED_CLEARANCE_CORE_ATTRS + animal_collections()

@cache
def footprint_clearance_attrs():
    """Коллекции, для которых зазор считается по занимаемому месту объекта."""
    return tuple(dict.fromkeys(
        attr for attr, _cls in object_types().values()
        if attr not in FIXED_CLEARANCE_CORE_ATTRS
    ))

@cache
def creature_blocking_attrs():
    race_attrs = tuple(
        spec.attr
        for descriptor in all_races()
        for spec in descriptor.placeable_objects
        if spec.blocks_creature_spawn
    )
    return CREATURE_BLOCKING_CORE_ATTRS + race_attrs

# ---------- Создание и определение типа ----------

def _create_meat(cls, x, y):
    amount = random.randint(settings.MEAT_PLACEMENT_AMOUNT_MIN, settings.MEAT_PLACEMENT_AMOUNT_MAX)
    return cls(x, y, food_amount=amount)

# Типам, чей конструктор принимает что-то кроме (x, y), нужна своя фабрика
_CUSTOM_FACTORIES = {
    "meat": _create_meat,
}

def create_object(obj_type, x, y):
    _attr, cls = object_types()[obj_type]
    factory = _CUSTOM_FACTORIES.get(obj_type)
    return factory(cls, x, y) if factory is not None else cls(x, y)

def type_of_instance(obj):
    """obj_type объекта или None, если такой объект не размещается через реестр."""
    for obj_type, (_attr, cls) in object_types().items():
        if isinstance(obj, cls):
            return obj_type
    return None