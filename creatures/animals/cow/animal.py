"""Регистрация животного 'Корова' в animal_registry."""

import uuid

from game import animal_registry
from . import cow
from . import cow_objects
from . import cow_settings
from . import cow_ai
from . import names

def spawn_cow(object_manager, wx, wy, placement_mode):
    new_id = str(uuid.uuid4())[:8]
    new_cow = cow.Cow(new_id, wx, wy)
    object_manager.game.world.cows.append(new_cow)

ANIMAL_DESCRIPTOR = animal_registry.AnimalDescriptor(
    animal_name="cow",
    animal_cls=cow.Cow,
    loader_fn=cow.Cow.from_dict,
    spawn_fn=spawn_cow,
    world_collection="cows",
    save_filename="cow.json",
    placement_mode="animal_cow",
    placement_label=cow_settings.COW_KIND_NAME,
    name_pools=names.COW_NAME_POOLS,
    object_panel_extra_fn=cow.cow_object_panel_extra_lines,
    minimap_checkbox_label=cow_settings.COW_MINIMAP_LABEL,
    minimap_marker_fn=cow.cow_minimap_marker,
    drop_collections=("leathers",),
    drop_persistence_registry=(("leathers.json", "leathers", cow_objects.Leather),),
    tick_fn=cow_ai.tick_cow,
    initial_count=cow_settings.COW_INITIAL_COUNT,
    instruction_sections=cow.COW_INSTRUCTION_SECTIONS,
    instruction_preview_icon="cow",
    instruction_icon_factory=cow.cow_instruction_icon,
)