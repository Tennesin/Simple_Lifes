"""Создание существ расы 'Круг'."""

import math
import random

import settings

from ....all_needed.ids import new_id
from .. import ci_settings
from ..creature import Creature
from ..genealogy import GenealogyRegistry
from ..life_cycle import CreatureAging

from ..state.puberty_state import PubertyState
from ..state.burial_state import BurialState
from ..state.construction_state import ConstructionState
from ..state.feeding_state import FeedingState
from ..state.storage_supply_state import StorageSupplyState
from ..state.housing_state import HousingState

# =========================================================================
# Домен: спавн существ — новое существо "с нуля" и рождение ребёнка
# =========================================================================

def circle_spawn_dispatch(object_manager, wx, wy, placement_mode):
    gender = ci_settings.GENDER_MALE if placement_mode == "creature_male" else ci_settings.GENDER_FEMALE
    object_manager.spawn_managers[ci_settings.RACE_NAME].create_creature_at(wx, wy, gender)

class CircleSpawnManager:
    def __init__(self, game, descriptor=None):
        self.game = game
        self.descriptor = descriptor
        self.genealogy = GenealogyRegistry()

    def create_creature_at(self, wx, wy, gender):
        game = self.game
        new_creature_id = new_id()
        pools = self.descriptor.name_pools if self.descriptor else None
        creature = Creature(new_creature_id, gender=gender, name_pools=pools)
        creature.x = wx
        creature.y = wy
        creature.comfort_point = (wx, wy)
        game.world.creatures.append(creature)
        creature.age = ci_settings.AGE_CHILD_END
        creature.life_stage = ci_settings.LIFE_STAGE_ADULT

    def create_child_creature(self, mother, father_id):
        game = self.game
        father = next((c for c in game.world.creatures if c.id == father_id), None)

        gender = random.choice(ci_settings.GENDER_LIST)
        temperament = None
        if random.random() < ci_settings.FAMILY_TEMPERAMENT_INHERIT_CHANCE:
            temperament = random.choice([mother.temperament, father.temperament]) \
                if father is not None else mother.temperament

        child_id = new_id()
        pools = self.descriptor.name_pools if self.descriptor else None
        child = Creature(child_id, temperament=temperament, gender=gender, name_pools=pools)

        cx, cy = self._pick_child_spawn_point(mother)
        child.x = cx
        child.y = cy
        child.comfort_point = (child.x, child.y)

        child.age = 0.0
        child.life_stage = ci_settings.LIFE_STAGE_CHILD
        child.parent_ids = (mother.id, father.id if father is not None else None)

        if mother.known_campfire is not None:
            child.known_campfire = mother.known_campfire
            child.known_campfire_id = mother.known_campfire_id

        child.relationships[mother.id] = ci_settings.FAMILY_PARENT_START_RELATIONSHIP
        mother.relationships[child.id] = ci_settings.FAMILY_PARENT_START_RELATIONSHIP
        if father is not None:
            child.relationships[father.id] = ci_settings.FAMILY_PARENT_START_RELATIONSHIP
            father.relationships[child.id] = ci_settings.FAMILY_PARENT_START_RELATIONSHIP

        if mother.home_id is not None:
            house = next((h for h in game.world.houses if h.id == mother.home_id), None)
            if house is not None and house.add_resident(child.id):
                child.home_id = house.id

        game.world.creatures.append(child)

    def _pick_child_spawn_point(self, mother, attempts=8):
        game = self.game
        biome_grid = game.biome_manager.grid
        fallback = (mother.x, mother.y)
        for _ in range(attempts):
            angle = random.uniform(0, 2 * math.pi)
            px = mother.x + math.cos(angle) * ci_settings.FAMILY_CHILD_SPAWN_OFFSET
            py = mother.y + math.sin(angle) * ci_settings.FAMILY_CHILD_SPAWN_OFFSET
            px = max(20, min(px, settings.WORLD_WIDTH - 20))
            py = max(20, min(py, settings.WORLD_HEIGHT - 20))
            if biome_grid is None or biome_grid.get_at(px, py) not in (settings.BIOME_SEA, settings.BIOME_RIVER):
                return px, py
            fallback = (px, py)
        if biome_grid is not None and biome_grid.get_at(mother.x, mother.y) not in (
                settings.BIOME_SEA, settings.BIOME_RIVER):
            return mother.x, mother.y
        return fallback

# =========================================================================
# Домен: загрузка существа из сохранённого состояния (state.json)
# =========================================================================

_KEEP_CONSTRUCTOR_DEFAULT = object()

_CREATURE_SIMPLE_FIELDS = (
    ("hp", "hp", ci_settings.HP_MAX),
    ("hunger", "hunger", ci_settings.HUNGER_MAX),
    ("thirst", "thirst", ci_settings.THIRST_MAX),
    ("consciousness", "consciousness", ci_settings.SANITY_MAX),
    ("x", "x", 0.0),
    ("y", "y", 0.0),
    ("player_memory", "player_memory", list),
    ("is_dead", "is_dead", False),
    ("death_timer", "death_timer", 0.0),
    ("death_cause", "death_cause", None),
    ("player_relationship", "player_relationship", 0.0),
    ("favorite_bonus_applied", "favorite_bonus_applied", False),
    ("player_named", "player_named", False),
    ("known_roads", "known_roads", dict),
    ("known_road_links", "known_road_links", dict),
    ("relationships", "relationships", dict),
    ("energy", "energy", ci_settings.ENERGY_MAX),
    ("partner_id", "partner_id", None),
    ("is_pregnant", "is_pregnant", False),
    ("pregnancy_timer", "pregnancy_timer", 0.0),
    ("elder_ward_id", "elder_ward_id", None),
    ("known_campfire_id", "known_campfire_id", None),
    ("curiosity", "curiosity", _KEEP_CONSTRUCTOR_DEFAULT),
    ("is_sleeping", "is_sleeping", False),
    ("sleep_forced", "sleep_forced", False),
)

_CREATURE_TUPLE_FIELDS = (
    ("known_campfire", "known_campfire"),
    ("parent_ids", "parent_ids"),
)

_CREATURE_PSYCHE_FIELDS = (
    ("psyche_joy", "joy"),
    ("psyche_satisfaction", "satisfaction"),
    ("psyche_calmness", "calmness"),
    ("psyche_confidence", "confidence"),
    ("psyche_attachment", "attachment"),
)

def _load_creature_simple_fields(creature, state):
    for key, attr, default in _CREATURE_SIMPLE_FIELDS:
        if key in state:
            setattr(creature, attr, state[key])
        elif default is not _KEEP_CONSTRUCTOR_DEFAULT:
            setattr(creature, attr, default() if callable(default) else default)

def _load_creature_tuple_fields(creature, state):
    if "comfort_point" in state:
        creature.comfort_point = tuple(state["comfort_point"])
    for key, attr in _CREATURE_TUPLE_FIELDS:
        value = state.get(key)
        setattr(creature, attr, tuple(value) if value else None)

def _load_creature_knowledge(creature, state):
    default_knowledge = {"fruit": False, "spike": False, "water": False,
                         "bush": False, "campfire": False}
    creature.knowledge = {**default_knowledge, **state.get("knowledge", {})}

def _load_creature_age_and_stage(creature, state):
    creature.age = state.get("age", ci_settings.AGE_CHILD_END)
    creature.life_stage = CreatureAging.compute_stage(creature.age)
    creature.aging.sync_stage_modifiers()

# ---------- state-блок ----------

def _load_creature_puberty(creature, state):
    creature.puberty = PubertyState.from_persisted_dict(state)
    creature.aging.sync_puberty_state()

def _load_creature_burial(creature, state):
    creature.burial = BurialState.from_persisted_dict(state)

def _load_creature_construction(creature, state):
    creature.construction = ConstructionState.from_persisted_dict(state)

def _load_creature_feeding(creature, state):
    creature.feeding = FeedingState.from_persisted_dict(state)

def _load_creature_storage_supply(creature, state):
    creature.storage_supply = StorageSupplyState.from_persisted_dict(state)

def _load_creature_housing(creature, state):
    creature.housing = HousingState.from_persisted_dict(state)

def _load_creature_psyche(creature, state):
    for key, attr in _CREATURE_PSYCHE_FIELDS:
        setattr(creature.psyche, attr, state.get(key, 0.0))

def load_creature_from_state(state):
    """Точка входа для game/race_registry.py: RaceDescriptor.loader_fn расы 'circle'."""
    creature = Creature(state["id"], name=state.get("name"),
                        temperament=state.get("temperament"),
                        gender=state.get("gender"))
    _load_creature_simple_fields(creature, state)
    _load_creature_tuple_fields(creature, state)
    _load_creature_knowledge(creature, state)
    _load_creature_age_and_stage(creature, state)
    _load_creature_puberty(creature, state)
    _load_creature_burial(creature, state)
    _load_creature_psyche(creature, state)
    _load_creature_construction(creature, state)
    _load_creature_feeding(creature, state)
    _load_creature_storage_supply(creature, state)
    _load_creature_housing(creature, state)
    return creature

# =========================================================================
# Домен: постоянная память о родословной (реестр 'Геном') - живёт дольше
# отдельных Creature, поэтому хранится и грузится отдельным файлом мира.
# =========================================================================

def save_circle_genealogy(game):
    manager = game.object_manager.spawn_managers.get(ci_settings.RACE_NAME)
    if manager is not None and game.world_path:
        manager.genealogy.save(game.world_path)


def load_circle_genealogy(game):
    manager = game.object_manager.spawn_managers.get(ci_settings.RACE_NAME)
    if manager is not None:
        manager.genealogy = GenealogyRegistry()
        if game.world_path:
            manager.genealogy.load(game.world_path)