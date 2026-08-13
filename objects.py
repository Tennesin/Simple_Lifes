import pygame
from settings import *
from info import *
import time
import uuid
import math
import random

# --------------- Шаблоны ---------------

class WorldObject:
    type_name = None

    def __init__(self, x, y, gen_id=False):
        self.x = x
        self.y = y
        self.created = time.time()
        if gen_id:
            self.id = str(uuid.uuid4())[:8]

    def get_type_name(self):
        return self.type_name

    def _base_dict(self):
        d = {"x": self.x, "y": self.y, "created": self.created}
        if hasattr(self, "id"):
            d["id"] = self.id
        return d

    def _apply_base(self, data):
        self.created = data.get("created", self.created)
        if hasattr(self, "id"):
            self.id = data.get("id", self.id)

class PolylineRoad:

    def __init__(self, points=None, road_id=None):
        self.points = points if points else []
        self.id = road_id if road_id else str(uuid.uuid4())[:8]
        self.created = time.time()
        self._bounds_cache = None

    def add_point(self, x, y):
        self.points.append((x, y))
        self._bounds_cache = None

    def get_bounding_circle(self):
        if self._bounds_cache is None:
            if not self.points:
                self._bounds_cache = (0.0, 0.0, 0.0)
            else:
                xs = [p[0] for p in self.points]
                ys = [p[1] for p in self.points]
                cx = (min(xs) + max(xs)) / 2
                cy = (min(ys) + max(ys)) / 2
                radius = math.hypot(max(xs) - min(xs), max(ys) - min(ys)) / 2
                self._bounds_cache = (cx, cy, radius)
        return self._bounds_cache


class LineObstacle:

    def __init__(self, points=None, obj_id=None):
        self.points = points if points else []
        self.id = obj_id if obj_id else str(uuid.uuid4())[:8]
        self.created = time.time()
        self._bounds_cache = None

    def add_point(self, x, y):
        self.points.append((x, y))
        self._bounds_cache = None

    def get_bounding_circle(self):
        if self._bounds_cache is None:
            if not self.points:
                self._bounds_cache = (0.0, 0.0, 0.0)
            else:
                xs = [p[0] for p in self.points]
                ys = [p[1] for p in self.points]
                cx = (min(xs) + max(xs)) / 2
                cy = (min(ys) + max(ys)) / 2
                radius = math.hypot(max(xs) - min(xs), max(ys) - min(ys)) / 2
                self._bounds_cache = (cx, cy, radius)
        return self._bounds_cache

    def to_dict(self):
        return {"id": self.id, "points": self.points, "created": self.created}

    @classmethod
    def from_dict(cls, data):
        obj = cls(points=[tuple(p) for p in data.get("points", [])], obj_id=data.get("id"))
        obj.created = data.get("created", time.time())
        return obj

# --------------- Объекты ---------------

class Fruit(WorldObject):
    type_name = INFO_OBJECT_FRUIT

    def __init__(self, x, y):
        super().__init__(x, y)
        self.active = True
        self.radius = 8

    def draw(self, screen, screen_pos):
        if self.active:
            sx, sy = int(screen_pos[0]), int(screen_pos[1])
            pygame.draw.circle(screen, FRUIT_COLOR, (sx, sy), self.radius)
            pygame.draw.circle(screen, FRUIT_COLOR_BORDER, (sx, sy), self.radius, 2)

    def to_dict(self):
        d = self._base_dict()
        d["active"] = self.active
        return d

    @staticmethod
    def from_dict(data):
        fruit = Fruit(data["x"], data["y"])
        fruit._apply_base(data)
        fruit.active = data.get("active", True)
        return fruit

class Spike(WorldObject):
    type_name = INFO_OBJECT_SPIKE

    def __init__(self, x, y):
        super().__init__(x, y)
        self.radius = 8

    def draw(self, screen, screen_pos):
        sx, sy = int(screen_pos[0]), int(screen_pos[1])
        pygame.draw.circle(screen, (255, 165, 0), (sx, sy), self.radius)
        pygame.draw.line(screen, (0, 0, 0), (sx - 5, sy), (sx + 5, sy), 2)
        pygame.draw.line(screen, (0, 0, 0), (sx, sy - 5), (sx, sy + 5), 2)

    def to_dict(self):
        return self._base_dict()

    @staticmethod
    def from_dict(data):
        spike = Spike(data["x"], data["y"])
        spike._apply_base(data)
        return spike

class WaterPuddle(WorldObject):
    type_name = INFO_OBJECT_WATER

    def __init__(self, x, y):
        super().__init__(x, y, gen_id=True)
        self.radius = 14
        self.claimed_by = None

    def draw(self, screen, screen_pos):
        sx, sy = int(screen_pos[0]), int(screen_pos[1])
        rect = (sx - self.radius, sy - self.radius // 2, self.radius * 2, self.radius)
        pygame.draw.ellipse(screen, (60, 140, 220), rect)
        pygame.draw.ellipse(screen, (30, 90, 170), rect, 2)

    def to_dict(self):
        d = self._base_dict()
        d["claimed_by"] = self.claimed_by
        return d

    @staticmethod
    def from_dict(data):
        water = WaterPuddle(data["x"], data["y"])
        water._apply_base(data)
        water.claimed_by = data.get("claimed_by")
        return water

class Bush(WorldObject):
    type_name = INFO_OBJECT_BUSH

    def __init__(self, x, y):
        super().__init__(x, y, gen_id=True)
        self.radius = 14
        self.spawn_timer = 0.0
        self.claimed_by = None

    def update(self, dt):
        self.spawn_timer += dt
        if self.spawn_timer >= BUSH_SPAWN_INTERVAL:
            self.spawn_timer -= BUSH_SPAWN_INTERVAL
            return True
        return False

    def draw(self, screen, screen_pos):
        sx, sy = int(screen_pos[0]), int(screen_pos[1])
        pygame.draw.circle(screen, BUSH_COLOR, (sx, sy), self.radius)
        pygame.draw.circle(screen, BUSH_COLOR_BORDER, (sx, sy), self.radius, 2)
        pygame.draw.circle(screen, BUSH_COLOR, (sx - 8, sy + 4), self.radius - 5)
        pygame.draw.circle(screen, BUSH_COLOR, (sx + 8, sy + 4), self.radius - 5)

    def to_dict(self):
        d = self._base_dict()
        d["claimed_by"] = self.claimed_by
        return d

    @staticmethod
    def from_dict(data):
        bush = Bush(data["x"], data["y"])
        bush._apply_base(data)
        bush.claimed_by = data.get("claimed_by")
        return bush

class Tree(WorldObject):
    type_name = INFO_OBJECT_TREE

    def __init__(self, x, y, wood_amount=None):
        super().__init__(x, y, gen_id=True)
        self.radius = TREE_RADIUS
        self.wood = wood_amount if wood_amount is not None else random.randint(TREE_WOOD_MIN, TREE_WOOD_MAX)
        self.claimed_by = None

    def has_wood(self):
        return self.wood > 0

    def draw(self, screen, screen_pos):
        sx, sy = int(screen_pos[0]), int(screen_pos[1])
        trunk_w, trunk_h = 8, self.radius + 6
        trunk_rect = (sx - trunk_w // 2, sy - 4, trunk_w, trunk_h)
        pygame.draw.rect(screen, TREE_COLOR_TRUNK, trunk_rect)
        pygame.draw.rect(screen, TREE_COLOR_TRUNK_BORDER, trunk_rect, 1)

        crown_center = (sx, sy - self.radius // 2)
        pygame.draw.circle(screen, TREE_COLOR_LEAVES, crown_center, self.radius)
        pygame.draw.circle(screen, TREE_COLOR_LEAVES_BORDER, crown_center, self.radius, 2)

    def to_dict(self):
        d = self._base_dict()
        d.update({"wood": self.wood, "claimed_by": self.claimed_by})
        return d

    @staticmethod
    def from_dict(data):
        tree = Tree(data["x"], data["y"], wood_amount=data.get("wood"))
        tree._apply_base(data)
        tree.claimed_by = data.get("claimed_by")
        return tree

class Stone(WorldObject):
    type_name = INFO_OBJECT_STONE

    def __init__(self, x, y, stone_amount=None):
        super().__init__(x, y, gen_id=True)
        self.radius = STONE_RADIUS
        self.stone = stone_amount if stone_amount is not None else random.randint(STONE_MIN_AMOUNT, STONE_MAX_AMOUNT)

    def has_stone(self):
        return self.stone > 0

    def draw(self, screen, screen_pos):
        sx, sy = int(screen_pos[0]), int(screen_pos[1])
        pygame.draw.circle(screen, STONE_COLOR, (sx, sy), self.radius)
        pygame.draw.circle(screen, STONE_COLOR_BORDER, (sx, sy), self.radius, 2)
        pygame.draw.circle(screen, STONE_COLOR_LIGHT, (sx - 4, sy - 4), max(2, self.radius // 3))

    def to_dict(self):
        d = self._base_dict()
        d["stone"] = self.stone
        return d

    @staticmethod
    def from_dict(data):
        stone = Stone(data["x"], data["y"], stone_amount=data.get("stone"))
        stone._apply_base(data)
        return stone

class Campfire(WorldObject):
    type_name = INFO_OBJECT_CAMPFIRE

    def __init__(self, x, y):
        super().__init__(x, y, gen_id=True)
        self.radius = 16
        self.effect_radius = CAMPFIRE_RADIUS

    def draw(self, screen, screen_pos):
        sx, sy = int(screen_pos[0]), int(screen_pos[1])
        halo = pygame.Surface((self.effect_radius * 2, self.effect_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(halo, (255, 170, 60, 18),
                           (self.effect_radius, self.effect_radius), self.effect_radius)
        screen.blit(halo, (sx - self.effect_radius, sy - self.effect_radius))

        pygame.draw.circle(screen, (90, 70, 60), (sx, sy), self.radius + 3)
        pygame.draw.circle(screen, CAMPFIRE_COLOR_BORDER, (sx, sy), self.radius, 2)
        pygame.draw.circle(screen, CAMPFIRE_COLOR, (sx, sy - 2), self.radius - 5)
        pygame.draw.circle(screen, CAMPFIRE_COLOR_CORE, (sx, sy - 4), self.radius - 9)

    def to_dict(self):
        return self._base_dict()

    @staticmethod
    def from_dict(data):
        fire = Campfire(data["x"], data["y"])
        fire._apply_base(data)
        return fire

# --------------- Дороги ---------------

class Road(PolylineRoad):

    def __init__(self, points=None, road_id=None):
        super().__init__(points=points, road_id=road_id)
        self.rating = None
        self.endpoint_a = None
        self.endpoint_b = None

    def get_type_name(self):
        return INFO_OBJECT_ROAD

    def draw(self, screen, camera):
        if len(self.points) < 2:
            return
        if self.rating == "useful":
            color = (90, 230, 120)
        elif self.rating == "dangerous":
            color = (230, 30, 30)
        elif self.rating == "useless":
            color = (150, 150, 150)
        else:
            color = (255, 255, 255)
        screen_points = [camera.apply_pos(p) for p in self.points]
        pygame.draw.lines(screen, color, False, screen_points, 3)

        if self.endpoint_a is not None:
            pos = camera.apply_pos(self.points[0])
            pygame.draw.circle(screen, (255, 255, 255), (int(pos[0]), int(pos[1])), 5)
        if self.endpoint_b is not None:
            pos = camera.apply_pos(self.points[-1])
            pygame.draw.circle(screen, (255, 255, 255), (int(pos[0]), int(pos[1])), 5)

    def to_dict(self):
        return {
            "id": self.id, "points": self.points, "rating": self.rating, "created": self.created,
            "endpoint_a": self.endpoint_a, "endpoint_b": self.endpoint_b,
        }

    @staticmethod
    def from_dict(data):
        road = Road(points=[tuple(p) for p in data.get("points", [])], road_id=data.get("id"))
        road.rating = data.get("rating")
        road.created = data.get("created", time.time())
        road.endpoint_a = data.get("endpoint_a")
        road.endpoint_b = data.get("endpoint_b")
        return road

# --------------- Преграды ---------------

class Wall(LineObstacle):

    def get_type_name(self):
        return INFO_OBJECT_WALL

    def draw(self, screen, camera, extra_point=None):
        points = self.points if extra_point is None else self.points + [extra_point]
        if len(points) < 2:
            return
        screen_points = [camera.apply_pos(p) for p in points]
        pygame.draw.lines(screen, WALL_COLOR, False, screen_points, WALL_THICKNESS)
        joint_radius = WALL_THICKNESS // 2 + 1
        for px, py in screen_points:
            pygame.draw.circle(screen, WALL_COLOR, (int(px), int(py)), joint_radius)

class Fence(LineObstacle):

    def get_type_name(self):
        return INFO_OBJECT_FENCE

    def draw(self, screen, camera, extra_point=None):
        points = self.points if extra_point is None else self.points + [extra_point]
        if len(points) < 2:
            return
        screen_points = [camera.apply_pos(p) for p in points]
        pygame.draw.lines(screen, FENCE_COLOR, False, screen_points, FENCE_THICKNESS)
        joint_radius = FENCE_THICKNESS // 2 + 1
        for px, py in screen_points:
            pygame.draw.circle(screen, FENCE_COLOR, (int(px), int(py)), joint_radius)
        self._draw_ticks(screen, screen_points)

    def _draw_ticks(self, screen, screen_points):
        distance_since_tick = FENCE_TICK_INTERVAL / 2
        for i in range(len(screen_points) - 1):
            x1, y1 = screen_points[i]
            x2, y2 = screen_points[i + 1]
            seg_len = math.hypot(x2 - x1, y2 - y1)
            if seg_len == 0:
                continue
            dx, dy = (x2 - x1) / seg_len, (y2 - y1) / seg_len
            pos = FENCE_TICK_INTERVAL - distance_since_tick
            while pos < seg_len:
                cx = x1 + dx * pos
                cy = y1 + dy * pos
                half = FENCE_TICK_LENGTH / 2
                pygame.draw.line(screen, FENCE_TICK_COLOR,
                                 (cx - half, cy + half), (cx + half, cy - half), 2)
                pos += FENCE_TICK_INTERVAL
            distance_since_tick = seg_len - (pos - FENCE_TICK_INTERVAL)

# --------------- Особые виды объектов ---------------

class RoadCrossing:

    def __init__(self, x, y, crossing_id=None):
        self.id = crossing_id if crossing_id else str(uuid.uuid4())[:8]
        self.x = x
        self.y = y
        self.road_ids = set()

    def get_type_name(self):
        return INFO_OBJECT_ROAD_CROSSING

    def draw(self, screen, screen_pos):
        sx, sy = int(screen_pos[0]), int(screen_pos[1])
        pygame.draw.circle(screen, ROAD_CROSSING_COLOR, (sx, sy), ROAD_CROSSING_RADIUS)
        pygame.draw.circle(screen, ROAD_CROSSING_COLOR_BORDER, (sx, sy), ROAD_CROSSING_RADIUS, 2)

    def to_dict(self):
        return {"id": self.id, "x": self.x, "y": self.y, "road_ids": list(self.road_ids)}

    @staticmethod
    def from_dict(data):
        crossing = RoadCrossing(data["x"], data["y"], crossing_id=data.get("id"))
        crossing.road_ids = set(data.get("road_ids", []))
        return crossing