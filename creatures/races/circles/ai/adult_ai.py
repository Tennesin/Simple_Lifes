import math
import random

from ..ci_settings import *
from ..ci_info import *
from .patterns import (
    GoalComponent, ResourceActions, Roads, SurvivalNeeds, CorpseHandling,
    EmpathyHelp, Feeding, SocialResponse, PartnerBond,
    ChildRoadVerification, Curiosity, CuriosityStrategy,
    )
from .private_storage import PrivateStorage, PrivateConstruction
from ..life_cycle import is_blood_relative
from ....all_needed.ai.utility import Consideration, pick_best

# =========================================================================
# Территориальная защита - только у AdultAI
# =========================================================================

class TerritoryDefense(GoalComponent):
    SCORE_COMMITTED = 70.0
    SCORE_NEW = 65.0

    def __init__(self, creature):
        self.c = creature

    def consider(self, ctx):
        c = self.c
        if c.gender != TERRITORY_ENABLED_GENDER:
            return [None]

        cached_intrusion = None
        if c.territory_pursuit_target_id is not None:
            score = self.SCORE_COMMITTED
        else:
            cached_intrusion = c.territory.find_intrusion(
                ctx.visible_bushes, ctx.visible_water, ctx.visible_companions)
            if cached_intrusion is None:
                return [None]
            score = self.SCORE_NEW

        def execute():
            return self._pursue(ctx, cached_intrusion)

        return [Consideration("territory", score, execute)]

    def _pursue(self, ctx, cached_intrusion=None):
        c = self.c
        visible_bushes, visible_water, visible_companions, dt = (
            ctx.visible_bushes, ctx.visible_water, ctx.visible_companions, ctx.dt)

        if c.territory_pursuit_commit_timer > 0:
            c.territory_pursuit_commit_timer -= dt

        if c.territory_pursuit_target_id is not None:
            intruder = next((o for o in visible_companions
                             if o.id == c.territory_pursuit_target_id), None)
            obj = c.territory_pursuit_obj

            still_near_object = False
            if intruder is not None and obj is not None:
                still_near_object = (
                    math.hypot(intruder.x - obj.x, intruder.y - obj.y)
                    < TERRITORY_INTRUSION_RADIUS * TERRITORY_PURSUIT_EXIT_RADIUS_FACTOR
                )
                c.territory_pursuit_last_pos = (intruder.x, intruder.y)

            keep_pursuing = still_near_object or c.territory_pursuit_commit_timer > 0

            if keep_pursuing and c.territory_pursuit_last_pos is not None:
                c.state = STATE_SEEKING
                c.goal_text = INFO_CREATURE_GOAL_TERRITORY_GUARD
                target_pos = c.territory_pursuit_last_pos
                if math.hypot(c.x - target_pos[0], c.y - target_pos[1]) > TERRITORY_GUARD_APPROACH_DISTANCE:
                    c.target = target_pos
                else:
                    c.target = (c.x, c.y)
                return c.target

            c.territory_pursuit_target_id = None
            c.territory_pursuit_obj = None
            c.territory_pursuit_last_pos = None

        # ---------- НОВОЕ: используем то, что уже посчитано в consider(),
        # и пересчитываем find_intrusion только если сюда попали без кэша
        # (например, из ветки "committed", где до этого intrusion не искали) ----------
        intrusion = cached_intrusion if cached_intrusion is not None else c.territory.find_intrusion(
            visible_bushes, visible_water, visible_companions)
        if intrusion is None:
            return None
        intruder, obj = intrusion

        if random.random() > c.psyche.territory_boldness():
            return None
        c.territory.confront(intruder)

        c.territory_pursuit_target_id = intruder.id
        c.territory_pursuit_obj = obj
        c.territory_pursuit_last_pos = (intruder.x, intruder.y)
        c.territory_pursuit_commit_timer = TERRITORY_PURSUIT_COMMIT_TIME

        c.state = STATE_SEEKING
        c.goal_text = INFO_CREATURE_GOAL_TERRITORY_GUARD
        if c.distance_to(intruder) > TERRITORY_GUARD_APPROACH_DISTANCE:
            c.target = (intruder.x, intruder.y)
        else:
            c.target = (c.x, c.y)
        return c.target

# =========================================================================
# Гормональный бум - активное ухаживание за партнёром - только у AdultAI
# =========================================================================

class PubertyCourtship(GoalComponent):
    SCORE = 35.0

    def __init__(self, creature):
        self.c = creature

    def consider(self, ctx):
        c = self.c
        if not c.puberty_active or c.partner_id is not None:
            self._reset_courtship()
            c.puberty_courtship_fail_streak = 0
            return [None]
        if c.panic_active or c.fear_timer > 0 or c.is_sleeping:
            return [None]
        wellbeing_threshold = FAMILY_MIN_WELLBEING - PUBERTY_WELLBEING_DISCOUNT
        if c.needs.wellbeing_score() < wellbeing_threshold:
            return [None]
        if c.puberty_courtship_cooldown > 0:
            return [None]

        def execute():
            return self._pursue(ctx)

        return [Consideration("puberty", self.SCORE, execute)]

    # ---------- Сброс состояния ухаживания ----------

    def _reset_courtship(self):
        c = self.c
        c.puberty_courtship_target_id = None
        c.puberty_courtship_timer = 0.0
        c.puberty_courtship_deadline = 0.0

    def _tick_avoid_list(self, dt):
        c = self.c
        if not c.puberty_courtship_avoid:
            return
        expired = []
        for target_id, remaining in c.puberty_courtship_avoid.items():
            remaining -= dt
            if remaining <= 0:
                expired.append(target_id)
            else:
                c.puberty_courtship_avoid[target_id] = remaining
        for target_id in expired:
            del c.puberty_courtship_avoid[target_id]

    # ---------- Выбор/удержание цели ----------

    def _resolve_committed_target(self, visible_companions):
        c = self.c
        if c.puberty_courtship_target_id is None:
            return None
        target = next((o for o in visible_companions if o.id == c.puberty_courtship_target_id), None)
        if (target is None or target.is_dead or target.partner_id is not None
                or target.is_sleeping or target.panic_active or target.fear_timer > 0):
            self._reset_courtship()
            return None
        return target

    def _pick_new_target(self, ctx):
        c = self.c
        wellbeing_threshold = FAMILY_MIN_WELLBEING - PUBERTY_WELLBEING_DISCOUNT
        my_threshold = (FAMILY_MIN_RELATIONSHIP - PUBERTY_PAIR_RELATIONSHIP_DISCOUNT
                        - c.psyche.pairing_relationship_discount())

        candidates = [
            o for o in ctx.visible_companions
            if o.gender != c.gender
               and o.life_stage == LIFE_STAGE_ADULT
               and o.partner_id is None
               and not o.is_dead and not o.is_sleeping
               and not o.panic_active and o.fear_timer <= 0
               and o.id not in c.puberty_courtship_avoid
               and not is_blood_relative(c, o)
               and o.needs.wellbeing_score() >= wellbeing_threshold
               and c.social.get_relationship(o) >= my_threshold
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda o: c.social.pairing_score(o, ctx.storage_fields))

    def _give_up_on(self, target_id):
        c = self.c
        c.puberty_courtship_avoid[target_id] = random.uniform(*PUBERTY_COURTSHIP_REJECT_COOLDOWN)
        c.puberty_courtship_fail_streak += 1
        self._reset_courtship()

        if c.puberty_courtship_fail_streak >= PUBERTY_COURTSHIP_MAX_FAIL_STREAK:
            c.puberty_courtship_fail_streak = 0
            c.puberty_courtship_cooldown = random.uniform(*PUBERTY_COURTSHIP_LONG_COOLDOWN)
        else:
            c.puberty_courtship_cooldown = random.uniform(*PUBERTY_COURTSHIP_RECHECK_INTERVAL)

    # ---------- Основная логика тика ----------

    def _pursue(self, ctx):
        c = self.c
        dt = ctx.dt

        if not c.puberty_active or c.partner_id is not None:
            self._reset_courtship()
            return None
        if c.panic_active or c.fear_timer > 0 or c.is_sleeping:
            return None

        wellbeing_threshold = FAMILY_MIN_WELLBEING - PUBERTY_WELLBEING_DISCOUNT
        if c.needs.wellbeing_score() < wellbeing_threshold:
            return None

        if c.puberty_courtship_cooldown > 0:
            c.puberty_courtship_cooldown -= dt
            return None

        self._tick_avoid_list(dt)

        target = self._resolve_committed_target(ctx.visible_companions)
        if target is None:
            target = self._pick_new_target(ctx)
            if target is None:
                c.puberty_courtship_cooldown = random.uniform(*PUBERTY_COURTSHIP_RECHECK_INTERVAL)
                return None
            c.puberty_courtship_target_id = target.id
            c.puberty_courtship_timer = 0.0
            c.puberty_courtship_deadline = random.uniform(*PUBERTY_COURTSHIP_ATTEMPT_DURATION)

        c.puberty_courtship_timer += dt
        if c.puberty_courtship_timer > c.puberty_courtship_deadline:
            self._give_up_on(target.id)
            return None

        c.state = STATE_SEEKING
        c.goal_text = INFO_CREATURE_GOAL_PUBERTY_COURT

        if c.distance_to(target) > TALK_DISTANCE:
            c.target = (target.x, target.y)
        else:
            c.target = (c.x, c.y)
        return c.target

# =========================================================================
# Стратегия любопытства взрослого: опасность изучается вблизи
# =========================================================================

class AdultCuriosityStrategy(CuriosityStrategy):

    def __init__(self, creature):
        self.c = creature

    def pursue(self, unknown_harmless, unknown_hazards):
        c = self.c
        interested_harmless = [(t, obj) for t, obj in unknown_harmless if t in c.curiosity_interested]
        interested_hazards = unknown_hazards if "spike" in c.curiosity_interested else []

        if not interested_harmless and not interested_hazards:
            c.curiosity_active = False
            return None

        c.curiosity_active = True
        c.state = STATE_SEEKING

        if interested_hazards:
            target_obj = min(interested_hazards, key=c.distance_to)
            dx = c.x - target_obj.x
            dy = c.y - target_obj.y
            d = math.hypot(dx, dy)
            if d <= CURIOSITY_HAZARD_STUDY_DISTANCE:
                c.memory.add_memory("spike", target_obj.x, target_obj.y, importance=-1.5)
                c.knowledge["spike"] = True
                c.goal_text = INFO_CREATURE_GOAL_CURIOSITY_HAZARD_KNOWN
                c.target = (c.x, c.y)
                return c.target
            ratio = CURIOSITY_HAZARD_STUDY_DISTANCE / d
            approach_point = (target_obj.x + dx * ratio, target_obj.y + dy * ratio)
            c.goal_text = INFO_CREATURE_GOAL_CURIOSITY_HAZARD_STUDY
            c.target = approach_point
            return approach_point

        target_type, target_obj = min(interested_harmless, key=lambda p: c.distance_to(p[1]))
        c.goal_text = INFO_CREATURE_GOAL_CURIOSITY_UNKNOWN
        c.target = (target_obj.x, target_obj.y)
        return c.target

# =========================================================================
# Оркестратор: явный список компонентов вместо MRO-магии
# =========================================================================

class AdultAI:

    def __init__(self, creature, instincts):
        self.c = creature
        self.instincts = instincts

        self.actions = ResourceActions(creature)
        self.roads = Roads(creature, follow_dampener=1.0)

        self.survival = SurvivalNeeds(creature, instincts, self.roads)
        self.corpse_handling = CorpseHandling(creature, instincts)
        self.empathy = EmpathyHelp(creature, instincts)
        self.feeding = Feeding(creature, self.actions)
        self.social_response = SocialResponse(creature)
        self.territory = TerritoryDefense(creature)
        self.puberty = PubertyCourtship(creature)
        self.partner_bond = PartnerBond(creature)
        self.storage = PrivateStorage(creature, instincts, self.actions)
        self.construction = PrivateConstruction(creature, instincts, self.roads)
        self.child_road_verification = ChildRoadVerification(creature)
        self.curiosity = Curiosity(creature, AdultCuriosityStrategy(creature))

        self.components = [
            self.survival, self.corpse_handling, self.empathy, self.feeding,
            self.social_response, self.territory, self.puberty, self.partner_bond,
            self.storage, self.construction, self.roads,
            self.child_road_verification, self.curiosity,
        ]

    def decide(self, ctx):
        considerations = []
        for comp in self.components:
            considerations.extend(comp.consider(ctx))
        return pick_best(considerations)
