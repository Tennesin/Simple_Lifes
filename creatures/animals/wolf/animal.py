"""Регистрация животного 'Волк' в animal_registry."""

import uuid

from game.animal_registry import AnimalDescriptor
from .wolf import Wolf, wolf_object_panel_extra_lines, wolf_minimap_marker
from .wolf_objects import Hide
from .wolf_settings import WOLF_KIND_NAME
from .wolf_ai import tick_wolf
from .names import WOLF_NAME_POOLS
from info import INFO_SETTINGS_MINIMAP_WOLVES

def spawn_wolf(object_manager, wx, wy, placement_mode):
    new_id = str(uuid.uuid4())[:8]
    wolf = Wolf(new_id, wx, wy)
    object_manager.game.world.wolves.append(wolf)

ANIMAL_DESCRIPTOR = AnimalDescriptor(
    animal_name="wolf",
    animal_cls=Wolf,
    loader_fn=Wolf.from_dict,
    spawn_fn=spawn_wolf,
    world_collection="wolves",
    save_filename="wolves.json",
    placement_mode="animal_wolf",
    placement_label=WOLF_KIND_NAME,
    name_pools=WOLF_NAME_POOLS,
    object_panel_extra_fn=wolf_object_panel_extra_lines,
    minimap_checkbox_label=INFO_SETTINGS_MINIMAP_WOLVES,
    minimap_marker_fn=wolf_minimap_marker,
    drop_collections=("hides",),
    drop_persistence_registry=(("hides.json", "hides", Hide),),
    tick_fn=tick_wolf,
)