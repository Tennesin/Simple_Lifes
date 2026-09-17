"""Тик овцы: голод/жажда/энергия, блуждание, выпас, водопой, бегство от волков."""

from ...all_needed.ai.grazer_ai import tick_grazer_species
from .sheep_settings import *

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

def tick_sheep(game, dt, nav_grid=None, fallback_nav_grid=None, active_ids=None, spatial_grids=None):
    tick_grazer_species(
        game, dt, nav_grid, fallback_nav_grid, active_ids, spatial_grids,
        world_attr="sheep", ai_cache_attr="_grazer_ai", cfg=_SHEEP_AI_CFG,
        flee_speed_multiplier=SHEEP_FLEE_SPEED_MULTIPLIER,
    )