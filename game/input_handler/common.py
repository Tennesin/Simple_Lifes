"""Общие вещи пакета ввода: базовый класс модального слоя, геометрия клика,
единая точка смены выбора и упорядоченный Escape-стек."""

import settings


class ScreenLayer:
    """Слой ввода, который, пока активен, забирает ВСЕ события себе (модальный экран)."""

    def __init__(self, game):
        self.game = game

    @property
    def ui(self):
        return self.game.ui

    def is_active(self):
        raise NotImplementedError

    def handle(self, event):
        raise NotImplementedError

def in_world_area(mouse_y):
    """Клик ниже верхней панели - т.е. в игровое поле."""
    return mouse_y > settings.UI_HEIGHT

def world_point(game, mouse_pos, clamp=False):
    """Мировая точка под курсором; clamp=True - прижать к границам мира (для рисования линий)."""
    wx, wy = game.camera.world_from_screen(*mouse_pos)
    if clamp:
        wx = max(0, min(wx, game.camera.world_w))
        wy = max(0, min(wy, game.camera.world_h))
    return wx, wy

def dispatch_hooks(hooks, game, event, mouse_x, mouse_y):
    for hook in hooks:
        if hook(game, event, mouse_x, mouse_y):
            return True
    return False

class SelectionService:
    """Существо / объект / боковая панель выбора взаимоисключаемы - это поддерживается здесь."""

    def __init__(self, game):
        self.game = game

    def clear(self):
        game = self.game
        game.selected_creature = None
        game.selected_object = None
        game.selected_object_click_pos = None
        game.clear_secondary_selections()

    def select_creature(self, creature):
        self.clear()
        self.game.selected_creature = creature

    def select_object(self, obj, anchor):
        self.clear()
        self.game.selected_object = obj
        self.game.selected_object_click_pos = anchor

    def select_in_secondary_panel(self, panel_attr, obj):
        self.clear()
        getattr(self.game.ui, panel_attr).selected = obj

    # ---------- Шаги Escape-стека: True, если что-то было снято ----------

    def clear_creature(self):
        if self.game.selected_creature is None:
            return False
        self.game.selected_creature = None
        return True

    def clear_object(self):
        if self.game.selected_object is None:
            return False
        self.game.selected_object = None
        return True

class EscapeStack:
    """Упорядоченный список шагов "отступить на один уровень назад"."""

    def __init__(self, steps):
        self._steps = tuple(steps)

    def handle(self):
        for step in self._steps:
            if step():
                return True
        return False