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

def resolve_circle_vs_polylines(x, y, radius, polylines, thickness, iterations=2):
    clearance = radius + thickness / 2
    for _ in range(iterations):
        closest = None
        closest_dist = clearance
        for points in polylines:
            for i in range(len(points) - 1):
                ax, ay = points[i]
                bx, by = points[i + 1]
                cx, cy = closest_point_on_segment(x, y, ax, ay, bx, by)
                d = math.hypot(x - cx, y - cy)
                if d < closest_dist:
                    closest_dist = d
                    closest = (x - cx, y - cy, d)
        if closest is None:
            break
        ddx, ddy, d = closest
        if d < 1e-6:
            ddx, ddy, d = 0.0, -1.0, 1.0
        push = clearance - d
        x += (ddx / d) * push
        y += (ddy / d) * push
    return x, y

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

def ray_segment_intersection(ox, oy, dx, dy, ax, ay, bx, by):
    v1x, v1y = ox - ax, oy - ay
    v2x, v2y = bx - ax, by - ay
    v3x, v3y = -dy, dx
    dot = v2x * v3x + v2y * v3y
    if abs(dot) < 1e-9:
        return None
    t1 = (v2x * v1y - v2y * v1x) / dot
    t2 = (v1x * v3x + v1y * v3y) / dot
    if t1 >= 0 and 0 <= t2 <= 1:
        return t1
    return None

def visibility_polygon(cx, cy, radius, blocking_polylines, num_rays=180, corner_epsilon=0.0006):
    segments = []
    for points in blocking_polylines:
        for i in range(len(points) - 1):
            ax, ay = points[i]
            bx, by = points[i + 1]
            if max(ax, bx) + radius < cx or min(ax, bx) - radius > cx:
                continue
            if max(ay, by) + radius < cy or min(ay, by) - radius > cy:
                continue
            segments.append((ax, ay, bx, by))

    if not segments:
        return [
            (cx + math.cos(2 * math.pi * i / num_rays) * radius,
             cy + math.sin(2 * math.pi * i / num_rays) * radius)
            for i in range(num_rays)
        ]

    TWO_PI = 2 * math.pi
    angles = {(2 * math.pi * i / num_rays) % TWO_PI for i in range(num_rays)}

    for ax, ay, bx, by in segments:
        for px, py in ((ax, ay), (bx, by)):
            dx, dy = px - cx, py - cy
            dist = math.hypot(dx, dy)
            if dist < 1e-6 or dist > radius * 1.4:
                continue
            base_angle = math.atan2(dy, dx) % TWO_PI
            angles.add((base_angle - corner_epsilon) % TWO_PI)
            angles.add(base_angle)
            angles.add((base_angle + corner_epsilon) % TWO_PI)

    points = []
    for angle in sorted(angles):
        dx, dy = math.cos(angle), math.sin(angle)
        closest = radius
        for ax, ay, bx, by in segments:
            t = ray_segment_intersection(cx, cy, dx, dy, ax, ay, bx, by)
            if t is not None and t < closest:
                closest = t
        points.append((cx + dx * closest, cy + dy * closest))

    return points

def weld_polyline_endpoints(polylines, tolerance=18):
    welded = [list(points) for points in polylines]

    for i, points in enumerate(welded):
        if not points:
            continue
        end_indices = (0,) if len(points) < 2 else (0, -1)
        for end_index in end_indices:
            px, py = points[end_index]
            best_point = None
            best_dist = tolerance
            for j, other in enumerate(welded):
                if j == i or len(other) < 2:
                    continue
                for k in range(len(other) - 1):
                    ax, ay = other[k]
                    bx, by = other[k + 1]
                    cx, cy = closest_point_on_segment(px, py, ax, ay, bx, by)
                    d = math.hypot(px - cx, py - cy)
                    if d < best_dist:
                        best_dist = d
                        best_point = (cx, cy)
            if best_point is not None:
                points[end_index] = best_point

    return welded