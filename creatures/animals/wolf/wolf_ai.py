"""ИИ волка: бродит, пьёт воду, при голоде охотится на скот, кусает, после смерти жертвы поедает мясо."""

import math
from ...all_needed.ai.roaming_ai import RoamingAnimalMixin
import settings
from .wolf_settings import *

_WOLF_AI_CFG = {
    "speed": WOLF_SPEED,
    "hunger_drain_interval": WOLF_HUNGER_DRAIN_INTERVAL,
    "thirst_drain_interval": WOLF_THIRST_DRAIN_INTERVAL,
    "energy_drain_interval_hunt": WOLF_ENERGY_DRAIN_INTERVAL_HUNT,
    "energy_regen_interval": WOLF_ENERGY_REGEN_INTERVAL,
    "starve_hp_drain": WOLF_STARVE_HP_DRAIN,
    "dehydrate_hp_drain": WOLF_DEHYDRATE_HP_DRAIN,
    "wander_distance": WOLF_WANDER_DISTANCE,
    "wander_timer": WOLF_WANDER_TIMER,
    "drink_distance": WOLF_DRINK_DISTANCE,
    "drink_rate": WOLF_DRINK_RATE,
    "thirst_seek_ratio": WOLF_THIRST_SEEK_RATIO,
    "hunt_hunger_ratio": WOLF_HUNT_HUNGER_RATIO,
    "hunger_satisfy_ratio": WOLF_HUNGER_SATISFY_RATIO,
    "thirst_satisfy_ratio": WOLF_THIRST_SATISFY_RATIO,
    "bite_distance": WOLF_BITE_DISTANCE,
    "bite_damage": WOLF_BITE_DAMAGE,
    "bite_cooldown": WOLF_BITE_COOLDOWN,
    "eat_distance": WOLF_EAT_DISTANCE,
    "eat_rate": WOLF_EAT_RATE,
    "hunt_max_duration": WOLF_HUNT_MAX_DURATION,
    "hunt_giveup_distance": WOLF_HUNT_GIVEUP_DISTANCE,
}

class WolfAI(RoamingAnimalMixin):

    def __init__(self, wolf, cfg):
        self.entity = wolf
        self.cfg = cfg
        self.target = None
        self.decision_timer = 0.0
        self.hunting_target_id = None
        self.hunt_timer = 0.0
        self.bite_cooldown = 0.0
        self.seeking_food = False
        self.seeking_water = False

    # ---------- Потребности ----------

    def update_needs(self, dt):
        w, cfg = self.entity, self.cfg
        self._tick_spike_invuln(dt)
        if w.hp <= 0:
            return
        w.hunger = max(0.0, w.hunger - dt / cfg["hunger_drain_interval"])
        w.thirst = max(0.0, w.thirst - dt / cfg["thirst_drain_interval"])
        if self.hunting_target_id is not None:
            w.energy = max(0.0, w.energy - dt / cfg["energy_drain_interval_hunt"])
        else:
            w.energy = min(w.energy_max, w.energy + dt / cfg["energy_regen_interval"])

        if w.hunger <= 0:
            w.hp -= cfg["starve_hp_drain"] * dt
        if w.thirst <= 0:
            w.hp -= cfg["dehydrate_hp_drain"] * dt
        w.hp = max(0.0, w.hp)

        if self.bite_cooldown > 0:
            self.bite_cooldown -= dt

    # ---------- Решение ----------

    def decide(self, dt, prey_lists, water_puddles, meats, biome_grid, spikes=None):
        w, cfg = self.entity, self.cfg

        if self.hunting_target_id is None:
            nearest_spike = self._nearest_spike(spikes, settings.ANIMAL_SPIKE_FEAR_RADIUS)
            if nearest_spike is not None:
                return self._flee_from_spike(nearest_spike, biome_grid)

        self._update_seek_state(cfg["hunt_hunger_ratio"], cfg["hunger_satisfy_ratio"],
                                cfg["thirst_seek_ratio"], cfg["thirst_satisfy_ratio"])

        if self.seeking_food or self.hunting_target_id is not None:
            if self.hunting_target_id is None:
                meat = self._nearest_within(meats, w.vision_radius, predicate=lambda m: m.has_food())
                if meat is not None:
                    return (meat.x, meat.y)

            prey = self._resolve_hunt_target(prey_lists, w.vision_radius, dt)
            if prey is not None:
                self.hunting_target_id = prey.id
                return (prey.x, prey.y)
            self.hunting_target_id = None

            if self.seeking_food:
                meat = self._nearest_within(meats, w.vision_radius, predicate=lambda m: m.has_food())
                if meat is not None:
                    return (meat.x, meat.y)

        if self.seeking_water:
            water_target = self._nearest_water_target(water_puddles, biome_grid, w.vision_radius)
            if water_target is not None:
                return water_target

        return self._wander(dt, biome_grid)

    def _resolve_hunt_target(self, prey_lists, radius, dt=0.0):
        w, cfg = self.entity, self.cfg

        if self.hunting_target_id is not None:
            current = self._find_prey_by_id(prey_lists, self.hunting_target_id)

            if current is not None and current.hp > 0:
                self.hunt_timer += dt
                dist = math.hypot(w.x - current.x, w.y - current.y)
                too_long = self.hunt_timer > cfg["hunt_max_duration"]
                too_far = dist > cfg["hunt_giveup_distance"]
                if not too_long and not too_far:
                    return current
                # ---------- Погоня слишком долгая или жертва слишком далеко оторвалась - бросаем ----------

            self.hunting_target_id = None
            self.hunt_timer = 0.0

        best, best_dist = None, radius
        for prey_list in prey_lists:
            for prey in prey_list:
                if prey.hp <= 0:
                    continue
                d = math.hypot(w.x - prey.x, w.y - prey.y)
                if d < best_dist:
                    best_dist = d
                    best = prey

        if best is not None:
            self.hunt_timer = 0.0

        return best

    @staticmethod
    def _find_prey_by_id(prey_lists, target_id):
        for prey_list in prey_lists:
            for prey in prey_list:
                if prey.id == target_id:
                    return prey
        return None

    # ---------- Действия вблизи ----------

    def interact(self, dt, prey_lists, water_puddles, meats, biome_grid, spikes=None):
        w, cfg = self.entity, self.cfg
        if w.hp <= 0:
            return

        self._apply_spike_damage(spikes, biome_grid=biome_grid)
        if w.hp <= 0:
            return

        bit = False
        if self.hunting_target_id is not None and self.bite_cooldown <= 0:
            for prey_list in prey_lists:
                for prey in prey_list:
                    if prey.id == self.hunting_target_id and prey.hp > 0:
                        if math.hypot(w.x - prey.x, w.y - prey.y) < cfg["bite_distance"]:
                            prey.hp = max(0.0, prey.hp - cfg["bite_damage"])
                            self.bite_cooldown = cfg["bite_cooldown"]
                            bit = True
                        break

        if bit:
            self.hunt_timer = 0.0

        if not bit and self.hunting_target_id is None and self.seeking_food:
            meat = self._nearest_within(meats, cfg["eat_distance"], predicate=lambda m: m.has_food())
            if meat is not None:
                amount = min(cfg["eat_rate"] * dt, meat.food, w.hunger_max - w.hunger)
                if amount > 0:
                    meat.food -= amount
                    w.hunger = min(w.hunger_max, w.hunger + amount)

        if self.seeking_water:
            water = self._nearest_within(water_puddles, cfg["drink_distance"], predicate=lambda p: p.has_water())
            if water is not None:
                wanted = min(cfg["drink_rate"] * dt, w.thirst_max - w.thirst)
                gained = water.consume(wanted)
                w.thirst = min(w.thirst_max, w.thirst + gained)
            elif biome_grid is not None and biome_grid.get_at(w.x, w.y) == settings.BIOME_RIVER:
                w.thirst = min(w.thirst_max, w.thirst + cfg["drink_rate"] * dt)

def _get_ai(wolf):
    ai = getattr(wolf, "_wolf_ai", None)
    if ai is None:
        ai = WolfAI(wolf, _WOLF_AI_CFG)
        wolf._wolf_ai = ai
    return ai

def tick_wolf(game, dt, nav_grid=None, fallback_nav_grid=None):
    world = game.world
    biome_grid = game.biome_manager.grid
    prey_lists = [world.cow, world.sheep]
    wall_polylines, fence_polylines = game.welded_landscape_polylines()

    dead = [w for w in world.wolves if w.hp <= 0]
    for wolf in dead:
        game.object_manager.remove_animal_and_drop(wolf)

    for wolf in world.wolves:
        if wolf.hp <= 0:
            continue
        ai = _get_ai(wolf)
        ai.update_needs(dt)
        if wolf.hp <= 0:
            continue
        if wolf is not game.player.grabbed_object:
            target = ai.decide(dt, prey_lists, world.water_puddles, world.meats, biome_grid,
                               spikes=world.spikes)
            chase_mult = WOLF_CHASE_SPEED_MULTIPLIER if ai.hunting_target_id is not None else 1.0
            ai.move_towards(target, dt, biome_grid=biome_grid, nav_grid=nav_grid,
                            fallback_nav_grid=fallback_nav_grid,
                            speed_multiplier=chase_mult,
                            wall_polylines=wall_polylines, fence_polylines=fence_polylines)
        ai.interact(dt, prey_lists, world.water_puddles, world.meats, biome_grid, spikes=world.spikes)