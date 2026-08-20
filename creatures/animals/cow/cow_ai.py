"""Тик коровы: голод/жажда/энергия, блуждание, выпас, водопой, бегство от волков."""

from ...all_needed.ai.grazer_ai import GrazerAI
from .cow_settings import *

_COW_AI_CFG = {
    "speed": COW_SPEED,
    "hunger_drain_interval": COW_HUNGER_DRAIN_INTERVAL,
    "thirst_drain_interval": COW_THIRST_DRAIN_INTERVAL,
    "energy_drain_interval_flee": COW_ENERGY_DRAIN_INTERVAL_FLEE,
    "energy_regen_interval": COW_ENERGY_REGEN_INTERVAL,
    "starve_hp_drain": COW_STARVE_HP_DRAIN,
    "dehydrate_hp_drain": COW_DEHYDRATE_HP_DRAIN,
    "wander_distance": COW_WANDER_DISTANCE,
    "wander_timer": COW_WANDER_TIMER,
    "graze_distance": COW_GRAZE_DISTANCE,
    "graze_rate": COW_GRAZE_RATE,
    "drink_distance": COW_DRINK_DISTANCE,
    "drink_rate": COW_DRINK_RATE,
    "hunger_seek_ratio": COW_HUNGER_SEEK_RATIO,
    "thirst_seek_ratio": COW_THIRST_SEEK_RATIO,
    "hunger_satisfy_ratio": COW_HUNGER_SATISFY_RATIO,
    "thirst_satisfy_ratio": COW_THIRST_SATISFY_RATIO,
    "flee_run_distance": COW_FLEE_RUN_DISTANCE,
}

def _get_ai(cow):
    ai = getattr(cow, "_grazer_ai", None)
    if ai is None:
        ai = GrazerAI(cow, _COW_AI_CFG)
        cow._grazer_ai = ai
    return ai

def tick_cow(game, dt):
    world = game.world
    biome_grid = game.biome_manager.grid

    dead = [c for c in world.cow if c.hp <= 0]
    for cow in dead:
        game.object_manager.remove_animal_and_drop(cow)

    alive_wolves = [w for w in world.wolves if w.hp > 0]

    for cow in world.cow:
        if cow.hp <= 0:
            continue
        ai = _get_ai(cow)
        ai.update_needs(dt)
        if cow.hp <= 0:
            continue
        target = ai.decide(dt, world.grass, world.water_puddles, alive_wolves, biome_grid,
                           spikes=world.spikes)
        ai.move_towards(target, dt, speed_multiplier=(COW_FLEE_SPEED_MULTIPLIER if ai.fleeing else 1.0))
        ai.interact(dt, world.grass, world.water_puddles, biome_grid, spikes=world.spikes)