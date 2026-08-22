import math
import random

from settings import *
from ...ci_settings import *
from ...ci_info import *
from .....all_needed.ai.utility import Consideration, GoalComponent, lookup_creature

# =========================================================================
# Общие операции с переноской ресурсов - раньше разбросаны между
# _FeedingMixin и _StorageMixin (кража чужих методов через self)
# =========================================================================

class ResourceActions:

    def __init__(self, creature):
        self.c = creature

    def find_needy_friend(self, other_creatures):
        c = self.c
        if random.random() > GIFT_CHECK_CHANCE * c.psyche.helpfulness_modifier():
            return None
        candidates = [
            o for o in other_creatures
            if o.life_stage != LIFE_STAGE_CHILD and not o.is_dead and o is not c
               and c.social.get_relationship(o) >= GIFT_MIN_RELATIONSHIP
               and (o.hunger < CHILD_FEED_HUNGER_THRESHOLD or o.thirst < CHILD_FEED_THIRST_THRESHOLD)
        ]
        if not candidates:
            return None
        return c.social.best_companion(candidates)

    def go_fetch_fruit(self, visible_fruits, recipient=None):
        c = self.c
        if not c.eats_food_type("fruit"):
            return None
        target_fruit = min(visible_fruits, key=c.distance_to) if visible_fruits else None
        fetch_text, carry_text = self._feed_food_texts(recipient)

        if target_fruit is not None:
            if c.distance_to(target_fruit) < EAT_DISTANCE:
                target_fruit.active = False
                c.carried_fruit = True
                c.goal_text = carry_text
                c.target = (c.x, c.y)
                return c.target
            c.state = STATE_SEEKING
            c.goal_text = fetch_text
            c.target = (target_fruit.x, target_fruit.y)
            return c.target

        memory_positions = c.memory.get_food_memories()
        if memory_positions:
            pos = min(memory_positions, key=lambda p: math.hypot(c.x - p[0], c.y - p[1]))
            c.state = STATE_SEEKING
            c.goal_text = fetch_text
            c.target = pos
            return pos
        return None

    @staticmethod
    def _feed_food_texts(recipient):
        if recipient is not None and recipient.life_stage != LIFE_STAGE_CHILD:
            return INFO_CREATURE_GOAL_FEED_FETCH_FOOD_ADULT, INFO_CREATURE_GOAL_FEED_CARRY_FOOD_ADULT
        return INFO_CREATURE_GOAL_FEED_FETCH_FOOD, INFO_CREATURE_GOAL_FEED_CARRY_FOOD

    @staticmethod
    def _feed_water_texts(recipient):
        if recipient is not None and recipient.life_stage != LIFE_STAGE_CHILD:
            return INFO_CREATURE_GOAL_FEED_FETCH_WATER_ADULT, INFO_CREATURE_GOAL_FEED_CARRY_WATER_ADULT
        return INFO_CREATURE_GOAL_FEED_FETCH_WATER, INFO_CREATURE_GOAL_FEED_CARRY_WATER

    def go_fetch_water(self, visible_water, biome_grid=None, recipient=None):
        c = self.c
        available_water = [w for w in visible_water if w.has_water()]
        target_water = min(available_water, key=c.distance_to) if available_water else None
        fetch_text, carry_text = self._feed_water_texts(recipient)

        if target_water is not None:
            if c.distance_to(target_water) < EAT_DISTANCE + target_water.radius:
                if target_water.take_charge():
                    c.carried_water = True
                    c.goal_text = carry_text
                    c.target = (c.x, c.y)
                    return c.target
                # заряд иссяк прямо в момент подхода - падаем в общий поиск ниже
            else:
                c.state = STATE_SEEKING
                c.goal_text = fetch_text
                c.target = (target_water.x, target_water.y)
                return c.target

        memory_positions = c.memory.get_water_memories()
        if memory_positions:
            pos = min(memory_positions, key=lambda p: math.hypot(c.x - p[0], c.y - p[1]))
            c.state = STATE_SEEKING
            c.goal_text = fetch_text
            c.target = pos
            return pos

        if biome_grid is not None:
            if biome_grid.get_at(c.x, c.y) == BIOME_RIVER:
                c.carried_water = True
                c.goal_text = carry_text
                c.target = (c.x, c.y)
                return c.target
            vision_radius = c.aging.effective_vision_radius()
            river_point = biome_grid.find_nearest_of_type(c.x, c.y, BIOME_RIVER, vision_radius)
            if river_point:
                c.state = STATE_SEEKING
                c.goal_text = fetch_text
                c.target = river_point
                return river_point

        return None

    def deliver_resource_to(self, target):
        c = self.c
        still_needs_food = c.carried_fruit and target.hunger < HUNGER_SATISFY_THRESHOLD
        still_needs_water = c.carried_water and target.thirst < THIRST_SATISFY_THRESHOLD

        if not still_needs_food and not still_needs_water:
            c.feed_target_id = None
            return None

        is_adult_recipient = target.life_stage != LIFE_STAGE_CHILD
        deliver_text = INFO_CREATURE_GOAL_FEED_DELIVER_ADULT if is_adult_recipient else INFO_CREATURE_GOAL_FEED_DELIVER
        done_text = INFO_CREATURE_GOAL_FEED_DONE_ADULT if is_adult_recipient else INFO_CREATURE_GOAL_FEED_DONE

        c.state = STATE_SEEKING
        if c.distance_to(target) > FEED_DISTANCE:
            c.goal_text = deliver_text
            c.target = (target.x, target.y)
            return c.target

        if still_needs_food:
            target.hunger = min(target.hunger + FRUIT_HUNGER_BONUS, HUNGER_MAX)
            target.hp = min(target.hp + FRUIT_HP_BONUS, HP_MAX)
            c.carried_fruit = False
        if still_needs_water:
            target.thirst = min(target.thirst + PARENT_CARRY_WATER_HYDRATION, THIRST_MAX)
            c.carried_water = False

        bonus = (FAMILY_FEED_RELATIONSHIP_BONUS if target.life_stage == LIFE_STAGE_CHILD
                 else FAMILY_FEED_RELATIONSHIP_BONUS_ADULT)
        c.social.adjust_mutual_relationship(target, bonus)
        c.psyche.on_help_given()
        target.psyche.on_help_received()
        c.feed_target_id = None
        c.goal_text = done_text
        c.target = (c.x, c.y)
        return c.target


# =========================================================================
# Донашивание еды/воды детям и друзьям
# =========================================================================

class Feeding(GoalComponent):
    SCORE_URGENT_CHILD = 95.0
    SCORE_COMMITTED = 70.0
    SCORE_NEW = 45.0

    def __init__(self, creature, actions):
        self.c = creature
        self.actions = actions

    def consider(self, ctx):
        c = self.c
        urgent_child_active = c.urgent_child_id is not None and c.urgent_child_timer > 0
        already_committed = c.feed_target_id is not None or c.carried_fruit or c.carried_water
        if not (urgent_child_active or already_committed
                or c.needs.wellbeing_score() >= PARENT_FEED_MIN_WELLBEING):
            return [None]

        if urgent_child_active:
            score = self.SCORE_URGENT_CHILD
        elif already_committed:
            score = self.SCORE_COMMITTED
        else:
            score = self.SCORE_NEW

        def execute():
            return self._pursue(ctx)

        return [Consideration("feeding", score, execute)]

    def _pursue(self, ctx):
        c = self.c
        other_creatures, other_by_id, dt = ctx.other_creatures, ctx.other_by_id, ctx.dt

        urgent_child = None
        if c.urgent_child_id is not None and c.urgent_child_timer > 0:
            candidate = lookup_creature(other_creatures, c.urgent_child_id, other_by_id)
            if (candidate is not None and not candidate.is_dead
                    and candidate.life_stage == LIFE_STAGE_CHILD
                    and candidate.parent_ids and c.id in candidate.parent_ids):
                urgent_child = candidate

        already_committed = c.feed_target_id is not None or c.carried_fruit or c.carried_water
        if urgent_child is None and not already_committed and c.needs.wellbeing_score() < PARENT_FEED_MIN_WELLBEING:
            return None

        if urgent_child is not None and c.feed_target_id != urgent_child.id:
            c.feed_target_id = urgent_child.id

        if c.carried_fruit or c.carried_water:
            if c.storage_supply_mode and urgent_child is None:
                return None

            recipient = urgent_child
            if recipient is None and c.feed_target_id is not None:
                recipient = lookup_creature(other_creatures, c.feed_target_id, other_by_id, alive_only=True)
            if recipient is None:
                recipient = self.actions.find_needy_friend(other_creatures)
            if recipient:
                c.storage_supply_mode = False
                c.feed_target_id = recipient.id
                return self.actions.deliver_resource_to(recipient)
            c.carried_fruit = False
            c.carried_water = False
            c.feed_target_id = None
            return None

        if c.feed_target_id is not None:
            recipient = lookup_creature(other_creatures, c.feed_target_id, other_by_id, alive_only=True)
            if recipient is not None and (recipient.hunger < CHILD_FEED_HUNGER_THRESHOLD
                                          or recipient.thirst < CHILD_FEED_THIRST_THRESHOLD):
                if recipient.hunger < CHILD_FEED_HUNGER_THRESHOLD:
                    goal = self.actions.go_fetch_fruit(ctx.visible_fruits, recipient=recipient)
                    if goal:
                        return goal
                if recipient.thirst < CHILD_FEED_THIRST_THRESHOLD:
                    goal = self.actions.go_fetch_water(ctx.visible_water, biome_grid=ctx.biome_grid,
                                                       recipient=recipient)
                    if goal:
                        return goal
            c.feed_target_id = None

        if urgent_child is not None:
            needy = urgent_child
        else:
            if c.reuniting_with_partner:
                return None
            if c.parent_feed_check_timer > 0:
                c.parent_feed_check_timer -= dt
                return None
            c.parent_feed_check_timer = random.uniform(*PARENT_FEED_CHECK_INTERVAL)
            needy = self.actions.find_needy_friend(other_creatures)
            if needy is None:
                return None

        c.feed_target_id = needy.id
        if needy.hunger < CHILD_FEED_HUNGER_THRESHOLD:
            goal = self.actions.go_fetch_fruit(ctx.visible_fruits, recipient=needy)
            if goal:
                return goal
        if needy.thirst < CHILD_FEED_THIRST_THRESHOLD:
            goal = self.actions.go_fetch_water(ctx.visible_water, biome_grid=ctx.biome_grid, recipient=needy)
            if goal:
                return goal

        c.feed_target_id = None
        return None