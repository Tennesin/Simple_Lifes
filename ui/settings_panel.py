"""Экран "Настройки" — core-чекбоксы + расовые (через display_checkboxes)."""

import pygame

import info
import settings
from game.display_settings import (
    all_display_checkbox_specs,
    all_technical_checkbox_specs,
    all_technical_slider_specs,
)
from game.widgets import ScrollArea

SETTINGS_TABS = (
    ("technical", info.INFO_SETTINGS_TAB_TECHNICAL),
    ("display", info.INFO_SETTINGS_TAB_DISPLAY),
)

class SettingsPanel:

    PANEL_WIDTH = 700
    PANEL_HEIGHT = 650
    SIDEBAR_RATIO = 0.20
    ROW_HEIGHT = 34
    CHECKBOX_SIZE = 18

    def __init__(self, game, font):
        self.game = game
        self.font = font
        self.title_font = pygame.font.SysFont(settings.FONT_NAME, settings.FONT_SIZE_TITLE)

        self._checkboxes = all_display_checkbox_specs()
        self._technical_checkboxes = all_technical_checkbox_specs()
        self._technical_sliders = all_technical_slider_specs()

        self.panel_rect = pygame.Rect(0, 0, 0, 0)
        self.tab_rects = {}
        self.settings_save_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.settings_back_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.settings_checkbox_rows = {}
        self.settings_slider_rows = {}
        self.slider_dragging_key = None
        self.scrolls = {"display": ScrollArea(), "technical": ScrollArea()}

    def _layout_panel(self, screen):
        window_w, window_h = screen.get_width(), screen.get_height()
        width = min(self.PANEL_WIDTH, window_w - 40)
        height = min(self.PANEL_HEIGHT, window_h - 40)
        x = (window_w - width) // 2
        y = (window_h - height) // 2
        self.panel_rect = pygame.Rect(x, y, width, height)

    def draw(self, screen, state):
        self._layout_panel(screen)
        mouse_pos = pygame.mouse.get_pos()

        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, settings.SETTINGS_OVERLAY_ALPHA))
        screen.blit(overlay, (0, 0))

        panel = self.panel_rect
        pygame.draw.rect(screen, settings.SETTINGS_PANEL_BG, panel)
        pygame.draw.rect(screen, settings.SETTINGS_PANEL_BORDER, panel, 2)

        title_txt = self.title_font.render(info.INFO_SETTINGS_TITLE, True, settings.WORLD_SCREEN_TEXT)
        screen.blit(title_txt, (panel.x + 16, panel.y + 14))

        content_top = panel.y + 14 + title_txt.get_height() + 14
        buttons_area_height = 56
        content_rect = pygame.Rect(
            panel.x + 12, content_top,
            panel.width - 24, panel.bottom - buttons_area_height - content_top - 10
        )

        sidebar_width = int(content_rect.width * self.SIDEBAR_RATIO)
        sidebar_rect = pygame.Rect(content_rect.x, content_rect.y, sidebar_width, content_rect.height)
        body_rect = pygame.Rect(
            sidebar_rect.right + 12, content_rect.y,
            content_rect.width - sidebar_width - 12, content_rect.height
        )

        pygame.draw.rect(screen, settings.SETTINGS_SIDEBAR_BG, sidebar_rect)

        self._draw_tabs(screen, state, sidebar_rect, mouse_pos)
        self._draw_body(screen, state, body_rect, mouse_pos)
        self._draw_buttons(screen, panel, mouse_pos)

    def _draw_tabs(self, screen, state, sidebar_rect, mouse_pos):
        y = sidebar_rect.y + 8
        for tab_key, tab_label in SETTINGS_TABS:
            rect = pygame.Rect(sidebar_rect.x + 6, y, sidebar_rect.width - 12, settings.BUTTON_HEIGHT)
            self.tab_rects[tab_key] = rect

            if state.active_tab == tab_key:
                color = settings.SETTINGS_TAB_SELECTED
            elif rect.collidepoint(mouse_pos):
                color = settings.SETTINGS_TAB_HOVER
            else:
                color = settings.SETTINGS_TAB_COLOR
            pygame.draw.rect(screen, color, rect, border_radius=4)

            label_txt = self.font.render(tab_label, True, settings.TEXT_COLOR)
            screen.blit(label_txt, label_txt.get_rect(center=rect.center))
            y += settings.BUTTON_HEIGHT + 6

    def _draw_body(self, screen, state, body_rect, mouse_pos):
        self.settings_checkbox_rows = {}
        self.settings_slider_rows = {}
        if state.active_tab == "display":
            checkboxes = self._checkboxes
            sliders = ()
        elif state.active_tab == "technical":
            checkboxes = self._technical_checkboxes
            sliders = self._technical_sliders
        else:
            return

        scroll = self.scrolls[state.active_tab]
        content_height = len(checkboxes) * self.ROW_HEIGHT
        if sliders:
            content_height += 12 + len(sliders) * 60
        scroll.update_bounds(content_height, body_rect.height)

        prev_clip = screen.get_clip()
        screen.set_clip(body_rect)

        y = body_rect.y - int(scroll.offset)
        for key, label in checkboxes:
            row_rect = pygame.Rect(body_rect.x, y, body_rect.width, self.ROW_HEIGHT)
            if row_rect.bottom >= body_rect.y and row_rect.y <= body_rect.bottom:
                self._draw_checkbox_row(screen, state, key, label, row_rect, mouse_pos)
                clipped = row_rect.clip(body_rect)
                if clipped.width > 0 and clipped.height > 0:
                    self.settings_checkbox_rows[key] = clipped
            y += self.ROW_HEIGHT

        if sliders:
            y += 12
            for key, label_template, min_v, max_v, step in sliders:
                row_bottom = self._draw_slider_row(screen, state, key, label_template, min_v, max_v, step,
                                                   body_rect.x, y, body_rect.width, mouse_pos)
                slider_rect = self.settings_slider_rows.get(key)
                if slider_rect is not None:
                    clipped = slider_rect.clip(body_rect)
                    self.settings_slider_rows[key] = clipped if clipped.height > 0 else None
                y = row_bottom

        screen.set_clip(prev_clip)
        if scroll.max_scroll > 0:
            scroll.draw_scrollbar(screen, body_rect)

    def _draw_slider_row(self, screen, state, key, label_template, min_v, max_v, step, x, y, width, mouse_pos):
        value = state.draft.get(key, min_v)
        label_txt = self.font.render(label_template.format(value=value), True, settings.TEXT_COLOR)
        screen.blit(label_txt, (x, y))

        bar_y = y + label_txt.get_height() + 6
        bar_rect = pygame.Rect(x, bar_y, width, 10)
        pygame.draw.rect(screen, (30, 30, 30), bar_rect)

        ratio = (value - min_v) / (max_v - min_v) if max_v > min_v else 0.0
        fill_w = max(4, int(bar_rect.width * max(0.0, min(1.0, ratio))))
        fill_rect = pygame.Rect(bar_rect.x, bar_rect.y, fill_w, bar_rect.height)
        fill_color = (100, 160, 210) if self.slider_dragging_key == key else settings.BUTTON_COLOR
        pygame.draw.rect(screen, fill_color, fill_rect)
        pygame.draw.rect(screen, (15, 15, 15), bar_rect, 1)

        handle_rect = pygame.Rect(0, 0, 4, bar_rect.height + 6)
        handle_rect.center = (bar_rect.x + fill_w, bar_rect.centery)
        pygame.draw.rect(screen, (240, 240, 240), handle_rect, border_radius=2)

        self.settings_slider_rows[key] = bar_rect
        return bar_rect.bottom + 16

    def _draw_checkbox_row(self, screen, state, key, label, row_rect, mouse_pos):
        cb_y = row_rect.y + (row_rect.height - self.CHECKBOX_SIZE) // 2
        cb_rect = pygame.Rect(row_rect.x, cb_y, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)

        hovered = row_rect.collidepoint(mouse_pos)
        box_bg = (55, 55, 55) if hovered else (40, 40, 40)
        pygame.draw.rect(screen, box_bg, cb_rect)
        pygame.draw.rect(screen, settings.WORLD_SCREEN_TEXT, cb_rect, 1)
        if state.draft.get(key):
            pygame.draw.line(screen, (120, 230, 120),
                             (cb_rect.x + 3, cb_rect.y + 9), (cb_rect.x + 7, cb_rect.y + 13), 2)
            pygame.draw.line(screen, (120, 230, 120),
                             (cb_rect.x + 7, cb_rect.y + 13), (cb_rect.x + 15, cb_rect.y + 3), 2)

        label_txt = self.font.render(label, True, settings.TEXT_COLOR)
        screen.blit(label_txt, (cb_rect.right + 10,
                                row_rect.y + (row_rect.height - label_txt.get_height()) // 2))

    def slider_value_from_mouse(self, key, mouse_x):
        for spec_key, _label, min_v, max_v, step in self._technical_sliders:
            if spec_key != key:
                continue
            rect = self.settings_slider_rows.get(key)
            if rect is None or rect.width <= 0:
                return None
            ratio = (mouse_x - rect.x) / rect.width
            ratio = max(0.0, min(1.0, ratio))
            raw = min_v + ratio * (max_v - min_v)
            stepped = round(raw / step) * step
            return int(max(min_v, min(max_v, stepped)))
        return None

    def _draw_buttons(self, screen, panel, mouse_pos):
        btn_w, btn_h = 130, 34
        gap = 12
        self.settings_save_btn_rect = pygame.Rect(
            panel.right - 12 - btn_w, panel.bottom - 12 - btn_h, btn_w, btn_h)
        self.settings_back_btn_rect = pygame.Rect(
            self.settings_save_btn_rect.x - gap - btn_w, panel.bottom - 12 - btn_h, btn_w, btn_h)

        save_color = settings.BUTTON_HOVER if self.settings_save_btn_rect.collidepoint(mouse_pos) else settings.BUTTON_COLOR
        pygame.draw.rect(screen, save_color, self.settings_save_btn_rect, border_radius=4)
        save_txt = self.font.render(info.INFO_BTN_SETTINGS_SAVE, True, settings.TEXT_COLOR)
        screen.blit(save_txt, save_txt.get_rect(center=self.settings_save_btn_rect.center))

        back_color = settings.CLOSE_BUTTON_HOVER if self.settings_back_btn_rect.collidepoint(mouse_pos) else settings.CLOSE_BUTTON_COLOR
        pygame.draw.rect(screen, back_color, self.settings_back_btn_rect, border_radius=4)
        back_txt = self.font.render(info.INFO_BTN_BACK, True, settings.TEXT_COLOR)
        screen.blit(back_txt, back_txt.get_rect(center=self.settings_back_btn_rect.center))