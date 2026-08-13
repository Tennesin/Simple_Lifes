import math
import random

from settings import CAMPFIRE_RADIUS
from ..ci_settings import *
from ..ci_info import *
from .circles_adult_patterns import (
    GoalComponent, ResourceActions, Roads, SurvivalNeeds, CorpseHandling,
    Feeding, SocialResponse, PartnerBond, Storage, Curiosity, CuriosityStrategy,
    lookup_creature,
)
from ....all_needed.ai.utility import Consideration, pick_best

# =========================================================================
# Опека над случайными (не своими) детьми - только у OlderAI
# =========================================================================

class ElderWardCare(GoalComponent):
    SCORE_COMMITTED = 65.0
    SCORE_NEW = 40.0

    def __init__(self, creature, instincts, actions):
        self.c = creature
        self.instincts = instincts
        self.actions = actions

    def consider(self, ctx):
        c = self.c
        committed = c.elder_ward_id is not None
        has_candidate = committed or any(
            o.life_stage == LIFE_STAGE_CHILD for o in ctx.visible_companions
        )
        if not has_candidate:
            return [None]
        score = self.SCORE_COMMITTED if committed else self.SCORE_NEW

        def execute():
            return self._help_any_needy_child(ctx)

        return [Consideration("extra_care", score, execute)]

    def _child_needs_help(self, child, visible_companions, other_creatures):
        if not child.family.has_living_parent(other_creatures):
            return True
        parent_visible = False
        if child.parent_ids:
            for pid in child.parent_ids:
                if pid is not None and any(o.id == pid for o in visible_companions):
                    parent_visible = True
                    break
        if parent_visible:
            return False
        return (child.hunger < CHILD_FEED_HUNGER_THRESHOLD or
                child.thirst < CHILD_FEED_THIRST_THRESHOLD)

    def _help_any_needy_child(self, ctx):
        c = self.c
        visible_companions, other_creatures, dt, other_by_id = (
            ctx.visible_companions, ctx.other_creatures, ctx.dt, ctx.other_by_id)

        if c.elder_ward_id is not None:
            ward = lookup_creature(other_creatures, c.elder_ward_id, other_by_id)
            if ward is not None and (ward.is_dead or ward.life_stage != LIFE_STAGE_CHILD):
                ward = None

            if ward is not None:
                if c.carried_fruit or c.carried_water:
                    result = self.actions.deliver_resource_to(ward)
                    if result is not None:
                        return result
                elif self._child_needs_help(ward, visible_companions, other_creatures):
                    return self._tend_to(ward, ctx.visible_fruits, ctx.visible_water, dt)
            c.elder_ward_id = None
            c.carried_fruit = False
            c.carried_water = False

        if c.elder_ward_check_timer > 0:
            c.elder_ward_check_timer -= dt
            return None
        c.elder_ward_check_timer = random.uniform(*ELDER_WARD_CHECK_INTERVAL)

        candidates = [o for o in visible_companions
                     if o.life_stage == LIFE_STAGE_CHILD
                     and self._child_needs_help(o, visible_companions, other_creatures)]
        if not candidates:
            return None

        ward = min(candidates, key=c.distance_to)
        c.elder_ward_id = ward.id
        c.social.adjust_mutual_relationship(ward, RELATIONSHIP_HELP_BONUS_HELPER, RELATIONSHIP_HELP_BONUS_HELPED)
        c.communication.share_information(ward)

        return self._tend_to(ward, ctx.visible_fruits, ctx.visible_water, dt)

    def _tend_to(self, ward, visible_fruits, visible_water, dt):
        c = self.c
        c.state = STATE_SEEKING
        c.energy = max(0.0, c.energy - ELDER_WARD_ENERGY_DRAIN_RATE * dt)

        if ward.hunger < CHILD_FEED_HUNGER_THRESHOLD:
            goal = self.actions.go_fetch_fruit(visible_fruits)
            if goal:
                c.goal_text = INFO_CREATURE_GOAL_ELDER_WARD_FETCH
                return goal
        if ward.thirst < CHILD_FEED_THIRST_THRESHOLD:
            goal = self.actions.go_fetch_water(visible_water)
            if goal:
                c.goal_text = INFO_CREATURE_GOAL_ELDER_WARD_FETCH
                return goal

        if c.distance_to(ward) > HELP_APPROACH_DISTANCE:
            c.goal_text = INFO_CREATURE_GOAL_ELDER_WARD_APPROACH
            return (ward.x, ward.y)

        campfire_pos = self.instincts.nearest_known_campfire()
        if campfire_pos and math.hypot(ward.x - campfire_pos[0], ward.y - campfire_pos[1]) > CAMPFIRE_RADIUS * 0.6:
            c.goal_text = INFO_CREATURE_GOAL_ELDER_WARD_LEAD
            return campfire_pos

        c.goal_text = INFO_CREATURE_GOAL_ELDER_WARD_COMFORT
        return (c.x, c.y)


# =========================================================================
# Стратегия любопытства старика: опасность узнаётся мгновенно
# =========================================================================

class ElderCuriosityStrategy(CuriosityStrategy):

    def __init__(self, creature):
        self.c = creature

    def pursue(self, unknown_harmless, unknown_hazards):
        c = self.c

        if unknown_hazards:
            for spike in unknown_hazards:
                c.memory.add_memory("spike", spike.x, spike.y, importance=-1.5)
            c.knowledge["spike"] = True
            c.state = STATE_CALM
            c.goal_text = INFO_CREATURE_GOAL_ELDER_HAZARD_KNOWN

        interested_harmless = [(t, obj) for t, obj in unknown_harmless if t in c.curiosity_interested]
        if not interested_harmless:
            c.curiosity_active = False
            return None

        c.curiosity_active = True
        c.state = STATE_SEEKING
        target_type, target_obj = min(interested_harmless, key=lambda p: c.distance_to(p[1]))
        c.goal_text = INFO_CREATURE_GOAL_CURIOSITY_UNKNOWN
        c.target = (target_obj.x, target_obj.y)
        return c.target


# =========================================================================
# Оркестратор
# =========================================================================

class OlderAI:

    def __init__(self, creature, instincts):
        self.c = creature
        self.instincts = instincts

        self.actions = ResourceActions(creature)
        self.roads = Roads(creature, follow_dampener=ELDER_ROAD_FOLLOW_DAMPENER)

        self.survival = SurvivalNeeds(creature, instincts, self.roads)
        self.corpse_handling = CorpseHandling(creature, instincts)
        self.ward_care = ElderWardCare(creature, instincts, self.actions)
        self.feeding = Feeding(creature, self.actions)
        self.social_response = SocialResponse(creature)
        self.partner_bond = PartnerBond(creature)
        self.storage = Storage(creature, instincts, self.actions)
        self.curiosity = Curiosity(creature, ElderCuriosityStrategy(creature))

        # ---------- территории, пубертата и проверки детских дорог у стариков нет -
        # не заглушки в общем файле, а просто отсутствие в этом списке ----------
        self.components = [
            self.survival, self.corpse_handling, self.ward_care, self.feeding,
            self.social_response, self.partner_bond, self.storage, self.roads,
            self.curiosity,
        ]

    def decide(self, ctx):
        considerations = []
        for comp in self.components:
            considerations.extend(comp.consider(ctx))
        return pick_best(considerations)