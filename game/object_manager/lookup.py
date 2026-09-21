"""Поиск: что находится под курсором."""

import math

from game.race_registry import (
    CORE_ROAD_NETWORK, all_races, all_road_networks, all_extra_object_collections,
)
from creatures.all_needed.geometry import point_segment_distance, distance_to_footprint
from game.animal_registry import all_animals
from . import object_settings as cfg
from .object_types import animal_collections, animal_drop_attrs

# Круглые объекты ядра в порядке приоритета при клике
_CORE_CIRCULAR_ATTRS = (
    "fruits", "spikes", "water_puddles", "bushes", "trees", "stones", "grass", "meats",
)

class ObjectLookup:

    def __init__(self, game):
        self.game = game

    # =====================================================================
    # Существа
    # =====================================================================

    @staticmethod
    def _is_hidden(creature):
        # Живое существо внутри своего дома на поле не рисуется и выбраться кликом не должно
        # (at_home - признак расы "Круг"; убрать его из ядра можно свойством в LivingEntity)
        return not creature.is_dead and getattr(creature, "at_home", False)

    def creature_at(self, wx, wy):
        best, best_dist = None, cfg.CREATURE_PICK_RADIUS
        for creature in self.game.world.creatures:
            if self._is_hidden(creature):
                continue
            dist = math.hypot(wx - creature.x, wy - creature.y)
            if dist <= best_dist:
                best, best_dist = creature, dist
        return best

    def favorite_target_at(self, wx, wy):
        """Кого можно назначить Избранным: существо или живое животное."""
        creature = self.creature_at(wx, wy)
        if creature is not None:
            return creature
        best, best_dist = None, cfg.CREATURE_PICK_RADIUS
        for descriptor in all_animals():
            for animal in getattr(self.game.world, descriptor.world_collection):
                if animal.hp <= 0:
                    continue
                dist = math.hypot(wx - animal.x, wy - animal.y)
                if dist <= best_dist:
                    best, best_dist = animal, dist
        return best

    # =====================================================================
    # Объекты
    # =====================================================================

    def object_at(self, wx, wy):
        world = self.game.world

        # 1. трупы
        for creature in world.creatures:
            if creature.is_dead and self._hits_circle(creature, wx, wy):
                return creature

        # 2. круглые объекты ядра, животные и их дропы
        for attr, collection in self._circular_collections():
            for obj in collection:
                if attr == "fruits" and not obj.active:
                    continue
                if self._hits_circle(obj, wx, wy):
                    return obj

        # 3. точечные объекты рас (склад, кладбище, стройплощадка, дом, костёр)
        for spec in all_extra_object_collections():
            for obj in getattr(world, spec.attr):
                if distance_to_footprint(obj, wx, wy) <= spec.hit_margin:
                    return obj

        # 4. дороги рас, затем стены/заборы, затем обычные дороги (они самые "тонкие")
        for spec in all_road_networks():
            if spec is not CORE_ROAD_NETWORK:
                hit = self._first_polyline_hit(getattr(world, spec.road_collection), wx, wy)
                if hit is not None:
                    return hit
        for collection in (world.walls, world.fences):
            hit = self._first_polyline_hit(collection, wx, wy)
            if hit is not None:
                return hit
        return self._first_polyline_hit(getattr(world, CORE_ROAD_NETWORK.road_collection), wx, wy)

    def _circular_collections(self):
        world = self.game.world
        for attr in _CORE_CIRCULAR_ATTRS + animal_collections() + animal_drop_attrs():
            yield attr, getattr(world, attr)

    @staticmethod
    def _hits_circle(obj, wx, wy):
        return math.hypot(wx - obj.x, wy - obj.y) <= obj.radius + cfg.CIRCLE_PICK_MARGIN

    @staticmethod
    def _first_polyline_hit(collection, wx, wy):
        for obj in collection:
            points = obj.points
            for i in range(len(points) - 1):
                ax, ay = points[i]
                bx, by = points[i + 1]
                if point_segment_distance(wx, wy, ax, ay, bx, by) <= cfg.POLYLINE_PICK_TOLERANCE:
                    return obj
        return None

    def secondary_panel_target(self, obj):
        """attr_name боковой панели, которую нужно открыть при выборе obj, либо None."""
        world = self.game.world
        for descriptor in all_races():
            for spec in descriptor.placeable_objects:
                if spec.secondary_panel_attr is None:
                    continue
                if obj in getattr(world, spec.attr):
                    return spec.secondary_panel_attr
        return None