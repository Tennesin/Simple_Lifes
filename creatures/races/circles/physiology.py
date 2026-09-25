"""Физиологическое состояние существа каждый тик."""

import settings

from ...all_needed.navigation import BasePathfinder
from ...all_needed.weak_owner import WeakOwnerMixin
from . import ci_settings

# =========================================================================
# Домен: голод / жажда / сон / здоровье / рассудок
# =========================================================================

class CreatureNeeds(WeakOwnerMixin):
    def __init__(self, creature):
        super().__init__(creature)

    def update(self, dt, other_creatures=None, biome_grid=None):
        c = self.c
        c.memory.maybe_prune(dt)

        biome = biome_grid.get_at(c.x, c.y) if biome_grid is not None else settings.BIOME_PLAINS

        metabolism = self._metabolism_multiplier()
        thirst_metabolism = metabolism * (
            ci_settings.DESERT_THIRST_DRAIN_MULTIPLIER if biome == settings.BIOME_DESERT else 1.0)

        if c.hp >= ci_settings.HP_MAX:
            hunger_interval = ci_settings.BASE_HUNGER_INTERVAL / metabolism
            thirst_interval = ci_settings.BASE_THIRST_INTERVAL / thirst_metabolism
        else:
            if c.hunger > 10:
                hunger_interval = ci_settings.HEALING_HUNGER_INTERVAL / metabolism
                thirst_interval = ci_settings.HEALING_THIRST_INTERVAL / thirst_metabolism
                c.hp = min(c.hp + 2 * (dt / hunger_interval), ci_settings.HP_MAX)
            else:
                hunger_interval = ci_settings.STARVING_HUNGER_INTERVAL / metabolism
                thirst_interval = ci_settings.STARVING_THIRST_INTERVAL / thirst_metabolism

        c.hunger -= dt / hunger_interval
        c.thirst -= dt / thirst_interval

        if c.hunger <= 0:
            c.hp -= ci_settings.STARVE_HP_DRAIN * dt
        if c.thirst <= 0:
            c.hp -= ci_settings.DEHYDRATE_HP_DRAIN * dt

        c.hunger = max(0, min(c.hunger, ci_settings.HUNGER_MAX))
        c.thirst = max(0, min(c.thirst, ci_settings.THIRST_MAX))
        c.hp = max(0, c.hp)

        self._update_sanity(dt, other_creatures)

        if biome == settings.BIOME_DESERT:
            c.psyche.on_desert_exposure(dt)

        if c.hp <= 0:
            c.die(ci_settings.DEATH_CAUSE_STARVATION)
        elif c.consciousness <= 0:
            c.die(ci_settings.DEATH_CAUSE_SANITY)

        self._update_energy(dt, biome)

    def _metabolism_multiplier(self):
        c = self.c
        mult = ci_settings.METABOLISM_LIFE_STAGE_MULTIPLIER.get(c.life_stage, 1.0)
        mult *= ci_settings.METABOLISM_TEMPERAMENT_MULTIPLIER.get(c.temperament, 1.0)
        mult *= ci_settings.METABOLISM_STATE_MULTIPLIER.get(c.state, 1.0)
        if c.gender == ci_settings.GENDER_FEMALE and c.is_pregnant:
            mult *= ci_settings.PREGNANCY_METABOLISM_MULTIPLIER
        return mult

    def _update_sanity(self, dt, other_creatures=None):
        c = self.c
        if not c.is_talking and not self._has_sanity_support(other_creatures):
            decay_interval = ci_settings.SANITY_DECAY_INTERVAL * (
                ci_settings.NAMED_SANITY_DECAY_MULTIPLIER if c.player_named else 1.0)
            if c.puberty.active:
                decay_interval /= ci_settings.PUBERTY_SANITY_DECAY_MULTIPLIER
            state_mult = ci_settings.SANITY_STATE_DECAY_MULTIPLIER.get(c.state, 1.0)
            if state_mult > 0:
                decay_interval /= state_mult
            c.sanity_decay_timer -= dt
            while c.sanity_decay_timer <= 0:
                c.consciousness -= 1
                c.sanity_decay_timer += decay_interval
        c.consciousness = max(0, min(c.consciousness, ci_settings.SANITY_MAX))

    def _has_sanity_support(self, other_creatures):
        c = self.c
        if not other_creatures:
            return False
        vision_radius = c.aging.effective_vision_radius()
        for other in other_creatures:
            if other is c or other.is_dead:
                continue
            if c.distance_to(other) > vision_radius:
                continue
            if c.family.partner_id is not None and other.id == c.family.partner_id:
                return True
            if other.family.parent_ids and c.id in other.family.parent_ids:
                return True
            if c.social.get_relationship(other) >= ci_settings.CLOSE_FRIEND_SANITY_RELATIONSHIP:
                return True
        return False

    def _update_energy(self, dt, biome=settings.BIOME_PLAINS):
        c = self.c
        if c.is_sleeping:
            restore_rate = (ci_settings.ENERGY_FORCED_SLEEP_RESTORE_RATE if c.sleep_forced
                            else ci_settings.ENERGY_SLEEP_RESTORE_RATE)
            restore_rate *= ci_settings.ENERGY_STATE_MULTIPLIER.get(ci_settings.STATE_SLEEP, 1.0)
            c.energy = min(c.energy + restore_rate * dt, ci_settings.ENERGY_MAX)
        else:
            drain_multiplier = (ci_settings.OLD_ENERGY_DRAIN_MULTIPLIER
                                if c.life_stage == ci_settings.LIFE_STAGE_OLD else 1.0)
            drain_multiplier *= ci_settings.ENERGY_TEMPERAMENT_MULTIPLIER.get(c.temperament, 1.0)
            drain_multiplier *= ci_settings.ENERGY_STATE_MULTIPLIER.get(c.state, 1.0)
            if c.gender == ci_settings.GENDER_FEMALE and c.is_pregnant:
                drain_multiplier *= ci_settings.PREGNANCY_ENERGY_MULTIPLIER
            if biome == settings.BIOME_DESERT:
                drain_multiplier *= ci_settings.DESERT_ENERGY_DRAIN_MULTIPLIER
            if c.housing.at_home:
                drain_multiplier *= ci_settings.HOME_ENERGY_DRAIN_MULTIPLIER
            c.energy -= (dt / ci_settings.ENERGY_DRAIN_INTERVAL) * drain_multiplier
            if c.energy <= 0:
                c.energy = 0
                c.is_sleeping = True
                c.sleep_forced = True

    def wellbeing_score(self):
        c = self.c
        base = (c.hp / ci_settings.HP_MAX + c.hunger / ci_settings.HUNGER_MAX +
                c.thirst / ci_settings.THIRST_MAX + c.consciousness / ci_settings.SANITY_MAX) / 4.0
        return max(0.0, min(1.0, base + c.psyche.wellbeing_modifier()))

    def tick_corpse(self, dt):
        c = self.c
        c.death_timer -= dt
        return c.death_timer <= 0

# =========================================================================
# Домен: скорость передвижения (паника/беременность/психика/река)
# =========================================================================

class CirclePathfinder(BasePathfinder):

    def compute_speed(self, dt, biome_grid=None):
        c = self.c
        multiplier = ci_settings.PANIC_SPEED_MULTIPLIER if c.panic_active else c.base_speed_multiplier

        if getattr(c, "is_pregnant", False) and not c.panic_active:
            multiplier *= ci_settings.PREGNANCY_SPEED_MULTIPLIER

        psyche = getattr(c, "psyche", None)
        if psyche is not None and not c.panic_active:
            multiplier *= psyche.speed_modifier()

        if biome_grid is not None and biome_grid.get_at(c.x, c.y) == settings.BIOME_RIVER:
            multiplier *= ci_settings.RIVER_SWIM_SPEED_MULTIPLIER

        return ci_settings.SPEED * multiplier