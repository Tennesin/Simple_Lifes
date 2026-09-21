"""Размещение: режим "поставить объект" и проверки "можно ли здесь стоять"."""

import math

import settings
from game.race_registry import all_road_networks
from creatures.all_needed.geometry import footprint_radius, distance_to_footprint
from . import object_settings as cfg
from .object_types import (
    object_types, create_object, allowed_biomes, placement_clearance, mutual_additive_attrs,
    creature_like_attrs, creature_blocking_attrs, fixed_clearance_attrs, footprint_clearance_attrs,
    ANIMAL_BIOMES, LANDSCAPE_AFFECTING_TYPES,
)
from .spatial import LinearSource

class PlacementService:

    def __init__(self, game):
        self.game = game

    # =====================================================================
    # Режим размещения (кнопка меню -> курсор -> клик)
    # =====================================================================

    def start(self, obj_type):
        game = self.game
        if not game.world_loaded:
            return
        player = game.player
        if player.grabbed_creature is not None:
            # (раньше тут вызывался несуществующий finish_grab() - падение при выборе
            # пункта меню с существом в руке)
            player.grabbed_creature.release_by_player()
            player.grabbed_creature = None
        player.grabbed_object = None
        for spec in all_road_networks():
            setattr(player, f"drawing_{spec.obj_type}", None)
        player.reset_tool()
        game.placement_mode = obj_type
        game.close_all_menus()

    def stop(self):
        game = self.game
        game.placement_mode = None
        game.placement_pos = None

    def place(self, wx, wy):
        game = self.game
        obj_type = game.placement_mode
        entry = object_types().get(obj_type)
        if entry is None:
            return
        attr, _cls = entry
        getattr(game.world, attr).append(create_object(obj_type, wx, wy))
        if obj_type in LANDSCAPE_AFFECTING_TYPES:
            game.world.landscape_version += 1

    # =====================================================================
    # Проверки. index - SpatialIndex (быстро, для массовой генерации) или None
    # =====================================================================

    def creature_position_valid(self, wx, wy, index=None):
        game = self.game
        source = index if index is not None else LinearSource(game)

        if not self._inside_world(wx, wy, cfg.WORLD_EDGE_MARGIN_CREATURE):
            return False
        grid = game.biome_manager.grid
        if grid is not None and grid.get_at(wx, wy) not in ANIMAL_BIOMES:
            return False

        clearance = cfg.CREATURE_CLEARANCE
        for attr in creature_like_attrs():
            for other in source.candidates(attr, wx, wy, clearance):
                if math.hypot(wx - other.x, wy - other.y) < clearance:
                    return False

        for attr in creature_blocking_attrs():
            for obj in source.candidates(attr, wx, wy, cfg.QUERY_MARGIN):
                if distance_to_footprint(obj, wx, wy) < cfg.CREATURE_SPAWN_OBJECT_GAP:
                    return False
        return True

    def object_position_valid(self, wx, wy, obj_type=None, exclude=None, index=None):
        game = self.game
        obj_type = obj_type if obj_type is not None else game.placement_mode
        source = index if index is not None else LinearSource(game)

        if not self._inside_world(wx, wy, cfg.WORLD_EDGE_MARGIN_OBJECT):
            return False
        if not self.biome_allows(wx, wy, obj_type):
            return False

        clearance = placement_clearance(obj_type)

        # ---------- Фиксированная дистанция: фрукты, шипы, существа, животные ----------
        fixed_radius = max(cfg.FIXED_CLEARANCE_MIN, clearance)
        for attr in fixed_clearance_attrs():
            for obj in source.candidates(attr, wx, wy, fixed_radius):
                if obj is exclude:
                    continue
                if attr == "fruits" and not obj.active:
                    continue
                if math.hypot(wx - obj.x, wy - obj.y) < fixed_radius:
                    return False

        # ---------- Дистанция по занимаемому месту: всё остальное ----------
        additive_attrs = mutual_additive_attrs()
        search_radius = clearance + cfg.QUERY_MARGIN
        for attr in footprint_clearance_attrs():
            additive = attr in additive_attrs
            for obj in source.candidates(attr, wx, wy, search_radius):
                if obj is exclude:
                    continue
                own_clearance = footprint_radius(obj) + cfg.FOOTPRINT_EXTRA_GAP
                required = (own_clearance + clearance) if additive else max(own_clearance, clearance)
                if distance_to_footprint(obj, wx, wy) < required:
                    return False
        return True

    def biome_allows(self, wx, wy, obj_type):
        grid = self.game.biome_manager.grid
        if grid is None:
            return True
        return grid.get_at(wx, wy) in allowed_biomes(obj_type)

    @staticmethod
    def _inside_world(x, y, margin):
        return (margin <= x <= settings.WORLD_WIDTH - margin
                and margin <= y <= settings.WORLD_HEIGHT - margin)