"""Плашка выбранного объекта (не существа) — core-часть + расовые расширения."""

import time
import pygame

from settings import *
from info import *
from game.race_registry import all_object_panel_extensions
from game.animal_registry import all_animal_object_panel_extensions
from creatures.all_needed.instruction import wrap_instruction_text

class ObjectPanel:

    MIN_WIDTH = 200
    MAX_WIDTH = 420
    LINE_HEIGHT = 22

    def __init__(self, game, font):
        self.game = game
        self.font = font

    def _get_object_anchor_pos(self, obj):
        if hasattr(obj, "x"):
            return (obj.x, obj.y)
        if hasattr(obj, "points") and obj.points:
            avg_x = sum(p[0] for p in obj.points) / len(obj.points)
            avg_y = sum(p[1] for p in obj.points) / len(obj.points)
            return (avg_x, avg_y)
        return (0, 0)

    def _get_resource_label(self, obj):
        if hasattr(obj, "wood"):
            return INFO_INFO_TREE_WOOD.format(count=int(obj.wood))
        if hasattr(obj, "stone") and not hasattr(obj, "fruits") and not hasattr(obj, "build_type"):
            return INFO_INFO_STONE_AMOUNT.format(count=int(obj.stone))
        if hasattr(obj, "charges") and hasattr(obj, "max_charges"):
            return INFO_INFO_WATER_CHARGES.format(count=int(obj.charges))
        if hasattr(obj, "food"):
            return INFO_INFO_FOOD_AMOUNT.format(count=int(obj.food))
        if hasattr(obj, "amount"):
            return INFO_INFO_RESOURCE_AMOUNT.format(count=int(obj.amount))
        return None

    def _collect_extra_lines(self, obj):
        lines = []
        for extra_fn in all_object_panel_extensions():
            lines.extend(extra_fn(obj, self.game.world.creatures))
        for extra_fn in all_animal_object_panel_extensions():
            lines.extend(extra_fn(obj, self.game.world.creatures))
        return lines

    def draw(self, screen):
        game = self.game
        obj = game.selected_object
        if not obj:
            return

        resource_label = self._get_resource_label(obj)
        extra_lines = self._collect_extra_lines(obj)

        type_name = obj.get_type_name()
        created_str = time.strftime("%H:%M:%S %d.%m", time.localtime(obj.created))
        created_label = INFO_INFO_CREATED.format(created=created_str)
        hint_label = INFO_INFO_DELETE_HINT

        # ---------- Ширина подгоняется под самый длинный текст, но с потолком под размер окна ----------
        screen_w, screen_h = screen.get_width(), screen.get_height()
        max_box_width = max(self.MIN_WIDTH, min(self.MAX_WIDTH, screen_w - 40))

        natural_widths = [
            self.font.size(type_name)[0],
            self.font.size(created_label)[0],
            self.font.size(hint_label)[0],
        ]
        if resource_label:
            natural_widths.append(self.font.size(resource_label)[0])
        for text, _color in extra_lines:
            natural_widths.append(self.font.size(text)[0])

        content_max = max(natural_widths) if natural_widths else 0
        box_width = int(max(self.MIN_WIDTH, min(max_box_width, content_max + 20)))
        text_max_width = box_width - 20

        # ---------- То, что не влезло даже на максимальной ширине, переносим на несколько строк ----------
        resource_sub_lines = wrap_instruction_text(self.font, resource_label, text_max_width) if resource_label else []
        extra_sub_lines = []
        for text, color in extra_lines:
            for sub in wrap_instruction_text(self.font, text, text_max_width):
                extra_sub_lines.append((sub, color))

        body_line_count = len(resource_sub_lines) + len(extra_sub_lines)
        box_height = 78 + self.LINE_HEIGHT * body_line_count

        anchor = game.selected_object_click_pos or self._get_object_anchor_pos(obj)
        screen_pos = game.camera.apply_pos(anchor)

        box_x = screen_pos[0] + 20
        box_y = screen_pos[1] - 15
        box_x = max(5, min(box_x, screen_w - box_width - 5))
        box_y = max(UI_HEIGHT + 5, min(box_y, screen_h - box_height - 5))

        rect = pygame.Rect(int(box_x), int(box_y), box_width, box_height)
        pygame.draw.rect(screen, INFO_PANEL_COLOR, rect)
        pygame.draw.rect(screen, INFO_PANEL_BORDER, rect, 2)

        type_txt = self.font.render(type_name, True, TEXT_COLOR)
        screen.blit(type_txt, (rect.x + 10, rect.y + 8))

        created_txt = self.font.render(created_label, True, TEXT_COLOR)
        screen.blit(created_txt, (rect.x + 10, rect.y + 34))

        next_y = rect.y + 56

        for line in resource_sub_lines:
            line_txt = self.font.render(line, True, (200, 200, 200))
            screen.blit(line_txt, (rect.x + 10, next_y))
            next_y += self.LINE_HEIGHT

        for line, color in extra_sub_lines:
            line_txt = self.font.render(line, True, color)
            screen.blit(line_txt, (rect.x + 10, next_y))
            next_y += self.LINE_HEIGHT

        hint_txt = self.font.render(hint_label, True, (190, 190, 190))
        screen.blit(hint_txt, (rect.x + 10, next_y))