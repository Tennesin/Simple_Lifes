"""Регистрация животного 'Корова' в animal_registry."""

import uuid

from game.animal_registry import AnimalDescriptor
from .cow import Cow
from .cow_settings import COW_KIND_NAME
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
    save_filename="cows.json",
    placement_mode="animal_cow",
    placement_label=COW_KIND_NAME,
    name_pools=COW_NAME_POOLS,
)