import math
import random

from ...ci_settings import *
from ...ci_info import *
from .....all_needed.ai.utility import Consideration, scale, GoalComponent, lookup_creature

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