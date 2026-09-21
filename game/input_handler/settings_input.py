"""Обработка ввода экрана 'Настройки' - пара к ui/settings_panel.py."""

import pygame

from .common import ScreenLayer


class SettingsLayer(ScreenLayer):

    def is_active(self):
        return self.game.settings_screen is not None

    def handle(self, event):
        game = self.game
        state = game.settings_screen
        panel = self.ui.settings_panel

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            game.close_settings_screen()
        elif event.type == pygame.MOUSEWHEEL:
            scroll = panel.scrolls.get(state.active_tab)
            if scroll is not None:
                scroll.scroll_by_wheel(event.y)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            panel.slider_dragging_key = None
        elif event.type == pygame.MOUSEMOTION:
            self._drag_slider(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._on_click(event.pos)

    def _drag_slider(self, mouse_x):
        panel = self.ui.settings_panel
        key = panel.slider_dragging_key
        if key is None:
            return
        value = panel.slider_value_from_mouse(key, mouse_x)
        if value is not None:
            self.game.settings_screen.set_value(key, value)

    def _on_click(self, pos):
        game = self.game
        state = game.settings_screen
        panel = self.ui.settings_panel

        if panel.settings_back_btn_rect.collidepoint(pos):
            game.close_settings_screen()
            return
        if panel.settings_save_btn_rect.collidepoint(pos):
            game.save_settings_screen()
            return
        for tab_key, rect in panel.tab_rects.items():
            if rect.collidepoint(pos):
                state.active_tab = tab_key
                return
        for key, row_rect in panel.settings_checkbox_rows.items():
            if row_rect.collidepoint(pos):
                state.toggle(key)
                return
        for key, slider_rect in panel.settings_slider_rows.items():
            if slider_rect is not None and slider_rect.collidepoint(pos):
                panel.slider_dragging_key = key
                self._drag_slider(pos[0])
                return