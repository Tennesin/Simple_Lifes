"""Единый трекер прогресса движения по ломаной линии (дорога
/ детская дорога / проверка детской дороги)."""

import math

class PathProgressTracker:

    ARRIVAL_DISTANCE = 14

    @staticmethod
    def start(points, from_x, from_y, target_index=None):
        """Стартовый (progress_index, direction) для движения по points
        из точки (from_x, from_y)."""
        if not points:
            return 0, 1
        progress_index = min(
            range(len(points)),
            key=lambda i: math.hypot(from_x - points[i][0], from_y - points[i][1])
        )
        if target_index is None:
            dist_to_start = math.hypot(from_x - points[0][0], from_y - points[0][1])
            dist_to_end = math.hypot(from_x - points[-1][0], from_y - points[-1][1])
            direction = 1 if dist_to_start <= dist_to_end else -1
        else:
            direction = 1 if target_index >= progress_index else -1
        return progress_index, direction

    @staticmethod
    def has_arrived(points, index, cur_x, cur_y, arrival_distance=ARRIVAL_DISTANCE):
        if not points or index < 0 or index >= len(points):
            return False
        px, py = points[index]
        return math.hypot(cur_x - px, cur_y - py) < arrival_distance

    @staticmethod
    def advance(points, index, direction):
        """Двигает индекс на direction. Возвращает (new_index, finished)."""
        new_index = index + direction
        finished = new_index < 0 or new_index >= len(points)
        return new_index, finished

    @staticmethod
    def target_point(points, index):
        if not points or index < 0 or index >= len(points):
            return None
        return points[index]