"""ObjectManager - фасад. Логики здесь нет: он создаёт сервисы, связывает их друг с другом
и сохраняет прежние имена методов, которые вызывает остальной проект."""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.race_registry import all_races

from .animals import AnimalService
from .biome_paint import BiomePainter
from .generation import WorldGenerator
from .growth import NaturalGrowth
from .lookup import ObjectLookup
from .object_placement import PlacementService
from .object_types import type_of_instance
from .removal import CoreClear, ObjectRemover
from .roads import RoadNetworkService

if TYPE_CHECKING:
    from game.game import Game

class ObjectManager:

    def __init__(self, game: Game):
        self.game = game

        # ---------- Менеджеры спавна рас (их ищут по имени расы: spawn_managers["circle"]) ----------
        self.spawn_managers = {
            descriptor.race_name: descriptor.spawn_manager_cls(game, descriptor)
            for descriptor in all_races()
            if descriptor.spawn_manager_cls is not None
        }

        # ---------- Сервисы. Каждому - только то, что ему реально нужно ----------
        self.placement = PlacementService(game)
        self.roads = RoadNetworkService(game)
        self.animals = AnimalService(game)
        self.remover = ObjectRemover(game, self.roads, self.animals)
        self.lookup = ObjectLookup(game)
        self.growth = NaturalGrowth(game, self.placement)
        self.generator = WorldGenerator(game, self.placement, self)
        self.biome_painter = BiomePainter(game, self.remover, self.roads)

    # ---------- Размещение ----------

    def start_placement(self, obj_type):
        self.placement.start(obj_type)

    def stop_placement(self):
        self.placement.stop()

    def place_object(self, wx, wy):
        self.placement.place(wx, wy)

    def check_creature_placement_valid(self, wx, wy, index=None):
        return self.placement.creature_position_valid(wx, wy, index=index)

    def check_object_placement_valid(self, wx, wy, obj_type=None, exclude=None, index=None):
        return self.placement.object_position_valid(wx, wy, obj_type=obj_type, exclude=exclude, index=index)

    # ---------- Генерация мира ----------

    def generate_initial_resources(self, seed):
        self.generator.generate_resources(seed)

    def generate_initial_animals(self, seed):
        self.generator.generate_animals(seed)

    # ---------- Естественный рост ----------

    def try_spawn_fruit_near_bush(self, bush):
        self.growth.try_spawn_fruit_near_bush(bush)

    def try_natural_tree_growth(self):
        self.growth.try_grow("tree")

    def try_natural_bush_growth(self):
        self.growth.try_grow("bush")

    def try_natural_stone_growth(self):
        self.growth.try_grow("stone")

    def try_natural_grass_growth(self):
        self.growth.try_grow("grass")

    # ---------- Биомы и расчистка территории ----------

    def paint_biome(self, wx, wy, biome_type, radius, bump_version=True):
        self.biome_painter.paint(wx, wy, biome_type, radius, bump_version=bump_version)

    def clear_core_objects_in_zone(self, in_zone_fn, clear_fruits=True, clear_spikes=True,
                                   clear_water=True, clear_bushes=True,
                                   clear_trees=True, clear_stones=True, clear_grass=False):
        """Публичный хелпер для рас: чистит только коллекции ЯДРА в зоне."""
        self.remover.clear_in_zone(in_zone_fn, CoreClear(
            fruits=clear_fruits, spikes=clear_spikes, water=clear_water, bushes=clear_bushes,
            trees=clear_trees, stones=clear_stones, grass=clear_grass))

    # ---------- Дороги ----------

    def create_road_instance(self, obj_type):
        return self.roads.create_road(obj_type)

    def finalize_drawn_road(self, obj_type, road):
        self.roads.finalize_drawn(obj_type, road)

    def register_crossings(self, obj_type, new_road):
        self.roads.register_crossings(obj_type, new_road)

    def cleanup_crossings_for(self, obj_type, road_id):
        self.roads.cleanup_crossings_for(obj_type, road_id)

    def snap_to_existing(self, wx, wy, obj_type, tolerance=None, self_points=None):
        return self.roads.snap(wx, wy, obj_type, tolerance=tolerance, self_points=self_points)

    def link_road_endpoints(self, road):
        self.roads.link_endpoints(road)

    def resolve_road_endpoint(self, endpoint):
        return self.roads.resolve_endpoint(endpoint)

    def unlink_road_endpoints(self, obj_type, obj_id):
        self.roads.unlink_endpoints(obj_type, obj_id)

    # ---------- Поиск ----------

    def find_creature_at(self, wx, wy):
        return self.lookup.creature_at(wx, wy)

    def find_favorite_target_at(self, wx, wy):
        return self.lookup.favorite_target_at(wx, wy)

    def find_object_at(self, wx, wy):
        return self.lookup.object_at(wx, wy)

    def find_secondary_panel_target(self, obj):
        return self.lookup.secondary_panel_target(obj)

    def resolve_obj_type_for_instance(self, obj):
        return type_of_instance(obj)

    # ---------- Удаление ----------

    def delete_object(self, obj):
        self.remover.delete(obj)

    def remove_animal_and_drop(self, animal):
        return self.animals.remove_with_drops(animal)

    def remove_animal_silently(self, animal):
        return self.animals.remove_silently(animal)