"""Дорожные сети: создание, примагничивание, перекрёстки, привязка концов дорог к ориентирам."""

import math
from collections import namedtuple

import settings
from creatures.all_needed import geometry
from creatures.all_needed.geometry import distance_to_footprint
from game.race_registry import all_landmark_specs, all_road_networks
from objects import RoadCrossing

from . import object_settings as cfg

# Ориентиры ядра, к которым может быть привязан конец дороги: (тип, коллекция мира).
# Ориентиры рас (костёр, склад, кладбище) приходят через LandmarkSpec в дескрипторе расы.
_CORE_LANDMARKS = (
    ("water", "water_puddles"),
    ("bush", "bushes"),
    ("tree", "trees"),
    ("stone", "stones"),
)

# Пересечение двух отрезков: point - точка, *_seg - индекс сегмента, *_t - расстояние
# от начала сегмента до точки (нужно, чтобы вставлять точки в правильном порядке)
_Hit = namedtuple("_Hit", "point other_road new_seg other_seg new_t other_t")

def segment_intersection(p1, p2, p3, p4):
    """Точка пересечения отрезков p1-p2 и p3-p4 (без самых концов) или None."""
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-9:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u = ((x1 - x3) * (y1 - y2) - (y1 - y3) * (x1 - x2)) / denom
    low, high = cfg.CROSSING_SEGMENT_EDGE, 1.0 - cfg.CROSSING_SEGMENT_EDGE
    if low <= t <= high and low <= u <= high:
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
    return None

class RoadNetworkService:

    def __init__(self, game):
        self.game = game

    # =====================================================================
    # Создание и завершение дороги
    # =====================================================================

    def _spec(self, obj_type):
        for spec in all_road_networks():
            if spec.obj_type == obj_type:
                return spec
        raise KeyError(f"Неизвестная дорожная сеть: {obj_type}")

    def create_road(self, obj_type):
        spec = self._spec(obj_type)
        if spec.road_cls is None:
            raise KeyError(f"Дорожная сеть '{obj_type}' не зарегистрировала road_cls")
        return spec.road_cls()

    def finalize_drawn(self, obj_type, road):
        """Игрок отпустил кнопку: примагничиваем конец, привязываем к ориентирам, ищем перекрёстки."""
        spec = self._spec(obj_type)
        if len(road.points) < 2:
            return
        last_x, last_y = road.points[-1]
        road.points[-1] = self.snap(last_x, last_y, obj_type, self_points=road.points[:-1])
        road._bounds_cache = None
        if hasattr(road, "endpoint_a"):         # концы есть не у всех видов дорог
            self.link_endpoints(road)
        self.register_crossings(obj_type, road)
        getattr(self.game.world, spec.road_collection).append(road)

    # =====================================================================
    # Примагничивание к уже существующим линиям
    # =====================================================================

    def snap(self, wx, wy, obj_type, tolerance=None, self_points=None):
        tolerance = settings.LANDSCAPE_SNAP_TOLERANCE if tolerance is None else tolerance
        polylines = self._polylines_of(obj_type)
        if polylines is None:
            return (wx, wy)

        best_point, best_dist = None, tolerance
        for points in polylines:
            best_point, best_dist = self._closest_on(points, wx, wy, best_point, best_dist)

        if self_points:
            keep = cfg.SELF_SNAP_EXCLUDE_RECENT_POINTS
            safe_points = self_points[:-keep] if len(self_points) > keep else []
            best_point, best_dist = self._closest_on(safe_points, wx, wy, best_point, best_dist)

        return best_point if best_point is not None else (wx, wy)

    def _polylines_of(self, obj_type):
        world = self.game.world
        for spec in all_road_networks():
            if spec.obj_type == obj_type:
                return [road.points for road in getattr(world, spec.road_collection)]
        if obj_type == "wall":
            return [wall.points for wall in world.walls]
        if obj_type == "fence":
            return [fence.points for fence in world.fences]
        return None

    @staticmethod
    def _closest_on(points, wx, wy, best_point, best_dist):
        if not points:
            return best_point, best_dist
        if len(points) == 1:
            px, py = points[0]
            d = math.hypot(wx - px, wy - py)
            return ((px, py), d) if d < best_dist else (best_point, best_dist)
        for i in range(len(points) - 1):
            ax, ay = points[i]
            bx, by = points[i + 1]
            cx, cy = geometry.closest_point_on_segment(wx, wy, ax, ay, bx, by)
            d = math.hypot(wx - cx, wy - cy)
            if d < best_dist:
                best_point, best_dist = (cx, cy), d
        return best_point, best_dist

    # =====================================================================
    # Перекрёстки
    # =====================================================================

    def register_crossings(self, obj_type, new_road):
        spec = self._spec(obj_type)
        others = getattr(self.game.world, spec.road_collection)
        hits = self._find_intersections(new_road, others)
        if not hits:
            return

        # ---------- В новую дорогу: с конца, а внутри одного сегмента - от дальней точки к ближней,
        # иначе вставка сдвигает индексы ещё не вставленных точек и порядок ломается ----------
        for hit in sorted(hits, key=lambda h: (h.new_seg, h.new_t), reverse=True):
            crossing = self._find_or_create_crossing(spec.crossing_collection, hit.point)
            self._insert_crossing_point(obj_type, new_road, hit.new_seg, hit.point, notify_followers=False)
            crossing.road_ids.add(new_road.id)
            crossing.road_ids.add(hit.other_road.id)

        # ---------- В остальные дороги - по тому же правилу ----------
        by_road = {}
        for hit in hits:
            by_road.setdefault(id(hit.other_road), (hit.other_road, []))[1].append(hit)
        for road, road_hits in by_road.values():
            for hit in sorted(road_hits, key=lambda h: (h.other_seg, h.other_t), reverse=True):
                self._insert_crossing_point(obj_type, road, hit.other_seg, hit.point)

    @staticmethod
    def _find_intersections(new_road, others):
        hits = []
        for other in others:
            if other is new_road or len(other.points) < 2:
                continue
            for ni in range(len(new_road.points) - 1):
                a1, a2 = new_road.points[ni], new_road.points[ni + 1]
                for oi in range(len(other.points) - 1):
                    b1, b2 = other.points[oi], other.points[oi + 1]
                    point = segment_intersection(a1, a2, b1, b2)
                    if point is not None:
                        hits.append(_Hit(
                            point, other, ni, oi,
                            math.hypot(point[0] - a1[0], point[1] - a1[1]),
                            math.hypot(point[0] - b1[0], point[1] - b1[1])))
        return hits

    def _find_or_create_crossing(self, collection_name, point):
        collection = getattr(self.game.world, collection_name)
        for crossing in collection:
            if math.hypot(crossing.x - point[0], crossing.y - point[1]) < settings.CROSSING_MERGE_RADIUS:
                return crossing
        crossing = RoadCrossing(point[0], point[1])
        collection.append(crossing)
        return crossing

    def _insert_crossing_point(self, obj_type, road, seg_index, point, notify_followers=True):
        p1 = road.points[seg_index]
        p2 = road.points[seg_index + 1]
        tolerance = cfg.CROSSING_INSERT_TOLERANCE
        if math.hypot(point[0] - p1[0], point[1] - p1[1]) < tolerance:
            return
        if math.hypot(point[0] - p2[0], point[1] - p2[1]) < tolerance:
            return
        road.points.insert(seg_index + 1, point)
        road._bounds_cache = None
        if notify_followers:
            # существа, идущие по этой дороге, должны сдвинуть свой индекс точки
            for creature in self.game.world.creatures:
                creature.on_road_progress_shift(obj_type, road, seg_index + 1)

    def cleanup_crossings_for(self, obj_type, road_id):
        spec = self._spec(obj_type)
        world = self.game.world
        remaining = []
        for crossing in getattr(world, spec.crossing_collection):
            crossing.road_ids.discard(road_id)
            if len(crossing.road_ids) >= 2:
                remaining.append(crossing)
        setattr(world, spec.crossing_collection, remaining)

    # =====================================================================
    # Привязка концов дороги к ориентирам (вода, куст, костёр, ...)
    # =====================================================================

    def _landmarks(self):
        world = self.game.world
        for type_name, attr in _CORE_LANDMARKS:
            yield type_name, getattr(world, attr)
        for spec in all_landmark_specs():
            yield spec.type_name, getattr(world, spec.attr)

    def find_landmark(self, wx, wy):
        """Ближайший ориентир в пределах ROAD_ENDPOINT_LINK_MARGIN или None
        (раньше побеждал первый найденный по порядку списка, а не ближайший)."""
        margin = settings.ROAD_ENDPOINT_LINK_MARGIN
        best, best_dist = None, None
        for type_name, collection in self._landmarks():
            for obj in collection:
                d = distance_to_footprint(obj, wx, wy)
                if d <= margin and (best is None or d < best_dist):
                    best, best_dist = {"type": type_name, "obj_id": obj.id}, d
        return best

    def link_endpoints(self, road):
        if not road.points:
            return
        road.endpoint_a = self.find_landmark(*road.points[0])
        road.endpoint_b = self.find_landmark(*road.points[-1])

    def resolve_endpoint(self, endpoint):
        if endpoint is None:
            return None
        type_name, obj_id = endpoint.get("type"), endpoint.get("obj_id")
        for registered_type, collection in self._landmarks():
            if registered_type == type_name:
                return next((o for o in collection if o.id == obj_id), None)
        return None

    def unlink_endpoints(self, obj_type, obj_id):
        """Ориентир исчез - отвязываем от него концы всех дорог."""
        world = self.game.world
        for spec in all_road_networks():
            for road in getattr(world, spec.road_collection):
                if not hasattr(road, "endpoint_a"):
                    continue
                for attr in ("endpoint_a", "endpoint_b"):
                    endpoint = getattr(road, attr)
                    if endpoint and endpoint.get("type") == obj_type and endpoint.get("obj_id") == obj_id:
                        setattr(road, attr, None)

    # =====================================================================
    # Затопление дорог (кисть реки/моря)
    # =====================================================================

    def mark_flooded(self, point_in_zone_fn):
        """Дороги, хоть одной точкой попавшие в зону, помечаются опасными; идущие по ним
        существа уведомляются."""
        world = self.game.world
        for spec in all_road_networks():
            for road in getattr(world, spec.road_collection):
                if any(point_in_zone_fn(px, py) for px, py in road.points):
                    road.rating = "dangerous"
                    for creature in world.creatures:
                        creature.on_road_deleted(spec.obj_type, road)