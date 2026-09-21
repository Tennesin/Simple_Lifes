"""Обработка ввода экрана 'Инструкция' - пара к ui/instruction_panel.py."""

import pygame

from .common import ScreenLayer


class InstructionLayer(ScreenLayer):

    def is_active(self):
        return self.game.instruction_screen is not None

    def handle(self, event):
        state = self.game.instruction_screen
        scroll = state.active_scroll()

        if event.type == pygame.KEYDOWN:
            self._on_keydown(event.key, scroll)
        elif event.type == pygame.MOUSEWHEEL:
            if scroll is not None:
                scroll.scroll_by_wheel(event.y)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if scroll is not None:
                scroll.end_drag()
        elif event.type == pygame.MOUSEMOTION:
            if scroll is not None and scroll.is_dragging():
                scroll.drag_to(event.pos[1])
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._on_click(event.pos, state, scroll)

    def _on_keydown(self, key, scroll):
        if key == pygame.K_ESCAPE:
            self.game.close_instruction_screen()
        elif scroll is not None and key == pygame.K_UP:
            scroll.scroll_by_step(-1)
        elif scroll is not None and key == pygame.K_DOWN:
            scroll.scroll_by_step(1)

    def _on_click(self, pos, state, scroll):
        panel = self.ui.instruction_panel
        if panel.close_btn_rect.collidepoint(pos):
            self.game.close_instruction_screen()
            return
        for key, rect in panel.tab_rects.items():
            if rect.collidepoint(pos):
                state.set_active(key)
                return
        if scroll is not None and scroll.hit_test_scrollbar(pos):
            scroll.begin_drag(pos[1])
            return
        accordion = state.active_accordion()
        if accordion is not None and panel.body_rect.collidepoint(pos):
            accordion.handle_click(pos)