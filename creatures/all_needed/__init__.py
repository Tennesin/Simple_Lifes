"""Универсальные инструменты и правила, не завязанные на конкретную расу существ."""

from . import geometry
from . import diet
from .base_entity import BaseEntity
from .ai.utility import GoalComponent, lookup_creature
from .navigation import NavGrid, NavGridCache, SpatialGrid, BasePathfinder
from .diet import (
    DIET_HERBIVORE, DIET_CARNIVORE, DIET_OMNIVORE,
    FOOD_CATEGORY_PLANT, FOOD_CATEGORY_MEAT, DIET_DISPLAY_MAP, diet_allows_category,
)

__all__ = [
    "geometry", "diet",
    "BaseEntity",
    "GoalComponent", "lookup_creature",
    "NavGrid", "NavGridCache", "SpatialGrid", "BasePathfinder",
    "DIET_HERBIVORE", "DIET_CARNIVORE", "DIET_OMNIVORE",
    "FOOD_CATEGORY_PLANT", "FOOD_CATEGORY_MEAT", "DIET_DISPLAY_MAP", "diet_allows_category",
]