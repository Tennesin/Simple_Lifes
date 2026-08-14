"""Точка входа расы 'Круг' для авто-регистрации."""

from objects import RoadCrossing

from game.race_registry import (
    RaceDescriptor, RenderLayer, PlaceableObjectSpec, RoadNetworkSpec,
    MinimapLayer, SecondaryPanelSpec, LandmarkSpec,
    ExtraObjectCollectionSpec, BiomeCascadeSpec,
)
from .mechanics.object_events import (
    on_delete_storage_field, on_delete_graveyard, on_delete_construction_site,
)

from .creature import Creature
from .ci_info import (
    INFO_BTN_CREATE_MALE, INFO_BTN_CREATE_FEMALE, INFO_BTN_GRAVEYARD,
    INFO_BTN_DRAW_CHILD_ROAD, INFO_TOOL_CHILD_ROAD_HINT,
    INFO_SETTINGS_MINIMAP_CONSTRUCTIONS,
)
from .ci_settings import GRAVEYARD_DEFAULT_SIZE, CHILD_ROAD_COLOR_PENDING
from .circle_objects import ChildRoad, StorageField, ConstructionSite, Graveyard

from .mechanics.tick import CircleTickProcessor, tick_circle_world
from .mechanics.creature_lifecycle import (
    CircleSpawnManager, circle_spawn_dispatch,
    save_circle_genealogy, load_circle_genealogy,
)
from .mechanics.panel import (
    CreaturePanel, GraveyardPanel, GenealogyTreeOverlay, circle_object_panel_extra_lines,
)
from .mechanics.creature_lifecycle import load_creature_from_state as load_circle_creature
from .mechanics.render import (
    draw_child_roads, draw_storage_fields, draw_construction_sites, draw_graveyards,
    draw_minimap_child_roads, draw_minimap_constructions,
)

RACE_DESCRIPTOR = RaceDescriptor(
    race_name="circle",
    creature_cls=Creature,
    tick_processor_cls=CircleTickProcessor,
    loader_fn=load_circle_creature,
    panel_cls=CreaturePanel,
    spawn_manager_cls=CircleSpawnManager,
    creature_placement_modes=(
        ("creature_male", INFO_BTN_CREATE_MALE),
        ("creature_female", INFO_BTN_CREATE_FEMALE),
    ),
    spawn_fn=circle_spawn_dispatch,
    world_collections=(
        "child_roads", "child_road_crossings",
        "storage_fields", "construction_sites", "graveyards",
    ),
    persistence_registry=(
        ("child_roads.json", "child_roads", ChildRoad),
        ("storage_fields.json", "storage_fields", StorageField),
        ("construction_sites.json", "construction_sites", ConstructionSite),
        ("graveyards.json", "graveyards", Graveyard),
        ("child_road_crossings.json", "child_road_crossings", RoadCrossing),
    ),
    placeable_objects=(
        PlaceableObjectSpec(
            obj_type="graveyard", attr="graveyards", cls=Graveyard, label=INFO_BTN_GRAVEYARD,
            placement_clearance=GRAVEYARD_DEFAULT_SIZE[0] / 2 + 10,
            secondary_panel_attr="graveyard_panel",
            blocks_creature_spawn=True,
            mutual_clearance_additive=True,
            manually_placeable=False,
        ),
    ),
    render_layers=(
        RenderLayer("child_roads", insert_after="road_crossings", draw_fn=draw_child_roads),
        RenderLayer("storage_fields", insert_after="campfires", draw_fn=draw_storage_fields),
        RenderLayer("construction_sites", insert_after="campfires", draw_fn=draw_construction_sites),
        RenderLayer("graveyards", insert_after="campfires", draw_fn=draw_graveyards),
    ),
    road_networks=(
        RoadNetworkSpec(
            obj_type="child_road", road_collection="child_roads",
            crossing_collection="child_road_crossings",
            verify_fn=lambda road, spikes: road.verify_safety(spikes),
            road_cls=ChildRoad,
            preview_color=CHILD_ROAD_COLOR_PENDING,
            menu_label=INFO_BTN_DRAW_CHILD_ROAD,
            menu_hint=INFO_TOOL_CHILD_ROAD_HINT,
        ),
    ),
    world_tick_fn=tick_circle_world,
    display_checkboxes=(
        ("minimap_show_constructions", INFO_SETTINGS_MINIMAP_CONSTRUCTIONS),
    ),
    minimap_layers=(
        MinimapLayer("child_roads", insert_after="roads", draw_fn=draw_minimap_child_roads),
        MinimapLayer("constructions", insert_after="campfires", draw_fn=draw_minimap_constructions),
    ),
    object_panel_extra_fn=circle_object_panel_extra_lines,
    secondary_panel_specs=(
        SecondaryPanelSpec(attr_name="graveyard_panel", panel_cls=GraveyardPanel),
        SecondaryPanelSpec(attr_name="genealogy_overlay", panel_cls=GenealogyTreeOverlay),
    ),
    landmark_specs=(
        LandmarkSpec(type_name="storage", attr="storage_fields"),
        LandmarkSpec(type_name="graveyard", attr="graveyards"),
    ),
    extra_object_collections=(
        ExtraObjectCollectionSpec(attr="storage_fields", on_delete=on_delete_storage_field),
        ExtraObjectCollectionSpec(attr="graveyards", on_delete=on_delete_graveyard),
        ExtraObjectCollectionSpec(attr="construction_sites", on_delete=on_delete_construction_site),
    ),
    extra_world_save_fn=save_circle_genealogy,
    extra_world_load_fn=load_circle_genealogy,
    biome_cascade_specs=(
        BiomeCascadeSpec(attr="graveyards", clear_on_flood=True, on_removed=on_delete_graveyard),
        BiomeCascadeSpec(attr="storage_fields", clear_on_flood=True, on_removed=on_delete_storage_field),
    ),
)