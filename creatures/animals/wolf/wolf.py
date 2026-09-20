"""Класс волка - минимальный набор данных + отрисовка."""

import random
import pygame

from ...all_needed import base_creature
from ...all_needed import instruction
from ...all_needed import instruction_icons
from . import wolf_settings
from . import wolf_objects
from . import names

class Wolf(base_creature.CreatureBase):
    race_name = "wolf"
    diet = wolf_settings.WOLF_DIET
    food_category_map = wolf_settings.WOLF_FOOD_CATEGORY_MAP

    def __init__(self, creature_id, x, y, gender=None):
        super().__init__(
            creature_id, x, y,
            gender=gender,
            name_pools=names.WOLF_NAME_POOLS,
            hp_max=wolf_settings.WOLF_HP_MAX, hunger_max=wolf_settings.WOLF_HUNGER_MAX,
            thirst_max=wolf_settings.WOLF_THIRST_MAX, energy_max=wolf_settings.WOLF_ENERGY_MAX,
            vision_radius=wolf_settings.WOLF_VISION_RADIUS,
            base_speed_multiplier=wolf_settings.WOLF_BASE_SPEED_MULTIPLIER,
            radius=wolf_settings.WOLF_RADIUS,
        )

        # ---------- Ресурсы ----------
        self.hide = random.randint(wolf_settings.WOLF_HIDE_MIN, wolf_settings.WOLF_HIDE_MAX)

    def has_hide(self):
        return self.hide > 0

    def get_type_name(self):
        return wolf_settings.WOLF_KIND_NAME

    # ---------- Отрисовка: светло-серый прямоугольник + 2 маленькие треугольные ножки ----------
    def draw(self, screen, screen_pos, show_status_rings=True):
        sx, sy = int(screen_pos[0]), int(screen_pos[1])
        half_w, half_h = wolf_settings.WOLF_BODY_WIDTH // 2, wolf_settings.WOLF_BODY_HEIGHT // 2

        for leg_dx in (-half_w // 2, half_w // 2):
            top = (sx + leg_dx - wolf_settings.WOLF_LEG_WIDTH // 2, sy + half_h - 1)
            bottom_left = (
                sx + leg_dx - wolf_settings.WOLF_LEG_WIDTH // 2 - 2,
                sy + half_h + wolf_settings.WOLF_LEG_HEIGHT)
            bottom_right = (
                sx + leg_dx + wolf_settings.WOLF_LEG_WIDTH // 2 + 2,
                sy + half_h + wolf_settings.WOLF_LEG_HEIGHT)
            pygame.draw.polygon(screen, wolf_settings.WOLF_COLOR_LEG, [top, bottom_left, bottom_right])

        body_rect = pygame.Rect(
            sx - half_w, sy - half_h, wolf_settings.WOLF_BODY_WIDTH, wolf_settings.WOLF_BODY_HEIGHT)
        pygame.draw.rect(screen, wolf_settings.WOLF_COLOR_BODY, body_rect, border_radius=3)
        pygame.draw.rect(screen, wolf_settings.WOLF_COLOR_BODY_BORDER, body_rect, 2, border_radius=3)

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
            drops.append(wolf_objects.Hide(self.x, self.y, self.hide))
        return drops

def wolf_object_panel_extra_lines(obj, all_creatures):
    if not isinstance(obj, Wolf):
        return []
    return [
        (wolf_settings.WOLF_INFO_HIDE.format(count=int(obj.hide)), wolf_settings.HIDE_COLOR),
    ]

def wolf_minimap_marker(screen, pos):
    """Волк на мини-карте: серый треугольник."""
    x, y = int(pos[0]), int(pos[1])
    size = 3
    points = [(x, y - size), (x - size, y + size), (x + size, y + size)]
    pygame.draw.polygon(screen, wolf_settings.WOLF_COLOR_BODY, points)

wolf_instruction_icon = instruction_icons.make_singleton_icon_factory(
    Wolf,
    (wolf_settings.WOLF_BODY_WIDTH, wolf_settings.WOLF_BODY_HEIGHT, wolf_settings.WOLF_LEG_HEIGHT))

WOLF_INSTRUCTION_SECTIONS = (
    instruction.InstructionParagraph(
        "Волк - единственный хищник мира. Светло-серое прямоугольное тело на маленьких "
        "треугольных лапах. Быстрее и зорче любого домашнего животного, ест исключительно "
        "сырое мясо - траву он не тронет даже умирая от голода."),

    instruction.InstructionHeader("Охота"),
    instruction.InstructionBullet(
        "Проголодавшись, выбирает ближайшую корову или овцу и преследует её, "
        "ускоряясь на погоне.", icon="wolf"),
    instruction.InstructionBullet(
        "Догнав, кусает жертву с небольшой паузой между укусами, пока та не падёт.",
        color=instruction.INSTRUCTION_COLOR_WARNING),
    instruction.InstructionBullet(
        "Погоня не бесконечна: если жертва слишком долго уходит или отрывается "
        "слишком далеко, волк бросает её и ищет другую."),
    instruction.InstructionBullet(
        "Готовую падаль (мясо на земле) волк съест охотнее, чем начнёт новую охоту.",
        color=instruction.INSTRUCTION_COLOR_HINT),

    instruction.InstructionHeader("Что даёт"),
    instruction.InstructionBullet("Шкура - падает после смерти.", color=instruction.INSTRUCTION_COLOR_GOOD),

    instruction.InstructionHeader("Особенности"),
    instruction.InstructionBullet(
        "Шипов волк боится и обходит их - но только пока не охотится. "
        "В разгар погони он их полностью игнорирует и может погибнуть.",
        color=instruction.INSTRUCTION_COLOR_WARNING),
    instruction.InstructionBullet("Охота дорого стоит: во время преследования силы тратятся заметно быстрее."),
    instruction.InstructionParagraph(
        "Волки не нападают на Кругов - их добыча только скот.", color=instruction.INSTRUCTION_COLOR_HINT),
)