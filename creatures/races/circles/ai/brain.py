from __future__ import annotations

import math
import random
from collections import namedtuple
from typing import TYPE_CHECKING

from settings import WALL_VISION_BLOCK_MARGIN
from ..ci_settings import *
from ..ci_info import *
from ....all_needed import geometry, filter_same_race
from .circles_instincts import UniversalInstincts
from .adult_ai import AdultAI
from .child_ai import ChildAI
from .older_ai import OlderAI
from .circles_adult_patterns import DecisionContext

if TYPE_CHECKING:
    from ..creature import Creature
    from game.world_context import WorldFrameContext

_Perception = namedtuple("_Perception", [
    "reaction_distance",
    "nearby_blocking_polylines",
    "visible_fruits", "visible_spikes", "visible_water", "visible_bushes", "visible_campfires",
    "visible_trees", "visible_stones",
    "visible_corpses", "visible_companions",
    "visible_roads", "visible_child_roads", "visible_graveyards",
])

class _BrainMixinBase:
    c: "Creature"
    instincts: "UniversalInstincts"

class _LifeStageDispatchBase(_BrainMixinBase):
    child: "ChildAI"
    adult: "AdultAI"
    older: "OlderAI"

# =========================================================================
# Домен: тик всех таймеров/кулдаунов существа (без принятия решений)
# =========================================================================

class _TimerTickMixin(_BrainMixinBase):

    def _tick_timers(self, dt):
        c = self.c
        c.decision_timer -= dt
        c.stuck_check_timer -= dt
        c.road_follow_check_timer -= dt
        c.territory.tick_cooldowns(dt)
        c.speed_factor = 1.0
        c.panic_active = False
        c.following_road_active = False

        if c.calm_timer > 0:
            c.calm_timer -= dt
        if c.fear_timer > 0:
            c.fear_timer -= dt
        if c.spike_invuln_timer > 0:
            c.spike_invuln_timer -= dt
        if c.player_fear_timer > 0:
            c.player_fear_timer -= dt
        if c.social_request_timer > 0:
            c.social_request_timer -= dt
        if c.urgent_child_timer > 0:
            c.urgent_child_timer -= dt
        if c.reunite_commit_timer > 0:
            c.reunite_commit_timer -= dt
        if c.partner_reunite_cooldown > 0:
            c.partner_reunite_cooldown -= dt
        if c.graveyard_alert_timer > 0:
            c.graveyard_alert_timer -= dt
        if getattr(c, 'state', None) == STATE_PANIC:
            c.panic_duration = getattr(c, 'panic_duration', 0.0) + dt
        else:
            c.panic_duration = 0.0


# =========================================================================
# Домен: восприятие мира - что существо реально видит прямо сейчас
# =========================================================================

class _PerceptionMixin(_BrainMixinBase):

    @staticmethod
    def _bounding_circle_visible(obj, cx, cy, radius):
        bx, by, br = obj.get_bounding_circle()
        return math.hypot(cx - bx, cy - by) < radius + br

    def _gather_perception(self, ctx: "WorldFrameContext"):
        c = self.c
        fruits, spikes, water_puddles = ctx.fruits, ctx.spikes, ctx.water_puddles
        bushes, campfires, other_creatures = ctx.bushes, ctx.campfires, ctx.creatures
        roads = ctx.roads
        child_roads = ctx.race_collections.get("child_roads", [])
        graveyards = ctx.race_collections.get("graveyards", [])
        walls, fences, spatial_grids = ctx.walls, ctx.fences, ctx.spatial_grids
        trees, stones, dt = ctx.trees, ctx.stones, ctx.dt

        reaction_distance = (LAZY_RISK_REACTION_DISTANCE if c.temperament == TEMPERAMENT_LAZY
                             else DEFAULT_RISK_REACTION_DISTANCE)
        vision_radius = c.aging.effective_vision_radius()

        nearby_wall_polylines = [
            w.points for w, bx, by, br in ctx.wall_bounds
            if math.hypot(c.x - bx, c.y - by) < vision_radius + WALL_VISION_BLOCK_MARGIN + br
        ]

        nearby_blocking_polylines = list(nearby_wall_polylines)
        if not c.can_jump_fences():
            nearby_blocking_polylines += [
                f.points for f, bx, by, br in ctx.fence_bounds
                if math.hypot(c.x - bx, c.y - by) < vision_radius + WALL_VISION_BLOCK_MARGIN + br
            ]

        def _visible(obj):
            if c.distance_to(obj) >= vision_radius:
                return False
            if nearby_wall_polylines and geometry.segment_blocked_by_polylines(
                    c.x, c.y, obj.x, obj.y, nearby_wall_polylines):
                return False
            return True

        if spatial_grids is not None:
            candidate_fruits = spatial_grids["fruits"].query_nearby(c.x, c.y, vision_radius)
            candidate_spikes = spatial_grids["spikes"].query_nearby(c.x, c.y, vision_radius)
            candidate_water = spatial_grids["water"].query_nearby(c.x, c.y, vision_radius)
            candidate_bushes = spatial_grids["bushes"].query_nearby(c.x, c.y, vision_radius)
            candidate_campfires = spatial_grids["campfires"].query_nearby(c.x, c.y, vision_radius)
            candidate_corpses = spatial_grids["corpses"].query_nearby(c.x, c.y, vision_radius)
            candidate_companions = spatial_grids["creatures"].query_nearby(c.x, c.y, vision_radius)
        else:
            candidate_fruits, candidate_spikes = fruits, spikes
            candidate_water, candidate_bushes = water_puddles, bushes
            candidate_campfires = campfires
            candidate_corpses = other_creatures
            candidate_companions = other_creatures

        visible_fruits = [f for f in candidate_fruits if f.active and _visible(f)]
        visible_spikes = [s for s in candidate_spikes if _visible(s)]
        visible_water = [w for w in candidate_water if w.has_water() and _visible(w)]
        visible_bushes = [b for b in candidate_bushes if _visible(b)]
        visible_campfires = [cf for cf in candidate_campfires if _visible(cf)]
        if spatial_grids is not None:
            candidate_trees = spatial_grids["trees"].query_nearby(c.x, c.y, vision_radius)
            candidate_stones = spatial_grids["stones"].query_nearby(c.x, c.y, vision_radius)
        else:
            candidate_trees = trees or []
            candidate_stones = stones or []

        visible_trees = [t for t in candidate_trees if t.has_wood() and _visible(t)]
        visible_stones = [s for s in candidate_stones if s.has_stone() and _visible(s)]
        visible_corpses = [o for o in candidate_corpses
                           if o is not c and o.is_dead and _visible(o)]
        visible_companions = [o for o in candidate_companions
                              if o is not c and not o.is_dead and _visible(o)]

        visible_roads = [r for r in roads if r.points
                         and self._bounding_circle_visible(r, c.x, c.y, vision_radius)
                         and any(math.hypot(c.x - px, c.y - py) < vision_radius for px, py in r.points)]

        visible_child_roads = [r for r in (child_roads or []) if r.points
                               and self._bounding_circle_visible(r, c.x, c.y, vision_radius)
                               and any(math.hypot(c.x - px, c.y - py) < vision_radius for px, py in r.points)]

        visible_graveyards = [g for g in graveyards if g.distance_to_point(c.x, c.y) < vision_radius]
        visible_companions = filter_same_race(c, visible_companions)
        visible_corpses = filter_same_race(c, visible_corpses)

        self.instincts.register_landmarks(
            visible_water, visible_bushes, visible_campfires, dt, visible_graveyards,
            campfire_occupancy=getattr(ctx, "campfire_occupancy", None))

        return _Perception(
            reaction_distance=reaction_distance,
            nearby_blocking_polylines=nearby_blocking_polylines,
            visible_fruits=visible_fruits, visible_spikes=visible_spikes, visible_water=visible_water,
            visible_bushes=visible_bushes, visible_campfires=visible_campfires,
            visible_trees=visible_trees, visible_stones=visible_stones,
            visible_corpses=visible_corpses, visible_companions=visible_companions,
            visible_roads=visible_roads, visible_child_roads=visible_child_roads,
            visible_graveyards=visible_graveyards,
        )


# =========================================================================
# Домен: рефлексы, которые перекрывают любое взвешенное решение (сон/паника)
# =========================================================================

class _ReflexMixin(_BrainMixinBase):

    def _resolve_sleep_state(self, nearby_corpse_threats):
        c = self.c
        if not c.is_sleeping:
            return False

        if nearby_corpse_threats or c.fear_timer > 0:
            c.is_sleeping = False
            c.sleep_forced = False
            c.sleep_spot = None
            return False

        if c.energy >= c.wake_threshold:
            c.is_sleeping = False
            c.seeking_sleep = False
            c.sleep_spot = None
            return False

        c.state = STATE_SLEEP
        c.goal_text = INFO_CREATURE_GOAL_SLEEP_FORCED if c.sleep_forced else INFO_CREATURE_GOAL_SLEEP_FIRE
        c.target = (c.x, c.y)
        return True

    def _flee_from_corpse(self, nearby_corpse_threats, visible_companions):
        c = self.c
        nearest_corpse = min(nearby_corpse_threats, key=c.distance_to)
        self.instincts.notify_elders_of_corpse(nearest_corpse, visible_companions)
        self._interrupt_child_road_play()          # НОВОЕ
        return self.instincts.flee_to_campfire((nearest_corpse.x, nearest_corpse.y))

    def _flee_from_fear(self):
        c = self.c
        c.state = STATE_PANIC
        c.panic_active = True
        c.goal_text = INFO_CREATURE_GOAL_PANIC_FLEE
        self._interrupt_child_road_play()
        goal = c.flee_point(c.fear_source, 130)
        c.target = goal
        return goal

    def _interrupt_child_road_play(self):
        c = self.c
        if c.following_child_road is None:
            return
        c.following_child_road = None
        c.child_road_progress = 0
        c.child_road_entry_reached = False
        c.following_road_active = False
        c.child_road_play_cooldown = max(c.child_road_play_cooldown, 1.0)


# =========================================================================
# Домен: маршрутизация по стадии жизни + запасной вариант (заморозка/исследование)
# =========================================================================

class _DispatchMixin(_LifeStageDispatchBase):

    def _fallback_goal(self, dt, biome_grid):
        c = self.c
        c.state = STATE_CALM
        if c.freeze_timer > 0:
            c.freeze_timer -= dt
            c.goal_text = INFO_CREATURE_GOAL_FROZEN
            return None

        reached = (c.target is None or
                   math.hypot(c.x - c.target[0], c.y - c.target[1]) < 12)
        if reached or c.decision_timer <= 0:
            if random.random() < FREEZE_CHANCE.get(c.temperament, 0.2) * c.psyche.freeze_modifier():
                c.freeze_timer = random.uniform(*FREEZE_DURATION[c.temperament])
                c.target = None
                c.goal_text = INFO_CREATURE_GOAL_FROZEN
                return None
            c.goal_text = (INFO_CREATURE_GOAL_LAZY_REST if c.temperament == TEMPERAMENT_LAZY
                           else INFO_CREATURE_GOAL_EXPLORE)
            c.target = self.instincts.explore(biome_grid=biome_grid)
            c.decision_timer = random.uniform(*EXPLORE_TIMER[c.temperament])
            return c.target

        c.goal_text = (INFO_CREATURE_GOAL_LAZY_REST if c.temperament == TEMPERAMENT_LAZY
                       else INFO_CREATURE_GOAL_EXPLORE)
        return c.target

    def _dispatch_life_stage(self, perception, ctx: "WorldFrameContext"):
        c = self.c
        other_creatures = filter_same_race(c, ctx.creatures)
        roads = ctx.roads
        storage_fields = ctx.race_collections.get("storage_fields", [])
        graveyards = ctx.race_collections.get("graveyards", [])
        child_roads = ctx.race_collections.get("child_roads", [])
        construction_sites = ctx.race_collections.get("construction_sites", [])

        dt = ctx.dt
        creatures_by_id, road_crossings = ctx.creatures_by_id, ctx.road_crossings
        biome_grid = ctx.biome_grid
        campfires = ctx.campfires

        if c.life_stage == LIFE_STAGE_CHILD:
            goal = self.child.decide(perception.visible_companions, perception.visible_roads, storage_fields,
                                     other_creatures, dt, visible_child_roads=perception.visible_child_roads,
                                     biome_grid=biome_grid)
        else:
            threat_corpses = [] if c.can_handle_corpses() else perception.visible_corpses
            all_threats = perception.visible_spikes + threat_corpses

            dctx = DecisionContext(
                visible_fruits=perception.visible_fruits,
                visible_spikes=perception.visible_spikes,
                visible_water=perception.visible_water,
                visible_bushes=perception.visible_bushes,
                visible_campfires=perception.visible_campfires,
                visible_companions=perception.visible_companions,
                other_creatures=other_creatures,
                visible_roads=perception.visible_roads,
                all_roads=roads,
                storage_fields=storage_fields,
                visible_corpses=perception.visible_corpses,
                graveyards=graveyards,
                dt=dt,
                other_by_id=creatures_by_id,
                road_crossings=road_crossings,
                visible_child_roads=perception.visible_child_roads,
                all_child_roads=child_roads,
                biome_grid=biome_grid,
                visible_trees=perception.visible_trees,
                visible_stones=perception.visible_stones,
                all_trees=ctx.trees,
                all_stones=ctx.stones,
                campfires=campfires,
                construction_sites=construction_sites,
                all_threats=all_threats,
            )

            if c.life_stage == LIFE_STAGE_OLD:
                goal = self.older.decide(dctx)
            else:
                goal = self.adult.decide(dctx)

        if goal is None:
            return self._fallback_goal(dt, biome_grid)

        c.target = goal
        return goal

# =========================================================================
# Итоговый класс: композиция доменов + единственная точка входа decide()
# =========================================================================

class CreatureBrain(_TimerTickMixin, _PerceptionMixin, _ReflexMixin, _DispatchMixin):

    def __init__(self, creature):
        self.c = creature
        self.instincts = UniversalInstincts(creature)
        self.adult = AdultAI(creature, self.instincts)
        self.child = ChildAI(creature, self.instincts)
        self.older = OlderAI(creature, self.instincts)

    def decide(self, ctx: "WorldFrameContext"):
        c = self.c

        self._tick_timers(ctx.dt)

        perception = self._gather_perception(ctx)

        if c.life_stage == LIFE_STAGE_CHILD:
            self.child.maybe_signal_parent(perception.visible_companions)

        can_handle_corpses = c.can_handle_corpses()
        threat_corpses = [] if can_handle_corpses else perception.visible_corpses

        if c.calm_timer > 0 or c.following_road:
            nearby_corpse_threats = []
        else:
            nearby_corpse_threats = [t for t in threat_corpses if c.distance_to(t) < perception.reaction_distance]

        if self._resolve_sleep_state(nearby_corpse_threats):
            return None

        if c.fear_timer > 0 and c.fear_source is not None:
            goal = self._flee_from_fear()
        elif nearby_corpse_threats:
            goal = self._flee_from_corpse(nearby_corpse_threats, perception.visible_companions)
        else:
            goal = self._dispatch_life_stage(perception, ctx)

        self.instincts.check_if_stuck(goal, biome_grid=ctx.biome_grid)
        goal = c.target

        nav_grid = ctx.nav_grid_no_fences if c.can_jump_fences() else ctx.nav_grid_with_fences
        fallback_nav_grid = (ctx.nav_grid_no_fences_fallback if c.can_jump_fences()
                             else ctx.nav_grid_with_fences_fallback)

        return c.pathfinder.resolve_path(goal, ctx.dt, nav_grid=nav_grid,
                                         wall_polylines=perception.nearby_blocking_polylines,
                                         biome_grid=ctx.biome_grid,
                                         fallback_nav_grid=fallback_nav_grid)