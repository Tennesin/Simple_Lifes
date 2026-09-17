"""Класс коровы - минимальный набор данных + отрисовка."""

import random
import pygame

from ...all_needed.base_creature import CreatureBase
from ...all_needed.instruction import (
    InstructionHeader, InstructionParagraph, InstructionBullet,
    INSTRUCTION_COLOR_WARNING, INSTRUCTION_COLOR_GOOD, INSTRUCTION_COLOR_HINT,
)
from ...all_needed.instruction_icons import make_singleton_icon_factory
from .cow_settings import *
from .names import COW_NAME_POOLS
from objects import Meat
from .cow_objects import Leather
from settings import MEAT_COLOR
from info import INFO_INFO_ANIMAL_MEAT

class Cow(CreatureBase):
    race_name = "cow"
    diet = COW_DIET
    food_category_map = COW_FOOD_CATEGORY_MAP

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

    def to_dict(self):
        d = self.base_to_dict()
        d["meat"] = self.meat
        d["leather"] = self.leather
        d["milk_charges"] = self.milk_charges
        return d

    @staticmethod
    def from_dict(data):
        cow = Cow(data["id"], data["x"], data["y"], gender=data.get("gender"))
        cow.apply_base_dict(data)
        cow.meat = data.get("meat", cow.meat)
        cow.leather = data.get("leather", cow.leather)
        cow.milk_charges = data.get("milk_charges", cow.milk_charges)
        return cow

    def get_drops(self):
        """Ресурсы, которые корова оставляет после себя вместо трупа."""
        drops = []
        if self.meat > 0:
            drops.append(Meat(self.x, self.y, food_amount=self.meat))
        if self.leather > 0:
            drops.append(Leather(self.x, self.y, self.leather))
        return drops

# =========================================================================
# Строки панели объекта - расширение generic ObjectPanel
# =========================================================================

def cow_object_panel_extra_lines(obj, all_creatures):
    if not isinstance(obj, Cow):
        return []
    return [
        (INFO_INFO_ANIMAL_MEAT.format(count=int(obj.meat)), MEAT_COLOR),
        (COW_INFO_LEATHER.format(count=int(obj.leather)), LEATHER_COLOR),
    ]

def cow_minimap_marker(screen, pos):
    """Корова на мини-карте: тёмно-серый круг."""
    pygame.draw.circle(screen, COW_COLOR_BODY, (int(pos[0]), int(pos[1])), 2)

# =========================================================================
# Инструкция: иконка (настоящий draw() коровы, вписанный в квадрат)
# и текстовое описание вида
# =========================================================================

cow_instruction_icon = make_singleton_icon_factory(
    Cow, (COW_BODY_WIDTH, COW_BODY_HEIGHT, COW_LEG_HEIGHT))

COW_INSTRUCTION_SECTIONS = (
    InstructionParagraph(
        "Корова - крупное мирное травоядное. Тёмно-серое прямоугольное тело с белыми "
        "пятнами на двух тонких ножках. Самое выносливое из домашних животных, но и "
        "самое медлительное."),

    InstructionHeader("Поведение"),
    InstructionBullet("Бесцельно бродит по равнине, пока сыта и не напугана.", icon="cow"),
    InstructionBullet("Голодная ищет траву и выедает её - поляна при этом заметно скудеет."),
    InstructionBullet("Жажду утоляет из водоёмов и прямо из реки."),
    InstructionBullet("Увидев волка, бросает всё и убегает, разгоняясь в полтора раза. "
                      "Убегая, обходит углы и тупики, а не утыкается в них.",
                      color=INSTRUCTION_COLOR_WARNING),

    InstructionHeader("Что даёт"),
    InstructionBullet("Мясо - падает после смерти.", color=INSTRUCTION_COLOR_GOOD),
    InstructionBullet("Кожа - падает после смерти.", color=INSTRUCTION_COLOR_GOOD),

    InstructionHeader("Опасности"),
    InstructionBullet("Шипы ранят корову и отбрасывают её в сторону; она боится их и "
                      "старается держаться подальше.", color=INSTRUCTION_COLOR_WARNING),
    InstructionBullet("Море смертельно: оказавшуюся в воде корову выбрасывает на ближайший "
                      "берег уже мёртвой.", color=INSTRUCTION_COLOR_WARNING),
    InstructionParagraph(
        "Животное вне области симуляции замирает и через некоторое время исчезает - "
        "если только игрок ни разу его не трогал.", color=INSTRUCTION_COLOR_HINT),
)