"""Класс волка - минимальный набор данных + отрисовка."""

import random
import pygame

from ...all_needed.base_creature import CreatureBase
from .wolf_settings import *
from .names import WOLF_NAME_POOLS

class Wolf(CreatureBase):
    race_name = "wolf"

    def __init__(self, creature_id, x, y, gender=None):
        super().__init__(
            creature_id, x, y,
            gender=gender,
            name_pools=WOLF_NAME_POOLS,
            hp_max=WOLF_HP_MAX, hunger_max=WOLF_HUNGER_MAX,
            thirst_max=WOLF_THIRST_MAX, energy_max=WOLF_ENERGY_MAX,
            vision_radius=WOLF_VISION_RADIUS,
            base_speed_multiplier=WOLF_BASE_SPEED_MULTIPLIER,
            radius=WOLF_RADIUS,
        )

        # ---------- Ресурсы ----------
        self.hide = random.randint(WOLF_HIDE_MIN, WOLF_HIDE_MAX)

    def has_hide(self):
        return self.hide > 0

    def get_type_name(self):
        return WOLF_KIND_NAME

    # ---------- Отрисовка: светло-серый прямоугольник + 2 маленькие треугольные ножки ----------
    def draw(self, screen, screen_pos, show_status_rings=True):
        sx, sy = int(screen_pos[0]), int(screen_pos[1])
        half_w, half_h = WOLF_BODY_WIDTH // 2, WOLF_BODY_HEIGHT // 2

        for leg_dx in (-half_w // 2, half_w // 2):
            top = (sx + leg_dx - WOLF_LEG_WIDTH // 2, sy + half_h - 1)
            bottom_left = (sx + leg_dx - WOLF_LEG_WIDTH // 2 - 2, sy + half_h + WOLF_LEG_HEIGHT)
            bottom_right = (sx + leg_dx + WOLF_LEG_WIDTH // 2 + 2, sy + half_h + WOLF_LEG_HEIGHT)
            pygame.draw.polygon(screen, WOLF_COLOR_LEG, [top, bottom_left, bottom_right])

        body_rect = pygame.Rect(sx - half_w, sy - half_h, WOLF_BODY_WIDTH, WOLF_BODY_HEIGHT)
        pygame.draw.rect(screen, WOLF_COLOR_BODY, body_rect, border_radius=3)
        pygame.draw.rect(screen, WOLF_COLOR_BODY_BORDER, body_rect, 2, border_radius=3)