"""Точка входа расы 'Круг' для авто-регистрации."""

from game.race_registry import (
    BiomeCascadeSpec,
    ExtraObjectCollectionSpec,
    LandmarkSpec,
    MinimapLayer,
    PlaceableObjectSpec,
    RaceDescriptor,
    RenderLayer,
    RoadNetworkSpec,
    SecondaryPanelSpec,
)
from objects import RoadCrossing

from . import ci_info, ci_settings
from .circle_objects import (
    Campfire,
    ChildRoad,
    ConstructionSite,
    Graveyard,
    House,
    StorageField,
)
from .creature import Creature
from .mechanics.creature_lifecycle import (
    CircleSpawnManager,
    circle_spawn_dispatch,
    load_circle_genealogy,
    save_circle_genealogy,
)
from .mechanics.creature_lifecycle import (
    load_creature_from_state as load_circle_creature,
)
from .mechanics.input_events import (
    circle_handle_relationships_scrollbar_down,
    circle_handle_relationships_scrollbar_motion,
    circle_handle_relationships_scrollbar_up,
    circle_handle_relationships_wheel,
    on_delete_campfire,
    on_delete_construction_site,
    on_delete_graveyard,
    on_delete_house,
    on_delete_storage_field,
    storage_field_can_delete,
)
from .mechanics.panel import (
    CreaturePanel,
    GenealogyTreeOverlay,
    GraveyardPanel,
    circle_object_panel_extra_lines,
)
from .mechanics.render import (
    draw_campfires,
    draw_child_roads,
    draw_construction_sites,
    draw_graveyards,
    draw_houses,
    draw_minimap_campfires,
    draw_minimap_child_roads,
    draw_minimap_constructions,
    draw_minimap_houses,
    draw_storage_fields,
)
from .mechanics.tick import CircleTickProcessor, tick_circle_world
from .race_instruction import (
    CIRCLE_INSTRUCTION_PREVIEW_ICON,
    CIRCLE_INSTRUCTION_SECTIONS,
    CIRCLE_INSTRUCTION_TITLE,
    circle_instruction_icon,
)

RACE_DESCRIPTOR = RaceDescriptor(
    race_name=ci_settings.RACE_NAME,
    creature_cls=Creature,
    tick_processor_cls=CircleTickProcessor,
    loader_fn=load_circle_creature,
    panel_cls=CreaturePanel,
    spawn_manager_cls=CircleSpawnManager,
    creature_placement_modes=(
        ("creature_male", ci_info.INFO_BTN_CREATE_MALE),
        ("creature_female", ci_info.INFO_BTN_CREATE_FEMALE),
    ),
    spawn_fn=circle_spawn_dispatch,
    world_collections=(
        "child_roads", "child_road_crossings",
        "storage_fields", "construction_sites", "graveyards",
        "houses", "campfires",
    ),
    persistence_registry=(
        ("child_roads.json", "child_roads", ChildRoad),
        ("storage_fields.json", "storage_fields", StorageField),
        ("construction_sites.json", "construction_sites", ConstructionSite),
        ("graveyards.json", "graveyards", Graveyard),
        ("child_road_crossings.json", "child_road_crossings", RoadCrossing),
        ("houses.json", "houses", House),
        ("campfires.json", "campfires", Campfire),
    ),
    placeable_objects=(
        PlaceableObjectSpec(
            obj_type="graveyard", attr="graveyards", cls=Graveyard, label=ci_info.INFO_BTN_GRAVEYARD,
            placement_clearance=ci_settings.GRAVEYARD_DEFAULT_SIZE[0] / 2 + 10,
            secondary_panel_attr="graveyard_panel",
            blocks_creature_spawn=True,
            mutual_clearance_additive=True,
            manually_placeable=False,
        ),
        PlaceableObjectSpec(
            obj_type="house", attr="houses", cls=House, label=ci_info.INFO_BTN_HOUSE,
            placement_clearance=ci_settings.HOUSE_DEFAULT_SIZE[0] / 2 + 10,
            blocks_creature_spawn=True,
            mutual_clearance_additive=True,
            manually_placeable=False,
        ),
        PlaceableObjectSpec(
            obj_type="campfire", attr="campfires", cls=Campfire, label=ci_info.INFO_BTN_CAMPFIRE,
            blocks_creature_spawn=True,
            manually_placeable=False,
        ),
    ),
    render_layers=(
        RenderLayer("child_roads", insert_after="road_crossings", draw_fn=draw_child_roads),
        RenderLayer("campfires", insert_after="stones", draw_fn=draw_campfires),
        RenderLayer("storage_fields", insert_after="stones", draw_fn=draw_storage_fields),
        RenderLayer("construction_sites", insert_after="stones", draw_fn=draw_construction_sites),
        RenderLayer("graveyards", insert_after="stones", draw_fn=draw_graveyards),
        RenderLayer("houses", insert_after="stones", draw_fn=draw_houses),
    ),
    road_networks=(
        RoadNetworkSpec(
            obj_type="child_road", road_collection="child_roads",
            crossing_collection="child_road_crossings",
            verify_fn=lambda road, spikes: road.verify_safety(spikes),
            road_cls=ChildRoad,
            preview_color=ci_settings.CHILD_ROAD_COLOR_PENDING,
            menu_label=ci_info.INFO_BTN_DRAW_CHILD_ROAD,
            menu_hint=ci_info.INFO_TOOL_CHILD_ROAD_HINT,
        ),
    ),
    world_tick_fn=tick_circle_world,
    display_checkboxes=(
        ("minimap_show_constructions", ci_info.INFO_SETTINGS_MINIMAP_CONSTRUCTIONS),
        ("minimap_show_houses", ci_info.INFO_SETTINGS_MINIMAP_HOUSES),
    ),
    minimap_layers=(
        MinimapLayer("child_roads", insert_after="roads", draw_fn=draw_minimap_child_roads),
        MinimapLayer("campfires", insert_after="stones", draw_fn=draw_minimap_campfires),
        MinimapLayer("constructions", insert_after="stones", draw_fn=draw_minimap_constructions),
        MinimapLayer("houses", insert_after="stones", draw_fn=draw_minimap_houses),
    ),
    object_panel_extra_fn=circle_object_panel_extra_lines,
    secondary_panel_specs=(
        SecondaryPanelSpec(attr_name="graveyard_panel", panel_cls=GraveyardPanel),
        SecondaryPanelSpec(attr_name="genealogy_overlay", panel_cls=GenealogyTreeOverlay),
    ),
    landmark_specs=(
        LandmarkSpec(type_name="campfire", attr="campfires"),
        LandmarkSpec(type_name="storage", attr="storage_fields"),
        LandmarkSpec(type_name="graveyard", attr="graveyards"),
    ),
    extra_object_collections=(
        ExtraObjectCollectionSpec(attr="storage_fields", on_delete=on_delete_storage_field,
                                  can_delete_fn=storage_field_can_delete),
        ExtraObjectCollectionSpec(attr="graveyards", on_delete=on_delete_graveyard),
        ExtraObjectCollectionSpec(attr="construction_sites", on_delete=on_delete_construction_site),
        ExtraObjectCollectionSpec(attr="houses", on_delete=on_delete_house),
        ExtraObjectCollectionSpec(attr="campfires", on_delete=on_delete_campfire),
    ),
    extra_world_save_fn=save_circle_genealogy,
    extra_world_load_fn=load_circle_genealogy,
    biome_cascade_specs=(
        BiomeCascadeSpec(attr="graveyards", clear_on_flood=True, on_removed=on_delete_graveyard),
        BiomeCascadeSpec(attr="storage_fields", clear_on_flood=True, on_removed=on_delete_storage_field),
        BiomeCascadeSpec(attr="houses", clear_on_flood=True, on_removed=on_delete_house),
        BiomeCascadeSpec(attr="campfires", clear_on_flood=True, on_removed=on_delete_campfire),
    ),
    mouse_down_hooks=(circle_handle_relationships_scrollbar_down,),
    mouse_up_hooks=(circle_handle_relationships_scrollbar_up,),
    mouse_motion_hooks=(circle_handle_relationships_scrollbar_motion,),
    mouse_wheel_hooks=(circle_handle_relationships_wheel,),
    instruction_title=CIRCLE_INSTRUCTION_TITLE,
    instruction_sections=CIRCLE_INSTRUCTION_SECTIONS,
    instruction_preview_icon=CIRCLE_INSTRUCTION_PREVIEW_ICON,
    instruction_icon_factory=circle_instruction_icon,
)