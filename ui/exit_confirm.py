"""Диалог "Сохранить игру?" при выходе (X окна / кнопка "Выйти")."""

import pygame

import settings
import info

class ExitConfirmPanel:

    WIDTH = 360
    HEIGHT = 160
    BTN_WIDTH = 100
    BTN_HEIGHT = 36
    BTN_GAP = 16

    def __init__(self, game, font):
        self.game = game
        self.font = font
        self.title_font = pygame.font.SysFont(settings.FONT_NAME, settings.FONT_SIZE_TITLE)
        self.exit_confirm_yes_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.exit_confirm_no_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.exit_confirm_back_btn_rect = pygame.Rect(0, 0, 0, 0)

    def draw(self, screen):
        window_w, window_h = screen.get_width(), screen.get_height()

        overlay = pygame.Surface((window_w, window_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, settings.SETTINGS_OVERLAY_ALPHA))
        screen.blit(overlay, (0, 0))

        width = min(self.WIDTH, window_w - 40)
        height = min(self.HEIGHT, window_h - 40)
        rect = pygame.Rect((window_w - width) // 2, (window_h - height) // 2, width, height)

        pygame.draw.rect(screen, settings.SETTINGS_PANEL_BG, rect)
        pygame.draw.rect(screen, settings.SETTINGS_PANEL_BORDER, rect, 2)

        title_txt = self.title_font.render(info.INFO_EXIT_CONFIRM_TITLE, True, settings.WORLD_SCREEN_TEXT)
        screen.blit(title_txt, title_txt.get_rect(centerx=rect.centerx, y=rect.y + 22))

        mouse_pos = pygame.mouse.get_pos()
        btn_y = rect.bottom - 20 - self.BTN_HEIGHT
        total_w = self.BTN_WIDTH * 3 + self.BTN_GAP * 2
        start_x = rect.centerx - total_w // 2

        self.exit_confirm_yes_btn_rect = pygame.Rect(start_x, btn_y, self.BTN_WIDTH, self.BTN_HEIGHT)
        self.exit_confirm_no_btn_rect = pygame.Rect(
            start_x + self.BTN_WIDTH + self.BTN_GAP, btn_y, self.BTN_WIDTH, self.BTN_HEIGHT)
        self.exit_confirm_back_btn_rect = pygame.Rect(
            start_x + 2 * (self.BTN_WIDTH + self.BTN_GAP), btn_y, self.BTN_WIDTH, self.BTN_HEIGHT)

        self._draw_button(screen, self.exit_confirm_yes_btn_rect, info.INFO_EXIT_CONFIRM_YES, mouse_pos)
        self._draw_button(screen, self.exit_confirm_no_btn_rect, info.INFO_EXIT_CONFIRM_NO, mouse_pos)
        self._draw_button(screen, self.exit_confirm_back_btn_rect, info.INFO_EXIT_CONFIRM_BACK, mouse_pos,
                          close_style=True)

    def _draw_button(self, screen, rect, label, mouse_pos, close_style=False):
        if close_style:
            color = settings.CLOSE_BUTTON_HOVER if rect.collidepoint(mouse_pos) else settings.CLOSE_BUTTON_COLOR
        else:
            color = settings.BUTTON_HOVER if rect.collidepoint(mouse_pos) else settings.BUTTON_COLOR
        pygame.draw.rect(screen, color, rect, border_radius=4)
        txt = self.font.render(label, True, settings.TEXT_COLOR)
        screen.blit(txt, txt.get_rect(center=rect.center))