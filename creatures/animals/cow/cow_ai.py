"""Тик коровы: голод/жажда/энергия, блуждание, выпас, водопой, бегство от волков."""

from ...all_needed.ai.grazer_ai import tick_grazer_species
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

def tick_cow(game, dt, nav_grid=None, fallback_nav_grid=None, active_ids=None, spatial_grids=None):
    tick_grazer_species(
        game, dt, nav_grid, fallback_nav_grid, active_ids, spatial_grids,
        world_attr="cows", ai_cache_attr="_grazer_ai", cfg=_COW_AI_CFG,
        flee_speed_multiplier=COW_FLEE_SPEED_MULTIPLIER,
    )