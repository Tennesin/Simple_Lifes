"""Класс овцы - минимальный набор данных + отрисовка. Поведение (AI, тик,
стрижка, разделка, стадность) будет добавлено отдельно."""

import random
import pygame

from ...all_needed.base_creature import CreatureBase
from .sheep_settings import *
from .names import SHEEP_NAME_POOLS

class Sheep(CreatureBase):
    race_name = "sheep"

    def __init__(self, creature_id, x, y, gender=None):
        super().__init__(
            creature_id, x, y,
            gender=gender,
            name_pools=SHEEP_NAME_POOLS,
            hp_max=SHEEP_HP_MAX, hunger_max=SHEEP_HUNGER_MAX,
            thirst_max=SHEEP_THIRST_MAX, energy_max=SHEEP_ENERGY_MAX,
            vision_radius=SHEEP_VISION_RADIUS,
            base_speed_multiplier=SHEEP_BASE_SPEED_MULTIPLIER,
            radius=SHEEP_RADIUS,
        )

        # ---------- Ресурсы. Пока просто хранятся - логика добычи появится позже ----------
        self.meat = random.randint(SHEEP_MEAT_MIN, SHEEP_MEAT_MAX)
        self.wool = random.randint(SHEEP_WOOL_MIN, SHEEP_WOOL_MAX)

    def has_meat(self):
        return self.meat > 0

    def has_wool(self):
        return self.wool > 0

    def get_type_name(self):
        return SHEEP_KIND_NAME

    # ---------- Отрисовка: белое овальное тело + две тонкие чёрные ножки ----------
    def draw(self, screen, screen_pos, show_status_rings=True):
        sx, sy = int(screen_pos[0]), int(screen_pos[1])
        half_w, half_h = SHEEP_BODY_WIDTH // 2, SHEEP_BODY_HEIGHT // 2

        for leg_dx in (-half_w // 2, half_w // 2):
            leg_rect = pygame.Rect(
                sx + leg_dx - SHEEP_LEG_WIDTH // 2, sy + half_h - 2,
                SHEEP_LEG_WIDTH, SHEEP_LEG_HEIGHT)
            pygame.draw.rect(screen, SHEEP_COLOR_LEG, leg_rect)

        body_rect = pygame.Rect(sx - half_w, sy - half_h, SHEEP_BODY_WIDTH, SHEEP_BODY_HEIGHT)
        pygame.draw.ellipse(screen, SHEEP_COLOR_BODY, body_rect)
        pygame.draw.ellipse(screen, SHEEP_COLOR_BODY_BORDER, body_rect, 2)