"""Универсальные инструменты и правила, не завязанные на конкретную расу существ."""

from . import diet, geometry, instruction
from .ai import GoalComponent, lookup_creature
from .base_entity import BaseEntity, LivingEntity, filter_same_race, same_race
from .diet import (
    DIET_CARNIVORE,
    DIET_DISPLAY_MAP,
    DIET_HERBIVORE,
    DIET_OMNIVORE,
    FOOD_CATEGORY_COOKED_MEAT,
    FOOD_CATEGORY_PLANT,
    FOOD_CATEGORY_RAW_MEAT,
    diet_allows_category,
)
from .instruction import (
    INSTRUCTION_COLOR_DEFAULT,
    INSTRUCTION_COLOR_FEMALE,
    INSTRUCTION_COLOR_GOOD,
    INSTRUCTION_COLOR_HINT,
    INSTRUCTION_COLOR_MALE,
    INSTRUCTION_COLOR_NEUTRAL_ACCENT,
    INSTRUCTION_COLOR_WARNING,
    InstructionBullet,
    InstructionCallout,
    InstructionCategory,
    InstructionEntry,
    InstructionHeader,
    InstructionParagraph,
    wrap_instruction_text,
)
from .navigation import BasePathfinder, NavGrid, NavGridCache, SpatialGrid
from .weak_owner import WeakEntityMixin, WeakOwnerMixin

__all__ = [
    "DIET_CARNIVORE",
    "DIET_DISPLAY_MAP",
    "DIET_HERBIVORE",
    "DIET_OMNIVORE",
    "FOOD_CATEGORY_COOKED_MEAT",
    "FOOD_CATEGORY_PLANT",
    "FOOD_CATEGORY_RAW_MEAT",
    "INSTRUCTION_COLOR_DEFAULT",
    "INSTRUCTION_COLOR_FEMALE",
    "INSTRUCTION_COLOR_GOOD",
    "INSTRUCTION_COLOR_HINT",
    "INSTRUCTION_COLOR_MALE",
    "INSTRUCTION_COLOR_NEUTRAL_ACCENT",
    "INSTRUCTION_COLOR_WARNING",
    "BaseEntity",
    "BasePathfinder",
    "GoalComponent",
    "InstructionBullet",
    "InstructionCallout",
    "InstructionCategory",
    "InstructionEntry",
    "InstructionHeader",
    "InstructionParagraph",
    "LivingEntity",
    "NavGrid",
    "NavGridCache",
    "SpatialGrid",
    "WeakEntityMixin",
    "WeakOwnerMixin",
    "diet",
    "diet_allows_category",
    "filter_same_race",
    "geometry",
    "instruction",
    "lookup_creature",
    "same_race",
    "wrap_instruction_text",
]