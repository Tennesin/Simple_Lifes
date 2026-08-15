from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..creature import Creature
    from .circles_instincts import UniversalInstincts

import math
import random

from ..ci_settings import *
from ..ci_info import *
from .private_storage import field_belongs_to
from ....all_needed import geometry
from ....all_needed.ai.utility import Consideration, pick_best, scale

# ---------- Веса принятия решений для детей ----------
SCORE_CHILD_DISTRESS_BASE = 90.0
SCORE_CHILD_DISTRESS_MAX_BONUS = 10.0

SCORE_CHILD_SLEEP_BASE = 60.0
SCORE_CHILD_SLEEP_MAX_BONUS = 15.0

SCORE_CHILD_HUNGER_BASE = 45.0
SCORE_CHILD_HUNGER_MAX_BONUS = 30.0

SCORE_CHILD_FREE_TIME = 30.0
SCORE_CHILD_PLAY_CONTINUE = 55.0

SCORE_CHILD_EXPLORE = 8.0

SCORE_CHILD_ROAD_PLAY_NEW = 48.0
SCORE_CHILD_ROAD_PLAY_ACTIVE = 58.0

class _ChildAIMixinBase:
    c: "Creature"
    instincts: "UniversalInstincts"

# =========================================================================
# Общие утилиты без собственного домена: поиск видимого родителя по
# parent_ids. Используется из distress/hunger/decide, поэтому вынесен
# отдельно - как _SharedUtilsMixin в circles_adult_patterns.py
# =========================================================================

class _ChildSharedUtilsMixin:

    @staticmethod
    def _find_visible_parent(parent_ids, visible_companions):
        if not parent_ids:
            return None
        for pid in parent_ids:
            if pid is None:
                continue
            parent = next((o for o in visible_companions if o.id == pid), None)
            if parent is not None:
                return parent
        return None

# =========================================================================
# Домен: испуг/одиночество - ребёнок ищет родителя или знакомый костёр
# =========================================================================

class _ChildDistressMixin(_ChildAIMixinBase, _ChildSharedUtilsMixin):

    def _consider_distress(self, visible_companions, biome_grid=None):
        c = self.c
        if c.child_distress_timer <= CHILD_DISTRESS_THRESHOLD:
            return None
        urgency = scale(c.child_distress_timer - CHILD_DISTRESS_THRESHOLD, 0, CHILD_DISTRESS_THRESHOLD)
        score = SCORE_CHILD_DISTRESS_BASE + urgency * SCORE_CHILD_DISTRESS_MAX_BONUS

        def execute():
            return self._handle_distress(visible_companions, biome_grid=biome_grid)

        return Consideration("child_distress", score, execute)

    def _handle_distress(self, visible_companions, biome_grid=None):
        c = self.c
        c.state = STATE_PANIC
        c.panic_active = True
        c.goal_text = INFO_CREATURE_GOAL_CHILD_DISTRESS

        parent = self._find_visible_parent(c.parent_ids, visible_companions)
        if parent is not None:
            c.target = (parent.x, parent.y)
            return c.target

        campfire_pos = None
        campfire_memories = c.memory.get_campfire_memories()
        if campfire_memories:
            campfire_pos = min(campfire_memories, key=lambda pos: math.hypot(c.x - pos[0], c.y - pos[1]))
        elif c.known_campfire:
            campfire_pos = c.known_campfire

        if campfire_pos:
            c.target = campfire_pos
            return campfire_pos

        c.target = self.instincts.pursue_search_target(biome_grid=biome_grid)
        return c.target


# =========================================================================
# Домен: сон ребёнка
# =========================================================================

class _ChildSleepMixin(_ChildAIMixinBase):

    def _consider_child_sleep(self, biome_grid=None):
        c = self.c
        if not c.seeking_sleep:
            return None
        deficit = scale(ENERGY_LOW_THRESHOLD - c.energy, 0, ENERGY_LOW_THRESHOLD)
        score = SCORE_CHILD_SLEEP_BASE + deficit * SCORE_CHILD_SLEEP_MAX_BONUS

        def execute():
            return self.instincts.seek_sleep_spot(biome_grid=biome_grid)

        return Consideration("child_sleep", score, execute)


# =========================================================================
# Домен: сигнал голода/жажды - сперва склад, потом зов родителей
# =========================================================================

class _ChildHungerMixin(_ChildAIMixinBase, _ChildSharedUtilsMixin):

    def maybe_signal_parent(self, visible_companions):
        c = self.c
        if not (c.hunger < CHILD_FEED_HUNGER_THRESHOLD or c.thirst < CHILD_FEED_THIRST_THRESHOLD):
            return
        parent = self._find_visible_parent(c.parent_ids, visible_companions)
        if parent is not None:
            parent.urgent_child_id = c.id
            parent.urgent_child_timer = CHILD_URGENT_SIGNAL_HOLD_TIME

    def _consider_hunger_signal(self, visible_companions, other_creatures, storage_fields, biome_grid=None):
        c = self.c
        if not (c.hunger < CHILD_FEED_HUNGER_THRESHOLD or c.thirst < CHILD_FEED_THIRST_THRESHOLD):
            return None

        self.maybe_signal_parent(visible_companions)

        hunger_deficit = scale(CHILD_FEED_HUNGER_THRESHOLD - c.hunger, 0, CHILD_FEED_HUNGER_THRESHOLD)
        thirst_deficit = scale(CHILD_FEED_THIRST_THRESHOLD - c.thirst, 0, CHILD_FEED_THIRST_THRESHOLD)
        deficit = max(hunger_deficit, thirst_deficit)
        score = SCORE_CHILD_HUNGER_BASE + deficit * SCORE_CHILD_HUNGER_MAX_BONUS

        if c.urgent_child_timer > 0:
            score = max(score, SCORE_CHILD_FREE_TIME + 5.0)

        def execute():
            return self._handle_child_hunger_signal(visible_companions, other_creatures, storage_fields,
                                                    biome_grid=biome_grid)

        return Consideration("child_hunger_signal", score, execute)

    def _handle_child_hunger_signal(self, visible_companions, other_creatures, storage_fields, biome_grid=None):
        c = self.c
        if not (c.hunger < CHILD_FEED_HUNGER_THRESHOLD or c.thirst < CHILD_FEED_THIRST_THRESHOLD):
            return None

        field = self._find_family_storage_field(storage_fields, other_creatures)
        if field is not None:
            wants_fruit = c.hunger < CHILD_FEED_HUNGER_THRESHOLD and field.fruits > 0
            wants_water = c.thirst < CHILD_FEED_THIRST_THRESHOLD and field.water > 0
            if wants_fruit or wants_water:
                c.state = STATE_SEEKING
                c.goal_text = INFO_CREATURE_GOAL_CHILD_SEEK_STORAGE
                c.target = (field.x, field.y)
                return c.target

        if not c.family.has_living_parent(other_creatures):
            return None

        parent = self._find_visible_parent(c.parent_ids, visible_companions)
        if c.urgent_child_timer > 0 and parent is not None:
            c.state = STATE_SEEKING
            c.goal_text = INFO_CREATURE_GOAL_CHILD_HUNGER_SIGNAL
            c.target = (c.x, c.y)
            return c.target

        campfire_pos = self.instincts.nearest_known_campfire()

        c.state = STATE_SEEKING
        c.goal_text = INFO_CREATURE_GOAL_CHILD_HUNGER_SIGNAL
        if campfire_pos:
            c.target = campfire_pos
        else:
            c.target = self.instincts.pursue_search_target(biome_grid=biome_grid)
        return c.target

    def _find_family_storage_field(self, storage_fields, other_creatures):
        c = self.c
        candidates = [f for f in storage_fields if field_belongs_to(c, f, other_creatures)]
        if not candidates:
            return None
        return min(candidates, key=c.distance_to)

# =========================================================================
# Домен: спонтанное исследование окрестностей
# =========================================================================

class _ChildExploreMixin(_ChildAIMixinBase):

    def _consider_explore(self, biome_grid=None):
        c = self.c

        def execute():
            c.goal_text = INFO_CREATURE_GOAL_CHILD_EXPLORE
            reached = (c.target is None or math.hypot(c.x - c.target[0], c.y - c.target[1]) < 12)
            if reached or c.decision_timer <= 0:
                angle = random.uniform(0, 2 * math.pi)
                dist = random.uniform(*CHILD_EXPLORE_DISTANCE)
                point = geometry.clamped_point(c.x, c.y, angle, dist)
                c.target = self.instincts.avoid_sea(point, biome_grid)
                c.decision_timer = random.uniform(*EXPLORE_TIMER[TEMPERAMENT_NORMAL])
            return c.target

        return Consideration("child_explore", SCORE_CHILD_EXPLORE, execute)

# =========================================================================
# Домен: догонялки со сверстником
# =========================================================================

class _ChildTagGameMixin(_ChildAIMixinBase):

    def _consider_free_time(self, visible_companions, visible_roads, dt):
        c = self.c
        active_game = c.play_target_id is not None and c.play_role is not None

        if c.urgent_child_timer > 0:
            if active_game:
                self._end_child_tag_game()
            return None

        if active_game:
            def execute():
                return self._pursue_child_tag_game(visible_companions, dt)

            return Consideration("child_play_continue", SCORE_CHILD_PLAY_CONTINUE, execute)

        if c.play_cooldown > 0:
            c.play_cooldown -= dt
            return None

        def execute():
            c.play_cooldown = random.uniform(*CHILD_PLAY_CHECK_INTERVAL)
            started_tag = False

            if c.temperament != TEMPERAMENT_LAZY:
                other_children = [o for o in visible_companions
                                  if o.life_stage == LIFE_STAGE_CHILD and o.play_target_id is None
                                  and o.temperament != TEMPERAMENT_LAZY]
                if other_children and random.random() < CHILD_PLAY_CHANCE:
                    playmate = min(other_children, key=c.distance_to)
                    self._start_child_tag_game(playmate)
                    started_tag = True
                    return self._pursue_child_tag_game(visible_companions, dt)

            if not started_tag and visible_roads and random.random() < CHILD_ROAD_RUN_CHANCE:
                safe_roads = [r for r in visible_roads if c.known_roads.get(r.id) != "dangerous"]
                if safe_roads:
                    road = random.choice(safe_roads)
                    c.state = STATE_SEEKING
                    c.goal_text = INFO_CREATURE_GOAL_CHILD_PLAY_ROAD
                    point = random.choice(road.points)
                    c.target = point
                    return point

            return None

        return Consideration("child_free_time", SCORE_CHILD_FREE_TIME, execute)

    def _start_child_tag_game(self, playmate):
        c = self.c
        c.play_target_id = playmate.id
        c.play_role = "chaser"
        c.play_timer = 0.0

    def _pursue_child_tag_game(self, visible_companions, dt):
        c = self.c
        partner = next((o for o in visible_companions if o.id == c.play_target_id), None)
        if partner is None or partner.is_dead or partner.life_stage != LIFE_STAGE_CHILD:
            self._end_child_tag_game()
            return None

        c.play_timer += dt
        if c.play_timer >= CHILD_PLAY_MAX_DURATION:
            self._end_child_tag_game(partner)
            return None

        c.state = STATE_SEEKING
        c.goal_text = INFO_CREATURE_GOAL_CHILD_PLAY_TAG

        if c.temperament == TEMPERAMENT_NORMAL:
            c.speed_factor = SPEED_MULTIPLIER[TEMPERAMENT_EXPLORER] / SPEED_MULTIPLIER[TEMPERAMENT_NORMAL]

        if c.play_role == "chaser":
            dist = c.distance_to(partner)
            if dist < CHILD_TAG_DISTANCE:
                partner.play_target_id = c.id
                partner.play_role = "chaser"
                partner.play_timer = c.play_timer
                c.play_role = "runner"
                c.target = c.flee_point((partner.x, partner.y), CHILD_FLEE_DISTANCE)
                return c.target
            c.target = (partner.x, partner.y)
            return c.target

        c.target = c.flee_point((partner.x, partner.y), CHILD_FLEE_DISTANCE)
        return c.target

    def _end_child_tag_game(self, partner=None):
        c = self.c
        c.play_target_id = None
        c.play_role = None
        c.play_timer = 0.0
        c.play_cooldown = random.uniform(*CHILD_PLAY_CHECK_INTERVAL)
        if partner is not None:
            partner.play_target_id = None
            partner.play_role = None
            partner.play_timer = 0.0
            partner.play_cooldown = random.uniform(*CHILD_PLAY_CHECK_INTERVAL)


# =========================================================================
# Домен: игра на детской дороге (пройти туда-обратно + скука от повторов)
# =========================================================================

class _ChildRoadPlayMixin(_ChildAIMixinBase):

    def _consider_child_road_play(self, visible_child_roads, dt):
        c = self.c

        self._tick_child_road_disinterest(dt)

        if c.urgent_child_timer > 0:
            if c.following_child_road is not None:
                self._end_child_road_play()
            return None

        if c.following_child_road is not None:
            def execute():
                return self._pursue_child_road_play(dt)

            return Consideration("child_road_play", SCORE_CHILD_ROAD_PLAY_ACTIVE, execute)

        if c.child_road_play_cooldown > 0:
            c.child_road_play_cooldown -= dt
            return None

        safe_roads = [r for r in visible_child_roads
                      if r.rating == "safe" and c.child_road_disinterest.get(r.id, 0.0) <= 0.0]
        if not safe_roads:
            return None

        def execute():
            return self._start_child_road_play(safe_roads)

        return Consideration("child_road_play", SCORE_CHILD_ROAD_PLAY_NEW, execute)

    def _start_child_road_play(self, safe_roads):
        c = self.c
        road = min(safe_roads, key=lambda r: min(
            math.hypot(c.x - r.points[0][0], c.y - r.points[0][1]),
            math.hypot(c.x - r.points[-1][0], c.y - r.points[-1][1])
        ))
        c.following_child_road = road
        c.child_road_progress = min(
            range(len(road.points)),
            key=lambda i: math.hypot(c.x - road.points[i][0], c.y - road.points[i][1])
        )
        dist_to_start = math.hypot(c.x - road.points[0][0], c.y - road.points[0][1])
        dist_to_end = math.hypot(c.x - road.points[-1][0], c.y - road.points[-1][1])
        c.child_road_direction = 1 if dist_to_start <= dist_to_end else -1
        c.child_road_entry_reached = False
        c.state = STATE_SEEKING
        c.goal_text = INFO_CREATURE_GOAL_CHILD_ROAD_APPROACH
        c.target = road.points[c.child_road_progress]
        return c.target

    def _pursue_child_road_play(self, dt):
        c = self.c
        road = c.following_child_road

        if road is None or not road.points or road.rating != "safe":
            self._end_child_road_play()
            return None
        if c.child_road_progress < 0 or c.child_road_progress >= len(road.points):
            self._end_child_road_play()
            return None

        target_point = road.points[c.child_road_progress]
        if math.hypot(c.x - target_point[0], c.y - target_point[1]) < 14:
            c.child_road_entry_reached = True
            c.child_road_progress += c.child_road_direction
            if c.child_road_progress < 0 or c.child_road_progress >= len(road.points):
                self._end_child_road_play()
                return None
            target_point = road.points[c.child_road_progress]

        c.state = STATE_SEEKING
        c.target = target_point
        c.goal_text = (INFO_CREATURE_GOAL_CHILD_ROAD_PLAY if c.child_road_entry_reached
                       else INFO_CREATURE_GOAL_CHILD_ROAD_APPROACH)
        # ---------- Как только "зашёл" на дорогу - идём прямо по точкам, без пересчёта A* ----------
        c.following_road_active = c.child_road_entry_reached

        if c.child_road_entry_reached:
            c.psyche.on_child_road_play(dt)

        return target_point

    def _end_child_road_play(self):
        c = self.c
        road = c.following_child_road
        if road is not None and c.child_road_entry_reached:
            self._register_child_road_play_session(road)

        c.following_child_road = None
        c.child_road_progress = 0
        c.child_road_entry_reached = False
        c.following_road_active = False
        c.child_road_play_cooldown = random.uniform(*CHILD_ROAD_PLAY_COOLDOWN)

    def _register_child_road_play_session(self, road):
        c = self.c
        count = c.child_road_play_counts.get(road.id, 0) + 1
        if count >= CHILD_ROAD_DISINTEREST_THRESHOLD:
            c.child_road_disinterest[road.id] = CHILD_ROAD_DISINTEREST_DURATION
            c.child_road_play_counts[road.id] = 0
        else:
            c.child_road_play_counts[road.id] = count

    def _tick_child_road_disinterest(self, dt):
        c = self.c
        if not c.child_road_disinterest:
            return
        expired = []
        for road_id in list(c.child_road_disinterest.keys()):
            c.child_road_disinterest[road_id] -= dt
            if c.child_road_disinterest[road_id] <= 0:
                expired.append(road_id)
        for road_id in expired:
            del c.child_road_disinterest[road_id]
            c.child_road_play_counts.pop(road_id, None)

# =========================================================================
# Итоговый класс: композиция доменов + единственная точка входа decide()
# =========================================================================

class ChildAI(_ChildDistressMixin, _ChildSleepMixin, _ChildHungerMixin,
              _ChildExploreMixin, _ChildTagGameMixin, _ChildRoadPlayMixin):

    def __init__(self, creature, instincts):
        self.c = creature
        self.instincts = instincts

    def decide(self, visible_companions, visible_roads, storage_fields, other_creatures, dt,
               visible_child_roads=None, biome_grid=None):
        c = self.c
        c.state = STATE_CALM
        visible_child_roads = visible_child_roads or []

        near_fire = self.instincts.is_near_known_campfire()
        near_parent = False
        if not near_fire:
            near_parent = self._find_visible_parent(c.parent_ids, visible_companions) is not None

        near_caretaker = False
        if not near_fire and not near_parent:
            near_caretaker = any(
                o.life_stage == LIFE_STAGE_OLD and getattr(o, "elder_ward_id", None) == c.id
                for o in visible_companions
            )

        if near_fire or near_parent or near_caretaker:
            c.child_distress_timer = 0.0
        else:
            c.child_distress_timer += dt

        if c.energy < ENERGY_LOW_THRESHOLD:
            c.seeking_sleep = True

        considerations = [
            self._consider_distress(visible_companions, biome_grid=biome_grid),
            self._consider_child_sleep(biome_grid=biome_grid),
            self._consider_hunger_signal(visible_companions, other_creatures, storage_fields, biome_grid=biome_grid),
            self._consider_child_road_play(visible_child_roads, dt),
            self._consider_free_time(visible_companions, visible_roads, dt),
            self._consider_explore(biome_grid=biome_grid),
        ]

        goal = pick_best(considerations)
        return goal if goal is not None else (c.x, c.y)