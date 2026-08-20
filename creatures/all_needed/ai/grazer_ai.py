"""Универсальный ИИ травоядных: бродит, ест траву, пьёт воду, в панике убегает от волков."""

from .roaming_ai import RoamingAnimalMixin
from settings import BIOME_RIVER

class GrazerAI(RoamingAnimalMixin):

    def __init__(self, animal, cfg):
        self.entity = animal
        self.cfg = cfg
        self.target = None
        self.decision_timer = 0.0
        self.fleeing = False

    # ---------- Потребности ----------

    def update_needs(self, dt):
        a, cfg = self.entity, self.cfg
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

    # ---------- Решение ----------

    def decide(self, dt, grass_list, water_puddles, wolves, biome_grid):
        a, cfg = self.entity, self.cfg

        nearest_wolf = self._nearest_within(wolves, a.vision_radius)
        if nearest_wolf is not None:
            self.fleeing = True
            point = a.flee_point((nearest_wolf.x, nearest_wolf.y), cfg["flee_run_distance"])
            return self._avoid_sea(point, biome_grid)
        self.fleeing = False

        if a.hunger < a.hunger_max * cfg["hunger_seek_ratio"]:
            grass = self._nearest_within(grass_list, a.vision_radius, predicate=lambda g: g.has_food())
            if grass is not None:
                return (grass.x, grass.y)

        if a.thirst < a.thirst_max * cfg["thirst_seek_ratio"]:
            water_target = self._nearest_water_target(water_puddles, biome_grid, a.vision_radius)
            if water_target is not None:
                return water_target

        return self._wander(dt, biome_grid)

    # ---------- Действия вблизи ----------

    def interact(self, dt, grass_list, water_puddles, biome_grid):
        a, cfg = self.entity, self.cfg
        if a.hp <= 0:
            return

        if a.hunger < a.hunger_max:
            grass = self._nearest_within(grass_list, cfg["graze_distance"], predicate=lambda g: g.has_food())
            if grass is not None:
                amount = min(cfg["graze_rate"] * dt, grass.food, a.hunger_max - a.hunger)
                if amount > 0:
                    grass.food -= amount
                    a.hunger = min(a.hunger_max, a.hunger + amount)

        if a.thirst < a.thirst_max:
            water = self._nearest_within(water_puddles, cfg["drink_distance"], predicate=lambda w: w.has_water())
            if water is not None:
                wanted = min(cfg["drink_rate"] * dt, a.thirst_max - a.thirst)
                gained = water.consume(wanted)
                a.thirst = min(a.thirst_max, a.thirst + gained)
            elif biome_grid is not None and biome_grid.get_at(a.x, a.y) == BIOME_RIVER:
                a.thirst = min(a.thirst_max, a.thirst + cfg["drink_rate"] * dt)