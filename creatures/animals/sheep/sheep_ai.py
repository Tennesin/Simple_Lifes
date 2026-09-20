"""Тик овцы: голод/жажда/энергия, блуждание, выпас, водопой, бегство от волков."""

from ...all_needed.ai import grazer_ai
from . import sheep_settings

_SHEEP_AI_CFG = {
    "speed": sheep_settings.SHEEP_SPEED,
    "hunger_drain_interval": sheep_settings.SHEEP_HUNGER_DRAIN_INTERVAL,
    "thirst_drain_interval": sheep_settings.SHEEP_THIRST_DRAIN_INTERVAL,
    "energy_drain_interval_flee": sheep_settings.SHEEP_ENERGY_DRAIN_INTERVAL_FLEE,
    "energy_regen_interval": sheep_settings.SHEEP_ENERGY_REGEN_INTERVAL,
    "starve_hp_drain": sheep_settings.SHEEP_STARVE_HP_DRAIN,
    "dehydrate_hp_drain": sheep_settings.SHEEP_DEHYDRATE_HP_DRAIN,
    "wander_distance": sheep_settings.SHEEP_WANDER_DISTANCE,
    "wander_timer": sheep_settings.SHEEP_WANDER_TIMER,
    "graze_distance": sheep_settings.SHEEP_GRAZE_DISTANCE,
    "graze_rate": sheep_settings.SHEEP_GRAZE_RATE,
    "drink_distance": sheep_settings.SHEEP_DRINK_DISTANCE,
    "drink_rate": sheep_settings.SHEEP_DRINK_RATE,
    "hunger_seek_ratio": sheep_settings.SHEEP_HUNGER_SEEK_RATIO,
    "thirst_seek_ratio": sheep_settings.SHEEP_THIRST_SEEK_RATIO,
    "hunger_satisfy_ratio": sheep_settings.SHEEP_HUNGER_SATISFY_RATIO,
    "thirst_satisfy_ratio": sheep_settings.SHEEP_THIRST_SATISFY_RATIO,
    "flee_run_distance": sheep_settings.SHEEP_FLEE_RUN_DISTANCE,
}

def tick_sheep(game, dt, nav_grid=None, fallback_nav_grid=None, active_ids=None, spatial_grids=None):
    grazer_ai.tick_grazer_species(
        game, dt, nav_grid, fallback_nav_grid, active_ids, spatial_grids,
        world_attr="sheep", ai_cache_attr="_grazer_ai", cfg=_SHEEP_AI_CFG,
        flee_speed_multiplier=sheep_settings.SHEEP_FLEE_SPEED_MULTIPLIER,
    )