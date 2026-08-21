"""ИИ волка: взвешенная система принятия решений (Consideration + pick_best,
по образцу расы 'Круг') - бродит, пьёт воду, при голоде охотится на скот
или ест мясо."""

import math
from ...all_needed.ai.roaming_ai import RoamingAnimalMixin
from ...all_needed.ai.utility import Consideration, pick_best, scale
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

# ---------- Веса принятия решений ----------
SCORE_FLEE_SPIKE = 88.0
SCORE_EAT_MEAT = 78.0
SCORE_HUNT_COMMITTED = 72.0
SCORE_HUNT_NEW = 65.0
SCORE_WATER_BASE = 40.0
SCORE_WATER_MAX_BONUS = 30.0
SCORE_WANDER = 8.0

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
        self.is_urgent = False  # НОВОЕ (п.3): включает "прокачанный" A* в move_towards

        # ---------- НОВОЕ (п.2): тот же гистерезис страха перед шипом, что у травоядных ----------
        self._spike_flee_commit_timer = 0.0
        self._last_spike_threat = None

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

    # =====================================================================
    # Домен (п.2): побег от шипов. Во время реальной погони волк шипы
    # игнорирует - как и раньше (решение оставлено прежним).
    # =====================================================================

    def _consider_flee_spike(self, dt, spikes, biome_grid):
        if self.hunting_target_id is not None:
            self._spike_flee_commit_timer = 0.0
            return None

        nearest_spike = self._nearest_spike(spikes, settings.ANIMAL_SPIKE_FEAR_RADIUS)
        commit_active = self._spike_flee_commit_timer > 0

        if nearest_spike is None and not commit_active:
            return None

        if nearest_spike is not None:
            self._spike_flee_commit_timer = settings.ANIMAL_SPIKE_FLEE_COMMIT_TIME
            threat = (nearest_spike.x, nearest_spike.y)
        else:
            self._spike_flee_commit_timer -= dt
            threat = self._last_spike_threat

        if threat is None:
            return None
        self._last_spike_threat = threat

        def execute():
            return self.flee_from(threat, settings.ANIMAL_SPIKE_FLEE_DISTANCE, dt, biome_grid=biome_grid)

        return Consideration("flee_spike", SCORE_FLEE_SPIKE, execute)

    # =====================================================================
    # Домен: падаль - приоритет выше поиска новой жертвы, но ниже уже идущей погони
    # =====================================================================

    def _consider_eat_meat(self, meats):
        w = self.entity
        if self.hunting_target_id is not None:
            return None
        if not self.seeking_food:
            return None
        meat = self._nearest_within(meats, w.vision_radius, predicate=lambda m: m.has_food())
        if meat is None:
            return None

        def execute():
            return (meat.x, meat.y)

        return Consideration("eat_meat", SCORE_EAT_MEAT, execute)

    # =====================================================================
    # Домен: охота на скот
    # =====================================================================

    def _consider_hunt(self, dt, prey_lists):
        if not (self.seeking_food or self.hunting_target_id is not None):
            return None
        score = SCORE_HUNT_COMMITTED if self.hunting_target_id is not None else SCORE_HUNT_NEW
        w = self.entity

        def execute():
            prey = self._resolve_hunt_target(prey_lists, w.vision_radius, dt)
            if prey is None:
                self.hunting_target_id = None
                return None
            self.hunting_target_id = prey.id
            return (prey.x, prey.y)

        return Consideration("hunt", score, execute)

    # =====================================================================
    # Домен: жажда
    # =====================================================================

    def _consider_water(self, water_puddles, biome_grid):
        w, cfg = self.entity, self.cfg
        if not self.seeking_water:
            return None
        deficit = scale(w.thirst_max * cfg["thirst_seek_ratio"] - w.thirst, 0, w.thirst_max)
        score = SCORE_WATER_BASE + deficit * SCORE_WATER_MAX_BONUS

        def execute():
            return self._nearest_water_target(water_puddles, biome_grid, w.vision_radius)

        return Consideration("water", score, execute)

    # =====================================================================
    # Домен: бродяжничество
    # =====================================================================

    def _consider_wander(self, dt, biome_grid):
        def execute():
            return self._wander(dt, biome_grid)

        return Consideration("wander", SCORE_WANDER, execute)

    # =====================================================================
    # Итог: взвешенное решение (п.1)
    # =====================================================================

    def decide(self, dt, prey_lists, water_puddles, meats, biome_grid, spikes=None):
        cfg = self.cfg
        self._update_seek_state(cfg["hunt_hunger_ratio"], cfg["hunger_satisfy_ratio"],
                                cfg["thirst_seek_ratio"], cfg["thirst_satisfy_ratio"])

        considerations = [
            self._consider_flee_spike(dt, spikes, biome_grid),
            self._consider_eat_meat(meats),
            self._consider_hunt(dt, prey_lists),
            self._consider_water(water_puddles, biome_grid),
            self._consider_wander(dt, biome_grid),
        ]
        goal = pick_best(considerations)

        # ---------- НОВОЕ (п.3): "вопрос выживания" - включаем усиленный A* ----------
        self.is_urgent = self.seeking_food or self.hunting_target_id is not None or self.seeking_water

        return goal if goal is not None else self._wander(dt, biome_grid)

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

    # ---------- НОВОЕ: утопление в море + перенос будущего дропа на ближайшую сушу ----------
    if biome_grid is not None:
        max_search = max(game.camera.world_w, game.camera.world_h)
        for wolf in world.wolves:
            if wolf.hp > 0 and biome_grid.get_at(wolf.x, wolf.y) == settings.BIOME_SEA:
                land = biome_grid.find_nearest_land(wolf.x, wolf.y, max_search)
                if land is not None:
                    wolf.x, wolf.y = land
                wolf.hp = 0

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
                            wall_polylines=wall_polylines, fence_polylines=fence_polylines,
                            urgent=ai.is_urgent)
        ai.interact(dt, prey_lists, world.water_puddles, world.meats, biome_grid, spikes=world.spikes)