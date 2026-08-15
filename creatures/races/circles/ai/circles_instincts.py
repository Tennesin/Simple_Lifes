import math
import random

from settings import *
from ..ci_settings import *
from ..ci_info import *
from ....all_needed import geometry

# =========================================================================
# Домен: труп сородича - подход, перенос, выбор кладбища, реакция на тревогу
# =========================================================================

class _CorpseHandlingInstinctMixin:

    def notify_elders_of_corpse(self, corpse, visible_companions):
        if corpse.being_carried_by is not None or corpse.burial_claimant_id is not None:
            return
        for other in visible_companions:
            if other.life_stage == LIFE_STAGE_OLD:
                other.graveyard_alert_pos = (corpse.x, corpse.y)
                other.graveyard_alert_timer = GRAVEYARD_ALERT_HOLD_TIME

    def pursue_corpse_burial(self, visible_corpses, graveyards):
        c = self.c

        if c.burial_target_id is not None:
            corpse = next((o for o in visible_corpses if o.id == c.burial_target_id), None)
            if corpse is None or corpse.burial_claimant_id != c.id:
                c.burial_target_id = None
                c.graveyard_target_id = None
                c.is_dragging_corpse = False
            elif corpse.being_carried_by == c.id:
                return self._continue_carrying(corpse, graveyards)
            else:
                return self._approach_claimed_corpse(corpse, graveyards)

        candidates = [o for o in visible_corpses
                      if o.burial_claimant_id is None and o.being_carried_by is None]
        if candidates:
            target_corpse = min(candidates, key=c.distance_to)
            target_corpse.burial_claimant_id = c.id
            c.burial_target_id = target_corpse.id
            return self._approach_claimed_corpse(target_corpse, graveyards)

        if c.graveyard_alert_timer > 0 and c.graveyard_alert_pos is not None:
            return self._investigate_alert()

        return None

    def _approach_claimed_corpse(self, corpse, graveyards):
        c = self.c
        c.state = STATE_SEEKING
        if c.distance_to(corpse) > CORPSE_APPROACH_DISTANCE:
            c.goal_text = INFO_CREATURE_GOAL_CORPSE_APPROACH
            c.target = (corpse.x, corpse.y)
            return c.target

        corpse.being_carried_by = c.id
        return self._continue_carrying(corpse, graveyards)

    def _continue_carrying(self, corpse, graveyards):
        c = self.c
        c.is_dragging_corpse = True
        c.state = STATE_SEEKING
        c.speed_factor = CORPSE_DRAG_SPEED_FACTOR
        c.goal_text = INFO_CREATURE_GOAL_CORPSE_CARRY

        target_graveyard = next((g for g in graveyards if g.id == c.graveyard_target_id), None)
        if target_graveyard is None:
            target_graveyard = self._choose_graveyard(graveyards)
            c.graveyard_target_id = target_graveyard.id if target_graveyard else None

        if target_graveyard is None:
            c.target = self.pursue_search_target()
            return c.target

        c.target = (target_graveyard.x, target_graveyard.y)
        return c.target

    def _choose_graveyard(self, graveyards):
        c = self.c
        if not graveyards:
            return None
        known_pos = self.nearest_known_graveyard()
        if known_pos:
            return min(graveyards, key=lambda g: math.hypot(g.x - known_pos[0], g.y - known_pos[1]))
        return min(graveyards, key=c.distance_to)

    def _investigate_alert(self):
        c = self.c
        c.state = STATE_SEEKING
        c.goal_text = INFO_CREATURE_GOAL_CORPSE_ALERT
        if math.hypot(c.x - c.graveyard_alert_pos[0], c.y - c.graveyard_alert_pos[1]) < CORPSE_APPROACH_DISTANCE * 2:
            c.graveyard_alert_pos = None
            c.graveyard_alert_timer = 0.0
            return None
        c.target = c.graveyard_alert_pos
        return c.target

    def flee_to_campfire(self, threat_pos):
        c = self.c
        c.state = STATE_PANIC
        c.panic_active = True
        campfire_pos = self.nearest_known_campfire()
        if campfire_pos:
            c.goal_text = INFO_CREATURE_GOAL_CORPSE_FLEE_FIRE
            c.target = campfire_pos
            return campfire_pos
        c.goal_text = INFO_CREATURE_GOAL_CORPSE_FLEE_BLIND
        c.target = c.flee_point(threat_pos, PANIC_SCAN_DISTANCE)
        return c.target


# =========================================================================
# Домен: поиск места для сна
# =========================================================================

class _SleepInstinctMixin:

    def seek_sleep_spot(self, biome_grid=None):
        c = self.c
        campfire_pos = None
        campfire_memories = c.memory.get_campfire_memories()
        if campfire_memories:
            campfire_pos = min(campfire_memories, key=lambda pos: math.hypot(c.x - pos[0], c.y - pos[1]))
        elif c.known_campfire:
            campfire_pos = c.known_campfire

        if campfire_pos:
            # ---------- Конкретная точка рядом с костром, а не любое место в его широкой зоне действия ----------
            needs_new_spot = (
                    c.sleep_spot is None or c.sleep_spot_campfire is None or
                    math.hypot(c.sleep_spot_campfire[0] - campfire_pos[0],
                               c.sleep_spot_campfire[1] - campfire_pos[1]) > 5
            )
            if needs_new_spot:
                angle = random.uniform(0, 2 * math.pi)
                dist = random.uniform(SLEEP_SPOT_MIN_DISTANCE, CAMPFIRE_RADIUS * SLEEP_SPOT_MAX_RADIUS_FACTOR)
                c.sleep_spot = geometry.clamped_point(campfire_pos[0], campfire_pos[1], angle, dist)
                c.sleep_spot_campfire = campfire_pos

            dist_to_spot = math.hypot(c.x - c.sleep_spot[0], c.y - c.sleep_spot[1])
            if dist_to_spot > SLEEP_SPOT_ARRIVAL_DISTANCE:
                c.goal_text = INFO_CREATURE_GOAL_SLEEP_GO_FIRE
                c.target = c.sleep_spot
                return c.sleep_spot
            c.goal_text = INFO_CREATURE_GOAL_SLEEP_AT_FIRE
            c.target = (c.x, c.y)
            c.is_sleeping = True
            c.sleep_forced = False
            return c.target

        intuitive = c.memory.get_campfire_intuitive_target(*c.comfort_point)
        if intuitive:
            c.goal_text = INFO_CREATURE_GOAL_SLEEP_INTUITIVE
            c.target = intuitive
            return intuitive

        c.goal_text = INFO_CREATURE_GOAL_SLEEP_ON_MOVE
        return self.pursue_search_target(biome_grid=biome_grid)


# =========================================================================
# Домен: поиск знакомых ориентиров (костёр/кладбище/склад) и их регистрация
# =========================================================================

class _LandmarkLookupMixin:

    def nearest_known_campfire(self):
        c = self.c
        if c.known_campfire:
            return c.known_campfire
        campfire_memories = c.memory.get_campfire_memories()
        if campfire_memories:
            return min(campfire_memories, key=lambda pos: math.hypot(c.x - pos[0], c.y - pos[1]))
        return None

    def is_near_known_campfire(self):
        c = self.c
        pos = self.nearest_known_campfire()
        if pos is None:
            return False
        return math.hypot(c.x - pos[0], c.y - pos[1]) < CAMPFIRE_RADIUS

    def nearest_known_graveyard(self):
        c = self.c
        memories = c.memory.get_graveyard_memories()
        if memories:
            return min(memories, key=lambda pos: math.hypot(c.x - pos[0], c.y - pos[1]))
        return c.known_graveyard

    def find_storage_field(self, storage_fields):
        campfire_pos = self.nearest_known_campfire()
        if campfire_pos is None or not storage_fields:
            return None
        for field in storage_fields:
            if field.is_owned_by_campfire(campfire_pos):
                return field
        return None

    def register_landmarks(self, visible_water, visible_bushes, visible_campfires, dt, visible_graveyards=None):
        c = self.c
        if c.landmark_register_timer > 0:
            c.landmark_register_timer -= dt
            return
        c.landmark_register_timer = random.uniform(*LANDMARK_REGISTER_INTERVAL)

        for water in visible_water:
            c.memory.add_intuitive_memory("water", *c.comfort_point, water.x, water.y, importance=1.0)
        for bush in visible_bushes:
            c.memory.add_intuitive_memory("bush", *c.comfort_point, bush.x, bush.y, importance=1.0)
        for fire in visible_campfires:
            c.memory.add_intuitive_memory("campfire", *c.comfort_point, fire.x, fire.y, importance=1.5)
            c.memory.add_memory("campfire", fire.x, fire.y, importance=2.0)
            if c.known_campfire is None:
                c.known_campfire = (fire.x, fire.y)
                c.comfort_point = c.known_campfire
        for gy in (visible_graveyards or []):
            c.memory.add_intuitive_memory("graveyard", *c.comfort_point, gy.x, gy.y, importance=1.2)
            c.memory.add_memory("graveyard", gy.x, gy.y, importance=1.5)
            if c.known_graveyard is None:
                c.known_graveyard = (gy.x, gy.y)


# =========================================================================
# Домен: навигационные инстинкты - застревание и активный поиск без цели
# =========================================================================

class _NavigationInstinctMixin:

    def check_if_stuck(self, goal, biome_grid=None):
        c = self.c
        if c.stuck_check_timer > 0 or goal is None:
            return
        c.stuck_check_timer = STUCK_CHECK_INTERVAL
        moved = math.hypot(c.x - c.position_at_last_check[0], c.y - c.position_at_last_check[1])
        c.position_at_last_check = (c.x, c.y)

        nav_index = getattr(c, "nav_path_index", 0)
        path_advanced = nav_index > c.stuck_last_nav_index
        c.stuck_last_nav_index = nav_index

        goal_dist = math.hypot(c.x - goal[0], c.y - goal[1])
        if not path_advanced and moved < STUCK_DISTANCE_THRESHOLD and goal_dist > STUCK_DISTANCE_THRESHOLD:
            c.stuck_level += 1
            c.pathfinder.reset_navigation()
            c.following_road_active = False

            if c.stuck_level >= STUCK_ESCALATION_THRESHOLD:
                angle = random.uniform(0, 2 * math.pi)
                dist = random.uniform(*STUCK_ESCAPE_DISTANCE)
                point = geometry.clamped_point(c.x, c.y, angle, dist)
                c.target = self._avoid_sea(point, biome_grid)
                c.stuck_level = 0
            else:
                c.target = self.explore(biome_grid=biome_grid)

            c.decision_timer = random.uniform(*EXPLORE_TIMER[c.temperament])
        else:
            c.stuck_level = max(0, c.stuck_level - 1)

    def pursue_search_target(self, visible_companions=None, biome_grid=None):
        c = self.c
        if visible_companions:
            nearest = c.social.best_companion(visible_companions)
            if c.distance_to(nearest) > TALK_DISTANCE:
                c.target = (nearest.x, nearest.y)
            else:
                c.target = (c.x, c.y)
            c.decision_timer = random.uniform(*ACTIVE_SEARCH_TIMER)
            return c.target

        reached = (c.target is None or
                   math.hypot(c.x - c.target[0], c.y - c.target[1]) < 12)
        if reached or c.decision_timer <= 0:
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(*ACTIVE_SEARCH_DISTANCE)
            point = geometry.clamped_point(c.x, c.y, angle, dist)
            c.target = self._avoid_sea(point, biome_grid)
            c.decision_timer = random.uniform(*ACTIVE_SEARCH_TIMER)
        return c.target


# =========================================================================
# Домен: память о еде/воде/опасности (в т.ч. протухание точной памяти)
# =========================================================================

class _ResourceMemoryMixin:

    def _nearest_known_target(self, visible_objs, memory_positions, target_attr, extra_visible_positions=None):
        c = self.c
        visible_positions = [(o.x, o.y) for o in visible_objs]
        if extra_visible_positions:
            visible_positions = visible_positions + list(extra_visible_positions)
        candidates = visible_positions + memory_positions
        if candidates:
            target = min(candidates, key=lambda pos: math.hypot(c.x - pos[0], c.y - pos[1]))
            setattr(c, target_attr, target if target not in visible_positions else None)
            return target
        setattr(c, target_attr, None)
        return None

    def nearest_food_target(self, visible_fruits):
        c = self.c
        if not c.eats_food_type("fruit"):
            return None
        target = self._nearest_known_target(visible_fruits, c.memory.get_food_memories(), "food_memory_target")
        if target is not None:
            return target
        return c.memory.get_bush_intuitive_target(*c.comfort_point)

    def nearest_water_target(self, visible_water, biome_grid=None):
        c = self.c
        visible_water = [w for w in visible_water if w.has_water()]
        extra = []
        if biome_grid is not None:
            vision_radius = c.aging.effective_vision_radius()
            river_point = biome_grid.find_nearest_of_type(c.x, c.y, BIOME_RIVER, vision_radius)
            if river_point:
                extra.append(river_point)
        target = self._nearest_known_target(visible_water, c.memory.get_water_memories(),
                                            "water_memory_target", extra_visible_positions=extra)
        if target is not None:
            return target
        return c.memory.get_water_intuitive_target(*c.comfort_point)

    def _check_stale_memory_target(self, mem_type, target_attr, visible_objs, presence_check):
        c = self.c
        target = getattr(c, target_attr)
        if target is None:
            return
        tx, ty = target
        if math.hypot(c.x - tx, c.y - ty) > EAT_DISTANCE + 10:
            return
        still_there = any(presence_check(o, tx, ty) for o in visible_objs)
        if not still_there:
            c.memory.forget_memory(mem_type, tx, ty)
        setattr(c, target_attr, None)

    def check_stale_food_memory(self, visible_fruits):
        self._check_stale_memory_target(
            "fruit", "food_memory_target", visible_fruits,
            lambda f, tx, ty: f.active and math.hypot(f.x - tx, f.y - ty) < EAT_DISTANCE + 10)

    def check_stale_water_memory(self, visible_water):
        self._check_stale_memory_target(
            "water", "water_memory_target", visible_water,
            lambda w, tx, ty: w.has_water() and math.hypot(w.x - tx, w.y - ty) < EAT_DISTANCE + 10)

    def nearest_danger_position(self, known_threats):
        c = self.c
        candidates = [(t.x, t.y) for t in known_threats] + c.memory.get_danger_memories()
        if not candidates:
            return None
        return min(candidates, key=lambda pos: math.hypot(c.x - pos[0], c.y - pos[1]))


# =========================================================================
# Домен: исследование мира (в т.ч. обход моря)
# =========================================================================

class _ExplorationMixin:

    def avoid_sea(self, point, biome_grid, attempts=3):
        return self._avoid_sea(point, biome_grid, attempts=attempts)

    def explore(self, biome_grid=None):
        c = self.c
        if c.temperament == TEMPERAMENT_LAZY:
            point = self._explore_lazy()
        elif c.temperament == TEMPERAMENT_EXPLORER:
            point = self._explore_wide()
        else:
            point = self._explore_normal()
        return self._avoid_sea(point, biome_grid)

    def _explore_normal(self):
        c = self.c
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(*EXPLORE_DISTANCE[TEMPERAMENT_NORMAL])
        return geometry.clamped_point(c.x, c.y, angle, dist)

    def _explore_wide(self):
        c = self.c
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(*EXPLORE_DISTANCE[TEMPERAMENT_EXPLORER])
        return geometry.clamped_point(c.x, c.y, angle, dist)

    def _explore_lazy(self):
        c = self.c
        cx, cy = c.comfort_point
        dist_from_comfort = math.hypot(c.x - cx, c.y - cy)
        if dist_from_comfort > LAZY_COMFORT_RADIUS * 1.5:
            angle = math.atan2(cy - c.y, cx - c.x) + random.uniform(-0.4, 0.4)
            dist = min(dist_from_comfort, random.uniform(*EXPLORE_DISTANCE[TEMPERAMENT_LAZY]) + 60)
            return geometry.clamped_point(c.x, c.y, angle, dist)
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(*EXPLORE_DISTANCE[TEMPERAMENT_LAZY])
        return geometry.clamped_point(cx, cy, angle, dist)

    def _avoid_sea(self, point, biome_grid, attempts=3):
        if biome_grid is None or point is None:
            return point
        c = self.c
        for _ in range(attempts):
            if biome_grid.get_at(point[0], point[1]) != BIOME_SEA:
                return point
            angle = random.uniform(0, 2 * math.pi)
            dist_range = EXPLORE_DISTANCE.get(c.temperament, EXPLORE_DISTANCE[TEMPERAMENT_NORMAL])
            dist = random.uniform(*dist_range)
            point = geometry.clamped_point(c.x, c.y, angle, dist)
        return point


# =========================================================================
# Итоговый класс: чистая композиция доменов инстинктов
# =========================================================================

class UniversalInstincts(
    _CorpseHandlingInstinctMixin,
    _SleepInstinctMixin,
    _LandmarkLookupMixin,
    _NavigationInstinctMixin,
    _ResourceMemoryMixin,
    _ExplorationMixin,
):
    def __init__(self, creature):
        self.c = creature