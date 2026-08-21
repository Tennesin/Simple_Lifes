"""Тик овцы: голод/жажда/энергия, блуждание, выпас, водопой, бегство от волков."""

from ...all_needed.ai.grazer_ai import GrazerAI
from .sheep_settings import *
from settings import BIOME_SEA

_SHEEP_AI_CFG = {
    "speed": SHEEP_SPEED,
    "hunger_drain_interval": SHEEP_HUNGER_DRAIN_INTERVAL,
    "thirst_drain_interval": SHEEP_THIRST_DRAIN_INTERVAL,
    "energy_drain_interval_flee": SHEEP_ENERGY_DRAIN_INTERVAL_FLEE,
    "energy_regen_interval": SHEEP_ENERGY_REGEN_INTERVAL,
    "starve_hp_drain": SHEEP_STARVE_HP_DRAIN,
    "dehydrate_hp_drain": SHEEP_DEHYDRATE_HP_DRAIN,
    "wander_distance": SHEEP_WANDER_DISTANCE,
    "wander_timer": SHEEP_WANDER_TIMER,
    "graze_distance": SHEEP_GRAZE_DISTANCE,
    "graze_rate": SHEEP_GRAZE_RATE,
    "drink_distance": SHEEP_DRINK_DISTANCE,
    "drink_rate": SHEEP_DRINK_RATE,
    "hunger_seek_ratio": SHEEP_HUNGER_SEEK_RATIO,
    "thirst_seek_ratio": SHEEP_THIRST_SEEK_RATIO,
    "hunger_satisfy_ratio": SHEEP_HUNGER_SATISFY_RATIO,
    "thirst_satisfy_ratio": SHEEP_THIRST_SATISFY_RATIO,
    "flee_run_distance": SHEEP_FLEE_RUN_DISTANCE,
}

def _get_ai(sheep):
    ai = getattr(sheep, "_grazer_ai", None)
    if ai is None:
        ai = GrazerAI(sheep, _SHEEP_AI_CFG)
        sheep._grazer_ai = ai
    return ai

def tick_sheep(game, dt, nav_grid=None, fallback_nav_grid=None):
    world = game.world
    biome_grid = game.biome_manager.grid
    wall_polylines, fence_polylines = game.welded_landscape_polylines()

    if biome_grid is not None:
        max_search = max(game.camera.world_w, game.camera.world_h)
        for sheep in world.sheep:
            if sheep.hp > 0 and biome_grid.get_at(sheep.x, sheep.y) == BIOME_SEA:
                land = biome_grid.find_nearest_land(sheep.x, sheep.y, max_search)
                if land is not None:
                    sheep.x, sheep.y = land
                sheep.hp = 0

    dead = [s for s in world.sheep if s.hp <= 0]
    for sheep in dead:
        game.object_manager.remove_animal_and_drop(sheep)

    alive_wolves = [w for w in world.wolves if w.hp > 0]

    for sheep in world.sheep:
        if sheep.hp <= 0:
            continue
        ai = _get_ai(sheep)
        ai.update_needs(dt)
        if sheep.hp <= 0:
            continue
        if sheep is not game.player.grabbed_object:
            target = ai.decide(dt, world.grass, world.water_puddles, alive_wolves, biome_grid,
                               spikes=world.spikes)
            ai.move_towards(target, dt, biome_grid=biome_grid, nav_grid=nav_grid,
                            fallback_nav_grid=fallback_nav_grid,
                            speed_multiplier=(SHEEP_FLEE_SPEED_MULTIPLIER if ai.fleeing else 1.0),
                            wall_polylines=wall_polylines, fence_polylines=fence_polylines,
                            urgent=ai.is_urgent)
        ai.interact(dt, world.grass, world.water_puddles, biome_grid, spikes=world.spikes)