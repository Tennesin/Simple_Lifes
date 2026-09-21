"""Обработка ввода экранов 'Создание мира' и 'Загрузка мира' -
пара к ui/world_screens.py (там отрисовка, здесь клики/клавиатура)."""

import pygame

import settings
from .common import ScreenLayer

class CreateWorldLayer(ScreenLayer):

    def is_active(self):
        return self.game.create_world_screen is not None

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._on_mouse_down(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            for slider in self.game.create_world_screen.biome_sliders.values():
                slider.dragging = False
        elif event.type == pygame.MOUSEMOTION:
            self._drag_sliders(event.pos)
        elif event.type == pygame.KEYDOWN:
            self._on_keydown(event)

    def _on_mouse_down(self, pos):
        game = self.game
        screen = game.create_world_screen
        panel = self.ui.world_screens

        if panel.world_screen_back_btn_rect.collidepoint(pos):
            game.world_manager.cancel_create_screen()
            return
        for box in screen.all_inputs():
            box.try_focus(pos)
        if panel.ws_animals_checkbox_rect.collidepoint(pos):
            screen.generate_animals = not screen.generate_animals
            return
        for biome, slider in screen.biome_sliders.items():
            if slider.rect.collidepoint(pos):
                slider.dragging = True
                slider.set_from_mouse(pos[0])
                screen.apply_biome_slider_change(biome, slider.value)
                return
        if panel.ws_create_btn_rect.collidepoint(pos):
            game.world_manager.confirm_create_screen()

    def _drag_sliders(self, pos):
        screen = self.game.create_world_screen
        for biome, slider in screen.biome_sliders.items():
            if slider.dragging:
                slider.set_from_mouse(pos[0])
                screen.apply_biome_slider_change(biome, slider.value)
                break

    def _on_keydown(self, event):
        game = self.game
        if event.key == pygame.K_ESCAPE:
            game.world_manager.cancel_create_screen()
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            game.world_manager.confirm_create_screen()
        else:
            screen = game.create_world_screen
            for box in screen.all_inputs():
                if box.handle_keydown(event):
                    screen.error_text = None
                    break

class LoadWorldLayer(ScreenLayer):

    def is_active(self):
        return self.game.load_world_screen is not None

    def handle(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.game.world_manager.cancel_load_screen()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._on_click(event.pos)
        elif event.type == pygame.MOUSEWHEEL:
            self._on_wheel(event.y)

    def _on_click(self, pos):
        game = self.game
        screen = game.load_world_screen
        panel = self.ui.world_screens
        manager = game.world_manager

        if panel.world_screen_back_btn_rect.collidepoint(pos):
            manager.cancel_load_screen()
            return
        if panel.lw_list_rect is not None and panel.lw_list_rect.collidepoint(pos):
            local_y = pos[1] - panel.lw_list_rect.y + screen.list_scroll.offset
            index = int(local_y // settings.WORLD_LIST_ITEM_HEIGHT)
            if 0 <= index < len(screen.entries):
                manager.select_entry(screen, index)
            return
        if screen.selected_index is None:
            return
        if panel.lw_load_btn_rect is not None and panel.lw_load_btn_rect.collidepoint(pos):
            manager.load_selected(screen)
        elif panel.lw_delete_btn_rect is not None and panel.lw_delete_btn_rect.collidepoint(pos):
            manager.delete_selected(screen)

    def _on_wheel(self, wheel_y):
        screen = self.game.load_world_screen
        panel = self.ui.world_screens
        mouse_pos = pygame.mouse.get_pos()
        if panel.lw_list_rect is not None and panel.lw_list_rect.collidepoint(mouse_pos):
            content_height = len(screen.entries) * settings.WORLD_LIST_ITEM_HEIGHT
            screen.list_scroll.update_bounds(content_height, panel.lw_list_rect.height)
            screen.list_scroll.scroll_by_wheel(wheel_y)
        elif panel.lw_info_rect is not None and panel.lw_info_rect.collidepoint(mouse_pos):
            screen.info_scroll.update_bounds(panel.lw_info_content_height, panel.lw_info_rect.height)
            screen.info_scroll.scroll_by_wheel(wheel_y)