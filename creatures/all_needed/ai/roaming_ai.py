"""Общие примитивы простого ИИ для животных: бродяжничество,
поиск воды, обход моря, прямолинейное движение к точке, "умный" побег
(обход углов/тупиков) и усиленный A* для выживания."""

import math
import random
import settings
from creatures.all_needed import geometry
from settings import BIOME_SEA, BIOME_RIVER

class RoamingAnimalMixin:
    """Ожидает от наследника: self.entity (существо с .x/.y/.vision_radius),
    self.cfg (словарь настроек), self.target, self.decision_timer."""

    # ---------- Врождённый страх и урон от шипов, общий для всех животных ----------

    def _tick_spike_invuln(self, dt):
        e = self.entity
        if e.spike_invuln_timer > 0:
            e.spike_invuln_timer -= dt

    def _nearest_spike(self, spikes, radius):
        if not spikes:
            return None
        return self._nearest_within(spikes, radius)

    def _apply_spike_damage(self, spikes, biome_grid=None):
        e = self.entity
        if not spikes or e.spike_invuln_timer > 0:
            return
        for spike in spikes:
            if math.hypot(e.x - spike.x, e.y - spike.y) < settings.ANIMAL_SPIKE_HIT_DISTANCE:
                e.hp = max(0.0, e.hp - settings.ANIMAL_SPIKE_DAMAGE)
                e.spike_invuln_timer = settings.ANIMAL_SPIKE_INVULN_DURATION

                dx, dy = e.x - spike.x, e.y - spike.y
                dist = math.hypot(dx, dy)
                if dist != 0:
                    new_x = e.x + dx / dist * 30
                    new_y = e.y + dy / dist * 30
                    if biome_grid is None or biome_grid.get_at(new_x, new_y) != BIOME_SEA:
                        e.x = max(15, min(new_x, settings.WORLD_WIDTH - 15))
                        e.y = max(15, min(new_y, settings.WORLD_HEIGHT - 15))
                self._reset_navigation()
                break

    def _update_seek_state(self, hunger_seek_ratio, hunger_satisfy_ratio,
                            thirst_seek_ratio, thirst_satisfy_ratio):
        e = self.entity
        if e.hunger < e.hunger_max * hunger_seek_ratio:
            self.seeking_food = True
        if self.seeking_food and e.hunger >= e.hunger_max * hunger_satisfy_ratio:
            self.seeking_food = False

        if e.thirst < e.thirst_max * thirst_seek_ratio:
            self.seeking_water = True
        if self.seeking_water and e.thirst >= e.thirst_max * thirst_satisfy_ratio:
            self.seeking_water = False

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
            dist_range = cfg["wander_distance"]
            dist = random.uniform(*dist_range)
            point = geometry.clamped_point(e.x, e.y, angle, dist)
        return point

    # =====================================================================
    # НОВОЕ (п.4): "умный" побег - вместо одной прямой точки "от угрозы"
    # перебираем веер направлений и выбираем то, что реально уводит животное
    # подальше, а не утыкает его в угол карты/стену. Плюс отдельная проверка
    # "а мы вообще сдвинулись, убегая?" с аварийным рывком в сторону.
    # =====================================================================

    _FLEE_ANGLE_OFFSETS_DEG = (0, -30, 30, -60, 60, -90, 90, -130, 130, 180)

    def flee_from(self, threat_pos, distance, dt, biome_grid=None):
        """Единая точка входа для побега любого животного."""
        stuck_point = self._tick_flee_stuck(dt, distance)
        if stuck_point is not None:
            return self._avoid_sea(stuck_point, biome_grid, attempts=4)
        return self._flee_point_smart(threat_pos, distance, biome_grid=biome_grid)

    def _flee_point_smart(self, threat_pos, distance, biome_grid=None):
        e = self.entity
        base_dx = e.x - threat_pos[0]
        base_dy = e.y - threat_pos[1]
        base_dist = math.hypot(base_dx, base_dy)
        base_angle = math.atan2(base_dy, base_dx) if base_dist > 1e-6 else random.uniform(0, 2 * math.pi)

        min_displacement = distance * settings.ANIMAL_FLEE_MIN_DISPLACEMENT_RATIO
        best_point, best_dist_from_threat = None, -1.0

        for offset_deg in self._FLEE_ANGLE_OFFSETS_DEG:
            angle = base_angle + math.radians(offset_deg)
            point = geometry.clamped_point(e.x, e.y, angle, distance)
            point = self._avoid_sea(point, biome_grid, attempts=2)
            if point is None:
                continue
            displacement = math.hypot(point[0] - e.x, point[1] - e.y)
            if displacement < min_displacement:
                continue  # угол карты/стена почти не дали сдвинуться - такой вариант не годится
            dist_from_threat = math.hypot(point[0] - threat_pos[0], point[1] - threat_pos[1])
            if dist_from_threat > best_dist_from_threat:
                best_dist_from_threat = dist_from_threat
                best_point = point

        if best_point is not None:
            return best_point

        # ---------- Совсем зажаты (со всех сторон недостаточно свободного места) -
        # берём вариант хотя бы с максимальным реальным сдвигом ----------
        fallback_point, fallback_disp = None, -1.0
        for offset_deg in self._FLEE_ANGLE_OFFSETS_DEG:
            angle = base_angle + math.radians(offset_deg)
            point = geometry.clamped_point(e.x, e.y, angle, distance)
            point = self._avoid_sea(point, biome_grid, attempts=2)
            if point is None:
                continue
            displacement = math.hypot(point[0] - e.x, point[1] - e.y)
            if displacement > fallback_disp:
                fallback_disp = displacement
                fallback_point = point
        return fallback_point if fallback_point is not None else e.flee_point(threat_pos, distance)

    def _tick_flee_stuck(self, dt, distance):
        """Периодически проверяем: если животное убегает, но фактически почти
        не сдвинулось (зажато углом карты/стеной/забором) - выдаём большой
        случайный рывок в сторону вместо повторной попытки в тупиковую точку."""
        e = self.entity
        last_pos = getattr(self, "_flee_last_pos", None)
        if last_pos is None:
            self._flee_last_pos = (e.x, e.y)
            self._flee_stuck_timer = 0.0
            return None

        self._flee_stuck_timer = getattr(self, "_flee_stuck_timer", 0.0) + dt
        if self._flee_stuck_timer < settings.ANIMAL_FLEE_STUCK_CHECK_INTERVAL:
            return None

        moved = math.hypot(e.x - last_pos[0], e.y - last_pos[1])
        self._flee_last_pos = (e.x, e.y)
        self._flee_stuck_timer = 0.0

        if moved < distance * settings.ANIMAL_FLEE_STUCK_MOVE_RATIO:
            angle = random.uniform(0, 2 * math.pi)
            return geometry.clamped_point(
                e.x, e.y, angle, distance * settings.ANIMAL_FLEE_STUCK_ESCAPE_MULTIPLIER)
        return None

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

    # =====================================================================
    # Контекстный A* - включается, когда прямая линия перекрыта, либо
    # принудительно ("urgent" - п.3), когда речь о выживании.
    # =====================================================================

    def _reset_navigation(self):
        e = self.entity
        e.nav_path = []
        e.nav_path_index = 0
        e.nav_goal = None
        e.nav_recalc_timer = 0.0

    def _navigate_with_astar(self, target, dt, nav_grid, fallback_nav_grid=None, urgent=False):
        e = self.entity

        if e.nav_recalc_timer > 0:
            e.nav_recalc_timer -= dt

        goal_changed = (
                e.nav_goal is None or
                math.hypot(e.nav_goal[0] - target[0], e.nav_goal[1] - target[1]) > settings.NAV_GOAL_CHANGE_THRESHOLD
        )
        path_exhausted = not e.nav_path or e.nav_path_index >= len(e.nav_path)
        needs_recalc = goal_changed or path_exhausted or e.nav_recalc_timer <= 0

        if needs_recalc:
            # ---------- "Прокачанный" поиск для выживания: больше узлов на просмотр
            # и чаще пересчёт маршрута ----------
            max_nodes = settings.NAV_MAX_ASTAR_NODES * (settings.NAV_URGENT_NODE_MULTIPLIER if urgent else 1)
            recalc_interval = settings.NAV_URGENT_RECALC_INTERVAL if urgent else settings.NAV_PATH_RECALC_INTERVAL

            path = nav_grid.find_path((e.x, e.y), target, max_nodes=max_nodes)
            if not path and fallback_nav_grid is not None:
                path = fallback_nav_grid.find_path((e.x, e.y), target, max_nodes=max_nodes)
            e.nav_goal = target
            e.nav_recalc_timer = random.uniform(*recalc_interval)
            e.nav_path = path if path else []
            e.nav_path_index = 0

        if not e.nav_path:
            # A* не нашёл дорогу (например, полностью отрезаны морем) - хотя бы не стоим на месте
            return target

        while (e.nav_path_index < len(e.nav_path) - 1 and
               math.hypot(e.x - e.nav_path[e.nav_path_index][0],
                          e.y - e.nav_path[e.nav_path_index][1]) < settings.NAV_WAYPOINT_REACHED_DISTANCE):
            e.nav_path_index += 1

        return e.nav_path[e.nav_path_index]

    def move_towards(self, target, dt, biome_grid=None, speed_multiplier=1.0,
                     nav_grid=None, fallback_nav_grid=None,
                     wall_polylines=None, fence_polylines=None, urgent=False):
        e, cfg = self.entity, self.cfg
        if target is None:
            self._reset_navigation()
            return

        waypoint = target
        if nav_grid is not None:
            close_enough_for_direct = (
                    math.hypot(target[0] - e.x, target[1] - e.y) <= settings.ANIMAL_URGENT_DIRECT_RANGE
            )
            if (not urgent or close_enough_for_direct) and nav_grid.has_line_of_sight((e.x, e.y), target):
                self._reset_navigation()
            else:
                waypoint = self._navigate_with_astar(target, dt, nav_grid, fallback_nav_grid, urgent=urgent)

        tx, ty = waypoint
        dx, dy = tx - e.x, ty - e.y
        dist = math.hypot(dx, dy)
        if dist < 2:
            return
        speed = cfg["speed"] * speed_multiplier
        if biome_grid is not None and biome_grid.get_at(e.x, e.y) == BIOME_RIVER:
            speed *= settings.ANIMAL_RIVER_SWIM_SPEED_MULTIPLIER
        step = min(speed * dt, dist)
        new_x = max(15, min(e.x + dx / dist * step, settings.WORLD_WIDTH - 15))
        new_y = max(15, min(e.y + dy / dist * step, settings.WORLD_HEIGHT - 15))

        # ---------- Физически не даём пройти сквозь стену/забор ----------
        if wall_polylines:
            new_x, new_y = geometry.resolve_circle_vs_polylines(
                new_x, new_y, e.radius, wall_polylines, settings.WALL_THICKNESS)
        if fence_polylines:
            new_x, new_y = geometry.resolve_circle_vs_polylines(
                new_x, new_y, e.radius, fence_polylines, settings.FENCE_THICKNESS)

        e.x, e.y = new_x, new_y