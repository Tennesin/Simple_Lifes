import math
import random
import settings
from settings import *
from .ci_settings import *
from .ci_info import *
from ...all_needed import geometry

class CreatureInteractions:

    def __init__(self, creature):
        self.c = creature

    def process(self, fruits, spikes, water_puddles, bushes, campfires, other_creatures,
                storage_fields, dt, walls=None, biome_grid=None):
        self._eat_fruits(fruits, other_creatures)
        self._drink_water(water_puddles, dt, other_creatures, biome_grid=biome_grid, campfires=campfires)
        self._feed_from_storage_field(storage_fields)
        self._hit_spikes(spikes, other_creatures, walls, biome_grid=biome_grid)
        self._push_out_of_bushes(bushes, biome_grid=biome_grid)
        self._linger_near_bush(bushes, dt, campfires=campfires)
        self._warm_by_campfires(campfires, dt)
        self._talk_to_companions(other_creatures, dt)
        self._receive_elder_support(other_creatures, dt)
        self._check_jealousy(other_creatures, dt)

    def _child_must_wait_for_parent(self, other_creatures):
        c = self.c
        return c.life_stage == LIFE_STAGE_CHILD and c.family.has_living_parent(other_creatures)

    def _eat_fruits(self, fruits, other_creatures):
        c = self.c
        if self._child_must_wait_for_parent(other_creatures):
            return
        if c.hunger >= HUNGER_SATISFY_THRESHOLD and c.hp >= HP_MAX:
            return
        for fruit in fruits:
            if fruit.active and c.distance_to(fruit) < EAT_DISTANCE:
                self._register_resource_rivals(fruit, other_creatures, need_attr="hunger")
                fruit.active = False
                c.hp = min(c.hp + FRUIT_HP_BONUS, HP_MAX)
                c.hunger = min(c.hunger + FRUIT_HUNGER_BONUS, HUNGER_MAX)
                c.memory.add_memory("fruit", fruit.x, fruit.y, importance=2.0)
                c.knowledge["fruit"] = True

    def _register_resource_rivals(self, obj, other_creatures, need_attr):
        c = self.c
        for other in other_creatures:
            if other is c or other.is_dead:
                continue
            if getattr(other, need_attr) >= RESOURCE_STEAL_MIN_HUNGER_URGENCY:
                continue  # рыл не был голоден - ему всё равно
            if math.hypot(other.x - obj.x, other.y - obj.y) > RESOURCE_COMPETE_RADIUS:
                continue
            # он тоже спешил сюда и явно голодал - обидится
            other.social.adjust_relationship(c, RESOURCE_STEAL_PENALTY)

    def _drink_water(self, water_puddles, dt, other_creatures, biome_grid=None, campfires=None):
        c = self.c
        if self._child_must_wait_for_parent(other_creatures):
            return
        if c.thirst >= THIRST_SATISFY_THRESHOLD:
            return
        for water in water_puddles:
            if not water.has_water():
                continue
            if c.distance_to(water) < EAT_DISTANCE + water.radius:
                self._register_resource_rivals(water, other_creatures, need_attr="thirst")
                deficit_ratio = max(WATER_DRINK_DEFICIT_FLOOR, (THIRST_MAX - c.thirst) / THIRST_MAX)
                wanted = min(WATER_DRINK_RATE * deficit_ratio * dt, THIRST_MAX - c.thirst)
                actual_gain = water.consume(wanted)
                c.thirst = min(c.thirst + actual_gain, THIRST_MAX)
                c.memory.add_memory("water", water.x, water.y, importance=1.5)
                c.knowledge["water"] = True
                c.territory.register_use(water, "water", dt, campfires=campfires)

        if biome_grid is not None and biome_grid.get_at(c.x, c.y) == BIOME_RIVER:
            deficit_ratio = max(WATER_DRINK_DEFICIT_FLOOR, (THIRST_MAX - c.thirst) / THIRST_MAX)
            c.thirst = min(c.thirst + WATER_DRINK_RATE * deficit_ratio * dt, THIRST_MAX)
            c.knowledge["water"] = True

    def _check_jealousy(self, other_creatures, dt):
        c = self.c
        if c.partner_id is None:
            return
        partner = next((o for o in other_creatures if o.id == c.partner_id and not o.is_dead), None)
        if partner is None:
            return
        if c.distance_to(partner) > JEALOUSY_CHECK_DISTANCE:
            return
        for other in other_creatures:
            if other in (c, partner) or other.is_dead:
                continue
            if JEALOUSY_OPPOSITE_GENDER_ONLY and other.gender == partner.gender:
                continue
            if partner.distance_to(other) < TALK_DISTANCE and c.distance_to(other) > TALK_DISTANCE:
                if random.random() < JEALOUSY_CHANCE_PER_SEC * c.psyche.jealousy_modifier() * dt:
                    c.social.adjust_relationship(partner, JEALOUSY_PENALTY_PARTNER)
                    c.social.adjust_relationship(other, JEALOUSY_PENALTY_RIVAL)

    def _hit_spikes(self, spikes, other_creatures, walls=None, biome_grid=None):
        c = self.c
        if c.spike_invuln_timer > 0:
            return
        wall_polylines = [w.points for w in walls if w.points] if walls else []
        for spike in spikes:
            if c.distance_to(spike) < EAT_DISTANCE:
                c.hp -= SPIKE_DAMAGE
                c.spike_invuln_timer = SPIKE_INVULN_DURATION
                dx = c.x - spike.x
                dy = c.y - spike.y
                dist = math.hypot(dx, dy)
                if dist != 0:
                    new_x = c.x + dx / dist * 30
                    new_y = c.y + dy / dist * 30
                    blocked_by_wall = wall_polylines and geometry.segment_blocked_by_polylines(
                        c.x, c.y, new_x, new_y, wall_polylines)
                    blocked_by_sea = (biome_grid is not None
                                      and biome_grid.get_at(new_x, new_y) == BIOME_SEA)
                    if not blocked_by_wall and not blocked_by_sea:
                        c.x = new_x
                        c.y = new_y
                c.x = max(15, min(c.x, settings.WORLD_WIDTH - 15))
                c.y = max(15, min(c.y, settings.WORLD_HEIGHT - 15))
                c.memory.add_memory("spike", spike.x, spike.y, importance=-2.0)
                c.knowledge["spike"] = True
                c.psyche.on_hazard_encountered()

                if c.following_road is not None:
                    c.known_roads[c.following_road.id] = "dangerous"
                    c.following_road.rating = "dangerous"
                    c.following_road = None
                    c.following_road_active = False
                    c.road_progress = 0
                    c.road_entry_reached = False
                    c.goal_text = INFO_CREATURE_GOAL_ROAD_DEADLY

                if c.following_child_road is not None:
                    self._mark_child_road_dangerous(c.following_child_road, other_creatures)

                break

    def _mark_child_road_dangerous(self, road, other_creatures):
        c = self.c
        road.rating = "dangerous"

        c.following_child_road = None
        c.child_road_entry_reached = False
        c.child_road_progress = 0
        c.following_road_active = False
        c.fear_timer = max(c.fear_timer, CHILD_ROAD_DANGER_FEAR_DURATION)
        c.fear_source = (c.x, c.y)
        c.goal_text = INFO_CREATURE_GOAL_CHILD_ROAD_DANGER

        for other in other_creatures:
            if other is c or other.is_dead:
                continue
            if other.following_child_road is road:
                other.following_child_road = None
                other.child_road_entry_reached = False
                other.child_road_progress = 0
                other.following_road_active = False
                other.fear_timer = max(other.fear_timer, CHILD_ROAD_DANGER_FEAR_DURATION)
                other.fear_source = (c.x, c.y)

    def _push_out_of_bushes(self, bushes, biome_grid=None):
        c = self.c
        for bush in bushes:
            min_dist = bush.radius + 12
            if c.distance_to(bush) < min_dist:
                c.knowledge["bush"] = True
                dx = c.x - bush.x
                dy = c.y - bush.y
                dist = math.hypot(dx, dy)
                if dist != 0:
                    push = min_dist - dist
                    new_x = c.x + dx / dist * push
                    new_y = c.y + dy / dist * push
                    if biome_grid is not None and biome_grid.get_at(new_x, new_y) == BIOME_SEA:
                        continue
                    c.x = new_x
                    c.y = new_y
                    c.x = max(15, min(c.x, settings.WORLD_WIDTH - 15))
                    c.y = max(15, min(c.y, settings.WORLD_HEIGHT - 15))

    def _linger_near_bush(self, bushes, dt, campfires=None):
        c = self.c
        for bush in bushes:
            if c.distance_to(bush) < TERRITORY_BUSH_CLAIM_RADIUS:
                c.territory.register_use(bush, "bush", dt, campfires=campfires)

    def _warm_by_campfires(self, campfires, dt):
        c = self.c
        best_ratio = None
        for fire in campfires:
            d = c.distance_to(fire)
            if d < fire.effect_radius:
                ratio = 1.0 - (d / fire.effect_radius)
                if best_ratio is None or ratio > best_ratio:
                    best_ratio = ratio
        if best_ratio is not None:
            # ---------- Чем ближе к огню - тем быстрее восстановление (несколько костров не суммируются) ----------
            rate = SANITY_CAMPFIRE_RESTORE_RATE_FAR + (
                    SANITY_CAMPFIRE_RESTORE_RATE_NEAR - SANITY_CAMPFIRE_RESTORE_RATE_FAR) * best_ratio
            c.consciousness = min(c.consciousness + rate * dt, SANITY_MAX)
            c.knowledge["campfire"] = True
            
    def _talk_to_companions(self, other_creatures, dt):
        c = self.c
        c.is_talking = False
        c.share_info_timer -= dt
        for other in other_creatures:
            if other is c or other.is_dead:
                continue
            if c.distance_to(other) < TALK_DISTANCE:
                c.is_talking = True
                gender_bonus = GENDER_OPPOSITE_TALK_BONUS if c.gender != other.gender else 1.0
                rate = SANITY_TALK_RATE.get(other.temperament, 0.2) * gender_bonus
                c.consciousness = min(c.consciousness + rate * dt, SANITY_MAX)

                talk_mult = PUBERTY_TALK_RATE_MULTIPLIER if c.puberty_active else 1.0
                c.social.adjust_relationship(other, RELATIONSHIP_TALK_RATE * gender_bonus * talk_mult * dt)

                rel = c.social.get_relationship(other)
                c.psyche.on_talk(dt, rel, gender_bonus)

                if rel < QUARREL_THRESHOLD:
                    quarrel_chance = QUARREL_CHANCE_PER_SEC * c.psyche.quarrel_modifier()
                    if c.puberty_active:
                        quarrel_chance *= PUBERTY_QUARREL_CHANCE_MULTIPLIER
                    if random.random() < quarrel_chance * dt:
                        c.social.adjust_mutual_relationship(other, QUARREL_PENALTY)
                        c.psyche.on_quarrel()
                        other.psyche.on_quarrel()

                if c.share_info_timer <= 0:
                    c.communication.share_information(other)
                    c.share_info_timer = random.uniform(*SHARE_INFO_INTERVAL)

    def _receive_elder_support(self, other_creatures, dt):
        c = self.c
        if c.life_stage == LIFE_STAGE_OLD:
            return
        best_ratio = None
        for other in other_creatures:
            if other is c or other.is_dead or other.life_stage != LIFE_STAGE_OLD:
                continue
            d = c.distance_to(other)
            if d < OLD_SANITY_AURA_RADIUS:
                ratio = 1.0 - (d / OLD_SANITY_AURA_RADIUS)
                if best_ratio is None or ratio > best_ratio:
                    best_ratio = ratio
        if best_ratio is not None:
            rate = OLD_SANITY_AURA_RATE_FAR + (OLD_SANITY_AURA_RATE_NEAR - OLD_SANITY_AURA_RATE_FAR) * best_ratio
            c.consciousness = min(c.consciousness + rate * dt, SANITY_MAX)

    def _feed_from_storage_field(self, storage_fields):
        c = self.c
        if not storage_fields:
            return
        hungry_enough = c.hunger < STORAGE_CONSUME_HUNGER_THRESHOLD
        thirsty_enough = c.thirst < STORAGE_CONSUME_THIRST_THRESHOLD
        needs_hp = c.hp < HP_MAX
        if not hungry_enough and not thirsty_enough and not needs_hp:
            return

        fruit_needed = hungry_enough or needs_hp
        water_needed = thirsty_enough

        for field in storage_fields:
            if not fruit_needed and not water_needed:
                break
            if math.hypot(c.x - field.x, c.y - field.y) > STORAGE_FIELD_DEPOSIT_DISTANCE:
                continue
            if not self._is_family_storage(field):
                continue

            if fruit_needed and field.fruits > 0:
                field.fruits -= 1
                c.hp = min(c.hp + FRUIT_HP_BONUS, HP_MAX)
                if hungry_enough:
                    c.hunger = min(c.hunger + FRUIT_HUNGER_BONUS, HUNGER_MAX)
                fruit_needed = False

            if water_needed and field.water > 0:
                field.water -= 1
                c.thirst = min(c.thirst + STORAGE_FIELD_WATER_HYDRATION, THIRST_MAX)
                water_needed = False

    def _is_family_storage(self, field):
        return field.is_owned_by_campfire(self.c.known_campfire)