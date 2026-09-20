"""Класс коровы - минимальный набор данных + отрисовка."""

import random
import pygame

import objects
import settings
import info
from ...all_needed import base_creature
from ...all_needed import instruction
from ...all_needed import instruction_icons
from . import cow_settings
from . import names
from . import cow_objects

class Cow(base_creature.CreatureBase):
    race_name = "cow"
    diet = cow_settings.COW_DIET
    food_category_map = cow_settings.COW_FOOD_CATEGORY_MAP

    def __init__(self, creature_id, x, y, gender=None):
        super().__init__(
            creature_id, x, y,
            gender=gender,
            name_pools=names.COW_NAME_POOLS,
            hp_max=cow_settings.COW_HP_MAX, hunger_max=cow_settings.COW_HUNGER_MAX,
            thirst_max=cow_settings.COW_THIRST_MAX, energy_max=cow_settings.COW_ENERGY_MAX,
            vision_radius=cow_settings.COW_VISION_RADIUS,
            base_speed_multiplier=cow_settings.COW_BASE_SPEED_MULTIPLIER,
            radius=cow_settings.COW_RADIUS,
        )

        # ---------- Ресурсы ----------
        self.meat = random.randint(cow_settings.COW_MEAT_MIN, cow_settings.COW_MEAT_MAX)
        self.leather = random.randint(cow_settings.COW_LEATHER_MIN, cow_settings.COW_LEATHER_MAX)
        self.milk_max_charges = cow_settings.COW_MILK_MAX_CHARGES
        self.milk_charges = float(cow_settings.COW_MILK_MAX_CHARGES)

        # ---------- Фиксированные позиции белых пятен - считаются один раз при создании,
        # чтобы не "прыгали" на теле каждый кадр ----------
        spot_count = random.randint(*cow_settings.COW_SPOT_COUNT_RANGE)
        half_w = cow_settings.COW_BODY_WIDTH // 2 - 4
        half_h = cow_settings.COW_BODY_HEIGHT // 2 - 4
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
        return cow_settings.COW_KIND_NAME

    # ---------- Отрисовка: тёмно-серый прямоугольник + белые точки + 2 тонкие ножки ----------
    def draw(self, screen, screen_pos, show_status_rings=True):
        sx, sy = int(screen_pos[0]), int(screen_pos[1])
        half_w, half_h = cow_settings.COW_BODY_WIDTH // 2, cow_settings.COW_BODY_HEIGHT // 2

        for leg_dx in (-half_w // 2, half_w // 2):
            leg_rect = pygame.Rect(
                sx + leg_dx - cow_settings.COW_LEG_WIDTH // 2, sy + half_h - 2,
                cow_settings.COW_LEG_WIDTH, cow_settings.COW_LEG_HEIGHT)
            pygame.draw.rect(screen, cow_settings.COW_COLOR_LEG, leg_rect)

        body_rect = pygame.Rect(
            sx - half_w, sy - half_h, cow_settings.COW_BODY_WIDTH, cow_settings.COW_BODY_HEIGHT)
        pygame.draw.rect(screen, cow_settings.COW_COLOR_BODY, body_rect, border_radius=4)
        pygame.draw.rect(screen, cow_settings.COW_COLOR_BODY_BORDER, body_rect, 2, border_radius=4)

        for ox, oy in self._spot_offsets:
            pygame.draw.circle(
                screen, cow_settings.COW_COLOR_SPOTS, (sx + ox, sy + oy), cow_settings.COW_SPOT_RADIUS)

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
            drops.append(objects.Meat(self.x, self.y, food_amount=self.meat))
        if self.leather > 0:
            drops.append(cow_objects.Leather(self.x, self.y, self.leather))
        return drops

# =========================================================================
# Строки панели объекта - расширение generic ObjectPanel
# =========================================================================

def cow_object_panel_extra_lines(obj, all_creatures):
    if not isinstance(obj, Cow):
        return []
    return [
        (info.INFO_INFO_ANIMAL_MEAT.format(count=int(obj.meat)), settings.MEAT_COLOR),
        (cow_settings.COW_INFO_LEATHER.format(count=int(obj.leather)), cow_settings.LEATHER_COLOR),
    ]

def cow_minimap_marker(screen, pos):
    """Корова на мини-карте: тёмно-серый круг."""
    pygame.draw.circle(screen, cow_settings.COW_COLOR_BODY, (int(pos[0]), int(pos[1])), 2)

# =========================================================================
# Инструкция: иконка (настоящий draw() коровы, вписанный в квадрат)
# и текстовое описание вида
# =========================================================================

cow_instruction_icon = instruction_icons.make_singleton_icon_factory(
    Cow, (cow_settings.COW_BODY_WIDTH, cow_settings.COW_BODY_HEIGHT, cow_settings.COW_LEG_HEIGHT))

COW_INSTRUCTION_SECTIONS = (
    instruction.InstructionParagraph(
        "Корова - крупное мирное травоядное. Тёмно-серое прямоугольное тело с белыми "
        "пятнами на двух тонких ножках. Самое выносливое из домашних животных, но и "
        "самое медлительное."),

    instruction.InstructionHeader("Поведение"),
    instruction.InstructionBullet("Бесцельно бродит по равнине, пока сыта и не напугана.", icon="cow"),
    instruction.InstructionBullet("Голодная ищет траву и выедает её - поляна при этом заметно скудеет."),
    instruction.InstructionBullet("Жажду утоляет из водоёмов и прямо из реки."),
    instruction.InstructionBullet(
        "Увидев волка, бросает всё и убегает, разгоняясь в полтора раза. "
        "Убегая, обходит углы и тупики, а не утыкается в них.",
        color=instruction.INSTRUCTION_COLOR_WARNING),

    instruction.InstructionHeader("Что даёт"),
    instruction.InstructionBullet("Мясо - падает после смерти.", color=instruction.INSTRUCTION_COLOR_GOOD),
    instruction.InstructionBullet("Кожа - падает после смерти.", color=instruction.INSTRUCTION_COLOR_GOOD),

    instruction.InstructionHeader("Опасности"),
    instruction.InstructionBullet(
        "Шипы ранят корову и отбрасывают её в сторону; она боится их и "
        "старается держаться подальше.", color=instruction.INSTRUCTION_COLOR_WARNING),
    instruction.InstructionBullet(
        "Море смертельно: оказавшуюся в воде корову выбрасывает на ближайший "
        "берег уже мёртвой.", color=instruction.INSTRUCTION_COLOR_WARNING),
    instruction.InstructionParagraph(
        "Животное вне области симуляции замирает и через некоторое время исчезает - "
        "если только игрок ни разу его не трогал.", color=instruction.INSTRUCTION_COLOR_HINT),
)