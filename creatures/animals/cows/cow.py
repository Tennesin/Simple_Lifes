"""Класс коровы - минимальный набор данных + отрисовка."""

import random
import math
import pygame

from ...all_needed.base_creature import CreatureBase
from .cow_settings import *
from .names import COW_NAME_POOLS


class Cow(CreatureBase):
    race_name = "cow"

    def __init__(self, creature_id, x, y, gender=None):
        super().__init__(
            creature_id, x, y,
            gender=gender,
            name_pools=COW_NAME_POOLS,
            hp_max=COW_HP_MAX, hunger_max=COW_HUNGER_MAX,
            thirst_max=COW_THIRST_MAX, energy_max=COW_ENERGY_MAX,
            vision_radius=COW_VISION_RADIUS,
            base_speed_multiplier=COW_BASE_SPEED_MULTIPLIER,
            radius=COW_RADIUS,
        )

        # ---------- Ресурсы ----------
        self.meat = random.randint(COW_MEAT_MIN, COW_MEAT_MAX)
        self.leather = random.randint(COW_LEATHER_MIN, COW_LEATHER_MAX)
        self.milk_max_charges = COW_MILK_MAX_CHARGES
        self.milk_charges = float(COW_MILK_MAX_CHARGES)

        # ---------- Фиксированные позиции белых пятен - считаются один раз при создании,
        # чтобы не "прыгали" на теле каждый кадр ----------
        spot_count = random.randint(*COW_SPOT_COUNT_RANGE)
        half_w, half_h = COW_BODY_WIDTH // 2 - 4, COW_BODY_HEIGHT // 2 - 4
        self._spot_offsets = [
            (random.randint(-half_w, half_w), random.randint(-half_h, half_h))
            for _ in range(spot_count)
        ]

    def has_meat(self):
        return self.meat > 0

    def has_leather(self):
        return self.leather > 0

    def has_milk(self):
        return self.milk_charges > 0.0

    def get_type_name(self):
        return COW_KIND_NAME

    # ---------- Отрисовка: тёмно-серый прямоугольник + белые точки + 2 тонкие ножки ----------
    def draw(self, screen, screen_pos, show_status_rings=True):
        sx, sy = int(screen_pos[0]), int(screen_pos[1])
        half_w, half_h = COW_BODY_WIDTH // 2, COW_BODY_HEIGHT // 2

        for leg_dx in (-half_w // 2, half_w // 2):
            leg_rect = pygame.Rect(
                sx + leg_dx - COW_LEG_WIDTH // 2, sy + half_h - 2,
                COW_LEG_WIDTH, COW_LEG_HEIGHT)
            pygame.draw.rect(screen, COW_COLOR_LEG, leg_rect)

        body_rect = pygame.Rect(sx - half_w, sy - half_h, COW_BODY_WIDTH, COW_BODY_HEIGHT)
        pygame.draw.rect(screen, COW_COLOR_BODY, body_rect, border_radius=4)
        pygame.draw.rect(screen, COW_COLOR_BODY_BORDER, body_rect, 2, border_radius=4)

        for ox, oy in self._spot_offsets:
            pygame.draw.circle(screen, COW_COLOR_SPOTS, (sx + ox, sy + oy), COW_SPOT_RADIUS)