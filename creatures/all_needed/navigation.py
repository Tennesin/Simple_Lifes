import heapq
import math
import random
import settings
from settings import *
from . import geometry

DEFAULT_SPEED = 120

def _point_segment_distance(px, py, ax, ay, bx, by):
    abx, aby = bx - ax, by - ay
    apx, apy = px - ax, py - ay
    ab_len_sq = abx * abx + aby * aby
    if ab_len_sq == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, (apx * abx + apy * aby) / ab_len_sq))
    return math.hypot(px - (ax + t * abx), py - (ay + t * aby))

class NavGridCache:

    def __init__(self):
        self._cache = {}
        self._fallback_cache = {}

    @staticmethod
    def _landscape_signature(walls, fences, spikes, include_fences):
        total = 0.0
        count = 0
        for w in walls:
            for x, y in w.points:
                total += x + y
                count += 1
        if include_fences:
            for f in fences:
                for x, y in f.points:
                    total += x + y
                    count += 1
        for s in spikes:
            total += s.x + s.y
            count += 1
        return (count, round(total, 1))

    @staticmethod
    def _build_grid(world_w, world_h, cell_size, walls, fences, spikes,
                     include_fences, inflate, spike_block_radius, biome_grid, soft_margin):
        grid = NavGrid(world_w, world_h, cell_size)
        for w in walls:
            grid.mark_polyline(w.points, inflate, soft_margin=soft_margin)
        if include_fences:
            for f in fences:
                grid.mark_polyline(f.points, inflate, soft_margin=soft_margin)
        for s in spikes:
            grid.mark_circle(s.x, s.y, spike_block_radius)
        if biome_grid is not None:
            grid.mark_biome(biome_grid, BIOME_SEA)
        return grid

    def get(self, world_w, world_h, cell_size, walls, fences, spikes,
            include_fences, inflate, spike_block_radius, biome_grid=None, version=None,
            soft_margin=NAV_WALL_SOFT_MARGIN):
        key = (world_w, world_h, cell_size, include_fences, inflate, spike_block_radius, soft_margin)

        if version is None:
            version = self._landscape_signature(walls, fences, spikes, include_fences)

        cached = self._cache.get(key)
        if cached is not None and cached[0] == version:
            return cached[1]

        grid = self._build_grid(world_w, world_h, cell_size, walls, fences, spikes,
                                include_fences, inflate, spike_block_radius, biome_grid, soft_margin)
        self._cache[key] = (version, grid)
        return grid

    def get_fallback(self, world_w, world_h, cell_size, walls, fences, spikes,
                      include_fences, spike_block_radius, biome_grid=None, version=None):
        key = (world_w, world_h, cell_size, include_fences, spike_block_radius, "fallback")

        if version is None:
            version = self._landscape_signature(walls, fences, spikes, include_fences)

        cached = self._fallback_cache.get(key)
        if cached is not None and cached[0] == version:
            return cached[1]

        grid = self._build_grid(world_w, world_h, cell_size, walls, fences, spikes,
                                include_fences, NAV_OBSTACLE_INFLATE_FALLBACK, spike_block_radius,
                                biome_grid, soft_margin=0)
        self._fallback_cache[key] = (version, grid)
        return grid

    def invalidate(self):
        self._cache.clear()
        self._fallback_cache.clear()

class NavGrid:

    def __init__(self, world_w, world_h, cell_size):
        self.cell_size = cell_size
        self.cols = max(1, int(math.ceil(world_w / cell_size)))
        self.rows = max(1, int(math.ceil(world_h / cell_size)))
        self.blocked = bytearray(self.cols * self.rows)
        self.near_obstacle = bytearray(self.cols * self.rows)

    # ---------- Координаты ----------

    def _index(self, cx, cy):
        return cy * self.cols + cx

    def in_bounds(self, cx, cy):
        return 0 <= cx < self.cols and 0 <= cy < self.rows

    def world_to_cell(self, x, y):
        cx = max(0, min(int(x // self.cell_size), self.cols - 1))
        cy = max(0, min(int(y // self.cell_size), self.rows - 1))
        return cx, cy

    def cell_center(self, cx, cy):
        return (cx * self.cell_size + self.cell_size / 2,
                cy * self.cell_size + self.cell_size / 2)

    def is_blocked(self, cx, cy):
        if not self.in_bounds(cx, cy):
            return True
        return self.blocked[self._index(cx, cy)] != 0

    # ---------- Построение карты ----------

    def mark_polyline(self, points, inflate, soft_margin=0):
        if len(points) < 2:
            if points:
                self._mark_segment(points[0], points[0], inflate, soft_margin)
            return
        for i in range(len(points) - 1):
            self._mark_segment(points[i], points[i + 1], inflate, soft_margin)

    def _mark_segment(self, p1, p2, inflate, soft_margin=0):
        total_margin = inflate + soft_margin
        min_x = min(p1[0], p2[0]) - total_margin
        max_x = max(p1[0], p2[0]) + total_margin
        min_y = min(p1[1], p2[1]) - total_margin
        max_y = max(p1[1], p2[1]) + total_margin

        c_min_x, c_min_y = self.world_to_cell(min_x, min_y)
        c_max_x, c_max_y = self.world_to_cell(max_x, max_y)

        for cy in range(c_min_y, c_max_y + 1):
            for cx in range(c_min_x, c_max_x + 1):
                center_x, center_y = self.cell_center(cx, cy)
                dist = _point_segment_distance(center_x, center_y, p1[0], p1[1], p2[0], p2[1])
                if dist <= inflate:
                    self.blocked[self._index(cx, cy)] = 1
                elif soft_margin > 0 and dist <= total_margin:
                    self.near_obstacle[self._index(cx, cy)] = 1

    # ---------- Если старт/цель попали в заблокированную клетку ----------

    def _nearest_free_cell(self, cx, cy, max_radius=8):
        if not self.is_blocked(cx, cy):
            return (cx, cy)
        for radius in range(1, max_radius + 1):
            best = None
            best_dist_sq = None
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if max(abs(dx), abs(dy)) != radius:
                        continue
                    ncx, ncy = cx + dx, cy + dy
                    if not self.in_bounds(ncx, ncy) or self.is_blocked(ncx, ncy):
                        continue
                    dist_sq = dx * dx + dy * dy
                    if best is None or dist_sq < best_dist_sq:
                        best, best_dist_sq = (ncx, ncy), dist_sq
            if best is not None:
                return best
        return None

    # ---------- A* ----------

    _NEIGHBORS = (
        (1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
        (1, 1, math.sqrt(2)), (1, -1, math.sqrt(2)),
        (-1, 1, math.sqrt(2)), (-1, -1, math.sqrt(2)),
    )

    @staticmethod
    def _octile(dx, dy):
        dx, dy = abs(dx), abs(dy)
        return (dx + dy) + (math.sqrt(2) - 2) * min(dx, dy)

    def find_path(self, start_world, goal_world, max_nodes=6000):
        start_cell = self._nearest_free_cell(*self.world_to_cell(*start_world))
        goal_cell = self._nearest_free_cell(*self.world_to_cell(*goal_world))
        if start_cell is None or goal_cell is None:
            return None

        if start_cell == goal_cell:
            return [goal_world]

        open_heap = [(0.0, 0, start_cell)]
        counter = 0
        g_score = {start_cell: 0.0}
        came_from = {}
        closed = set()
        found = False
        visited_nodes = 0

        while open_heap:
            _, _, current = heapq.heappop(open_heap)
            if current in closed:
                continue
            closed.add(current)
            visited_nodes += 1

            if current == goal_cell:
                found = True
                break
            if visited_nodes > max_nodes:
                break

            cx, cy = current
            for dx, dy, cost in self._NEIGHBORS:
                nx, ny = cx + dx, cy + dy
                if not self.in_bounds(nx, ny) or self.is_blocked(nx, ny):
                    continue
                # Запрещаем "срезать" по диагонали через угол двух заблокированных клеток
                if dx != 0 and dy != 0:
                    if self.is_blocked(cx + dx, cy) and self.is_blocked(cx, cy + dy):
                        continue
                neighbor = (nx, ny)
                if neighbor in closed:
                    continue

                step_cost = cost
                if self.near_obstacle[self._index(nx, ny)]:
                    step_cost *= NAV_WALL_CLEARANCE_PENALTY  # НОВОЕ: путь предпочитает держаться подальше от стен

                tentative_g = g_score[current] + step_cost
                if tentative_g < g_score.get(neighbor, float('inf')):
                    g_score[neighbor] = tentative_g
                    came_from[neighbor] = current
                    counter += 1
                    f = tentative_g + self._octile(goal_cell[0] - nx, goal_cell[1] - ny)
                    heapq.heappush(open_heap, (f, counter, neighbor))

        if not found:
            return None

        cell_path = [goal_cell]
        node = goal_cell
        while node != start_cell:
            node = came_from.get(node)
            if node is None:
                return None
            cell_path.append(node)
        cell_path.reverse()

        raw_points = [start_world]
        for cx, cy in cell_path[1:-1]:
            raw_points.append(self.cell_center(cx, cy))
        raw_points.append(goal_world)

        smoothed = self._smooth_path(raw_points)
        return smoothed[1:] if smoothed and smoothed[0] == start_world else smoothed

    # ---------- Сглаживание маршрута ----------

    def _line_of_sight(self, p1, p2):
        x0, y0 = self.world_to_cell(*p1)
        x1, y1 = self.world_to_cell(*p2)

        if self.is_blocked(x0, y0) or self.is_blocked(x1, y1):
            return False

        dist = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if dist < 1e-6:
            return True

        step = self.cell_size / 4.0
        steps = max(1, int(dist / step))
        dx = (p2[0] - p1[0]) / steps
        dy = (p2[1] - p1[1]) / steps

        prev_cell = (x0, y0)
        for i in range(1, steps + 1):
            px = p1[0] + dx * i
            py = p1[1] + dy * i
            cx, cy = self.world_to_cell(px, py)
            if self.is_blocked(cx, cy):
                return False
            if (cx, cy) != prev_cell:
                pcx, pcy = prev_cell
                if pcx != cx and pcy != cy:
                    if self.is_blocked(cx, pcy) and self.is_blocked(pcx, cy):
                        return False
                prev_cell = (cx, cy)

        return True

    def _smooth_path(self, points):
        if len(points) <= 2:
            return points
        result = [points[0]]
        anchor = 0
        while anchor < len(points) - 1:
            farthest = anchor + 1
            for j in range(anchor + 2, len(points)):
                if self._line_of_sight(points[anchor], points[j]):
                    farthest = j
                else:
                    break
            result.append(points[farthest])
            anchor = farthest
        return result

    # ---------- Разметка круглых препятствий (шипы) ----------

    def mark_circle(self, x, y, radius, soft_margin=0):
        total_radius = radius + soft_margin
        min_x, max_x = x - total_radius, x + total_radius
        min_y, max_y = y - total_radius, y + total_radius

        c_min_x, c_min_y = self.world_to_cell(min_x, min_y)
        c_max_x, c_max_y = self.world_to_cell(max_x, max_y)

        for cy in range(c_min_y, c_max_y + 1):
            for cx in range(c_min_x, c_max_x + 1):
                center_x, center_y = self.cell_center(cx, cy)
                dist = math.hypot(center_x - x, center_y - y)
                if dist <= radius:
                    self.blocked[self._index(cx, cy)] = 1
                elif soft_margin > 0 and dist <= total_radius:
                    self.near_obstacle[self._index(cx, cy)] = 1

    # ---------- Разметка непроходимых клеток по биому (например, море) ----------

    def mark_biome(self, biome_grid, biome_type):
        if biome_grid is None:
            return
        for cy in range(self.rows):
            for cx in range(self.cols):
                wx, wy = self.cell_center(cx, cy)
                if biome_grid.get_at(wx, wy) == biome_type:
                    self.blocked[self._index(cx, cy)] = 1

class SpatialGrid:

    def __init__(self, cell_size=200):
        self.cell_size = cell_size
        self.buckets = {}

    def clear(self):
        self.buckets.clear()

    def _cell(self, x, y):
        return (int(x // self.cell_size), int(y // self.cell_size))

    def build(self, objects):
        self.clear()
        for obj in objects:
            key = self._cell(obj.x, obj.y)
            self.buckets.setdefault(key, []).append(obj)

    def query_nearby(self, x, y, radius):
        min_cx, min_cy = self._cell(x - radius, y - radius)
        max_cx, max_cy = self._cell(x + radius, y + radius)
        result = []
        for cy in range(min_cy, max_cy + 1):
            for cx in range(min_cx, max_cx + 1):
                bucket = self.buckets.get((cx, cy))
                if bucket:
                    result.extend(bucket)
        return result


class BasePathfinder:
    def __init__(self, entity):
        self.c = entity

    def resolve_path(self, goal, dt, nav_grid=None, wall_polylines=None, biome_grid=None,
                      fallback_nav_grid=None):
        c = self.c
        if goal is None:
            self.reset_navigation()
            return None

        if c.following_road_active:
            blocked_by_wall = wall_polylines and geometry.segment_blocked_by_polylines(
                c.x, c.y, goal[0], goal[1], wall_polylines)
            blocked_by_sea = (
                    biome_grid is not None
                    and (biome_grid.get_at(goal[0], goal[1]) == BIOME_SEA
                         or biome_grid.get_at(c.x, c.y) == BIOME_SEA)
            )
            if blocked_by_wall or blocked_by_sea:
                return self._update_navigation(goal, nav_grid, dt, fallback_nav_grid=fallback_nav_grid)
            self.reset_navigation()
            return goal

        return self._update_navigation(goal, nav_grid, dt, fallback_nav_grid=fallback_nav_grid)

    def _update_navigation(self, goal, nav_grid, dt, fallback_nav_grid=None):
        c = self.c

        if c.nav_recalc_timer > 0:
            c.nav_recalc_timer -= dt

        goal_changed = (
            c.nav_goal is None or
            math.hypot(c.nav_goal[0] - goal[0], c.nav_goal[1] - goal[1]) > NAV_GOAL_CHANGE_THRESHOLD
        )
        path_exhausted = not c.nav_path or c.nav_path_index >= len(c.nav_path)
        needs_recalc = nav_grid is not None and (goal_changed or path_exhausted or c.nav_recalc_timer <= 0)

        if needs_recalc:
            path = nav_grid.find_path((c.x, c.y), goal, max_nodes=NAV_MAX_ASTAR_NODES)
            if not path and fallback_nav_grid is not None:
                path = fallback_nav_grid.find_path((c.x, c.y), goal, max_nodes=NAV_MAX_ASTAR_NODES)
            c.nav_goal = goal
            c.nav_recalc_timer = random.uniform(*NAV_PATH_RECALC_INTERVAL)
            if path:
                c.nav_path = path
            else:
                c.nav_path = []
            c.nav_path_index = 0

        if not c.nav_path:
            return goal if nav_grid is None else (c.x, c.y)

        while (c.nav_path_index < len(c.nav_path) - 1 and
               math.hypot(c.x - c.nav_path[c.nav_path_index][0],
                          c.y - c.nav_path[c.nav_path_index][1]) < NAV_WAYPOINT_REACHED_DISTANCE):
            c.nav_path_index += 1

        return c.nav_path[c.nav_path_index]

    def reset_navigation(self):
        c = self.c
        c.nav_path = []
        c.nav_path_index = 0
        c.nav_goal = None
        c.nav_recalc_timer = 0.0

    # ---------- Движение ----------

    def move_towards(self, target, dt, biome_grid=None, wall_polylines=None):
        c = self.c
        if target is None:
            return
        tx, ty = target
        dx = tx - c.x
        dy = ty - c.y
        dist = math.hypot(dx, dy)
        if dist < 2:
            return
        speed = self.compute_speed(dt, biome_grid=biome_grid) * c.speed_factor
        step = min(speed * dt, dist)
        new_x = c.x + (dx / dist) * step
        new_y = c.y + (dy / dist) * step
        new_x = max(15, min(new_x, settings.WORLD_WIDTH - 15))
        new_y = max(15, min(new_y, settings.WORLD_HEIGHT - 15))

        if wall_polylines:
            new_x, new_y = self._resolve_wall_collision(new_x, new_y, wall_polylines)

        c.x, c.y = new_x, new_y

    def _resolve_wall_collision(self, x, y, wall_polylines):
        c = self.c
        radius = getattr(c, "radius", 10)
        return geometry.resolve_circle_vs_polylines(x, y, radius, wall_polylines, WALL_THICKNESS)

    # ---------- Точка расширения для конкретной расы ----------

    def compute_speed(self, dt, biome_grid=None):
        return DEFAULT_SPEED