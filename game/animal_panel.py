"""Панель информации о выбранном животном (корова/овца/волк) - уменьшенная
вдвое версия панели существа: здоровье/голод/жажда/энергия + ресурсы."""

import pygame
from settings import *
from game.animal_registry import all_animal_object_panel_extensions

class AnimalPanel:

    def __init__(self, game, font):
        self.game = game
        self.font = font
        self.rebuild_layout(WINDOW_WIDTH, WINDOW_HEIGHT)

    def rebuild_layout(self, window_w, window_h):
        full_height = window_h - UI_HEIGHT
        half_height = full_height // 2
        self.info_panel_rect = pygame.Rect(
            window_w - INFO_PANEL_WIDTH, UI_HEIGHT,
            INFO_PANEL_WIDTH, half_height
        )

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

    def draw(self, screen):
        game = self.game
        animal = game.selected_object
        if animal is None or not hasattr(animal, "hp"):
            return

        panel = self.info_panel_rect
        pygame.draw.rect(screen, INFO_PANEL_COLOR, panel)
        pygame.draw.rect(screen, INFO_PANEL_BORDER, panel, 2)

        name = animal.name if getattr(animal, "name", None) else animal.id
        title_txt = self.font.render(f"{animal.get_type_name()}: {name}", True, TEXT_COLOR)
        screen.blit(title_txt, (panel.x + 10, panel.y + 8))

        bar_width = panel.width - 20
        row_h = 30
        y = panel.y + 32

        self._draw_bar(screen, "Здоровье", animal.hp, animal.hp_max, (220, 60, 60), panel.x + 10, y, bar_width)
        y += row_h
        self._draw_bar(screen, "Голод", animal.hunger, animal.hunger_max, (200, 150, 40), panel.x + 10, y, bar_width)
        y += row_h
        self._draw_bar(screen, "Жажда", animal.thirst, animal.thirst_max, (60, 140, 220), panel.x + 10, y, bar_width)
        y += row_h
        self._draw_bar(screen, "Энергия", animal.energy, animal.energy_max, (90, 200, 200), panel.x + 10, y, bar_width)
        y += row_h + 6

        for text, color in self._collect_extra_lines(animal):
            line_txt = self.font.render(text, True, color)
            if y + 22 <= panel.bottom - 6:
                screen.blit(line_txt, (panel.x + 10, y))
                y += 22