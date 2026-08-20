"""Базовый шаблон существа - общий для ВСЕХ будущих рас и животных."""

import random
import time

from names import random_name
from .base_entity import LivingEntity

GENDER_MALE = "male"
GENDER_FEMALE = "female"
DEFAULT_GENDER_LIST = (GENDER_MALE, GENDER_FEMALE)

class CreatureBase(LivingEntity):
    """Базовый шаблон."""
    race_name = None

    def __init__(self, creature_id, x, y,
                 gender=None, gender_list=DEFAULT_GENDER_LIST,
                 name=None, name_pools=None,
                 hp_max=100, hunger_max=25, thirst_max=25, energy_max=100,
                 vision_radius=900, base_speed_multiplier=1.0, radius=10):

        # ---------- Идентификация ----------
        self.id = creature_id
        self.gender = gender if gender in gender_list else random.choice(gender_list)
        self.name = name if name else random_name(self.gender, pools=name_pools)

        # ---------- Позиция и физическое тело ----------
        self.x = x
        self.y = y
        self.radius = radius

        # ---------- Базовые потребности ----------
        self.hp_max = hp_max
        self.hunger_max = hunger_max
        self.thirst_max = thirst_max
        self.energy_max = energy_max

        self.hp = hp_max
        self.hunger = hunger_max
        self.thirst = thirst_max
        self.energy = energy_max

        # ---------- Восприятие и движение ----------
        self.vision_radius = vision_radius
        self.base_speed_multiplier = base_speed_multiplier

        # ---------- Смерть ----------
        self.is_dead = False
        self.death_timer = 0.0
        self.death_cause = None

        # ---------- Шипы: неуязвимость после удара (иначе урон "тикает" каждый кадр) ----------
        self.spike_invuln_timer = 0.0

        # ---------- Инфраструктура для BasePathfinder. ----------
        self.target = None
        self.speed_factor = 1.0
        self.following_road_active = False
        self.nav_path = []
        self.nav_path_index = 0
        self.nav_goal = None
        self.nav_recalc_timer = 0.0

        # ---------- Метка создания - нужна животным для отображения в ObjectPanel ----------
        self.created = time.time()

    # ---------- Переопределяем заглушку из LivingEntity ----------
    def effective_vision_radius(self):
        return self.vision_radius