import math
import random
from dataclasses import dataclass, field
from typing import Optional

from settings import *
from ..ci_settings import *
from ..ci_info import *
from ....all_needed import geometry
from ....all_needed.ai.utility import Consideration, scale, GoalComponent, lookup_creature
from ..circle_objects import StorageField, Graveyard, ConstructionSite, House, Campfire

@dataclass
class DecisionContext:
    """Контекст одного тика принятия решений у взрослого/старика.
    Именованные поля с default_factory - никакой позиционной хрупкости:
    добавление нового поля в середину больше не сдвигает остальные."""
    visible_fruits: list = field(default_factory=list)
    visible_spikes: list = field(default_factory=list)
    visible_water: list = field(default_factory=list)
    visible_bushes: list = field(default_factory=list)
    visible_campfires: list = field(default_factory=list)
    visible_companions: list = field(default_factory=list)
    other_creatures: list = field(default_factory=list)
    visible_roads: list = field(default_factory=list)
    all_roads: list = field(default_factory=list)
    storage_fields: list = field(default_factory=list)
    visible_corpses: list = field(default_factory=list)
    graveyards: list = field(default_factory=list)
    houses: list = field(default_factory=list)
    dt: float = 0.0
    other_by_id: Optional[dict] = None
    road_crossings: Optional[list] = None
    visible_child_roads: list = field(default_factory=list)
    all_child_roads: list = field(default_factory=list)
    biome_grid: object = None
    visible_trees: list = field(default_factory=list)
    visible_stones: list = field(default_factory=list)
    all_trees: list = field(default_factory=list)
    all_stones: list = field(default_factory=list)
    campfires: list = field(default_factory=list)
    construction_sites: list = field(default_factory=list)
    all_threats: list = field(default_factory=list)
    all_grass: list = field(default_factory=list)

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
        score = self.SCORE_SANITY_BASE + self.SCORE_SANITY_MAX_BONUS

        def execute():
            return self._seek_sanity_relief(ctx, urgent=False)

        return Consideration("sanity", score, execute)

    def _consider_water(self, ctx):
        c = self.c
        if not c.seeking_water:
            return None
        deficit = scale(THIRST_SATISFY_THRESHOLD - c.thirst, 0, THIRST_SATISFY_THRESHOLD)
        score = self.SCORE_WATER_BASE + deficit * self.SCORE_WATER_MAX_BONUS

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


# =========================================================================
# Труп сородича / кладбище
# =========================================================================

class CorpseHandling(GoalComponent):
    SCORE_COMMITTED = 60.0
    SCORE_NEW = 50.0

    def __init__(self, creature, instincts):
        self.c = creature
        self.instincts = instincts

    def consider(self, ctx):
        c = self.c
        if not c.can_handle_corpses():
            return [None]
        committed = c.burial_target_id is not None
        has_alert = c.graveyard_alert_timer > 0
        if not ctx.visible_corpses and not committed and not has_alert:
            return [None]
        score = self.SCORE_COMMITTED if committed else self.SCORE_NEW

        def execute():
            return self.instincts.pursue_corpse_burial(ctx.visible_corpses, ctx.graveyards)

        return [Consideration("corpse_burial", score, execute)]


# =========================================================================
# Эмпатия к сородичам (не путать с ElderWardCare - это про своих взрослых)
# =========================================================================

class EmpathyHelp(GoalComponent):
    SCORE_COMMITTED = 60.0
    SCORE_NEW = 45.0

    def __init__(self, creature, instincts):
        self.c = creature
        self.instincts = instincts

    def consider(self, ctx):
        c = self.c
        committed = c._helping_target_id is not None
        threshold = EMPATHY_MIN_RELATIONSHIP - c.psyche.empathy_threshold_discount()
        has_needy = committed or any(
            o.consciousness < SANITY_LOW_THRESHOLD
            and c.social.get_relationship(o) >= threshold
            for o in ctx.visible_companions
        )
        if not has_needy:
            return [None]
        score = self.SCORE_COMMITTED if committed else self.SCORE_NEW

        def execute():
            return self._try_help(ctx)

        return [Consideration("help_companion", score, execute)]

    def _try_help(self, ctx):
        c = self.c
        other_creatures, other_by_id = ctx.other_creatures, ctx.other_by_id

        if c.helping_commit_timer > 0:
            c.helping_commit_timer -= ctx.dt

        if c._helping_target_id is not None:
            current = lookup_creature(other_creatures, c._helping_target_id, other_by_id, alive_only=True)
            if current is not None:
                still_needy = (
                        current.consciousness < SANITY_SATISFY_THRESHOLD and
                        c.social.get_relationship(current) >= EMPATHY_MIN_RELATIONSHIP
                )
                if still_needy or c.helping_commit_timer > 0:
                    return self._go_help(current)
            c._helping_target_id = None

        threshold = EMPATHY_MIN_RELATIONSHIP - c.psyche.empathy_threshold_discount()
        needy = [o for o in ctx.visible_companions
                 if o.consciousness < SANITY_LOW_THRESHOLD
                 and c.social.get_relationship(o) >= threshold]
        if not needy:
            return None

        target_companion = c.social.best_companion(needy)
        c._helping_target_id = target_companion.id
        c.helping_commit_timer = HELP_COMMIT_MIN_DURATION
        c.social.adjust_mutual_relationship(target_companion,
                                            RELATIONSHIP_HELP_BONUS_HELPER,
                                            RELATIONSHIP_HELP_BONUS_HELPED)
        c.psyche.on_help_given()
        target_companion.psyche.on_help_received()

        return self._go_help(target_companion)

    def _go_help(self, target_companion):
        c = self.c
        c.state = STATE_SEEKING
        if c.distance_to(target_companion) > HELP_APPROACH_DISTANCE:
            c.goal_text = INFO_CREATURE_GOAL_HELP_APPROACH
            return (target_companion.x, target_companion.y)

        campfire_pos = self.instincts.nearest_known_campfire()
        companion_near_fire = (campfire_pos and math.hypot(
            campfire_pos[0] - target_companion.x, campfire_pos[1] - target_companion.y
        ) < CAMPFIRE_RADIUS * 0.6)

        if campfire_pos and not companion_near_fire:
            c.goal_text = INFO_CREATURE_GOAL_HELP_LEAD
            return campfire_pos
        else:
            c.goal_text = INFO_CREATURE_GOAL_HELP_TALK
            return (c.x, c.y)


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

# =========================================================================
# Реакция на просьбу компании
# =========================================================================

class SocialResponse(GoalComponent):
    SCORE = 55.0

    def __init__(self, creature):
        self.c = creature

    def consider(self, ctx):
        c = self.c
        if c.social_request_timer <= 0 or c.social_request_point is None:
            return [None]

        if random.random() > c.psyche.social_response_chance():
            c.social_request_timer = 0.0
            c.social_request_point = None
            return [None]

        def execute():
            return self._respond()

        return [Consideration("social_response", self.SCORE, execute)]

    def _respond(self):
        c = self.c
        target_pos = c.social_request_point
        if target_pos is None:
            return None
        c.state = STATE_SEEKING
        dist = math.hypot(c.x - target_pos[0], c.y - target_pos[1])
        if dist > TALK_DISTANCE:
            c.goal_text = INFO_CREATURE_GOAL_SOCIAL_RESPOND_GO
            c.target = target_pos
            return target_pos
        c.goal_text = INFO_CREATURE_GOAL_SOCIAL_RESPOND_TALK
        c.target = (c.x, c.y)
        return c.target


# =========================================================================
# Партнёрство - воссоединение с супругом на расстоянии
# (территория и пубертат отсюда убраны - это отдельные компоненты
# только у AdultAI, а не "заглушки на всякий случай")
# =========================================================================

class PartnerBond(GoalComponent):
    SCORE_COMMITTED = 65.0
    SCORE_BASE = 45.0
    SCORE_MAX_BONUS = 20.0

    def __init__(self, creature):
        self.c = creature

    def consider(self, ctx):
        c = self.c
        if c.partner_id is None:
            return [None]

        if c.reuniting_with_partner:
            score = self.SCORE_COMMITTED
        else:
            partner = lookup_creature(ctx.other_creatures, c.partner_id, ctx.other_by_id, alive_only=True)
            if partner is None:
                return [None]
            dist = c.distance_to(partner)
            if dist <= PARTNER_REUNITE_TRIGGER_DISTANCE or c.partner_reunite_cooldown > 0:
                return [None]
            over = scale(dist - PARTNER_REUNITE_TRIGGER_DISTANCE, 0, PARTNER_REUNITE_TRIGGER_DISTANCE)
            score = self.SCORE_BASE + over * self.SCORE_MAX_BONUS

        def execute():
            return self._pursue(ctx)

        return [Consideration("partner", score, execute)]

    def _pursue(self, ctx):
        c = self.c
        partner = lookup_creature(ctx.other_creatures, c.partner_id, ctx.other_by_id, alive_only=True)

        if partner is None:
            c.reuniting_with_partner = False
            c.reunite_commit_timer = 0.0
            return None

        dist = c.distance_to(partner)

        if c.reuniting_with_partner:
            if dist <= FAMILY_REUNITE_EXIT_DISTANCE and c.reunite_commit_timer <= 0:
                c.reuniting_with_partner = False
                c.partner_reunite_cooldown = random.uniform(*PARTNER_REUNITE_COOLDOWN)
        elif dist > PARTNER_REUNITE_TRIGGER_DISTANCE and c.partner_reunite_cooldown <= 0:
            c.reuniting_with_partner = True
            c.reunite_commit_timer = FAMILY_REUNITE_MIN_DURATION
            if c.following_road is not None:
                c.following_road = None
                c.following_road_active = False
                c.road_entry_reached = False

        if c.reuniting_with_partner:
            c.state = STATE_SEEKING
            c.goal_text = INFO_CREATURE_GOAL_FAMILY_REUNITE
            c.target = (partner.x, partner.y)
            return c.target

        return None


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
            if c.storage_supply_mode and (c.carried_fruit or c.carried_water):
                c.storage_supply_mode = False
            return None
        return self._pursue_supply(field, ctx)

    def _pursue_supply(self, field, ctx):
        c = self.c
        if c.carried_fruit or c.carried_water:
            return self._deposit(field, ctx)

        if not field.has_space_for_fruit() and not field.has_space_for_water():
            return None
        if c.needs.wellbeing_score() < PARENT_FEED_MIN_WELLBEING:
            return None
        if c.reuniting_with_partner:
            return None

        if c.storage_supply_check_timer > 0:
            c.storage_supply_check_timer -= ctx.dt
            return None
        c.storage_supply_check_timer = random.uniform(*STORAGE_SUPPLY_CHECK_INTERVAL)

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

        if not ((c.carried_fruit and field.has_space_for_fruit()) or
                (c.carried_water and field.has_space_for_water())):
            urgent_child = None
            if c.urgent_child_id is not None and c.urgent_child_timer > 0:
                candidate = lookup_creature(other_creatures, c.urgent_child_id, other_by_id)
                if (candidate is not None and not candidate.is_dead
                        and candidate.life_stage == LIFE_STAGE_CHILD
                        and candidate.parent_ids and c.id in candidate.parent_ids):
                    urgent_child = candidate
            needy = urgent_child if urgent_child is not None else self.actions.find_needy_friend(other_creatures)
            if needy:
                c.storage_supply_mode = False
                c.feed_target_id = needy.id
                return self.actions.deliver_resource_to(needy)
            c.carried_fruit = False
            c.carried_water = False
            c.storage_supply_mode = False
            return None

        c.state = STATE_SEEKING
        dist = math.hypot(c.x - field.x, c.y - field.y)
        if dist > STORAGE_FIELD_DEPOSIT_DISTANCE:
            c.goal_text = INFO_CREATURE_GOAL_STORAGE_DELIVER
            c.target = (field.x, field.y)
            return c.target

        if c.carried_fruit and field.has_space_for_fruit():
            field.fruits += 1
            c.carried_fruit = False
        if c.carried_water and field.has_space_for_water():
            field.water += 1
            c.carried_water = False

        c.storage_supply_mode = False
        c.goal_text = INFO_CREATURE_GOAL_STORAGE_STOCKED
        c.target = (c.x, c.y)
        return c.target


# =========================================================================
# Добыча ресурсов и строительство
# =========================================================================

class Construction(GoalComponent):
    SCORE_COMMITTED = 62.0
    SCORE_NEW = 42.0

    _BUILDING_FINAL_FOOTPRINT = {
        "campfire": 20,
        "storage": max(STORAGE_FIELD_WIDTH, STORAGE_FIELD_HEIGHT) / 2 + 8,
        "graveyard": max(GRAVEYARD_DEFAULT_SIZE) / 2 + 10,
        "house": max(HOUSE_DEFAULT_SIZE) / 2 + 10,
    }

    def __init__(self, creature, instincts):
        self.c = creature
        self.instincts = instincts

    def consider(self, ctx):
        c = self.c
        if c.gender != GENDER_MALE or c.life_stage != LIFE_STAGE_ADULT:
            return [None]
        if c.panic_active or c.fear_timer > 0 or c.is_sleeping:
            return [None]

        committed = c.construction_target_id is not None or c.gather_target_id is not None
        if not committed and c.needs.wellbeing_score() < PARENT_FEED_MIN_WELLBEING:
            return [None]

        score = self.SCORE_COMMITTED if committed else self.SCORE_NEW
        if c.puberty_active and not self._owns_any_storage(ctx.storage_fields):
            score += CONSTRUCTION_PUBERTY_DRIVE_BONUS

        def execute():
            return self._pursue(ctx)

        return [Consideration("construction", score, execute)]

    def _owns_any_storage(self, storage_fields):
        c = self.c
        return any(c.id in field.owner_ids for field in storage_fields)

    def _pursue(self, ctx):
        c = self.c

        if c.gather_target_id is not None:
            return self._continue_gathering(ctx)

        if c.construction_target_id is not None:
            site = next((s for s in ctx.construction_sites if s.id == c.construction_target_id), None)
            if site is not None:
                return self._work_on(site, ctx)
            c.construction_target_id = None
            c.construction_phase = None

        orphan_site = self._find_orphaned_site(ctx)
        if orphan_site is not None:
            c.construction_target_id = orphan_site.id
            c.construction_phase = "build" if orphan_site.is_building else "deposit"
            return self._work_on(orphan_site, ctx)

        help_goal = self._try_join_help(ctx)
        if help_goal is not None:
            return help_goal

        if c.construction_check_timer > 0:
            c.construction_check_timer -= ctx.dt
            return None
        c.construction_check_timer = random.uniform(*CONSTRUCTION_CHECK_INTERVAL)

        campfire_pos = c.known_campfire
        build_type = self._determine_need(campfire_pos, ctx)
        if build_type is None:
            return None

        site = self._find_or_create_site(build_type, campfire_pos, ctx)
        if site is None:
            return None
        c.construction_target_id = site.id
        c.construction_phase = "deposit"
        return self._work_on(site, ctx)

    # ---------- Добыча дерева/камня ----------

    def _find_gather_source(self, res_type, ctx):
        c = self.c
        pool = ctx.visible_trees if res_type == "wood" else ctx.visible_stones
        candidates = [o for o in pool if (o.has_wood() if res_type == "wood" else o.has_stone())]
        if not candidates:
            return None
        return min(candidates, key=c.distance_to)

    def _start_gathering(self, res_type, source, needed_amount=None):
        c = self.c
        c.gather_type = res_type
        c.gather_target_id = source.id
        c.gather_progress = 0.0
        c.gather_needed_amount = needed_amount

    def _cancel_gathering(self):
        c = self.c
        c.gather_target_id = None
        c.gather_type = None
        c.gather_progress = 0.0
        c.gather_needed_amount = None

    def _continue_gathering(self, ctx):
        c = self.c
        pool = ctx.all_trees if c.gather_type == "wood" else ctx.all_stones
        source = next((o for o in pool if o.id == c.gather_target_id), None)

        if source is None:
            self._cancel_gathering()
            return None

        has_resource = source.has_wood() if c.gather_type == "wood" else source.has_stone()
        if not has_resource or c.carry_free_space() <= 0:
            self._cancel_gathering()
            return None

        if (c.gather_needed_amount is not None
                and c.carried_resources[c.gather_type] >= c.gather_needed_amount):
            self._cancel_gathering()
            return None

        if c.distance_to(source) > GATHER_APPROACH_DISTANCE:
            c.state = STATE_SEEKING
            c.goal_text = (INFO_CREATURE_GOAL_GATHER_WOOD if c.gather_type == "wood"
                           else INFO_CREATURE_GOAL_GATHER_STONE)
            c.target = (source.x, source.y)
            return c.target

        c.state = STATE_SEEKING
        c.goal_text = (INFO_CREATURE_GOAL_GATHERING_WOOD if c.gather_type == "wood"
                       else INFO_CREATURE_GOAL_GATHERING_STONE)
        c.target = (c.x, c.y)

        c.gather_progress += ctx.dt
        tick = 1.0 / RESOURCE_GATHER_RATE
        while (c.gather_progress >= tick and c.carry_free_space() > 0 and has_resource
               and (c.gather_needed_amount is None
                    or c.carried_resources[c.gather_type] < c.gather_needed_amount)):
            c.gather_progress -= tick
            if c.gather_type == "wood":
                source.wood -= 1
            else:
                source.stone -= 1
            c.carried_resources[c.gather_type] += 1
            has_resource = source.has_wood() if c.gather_type == "wood" else source.has_stone()

        reached_needed = (c.gather_needed_amount is not None
                          and c.carried_resources[c.gather_type] >= c.gather_needed_amount)
        if not has_resource or c.carry_free_space() <= 0 or reached_needed:
            self._cancel_gathering()

        return c.target

    # ---------- Потребность и точка стройки ----------

    def _determine_need(self, campfire_pos, ctx):
        c = self.c
        sites = ctx.construction_sites

        owns_house = any(c.id in h.owner_ids for h in ctx.houses)
        if not owns_house:
            already_building = any(
                s.build_type == "house" and self._site_belongs_to(s, ctx)
                for s in sites
            )
            if already_building:
                return None
            return "house"

        if campfire_pos is None:
            nearby_campfire_site = any(
                s.build_type == "campfire"
                and math.hypot(c.x - s.x, c.y - s.y) < NEW_CAMPFIRE_JOIN_SEARCH_RADIUS
                for s in sites
            )
            if not nearby_campfire_site:
                return "campfire"
            return None

        house = next((h for h in ctx.houses if c.id in h.owner_ids), None)
        if house is not None and house.storage_field(ctx.storage_fields) is None:
            already_building_storage = any(
                s.build_type == "storage" and getattr(s, "storage_owner_id", None) == c.id
                for s in sites
            )
            if not already_building_storage:
                return "storage"

        if c.known_graveyard is None:
            linked = self._find_campfire_linked_graveyard(campfire_pos, ctx.graveyards)
            if linked is not None:
                c.known_graveyard = (linked.x, linked.y)
            elif not any(s.build_type == "graveyard" for s in sites):
                return "graveyard"
        return None

    def _find_campfire_linked_graveyard(self, campfire_pos, graveyards):
        if campfire_pos is None or not graveyards:
            return None
        for gy in graveyards:
            if math.hypot(gy.x - campfire_pos[0], gy.y - campfire_pos[1]) < GRAVEYARD_CAMPFIRE_LINK_RADIUS:
                return gy
        return None

    def _footprint_radius(self, build_type):
        return self._BUILDING_FINAL_FOOTPRINT.get(build_type, 30)

    def _point_clear(self, point, build_type, biome_grid, ctx, skip_house_id=None):
        px, py = point
        if biome_grid is not None and biome_grid.get_at(px, py) in (BIOME_SEA, BIOME_RIVER):
            return False

        footprint = self._footprint_radius(build_type) + CONSTRUCTION_CLEARANCE_MARGIN

        def _blocked(objects, radius_attr=None):
            for obj in objects:
                other_radius = getattr(obj, radius_attr, 0) if radius_attr else 0
                if math.hypot(px - obj.x, py - obj.y) < footprint + other_radius:
                    return True
            return False

        if _blocked(ctx.visible_fruits, "radius") or _blocked(ctx.visible_spikes, "radius"):
            return False
        if _blocked(ctx.visible_water, "radius") or _blocked(ctx.visible_bushes, "radius"):
            return False
        if _blocked(ctx.visible_trees, "radius") or _blocked(ctx.visible_stones, "radius"):
            return False
        if _blocked(ctx.campfires, "radius") or _blocked(ctx.storage_fields, "radius"):
            return False
        for gy in ctx.graveyards:
            if gy.distance_to_point(px, py) < footprint:
                return False
        for house in ctx.houses:
            if house.id == skip_house_id:
                continue
            house_radius = max(house.width, house.height) / 2
            if math.hypot(px - house.x, py - house.y) < footprint + house_radius:
                return False
        for site in ctx.construction_sites:
            site_radius = max(site.width, site.height) / 2
            if math.hypot(px - site.x, py - site.y) < footprint + site_radius:
                return False
        return True

    def _pick_point(self, build_type, campfire_pos, biome_grid, ctx, attempts=20):
        c = self.c
        if build_type == "campfire":
            return self._pick_new_campfire_point(ctx, attempts=max(attempts, 30))
        if build_type == "house":
            return self._pick_house_point(campfire_pos, biome_grid, ctx)
        if build_type == "storage":
            return self._pick_storage_point(ctx)

        anchor = campfire_pos if campfire_pos is not None else (c.x, c.y)
        dist_range = GRAVEYARD_BUILD_OFFSET_RANGE
        fallback = None
        for _ in range(attempts):
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(*dist_range)
            point = geometry.clamped_point(anchor[0], anchor[1], angle, dist)
            if self._point_clear(point, build_type, biome_grid, ctx):
                return point
            fallback = point
        return fallback

    def _pick_house_point(self, campfire_pos, biome_grid, ctx):
        c = self.c
        anchor = campfire_pos if campfire_pos is not None else (c.x, c.y)
        best_point, best_score = None, None
        for _ in range(HOUSE_SITE_SCORE_ATTEMPTS):
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(*HOUSE_BUILD_OFFSET_RANGE)
            point = geometry.clamped_point(anchor[0], anchor[1], angle, dist)
            if not self._point_clear(point, "house", biome_grid, ctx):
                continue
            score = self._score_house_site(point, campfire_pos, biome_grid, ctx)
            if best_score is None or score > best_score:
                best_score, best_point = score, point
        return best_point

    def _score_house_site(self, point, campfire_pos, biome_grid, ctx):
        px, py = point
        score = 0.0
        biome = biome_grid.get_at(px, py) if biome_grid is not None else BIOME_PLAINS
        if biome == BIOME_DESERT:
            score -= HOUSE_DESERT_PENALTY

        # ---------- Есть ли место сбоку под будущий склад ----------
        half_house_w = HOUSE_DEFAULT_SIZE[0] / 2
        side_w = STORAGE_FIELD_WIDTH + STORAGE_HOUSE_GAP * 2
        left_ok = self._point_clear((px - half_house_w - side_w / 2, py), "storage", biome_grid, ctx)
        right_ok = self._point_clear((px + half_house_w + side_w / 2, py), "storage", biome_grid, ctx)
        if left_ok or right_ok:
            score += HOUSE_STORAGE_ROOM_BONUS

        # ---------- Не слишком далеко и не впритык к костру ----------
        if campfire_pos is not None:
            dist = math.hypot(px - campfire_pos[0], py - campfire_pos[1])
            score -= abs(dist - HOUSE_CAMPFIRE_DISTANCE_IDEAL) * 0.05

        return score

    def _pick_storage_point(self, ctx):
        c = self.c
        house = next((h for h in ctx.houses if c.id in h.owner_ids), None)
        if house is None:
            return None
        half_house_w = house.width / 2
        half_store_w = STORAGE_FIELD_WIDTH / 2
        sides = [1, -1]
        random.shuffle(sides)
        for side_sign in sides:
            px = house.x + side_sign * (half_house_w + STORAGE_HOUSE_GAP + half_store_w)
            point = (px, house.y)
            if self._point_clear(point, "storage", ctx.biome_grid, ctx, skip_house_id=house.id):  # НОВОЕ
                return point
        return None

    def _pick_new_campfire_point(self, ctx, attempts=30):
        c = self.c
        existing_fires = list(ctx.campfires)
        pending_sites = [s for s in ctx.construction_sites if s.build_type == "campfire"]

        fallback = None
        for _ in range(attempts):
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(*NEW_CAMPFIRE_DISTANCE_RANGE)
            point = geometry.clamped_point(c.x, c.y, angle, dist)

            far_enough = (
                all(math.hypot(point[0] - f.x, point[1] - f.y) >= NEW_CAMPFIRE_DISTANCE_RANGE[0]
                    for f in existing_fires)
                and all(math.hypot(point[0] - s.x, point[1] - s.y) >= NEW_CAMPFIRE_DISTANCE_RANGE[0]
                        for s in pending_sites)
            )
            if not far_enough:
                continue

            if self._point_clear(point, "campfire", ctx.biome_grid, ctx):
                return point
            fallback = point

        return fallback

    def _find_or_create_site(self, build_type, campfire_pos, ctx):
        c = self.c
        for site in ctx.construction_sites:
            if site.build_type != build_type:
                continue
            if math.hypot(c.x - site.x, c.y - site.y) < CONSTRUCTION_SITE_SEARCH_RADIUS:
                return site

        point = self._pick_point(build_type, campfire_pos, ctx.biome_grid, ctx)
        if point is None:
            return None

        site = ConstructionSite(point[0], point[1], build_type, campfire_pos=campfire_pos)
        ctx.construction_sites.append(site)
        c.pending_site_cleanup = site
        return site

    # ---------- Доставка материалов / стройка ----------

    def _deliver(self, site):
        c = self.c
        c.state = STATE_SEEKING
        if math.hypot(c.x - site.x, c.y - site.y) > CONSTRUCTION_APPROACH_DISTANCE:
            c.goal_text = INFO_CREATURE_GOAL_CONSTRUCTION_GO
            c.target = (site.x, site.y)
            return c.target

        wood_to_deposit = min(c.carried_resources["wood"], site.needed("wood"))
        stone_to_deposit = min(c.carried_resources["stone"], site.needed("stone"))
        site.deposited_wood += wood_to_deposit
        site.deposited_stone += stone_to_deposit
        c.carried_resources["wood"] -= wood_to_deposit
        c.carried_resources["stone"] -= stone_to_deposit

        if wood_to_deposit > 0 or stone_to_deposit > 0:
            site.contributor_ids.add(c.id)

        if site.needed("wood") == 0:
            c.carried_resources["wood"] = 0
        if site.needed("stone") == 0:
            c.carried_resources["stone"] = 0

        c.goal_text = INFO_CREATURE_GOAL_CONSTRUCTION_DEPOSIT
        c.target = (c.x, c.y)

        if site.resources_complete():
            site.is_building = True
            site.builder_ids.add(c.id)
            c.construction_phase = "build"

        return c.target

    def _perform_build_phase(self, site, ctx):
        c = self.c
        site.builder_ids.add(c.id)
        site.contributor_ids.add(c.id)
        c.construction_phase = "build"
        c.state = STATE_SEEKING

        if math.hypot(c.x - site.x, c.y - site.y) > CONSTRUCTION_APPROACH_DISTANCE:
            c.goal_text = INFO_CREATURE_GOAL_CONSTRUCTION_GO
            c.target = (site.x, site.y)
            return c.target

        c.goal_text = INFO_CREATURE_GOAL_CONSTRUCTION_BUILD
        c.target = (c.x, c.y)

        alive_ids = {o.id for o in ctx.other_creatures if not o.is_dead}
        alive_ids.add(c.id)
        site.builder_ids &= alive_ids
        if not site.builder_ids:
            site.builder_ids = {c.id}

        is_leader = c.id == min(site.builder_ids)
        if is_leader:
            speed = 1.0 + max(0, len(site.builder_ids) - 1) * BUILD_HELP_SPEED_BONUS_PER_HELPER
            site.build_progress += ctx.dt * speed

        if site.build_progress >= site.build_time:
            self._finish(site, ctx)
            return (c.x, c.y)

        return c.target

    def _finish(self, site, ctx):
        c = self.c
        new_object = None
        if site.build_type == "campfire":
            new_object = Campfire(site.x, site.y)
            ctx.campfires.append(new_object)

        elif site.build_type == "storage":
            new_object = StorageField(site.x, site.y, owner_campfire_pos=site.campfire_pos)
            primary_owner_id = getattr(site, "storage_owner_id", None) or c.id
            new_object.add_owner(primary_owner_id)

            primary_owner = next((o for o in ctx.other_creatures if o.id == primary_owner_id), None)
            partner_id = primary_owner.partner_id if primary_owner is not None else None
            if partner_id is not None and partner_id in site.contributor_ids:
                new_object.add_owner(partner_id)

            new_object.built_by = c.id
            ctx.storage_fields.append(new_object)

            # ---------- Склад сразу становится неотделимой частью дома ----------
            linked_house_id = getattr(site, "linked_house_id", None)
            house = next((h for h in ctx.houses if h.id == linked_house_id), None) if linked_house_id else None
            if house is not None:
                house.attach_storage(new_object)
            else:
                new_object.house_id = None

        elif site.build_type == "graveyard":
            new_object = Graveyard(site.x, site.y)
            ctx.graveyards.append(new_object)

        elif site.build_type == "house":
            cap_range = HOUSE_CAPACITY_RANGE.get(c.temperament, (4, 6))
            new_object = House(site.x, site.y, capacity=random.randint(*cap_range))
            primary_owner_id = getattr(site, "house_owner_id", None) or c.id
            new_object.owner_ids.add(primary_owner_id)
            new_object.resident_ids.add(primary_owner_id)
            c.home_id = new_object.id

            primary_owner = next((o for o in ctx.other_creatures if o.id == primary_owner_id), None)
            partner_id = primary_owner.partner_id if primary_owner is not None else c.partner_id
            if partner_id is not None:
                new_object.owner_ids.add(partner_id)
                if new_object.add_resident(partner_id):
                    partner = next((o for o in ctx.other_creatures if o.id == partner_id), None)
                    if partner is not None:
                        partner.home_id = new_object.id

            # ---------- Ещё не расселённые дети переезжают вместе с семьёй ----------
            for child in ctx.other_creatures:
                if (not child.is_dead and child.home_id is None
                        and child.parent_ids and primary_owner_id in child.parent_ids):
                    if new_object.add_resident(child.id):
                        child.home_id = new_object.id

            # ---------- "Осиротевший" склад из старого мира привязываем к новому дому ----------
            for field in ctx.storage_fields:
                if primary_owner_id in field.owner_ids and getattr(field, "house_id", None) is None:
                    new_object.attach_storage(field)

            ctx.houses.append(new_object)

        if site in ctx.construction_sites:
            ctx.construction_sites.remove(site)

        c.goal_text = INFO_CREATURE_GOAL_CONSTRUCTION_DONE
        c.construction_target_id = None
        c.construction_phase = None
        c.pending_construction_cleanup = (site.build_type, new_object)

    def _work_on(self, site, ctx):
        c = self.c
        if site.is_building:
            return self._perform_build_phase(site, ctx)
        if site.resources_complete():
            site.is_building = True
            site.builder_ids.add(c.id)
            c.construction_phase = "build"
            return self._perform_build_phase(site, ctx)

        if c.carried_resources["wood"] > 0 or c.carried_resources["stone"] > 0:
            return self._deliver(site)

        needed_wood = site.needed("wood")
        needed_stone = site.needed("stone")
        res_type = "wood" if needed_wood > 0 else ("stone" if needed_stone > 0 else None)
        if res_type is None:
            return self._deliver(site)

        source = self._find_gather_source(res_type, ctx)
        if source is None and needed_wood > 0 and needed_stone > 0:
            alt_type = "stone" if res_type == "wood" else "wood"
            alt_source = self._find_gather_source(alt_type, ctx)
            if alt_source is not None:
                res_type, source = alt_type, alt_source

        if source is None:
            c.state = STATE_SEEKING
            c.goal_text = (INFO_CREATURE_GOAL_GATHER_WOOD if res_type == "wood"
                           else INFO_CREATURE_GOAL_GATHER_STONE)
            c.target = self.instincts.pursue_search_target()
            return c.target

        needed_amount = needed_wood if res_type == "wood" else needed_stone
        self._start_gathering(res_type, source, needed_amount=needed_amount)
        return self._continue_gathering(ctx)

    # ---------- Восстановление после перезапуска / кооперация ----------

    def _find_orphaned_site(self, ctx):
        c = self.c
        if c.gender != GENDER_MALE or c.life_stage != LIFE_STAGE_ADULT:
            return None
        if c.panic_active or c.fear_timer > 0 or c.is_sleeping:
            return None
        if not ctx.construction_sites:
            return None

        claimed_ids = {o.construction_target_id for o in ctx.other_creatures
                       if not o.is_dead and o.construction_target_id is not None}

        candidates = [s for s in ctx.construction_sites
                     if s.id not in claimed_ids
                     and math.hypot(c.x - s.x, c.y - s.y)
                         < CONSTRUCTION_SITE_SEARCH_RADIUS * ORPHAN_SITE_SEARCH_RADIUS_FACTOR]
        if not candidates:
            return None
        return min(candidates, key=lambda s: math.hypot(c.x - s.x, c.y - s.y))

    def _try_join_help(self, ctx):
        c = self.c
        if c.build_help_check_timer > 0:
            c.build_help_check_timer -= ctx.dt
            return None
        c.build_help_check_timer = random.uniform(*BUILD_HELP_CHECK_INTERVAL)

        sites_by_id = {s.id: s for s in ctx.construction_sites}

        candidates = [
            o for o in ctx.visible_companions
            if o.gender == GENDER_MALE and o.life_stage == LIFE_STAGE_ADULT
               and o.construction_target_id is not None and o.construction_phase in ("deposit", "build")
               and c.social.get_relationship(o) >= BUILD_HELP_MIN_RELATIONSHIP
               and sites_by_id.get(o.construction_target_id) is not None
               and sites_by_id[o.construction_target_id].build_type not in ("house", "storage")
        ]
        if not candidates:
            return None
        if random.random() >= BUILD_HELP_JOIN_CHANCE * c.psyche.helpfulness_modifier():
            return None

        target_worker = c.social.best_companion(candidates)
        c.construction_target_id = target_worker.construction_target_id
        c.construction_phase = "deposit"
        c.social.adjust_mutual_relationship(target_worker, BUILD_HELP_RELATIONSHIP_BONUS)

        c.state = STATE_SEEKING
        c.goal_text = INFO_CREATURE_GOAL_CONSTRUCTION_HELP
        c.target = (target_worker.x, target_worker.y)
        return c.target


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

        useful_objects = ctx.visible_fruits + ctx.visible_water + ctx.visible_bushes + ctx.visible_campfires
        helpful = any(math.hypot(ex - o.x, ey - o.y) < ROAD_OUTCOME_RADIUS for o in useful_objects)

        if not helpful:
            structures = list(ctx.graveyards) + list(ctx.houses) + list(ctx.storage_fields) + list(ctx.campfires)
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

# =========================================================================
# Любопытство к неизвестным объектам - общая часть (роль/скидка на интерес),
# специфика реакции ("подойти изучить" vs "мгновенно узнать") - в стратегии
# =========================================================================

class CuriosityStrategy:
    def pursue(self, unknown_harmless, unknown_hazards):
        raise NotImplementedError

class Curiosity(GoalComponent):
    SCORE_BASE = 10.0
    SCORE_CURIOSITY_FACTOR = 10.0

    def __init__(self, creature, strategy):
        self.c = creature
        self.strategy = strategy

    def consider(self, ctx):
        c = self.c
        score = self.SCORE_BASE + c.curiosity * self.SCORE_CURIOSITY_FACTOR

        def execute():
            return self._pursue(ctx)

        return [Consideration("curiosity", score, execute)]

    def _pursue(self, ctx):
        c = self.c
        unknown_harmless = self._collect_unknown_harmless(ctx)
        unknown_hazards = [s for s in ctx.visible_spikes if not c.knowledge["spike"]]

        visible_types_now = {t for t, _ in unknown_harmless}
        if unknown_hazards:
            visible_types_now.add("spike")
        self._roll_curiosity_interest(visible_types_now)

        return self.strategy.pursue(unknown_harmless, unknown_hazards)

    def _collect_unknown_harmless(self, ctx):
        c = self.c
        unknown_harmless = []
        if c.eats_food_type("fruit") and not c.knowledge["fruit"] and ctx.visible_fruits:
            unknown_harmless.append(("fruit", min(ctx.visible_fruits, key=c.distance_to)))
        if not c.knowledge["water"] and ctx.visible_water:
            unknown_harmless.append(("water", min(ctx.visible_water, key=c.distance_to)))
        if not c.knowledge["bush"] and ctx.visible_bushes:
            unknown_harmless.append(("bush", min(ctx.visible_bushes, key=c.distance_to)))
        if not c.knowledge["campfire"] and ctx.visible_campfires:
            unknown_harmless.append(("campfire", min(ctx.visible_campfires, key=c.distance_to)))
        return unknown_harmless

    def _roll_curiosity_interest(self, visible_types_now):
        c = self.c
        for t in list(c.curiosity_rolled):
            if t not in visible_types_now:
                c.curiosity_rolled.discard(t)
                c.curiosity_interested.discard(t)

        chance = CURIOSITY_DISCOVERY_CHANCE.get(c.temperament, 0.3) * c.psyche.curiosity_modifier()
        for t in visible_types_now:
            if t not in c.curiosity_rolled:
                c.curiosity_rolled.add(t)
                if random.random() < chance:
                    c.curiosity_interested.add(t)