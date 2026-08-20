"""Общие примитивы простого ИИ для животных: бродяжничество,
поиск воды, обход моря, прямолинейное движение к точке."""

import math
import random
import settings
from creatures.all_needed import geometry
from settings import BIOME_SEA, BIOME_RIVER

class RoamingAnimalMixin:
    """Ожидает от наследника: self.entity (существо с .x/.y/.vision_radius),
    self.cfg (словарь настроек), self.target, self.decision_timer."""

    def _wander(self, dt, biome_grid):
        e, cfg = self.entity, self.cfg
        reached = (self.target is None or math.hypot(e.x - self.target[0], e.y - self.target[1]) < 12)
        self.decision_timer -= dt
        if reached or self.decision_timer <= 0:
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(*cfg["wander_distance"])
            point = geometry.clamped_point(e.x, e.y, angle, dist)
            self.target = self._avoid_sea(point, biome_grid)
            self.decision_timer = random.uniform(*cfg["wander_timer"])
        return self.target

    def _avoid_sea(self, point, biome_grid, attempts=3):
        if biome_grid is None or point is None:
            return point
        e, cfg = self.entity, self.cfg
        for _ in range(attempts):
            if biome_grid.get_at(point[0], point[1]) != BIOME_SEA:
                return point
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(*cfg["wander_distance"])
            point = geometry.clamped_point(e.x, e.y, angle, dist)
        return point

    def _nearest_within(self, objects, radius, predicate=None):
        e = self.entity
        best, best_dist = None, radius
        for obj in objects:
            if predicate is not None and not predicate(obj):
                continue
            d = math.hypot(e.x - obj.x, e.y - obj.y)
            if d < best_dist:
                best_dist = d
                best = obj
        return best

    def _nearest_water_target(self, water_puddles, biome_grid, radius):
        e = self.entity
        nearest_puddle = self._nearest_within(water_puddles, radius, predicate=lambda w: w.has_water())
        river_point = None
        if biome_grid is not None:
            river_point = biome_grid.find_nearest_of_type(e.x, e.y, BIOME_RIVER, radius)
        if nearest_puddle is not None and river_point is not None:
            d_puddle = math.hypot(e.x - nearest_puddle.x, e.y - nearest_puddle.y)
            d_river = math.hypot(e.x - river_point[0], e.y - river_point[1])
            return (nearest_puddle.x, nearest_puddle.y) if d_puddle <= d_river else river_point
        if nearest_puddle is not None:
            return (nearest_puddle.x, nearest_puddle.y)
        return river_point

    def move_towards(self, target, dt, speed_multiplier=1.0):
        e, cfg = self.entity, self.cfg
        if target is None:
            return
        tx, ty = target
        dx, dy = tx - e.x, ty - e.y
        dist = math.hypot(dx, dy)
        if dist < 2:
            return
        speed = cfg["speed"] * speed_multiplier
        step = min(speed * dt, dist)
        new_x = max(15, min(e.x + dx / dist * step, settings.WORLD_WIDTH - 15))
        new_y = max(15, min(e.y + dy / dist * step, settings.WORLD_HEIGHT - 15))
        e.x, e.y = new_x, new_y