import math
import random
import settings

def clamped_point(origin_x, origin_y, angle, dist):
    tx = origin_x + math.cos(angle) * dist
    ty = origin_y + math.sin(angle) * dist
    return (max(20, min(tx, settings.WORLD_WIDTH - 20)),
            max(20, min(ty, settings.WORLD_HEIGHT - 20)))


def flee_point(x, y, from_pos, distance):
    dx = x - from_pos[0]
    dy = y - from_pos[1]
    dist = math.hypot(dx, dy)
    if dist == 0:
        angle = random.uniform(0, 2 * math.pi)
        dx, dy = math.cos(angle), math.sin(angle)
        dist = 1
    return (x + dx / dist * distance, y + dy / dist * distance)

def point_segment_distance(px, py, ax, ay, bx, by):
    abx, aby = bx - ax, by - ay
    apx, apy = px - ax, py - ay
    ab_len_sq = abx * abx + aby * aby
    if ab_len_sq == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0, min(1, (apx * abx + apy * aby) / ab_len_sq))
    return math.hypot(px - (ax + t * abx), py - (ay + t * aby))

def closest_point_on_segment(px, py, ax, ay, bx, by):
    abx, aby = bx - ax, by - ay
    apx, apy = px - ax, py - ay
    ab_len_sq = abx * abx + aby * aby
    if ab_len_sq == 0:
        return (ax, ay)
    t = max(0.0, min(1.0, (apx * abx + apy * aby) / ab_len_sq))
    return (ax + t * abx, ay + t * aby)

def clamp(value, lo, hi):
    return max(lo, min(hi, value))

class ObstaclePoint:
    __slots__ = ("x", "y", "radius")

    def __init__(self, x, y, radius):
        self.x = x
        self.y = y
        self.radius = radius


def segments_intersect(p1, p2, p3, p4):
    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])
    return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)


def segment_blocked_by_polylines(x1, y1, x2, y2, polylines):
    p1, p2 = (x1, y1), (x2, y2)
    min_x, max_x = (x1, x2) if x1 <= x2 else (x2, x1)
    min_y, max_y = (y1, y2) if y1 <= y2 else (y2, y1)
    for points in polylines:
        for i in range(len(points) - 1):
            ax, ay = points[i]
            bx, by = points[i + 1]
            if max(ax, bx) < min_x or min(ax, bx) > max_x:
                continue
            if max(ay, by) < min_y or min(ay, by) > max_y:
                continue
            if segments_intersect(p1, p2, (ax, ay), (bx, by)):
                return True
    return False