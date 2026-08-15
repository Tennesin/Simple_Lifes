import random
import math
from .ci_settings import *

class CreatureAging:

    def __init__(self, creature):
        self.c = creature
        self._old_modifiers_applied = False
        self._puberty_synced = False

    def update(self, dt):
        c = self.c
        c.age += dt

        new_stage = self.compute_stage(c.age)
        if new_stage != c.life_stage:
            self._on_stage_changed(c.life_stage, new_stage)
            c.life_stage = new_stage

        if c.age >= AGE_NATURAL_DEATH_START:
            self._check_natural_death(dt)

        self._update_puberty(dt)

    @staticmethod
    def compute_stage(age):
        if age < AGE_CHILD_END:
            return LIFE_STAGE_CHILD
        elif age < AGE_YOUNG_ADULT_END:
            return LIFE_STAGE_ADULT
        else:
            return LIFE_STAGE_OLD

    def _on_stage_changed(self, old_stage, new_stage):
        c = self.c
        if new_stage == LIFE_STAGE_OLD:
            self._apply_old_modifiers()
            if c.puberty_active:
                self._end_puberty()
        elif old_stage == LIFE_STAGE_CHILD and new_stage == LIFE_STAGE_ADULT:
            c.child_distress_timer = 0.0
            c.play_target_id = None
            c.play_role = None
            c.play_timer = 0.0

    def _apply_old_modifiers(self):
        c = self.c
        if self._old_modifiers_applied:
            return
        c.base_speed_multiplier *= OLD_SPEED_MULTIPLIER
        c.memory.decay_time /= OLD_MEMORY_DECAY_MULTIPLIER
        c.memory.intuitive_decay_time /= OLD_MEMORY_DECAY_MULTIPLIER
        self._old_modifiers_applied = True

    def sync_stage_modifiers(self):
        if self.c.life_stage == LIFE_STAGE_OLD:
            self._apply_old_modifiers()

    def _check_natural_death(self, dt):
        c = self.c
        if c.age >= AGE_NATURAL_DEATH_MAX:
            c.die("старость")
            return
        progress = (c.age - AGE_NATURAL_DEATH_START) / (AGE_NATURAL_DEATH_MAX - AGE_NATURAL_DEATH_START)
        chance_per_sec = AGE_NATURAL_DEATH_CHANCE_PER_SEC * (1.0 + progress * 4.0)
        if random.random() < chance_per_sec * dt:
            c.die("старость")

    def _update_puberty(self, dt):
        c = self.c
        if c.puberty_done:
            return
        if c.puberty_active:
            c.puberty_timer -= dt
            if c.puberty_timer <= 0:
                self._end_puberty()
            return
        if c.life_stage != LIFE_STAGE_ADULT:
            return
        if c.age >= c.puberty_trigger_age:
            self._start_puberty()

    def _start_puberty(self):
        c = self.c
        if c.puberty_active or c.puberty_done:
            return
        c.puberty_active = True
        c.puberty_timer = random.uniform(*PUBERTY_DURATION_RANGE)

        c._puberty_speed_bonus = random.uniform(*PUBERTY_SPEED_BONUS_RANGE)
        c.base_speed_multiplier *= (1.0 + c._puberty_speed_bonus)

        c._puberty_orig_curiosity = c.curiosity
        c.curiosity = random.uniform(*PUBERTY_CURIOSITY_RANGE)

    def _end_puberty(self):
        c = self.c
        c.puberty_active = False
        c.puberty_done = True
        c.puberty_timer = 0.0

        if c._puberty_speed_bonus:
            c.base_speed_multiplier /= (1.0 + c._puberty_speed_bonus)
            c._puberty_speed_bonus = 0.0

        if c._puberty_orig_curiosity is not None:
            c.curiosity = c._puberty_orig_curiosity
            c._puberty_orig_curiosity = None

    def sync_puberty_state(self):
        c = self.c
        if self._puberty_synced:
            return
        self._puberty_synced = True

        if not c.puberty_active:
            return

        if c._puberty_speed_bonus == 0.0:
            c._puberty_speed_bonus = random.uniform(*PUBERTY_SPEED_BONUS_RANGE)
        c.base_speed_multiplier *= (1.0 + c._puberty_speed_bonus)

        if c._puberty_orig_curiosity is None:
            c._puberty_orig_curiosity = c.curiosity
        c.curiosity = random.uniform(*PUBERTY_CURIOSITY_RANGE)

    def effective_vision_radius(self):
        c = self.c
        if c.life_stage == LIFE_STAGE_OLD:
            return VISION_RADIUS * OLD_VISION_RADIUS_MULTIPLIER
        return VISION_RADIUS

class CreatureFamily:

    def __init__(self, creature):
        self.c = creature
        self.pair_check_timer = random.uniform(*FAMILY_PAIR_CHECK_INTERVAL)
        self.birth_cooldown = 0.0

    def update(self, dt, other_creatures, creatures_by_id=None, storage_fields=None):
        c = self.c
        if c.is_dead or c.is_grabbed:
            return None

        if self.birth_cooldown > 0:
            self.birth_cooldown -= dt

        partner = self._find_partner(other_creatures, c.partner_id, creatures_by_id)
        self._validate_partner(partner)

        self.pair_check_timer -= dt
        if (c.partner_id is None and c.life_stage == LIFE_STAGE_ADULT
                and self.pair_check_timer <= 0):
            self.pair_check_timer = random.uniform(*FAMILY_PAIR_CHECK_INTERVAL)
            self._try_form_pair(other_creatures, storage_fields)
            if c.partner_id is not None and (partner is None or partner.id != c.partner_id):
                partner = self._find_partner(other_creatures, c.partner_id, creatures_by_id)

        if c.is_pregnant:
            return self._update_pregnancy(dt)

        self._try_conceive(dt, partner)
        return None

    def _find_partner(self, other_creatures, partner_id, creatures_by_id):
        if partner_id is None:
            return None
        if creatures_by_id is not None:
            return creatures_by_id.get(partner_id)
        return self._find_creature(other_creatures, partner_id)

    # ---------- Проверка актуальности партнёра ----------

    def _validate_partner(self, partner):
        c = self.c
        if c.partner_id is None:
            return
        if partner is None or partner.is_dead:
            c.partner_id = None
            c.is_pregnant = False
            c.pregnancy_timer = 0.0
            c.reuniting_with_partner = False
            c.reunite_commit_timer = 0.0
            c.psyche.on_partner_lost()

    # ---------- Зачатие ----------

    def _try_conceive(self, dt, partner):
        c = self.c
        if c.gender != GENDER_FEMALE:
            return
        if c.life_stage != LIFE_STAGE_ADULT:
            return
        if c.partner_id is None or self.birth_cooldown > 0:
            return
        if c.panic_active or c.fear_timer > 0 or c.is_sleeping:
            return
        if c.needs.wellbeing_score() < FAMILY_MIN_WELLBEING:
            return

        if partner is None or partner.is_dead:
            return
        if partner.life_stage != LIFE_STAGE_ADULT:
            return
        if c.distance_to(partner) > TALK_DISTANCE:
            return
        if partner.panic_active or partner.fear_timer > 0 or partner.is_sleeping:
            return

        chance = PREGNANCY_CHANCE_PER_SEC
        if c.puberty_active or partner.puberty_active:
            chance *= PUBERTY_PREGNANCY_CHANCE_MULTIPLIER

        if random.random() < chance * dt:
            c.is_pregnant = True
            c.pregnancy_timer = random.uniform(*PREGNANCY_DURATION)

    # ---------- Образование пары ----------

    def _try_form_pair(self, other_creatures, storage_fields=None):
        c = self.c
        if c.panic_active or c.fear_timer > 0 or c.is_sleeping:
            return
        if c.needs.wellbeing_score() < FAMILY_MIN_WELLBEING:
            return

        my_threshold = FAMILY_MIN_RELATIONSHIP - (PUBERTY_PAIR_RELATIONSHIP_DISCOUNT if c.puberty_active else 0.0)
        my_threshold -= c.psyche.pairing_relationship_discount()

        candidates = []
        for other in other_creatures:
            if other is c or other.is_dead or other.is_grabbed:
                continue
            if self._is_blood_relative(other):
                continue
            if other.gender == c.gender or other.life_stage != LIFE_STAGE_ADULT:
                continue
            if other.partner_id is not None:
                continue
            if c.distance_to(other) > FAMILY_BOND_DISTANCE:
                continue
            if other.panic_active or other.fear_timer > 0 or other.is_sleeping:
                continue
            if other.needs.wellbeing_score() < FAMILY_MIN_WELLBEING:
                continue
            other_threshold = FAMILY_MIN_RELATIONSHIP - (
                PUBERTY_PAIR_RELATIONSHIP_DISCOUNT if other.puberty_active else 0.0)
            other_threshold -= other.psyche.pairing_relationship_discount()
            if c.social.get_relationship(other) < my_threshold:
                continue
            if other.social.get_relationship(c) < other_threshold:
                continue
            candidates.append(other)

        if not candidates:
            return

        partner = min(candidates, key=lambda o: c.social.pairing_score(o, storage_fields))
        c.partner_id = partner.id
        partner.partner_id = c.id
        c.social.adjust_mutual_relationship(partner, FAMILY_PAIR_BOND_BONUS)
        c.psyche.on_pair_formed()
        partner.psyche.on_pair_formed()

    def _is_blood_relative(self, other):
        c = self.c
        if c.parent_ids and other.id in c.parent_ids:
            return True
        if other.parent_ids and c.id in other.parent_ids:
            return True
        return _shares_parent(c.parent_ids, other.parent_ids)

    # ---------- Течение беременности ----------

    def _update_pregnancy(self, dt):
        c = self.c
        if c.needs.wellbeing_score() < PREGNANCY_MIN_WELLBEING_TO_CARRY:
            c.is_pregnant = False
            c.pregnancy_timer = 0.0
            self.birth_cooldown = FAMILY_COOLDOWN_AFTER_BIRTH * 0.5
            return None

        c.pregnancy_timer -= dt
        if c.pregnancy_timer <= 0:
            c.is_pregnant = False
            c.pregnancy_timer = 0.0
            self.birth_cooldown = FAMILY_COOLDOWN_AFTER_BIRTH
            c.psyche.on_birth()
            return c.partner_id
        return None

    def has_living_parent(self, other_creatures):
        c = self.c
        if not c.parent_ids:
            return False
        for pid in c.parent_ids:
            if pid is None:
                continue
            parent = self._find_creature(other_creatures, pid)
            if parent is not None and not parent.is_dead:
                return True
        return False

    def has_family(self, other_creatures):
        c = self.c
        if c.partner_id is not None:
            return True
        return any(o.parent_ids and c.id in o.parent_ids and not o.is_dead for o in other_creatures)

    # ---------- Утилита ----------

    @staticmethod
    def _find_creature(creatures, creature_id):
        for cr in creatures:
            if cr.id == creature_id:
                return cr
        return None

class CreatureTerritory:

    def __init__(self, creature):
        self.c = creature
        self.usage_time = {}            # id(obj) -> накопленное время рядом с ресурсом
        self.claims_count = {"bush": 0, "water": 0}
        self.confront_cooldowns = {}    # other_id -> оставшееся время до следующей реакции

    # ---------- Накопление времени использования ----------

    def register_use(self, obj, resource_type, dt, campfires=None):
        c = self.c
        if c.gender != TERRITORY_ENABLED_GENDER or c.life_stage == LIFE_STAGE_OLD:
            return
        if getattr(obj, "claimed_by", None) is not None:
            return  # уже чей-то (свой или чужой) - копить незачем
        if campfires and self._is_public_domain(obj, campfires):
            return  # рядом с костром - общая земля, приватизации не подлежит

        key = obj.id
        self.usage_time[key] = self.usage_time.get(key, 0.0) + dt

        if self.usage_time[key] >= TERRITORY_CLAIM_TIME:
            if self.claims_count.get(resource_type, 0) < TERRITORY_MAX_CLAIMS_PER_TYPE:
                obj.claimed_by = c.id
                self.claims_count[resource_type] = self.claims_count.get(resource_type, 0) + 1
            del self.usage_time[key]

    def _is_public_domain(self, obj, campfires):
        for fire in campfires:
            if math.hypot(obj.x - fire.x, obj.y - fire.y) < TERRITORY_PUBLIC_DOMAIN_RADIUS:
                return True
        return False

    # ---------- "Свой/чужой" ----------

    def is_exempt(self, other):
        c = self.c
        if other.id == c.partner_id:
            return True
        if other.parent_ids and c.id in other.parent_ids:
            return True
        if TERRITORY_EXEMPT_ALL_CHILDREN and other.life_stage == LIFE_STAGE_CHILD:
            return True
        if other.gender == GENDER_FEMALE and other.is_pregnant:
            return True
        if getattr(other, "is_dragging_corpse", False):
            return True
        return False

    # ---------- Тик кулдаунов (вызывается из brain.decide) ----------

    def tick_cooldowns(self, dt):
        for oid in list(self.confront_cooldowns.keys()):
            self.confront_cooldowns[oid] -= dt
            if self.confront_cooldowns[oid] <= 0:
                del self.confront_cooldowns[oid]

    # ---------- Поиск нарушителя среди видимых существ ----------

    def find_intrusion(self, visible_bushes, visible_water, visible_companions):
        c = self.c
        if c.gender != TERRITORY_ENABLED_GENDER or c.life_stage == LIFE_STAGE_OLD:
            return None

        my_objects = [b for b in visible_bushes if getattr(b, "claimed_by", None) == c.id] + \
                     [w for w in visible_water if getattr(w, "claimed_by", None) == c.id]
        if not my_objects:
            return None

        for obj in my_objects:
            for other in visible_companions:
                if self.is_exempt(other) or other.id in self.confront_cooldowns:
                    continue
                dist = math.hypot(other.x - obj.x, other.y - obj.y)
                if dist < TERRITORY_INTRUSION_RADIUS:
                    return (other, obj)
        return None

    # ---------- Синхронизация после загрузки мира ----------

    def sync_claims_count(self, bushes, water_puddles):
        c = self.c
        self.claims_count["bush"] = sum(
            1 for b in bushes if getattr(b, "claimed_by", None) == c.id
        )
        self.claims_count["water"] = sum(
            1 for w in water_puddles if getattr(w, "claimed_by", None) == c.id
        )

    def confront(self, intruder):
        c = self.c
        self.confront_cooldowns[intruder.id] = random.uniform(*TERRITORY_CONFRONT_COOLDOWN)
        c.social.adjust_relationship(intruder, TERRITORY_INTRUDER_PENALTY)

        intruder.fear_timer = max(intruder.fear_timer, TERRITORY_CONFRONT_FEAR_DURATION)
        intruder.fear_source = (c.x, c.y)
        intruder.following_road = None
        intruder.following_road_active = False
        intruder.road_entry_reached = False
        intruder.psyche.on_territory_intruded()
        c.psyche.on_territory_defended()

# =========================================================================
# Домен: скорбь по умершим сородичам - разовое событие в момент смерти
# =========================================================================

def _shares_parent(ids_a, ids_b):
    if not ids_a or not ids_b:
        return False
    set_a = {pid for pid in ids_a if pid is not None}
    set_b = {pid for pid in ids_b if pid is not None}
    return bool(set_a & set_b)

def _grief_death_shock_multiplier(cause, deceased_age):
    if cause == "старость":
        return GRIEF_NATURAL_OLD_AGE_MULTIPLIER
    youth_ratio = 1.0 - max(0.0, min(1.0, deceased_age / AGE_NATURAL_DEATH_START))
    return GRIEF_UNNATURAL_DEATH_MULTIPLIER + youth_ratio * GRIEF_YOUTH_SHOCK_BONUS

def _grief_mourner_age_multiplier(life_stage):
    if life_stage == LIFE_STAGE_CHILD:
        return GRIEF_CHILD_MOURNER_MULTIPLIER
    if life_stage == LIFE_STAGE_OLD:
        return GRIEF_OLD_MOURNER_MULTIPLIER
    return 1.0

def _grief_kinship_penalty(deceased, mourner):
    if mourner.partner_id == deceased.id:
        return 0.0

    if mourner.parent_ids and deceased.id in mourner.parent_ids:
        return GRIEF_BASE_PENALTY["parent_child"]
    if deceased.parent_ids and mourner.id in deceased.parent_ids:
        return GRIEF_BASE_PENALTY["parent_child"]
    if _shares_parent(mourner.parent_ids, deceased.parent_ids):
        return GRIEF_BASE_PENALTY["sibling"]

    relationship = mourner.relationships.get(deceased.id, 0.0)
    is_ward_bond = getattr(mourner, "elder_ward_id", None) == deceased.id
    if is_ward_bond or relationship >= CLOSE_FRIEND_SANITY_RELATIONSHIP:
        return GRIEF_BASE_PENALTY["close_bond"]
    if relationship >= GRIEF_ACQUAINTANCE_MIN_RELATIONSHIP:
        return GRIEF_BASE_PENALTY["acquaintance"]

    if GRIEF_WITNESS_VISION_ONLY:
        vision_radius = mourner.aging.effective_vision_radius()
        if math.hypot(mourner.x - deceased.x, mourner.y - deceased.y) < vision_radius:
            return GRIEF_BASE_PENALTY["witness_stranger"]

    return 0.0

def apply_grief_for_death(deceased, living_creatures):
    shock = _grief_death_shock_multiplier(deceased.death_cause, deceased.age)

    for mourner in living_creatures:
        if mourner is deceased or mourner.is_dead:
            continue
        base_penalty = _grief_kinship_penalty(deceased, mourner)
        if base_penalty == 0.0:
            continue
        age_mult = _grief_mourner_age_multiplier(mourner.life_stage)
        mourner.psyche.on_grief(base_penalty * shock * age_mult)