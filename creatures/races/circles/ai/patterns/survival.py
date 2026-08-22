import math

from ...ci_settings import *
from ...ci_info import *
from .....all_needed.ai.utility import Consideration, scale, GoalComponent

# =========================================================================
# Базовые нужды: голод/жажда/сон/санити/выживание
# =========================================================================

class SurvivalNeeds(GoalComponent):
    SCORE_URGENT_SURVIVAL_BASE = 90.0
    SCORE_URGENT_SURVIVAL_MAX_BONUS = 10.0
    SCORE_URGENT_SANITY_BASE = 85.0
    SCORE_URGENT_SANITY_MAX_BONUS = 10.0
    SCORE_SLEEP_BASE = 55.0
    SCORE_SLEEP_MAX_BONUS = 25.0
    SCORE_FOOD_BASE = 40.0
    SCORE_FOOD_MAX_BONUS = 35.0
    SCORE_WATER_BASE = 40.0
    SCORE_WATER_MAX_BONUS = 35.0
    SCORE_SANITY_BASE = 35.0
    SCORE_SANITY_MAX_BONUS = 20.0

    def __init__(self, creature, instincts, roads):
        self.c = creature
        self.instincts = instincts
        self.roads = roads   # известные маршруты к еде/воде по дорогам

    def consider(self, ctx):
        self._tick_seeking_flags()
        return [
            self._consider_urgent_survival(ctx),
            self._consider_urgent_sanity(ctx),
            self._consider_sleep(ctx),
            self._consider_food(ctx),
            self._consider_water(ctx),
            self._consider_sanity(ctx),
        ]

    def _tick_seeking_flags(self):
        c = self.c
        if c.energy < ENERGY_LOW_THRESHOLD:
            c.seeking_sleep = True
        if c.consciousness < SANITY_LOW_THRESHOLD:
            c.seeking_sanity = True
        if c.seeking_sanity and c.consciousness >= SANITY_SATISFY_THRESHOLD:
            c.seeking_sanity = False
        if c.hunger < 10:
            c.seeking_food = True
        if c.seeking_food and c.hunger >= HUNGER_SATISFY_THRESHOLD:
            c.seeking_food = False
        if c.thirst < 10:
            c.seeking_water = True
        if c.seeking_water and c.thirst >= THIRST_SATISFY_THRESHOLD:
            c.seeking_water = False

    def _consider_urgent_survival(self, ctx):
        c = self.c
        if c.hp >= 30:
            return None
        urgency = scale(30 - c.hp, 0, 30)
        score = self.SCORE_URGENT_SURVIVAL_BASE + urgency * self.SCORE_URGENT_SURVIVAL_MAX_BONUS

        def execute():
            goal = self.instincts.nearest_food_target(ctx.visible_fruits)
            if goal:
                c.state = STATE_SEEKING
                c.goal_text = INFO_CREATURE_GOAL_URGENT_FOOD
                return goal
            danger_pos = self.instincts.nearest_danger_position(ctx.all_threats)
            if danger_pos:
                c.state = STATE_PANIC
                c.panic_active = True
                c.goal_text = INFO_CREATURE_GOAL_SEEK_SAFETY
                return c.flee_point(danger_pos, 80)
            return None

        return Consideration("urgent_survival", score, execute)

    def _consider_urgent_sanity(self, ctx):
        c = self.c
        if not (c.seeking_sanity and c.consciousness < SANITY_PANIC_THRESHOLD):
            return None
        urgency = scale(SANITY_PANIC_THRESHOLD - c.consciousness, 0, SANITY_PANIC_THRESHOLD)
        score = self.SCORE_URGENT_SANITY_BASE + urgency * self.SCORE_URGENT_SANITY_MAX_BONUS

        def execute():
            return self._seek_sanity_relief(ctx, urgent=True)

        return Consideration("urgent_sanity", score, execute)

    def _consider_sleep(self, ctx):
        c = self.c
        if not c.seeking_sleep:
            return None
        deficit = scale(ENERGY_LOW_THRESHOLD - c.energy, 0, ENERGY_LOW_THRESHOLD)
        score = self.SCORE_SLEEP_BASE + deficit * self.SCORE_SLEEP_MAX_BONUS

        def execute():
            return self.instincts.seek_sleep_spot(biome_grid=ctx.biome_grid, houses=ctx.houses)

        return Consideration("sleep", score, execute)

    def _consider_food(self, ctx):
        c = self.c
        if not c.seeking_food:
            return None
        score = self.SCORE_FOOD_BASE + self.SCORE_FOOD_MAX_BONUS

        def execute():
            self.instincts.check_stale_food_memory(ctx.visible_fruits)
            found = self.instincts.nearest_food_target(ctx.visible_fruits)
            c.state = STATE_SEEKING
            if found:
                c.goal_text = INFO_CREATURE_GOAL_SEEK_FOOD
                return found
            route = self.roads.pursue_known_link("food", ctx)
            if route:
                return route
            c.goal_text = INFO_CREATURE_GOAL_SEEK_FOOD_ACTIVE
            return self.instincts.pursue_search_target(ctx.visible_companions, biome_grid=ctx.biome_grid)

        return Consideration("food", score, execute)

    def _consider_water(self, ctx):
        c = self.c
        if not c.seeking_water:
            return None
        score = self.SCORE_WATER_BASE + self.SCORE_WATER_MAX_BONUS

        def execute():
            self.instincts.check_stale_water_memory(ctx.visible_water)
            found = self.instincts.nearest_water_target(ctx.visible_water, biome_grid=ctx.biome_grid)
            c.state = STATE_SEEKING
            if found:
                c.goal_text = INFO_CREATURE_GOAL_SEEK_WATER
                return found
            route = self.roads.pursue_known_link("water", ctx)
            if route:
                return route
            c.goal_text = INFO_CREATURE_GOAL_SEEK_WATER_ACTIVE
            return self.instincts.pursue_search_target(ctx.visible_companions, biome_grid=ctx.biome_grid)

        return Consideration("water", score, execute)

    def _consider_sanity(self, ctx):
        c = self.c
        if not c.seeking_sanity:
            return None
        deficit = scale(SANITY_LOW_THRESHOLD - c.consciousness, 0, SANITY_LOW_THRESHOLD)
        score = self.SCORE_SANITY_BASE + deficit * self.SCORE_SANITY_MAX_BONUS

        def execute():
            return self._seek_sanity_relief(ctx, urgent=False)

        return Consideration("sanity", score, execute)

    def _seek_sanity_relief(self, ctx, urgent):
        c = self.c
        other_creatures = ctx.other_creatures
        c.state = STATE_PANIC if urgent else STATE_SEEKING
        c.panic_active = urgent

        campfire_pos = self.instincts.nearest_known_campfire()

        if campfire_pos:
            dist_to_fire = math.hypot(c.x - campfire_pos[0], c.y - campfire_pos[1])
            if dist_to_fire > CAMPFIRE_RADIUS:
                c.goal_text = (INFO_CREATURE_GOAL_SANITY_URGENT_FIRE if urgent
                               else INFO_CREATURE_GOAL_SANITY_FIRE)
                c.target = campfire_pos
                return campfire_pos

            companions_in_fire_zone = [
                o for o in other_creatures
                if o is not c and not o.is_dead
                and math.hypot(o.x - campfire_pos[0], o.y - campfire_pos[1]) < CAMPFIRE_RADIUS
            ]
            if companions_in_fire_zone:
                nearest_companion = c.social.best_companion(companions_in_fire_zone)
                nearest_companion.social.request_company(campfire_pos)
                if c.distance_to(nearest_companion) > TALK_DISTANCE:
                    c.goal_text = (INFO_CREATURE_GOAL_SANITY_URGENT_COMPANION_FIRE if urgent
                                   else INFO_CREATURE_GOAL_SANITY_COMPANION_FIRE)
                    c.target = (nearest_companion.x, nearest_companion.y)
                    return c.target
                else:
                    c.goal_text = INFO_CREATURE_GOAL_SANITY_TALK
                    c.target = (c.x, c.y)
                    return c.target

            c.goal_text = INFO_CREATURE_GOAL_SANITY_ALONE
            c.target = campfire_pos
            return campfire_pos

        route = self.roads.pursue_known_link("campfire", ctx)
        if route:
            c.goal_text = (INFO_CREATURE_GOAL_SANITY_URGENT_FIRE if urgent
                           else INFO_CREATURE_GOAL_SANITY_FIRE)
            c.target = route
            return route

        companions = [o for o in other_creatures
                      if o is not c and not o.is_dead and c.distance_to(o) < VISION_RADIUS]
        nearest_companion = c.social.best_companion(companions)

        if nearest_companion:
            nearest_companion.social.request_company((c.x, c.y))
            c.goal_text = (INFO_CREATURE_GOAL_SANITY_URGENT_ANYONE if urgent
                           else INFO_CREATURE_GOAL_SANITY_COMPANIONS)
            c.target = (nearest_companion.x, nearest_companion.y)
            return c.target

        intuitive = c.memory.get_campfire_intuitive_target(*c.comfort_point)
        if intuitive:
            c.goal_text = (INFO_CREATURE_GOAL_SANITY_URGENT_NO_FIRE if urgent
                           else INFO_CREATURE_GOAL_SANITY_NO_FIRE)
            c.target = intuitive
            return intuitive

        c.goal_text = (INFO_CREATURE_GOAL_SANITY_URGENT_NO_FIRE if urgent
                       else INFO_CREATURE_GOAL_SANITY_NO_FIRE)
        return self.instincts.pursue_search_target(biome_grid=ctx.biome_grid)