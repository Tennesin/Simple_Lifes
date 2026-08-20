"""Панель информации о выбранном животном (корова/овца/волк) - компактная,
подстраивается под фактическое содержимое, в правом нижнем углу экрана."""

import pygame
from settings import *
from game.animal_registry import all_animal_object_panel_extensions

class AnimalPanel:

    MIN_WIDTH = 220
    MAX_WIDTH = 380
    MARGIN = 10
    ROW_HEIGHT = 30
    EXTRA_LINE_HEIGHT = 22
    TITLE_HEIGHT = 30

    def __init__(self, game, font):
        self.game = game
        self.font = font
        self.info_panel_rect = pygame.Rect(0, 0, 0, 0)
        self.rebuild_layout(WINDOW_WIDTH, WINDOW_HEIGHT)

    def rebuild_layout(self, window_w, window_h):
        # ---------- Позиция зависит от контента и считается в draw(), тут просто фиксируем экран ----------
        self.window_w = window_w
        self.window_h = window_h

    def _draw_bar(self, screen, label, value, max_value, color, x, y, width):
        label_txt = self.font.render(f"{label}: {value:.1f}/{max_value}", True, TEXT_COLOR)
        screen.blit(label_txt, (x, y))
        bar_rect = pygame.Rect(x, y + 18, width, 8)
        pygame.draw.rect(screen, (30, 30, 30), bar_rect)
        ratio = max(0.0, min(1.0, value / max_value)) if max_value else 0.0
        fill_rect = pygame.Rect(x, y + 18, width * ratio, 8)
        pygame.draw.rect(screen, color, fill_rect)

    def _collect_extra_lines(self, animal):
        lines = []
        for extra_fn in all_animal_object_panel_extensions():
            lines.extend(extra_fn(animal, self.game.world.creatures))
        return lines

    def _measure_content(self, animal, extra_lines, name):
        title_text = f"{animal.get_type_name()}: {name}"
        widths = [self.font.size(title_text)[0]]
        for label in ("Здоровье", "Голод", "Жажда", "Энергия"):
            widths.append(self.font.size(f"{label}: 000.0/000")[0])
        for text, _color in extra_lines:
            widths.append(self.font.size(text)[0])

        content_width = max(widths) if widths else 0
        width = int(max(self.MIN_WIDTH, min(self.MAX_WIDTH, content_width + 20)))
        height = self.TITLE_HEIGHT + self.ROW_HEIGHT * 4 + self.EXTRA_LINE_HEIGHT * len(extra_lines) + 16
        return width, height

    def draw(self, screen):
        game = self.game
        animal = game.selected_object
        if animal is None or not hasattr(animal, "hp"):
            return

        name = animal.name if getattr(animal, "name", None) else animal.id
        extra_lines = self._collect_extra_lines(animal)
        width, height = self._measure_content(animal, extra_lines, name)

        window_w, window_h = screen.get_width(), screen.get_height()
        panel = pygame.Rect(
            window_w - width - self.MARGIN,
            window_h - height - self.MARGIN,
            width, height
        )
        self.info_panel_rect = panel

        pygame.draw.rect(screen, INFO_PANEL_COLOR, panel)
        pygame.draw.rect(screen, INFO_PANEL_BORDER, panel, 2)

        title_txt = self.font.render(f"{animal.get_type_name()}: {name}", True, TEXT_COLOR)
        screen.blit(title_txt, (panel.x + 10, panel.y + 8))

        bar_width = panel.width - 20
        y = panel.y + self.TITLE_HEIGHT

        self._draw_bar(screen, "Здоровье", animal.hp, animal.hp_max, (220, 60, 60), panel.x + 10, y, bar_width)
        y += self.ROW_HEIGHT
        self._draw_bar(screen, "Голод", animal.hunger, animal.hunger_max, (200, 150, 40), panel.x + 10, y, bar_width)
        y += self.ROW_HEIGHT
        self._draw_bar(screen, "Жажда", animal.thirst, animal.thirst_max, (60, 140, 220), panel.x + 10, y, bar_width)
        y += self.ROW_HEIGHT
        self._draw_bar(screen, "Энергия", animal.energy, animal.energy_max, (90, 200, 200), panel.x + 10, y, bar_width)
        y += self.ROW_HEIGHT + 6

        for text, color in extra_lines:
            line_txt = self.font.render(text, True, color)
            screen.blit(line_txt, (panel.x + 10, y))
            y += self.EXTRA_LINE_HEIGHT