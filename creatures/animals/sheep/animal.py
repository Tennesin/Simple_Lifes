"""Регистрация животного 'Овца' в animal_registry."""

import uuid

from game.animal_registry import AnimalDescriptor
from .sheep import Sheep, sheep_object_panel_extra_lines
from .sheep_objects import Wool
from .sheep_settings import SHEEP_KIND_NAME
from .sheep_ai import tick_sheep
from .names import SHEEP_NAME_POOLS

def spawn_sheep(object_manager, wx, wy, placement_mode):
    new_id = str(uuid.uuid4())[:8]
    sheep = Sheep(new_id, wx, wy)
    object_manager.game.world.sheep.append(sheep)

ANIMAL_DESCRIPTOR = AnimalDescriptor(
    animal_name="sheep",
    animal_cls=Sheep,
    loader_fn=Sheep.from_dict,
    spawn_fn=spawn_sheep,
    world_collection="sheep",
    save_filename="sheep.json",
    placement_mode="animal_sheep",
    placement_label=SHEEP_KIND_NAME,
    name_pools=SHEEP_NAME_POOLS,
    object_panel_extra_fn=sheep_object_panel_extra_lines,
    drop_collections=("wools",),
    drop_persistence_registry=(("wools.json", "wools", Wool),),
    tick_fn=tick_sheep,
)