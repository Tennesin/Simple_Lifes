"""События мира, связанные с объектами и существами расы 'Круг':
- перехват/освобождение схваченного трупа (двойной клик игрока);
- редактирование имени существа;
- реакция на удаление объектов (склад/кладбище/стройплощадка);
- расчистка территории под новую постройку."""

import os
import shutil
import math

from game.object_manager import footprint_radius
from ..ci_info import INFO_CREATURE_GOAL_NAMED
from ..ci_settings import NAME_ASSIGN_RELATIONSHIP_BONUS, GRAVEYARD_BURIAL_DISTANCE

# =========================================================================
# Домен: труп сородича — перехват переноски при двойном клике и передача
# судьбы трупа при отпускании (закапывание или просто "уронил рядом")
# =========================================================================

def start_corpse_grab(corpse, world):
    if corpse.being_carried_by is not None:
        carrier = next((c for c in world.creatures if c.id == corpse.being_carried_by), None)
        if carrier is not None:
            carrier.burial_target_id = None
            carrier.graveyard_target_id = None
            carrier.is_dragging_corpse = False
        corpse.being_carried_by = None
    corpse.burial_claimant_id = None

def handle_corpse_release(corpse, game):
    game.selected_object = None

    target_graveyard = next(
        (g for g in game.world.graveyards
         if g.distance_to_point(corpse.x, corpse.y) < GRAVEYARD_BURIAL_DISTANCE), None)

    if target_graveyard is None:
        game.selected_creature = corpse
        return True

    target_graveyard.bury(corpse)

    for bush in game.world.bushes:
        if getattr(bush, "claimed_by", None) == corpse.id:
            bush.claimed_by = None
    for water in game.world.water_puddles:
        if getattr(water, "claimed_by", None) == corpse.id:
            water.claimed_by = None

    if game.selected_creature is corpse:
        game.selected_creature = None

    if game.world_path:
        folder_path = os.path.join(game.world_path, "creatures", corpse.id)
        shutil.rmtree(folder_path, ignore_errors=True)

    if corpse in game.world.creatures:
        game.world.creatures.remove(corpse)
    return True

# =========================================================================
# Домен: редактирование имени существа — присвоение бонусов только у "Круга"
# =========================================================================

def apply_name_edit(creature, new_name):
    creature.name = new_name
    if not creature.player_named:
        creature.player_named = True
        creature.player_relationship = max(-100.0, min(100.0,
            creature.player_relationship + NAME_ASSIGN_RELATIONSHIP_BONUS))
        creature.player_reactions.add_memory("named", relationship_after=creature.player_relationship)
        creature.goal_text = INFO_CREATURE_GOAL_NAMED

# =========================================================================
# Домен: on_delete / on_removed колбэки — реакция на исчезновение объекта
# =========================================================================

def on_delete_storage_field(game, field):
    game.object_manager.unlink_road_endpoints("storage", field.id)


def on_delete_graveyard(game, gy):
    game.object_manager.unlink_road_endpoints("graveyard", gy.id)
    pos = (gy.x, gy.y)
    for creature in game.world.creatures:
        creature.on_landmark_removed("graveyard", gy.id, pos)

def on_delete_construction_site(game, site):
    for creature in game.world.creatures:
        if creature.construction_target_id == site.id:
            creature.construction_target_id = None
            creature.construction_phase = None

# =========================================================================
# Домен: расчистка территории под новую постройку
# =========================================================================

def _clear_construction_sites_in_zone(game, in_zone_fn):
    world = game.world
    for site in [s for s in world.construction_sites if in_zone_fn(s)]:
        world.construction_sites.remove(site)
        on_delete_construction_site(game, site)

def cleanup_area_for_new_graveyard(game, gy):
    game.object_manager.clear_core_objects_in_zone(
        lambda obj: gy.distance_to_point(obj.x, obj.y) <= footprint_radius(obj)
    )
    _clear_construction_sites_in_zone(
        game, lambda site: gy.distance_to_point(site.x, site.y) <= footprint_radius(site)
    )

def cleanup_area_for_new_construction(game, obj, radius):
    def _in_zone(other):
        return other is not obj and math.hypot(other.x - obj.x, other.y - obj.y) <= radius + footprint_radius(other)

    game.object_manager.clear_core_objects_in_zone(_in_zone)
    _clear_construction_sites_in_zone(game, _in_zone)