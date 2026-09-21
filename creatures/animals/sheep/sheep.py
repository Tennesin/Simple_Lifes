"""Класс овцы - минимальный набор данных + отрисовка. Поведение (AI, тик,
стрижка, разделка, стадность) будет добавлено отдельно."""

import random

import pygame

import info
import objects
import settings

from ...all_needed import base_creature, instruction, instruction_icons
from . import names, sheep_objects, sheep_settings


class Sheep(base_creature.CreatureBase):
    race_name = "sheep"
    diet = sheep_settings.SHEEP_DIET
    food_category_map = sheep_settings.SHEEP_FOOD_CATEGORY_MAP

    def __init__(self, creature_id, x, y, gender=None):
        super().__init__(
            creature_id, x, y,
            gender=gender,
            name_pools=names.SHEEP_NAME_POOLS,
            hp_max=sheep_settings.SHEEP_HP_MAX, hunger_max=sheep_settings.SHEEP_HUNGER_MAX,
            thirst_max=sheep_settings.SHEEP_THIRST_MAX, energy_max=sheep_settings.SHEEP_ENERGY_MAX,
            vision_radius=sheep_settings.SHEEP_VISION_RADIUS,
            base_speed_multiplier=sheep_settings.SHEEP_BASE_SPEED_MULTIPLIER,
            radius=sheep_settings.SHEEP_RADIUS,
        )

        # ---------- Ресурсы. Пока просто хранятся - логика добычи появится позже ----------
        self.meat = random.randint(sheep_settings.SHEEP_MEAT_MIN, sheep_settings.SHEEP_MEAT_MAX)
        self.wool = random.randint(sheep_settings.SHEEP_WOOL_MIN, sheep_settings.SHEEP_WOOL_MAX)

    def has_meat(self):
        return self.meat > 0

    def has_wool(self):
        return self.wool > 0

    def get_type_name(self):
        return sheep_settings.SHEEP_KIND_NAME

    # ---------- Отрисовка: белое овальное тело + две тонкие чёрные ножки ----------
    def draw(self, screen, screen_pos, show_status_rings=True):
        sx, sy = int(screen_pos[0]), int(screen_pos[1])
        half_w, half_h = sheep_settings.SHEEP_BODY_WIDTH // 2, sheep_settings.SHEEP_BODY_HEIGHT // 2

        for leg_dx in (-half_w // 2, half_w // 2):
            leg_rect = pygame.Rect(
                sx + leg_dx - sheep_settings.SHEEP_LEG_WIDTH // 2, sy + half_h - 2,
                sheep_settings.SHEEP_LEG_WIDTH, sheep_settings.SHEEP_LEG_HEIGHT)
            pygame.draw.rect(screen, sheep_settings.SHEEP_COLOR_LEG, leg_rect)

        body_rect = pygame.Rect(
            sx - half_w, sy - half_h, sheep_settings.SHEEP_BODY_WIDTH, sheep_settings.SHEEP_BODY_HEIGHT)
        pygame.draw.ellipse(screen, sheep_settings.SHEEP_COLOR_BODY, body_rect)
        pygame.draw.ellipse(screen, sheep_settings.SHEEP_COLOR_BODY_BORDER, body_rect, 2)

    def to_dict(self):
        d = self.base_to_dict()
        d["meat"] = self.meat
        d["wool"] = self.wool
        return d

    @staticmethod
    def from_dict(data):
        sheep = Sheep(data["id"], data["x"], data["y"], gender=data.get("gender"))
        sheep.apply_base_dict(data)
        sheep.meat = data.get("meat", sheep.meat)
        sheep.wool = data.get("wool", sheep.wool)
        return sheep

    def get_drops(self):
        drops = []
        if self.meat > 0:
            drops.append(objects.Meat(self.x, self.y, food_amount=self.meat))
        if self.wool > 0:
            drops.append(sheep_objects.Wool(self.x, self.y, self.wool))
        return drops

def sheep_object_panel_extra_lines(obj, all_creatures):
    if not isinstance(obj, Sheep):
        return []
    return [
        (info.INFO_INFO_ANIMAL_MEAT.format(count=int(obj.meat)), settings.MEAT_COLOR),
        (sheep_settings.SHEEP_INFO_WOOL.format(count=int(obj.wool)), sheep_settings.WOOL_COLOR),
    ]

def sheep_minimap_marker(screen, pos):
    """Овца на мини-карте: белый овал."""
    x, y = int(pos[0]), int(pos[1])
    rect = pygame.Rect(0, 0, 6, 4)
    rect.center = (x, y)
    pygame.draw.ellipse(screen, sheep_settings.SHEEP_COLOR_BODY, rect)

sheep_instruction_icon = instruction_icons.make_singleton_icon_factory(
    Sheep,
    (sheep_settings.SHEEP_BODY_WIDTH, sheep_settings.SHEEP_BODY_HEIGHT, sheep_settings.SHEEP_LEG_HEIGHT))

SHEEP_INSTRUCTION_SECTIONS = (
    instruction.InstructionParagraph(
        "Овца - мелкое пугливое травоядное. Белое овальное тело на двух тонких чёрных "
        "ножках. Слабее коровы и хуже видит, зато заметно шустрее и удирает от опасности "
        "быстрее всех домашних животных."),

    instruction.InstructionHeader("Поведение"),
    instruction.InstructionBullet("Пасётся на траве и пьёт из водоёмов и рек.", icon="sheep"),
    instruction.InstructionBullet(
        "От волка убегает почти вдвое быстрее обычного шага.",
        color=instruction.INSTRUCTION_COLOR_WARNING),
    instruction.InstructionBullet("Из-за небольшого запаса сил истощается быстрее коровы."),

    instruction.InstructionHeader("Что даёт"),
    instruction.InstructionBullet("Мясо - падает после смерти.", color=instruction.INSTRUCTION_COLOR_GOOD),
    instruction.InstructionBullet(
        "Шерсть - падает после смерти. Практического применения пока нет, "
        "но лежит она дольше прочих ресурсов.", color=instruction.INSTRUCTION_COLOR_HINT),

    instruction.InstructionHeader("Опасности"),
    instruction.InstructionBullet(
        "Волки выбирают овец как самую доступную добычу.",
        color=instruction.INSTRUCTION_COLOR_WARNING),
    instruction.InstructionBullet(
        "Шипы и море опасны так же, как и для остальных животных.",
        color=instruction.INSTRUCTION_COLOR_WARNING),
)