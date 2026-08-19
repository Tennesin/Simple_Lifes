"""Регистрация животного 'Овца' в animal_registry."""

import uuid

from game.animal_registry import AnimalDescriptor
from .sheep import Sheep
from .sheep_settings import SHEEP_KIND_NAME
from .names import SHEEP_NAME_POOLS

def spawn_sheep(object_manager, wx, wy, placement_mode):
    new_id = str(uuid.uuid4())[:8]
    sheep = Sheep(new_id, wx, wy)
    object_manager.game.world.sheeps.append(sheep)

ANIMAL_DESCRIPTOR = AnimalDescriptor(
    animal_name="sheep",
    animal_cls=Sheep,
    loader_fn=Sheep.from_dict,
    spawn_fn=spawn_sheep,
    world_collection="sheeps",
    save_filename="sheeps.json",
    placement_mode="animal_sheep",
    placement_label=SHEEP_KIND_NAME,
    name_pools=SHEEP_NAME_POOLS,
)