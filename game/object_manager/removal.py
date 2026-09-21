"""Удаление объектов: одного (игрок нажал Del / Ctrl+ЛКМ) и пачкой (зона покраски биома,
расчистка под постройку). Реакция на исчезновение объекта (пересчёт карты проходимости,
отвязка концов дорог, забывание воды существами) описана ОДИН раз - в _after_removed."""

from dataclasses import dataclass

from game.race_registry import (
    all_biome_cascade_specs,
    all_extra_object_collections,
    all_road_networks,
    all_secondary_panel_specs,
)

from .object_types import animal_drop_attrs


@dataclass(frozen=True)
class CoreClear:
    """Какие коллекции ядра чистить при расчистке зоны."""
    fruits: bool = True
    spikes: bool = True
    water: bool = True
    bushes: bool = True
    trees: bool = True
    stones: bool = True
    grass: bool = False

    def attrs(self):
        pairs = (
            ("fruits", self.fruits), ("spikes", self.spikes), ("bushes", self.bushes),
            ("water_puddles", self.water), ("trees", self.trees), ("stones", self.stones),
            ("grass", self.grass),
        )
        return [attr for attr, enabled in pairs if enabled]

# Коллекции, которые игрок может удалить напрямую
_CORE_DELETABLE = (
    "fruits", "spikes", "water_puddles", "bushes", "trees", "stones",
    "walls", "fences", "grass", "meats",
)
# Изменение этих коллекций делает устаревшей карту проходимости
_LANDSCAPE_ATTRS = ("spikes", "walls", "fences")
# Коллекции, на которые могут быть "привязаны" концы дорог: attr -> тип ориентира
_ROAD_LANDMARK_TYPE = {
    "water_puddles": "water", "bushes": "bush", "trees": "tree", "stones": "stone",
}

class ObjectRemover:

    def __init__(self, game, roads, animals):
        self.game = game
        self.roads = roads          # RoadNetworkService
        self.animals = animals      # AnimalService

    # =====================================================================
    # Удаление одного объекта
    # =====================================================================

    def delete(self, obj):
        game = self.game
        world = game.world

        if self.animals.remove_with_drops(obj):
            return

        for spec in all_road_networks():
            collection = getattr(world, spec.road_collection)
            if obj in collection:
                collection.remove(obj)
                self.roads.cleanup_crossings_for(spec.obj_type, obj.id)
                for creature in world.creatures:
                    creature.on_road_deleted(spec.obj_type, obj)
                self._drop_references([obj])
                return

        for attr in _CORE_DELETABLE:
            collection = getattr(world, attr)
            if obj in collection:
                collection.remove(obj)
                self._after_removed(attr, [obj])
                self._drop_references([obj])
                return

        for attr in animal_drop_attrs():
            collection = getattr(world, attr)
            if obj in collection:
                collection.remove(obj)
                self._drop_references([obj])
                return

        for spec in all_extra_object_collections():
            collection = getattr(world, spec.attr)
            if obj in collection:
                if spec.can_delete_fn is not None and not spec.can_delete_fn(game, obj):
                    return
                collection.remove(obj)
                if spec.on_delete is not None:
                    spec.on_delete(game, obj)
                self._drop_references([obj])
                return

    # =====================================================================
    # Расчистка зоны (in_zone_fn(obj) -> bool)
    # =====================================================================

    def clear_in_zone(self, in_zone_fn, what=CoreClear()):
        """Чистит коллекции ЯДРА в зоне. Объекты рас чистит clear_race_objects."""
        world = self.game.world
        removed_total = []
        for attr in what.attrs():
            collection = getattr(world, attr)
            removed = [obj for obj in collection if in_zone_fn(obj)]
            if not removed:
                continue
            removed_ids = {id(obj) for obj in removed}
            setattr(world, attr, [obj for obj in collection if id(obj) not in removed_ids])
            self._after_removed(attr, removed)
            removed_total.extend(removed)
        self._drop_references(removed_total)

    def clear_race_objects(self, in_zone_fn, flood):
        """Чистит объекты рас по их BiomeCascadeSpec. flood=True - море/река, False - пустыня."""
        game = self.game
        removed_total = []
        for spec in all_biome_cascade_specs():
            if not (spec.clear_on_flood if flood else spec.clear_on_desert):
                continue
            collection = getattr(game.world, spec.attr)
            matched = [obj for obj in collection if in_zone_fn(obj)]
            if not matched:
                continue
            matched_ids = {id(obj) for obj in matched}
            setattr(game.world, spec.attr, [obj for obj in collection if id(obj) not in matched_ids])
            if spec.on_removed is not None:
                for obj in matched:
                    spec.on_removed(game, obj)
            removed_total.extend(matched)
        self._drop_references(removed_total)

    # =====================================================================
    # Общие реакции
    # =====================================================================

    def _after_removed(self, attr, removed):
        """removed - список удалённых объектов ОДНОЙ коллекции ядра."""
        world = self.game.world
        if attr in _LANDSCAPE_ATTRS:
            world.landscape_version += 1        # один раз на пачку

        landmark_type = _ROAD_LANDMARK_TYPE.get(attr)
        if landmark_type is not None:
            for obj in removed:
                self.roads.unlink_endpoints(landmark_type, obj.id)

        if attr == "water_puddles":
            for water in removed:
                position = (water.x, water.y)
                for creature in world.creatures:
                    creature.on_landmark_removed("water", water.id, position)

    def _drop_references(self, removed):
        """Убирает удалённые объекты из выделения игрока, руки и боковых панелей,
        чтобы они не оставались висеть на экране."""
        if not removed:
            return
        game = self.game
        removed_ids = {id(obj) for obj in removed}

        if game.selected_object is not None and id(game.selected_object) in removed_ids:
            game.selected_object = None
        grabbed = game.player.grabbed_object
        if grabbed is not None and id(grabbed) in removed_ids:
            game.player.grabbed_object = None

        ui = getattr(game, "ui", None)
        if ui is None:
            return
        for spec in all_secondary_panel_specs():
            panel = getattr(ui, spec.attr_name, None)
            selected = getattr(panel, "selected", None) if panel is not None else None
            if selected is not None and id(selected) in removed_ids:
                panel.clear(game)