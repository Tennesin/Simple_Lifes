"""Универсальные инструменты и правила, не завязанные на конкретную расу существ."""

from . import geometry
from . import diet
from .base_entity import BaseEntity, LivingEntity, same_race, filter_same_race
from .ai import GoalComponent, lookup_creature
from .navigation import NavGrid, NavGridCache, SpatialGrid, BasePathfinder
from .diet import (
    DIET_HERBIVORE, DIET_OMNIVORE,
    FOOD_CATEGORY_PLANT, DIET_DISPLAY_MAP, diet_allows_category,
)

__all__ = [
    "geometry", "diet",
    "BaseEntity", "LivingEntity", "same_race", "filter_same_race",
    "GoalComponent", "lookup_creature",
    "NavGrid", "NavGridCache", "SpatialGrid", "BasePathfinder",
    "DIET_HERBIVORE", "DIET_OMNIVORE",
    "FOOD_CATEGORY_PLANT", "DIET_DISPLAY_MAP", "diet_allows_category",
]