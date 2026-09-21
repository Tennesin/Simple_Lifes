"""Все инструменты игрока в одном месте: режим-обёртка (модальность + крестик выхода),
захват объекта в руку, рисование линий (дороги/стены/заборы), кисть биомов,
и точечные инструменты над существами (погладить/ударить/схватить/избранное)."""

import math
from collections import namedtuple

import pygame

import settings
from creatures.all_needed.base_entity import LivingEntity
from creatures.all_needed.geometry import clamp
from game.object_manager.object_types import LANDSCAPE_AFFECTING_TYPES
from game.race_registry import all_road_networks
from objects import Fence, Wall
from player import Player

from .common import in_world_area, world_point

# =========================================================================
# Модальная обёртка режима инструмента: пока player.tool не None, клики не
# доходят до верхней панели. Выход - крестик (exit_placement_btn) или Escape.
# =========================================================================

class ToolModeController:

    def __init__(self, game, grab, drawing, brush, player_tools):
        self.game = game
        self._grab = grab
        self._drawing = drawing
        # ---------- Порядок: линии (дороги/стены) -> инструменты-существа -> кисть ----------
        self._handlers = (drawing, player_tools, brush)

    def on_mouse_down(self, event):
        game = self.game
        if self._grab.on_mouse_down(event):
            return True
        if event.button != 1 or not game.world_loaded or game.player.tool is None:
            return False
        if game.ui.exit_placement_btn.collidepoint(event.pos):
            self.cancel_tool()
            return True
        for handler in self._handlers:
            if handler.on_mouse_down(event):
                return True
        return False

    def cancel_tool(self):
        self._drawing.cancel_all()
        self.game.player.reset_tool()

    def cancel_on_escape(self):
        if self.game.player.tool is None:
            return False
        self.game.player.reset_tool()
        return True

# =========================================================================
# То, что игрок держит в руке: существо (инструмент "Схватить") или объект
# (двойной клик по миру - см. WorldClickController в panels_input.py).
# =========================================================================

class GrabController:

    def __init__(self, game, selection):
        self.game = game
        self._selection = selection

    def start_grab_object(self, obj):
        game, player = self.game, self.game.player
        if isinstance(obj, LivingEntity):
            obj.on_grab_start(game.world)
        player.grabbed_object = obj
        player.grabbed_object_valid = True      # объект пока стоит там, где стоял
        player.last_click_target = None
        game.close_all_menus()
        self._selection.clear()

    def on_mouse_down(self, event):
        if event.button != 1:
            return False
        game, player = self.game, self.game.player
        if player.grabbed_creature is not None:
            player.grabbed_creature.release_by_player()
            player.grabbed_creature = None
            if game.ui.exit_placement_btn.collidepoint(event.pos):
                player.reset_tool()
            return True
        if player.grabbed_object is not None:
            if player.grabbed_object_valid:
                self.release_object()
            return True         # положить в недопустимом месте нельзя, но клик съедается
        return False

    def release_object(self):
        game = self.game
        obj = game.player.grabbed_object
        game.player.grabbed_object = None

        if game.object_manager.resolve_obj_type_for_instance(obj) in LANDSCAPE_AFFECTING_TYPES:
            game.world.landscape_version += 1

        if game.ui.has_creature_panel(obj):
            # ---------- Контракт: True - существо само решило, что теперь выбрано ----------
            if not obj.on_grab_release(game):
                self._selection.select_creature(obj)
            return

        panel_attr = game.object_manager.find_secondary_panel_target(obj)
        if panel_attr is not None:
            self._selection.select_in_secondary_panel(panel_attr, obj)
        else:
            self._selection.select_object(obj, (obj.x, obj.y))

    def on_motion(self, event):
        player = self.game.player
        if player.grabbed_creature is not None:
            if event.pos[1] > settings.UI_HEIGHT:
                self._drag_creature(player.grabbed_creature, event.pos)
            return True
        if player.grabbed_object is not None:
            if event.pos[1] > settings.UI_HEIGHT:
                self._drag_object(player.grabbed_object, event.pos)
            return True
        return False

    def _drag_creature(self, creature, pos):
        camera = self.game.camera
        margin = settings.GRAB_WORLD_MARGIN_CREATURE
        wx, wy = camera.world_from_screen(*pos)
        creature.x = max(margin, min(wx, camera.world_w - margin))
        creature.y = max(margin, min(wy, camera.world_h - margin))

    def _drag_object(self, obj, pos):
        game, player = self.game, self.game.player
        camera = game.camera
        margin = settings.GRAB_WORLD_MARGIN_OBJECT
        wx, wy = camera.world_from_screen(*pos)
        wx = max(margin, min(wx, camera.world_w - margin))
        wy = max(margin, min(wy, camera.world_h - margin))

        obj_type = None if isinstance(obj, LivingEntity) else game.object_manager.resolve_obj_type_for_instance(obj)
        if obj_type is None:
            player.grabbed_object_valid = True
        else:
            player.grabbed_object_valid = game.object_manager.check_object_placement_valid(
                wx, wy, obj_type=obj_type, exclude=obj)
        obj.x, obj.y = wx, wy
        if hasattr(obj, "on_object_moved"):
            obj.on_object_moved(game)

    def cancel_on_escape(self):
        player = self.game.player
        if player.grabbed_creature is not None:
            player.grabbed_creature.release_by_player()
            player.grabbed_creature = None
            return True
        if player.grabbed_object is not None:
            if player.grabbed_object_valid:
                self.release_object()
            return True
        return False

# =========================================================================
# Рисование линий: дороги (любые зарегистрированные сети) и стены/заборы.
# =========================================================================

_LandscapeKind = namedtuple("_LandscapeKind", "kind cls world_attr")
_LANDSCAPE_TOOLS = {
    Player.TOOL_WALL: _LandscapeKind("wall", Wall, "walls"),
    Player.TOOL_FENCE: _LandscapeKind("fence", Fence, "fences"),
}
_LANDSCAPE_BY_KIND = {k.kind: k for k in _LANDSCAPE_TOOLS.values()}


def _drawing_attr(road_spec):
    return f"drawing_{road_spec.obj_type}"


class DrawingController:

    def __init__(self, game):
        self.game = game
        self._road_specs = all_road_networks()

    def _road_spec_for(self, tool):
        return next((s for s in self._road_specs if s.obj_type == tool), None)

    def on_mouse_down(self, event):
        tool = self.game.player.tool
        road_spec = self._road_spec_for(tool)
        landscape = _LANDSCAPE_TOOLS.get(tool)
        if road_spec is None and landscape is None:
            return False
        if in_world_area(event.pos[1]):
            if road_spec is not None:
                self._begin_road(road_spec, event.pos)
            else:
                self._begin_landscape(landscape, event.pos)
        return True

    def _begin_road(self, spec, pos):
        game = self.game
        wx, wy = world_point(game, pos, clamp=True)
        wx, wy = game.object_manager.snap_to_existing(wx, wy, spec.obj_type)
        road = game.object_manager.create_road_instance(spec.obj_type)
        road.add_point(wx, wy)
        setattr(game.player, _drawing_attr(spec), road)

    def _begin_landscape(self, landscape, pos):
        game = self.game
        wx, wy = world_point(game, pos, clamp=True)
        wx, wy = game.object_manager.snap_to_existing(wx, wy, landscape.kind)
        obj = landscape.cls()
        obj.add_point(wx, wy)
        game.player.drawing_landscape = obj
        game.player.landscape_type = landscape.kind

    def on_motion(self, event):
        player = self.game.player
        if not event.buttons[0] or not in_world_area(event.pos[1]):
            return False
        wx, wy = world_point(self.game, event.pos, clamp=True)
        for spec in self._road_specs:
            road = getattr(player, _drawing_attr(spec), None)
            if road is not None:
                self._extend(road, wx, wy, player.road_min_point_dist)
        if player.drawing_landscape is not None:
            self._extend(player.drawing_landscape, wx, wy, player.landscape_min_point_dist)
        return False

    @staticmethod
    def _extend(line, wx, wy, min_dist):
        last_x, last_y = line.points[-1]
        if math.hypot(wx - last_x, wy - last_y) >= min_dist:
            line.add_point(wx, wy)

    def on_mouse_up(self, event):
        if event.button != 1:
            return
        game, player = self.game, self.game.player
        for spec in self._road_specs:
            road = getattr(player, _drawing_attr(spec), None)
            if road is not None:
                game.object_manager.finalize_drawn_road(spec.obj_type, road)
                setattr(player, _drawing_attr(spec), None)

        line = player.drawing_landscape
        if line is not None:
            if len(line.points) >= 2:
                landscape = _LANDSCAPE_BY_KIND[player.landscape_type]
                last_x, last_y = line.points[-1]
                line.points[-1] = game.object_manager.snap_to_existing(
                    last_x, last_y, landscape.kind, self_points=line.points[:-1])
                getattr(game.world, landscape.world_attr).append(line)
                game.world.landscape_version += 1
            player.drawing_landscape = None
            player.landscape_type = None

    def cancel_road(self):
        """Шаг Escape-стека: True, если какая-то дорога рисовалась."""
        player = self.game.player
        for spec in self._road_specs:
            if getattr(player, _drawing_attr(spec), None) is not None:
                setattr(player, _drawing_attr(spec), None)
                return True
        return False

    def cancel_landscape(self):
        player = self.game.player
        if player.drawing_landscape is None:
            return False
        player.drawing_landscape = None
        player.landscape_type = None
        return True

    def cancel_all(self):
        self.cancel_road()
        self.cancel_landscape()

# =========================================================================
# Кисть биомов: покраска мазком и Shift+движение мыши для смены радиуса.
# =========================================================================

BIOME_TOOL_MAP = {
    Player.TOOL_BIOME_PLAINS: settings.BIOME_PLAINS,
    Player.TOOL_BIOME_DESERT: settings.BIOME_DESERT,
    Player.TOOL_BIOME_RIVER: settings.BIOME_RIVER,
    Player.TOOL_BIOME_SEA: settings.BIOME_SEA,
}

class BiomeBrushController:

    def __init__(self, game):
        self.game = game
        self._last_pos = None       # предыдущая точка мазка - для интерполяции без "дырок"

    def _is_active(self):
        return self.game.player.tool in BIOME_TOOL_MAP

    @staticmethod
    def _shift_held():
        return bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)

    def on_mouse_down(self, event):
        if not self._is_active():
            return False
        if in_world_area(event.pos[1]) and not self._shift_held():
            self._paint(event.pos)
        return True

    def on_motion(self, event):
        if not self._is_active():
            return False
        player = self.game.player
        if self._shift_held():
            self._adjust_radius(event.pos[1])
            return True                     # пока меняем радиус - остальное не обрабатываем
        player.brush_adjust_start_y = None
        player.brush_adjust_start_radius = None
        if (event.buttons[0] and in_world_area(event.pos[1])
                and not self.game.ui.exit_placement_btn.collidepoint(event.pos)):
            self._paint(event.pos)
        return False

    def reset_stroke(self):
        self._last_pos = None

    def _adjust_radius(self, mouse_y):
        player = self.game.player
        if player.brush_adjust_start_y is None:
            player.brush_adjust_start_y = mouse_y
            player.brush_adjust_start_radius = player.brush_radius
            return
        delta = player.brush_adjust_start_y - mouse_y
        radius = player.brush_adjust_start_radius + delta * settings.BIOME_BRUSH_SENSITIVITY
        player.brush_radius = clamp(radius, settings.BIOME_BRUSH_MIN_RADIUS, settings.BIOME_BRUSH_MAX_RADIUS)

    def _paint(self, pos):
        game = self.game
        wx, wy = world_point(game, pos)
        biome_type = BIOME_TOOL_MAP[game.player.tool]
        radius = game.player.brush_radius
        last = self._last_pos
        if last is None:
            game.object_manager.paint_biome(wx, wy, biome_type, radius)
        else:
            dist = math.hypot(wx - last[0], wy - last[1])
            step = max(settings.BIOME_BRUSH_MIN_STEP, radius * settings.BIOME_BRUSH_STEP_RADIUS_RATIO)
            steps = max(1, int(dist / step))
            for i in range(1, steps + 1):
                t = i / steps
                game.object_manager.paint_biome(
                    last[0] + (wx - last[0]) * t, last[1] + (wy - last[1]) * t,
                    biome_type, radius, bump_version=False)
            game.world.landscape_version += 1       # одна версия на мазок, а не на каждый шаг
        self._last_pos = (wx, wy)

# =========================================================================
# Точечные инструменты игрока над существами: погладить, ударить, схватить,
# сделать избранным.
# =========================================================================

class PlayerToolController:

    def __init__(self, game):
        self.game = game
        self._actions = {
            Player.TOOL_PET: self._pet,
            Player.TOOL_HIT: self._hit,
            Player.TOOL_GRAB: self._grab,
            Player.TOOL_FAVORITE: self._favorite,
        }

    def on_mouse_down(self, event):
        action = self._actions.get(self.game.player.tool)
        if action is None:
            return False
        if in_world_area(event.pos[1]):
            action(*world_point(self.game, event.pos))
        return True

    def _living_creature_at(self, wx, wy):
        creature = self.game.object_manager.find_creature_at(wx, wy)
        return creature if creature is not None and not creature.is_dead else None

    def _pet(self, wx, wy):
        creature = self._living_creature_at(wx, wy)
        if creature is not None:
            creature.receive_pet()

    def _hit(self, wx, wy):
        creature = self._living_creature_at(wx, wy)
        if creature is not None:
            creature.receive_hit()

    def _grab(self, wx, wy):
        creature = self._living_creature_at(wx, wy)
        if creature is not None:
            creature.grab_by_player()
            self.game.player.grabbed_creature = creature

    def _favorite(self, wx, wy):
        entity = self.game.object_manager.find_favorite_target_at(wx, wy)
        if entity is not None:
            self.game.toggle_favorite(entity.id, entity=entity)