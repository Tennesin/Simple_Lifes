"""Регистрация животного 'Волк' в animal_registry."""

from game import animal_registry
from . import wolf
from . import wolf_objects
from . import wolf_settings
from . import wolf_ai
from . import names
from creatures.all_needed.ids import new_id

def spawn_wolf(object_manager, wx, wy, placement_mode):
    new_wolf = wolf.Wolf(new_id(), wx, wy)
    object_manager.game.world.wolves.append(new_wolf)

ANIMAL_DESCRIPTOR = animal_registry.AnimalDescriptor(
    animal_name="wolf",
    animal_cls=wolf.Wolf,
    loader_fn=wolf.Wolf.from_dict,
    spawn_fn=spawn_wolf,
    world_collection="wolves",
    save_filename="wolves.json",
    placement_mode="animal_wolf",
    placement_label=wolf_settings.WOLF_KIND_NAME,
    name_pools=names.WOLF_NAME_POOLS,
    object_panel_extra_fn=wolf.wolf_object_panel_extra_lines,
    minimap_checkbox_label=wolf_settings.WOLF_MINIMAP_LABEL,
    minimap_marker_fn=wolf.wolf_minimap_marker,
    drop_collections=("hides",),
    drop_persistence_registry=(("hides.json", "hides", wolf_objects.Hide),),
    tick_fn=wolf_ai.tick_wolf,
    initial_count=wolf_settings.WOLF_INITIAL_COUNT,
    instruction_sections=wolf.WOLF_INSTRUCTION_SECTIONS,
    instruction_preview_icon="wolf",
    instruction_icon_factory=wolf.wolf_instruction_icon,
)