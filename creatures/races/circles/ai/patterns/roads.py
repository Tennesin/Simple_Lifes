import math
import random

from settings import *
from ...ci_settings import *
from ...ci_info import *
from .....all_needed.ai.utility import Consideration, GoalComponent

# =========================================================================
# Дороги, нарисованные игроком, и перекрёстки
# =========================================================================

class Roads(GoalComponent):
    SCORE_COMMITTED = 40.0
    SCORE_BASE = 15.0
    SCORE_CURIOSITY_FACTOR = 15.0

    def __init__(self, creature, follow_dampener=1.0):
        self.c = creature
        self.follow_dampener = follow_dampener

    def consider(self, ctx):
        c = self.c
        if c.following_road is not None:
            score = self.SCORE_COMMITTED
        else:
            if not ctx.visible_roads:
                return [None]
            score = self.SCORE_BASE + c.curiosity * self.SCORE_CURIOSITY_FACTOR

        def execute():
            return self._pursue(ctx)

        return [Consideration("road", score, execute)]

    def pursue_known_link(self, resource_type, ctx):
        """Публичный вход для SurvivalNeeds - дойти до ресурса по уже
        известной дороге, минуя обычный цикл consider()."""
        c = self.c
        link = c.known_road_links.get(resource_type)
        if link is None:
            return None
        road = next((r for r in ctx.all_roads if r.id == link["road_id"]), None)
        if road is None or not road.points:
            c.known_road_links.pop(resource_type, None)
            return None
        if c.known_roads.get(road.id) == "dangerous":
            c.known_road_links.pop(resource_type, None)
            return None
        endpoint = road.endpoint_a if link["target_end"] == "a" else road.endpoint_b
        if endpoint is None or ROAD_LINK_RESOURCE_MAP.get(endpoint["type"]) != resource_type:
            c.known_road_links.pop(resource_type, None)
            return None
        if c.following_road is not road:
            target_index = 0 if link["target_end"] == "a" else len(road.points) - 1
            self._start_following(road, target_index=target_index)
            c.goal_text = INFO_CREATURE_GOAL_ROAD_KNOWN_ROUTE
            return c.target
        return self._continue_following(ctx)

    def _pursue(self, ctx):
        c = self.c
        if c.following_road is not None:
            return self._continue_following(ctx)

        if c.road_follow_check_timer > 0:
            return None
        c.road_follow_check_timer = random.uniform(*ROAD_FOLLOW_REROLL_INTERVAL)

        candidates = [r for r in ctx.visible_roads if c.known_roads.get(r.id) not in ("useless", "dangerous")]
        if not candidates:
            return None

        effective_chance = c.curiosity * ROAD_FOLLOW_CHANCE_FACTOR * self.follow_dampener * c.psyche.curiosity_modifier()
        if random.random() >= effective_chance:
            return None

        road = min(candidates, key=lambda r: min(
            math.hypot(c.x - r.points[0][0], c.y - r.points[0][1]),
            math.hypot(c.x - r.points[-1][0], c.y - r.points[-1][1])
        ))
        self._start_following(road)
        c.goal_text = INFO_CREATURE_GOAL_ROAD_APPROACH
        return c.target

    def _start_following(self, road, target_index=None, entry_already_reached=False):
        c = self.c
        c.following_road = road
        c.road_progress = min(range(len(road.points)),
                              key=lambda i: math.hypot(c.x - road.points[i][0], c.y - road.points[i][1]))
        if target_index is None:
            dist_to_start = math.hypot(c.x - road.points[0][0], c.y - road.points[0][1])
            dist_to_end = math.hypot(c.x - road.points[-1][0], c.y - road.points[-1][1])
            c.road_direction = 1 if dist_to_start <= dist_to_end else -1
        else:
            c.road_direction = 1 if target_index >= c.road_progress else -1
        c.road_entry_reached = entry_already_reached
        c.state = STATE_SEEKING
        c.following_road_active = entry_already_reached
        c.target = road.points[c.road_progress]

    def _continue_following(self, ctx):
        c = self.c
        road = c.following_road
        if not road.points:
            c.following_road = None
            c.following_road_active = False
            c.road_entry_reached = False
            return None
        if c.road_progress < 0 or c.road_progress >= len(road.points):
            self._evaluate_end(road, ctx)
            return None

        target_point = road.points[c.road_progress]
        if math.hypot(c.x - target_point[0], c.y - target_point[1]) < 14:
            c.road_entry_reached = True
            switched = self._maybe_switch_at_crossing(road, target_point, ctx)
            if switched:
                road = c.following_road
            else:
                c.road_progress += c.road_direction
                if c.road_progress < 0 or c.road_progress >= len(road.points):
                    self._evaluate_end(road, ctx)
                    return None
            target_point = road.points[c.road_progress]

        c.state = STATE_SEEKING
        c.target = target_point
        if c.road_entry_reached:
            c.goal_text = INFO_CREATURE_GOAL_ROAD_FOLLOW
            c.following_road_active = True
        else:
            c.goal_text = INFO_CREATURE_GOAL_ROAD_APPROACH
            c.following_road_active = False
        return target_point

    def _active_seeking_resource(self):
        c = self.c
        if c.seeking_food:
            return "food"
        if c.seeking_water:
            return "water"
        return None

    def _maybe_switch_at_crossing(self, road, point, ctx):
        c = self.c
        road_crossings, all_roads = ctx.road_crossings, ctx.all_roads
        if not road_crossings or not all_roads:
            return False
        crossing = next((cr for cr in road_crossings
                         if math.hypot(cr.x - point[0], cr.y - point[1]) < CROSSING_POINT_TOLERANCE), None)
        if crossing is None or len(crossing.road_ids) < 2:
            return False
        other_road_ids = [rid for rid in crossing.road_ids if rid != road.id]
        if not other_road_ids:
            return False

        target_resource = self._active_seeking_resource()
        if target_resource is not None:
            link = c.known_road_links.get(target_resource)
            if link and link["road_id"] in other_road_ids:
                candidate_road = next((r for r in all_roads if r.id == link["road_id"]), None)
                if candidate_road is not None and candidate_road.points:
                    target_index = 0 if link["target_end"] == "a" else len(candidate_road.points) - 1
                    self._start_following(candidate_road, target_index=target_index, entry_already_reached=True)
                    c.goal_text = INFO_CREATURE_GOAL_ROAD_CROSSING_KNOWN
                    return True

        if random.random() < c.curiosity * CROSSING_SWITCH_CHANCE_FACTOR * c.psyche.curiosity_modifier():
            chosen_id = random.choice(other_road_ids)
            candidate_road = next((r for r in all_roads if r.id == chosen_id), None)
            if candidate_road is not None and candidate_road.points:
                self._start_following(candidate_road, entry_already_reached=True)
                c.goal_text = INFO_CREATURE_GOAL_ROAD_CROSSING_SWITCH
                return True
        return False

    def _evaluate_end(self, road, ctx):
        c = self.c
        ex, ey = road.points[-1] if c.road_direction > 0 else road.points[0]
        self._learn_link_on_arrival(road)

        useful_objects = (ctx.visible_fruits + ctx.visible_water + ctx.visible_bushes
                          + ctx.visible_campfires + ctx.visible_trees + ctx.visible_stones)
        helpful = any(math.hypot(ex - o.x, ey - o.y) < ROAD_OUTCOME_RADIUS for o in useful_objects)

        if not helpful:
            structures = (list(ctx.graveyards) + list(ctx.houses) + list(ctx.storage_fields)
                          + list(ctx.campfires) + list(ctx.construction_sites))
            helpful = any(
                self._distance_to_structure(obj, ex, ey) < ROAD_OUTCOME_RADIUS
                for obj in structures
            )

        # ---------- Река у конца дороги ----------
        if not helpful and ctx.biome_grid is not None:
            helpful = ctx.biome_grid.get_at(ex, ey) == BIOME_RIVER

        # ---------- Травяная поляна поблизости ----------
        if not helpful and ctx.all_grass:
            helpful = any(math.hypot(ex - g.x, ey - g.y) < ROAD_OUTCOME_RADIUS for g in ctx.all_grass)

        nearby_danger = sum(1 for t in ctx.all_threats if math.hypot(ex - t.x, ey - t.y) < ROAD_OUTCOME_RADIUS)

        if helpful and nearby_danger == 0:
            verdict = "useful"
            c.goal_text = INFO_CREATURE_GOAL_ROAD_USEFUL
        elif nearby_danger >= ROAD_DANGEROUS_THRESHOLD or (not helpful and nearby_danger > 0):
            verdict = "useless"
            c.goal_text = INFO_CREATURE_GOAL_ROAD_USELESS_DANGER
        elif not helpful:
            verdict = "useless"
            c.goal_text = INFO_CREATURE_GOAL_ROAD_EMPTY
        else:
            verdict = "useful"
            c.goal_text = INFO_CREATURE_GOAL_ROAD_USEFUL_SIMPLE

        c.known_roads[road.id] = verdict
        road.rating = verdict
        c.following_road = None
        c.following_road_active = False
        c.road_entry_reached = False
        c.road_progress = 0

    def _learn_link_on_arrival(self, road):
        c = self.c
        reached_end_key = "b" if c.road_direction > 0 else "a"
        endpoint = road.endpoint_b if c.road_direction > 0 else road.endpoint_a
        if endpoint is None:
            return
        resource = ROAD_LINK_RESOURCE_MAP.get(endpoint["type"])
        if resource is None:
            return
        c.known_road_links[resource] = {"road_id": road.id, "target_end": reached_end_key}

    @staticmethod
    def _distance_to_structure(obj, px, py):
        if hasattr(obj, "distance_to_point"):
            return obj.distance_to_point(px, py)
        return math.hypot(px - obj.x, py - obj.y)

# =========================================================================
# Физическая проверка детской дороги взрослым
# =========================================================================

class ChildRoadVerification(GoalComponent):
    SCORE_COMMITTED = 42.0
    SCORE_NEW = 18.0

    def __init__(self, creature):
        self.c = creature

    def consider(self, ctx):
        c = self.c

        if c.child_road_verify_target_id is not None:
            def execute():
                return self._pursue(ctx)
            return [Consideration("child_road_verify", self.SCORE_COMMITTED, execute)]

        if c.child_road_verify_check_timer > 0:
            c.child_road_verify_check_timer -= ctx.dt
            return [None]
        c.child_road_verify_check_timer = random.uniform(*CHILD_ROAD_VERIFY_CHECK_INTERVAL)

        pending_roads = [r for r in ctx.visible_child_roads
                         if r.rating == "pending" and len(r.points) >= 2
                         and not self._is_claimed_by_active_verifier(r, ctx.other_creatures)]
        if not pending_roads:
            return [None]

        def execute():
            return self._start(pending_roads)

        return [Consideration("child_road_verify", self.SCORE_NEW, execute)]

    @staticmethod
    def _is_claimed_by_active_verifier(road, other_creatures):
        if road.verifier_id is None:
            return False
        claimant = next((o for o in other_creatures if o.id == road.verifier_id), None)
        if claimant is None or claimant.is_dead:
            return False
        return claimant.child_road_verify_target_id == road.id

    def _start(self, pending_roads):
        c = self.c
        road = min(pending_roads, key=lambda r: min(
            math.hypot(c.x - r.points[0][0], c.y - r.points[0][1]),
            math.hypot(c.x - r.points[-1][0], c.y - r.points[-1][1])
        ))
        road.verifier_id = c.id

        c.child_road_verify_target_id = road.id
        c.child_road_verify_found_danger = False
        c.child_road_verify_entry_reached = False
        c.child_road_verify_progress = min(
            range(len(road.points)),
            key=lambda i: math.hypot(c.x - road.points[i][0], c.y - road.points[i][1])
        )
        dist_to_start = math.hypot(c.x - road.points[0][0], c.y - road.points[0][1])
        dist_to_end = math.hypot(c.x - road.points[-1][0], c.y - road.points[-1][1])
        c.child_road_verify_direction = 1 if dist_to_start <= dist_to_end else -1

        c.state = STATE_SEEKING
        c.goal_text = INFO_CREATURE_GOAL_CHILD_ROAD_VERIFY
        c.target = road.points[c.child_road_verify_progress]
        return c.target

    def _pursue(self, ctx):
        c = self.c
        road = next((r for r in ctx.all_child_roads if r.id == c.child_road_verify_target_id), None)
        if road is None or road.rating != "pending" or not road.points:
            self._cancel(road)
            return None

        if any(math.hypot(c.x - s.x, c.y - s.y) < CHILD_ROAD_SAFETY_CHECK_RADIUS for s in ctx.visible_spikes):
            c.child_road_verify_found_danger = True

        if c.child_road_verify_progress < 0 or c.child_road_verify_progress >= len(road.points):
            self._finish(road)
            return None

        target_point = road.points[c.child_road_verify_progress]
        if math.hypot(c.x - target_point[0], c.y - target_point[1]) < 14:
            c.child_road_verify_entry_reached = True
            c.child_road_verify_progress += c.child_road_verify_direction
            if c.child_road_verify_progress < 0 or c.child_road_verify_progress >= len(road.points):
                self._finish(road)
                return None
            target_point = road.points[c.child_road_verify_progress]

        c.state = STATE_SEEKING
        c.goal_text = INFO_CREATURE_GOAL_CHILD_ROAD_VERIFY
        c.target = target_point
        c.following_road_active = c.child_road_verify_entry_reached
        return target_point

    def _finish(self, road):
        c = self.c
        road.rating = "dangerous" if c.child_road_verify_found_danger else "safe"
        road.checked_by = c.id
        road.verifier_id = None
        c.goal_text = (INFO_CREATURE_GOAL_CHILD_ROAD_VERIFY_DANGER if c.child_road_verify_found_danger
                       else INFO_CREATURE_GOAL_CHILD_ROAD_VERIFY_SAFE)
        c.child_road_verify_target_id = None
        c.child_road_verify_progress = 0
        c.child_road_verify_found_danger = False
        c.child_road_verify_entry_reached = False
        c.following_road_active = False

    def _cancel(self, road=None):
        c = self.c
        if road is not None and road.verifier_id == c.id:
            road.verifier_id = None
        c.child_road_verify_target_id = None
        c.child_road_verify_progress = 0
        c.child_road_verify_found_danger = False
        c.child_road_verify_entry_reached = False
        c.following_road_active = False