import math
import random

from .....all_needed.ai.utility import Consideration, GoalComponent, lookup_creature
from ... import ci_info, ci_settings

# =========================================================================
# Семейный склад запасов
# =========================================================================

class Storage(GoalComponent):
    SCORE = 25.0

    def __init__(self, creature, instincts, actions):
        self.c = creature
        self.instincts = instincts
        self.actions = actions

    def consider(self, ctx):
        campfire_pos = self.instincts.nearest_known_campfire()
        if campfire_pos is None:
            return [None]

        def execute():
            return self._pursue(ctx)

        return [Consideration("storage", self.SCORE, execute)]

    def _pursue(self, ctx):
        c = self.c
        field = self.instincts.find_storage_field(ctx.storage_fields, houses=ctx.houses)
        if field is None:
            if c.storage_supply_mode and (c.feeding.carried_fruit or c.feeding.carried_water):
                c.storage_supply_mode = False
            return None
        return self._pursue_supply(field, ctx)

    def _pursue_supply(self, field, ctx):
        c = self.c
        if c.feeding.carried_fruit or c.feeding.carried_water:
            return self._deposit(field, ctx)

        if not field.has_space_for_fruit() and not field.has_space_for_water():
            return None
        if c.needs.wellbeing_score() < ci_settings.PARENT_FEED_MIN_WELLBEING:
            return None
        if c.reuniting_with_partner:
            return None

        if c.storage_supply_check_timer > 0:
            c.storage_supply_check_timer -= ctx.dt
            return None
        c.storage_supply_check_timer = random.uniform(*ci_settings.STORAGE_SUPPLY_CHECK_INTERVAL)

        fetch_fruit = (self.actions.go_fetch_fruit, ctx.visible_fruits, field.has_space_for_fruit)
        fetch_water = (
            lambda visible_objs: self.actions.go_fetch_water(visible_objs, biome_grid=ctx.biome_grid),
            ctx.visible_water, field.has_space_for_water)
        order = (fetch_fruit, fetch_water) if field.fruits <= field.water else (fetch_water, fetch_fruit)

        for fetch_fn, visible_objs, has_space_fn in order:
            if has_space_fn():
                goal = fetch_fn(visible_objs)
                if goal:
                    c.storage_supply_mode = True
                    return goal
        return None

    def _deposit(self, field, ctx):
        c = self.c
        other_creatures, other_by_id = ctx.other_creatures, ctx.other_by_id

        if not ((c.feeding.carried_fruit and field.has_space_for_fruit()) or
                (c.feeding.carried_water and field.has_space_for_water())):
            urgent_child = None
            if c.feeding.urgent_child_id is not None and c.feeding.urgent_child_timer > 0:
                candidate = lookup_creature(other_creatures, c.feeding.urgent_child_id, other_by_id)
                if (candidate is not None and not candidate.is_dead
                        and candidate.life_stage == ci_settings.LIFE_STAGE_CHILD
                        and candidate.parent_ids and c.id in candidate.parent_ids):
                    urgent_child = candidate
            needy = urgent_child if urgent_child is not None else self.actions.find_needy_friend(ctx.visible_companions)
            if needy:
                c.storage_supply_mode = False
                c.feeding.feed_target_id = needy.id
                return self.actions.deliver_resource_to(needy)
            c.feeding.carried_fruit = False
            c.feeding.carried_water = False
            c.storage_supply_mode = False
            return None

        c.state = ci_settings.STATE_SEEKING
        dist = math.hypot(c.x - field.x, c.y - field.y)
        if dist > ci_settings.STORAGE_FIELD_DEPOSIT_DISTANCE:
            c.goal_text = ci_info.INFO_CREATURE_GOAL_STORAGE_DELIVER
            c.target = (field.x, field.y)
            return c.target

        if c.feeding.carried_fruit and field.has_space_for_fruit():
            field.fruits += 1
            c.feeding.carried_fruit = False
        if c.feeding.carried_water and field.has_space_for_water():
            field.water += 1
            c.feeding.carried_water = False

        c.storage_supply_mode = False
        c.goal_text = ci_info.INFO_CREATURE_GOAL_STORAGE_STOCKED
        c.target = (c.x, c.y)
        return c.target