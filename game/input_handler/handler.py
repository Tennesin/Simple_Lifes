"""Верхний уровень обработки ввода. InputHandler дёргается из game/game.py.
Здесь же - три самых маленьких модальных слоя (крах, диалог выхода, оверлей расы).
Экраны создания/загрузки/настроек/инструкции - в соседних файлах, по одному на экран,
как это сделано для отрисовки в ui/."""

import pygame

from .common import ScreenLayer
from .instruction_input import InstructionLayer
from .settings_input import SettingsLayer
from .world_layer import WorldLayer
from .world_screens import CreateWorldLayer, LoadWorldLayer


class CrashLayer(ScreenLayer):

    def is_active(self):
        return self.game.crashed

    def handle(self, event):
        game = self.game
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not game.crash_log_written and game.crash_log_btn_rect.collidepoint(event.pos):
                game.write_crash_log()

class ExitConfirmLayer(ScreenLayer):

    def is_active(self):
        return self.game.exit_confirm_active

    def handle(self, event):
        game = self.game
        panel = self.ui.exit_confirm_panel

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            game.cancel_exit()
            return
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return

        if panel.exit_confirm_yes_btn_rect.collidepoint(event.pos):
            game.confirm_exit_save()
        elif panel.exit_confirm_no_btn_rect.collidepoint(event.pos):
            game.confirm_exit_discard()
        elif panel.exit_confirm_back_btn_rect.collidepoint(event.pos):
            game.cancel_exit()

class ModalPanelLayer(ScreenLayer):
    """Модальные оверлеи расы (древо родословной и т.п.): активны, пока panel.modal_active."""

    def is_active(self):
        return self.ui.active_modal_panel() is not None

    def handle(self, event):
        panel = self.ui.active_modal_panel()
        if panel is not None:
            panel.handle_event(event)

class InputHandler:

    def __init__(self, game):
        self.game = game
        # ---------- Порядок = приоритет: первый активный слой забирает событие целиком ----------
        self._screen_layers = (
            ExitConfirmLayer(game), CrashLayer(game),
            CreateWorldLayer(game), LoadWorldLayer(game),
            SettingsLayer(game), InstructionLayer(game), ModalPanelLayer(game),
        )
        self._world = WorldLayer(game)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.game.request_exit(quit_app=True)
                continue
            layer = next((l for l in self._screen_layers if l.is_active()), None)
            if layer is not None:
                layer.handle(event)
            else:
                self._world.handle(event)