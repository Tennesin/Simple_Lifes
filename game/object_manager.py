from __future__ import annotations
import math
import random
import settings
from creatures.all_needed import geometry
from typing import TYPE_CHECKING
from game.race_registry import (
    all_races, all_road_networks, all_landmark_specs,
    all_extra_object_collections, all_biome_cascade_specs,
)

if TYPE_CHECKING:
    from .game import Game
from objects import (
    Fruit, Spike, WaterPuddle, Bush, Campfire,
    RoadCrossing, Tree, Stone
)
from settings import *


def _segment_intersection(p1, p2, p3, p4):
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-9:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u = ((x1 - x3) * (y1 - y2) - (y1 - y3) * (x1 - x2)) / denom
    if 0.02 <= t <= 0.98 and 0.02 <= u <= 0.98:
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
    return None


# =========================================================================
# Универсальная геометрия "занимаемого места" объекта.
# =========================================================================

def footprint_radius(obj):
    if hasattr(obj, "radius"):
        return obj.radius
    if hasattr(obj, "width") and hasattr(obj, "height"):
        return max(obj.width, obj.height) / 2
    return 0

def distance_to_footprint(obj, px, py):
    if hasattr(obj, "distance_to_point"):
        return obj.distance_to_point(px, py)
    return max(0.0, math.hypot(px - obj.x, py - obj.y) - footprint_radius(obj))


# =========================================================================
# Аналог _WORLD_OBJECT_REGISTRY из game/world_manager.py.
# =========================================================================

_CORE_OBJECT_TYPE_REGISTRY = {
    "fruit": ("fruits", Fruit),
    "spike": ("spikes", Spike),
    "water": ("water_puddles", WaterPuddle),
    "bush": ("bushes", Bush),
    "campfire": ("campfires", Campfire),
    "tree": ("trees", Tree),
    "stone": ("stones", Stone),
}

def _build_object_type_registry():
    registry = dict(_CORE_OBJECT_TYPE_REGISTRY)
    for descriptor in all_races():
        for spec in descriptor.placeable_objects:
            registry[spec.obj_type] = (spec.attr, spec.cls)
    return registry

_OBJECT_TYPE_REGISTRY = _build_object_type_registry()


def _build_placement_clearance_registry():
    registry = {}
    for descriptor in all_races():
        for spec in descriptor.placeable_objects:
            if spec.placement_clearance is not None:
                registry[spec.obj_type] = spec.placement_clearance
    return registry

_PLACEMENT_CLEARANCE_REGISTRY = _build_placement_clearance_registry()


def _build_mutual_clearance_additive_attrs():
    registry = set()
    for descriptor in all_races():
        for spec in descriptor.placeable_objects:
            if spec.mutual_clearance_additive:
                registry.add(spec.attr)
    return registry

_MUTUAL_CLEARANCE_ADDITIVE_ATTRS = _build_mutual_clearance_additive_attrs()

# ---------- Коллекции, у которых клиренс всегда фиксированный (не по footprint) ----------
_FIXED_CLEARANCE_ATTRS = {"fruits", "spikes", "creatures"}

# ---------- Типы, при появлении/исчезновении которых нужно бампать landscape_version (влияет на nav-сетку) ----------
_LANDSCAPE_VERSION_BUMP_TYPES = ("spike",)


# =========================================================================
# Домен: размещение объектов игроком (курсор/кнопки меню) + валидность.
# =========================================================================

class _PlacementMixin:
    game: "Game"

    def start_placement(self, obj_type):
        game = self.game
        if not game.world_loaded:
            return
        if game.player.grabbed_creature is not None:
            game.player.grabbed_creature.finish_grab()
            game.player.grabbed_creature = None
        game.player.grabbed_object = None
        for spec in all_road_networks():
            setattr(game.player, f"drawing_{spec.obj_type}", None)
        game.player.reset_tool()
        game.placement_mode = obj_type
        game.close_all_menus()

    def stop_placement(self):
        game = self.game
        game.placement_mode = None
        game.placement_pos = None

    def place_object(self, wx, wy):
        game = self.game
        entry = _OBJECT_TYPE_REGISTRY.get(game.placement_mode)
        if entry is None:
            return
        attr, cls = entry
        getattr(game.world, attr).append(cls(wx, wy))
        if game.placement_mode in _LANDSCAPE_VERSION_BUMP_TYPES:
            game.world.landscape_version += 1

    def check_creature_placement_valid(self, wx, wy):
        game = self.game
        if wx < 20 or wx > settings.WORLD_WIDTH - 20 or wy < 20 or wy > settings.WORLD_HEIGHT - 20:
            return False
        if (game.biome_manager.grid is not None
                and game.biome_manager.grid.get_at(wx, wy) == BIOME_SEA):
            return False
        for c in game.world.creatures:
            if math.hypot(wx - c.x, wy - c.y) < 30:
                return False
        for water in game.world.water_puddles:
            if math.hypot(wx - water.x, wy - water.y) < water.radius + 20:
                return False
        for bush in game.world.bushes:
            if math.hypot(wx - bush.x, wy - bush.y) < bush.radius + 20:
                return False
        for fire in game.world.campfires:
            if math.hypot(wx - fire.x, wy - fire.y) < fire.radius + 20:
                return False
        # ---------- Расовые объекты, помеченные как "мешают спавну существа" ----------
        for descriptor in all_races():
            for spec in descriptor.placeable_objects:
                if not spec.blocks_creature_spawn:
                    continue
                for obj in getattr(game.world, spec.attr):
                    if distance_to_footprint(obj, wx, wy) < 20:
                        return False
        return True

    def check_object_placement_valid(self, wx, wy, obj_type=None):
        game = self.game
        obj_type = obj_type if obj_type is not None else game.placement_mode

        if wx < 10 or wx > settings.WORLD_WIDTH - 10 or wy < 10 or wy > settings.WORLD_HEIGHT - 10:
            return False

        if game.biome_manager.grid is not None:
            biome = game.biome_manager.grid.get_at(wx, wy)
            if obj_type == "stone":
                if biome == BIOME_SEA:
                    return False
            else:
                if biome in (BIOME_RIVER, BIOME_SEA):
                    return False
                if obj_type in ("water", "bush") and biome == BIOME_DESERT:
                    return False
                if obj_type == "tree" and biome != BIOME_PLAINS:
                    return False

        clearance = _PLACEMENT_CLEARANCE_REGISTRY.get(obj_type, 0)

        fixed_clearance_collections = (
            [f for f in game.world.fruits if f.active],
            game.world.spikes,
            game.world.creatures,
        )
        for collection in fixed_clearance_collections:
            for obj in collection:
                if math.hypot(wx - obj.x, wy - obj.y) < max(20, clearance):
                    return False

        # ---------- Единый проход по ВСЕМ зарегистрированным типам объектов
        # (core: вода/куст/костёр/дерево/камень + расовые placeable_objects,
        # например кладбище) - никакой расы тут по имени не знаем. ----------
        for other_attr, _other_cls in _OBJECT_TYPE_REGISTRY.values():
            if other_attr in _FIXED_CLEARANCE_ATTRS:
                continue
            additive = other_attr in _MUTUAL_CLEARANCE_ADDITIVE_ATTRS
            for obj in getattr(game.world, other_attr):
                own_clearance = footprint_radius(obj) + 15
                required = (own_clearance + clearance) if additive else max(own_clearance, clearance)
                if distance_to_footprint(obj, wx, wy) < required:
                    return False

        return True


# =========================================================================
# Домен: первичное наполнение только что созданного мира ресурсами (core-only)
# =========================================================================

class _InitialResourceMixin(_PlacementMixin):

    def generate_initial_resources(self, seed):
        game = self.game
        rng = random.Random(seed ^ 0x5BD1E995)

        area_ratio = (settings.WORLD_WIDTH * settings.WORLD_HEIGHT) / INITIAL_RESOURCE_BASE_WORLD_AREA
        area_ratio = max(0.1, area_ratio)

        self._scatter_initial_objects(rng, int(INITIAL_TREE_COUNT * area_ratio), "tree")
        self._scatter_initial_objects(rng, int(INITIAL_BUSH_COUNT * area_ratio), "bush")
        self._scatter_initial_objects(rng, int(INITIAL_STONE_COUNT * area_ratio), "stone")
        self._scatter_initial_objects(rng, int(INITIAL_SPIKE_COUNT * area_ratio), "spike")

    def _scatter_initial_objects(self, rng, count, obj_type):
        game = self.game
        if count <= 0:
            return
        attr, cls = _OBJECT_TYPE_REGISTRY[obj_type]
        collection = getattr(game.world, attr)

        placed = 0
        attempts = 0
        attempts_limit = max(50, count * 25)
        while placed < count and attempts < attempts_limit:
            attempts += 1
            wx = rng.uniform(20, settings.WORLD_WIDTH - 20)
            wy = rng.uniform(20, settings.WORLD_HEIGHT - 20)
            if not self.check_object_placement_valid(wx, wy, obj_type=obj_type):
                continue
            collection.append(cls(wx, wy))
            placed += 1

        if obj_type in _LANDSCAPE_VERSION_BUMP_TYPES and placed > 0:
            game.world.landscape_version += 1


# =========================================================================
# Домен: естественный рост деревьев/кустов/камней и появление фруктов (core-only)
# =========================================================================

_GROWTH_RULES = {
    "tree": (TREE_MAX_TOTAL, lambda biome: biome == BIOME_PLAINS),
    "bush": (BUSH_MAX_TOTAL, lambda biome: biome == BIOME_PLAINS),
    "stone": (STONE_MAX_TOTAL, lambda biome: biome != BIOME_SEA),
}

class _NaturalGrowthMixin(_PlacementMixin):

    def try_spawn_fruit_near_bush(self, bush):
        game = self.game
        nearby_fruits = sum(
            1 for f in game.world.fruits
            if f.active and math.hypot(f.x - bush.x, f.y - bush.y) < BUSH_SPAWN_RADIUS
        )
        if nearby_fruits >= BUSH_MAX_NEARBY_FRUITS:
            return
        for _ in range(BUSH_SPAWN_ATTEMPTS):
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(bush.radius + 10, BUSH_SPAWN_RADIUS)
            wx = bush.x + math.cos(angle) * dist
            wy = bush.y + math.sin(angle) * dist
            if self.check_object_placement_valid(wx, wy, obj_type="fruit"):
                game.world.fruits.append(Fruit(wx, wy))
                return

    def _try_natural_growth(self, obj_type):
        game = self.game
        grid = game.biome_manager.grid
        if grid is None:
            return

        attr, cls = _OBJECT_TYPE_REGISTRY[obj_type]
        max_total, biome_allowed = _GROWTH_RULES[obj_type]
        collection = getattr(game.world, attr)
        if len(collection) >= max_total:
            return

        for _ in range(NATURAL_SPAWN_ATTEMPTS):
            wx = random.uniform(20, settings.WORLD_WIDTH - 20)
            wy = random.uniform(20, settings.WORLD_HEIGHT - 20)
            if not biome_allowed(grid.get_at(wx, wy)):
                continue
            if self.check_object_placement_valid(wx, wy, obj_type=obj_type):
                collection.append(cls(wx, wy))
                return

    def try_natural_tree_growth(self):
        self._try_natural_growth("tree")

    def try_natural_bush_growth(self):
        self._try_natural_growth("bush")

    def try_natural_stone_growth(self):
        self._try_natural_growth("stone")


# =========================================================================
# Домен: покраска биома + каскадное уничтожение/расчистка территории
# =========================================================================

class _BiomeCascadeMixin:
    game: "Game"

    def paint_biome(self, wx, wy, biome_type, radius, bump_version=True):
        game = self.game
        if game.biome_manager.grid is None:
            return
        game.biome_manager.paint(wx, wy, biome_type, radius)
        if bump_version:
            game.world.landscape_version += 1
        self._destroy_objects_invalidated_by_biome_change(wx, wy, radius, biome_type)

    def clear_core_objects_in_zone(self, in_zone_fn, clear_fruits=True, clear_spikes=True,
                                    clear_water=True, clear_bushes=True, clear_campfires=True,
                                    clear_trees=True, clear_stones=True):
        """Публичный generic-хелпер: чистит только CORE-коллекции."""
        game = self.game
        world = game.world

        if clear_fruits:
            world.fruits = [f for f in world.fruits if not in_zone_fn(f)]

        if clear_spikes:
            flooded_spikes = [s for s in world.spikes if in_zone_fn(s)]
            if flooded_spikes:
                world.spikes = [s for s in world.spikes if not in_zone_fn(s)]
                world.landscape_version += 1

        if clear_bushes:
            for bush in [b for b in world.bushes if in_zone_fn(b)]:
                world.bushes.remove(bush)
                self.unlink_road_endpoints("bush", bush.id)

        if clear_campfires:
            for fire in [f for f in world.campfires if in_zone_fn(f)]:
                world.campfires.remove(fire)
                self.unlink_road_endpoints("campfire", fire.id)
                self._cleanup_campfire_references(fire)

        if clear_water:
            world.water_puddles = [w for w in world.water_puddles if not in_zone_fn(w)]

        if clear_trees:
            world.trees = [t for t in world.trees if not in_zone_fn(t)]

        if clear_stones:
            world.stones = [s for s in world.stones if not in_zone_fn(s)]

    def _clear_race_cascade_objects(self, in_zone_fn, flood):
        game = self.game
        for spec in all_biome_cascade_specs():
            should_clear = spec.clear_on_flood if flood else spec.clear_on_desert
            if not should_clear:
                continue
            collection = getattr(game.world, spec.attr)
            matched = [obj for obj in collection if in_zone_fn(obj)]
            if not matched:
                continue
            setattr(game.world, spec.attr, [obj for obj in collection if obj not in matched])
            if spec.on_removed is not None:
                for obj in matched:
                    spec.on_removed(game, obj)

    def _flood_road_network(self, spec, point_in_flood_zone_fn):
        game = self.game
        for road in getattr(game.world, spec.road_collection):
            if any(point_in_flood_zone_fn(px, py) for px, py in road.points):
                road.rating = "dangerous"
                for creature in game.world.creatures:
                    creature.on_road_deleted(spec.obj_type, road)

    def _destroy_objects_invalidated_by_biome_change(self, wx, wy, radius, biome_type):
        def _in_flood_zone(obj):
            return math.hypot(obj.x - wx, obj.y - wy) <= radius

        def _point_in_flood_zone(px, py):
            return math.hypot(px - wx, py - wy) <= radius

        if biome_type in (BIOME_RIVER, BIOME_SEA):
            self.clear_core_objects_in_zone(_in_flood_zone, clear_stones=(biome_type == BIOME_SEA))
            self._clear_race_cascade_objects(_in_flood_zone, flood=True)
            for spec in all_road_networks():
                self._flood_road_network(spec, _point_in_flood_zone)

        elif biome_type == BIOME_DESERT:
            self.clear_core_objects_in_zone(
                _in_flood_zone,
                clear_fruits=False, clear_spikes=False, clear_campfires=False, clear_stones=False,
            )
            self._clear_race_cascade_objects(_in_flood_zone, flood=False)

    def _cleanup_campfire_references(self, fire):
        game = self.game
        fire_pos = (fire.x, fire.y)
        for creature in game.world.creatures:
            creature.on_landmark_removed("campfire", fire.id, fire_pos)


# =========================================================================
# Домен: дорожная сеть - привязка к ориентирам, перекрёстки, "примагничивание"
# =========================================================================

class _RoadNetworkMixin:
    game: "Game"

    SELF_SNAP_EXCLUDE_RECENT_POINTS = 3

    _CORE_LANDMARK_TYPES = (
        ("campfire", "campfires"),
        ("water", "water_puddles"),
        ("bush", "bushes"),
    )

    def _network_spec(self, obj_type):
        for spec in all_road_networks():
            if spec.obj_type == obj_type:
                return spec
        raise KeyError(f"Неизвестная дорожная сеть: {obj_type}")

    def create_road_instance(self, obj_type):
        spec = self._network_spec(obj_type)
        if spec.road_cls is None:
            raise KeyError(f"Дорожная сеть '{obj_type}' не зарегистрировала road_cls")
        return spec.road_cls()

    def link_road_endpoints(self, road):
        if not road.points:
            return
        road.endpoint_a = self._find_landmark_endpoint(*road.points[0])
        road.endpoint_b = self._find_landmark_endpoint(*road.points[-1])

    def finalize_drawn_road(self, obj_type, road):
        spec = self._network_spec(obj_type)
        if len(road.points) < 2:
            return
        last_x, last_y = road.points[-1]
        road.points[-1] = self.snap_to_existing(
            last_x, last_y, obj_type, self_points=road.points[:-1])
        if obj_type == "road":
            self.link_road_endpoints(road)
        self.register_crossings(obj_type, road)
        getattr(self.game.world, spec.road_collection).append(road)

    def register_crossings(self, obj_type, new_road):
        spec = self._network_spec(obj_type)
        other_roads = getattr(self.game.world, spec.road_collection)
        found = []
        for other_road in other_roads:
            if other_road is new_road or len(other_road.points) < 2:
                continue
            for ni in range(len(new_road.points) - 1):
                a1, a2 = new_road.points[ni], new_road.points[ni + 1]
                for oi in range(len(other_road.points) - 1):
                    b1, b2 = other_road.points[oi], other_road.points[oi + 1]
                    point = _segment_intersection(a1, a2, b1, b2)
                    if point is not None:
                        found.append((point, other_road, oi, ni))

        found.sort(key=lambda item: item[3], reverse=True)
        for point, other_road, other_seg_index, new_seg_index in found:
            crossing = self._find_or_create_crossing(spec.crossing_collection, point)
            self._insert_crossing_point(obj_type, new_road, new_seg_index, point)
            crossing.road_ids.add(new_road.id)
            crossing.road_ids.add(other_road.id)

        by_other_road = {}
        for point, other_road, other_seg_index, new_seg_index in found:
            by_other_road.setdefault(other_road, []).append((other_seg_index, point))
        for other_road, entries in by_other_road.items():
            entries.sort(key=lambda item: item[0], reverse=True)
            for other_seg_index, point in entries:
                self._insert_crossing_point(obj_type, other_road, other_seg_index, point)

    def _find_or_create_crossing(self, crossing_collection_name, point):
        collection = getattr(self.game.world, crossing_collection_name)
        for crossing in collection:
            if math.hypot(crossing.x - point[0], crossing.y - point[1]) < CROSSING_MERGE_RADIUS:
                return crossing
        crossing = RoadCrossing(point[0], point[1])
        collection.append(crossing)
        return crossing

    def _insert_crossing_point(self, obj_type, road, seg_index, point, tolerance=6):
        p1 = road.points[seg_index]
        p2 = road.points[seg_index + 1]
        if math.hypot(point[0] - p1[0], point[1] - p1[1]) < tolerance:
            return
        if math.hypot(point[0] - p2[0], point[1] - p2[1]) < tolerance:
            return
        road.points.insert(seg_index + 1, point)
        road._bounds_cache = None
        self._shift_followers(obj_type, road, seg_index + 1)

    def _shift_followers(self, obj_type, road, inserted_index):
        for creature in self.game.world.creatures:
            creature.on_road_progress_shift(obj_type, road, inserted_index)

    def cleanup_crossings_for(self, obj_type, road_id):
        spec = self._network_spec(obj_type)
        world = self.game.world
        remaining = []
        for crossing in getattr(world, spec.crossing_collection):
            crossing.road_ids.discard(road_id)
            if len(crossing.road_ids) >= 2:
                remaining.append(crossing)
        setattr(world, spec.crossing_collection, remaining)

    def verify_road_safety(self, road, obj_type="child_road"):
        spec = self._network_spec(obj_type)
        game = self.game
        candidates = [c for c in game.world.creatures
                     if not c.is_dead and c.can_verify_child_road_safety()]
        checker = random.choice(candidates) if candidates else None
        road.checked_by = checker.id if checker else None

        if spec.verify_fn is None:
            road.rating = "safe"
            return
        is_safe = spec.verify_fn(road, game.world.spikes)
        road.rating = "safe" if is_safe else "dangerous"

    def snap_to_existing(self, wx, wy, obj_type, tolerance=LANDSCAPE_SNAP_TOLERANCE, self_points=None):
        game = self.game
        network_collections = {spec.obj_type: spec.road_collection for spec in all_road_networks()}
        if obj_type in network_collections:
            collection = getattr(game.world, network_collections[obj_type])
        elif obj_type == "wall":
            collection = game.world.walls
        elif obj_type == "fence":
            collection = game.world.fences
        else:
            return (wx, wy)

        best_point = None
        best_dist = tolerance

        def _consider_points(points):
            nonlocal best_point, best_dist
            if not points:
                return
            if len(points) == 1:
                px, py = points[0]
                d = math.hypot(wx - px, wy - py)
                if d < best_dist:
                    best_dist = d
                    best_point = (px, py)
                return
            for i in range(len(points) - 1):
                ax, ay = points[i]
                bx, by = points[i + 1]
                cx, cy = geometry.closest_point_on_segment(wx, wy, ax, ay, bx, by)
                d = math.hypot(wx - cx, wy - cy)
                if d < best_dist:
                    best_dist = d
                    best_point = (cx, cy)

        for obj in collection:
            _consider_points(obj.points)

        if self_points:
            safe_points = (self_points[:-self.SELF_SNAP_EXCLUDE_RECENT_POINTS]
                           if len(self_points) > self.SELF_SNAP_EXCLUDE_RECENT_POINTS else [])
            _consider_points(safe_points)

        return best_point if best_point is not None else (wx, wy)

    def _landmark_registry(self):
        game = self.game
        entries = [(type_name, getattr(game.world, attr)) for type_name, attr in self._CORE_LANDMARK_TYPES]
        for spec in all_landmark_specs():
            entries.append((spec.type_name, getattr(game.world, spec.attr)))
        return entries

    def _find_landmark_endpoint(self, wx, wy):
        margin = ROAD_ENDPOINT_LINK_MARGIN
        for etype, collection in self._landmark_registry():
            for obj in collection:
                if distance_to_footprint(obj, wx, wy) <= margin:
                    return {"type": etype, "obj_id": obj.id}
        return None

    def resolve_road_endpoint(self, endpoint):
        if endpoint is None:
            return None
        etype, obj_id = endpoint.get("type"), endpoint.get("obj_id")
        for reg_type, collection in self._landmark_registry():
            if reg_type == etype:
                return next((o for o in collection if o.id == obj_id), None)
        return None

    def unlink_road_endpoints(self, obj_type, obj_id):
        for road in self.game.world.roads:
            if road.endpoint_a and road.endpoint_a.get("type") == obj_type and road.endpoint_a.get("obj_id") == obj_id:
                road.endpoint_a = None
            if road.endpoint_b and road.endpoint_b.get("type") == obj_type and road.endpoint_b.get("obj_id") == obj_id:
                road.endpoint_b = None


# =========================================================================
# Домен: поиск объекта под курсором и его удаление
# =========================================================================

class _LookupMixin(_RoadNetworkMixin, _BiomeCascadeMixin):
    game: "Game"

    _CORE_DELETE_HANDLERS = (
        ("fruits", None),
        ("spikes", "_on_delete_spike"),
        ("water_puddles", "_on_delete_water"),
        ("bushes", "_on_delete_bush"),
        ("trees", None),
        ("stones", None),
        ("campfires", "_on_delete_campfire"),
        ("walls", "_on_delete_wall"),
        ("fences", "_on_delete_fence"),
    )

    def find_creature_at(self, wx, wy):
        best = None
        best_dist = 14
        for creature in self.game.world.creatures:
            dist = math.hypot(wx - creature.x, wy - creature.y)
            if dist <= best_dist:
                best = creature
                best_dist = dist
        return best

    def find_object_at(self, wx, wy):
        game = self.game

        def _circle_hit(obj, extra=6):
            return math.hypot(wx - obj.x, wy - obj.y) <= obj.radius + extra

        def _polyline_hit(obj, tolerance=8):
            for i in range(len(obj.points) - 1):
                ax, ay = obj.points[i]
                bx, by = obj.points[i + 1]
                if geometry.point_segment_distance(wx, wy, ax, ay, bx, by) <= tolerance:
                    return True
            return False

        for creature in game.world.creatures:
            if creature.is_dead and _circle_hit(creature):
                return creature

        circle_checks = (
            (game.world.fruits, lambda f: f.active and _circle_hit(f)),
            (game.world.spikes, _circle_hit),
            (game.world.water_puddles, _circle_hit),
            (game.world.bushes, _circle_hit),
            (game.world.campfires, _circle_hit),
            (game.world.trees, _circle_hit),
            (game.world.stones, _circle_hit),
        )
        for collection, check in circle_checks:
            for obj in collection:
                if check(obj):
                    return obj

        # ---------- Расовые "точечные" объекты (склад/кладбище/стройплощадка и т.п.) ----------
        for spec in all_extra_object_collections():
            for obj in getattr(game.world, spec.attr):
                if distance_to_footprint(obj, wx, wy) <= spec.hit_margin:
                    return obj

        race_road_specs = [s for s in all_road_networks() if s.obj_type != "road"]
        core_road_specs = [s for s in all_road_networks() if s.obj_type == "road"]

        for spec in race_road_specs:
            for obj in getattr(game.world, spec.road_collection):
                if _polyline_hit(obj):
                    return obj

        for collection in (game.world.walls, game.world.fences):
            for obj in collection:
                if _polyline_hit(obj):
                    return obj

        for spec in core_road_specs:
            for road in getattr(game.world, spec.road_collection):
                if _polyline_hit(road):
                    return road

        return None

    def find_secondary_panel_target(self, obj):
        """attr_name вторичной панели, которую нужно открыть при выборе obj, либо None."""
        game = self.game
        for descriptor in all_races():
            for spec in descriptor.placeable_objects:
                if spec.secondary_panel_attr is None:
                    continue
                if obj in getattr(game.world, spec.attr):
                    return spec.secondary_panel_attr
        return None

    def _on_delete_spike(self, obj):
        self.game.world.landscape_version += 1

    def _on_delete_water(self, obj):
        self.unlink_road_endpoints("water", obj.id)

    def _on_delete_bush(self, obj):
        self.unlink_road_endpoints("bush", obj.id)

    def _on_delete_campfire(self, obj):
        self.unlink_road_endpoints("campfire", obj.id)
        self._cleanup_campfire_references(obj)

    def _on_delete_wall(self, obj):
        self.game.world.landscape_version += 1

    def _on_delete_fence(self, obj):
        self.game.world.landscape_version += 1

    def delete_object(self, obj):
        game = self.game

        for spec in all_road_networks():
            collection = getattr(game.world, spec.road_collection)
            if obj in collection:
                collection.remove(obj)
                self.cleanup_crossings_for(spec.obj_type, obj.id)
                for creature in game.world.creatures:
                    creature.on_road_deleted(spec.obj_type, obj)
                return

        for attr, handler_name in self._CORE_DELETE_HANDLERS:
            collection = getattr(game.world, attr)
            if obj in collection:
                collection.remove(obj)
                if handler_name is not None:
                    getattr(self, handler_name)(obj)
                return

        for spec in all_extra_object_collections():
            collection = getattr(game.world, spec.attr)
            if obj in collection:
                collection.remove(obj)
                if spec.on_delete is not None:
                    spec.on_delete(game, obj)
                return


# =========================================================================
# Итоговый класс: композиция доменов
# =========================================================================

class ObjectManager(_InitialResourceMixin, _NaturalGrowthMixin, _LookupMixin):

    def __init__(self, game):
        self.game = game
        self.spawn_managers = {
            descriptor.race_name: descriptor.spawn_manager_cls(self.game)
            for descriptor in all_races()
            if descriptor.spawn_manager_cls is not None
        }