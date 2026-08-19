"""Создание существ расы 'Круг'."""

import math
import random
import uuid

import settings
from settings import *
from ..ci_settings import *
from ..creature import Creature
from ..life_cycle import CreatureAging
from ..genealogy import GenealogyRegistry

# =========================================================================
# Домен: спавн существ — новое существо "с нуля" и рождение ребёнка
# =========================================================================

def circle_spawn_dispatch(object_manager, wx, wy, placement_mode):
    gender = GENDER_MALE if placement_mode == "creature_male" else GENDER_FEMALE
    object_manager.spawn_managers["circle"].create_creature_at(wx, wy, gender)

class CircleSpawnManager:
    def __init__(self, game, descriptor=None):
        self.game = game
        self.descriptor = descriptor
        self.genealogy = GenealogyRegistry()

    def create_creature_at(self, wx, wy, gender):
        game = self.game
        new_id = str(uuid.uuid4())[:8]
        pools = self.descriptor.name_pools if self.descriptor else None
        creature = Creature(new_id, gender=gender, name_pools=pools)
        creature.x = wx
        creature.y = wy
        creature.comfort_point = (wx, wy)
        game.world.creatures.append(creature)
        creature.age = AGE_CHILD_END
        creature.life_stage = LIFE_STAGE_ADULT
        creature.save(os.path.join(game.world_path, "creatures"))

    def create_child_creature(self, mother, father_id):
        game = self.game
        father = next((c for c in game.world.creatures if c.id == father_id), None)

        gender = random.choice(GENDER_LIST)
        temperament = None
        if random.random() < FAMILY_TEMPERAMENT_INHERIT_CHANCE:
            temperament = random.choice([mother.temperament, father.temperament]) \
                if father is not None else mother.temperament

        new_id = str(uuid.uuid4())[:8]
        pools = self.descriptor.name_pools if self.descriptor else None
        child = Creature(new_id, temperament=temperament, gender=gender, name_pools=pools)

        cx, cy = self._pick_child_spawn_point(mother)
        child.x = cx
        child.y = cy
        child.comfort_point = (child.x, child.y)

        child.age = 0.0
        child.life_stage = LIFE_STAGE_CHILD
        child.parent_ids = (mother.id, father.id if father is not None else None)

        if mother.known_campfire is not None:
            child.known_campfire = mother.known_campfire

        child.relationships[mother.id] = FAMILY_PARENT_START_RELATIONSHIP
        mother.relationships[child.id] = FAMILY_PARENT_START_RELATIONSHIP
        if father is not None:
            child.relationships[father.id] = FAMILY_PARENT_START_RELATIONSHIP
            father.relationships[child.id] = FAMILY_PARENT_START_RELATIONSHIP

        if mother.home_id is not None:
            house = next((h for h in game.world.houses if h.id == mother.home_id), None)
            if house is not None and house.add_resident(child.id):
                child.home_id = house.id

        game.world.creatures.append(child)
        if game.world_path:
            child.save(os.path.join(game.world_path, "creatures"))

    def _pick_child_spawn_point(self, mother, attempts=8):
        game = self.game
        biome_grid = game.biome_manager.grid
        fallback = (mother.x, mother.y)
        for _ in range(attempts):
            angle = random.uniform(0, 2 * math.pi)
            px = mother.x + math.cos(angle) * FAMILY_CHILD_SPAWN_OFFSET
            py = mother.y + math.sin(angle) * FAMILY_CHILD_SPAWN_OFFSET
            px = max(20, min(px, settings.WORLD_WIDTH - 20))
            py = max(20, min(py, settings.WORLD_HEIGHT - 20))
            if biome_grid is None or biome_grid.get_at(px, py) not in (BIOME_SEA, BIOME_RIVER):
                return px, py
            fallback = (px, py)
        if biome_grid is not None and biome_grid.get_at(mother.x, mother.y) not in (BIOME_SEA, BIOME_RIVER):
            return mother.x, mother.y
        return fallback

# =========================================================================
# Домен: загрузка существа из сохранённого состояния (state.json)
# =========================================================================

_CREATURE_SIMPLE_FIELDS = (
    ("hp", "hp", HP_MAX),
    ("hunger", "hunger", HUNGER_MAX),
    ("thirst", "thirst", THIRST_MAX),
    ("consciousness", "consciousness", SANITY_MAX),
    ("x", "x", 0.0),
    ("y", "y", 0.0),
    ("player_memory", "player_memory", list),
    ("is_dead", "is_dead", False),
    ("death_timer", "death_timer", 0.0),
    ("death_cause", "death_cause", None),
    ("player_relationship", "player_relationship", 0.0),
    ("player_named", "player_named", False),
    ("known_roads", "known_roads", dict),
    ("known_road_links", "known_road_links", dict),
    ("relationships", "relationships", dict),
    ("energy", "energy", ENERGY_MAX),
    ("partner_id", "partner_id", None),
    ("is_pregnant", "is_pregnant", False),
    ("pregnancy_timer", "pregnancy_timer", 0.0),
    ("carried_fruit", "carried_fruit", False),
    ("carried_water", "carried_water", False),
    ("storage_supply_mode", "storage_supply_mode", False),
    ("carry_capacity", "carry_capacity", lambda: random.randint(*CREATURE_CARRY_CAPACITY_RANGE)),
    ("carried_resources", "carried_resources", lambda: {"wood": 0, "stone": 0}),
    ("elder_ward_id", "elder_ward_id", None),
    ("burial_target_id", "burial_target_id", None),
    ("graveyard_target_id", "graveyard_target_id", None),
    ("feed_target_id", "feed_target_id", None),
    ("urgent_child_id", "urgent_child_id", None),
    ("urgent_child_timer", "urgent_child_timer", 0.0),
    ("home_id", "home_id", None),
    ("home_eviction_timer", "home_eviction_timer", 0.0),
    ("construction_target_id", "construction_target_id", None),
    ("construction_phase", "construction_phase", None),
    ("gather_target_id", "gather_target_id", None),
    ("gather_type", "gather_type", None),
    ("gather_progress", "gather_progress", 0.0),
    ("gather_needed_amount", "gather_needed_amount", None),
)

_CREATURE_TUPLE_FIELDS = (
    ("known_campfire", "known_campfire"),
    ("known_graveyard", "known_graveyard"),
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
        else:
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
    creature.age = state.get("age", AGE_CHILD_END)
    creature.life_stage = CreatureAging.compute_stage(creature.age)
    creature.aging.sync_stage_modifiers()

def _load_creature_puberty(creature, state):
    is_legacy_puberty_data = "puberty_trigger_age" not in state
    creature.puberty_trigger_age = state.get(
        "puberty_trigger_age", random.uniform(PUBERTY_TRIGGER_AGE_MIN, PUBERTY_TRIGGER_AGE_MAX))
    if is_legacy_puberty_data:
        creature.puberty_done = creature.age >= creature.puberty_trigger_age
        creature.puberty_active = False
        creature.puberty_timer = 0.0
        creature._puberty_speed_bonus = 0.0
        creature._puberty_orig_curiosity = None
    else:
        creature.puberty_done = state.get("puberty_done", False)
        creature.puberty_active = state.get("puberty_active", False)
        creature.puberty_timer = state.get("puberty_timer", 0.0)
        creature._puberty_speed_bonus = state.get("puberty_speed_bonus", 0.0)
        creature._puberty_orig_curiosity = state.get("puberty_orig_curiosity")
    creature.aging.sync_puberty_state()


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
    _load_creature_psyche(creature, state)
    return creature

# =========================================================================
# Домен: постоянная память о родословной (реестр 'Геном') - живёт дольше
# отдельных Creature, поэтому хранится и грузится отдельным файлом мира.
# =========================================================================

def save_circle_genealogy(game):
    manager = game.object_manager.spawn_managers.get("circle")
    if manager is not None and game.world_path:
        manager.genealogy.save(game.world_path)


def load_circle_genealogy(game):
    manager = game.object_manager.spawn_managers.get("circle")
    if manager is not None:
        manager.genealogy = GenealogyRegistry()
        if game.world_path:
            manager.genealogy.load(game.world_path)