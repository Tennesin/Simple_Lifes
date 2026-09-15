"""Класс овцы - минимальный набор данных + отрисовка. Поведение (AI, тик,
стрижка, разделка, стадность) будет добавлено отдельно."""

import random
import pygame

from ...all_needed.base_creature import CreatureBase
from ...all_needed.instruction_icons import IconCache, render_scaled_icon
from ...all_needed.instruction import (
    InstructionHeader, InstructionParagraph, InstructionBullet,
    INSTRUCTION_COLOR_WARNING, INSTRUCTION_COLOR_GOOD, INSTRUCTION_COLOR_HINT,
)
from .sheep_settings import *
from .names import SHEEP_NAME_POOLS
from objects import Meat
from .sheep_objects import Wool
from settings import MEAT_COLOR
from info import INFO_INFO_ANIMAL_MEAT

class Sheep(CreatureBase):
    race_name = "sheep"
    diet = SHEEP_DIET
    food_category_map = SHEEP_FOOD_CATEGORY_MAP

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

    def to_dict(self):
        return {
            "id": self.id, "x": self.x, "y": self.y, "gender": self.gender,
            "name": self.name, "hp": self.hp, "hunger": self.hunger, "thirst": self.thirst,
            "energy": self.energy, "meat": self.meat,
            "wool": self.wool, "created": self.created,
            "frozen_timer": self.frozen_timer,
            "player_touched": self.player_touched,
        }

    @staticmethod
    def from_dict(data):
        sheep = Sheep(data["id"], data["x"], data["y"], gender=data.get("gender"))
        sheep.name = data.get("name", sheep.name)
        sheep.hp = data.get("hp", sheep.hp)
        sheep.hunger = data.get("hunger", sheep.hunger)
        sheep.thirst = data.get("thirst", sheep.thirst)
        sheep.energy = data.get("energy", sheep.energy)
        sheep.meat = data.get("meat", sheep.meat)
        sheep.wool = data.get("wool", sheep.wool)
        sheep.created = data.get("created", sheep.created)
        sheep.frozen_timer = data.get("frozen_timer", 0.0)
        sheep.player_touched = data.get("player_touched", False)
        return sheep

    def get_drops(self):
        drops = []
        if self.meat > 0:
            drops.append(Meat(self.x, self.y, food_amount=self.meat))
        if self.wool > 0:
            drops.append(Wool(self.x, self.y, self.wool))
        return drops

def sheep_object_panel_extra_lines(obj, all_creatures):
    if not isinstance(obj, Sheep):
        return []
    return [
        (INFO_INFO_ANIMAL_MEAT.format(count=int(obj.meat)), MEAT_COLOR),
        (SHEEP_INFO_WOOL.format(count=int(obj.wool)), WOOL_COLOR),
    ]

def sheep_minimap_marker(screen, pos):
    """Овца на мини-карте: белый овал."""
    x, y = int(pos[0]), int(pos[1])
    rect = pygame.Rect(0, 0, 6, 4)
    rect.center = (x, y)
    pygame.draw.ellipse(screen, SHEEP_COLOR_BODY, rect)

_SHEEP_ICON_CACHE = IconCache()
_SHEEP_ICON_SAMPLE = None

def _icon_sheep():
    global _SHEEP_ICON_SAMPLE
    if _SHEEP_ICON_SAMPLE is None:
        _SHEEP_ICON_SAMPLE = Sheep("icon", 0, 0)
    return _SHEEP_ICON_SAMPLE

def sheep_instruction_icon(variant_key=None, size=20):
    def _build():
        source = (SHEEP_BODY_WIDTH + 12, SHEEP_BODY_HEIGHT + SHEEP_LEG_HEIGHT + 12)
        return render_scaled_icon(
            lambda surface, center: _icon_sheep().draw(surface, center), source, size)

    return _SHEEP_ICON_CACHE.get(size, _build)

SHEEP_INSTRUCTION_SECTIONS = (
    InstructionParagraph(
        "Овца - мелкое пугливое травоядное. Белое овальное тело на двух тонких чёрных "
        "ножках. Слабее коровы и хуже видит, зато заметно шустрее и удирает от опасности "
        "быстрее всех домашних животных."),

    InstructionHeader("Поведение"),
    InstructionBullet("Пасётся на траве и пьёт из водоёмов и рек.", icon="sheep"),
    InstructionBullet("От волка убегает почти вдвое быстрее обычного шага.",
                      color=INSTRUCTION_COLOR_WARNING),
    InstructionBullet("Из-за небольшого запаса сил истощается быстрее коровы."),

    InstructionHeader("Что даёт"),
    InstructionBullet("Мясо - падает после смерти.", color=INSTRUCTION_COLOR_GOOD),
    InstructionBullet("Шерсть - падает после смерти. Практического применения пока нет, "
                      "но лежит она дольше прочих ресурсов.", color=INSTRUCTION_COLOR_HINT),

    InstructionHeader("Опасности"),
    InstructionBullet("Волки выбирают овец как самую доступную добычу.",
                      color=INSTRUCTION_COLOR_WARNING),
    InstructionBullet("Шипы и море опасны так же, как и для остальных животных.",
                      color=INSTRUCTION_COLOR_WARNING),
)