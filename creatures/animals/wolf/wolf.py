"""Класс волка - минимальный набор данных + отрисовка."""

import random
import pygame

from ...all_needed.base_creature import CreatureBase
from ...all_needed.instruction import (
    InstructionHeader, InstructionParagraph, InstructionBullet,
    INSTRUCTION_COLOR_WARNING, INSTRUCTION_COLOR_GOOD, INSTRUCTION_COLOR_HINT,
)
from ...all_needed.instruction_icons import make_singleton_icon_factory
from .wolf_settings import *
from .wolf_objects import Hide
from .names import WOLF_NAME_POOLS

class Wolf(CreatureBase):
    race_name = "wolf"
    diet = WOLF_DIET
    food_category_map = WOLF_FOOD_CATEGORY_MAP

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

    def to_dict(self):
        d = self.base_to_dict()
        d["hide"] = self.hide
        return d

    @staticmethod
    def from_dict(data):
        wolf = Wolf(data["id"], data["x"], data["y"], gender=data.get("gender"))
        wolf.apply_base_dict(data)
        wolf.hide = data.get("hide", wolf.hide)
        return wolf

    def get_drops(self):
        drops = []
        if self.hide > 0:
            drops.append(Hide(self.x, self.y, self.hide))
        return drops

def wolf_object_panel_extra_lines(obj, all_creatures):
    if not isinstance(obj, Wolf):
        return []
    return [
        (WOLF_INFO_HIDE.format(count=int(obj.hide)), HIDE_COLOR),
    ]

def wolf_minimap_marker(screen, pos):
    """Волк на мини-карте: серый треугольник."""
    x, y = int(pos[0]), int(pos[1])
    size = 3
    points = [(x, y - size), (x - size, y + size), (x + size, y + size)]
    pygame.draw.polygon(screen, WOLF_COLOR_BODY, points)

wolf_instruction_icon = make_singleton_icon_factory(
    Wolf, (WOLF_BODY_WIDTH, WOLF_BODY_HEIGHT, WOLF_LEG_HEIGHT))

WOLF_INSTRUCTION_SECTIONS = (
    InstructionParagraph(
        "Волк - единственный хищник мира. Светло-серое прямоугольное тело на маленьких "
        "треугольных лапах. Быстрее и зорче любого домашнего животного, ест исключительно "
        "сырое мясо - траву он не тронет даже умирая от голода."),

    InstructionHeader("Охота"),
    InstructionBullet("Проголодавшись, выбирает ближайшую корову или овцу и преследует её, "
                      "ускоряясь на погоне.", icon="wolf"),
    InstructionBullet("Догнав, кусает жертву с небольшой паузой между укусами, пока та не падёт.",
                      color=INSTRUCTION_COLOR_WARNING),
    InstructionBullet("Погоня не бесконечна: если жертва слишком долго уходит или отрывается "
                      "слишком далеко, волк бросает её и ищет другую."),
    InstructionBullet("Готовую падаль (мясо на земле) волк съест охотнее, чем начнёт новую охоту.",
                      color=INSTRUCTION_COLOR_HINT),

    InstructionHeader("Что даёт"),
    InstructionBullet("Шкура - падает после смерти.", color=INSTRUCTION_COLOR_GOOD),

    InstructionHeader("Особенности"),
    InstructionBullet("Шипов волк боится и обходит их - но только пока не охотится. "
                      "В разгар погони он их полностью игнорирует и может погибнуть.",
                      color=INSTRUCTION_COLOR_WARNING),
    InstructionBullet("Охота дорого стоит: во время преследования силы тратятся заметно быстрее."),
    InstructionParagraph(
        "Волки не нападают на Кругов - их добыча только скот.", color=INSTRUCTION_COLOR_HINT),
)