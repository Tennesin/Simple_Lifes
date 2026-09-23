import math
import random

import settings

from ...all_needed import geometry
from ...all_needed.weak_owner import WeakOwnerMixin
from . import ci_info, ci_settings


class CreatureInteractions(WeakOwnerMixin):

    def __init__(self, creature):
        super().__init__(creature)

    def process(self, fruits, spikes, water_puddles, bushes, campfires, other_creatures,
                storage_fields, dt, walls=None, biome_grid=None):
        self._eat_fruits(fruits, other_creatures)
        self._drink_water(water_puddles, dt, other_creatures, biome_grid=biome_grid, campfires=campfires)
        self._feed_from_storage_field(storage_fields, other_creatures)
        self._hit_spikes(spikes, other_creatures, walls, biome_grid=biome_grid)
        self._push_out_of_bushes(bushes, biome_grid=biome_grid)
        self._linger_near_bush(bushes, dt, campfires=campfires)
        self._warm_by_campfires(campfires, dt)
        self._talk_to_companions(other_creatures, dt)
        self._receive_elder_support(other_creatures, dt)
        self._check_jealousy(other_creatures, dt)

    def _child_must_wait_for_parent(self, other_creatures):
        c = self.c
        return c.life_stage == ci_settings.LIFE_STAGE_CHILD and c.family.has_living_parent(other_creatures)

    def _eat_fruits(self, fruits, other_creatures):
        c = self.c
        if not c.eats_food_type("fruit"):
            return
        if self._child_must_wait_for_parent(other_creatures):
            return
        if c.hunger >= ci_settings.HUNGER_SATISFY_THRESHOLD and c.hp >= ci_settings.HP_MAX:
            return
        for fruit in fruits:
            if fruit.active and c.distance_to(fruit) < ci_settings.EAT_DISTANCE:
                self._register_resource_rivals(fruit, other_creatures, need_attr="hunger")
                fruit.active = False
                c.hp = min(c.hp + ci_settings.FRUIT_HP_BONUS, ci_settings.HP_MAX)
                c.hunger = min(c.hunger + ci_settings.FRUIT_HUNGER_BONUS, ci_settings.HUNGER_MAX)
                c.memory.add_memory("fruit", fruit.x, fruit.y, importance=2.0)
                c.knowledge["fruit"] = True

    def _register_resource_rivals(self, obj, other_creatures, need_attr):
        c = self.c
        for other in other_creatures:
            if other is c or other.is_dead:
                continue
            if getattr(other, need_attr) >= ci_settings.RESOURCE_STEAL_MIN_HUNGER_URGENCY:
                continue  # рыл не был голоден - ему всё равно
            if math.hypot(other.x - obj.x, other.y - obj.y) > ci_settings.RESOURCE_COMPETE_RADIUS:
                continue
            # он тоже спешил сюда и явно голодал - обидится
            other.social.adjust_relationship(c, ci_settings.RESOURCE_STEAL_PENALTY)

    def _drink_water(self, water_puddles, dt, other_creatures, biome_grid=None, campfires=None):
        c = self.c
        if self._child_must_wait_for_parent(other_creatures):
            return
        if c.thirst >= ci_settings.THIRST_SATISFY_THRESHOLD:
            return
        for water in water_puddles:
            if not water.has_water():
                continue
            if c.distance_to(water) < ci_settings.EAT_DISTANCE + water.radius:
                self._register_resource_rivals(water, other_creatures, need_attr="thirst")
                deficit_ratio = max(ci_settings.WATER_DRINK_DEFICIT_FLOOR,
                                    (ci_settings.THIRST_MAX - c.thirst) / ci_settings.THIRST_MAX)
                wanted = min(ci_settings.WATER_DRINK_RATE * deficit_ratio * dt,
                             ci_settings.THIRST_MAX - c.thirst)
                actual_gain = water.consume(wanted)
                c.thirst = min(c.thirst + actual_gain, ci_settings.THIRST_MAX)
                c.memory.add_memory("water", water.x, water.y, importance=1.5)
                c.knowledge["water"] = True
                c.territory.register_use(water, "water", dt, campfires=campfires)

        if biome_grid is not None and biome_grid.get_at(c.x, c.y) == settings.BIOME_RIVER:
            deficit_ratio = max(ci_settings.WATER_DRINK_DEFICIT_FLOOR,
                                (ci_settings.THIRST_MAX - c.thirst) / ci_settings.THIRST_MAX)
            c.thirst = min(c.thirst + ci_settings.WATER_DRINK_RATE * deficit_ratio * dt,
                           ci_settings.THIRST_MAX)
            c.knowledge["water"] = True

    def _check_jealousy(self, other_creatures, dt):
        c = self.c
        if c.partner_id is None:
            return
        partner = next((o for o in other_creatures if o.id == c.partner_id and not o.is_dead), None)
        if partner is None:
            return
        if c.distance_to(partner) > ci_settings.JEALOUSY_CHECK_DISTANCE:
            return
        for other in other_creatures:
            if other in (c, partner) or other.is_dead:
                continue
            if ci_settings.JEALOUSY_OPPOSITE_GENDER_ONLY and other.gender == partner.gender:
                continue
            if (partner.distance_to(other) < ci_settings.TALK_DISTANCE
                    and c.distance_to(other) > ci_settings.TALK_DISTANCE):
                if random.random() < ci_settings.JEALOUSY_CHANCE_PER_SEC * c.psyche.jealousy_modifier() * dt:
                    c.social.adjust_relationship(partner, ci_settings.JEALOUSY_PENALTY_PARTNER)
                    c.social.adjust_relationship(other, ci_settings.JEALOUSY_PENALTY_RIVAL)

    def _hit_spikes(self, spikes, other_creatures, walls=None, biome_grid=None):
        c = self.c
        if c.spike_invuln_timer > 0:
            return
        wall_polylines = [w.points for w in walls if w.points] if walls else []
        for spike in spikes:
            if c.distance_to(spike) < ci_settings.EAT_DISTANCE:
                c.hp -= ci_settings.SPIKE_DAMAGE
                c.spike_invuln_timer = ci_settings.SPIKE_INVULN_DURATION
                dx = c.x - spike.x
                dy = c.y - spike.y
                dist = math.hypot(dx, dy)
                if dist != 0:
                    new_x = c.x + dx / dist * settings.SPIKE_KNOCKBACK_DISTANCE
                    new_y = c.y + dy / dist * settings.SPIKE_KNOCKBACK_DISTANCE
                    blocked_by_wall = wall_polylines and geometry.segment_blocked_by_polylines(
                        c.x, c.y, new_x, new_y, wall_polylines)
                    blocked_by_sea = (biome_grid is not None
                                      and biome_grid.get_at(new_x, new_y) == settings.BIOME_SEA)
                    if not blocked_by_wall and not blocked_by_sea:
                        c.x = new_x
                        c.y = new_y
                c.x = max(15, min(c.x, settings.WORLD_WIDTH - 15))
                c.y = max(15, min(c.y, settings.WORLD_HEIGHT - 15))
                c.memory.add_memory("spike", spike.x, spike.y, importance=-2.0)
                c.knowledge["spike"] = True
                c.psyche.on_hazard_encountered()
                c.pathfinder.reset_navigation()

                if c.following_road is not None:
                    c.known_roads[c.following_road.id] = "dangerous"
                    c.following_road.rating = "dangerous"
                    c.following_road = None
                    c.following_road_active = False
                    c.road_progress = 0
                    c.road_entry_reached = False
                    c.goal_text = ci_info.INFO_CREATURE_GOAL_ROAD_DEADLY

                if c.child_road_play.road is not None:
                    self._mark_child_road_dangerous(c.child_road_play.road, other_creatures)

                break

    def _mark_child_road_dangerous(self, road, other_creatures):
        c = self.c
        road.rating = "dangerous"

        c.child_road_play.stop_playing()
        c.following_road_active = False
        c.fear_timer = max(c.fear_timer, ci_settings.CHILD_ROAD_DANGER_FEAR_DURATION)
        c.fear_source = (c.x, c.y)
        c.goal_text = ci_info.INFO_CREATURE_GOAL_CHILD_ROAD_DANGER

        for other in other_creatures:
            if other is c or other.is_dead:
                continue
            if other.child_road_play.road is road:
                other.child_road_play.stop_playing()
                other.following_road_active = False
                other.fear_timer = max(other.fear_timer, ci_settings.CHILD_ROAD_DANGER_FEAR_DURATION)
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
                    if biome_grid is not None and biome_grid.get_at(new_x, new_y) == settings.BIOME_SEA:
                        continue
                    c.x = new_x
                    c.y = new_y
                    c.x = max(15, min(c.x, settings.WORLD_WIDTH - 15))
                    c.y = max(15, min(c.y, settings.WORLD_HEIGHT - 15))

    def _linger_near_bush(self, bushes, dt, campfires=None):
        c = self.c
        for bush in bushes:
            if c.distance_to(bush) < ci_settings.TERRITORY_BUSH_CLAIM_RADIUS:
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
            rate = ci_settings.SANITY_CAMPFIRE_RESTORE_RATE_FAR + (
                    ci_settings.SANITY_CAMPFIRE_RESTORE_RATE_NEAR
                    - ci_settings.SANITY_CAMPFIRE_RESTORE_RATE_FAR) * best_ratio
            c.consciousness = min(c.consciousness + rate * dt, ci_settings.SANITY_MAX)
            c.knowledge["campfire"] = True

    def _talk_to_companions(self, other_creatures, dt):
        c = self.c
        c.is_talking = False
        c.share_info_timer -= dt
        for other in other_creatures:
            if other is c or other.is_dead:
                continue
            if c.distance_to(other) < ci_settings.TALK_DISTANCE:
                c.is_talking = True
                gender_bonus = ci_settings.GENDER_OPPOSITE_TALK_BONUS if c.gender != other.gender else 1.0
                rate = ci_settings.SANITY_TALK_RATE.get(other.temperament, 0.2) * gender_bonus
                c.consciousness = min(c.consciousness + rate * dt, ci_settings.SANITY_MAX)

                talk_mult = ci_settings.PUBERTY_TALK_RATE_MULTIPLIER if c.puberty.active else 1.0
                c.social.adjust_relationship(
                    other, ci_settings.RELATIONSHIP_TALK_RATE * gender_bonus * talk_mult * dt)

                rel = c.social.get_relationship(other)
                c.psyche.on_talk(dt, rel, gender_bonus)

                if rel < ci_settings.QUARREL_THRESHOLD:
                    quarrel_chance = ci_settings.QUARREL_CHANCE_PER_SEC * c.psyche.quarrel_modifier()
                    if c.puberty.active:
                        quarrel_chance *= ci_settings.PUBERTY_QUARREL_CHANCE_MULTIPLIER
                    if random.random() < quarrel_chance * dt:
                        c.social.adjust_mutual_relationship(other, ci_settings.QUARREL_PENALTY)
                        c.psyche.on_quarrel()
                        other.psyche.on_quarrel()

                if c.share_info_timer <= 0:
                    c.communication.share_information(other)
                    c.share_info_timer = random.uniform(*ci_settings.SHARE_INFO_INTERVAL)

    def _receive_elder_support(self, other_creatures, dt):
        c = self.c
        if c.life_stage == ci_settings.LIFE_STAGE_OLD:
            return
        best_ratio = None
        for other in other_creatures:
            if other is c or other.is_dead or other.life_stage != ci_settings.LIFE_STAGE_OLD:
                continue
            d = c.distance_to(other)
            if d < ci_settings.OLD_SANITY_AURA_RADIUS:
                ratio = 1.0 - (d / ci_settings.OLD_SANITY_AURA_RADIUS)
                if best_ratio is None or ratio > best_ratio:
                    best_ratio = ratio
        if best_ratio is not None:
            rate = ci_settings.OLD_SANITY_AURA_RATE_FAR + (
                    ci_settings.OLD_SANITY_AURA_RATE_NEAR - ci_settings.OLD_SANITY_AURA_RATE_FAR) * best_ratio
            c.consciousness = min(c.consciousness + rate * dt, ci_settings.SANITY_MAX)

    def _feed_from_storage_field(self, storage_fields, other_creatures):
        c = self.c
        if not storage_fields:
            return

        hungry_enough = c.hunger < ci_settings.STORAGE_CONSUME_HUNGER_THRESHOLD
        thirsty_enough = c.thirst < ci_settings.STORAGE_CONSUME_THIRST_THRESHOLD
        needs_hp = c.hp < ci_settings.HP_MAX
        emergency_hunger = c.hunger < ci_settings.STORAGE_EMERGENCY_HUNGER_THRESHOLD
        emergency_thirst = c.thirst < ci_settings.STORAGE_EMERGENCY_THIRST_THRESHOLD

        fruit_needed = hungry_enough or needs_hp or emergency_hunger
        water_needed = thirsty_enough or emergency_thirst
        if not fruit_needed and not water_needed:
            return

        for field in storage_fields:
            if not fruit_needed and not water_needed:
                break
            if math.hypot(c.x - field.x, c.y - field.y) > ci_settings.STORAGE_FIELD_DEPOSIT_DISTANCE:
                continue

            has_family_access = field.grants_full_access(c, other_creatures)
            # ---------- Чужаку склад доступен только на грани голодной/жаждущей смерти - и это кража ----------
            is_theft_attempt = not has_family_access and (emergency_hunger or emergency_thirst)
            if not has_family_access and not is_theft_attempt:
                continue

            took_something = False

            if fruit_needed and field.fruits > 0 and (has_family_access or emergency_hunger):
                field.fruits -= 1
                c.hp = min(c.hp + ci_settings.FRUIT_HP_BONUS, ci_settings.HP_MAX)
                if hungry_enough or emergency_hunger:
                    c.hunger = min(c.hunger + ci_settings.FRUIT_HUNGER_BONUS, ci_settings.HUNGER_MAX)
                fruit_needed = False
                took_something = True

            if water_needed and field.water > 0 and (has_family_access or emergency_thirst):
                field.water -= 1
                c.thirst = min(c.thirst + ci_settings.STORAGE_FIELD_WATER_HYDRATION, ci_settings.THIRST_MAX)
                water_needed = False
                took_something = True

            if took_something and is_theft_attempt:
                field.punish_theft(c, other_creatures)