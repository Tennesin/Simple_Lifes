"""Регистрация животного 'Корова' в animal_registry."""

import uuid

from game.animal_registry import AnimalDescriptor
from .cow import (
    Cow, cow_object_panel_extra_lines, cow_minimap_marker,
    cow_instruction_icon, COW_INSTRUCTION_SECTIONS,
)
from .cow_objects import Leather
from .cow_settings import COW_KIND_NAME, COW_MINIMAP_LABEL, COW_INITIAL_COUNT
from .cow_ai import tick_cow
from .names import COW_NAME_POOLS

def spawn_cow(object_manager, wx, wy, placement_mode):
    new_id = str(uuid.uuid4())[:8]
    cow = Cow(new_id, wx, wy)
    object_manager.game.world.cows.append(cow)

ANIMAL_DESCRIPTOR = AnimalDescriptor(
    animal_name="cow",
    animal_cls=Cow,
    loader_fn=Cow.from_dict,
    spawn_fn=spawn_cow,
    world_collection="cows",
    save_filename="cow.json",
    placement_mode="animal_cow",
    placement_label=COW_KIND_NAME,
    name_pools=COW_NAME_POOLS,
    object_panel_extra_fn=cow_object_panel_extra_lines,
    minimap_checkbox_label=COW_MINIMAP_LABEL,
    minimap_marker_fn=cow_minimap_marker,
    drop_collections=("leathers",),
    drop_persistence_registry=(("leathers.json", "leathers", Leather),),
    tick_fn=tick_cow,
    initial_count=COW_INITIAL_COUNT,
    instruction_sections=COW_INSTRUCTION_SECTIONS,
    instruction_preview_icon="cow",
    instruction_icon_factory=cow_instruction_icon,
)