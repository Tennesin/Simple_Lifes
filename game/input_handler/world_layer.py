"""Диспетчеризация ввода на игровом поле: сборка контроллеров + роутинг событий
по типу (аналог ui/manager.py, но для ввода, а не отрисовки)."""

import pygame

from game.race_registry import (
    all_mouse_down_hooks,
    all_mouse_motion_hooks,
    all_mouse_up_hooks,
    all_mouse_wheel_hooks,
    all_secondary_panel_specs,
)
from game.widgets import TEXT_EDIT_CANCEL, TEXT_EDIT_COMMIT, edit_text_buffer

from .common import EscapeStack, SelectionService, dispatch_hooks
from .panels_input import PlacementController, SidePanelController, WorldClickController
from .tools_input import (
    BiomeBrushController,
    DrawingController,
    GrabController,
    PlayerToolController,
    ToolModeController,
)
from .top_bar_input import TopBarController


class HudController:
    """Элементы поверх мира, обрабатываемые раньше режимов инструментов: ручка
    сворачивания панели и клик по миникарте. Слишком маленький домен для своего файла."""

    def __init__(self, game):
        self.game = game
        self._secondary_specs = all_secondary_panel_specs()

    def on_mouse_down(self, event):
        return self._click_collapse_handle(event) or self._click_minimap(event)

    def _click_collapse_handle(self, event):
        game = self.game
        if event.button != 1 or not game.world_loaded:
            return False
        any_secondary = any(getattr(game.ui, spec.attr_name).selected is not None
                            for spec in self._secondary_specs)
        if not (game.selected_creature or any_secondary):
            return False
        if game.ui.collapse_handle_rect.collidepoint(event.pos):
            game.right_panel_collapsed = not game.right_panel_collapsed
            return True
        return False

    def _click_minimap(self, event):
        game = self.game
        rect = game.ui.minimap.rect
        if not (game.show_minimap and game.world_loaded and rect.collidepoint(event.pos)):
            return False
        if event.button == 1 and game.player.drawing_road is None:
            wx = (event.pos[0] - rect.x) / rect.width * game.camera.world_w
            wy = (event.pos[1] - rect.y) / rect.height * game.camera.world_h
            game.camera.center_on(wx, wy)
        return True     # любой клик по миникарте (даже ПКМ) съедается

class CameraDragController:
    """Перетаскивание камеры зажатой ПКМ."""

    def __init__(self, game):
        self.game = game
        self._dragging = False
        self._last_pos = (0, 0)

    def on_mouse_down(self, event):
        if event.button != 3 or not self.game.world_loaded:
            return False
        self._dragging = True
        self._last_pos = event.pos
        return True

    def on_mouse_up(self, event):
        if event.button == 3:
            self._dragging = False

    def on_motion(self, event):
        if self._dragging and not self.game.placement_mode:
            dx = event.pos[0] - self._last_pos[0]
            dy = event.pos[1] - self._last_pos[1]
            self.game.camera.move(-dx, -dy)
            self._last_pos = event.pos
        return False        # камера не отменяет остальные обработчики движения

class KeyboardController:
    """Горячие клавиши и редактирование имени существа/кладбища."""

    def __init__(self, game, escape):
        self.game = game
        self._secondary_specs = all_secondary_panel_specs()
        self._hotkeys = {
            pygame.K_ESCAPE: escape.handle,
            pygame.K_SPACE: game.toggle_pause,
            pygame.K_TAB: self._toggle_minimap,
            pygame.K_DELETE: self._delete_selected,
        }

    def handle(self, event):
        game = self.game
        if game.editing_name:
            self._edit_creature_name(event)
            return
        for spec in self._secondary_specs:
            panel = getattr(game.ui, spec.attr_name)
            if getattr(panel, "text_editing", False):
                panel.handle_keydown(event)
                return
        action = self._hotkeys.get(event.key)
        if action is not None:
            action()

    def _edit_creature_name(self, event):
        game = self.game
        game.name_edit_buffer, action = edit_text_buffer(game.name_edit_buffer, event)
        if action == TEXT_EDIT_COMMIT:
            game.finish_name_editing()
        elif action == TEXT_EDIT_CANCEL:
            game.editing_name = False

    def _toggle_minimap(self):
        self.game.show_minimap = not self.game.show_minimap

    def _delete_selected(self):
        game = self.game
        if game.selected_object:
            game.object_manager.delete_object(game.selected_object)
            game.selected_object = None

# =========================================================================
# Роутеры: по одному на тип pygame-события - просто прогоняют событие через
# свою цепочку контроллеров в фиксированном порядке.
# =========================================================================

class MouseDownRouter:

    def __init__(self, game, hud, tool_mode, placement, camera_drag, left_click_chain):
        self.game = game
        self._hud = hud
        self._tool_mode = tool_mode
        self._placement = placement
        self._camera_drag = camera_drag
        self._left_click_chain = left_click_chain
        self._hooks = all_mouse_down_hooks()

    def handle(self, event):
        game = self.game
        x, y = event.pos

        if dispatch_hooks(self._hooks, game, event, x, y):
            return
        if self._hud.on_mouse_down(event):
            return
        if self._tool_mode.on_mouse_down(event):
            return
        if game.placement_mode:
            self._placement.on_mouse_down(event)
            return
        if self._camera_drag.on_mouse_down(event):
            return
        if event.button == 1:
            for handler in self._left_click_chain:
                if handler.on_left_click(x, y):
                    return

class MouseUpRouter:

    def __init__(self, game, camera_drag, brush, drawing):
        self.game = game
        self._camera_drag = camera_drag
        self._brush = brush
        self._drawing = drawing
        self._hooks = all_mouse_up_hooks()

    def handle(self, event):
        self._camera_drag.on_mouse_up(event)
        if event.button == 1:
            self._brush.reset_stroke()
            dispatch_hooks(self._hooks, self.game, event, *event.pos)
            self._drawing.on_mouse_up(event)

class MouseMotionRouter:

    def __init__(self, game, brush, grab, camera_drag, drawing, placement):
        self.game = game
        # ---------- Порядок важен: True от обработчика останавливает цепочку ----------
        self._chain = (brush, grab, camera_drag, drawing, placement)
        self._hooks = all_mouse_motion_hooks()

    def handle(self, event):
        if dispatch_hooks(self._hooks, self.game, event, *event.pos):
            return
        for handler in self._chain:
            if handler.on_motion(event):
                return

class WheelController:

    def __init__(self, game):
        self.game = game
        self._secondary_specs = all_secondary_panel_specs()
        self._hooks = all_mouse_wheel_hooks()

    def handle(self, event):
        game = self.game
        if game.right_panel_collapsed:
            return
        mouse_x, mouse_y = pygame.mouse.get_pos()
        if dispatch_hooks(self._hooks, game, event, mouse_x, mouse_y):
            return
        if not game.world_loaded:
            return
        for spec in self._secondary_specs:
            panel = getattr(game.ui, spec.attr_name)
            if panel.selected is not None and panel.handle_wheel(game, mouse_x, mouse_y, event.y):
                return

# =========================================================================
# Сборка: единственное место, где виден полный состав контроллеров игрового
# поля и порядок и цепочек кликов, и Escape-стека.
# =========================================================================

class WorldLayer:

    def __init__(self, game):
        selection = SelectionService(game)
        grab = GrabController(game, selection)
        drawing = DrawingController(game)
        brush = BiomeBrushController(game)
        player_tools = PlayerToolController(game)
        tool_mode = ToolModeController(game, grab, drawing, brush, player_tools)
        placement = PlacementController(game)
        camera_drag = CameraDragController(game)
        hud = HudController(game)
        top_bar = TopBarController(game)
        side_panels = SidePanelController(game)
        world_click = WorldClickController(game, selection, grab)

        # ---------- Escape: сверху вниз - от самого "внутреннего" состояния к самому "внешнему" ----------
        escape = EscapeStack((
            grab.cancel_on_escape,
            drawing.cancel_road,
            drawing.cancel_landscape,
            tool_mode.cancel_on_escape,
            placement.cancel_on_escape,
            side_panels.close_popup_on_escape,
            selection.clear_creature,
            side_panels.clear_selection_on_escape,
            selection.clear_object,
            top_bar.close_menus_on_escape,
        ))

        # ---------- Клик ЛКМ по интерфейсу/миру: первый, кто "съел" клик, останавливает остальных ----------
        left_click_chain = (top_bar, side_panels, world_click)

        self._handlers = {
            pygame.MOUSEBUTTONDOWN: MouseDownRouter(
                game, hud, tool_mode, placement, camera_drag, left_click_chain).handle,
            pygame.MOUSEBUTTONUP: MouseUpRouter(game, camera_drag, brush, drawing).handle,
            pygame.MOUSEMOTION: MouseMotionRouter(
                game, brush, grab, camera_drag, drawing, placement).handle,
            pygame.MOUSEWHEEL: WheelController(game).handle,
            pygame.KEYDOWN: KeyboardController(game, escape).handle,
        }

    def handle(self, event):
        handler = self._handlers.get(event.type)
        if handler is not None:
            handler(event)