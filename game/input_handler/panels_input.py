"""Выбор объектов в мире и боковые панели: двойной клик (захват), одиночный клик
(выбор существа/объекта/вторичной панели), панель животного, режим размещения."""

import math
import time

import pygame

import settings
from player import Player
from objects import Wall, Fence
from game.race_registry import all_road_networks, all_secondary_panel_specs, creature_placement_lookup
from game.animal_registry import animal_classes, animal_placement_lookup, get_animal

from .common import in_world_area, world_point

# =========================================================================
# Клик мышью в мире: двойной клик берёт объект в руку, одиночный - выбирает.
# =========================================================================

class WorldClickController:

    def __init__(self, game, selection, grab):
        self.game = game
        self._selection = selection
        self._grab = grab
        self._road_specs = all_road_networks()

    def on_left_click(self, x, y):
        """Последнее звено цепочки: съедает любой клик, дошедший досюда."""
        game = self.game
        if game.editing_name:
            game.finish_name_editing()

        in_world = game.world_loaded and y > settings.UI_HEIGHT
        if in_world and not game.any_menu_open() and self._try_grab_by_double_click(x, y):
            return True

        game.close_all_menus()
        if in_world:
            self._select_at(*game.camera.world_from_screen(x, y))
        else:
            self._selection.clear()
        return True

    def _try_grab_by_double_click(self, x, y):
        game, player = self.game, self.game.player
        wx, wy = game.camera.world_from_screen(x, y)
        obj = game.object_manager.find_object_at(wx, wy)
        now = time.time()
        is_double = (
            obj is not None
            and obj is player.last_click_target
            and now - player.last_click_time < Player.DOUBLE_CLICK_TIME
            and math.hypot(x - player.last_click_pos[0], y - player.last_click_pos[1]) < Player.DOUBLE_CLICK_DIST
        )
        if not is_double:
            player.last_click_target = obj
            player.last_click_time = now
            player.last_click_pos = (x, y)
            return False

        player.last_click_target = None
        if self._is_grabbable(obj):
            self._grab.start_grab_object(obj)
        return True     # двойной клик по непереносимому тоже съедается

    def _is_grabbable(self, obj):
        if isinstance(obj, (Wall, Fence)) or getattr(obj, "is_locked", False):
            return False
        world = self.game.world
        return not any(obj in getattr(world, spec.road_collection) for spec in self._road_specs)

    def _select_at(self, wx, wy):
        game = self.game
        manager = game.object_manager

        creature = manager.find_creature_at(wx, wy)
        if creature is not None:
            self._selection.select_creature(creature)
            creature.on_selected_by_player()
            return

        obj = manager.find_object_at(wx, wy)
        if obj is None:
            self._selection.clear()
        elif game.ui.has_creature_panel(obj):
            self._selection.select_creature(obj)
        elif pygame.key.get_mods() & pygame.KMOD_CTRL:
            manager.delete_object(obj)
            self._selection.clear()
        else:
            panel_attr = manager.find_secondary_panel_target(obj)
            if panel_attr is not None:
                self._selection.select_in_secondary_panel(panel_attr, obj)
            else:
                self._selection.select_object(obj, (wx, wy))

# =========================================================================
# Правая панель существа, вторичные панели (кладбище и т.п.), панель животного.
# =========================================================================

class SidePanelController:

    def __init__(self, game):
        self.game = game
        self._secondary_specs = all_secondary_panel_specs()
        self._animal_classes = animal_classes()

    def on_left_click(self, x, y):
        if not self.game.world_loaded:
            return False
        return (self._click_creature_panel(x, y)
                or self._click_secondary_popup(x, y)
                or self._click_secondary_panel(x, y)
                or self._click_animal_panel(x, y))

    def _panels(self):
        return (getattr(self.game.ui, spec.attr_name) for spec in self._secondary_specs)

    def _click_creature_panel(self, x, y):
        game = self.game
        if game.right_panel_collapsed or game.selected_creature is None:
            return False
        return game.ui.creature_panel.handle_click(game, x, y)

    def _click_secondary_popup(self, x, y):
        for panel in self._panels():
            if getattr(panel, "popup_active", False):
                panel.handle_popup_click(self.game, x, y)
                return True
        return False

    def _click_secondary_panel(self, x, y):
        if self.game.right_panel_collapsed:
            return False
        for panel in self._panels():
            if panel.selected is not None and panel.panel_rect.collidepoint(x, y):
                panel.handle_click(self.game, x, y)
                return True
        return False

    def _click_animal_panel(self, x, y):
        game = self.game
        animal = game.selected_object
        if animal is None or not isinstance(animal, self._animal_classes):
            return False
        panel = game.ui.animal_panel
        if panel.favorite_star_rect.collidepoint(x, y):
            game.toggle_favorite(animal.id, entity=animal)
            return True
        for stat_key, rect in panel.stat_bar_rects.items():
            if rect.collidepoint(x, y):
                animal.adjust_stat(stat_key, -1 if x < rect.centerx else 1)
                return True
        return False

    # ---------- Шаги Escape-стека ----------

    def close_popup_on_escape(self):
        for panel in self._panels():
            if getattr(panel, "popup_active", False):
                return panel.close_popup_or_deselect(self.game)
        return False

    def clear_selection_on_escape(self):
        for panel in self._panels():
            if panel.selected is not None:
                return panel.close_popup_or_deselect(self.game)
        return False

# =========================================================================
# Режим размещения (кнопка меню -> курсор -> клик).
# =========================================================================

class PlacementController:

    def __init__(self, game):
        self.game = game
        self._creature_modes = creature_placement_lookup()
        self._animal_modes = animal_placement_lookup()
        self._hover_mode = None
        self._hover_check_pos = None

    def on_mouse_down(self, event):
        game = self.game
        if game.ui.exit_placement_btn.collidepoint(event.pos):
            game.object_manager.stop_placement()
            return
        if event.button != 1 or not in_world_area(event.pos[1]):
            return

        manager = game.object_manager
        wx, wy = world_point(game, event.pos)
        mode = game.placement_mode
        if mode in self._creature_modes:
            if manager.check_creature_placement_valid(wx, wy):
                _race_name, spawn_fn = self._creature_modes[mode]
                spawn_fn(manager, wx, wy, mode)
        elif mode in self._animal_modes:
            if manager.check_creature_placement_valid(wx, wy):
                animal_name, spawn_fn = self._animal_modes[mode]
                spawn_fn(manager, wx, wy, mode)
                self._mark_last_placed_touched(animal_name)
        elif manager.check_object_placement_valid(wx, wy):
            manager.place_object(wx, wy)

    def _mark_last_placed_touched(self, animal_name):
        """Игрок сам поставил животное - вне ДОС оно не должно исчезать."""
        collection = getattr(self.game.world, get_animal(animal_name).world_collection)
        if collection:
            collection[-1].player_touched = True

    def on_motion(self, event):
        game = self.game
        mode = game.placement_mode
        if not mode:
            self._hover_mode = None
            self._hover_check_pos = None
            return False

        if mode != self._hover_mode:
            self._hover_mode = mode
            self._hover_check_pos = None

        if in_world_area(event.pos[1]) and not game.ui.exit_placement_btn.collidepoint(event.pos):
            last = self._hover_check_pos
            if last is None or math.hypot(event.pos[0] - last[0],
                                          event.pos[1] - last[1]) >= settings.PLACEMENT_CHECK_MIN_MOVE:
                self._hover_check_pos = event.pos
                wx, wy = world_point(game, event.pos)
                game.placement_pos = (wx, wy)
                if mode in self._creature_modes or mode in self._animal_modes:
                    game.placement_valid = game.object_manager.check_creature_placement_valid(wx, wy)
                else:
                    game.placement_valid = game.object_manager.check_object_placement_valid(wx, wy)
        else:
            game.placement_pos = None
        return False

    def cancel_on_escape(self):
        if not self.game.placement_mode:
            return False
        self.game.object_manager.stop_placement()
        return True