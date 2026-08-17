"""Физиологическое состояние существа каждый тик."""

from .ci_settings import *
from settings import *

from ...all_needed.navigation import BasePathfinder

# =========================================================================
# Домен: голод / жажда / сон / здоровье / рассудок
# =========================================================================

class CreatureNeeds:
    def __init__(self, creature):
        self.c = creature

    def update(self, dt, other_creatures=None, biome_grid=None):
        c = self.c
        c.memory.maybe_prune(dt)

        biome = biome_grid.get_at(c.x, c.y) if biome_grid is not None else BIOME_PLAINS

        metabolism = self._metabolism_multiplier()
        thirst_metabolism = metabolism * (DESERT_THIRST_DRAIN_MULTIPLIER if biome == BIOME_DESERT else 1.0)

        if c.hp >= HP_MAX:
            hunger_interval = BASE_HUNGER_INTERVAL / metabolism
            thirst_interval = BASE_THIRST_INTERVAL / thirst_metabolism
        else:
            if c.hunger > 10:
                hunger_interval = HEALING_HUNGER_INTERVAL / metabolism
                thirst_interval = HEALING_THIRST_INTERVAL / thirst_metabolism
                c.hp = min(c.hp + 2 * (dt / hunger_interval), HP_MAX)
            else:
                hunger_interval = STARVING_HUNGER_INTERVAL / metabolism
                thirst_interval = STARVING_THIRST_INTERVAL / thirst_metabolism

        c.hunger -= dt / hunger_interval
        c.thirst -= dt / thirst_interval

        if c.hunger <= 0:
            c.hp -= 2 * dt
        if c.thirst <= 0:
            c.hp -= 5 * dt

        c.hunger = max(0, min(c.hunger, HUNGER_MAX))
        c.thirst = max(0, min(c.thirst, THIRST_MAX))
        c.hp = max(0, c.hp)

        self._update_sanity(dt, other_creatures)

        if biome == BIOME_DESERT:
            c.psyche.on_desert_exposure(dt)

        if c.hp <= 0:
            c.die("истощение")
        elif c.consciousness <= 0:
            c.die("помутнение сознания")

        self._update_energy(dt, biome)

    def _metabolism_multiplier(self):
        c = self.c
        mult = METABOLISM_LIFE_STAGE_MULTIPLIER.get(c.life_stage, 1.0)
        mult *= METABOLISM_TEMPERAMENT_MULTIPLIER.get(c.temperament, 1.0)
        mult *= METABOLISM_STATE_MULTIPLIER.get(c.state, 1.0)
        if c.gender == GENDER_FEMALE and c.is_pregnant:
            mult *= PREGNANCY_METABOLISM_MULTIPLIER
        return mult

    def _update_sanity(self, dt, other_creatures=None):
        c = self.c
        if not c.is_talking and not self._has_sanity_support(other_creatures):
            decay_interval = SANITY_DECAY_INTERVAL * (NAMED_SANITY_DECAY_MULTIPLIER if c.player_named else 1.0)
            if c.puberty_active:
                decay_interval /= PUBERTY_SANITY_DECAY_MULTIPLIER
            state_mult = SANITY_STATE_DECAY_MULTIPLIER.get(c.state, 1.0)
            if state_mult > 0:
                decay_interval /= state_mult
            c.sanity_decay_timer -= dt
            while c.sanity_decay_timer <= 0:
                c.consciousness -= 1
                c.sanity_decay_timer += decay_interval
        c.consciousness = max(0, min(c.consciousness, SANITY_MAX))

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
            if c.partner_id is not None and other.id == c.partner_id:
                return True
            if other.parent_ids and c.id in other.parent_ids:
                return True
            if c.social.get_relationship(other) >= CLOSE_FRIEND_SANITY_RELATIONSHIP:
                return True
        return False

    def _update_energy(self, dt, biome=BIOME_PLAINS):
        c = self.c
        if c.is_sleeping:
            restore_rate = (ENERGY_FORCED_SLEEP_RESTORE_RATE if c.sleep_forced
                            else ENERGY_SLEEP_RESTORE_RATE)
            restore_rate *= ENERGY_STATE_MULTIPLIER.get(STATE_SLEEP, 1.0)
            c.energy = min(c.energy + restore_rate * dt, ENERGY_MAX)
        else:
            drain_multiplier = OLD_ENERGY_DRAIN_MULTIPLIER if c.life_stage == LIFE_STAGE_OLD else 1.0
            drain_multiplier *= ENERGY_TEMPERAMENT_MULTIPLIER.get(c.temperament, 1.0)
            drain_multiplier *= ENERGY_STATE_MULTIPLIER.get(c.state, 1.0)
            if c.gender == GENDER_FEMALE and c.is_pregnant:
                drain_multiplier *= PREGNANCY_ENERGY_MULTIPLIER
            if biome == BIOME_DESERT:
                drain_multiplier *= DESERT_ENERGY_DRAIN_MULTIPLIER
            if getattr(c, "at_home", False):
                drain_multiplier *= HOME_ENERGY_DRAIN_MULTIPLIER
            c.energy -= (dt / ENERGY_DRAIN_INTERVAL) * drain_multiplier
            if c.energy <= 0:
                c.energy = 0
                c.is_sleeping = True
                c.sleep_forced = True

    def wellbeing_score(self):
        c = self.c
        base = (c.hp / HP_MAX + c.hunger / HUNGER_MAX +
                c.thirst / THIRST_MAX + c.consciousness / SANITY_MAX) / 4.0
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
        multiplier = PANIC_SPEED_MULTIPLIER if c.panic_active else c.base_speed_multiplier

        if getattr(c, "is_pregnant", False) and not c.panic_active:
            multiplier *= PREGNANCY_SPEED_MULTIPLIER

        psyche = getattr(c, "psyche", None)
        if psyche is not None and not c.panic_active:
            multiplier *= psyche.speed_modifier()

        if biome_grid is not None and biome_grid.get_at(c.x, c.y) == BIOME_RIVER:
            multiplier *= RIVER_SWIM_SPEED_MULTIPLIER

        return SPEED * multiplier