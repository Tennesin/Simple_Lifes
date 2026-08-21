"""Универсальный ИИ травоядных: взвешенная система принятия решений
(Consideration + pick_best, по образцу расы 'Круг') - бродит, ест траву,
пьёт воду, убегает от волков и от шипов."""

from .roaming_ai import RoamingAnimalMixin
from .utility import Consideration, pick_best, scale
import settings

# ---------- Веса принятия решений ----------
SCORE_FLEE_PREDATOR_BASE = 95.0
SCORE_FLEE_PREDATOR_MAX_BONUS = 5.0
SCORE_FLEE_SPIKE = 88.0
SCORE_FOOD_BASE = 40.0
SCORE_FOOD_MAX_BONUS = 30.0
SCORE_WATER_BASE = 40.0
SCORE_WATER_MAX_BONUS = 30.0
SCORE_WANDER = 8.0

class GrazerAI(RoamingAnimalMixin):

    def __init__(self, animal, cfg):
        self.entity = animal
        self.cfg = cfg
        self.target = None
        self.decision_timer = 0.0
        self.fleeing = False
        self.seeking_food = False
        self.seeking_water = False
        self.is_urgent = False  # НОВОЕ (п.3): включает "прокачанный" A* в move_towards

        # ---------- НОВОЕ (п.2): гистерезис страха перед шипом ----------
        self._spike_flee_commit_timer = 0.0
        self._last_spike_threat = None

    # ---------- Потребности ----------

    def update_needs(self, dt):
        a, cfg = self.entity, self.cfg
        self._tick_spike_invuln(dt)
        if a.hp <= 0:
            return
        a.hunger = max(0.0, a.hunger - dt / cfg["hunger_drain_interval"])
        a.thirst = max(0.0, a.thirst - dt / cfg["thirst_drain_interval"])
        if self.fleeing:
            a.energy = max(0.0, a.energy - dt / cfg["energy_drain_interval_flee"])
        else:
            a.energy = min(a.energy_max, a.energy + dt / cfg["energy_regen_interval"])

        if a.hunger <= 0:
            a.hp -= cfg["starve_hp_drain"] * dt
        if a.thirst <= 0:
            a.hp -= cfg["dehydrate_hp_drain"] * dt
        a.hp = max(0.0, a.hp)

    # =====================================================================
    # Домен: побег от хищника - высший приоритет, оценка растёт с близостью волка
    # =====================================================================

    def _consider_flee_predator(self, dt, wolves, biome_grid):
        a, cfg = self.entity, self.cfg
        nearest_wolf = self._nearest_within(wolves, a.vision_radius)
        if nearest_wolf is None:
            return None
        dist = a.distance_to(nearest_wolf)
        urgency = scale(a.vision_radius - dist, 0, a.vision_radius)
        score = SCORE_FLEE_PREDATOR_BASE + urgency * SCORE_FLEE_PREDATOR_MAX_BONUS

        def execute():
            self.fleeing = True
            return self.flee_from((nearest_wolf.x, nearest_wolf.y), cfg["flee_run_distance"], dt,
                                  biome_grid=biome_grid)

        return Consideration("flee_predator", score, execute)

    # =====================================================================
    # Домен (п.2): побег от шипов - с гистерезисом, чтобы решение "бегу" не
    # переигрывалось каждый тик, из-за чего животное раньше тряслось на месте
    # вместо спокойного обхода шипа через A* по пути к цели.
    # =====================================================================

    def _consider_flee_spike(self, dt, spikes, biome_grid):
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
            self.fleeing = True
            return self.flee_from(threat, settings.ANIMAL_SPIKE_FLEE_DISTANCE, dt, biome_grid=biome_grid)

        return Consideration("flee_spike", SCORE_FLEE_SPIKE, execute)

    # =====================================================================
    # Домен: голод / жажда
    # =====================================================================

    def _consider_food(self, grass_list):
        a, cfg = self.entity, self.cfg
        if not self.seeking_food:
            return None
        deficit = scale(a.hunger_max * cfg["hunger_seek_ratio"] - a.hunger, 0, a.hunger_max)
        score = SCORE_FOOD_BASE + deficit * SCORE_FOOD_MAX_BONUS

        def execute():
            grass = self._nearest_within(grass_list, a.vision_radius, predicate=lambda g: g.has_food())
            return (grass.x, grass.y) if grass is not None else None

        return Consideration("food", score, execute)

    def _consider_water(self, water_puddles, biome_grid):
        a, cfg = self.entity, self.cfg
        if not self.seeking_water:
            return None
        deficit = scale(a.thirst_max * cfg["thirst_seek_ratio"] - a.thirst, 0, a.thirst_max)
        score = SCORE_WATER_BASE + deficit * SCORE_WATER_MAX_BONUS

        def execute():
            return self._nearest_water_target(water_puddles, biome_grid, a.vision_radius)

        return Consideration("water", score, execute)

    # =====================================================================
    # Домен: бесцельное бродяжничество - запасной вариант, доступен всегда
    # =====================================================================

    def _consider_wander(self, dt, biome_grid):
        def execute():
            return self._wander(dt, biome_grid)

        return Consideration("wander", SCORE_WANDER, execute)

    # =====================================================================
    # Итог: взвешенное решение (п.1)
    # =====================================================================

    def decide(self, dt, grass_list, water_puddles, wolves, biome_grid, spikes=None):
        cfg = self.cfg
        self.fleeing = False
        self._update_seek_state(cfg["hunger_seek_ratio"], cfg["hunger_satisfy_ratio"],
                                cfg["thirst_seek_ratio"], cfg["thirst_satisfy_ratio"])

        considerations = [
            self._consider_flee_predator(dt, wolves, biome_grid),
            self._consider_flee_spike(dt, spikes, biome_grid),
            self._consider_food(grass_list),
            self._consider_water(water_puddles, biome_grid),
            self._consider_wander(dt, biome_grid),
        ]
        goal = pick_best(considerations)

        # ---------- НОВОЕ (п.3): "вопрос выживания" - включаем усиленный A* ----------
        self.is_urgent = self.seeking_food or self.seeking_water or self.fleeing

        return goal if goal is not None else self._wander(dt, biome_grid)

    # ---------- Действия вблизи (не связаны с выбором цели) ----------

    def interact(self, dt, grass_list, water_puddles, biome_grid, spikes=None):
        a, cfg = self.entity, self.cfg
        if a.hp <= 0:
            return

        self._apply_spike_damage(spikes, biome_grid=biome_grid)
        if a.hp <= 0:
            return

        if self.seeking_food:
            grass = self._nearest_within(grass_list, cfg["graze_distance"], predicate=lambda g: g.has_food())
            if grass is not None:
                amount = min(cfg["graze_rate"] * dt, grass.food, a.hunger_max - a.hunger)
                if amount > 0:
                    grass.food -= amount
                    a.hunger = min(a.hunger_max, a.hunger + amount)

        if self.seeking_water:
            water = self._nearest_within(water_puddles, cfg["drink_distance"], predicate=lambda w: w.has_water())
            if water is not None:
                wanted = min(cfg["drink_rate"] * dt, a.thirst_max - a.thirst)
                gained = water.consume(wanted)
                a.thirst = min(a.thirst_max, a.thirst + gained)
            elif biome_grid is not None and biome_grid.get_at(a.x, a.y) == settings.BIOME_RIVER:
                a.thirst = min(a.thirst_max, a.thirst + cfg["drink_rate"] * dt)