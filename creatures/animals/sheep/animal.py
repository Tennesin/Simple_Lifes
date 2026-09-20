"""Регистрация животного 'Овца' в animal_registry."""

import uuid

from game import animal_registry
from . import sheep
from . import sheep_objects
from . import sheep_settings
from . import sheep_ai
from . import names

def spawn_sheep(object_manager, wx, wy, placement_mode):
    new_id = str(uuid.uuid4())[:8]
    new_sheep = sheep.Sheep(new_id, wx, wy)
    object_manager.game.world.sheep.append(new_sheep)

ANIMAL_DESCRIPTOR = animal_registry.AnimalDescriptor(
    animal_name="sheep",
    animal_cls=sheep.Sheep,
    loader_fn=sheep.Sheep.from_dict,
    spawn_fn=spawn_sheep,
    world_collection="sheep",
    save_filename="sheep.json",
    placement_mode="animal_sheep",
    placement_label=sheep_settings.SHEEP_KIND_NAME,
    name_pools=names.SHEEP_NAME_POOLS,
    object_panel_extra_fn=sheep.sheep_object_panel_extra_lines,
    minimap_checkbox_label=sheep_settings.SHEEP_MINIMAP_LABEL,
    minimap_marker_fn=sheep.sheep_minimap_marker,
    drop_collections=("wools",),
    drop_persistence_registry=(("wools.json", "wools", sheep_objects.Wool),),
    tick_fn=sheep_ai.tick_sheep,
    initial_count=sheep_settings.SHEEP_INITIAL_COUNT,
    instruction_sections=sheep.SHEEP_INSTRUCTION_SECTIONS,
    instruction_preview_icon="sheep",
    instruction_icon_factory=sheep.sheep_instruction_icon,
)