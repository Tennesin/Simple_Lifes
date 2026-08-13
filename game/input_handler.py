import time
import math
import pygame

from player import Player
from objects import Road, Wall, Fence
from settings import *
from game.race_registry import creature_placement_lookup, all_secondary_panel_specs, all_road_networks
from creatures.all_needed.base_entity import LivingEntity

BIOME_TOOL_MAP = {
    Player.TOOL_BIOME_PLAINS: BIOME_PLAINS,
    Player.TOOL_BIOME_DESERT: BIOME_DESERT,
    Player.TOOL_BIOME_RIVER: BIOME_RIVER,
    Player.TOOL_BIOME_SEA: BIOME_SEA,
}

def handle_pet_hit_grab_click(game, ui, mouse_x, mouse_y):
    if game.player.tool not in (Player.TOOL_PET, Player.TOOL_HIT, Player.TOOL_GRAB):
        return False

    if ui.exit_placement_btn.collidepoint(mouse_x, mouse_y):
        game.player.reset_tool()
        return True

    if mouse_y > UI_HEIGHT:
        wx, wy = game.camera.world_from_screen(mouse_x, mouse_y)
        creature_hit = game.object_manager.find_creature_at(wx, wy)
        if creature_hit and not creature_hit.is_dead:
            if game.player.tool == Player.TOOL_PET:
                creature_hit.player_reactions.pet()
            elif game.player.tool == Player.TOOL_HIT:
                creature_hit.player_reactions.hit()
            elif game.player.tool == Player.TOOL_GRAB:
                creature_hit.player_reactions.start_grab()
                game.player.grabbed_creature = creature_hit
    return True

# =========================================================================
# Домен: клавиатура - редактирование имён (существо/кладбище) и общие
# горячие клавиши (пауза, миникарта, удаление объекта, Escape-стек)
# =========================================================================

class _KeyboardMixin:

    def _handle_keydown(self, event):
        game = self.game
        if game.editing_name:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                game.finish_name_editing()
            elif event.key == pygame.K_ESCAPE:
                game.editing_name = False
                game.name_edit_buffer = ""
            elif event.key == pygame.K_BACKSPACE:
                game.name_edit_buffer = game.name_edit_buffer[:-1]
            else:
                if event.unicode and event.unicode.isprintable() and len(game.name_edit_buffer) < 24:
                    game.name_edit_buffer += event.unicode
            return

        for spec in all_secondary_panel_specs():
            panel = getattr(game.ui, spec.attr_name)
            if getattr(panel, "text_editing", False):
                panel.handle_keydown(event)
                return

        if event.key == pygame.K_ESCAPE:
            self._handle_escape()
        elif event.key == pygame.K_SPACE:
            game.toggle_pause()
        elif event.key == pygame.K_TAB:
            game.show_minimap = not game.show_minimap
        elif event.key == pygame.K_DELETE:
            if game.selected_object:
                game.object_manager.delete_object(game.selected_object)
                game.selected_object = None

    def _handle_escape(self):
        game = self.game
        if game.player.grabbed_creature is not None:
            game.player.grabbed_creature.player_reactions.finish_grab()
            game.player.grabbed_creature = None
        elif game.player.grabbed_object is not None:
            obj = game.player.grabbed_object
            game.player.grabbed_object = None
            self._release_grabbed_object(obj)
        elif self._reset_active_road_drawing():
            pass
        elif game.player.drawing_landscape is not None:
            game.player.drawing_landscape = None
            game.player.landscape_type = None
        elif game.player.tool is not None:
            game.player.reset_tool()
        elif game.placement_mode:
            game.object_manager.stop_placement()
        elif self._close_active_secondary_popup():
            pass
        elif game.selected_creature:
            game.selected_creature = None
        elif self._clear_active_secondary_selection():
            pass
        elif game.selected_object:
            game.selected_object = None
        else:
            game.close_all_menus()

    def _reset_active_road_drawing(self):
        game = self.game
        for spec in all_road_networks():
            attr = f"drawing_{spec.obj_type}"
            if getattr(game.player, attr, None) is not None:
                setattr(game.player, attr, None)
                return True
        return False

    def _close_active_secondary_popup(self):
        game = self.game
        for spec in all_secondary_panel_specs():
            panel = getattr(game.ui, spec.attr_name)
            if getattr(panel, "popup_active", False):
                return panel.close_popup_or_deselect(game)
        return False

    def _clear_active_secondary_selection(self):
        game = self.game
        for spec in all_secondary_panel_specs():
            panel = getattr(game.ui, spec.attr_name)
            if panel.selected is not None:
                return panel.close_popup_or_deselect(game)
        return False

# =========================================================================
# Домен: экран критической ошибки - единственная кнопка "Сохранить лог"
# =========================================================================

class _CrashScreenMixin:

    def _handle_crash_event(self, event):
        game = self.game
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if (not game.crash_log_written
                    and game.crash_log_btn_rect.collidepoint(event.pos)):
                game.write_crash_log()

# =========================================================================
# Домен: кисть биома - интерполяция мазка между предыдущей и текущей
# точкой курсора, чтобы не оставалось "дырок" при быстром движении мыши
# =========================================================================

class _BiomePaintState:
    def __init__(self):
        self.last_pos = None

    def reset(self):
        self.last_pos = None


class _PlacementHoverState:
    def __init__(self):
        self.mode = None
        self.check_pos = None


class _BiomePaintingMixin:

    def _paint_biome_stroke(self, wx, wy, biome_type, radius):
        game = self.game
        last = self.biome_paint.last_pos
        if last is None:
            game.object_manager.paint_biome(wx, wy, biome_type, radius)
        else:
            dist = math.hypot(wx - last[0], wy - last[1])
            step = max(4.0, radius * 0.5)
            steps = max(1, int(dist / step))
            for i in range(1, steps + 1):
                t = i / steps
                ix = last[0] + (wx - last[0]) * t
                iy = last[1] + (wy - last[1]) * t
                game.object_manager.paint_biome(ix, iy, biome_type, radius, bump_version=False)
            game.world.landscape_version += 1
        self.biome_paint.last_pos = (wx, wy)

# =========================================================================
# Домен: выпадающие подменю верхней панели
# =========================================================================

class _MenuMixin:

    def _toggle_menu(self, menu_name):
        game = self.game
        was_open = getattr(game, menu_name)
        game.close_all_menus()
        setattr(game, menu_name, not was_open)

    def _handle_landscape_menu_click(self, mouse_x, mouse_y):
        game = self.game
        ui = game.ui
        pos = (mouse_x, mouse_y)
        if ui.btn_wall.collidepoint(pos):
            game.activate_player_tool(Player.TOOL_WALL)
        elif ui.btn_fence.collidepoint(pos):
            game.activate_player_tool(Player.TOOL_FENCE)
        elif ui.btn_biome_plains.collidepoint(pos):
            game.activate_player_tool(Player.TOOL_BIOME_PLAINS)
        elif ui.btn_biome_desert.collidepoint(pos):
            game.activate_player_tool(Player.TOOL_BIOME_DESERT)
        elif ui.btn_biome_river.collidepoint(pos):
            game.activate_player_tool(Player.TOOL_BIOME_RIVER)
        elif ui.btn_biome_sea.collidepoint(pos):
            game.activate_player_tool(Player.TOOL_BIOME_SEA)
        game.show_landscape_menu = False

    def _handle_objects_menu_click(self, mouse_x, mouse_y):
        game = self.game
        for obj_type, btn in game.ui.object_placement_buttons.items():
            if btn.collidepoint(mouse_x, mouse_y):
                game.object_manager.start_placement(obj_type)
                return
        for obj_type, btn in game.ui.road_tool_buttons.items():
            if btn.collidepoint(mouse_x, mouse_y):
                game.activate_player_tool(obj_type)
                game.show_objects_menu = False
                return
        game.show_objects_menu = False

    def _handle_nature_menu_click(self, mouse_x, mouse_y):
        game = self.game
        ui = game.ui
        pos = (mouse_x, mouse_y)
        button_map = (
            (ui.btn_fruit, "fruit"),
            (ui.btn_bush, "bush"),
            (ui.btn_water, "water"),
            (ui.btn_tree, "tree"),
            (ui.btn_stone, "stone"),
        )
        for btn, obj_type in button_map:
            if btn.collidepoint(pos):
                game.object_manager.start_placement(obj_type)
                return
        game.show_nature_menu = False

    def _handle_player_menu_click(self, mouse_x, mouse_y):
        game = self.game
        ui = game.ui
        pos = (mouse_x, mouse_y)
        for tool_value, btn in ui.player_tool_buttons.items():
            if btn.collidepoint(pos):
                game.activate_player_tool(tool_value)
                break
        game.show_player_menu = False

# =========================================================================
# Домен: клик мышью (кнопка вниз)
# =========================================================================

class _MouseDownMixin:

    def _handle_mouse_down(self, event):
        game = self.game
        mouse_x, mouse_y = event.pos

        if self._handle_collapse_handle_click(event, mouse_x, mouse_y):
            return
        if self._handle_minimap_click(event, mouse_x, mouse_y):
            return
        if self._handle_active_action_click(event, mouse_x, mouse_y):
            return
        if game.placement_mode:
            self._handle_placement_click(event, mouse_x, mouse_y)
            return

        if event.button == 3 and game.world_loaded:
            game.dragging = True
            game.drag_start = event.pos
        elif event.button == 1:
            self._handle_left_click(mouse_x, mouse_y)

    def _handle_minimap_click(self, event, mouse_x, mouse_y):
        game = self.game
        if not (game.show_minimap and game.world_loaded
                and game.ui.minimap.rect.collidepoint(mouse_x, mouse_y)):
            return False
        if event.button == 1 and game.player.drawing_road is None:
            rect = game.ui.minimap.rect
            rel_x = (mouse_x - rect.x) / rect.width
            rel_y = (mouse_y - rect.y) / rect.height
            wx = rel_x * WORLD_WIDTH
            wy = rel_y * WORLD_HEIGHT
            game.camera.center_on(wx, wy)
        return True

    def _handle_active_action_click(self, event, mouse_x, mouse_y):
        game = self.game

        if event.button == 1 and game.player.grabbed_creature is not None:
            game.player.grabbed_creature.player_reactions.finish_grab()
            game.player.grabbed_creature = None
            if game.ui.exit_placement_btn.collidepoint(mouse_x, mouse_y):
                game.player.reset_tool()
            return True

        if event.button == 1 and game.player.grabbed_object is not None:
            obj = game.player.grabbed_object
            game.player.grabbed_object = None
            self._release_grabbed_object(obj)
            return True

        if event.button == 1 and game.world_loaded and self._handle_road_tool_click(event, mouse_x, mouse_y):
            return True

        if event.button == 1 and game.world_loaded and game.player.tool in (Player.TOOL_WALL, Player.TOOL_FENCE):
            if game.ui.exit_placement_btn.collidepoint(mouse_x, mouse_y):
                game.player.drawing_landscape = None
                game.player.landscape_type = None
                game.player.reset_tool()
            elif mouse_y > UI_HEIGHT:
                wx, wy = game.camera.world_from_screen(mouse_x, mouse_y)
                wx = max(0, min(wx, game.camera.world_w))
                wy = max(0, min(wy, game.camera.world_h))
                landscape_type = "wall" if game.player.tool == Player.TOOL_WALL else "fence"
                wx, wy = game.object_manager.snap_to_existing(wx, wy, landscape_type)
                obj = Wall() if landscape_type == "wall" else Fence()
                obj.add_point(wx, wy)
                game.player.drawing_landscape = obj
                game.player.landscape_type = landscape_type
            return True

        if event.button == 1 and game.world_loaded and handle_pet_hit_grab_click(
                game, game.ui, mouse_x, mouse_y):
            return True

        if event.button == 1 and game.world_loaded and game.player.tool in BIOME_TOOL_MAP:
            if game.ui.exit_placement_btn.collidepoint(mouse_x, mouse_y):
                game.player.reset_tool()
                return True
            mods = pygame.key.get_mods()
            if mouse_y > UI_HEIGHT and not (mods & pygame.KMOD_SHIFT):
                wx, wy = game.camera.world_from_screen(mouse_x, mouse_y)
                biome_type = BIOME_TOOL_MAP[game.player.tool]
                game.object_manager.paint_biome(wx, wy, biome_type, game.player.brush_radius)
                self.biome_paint.last_pos = (wx, wy)
            return True

        return False

	def _is_road_object(self, obj):
    	game = self.game
    	return any(obj in getattr(game.world, spec.road_collection) for spec in all_road_networks())

    def _handle_road_tool_click(self, event, mouse_x, mouse_y):
        game = self.game
        for spec in all_road_networks():
            if game.player.tool != spec.obj_type:
                continue
            attr = f"drawing_{spec.obj_type}"
            if game.ui.exit_placement_btn.collidepoint(mouse_x, mouse_y):
                setattr(game.player, attr, None)
                game.player.reset_tool()
            elif mouse_y > UI_HEIGHT:
                wx, wy = game.camera.world_from_screen(mouse_x, mouse_y)
                wx = max(0, min(wx, game.camera.world_w))
                wy = max(0, min(wy, game.camera.world_h))
                wx, wy = game.object_manager.snap_to_existing(wx, wy, spec.obj_type)
                road = game.object_manager.create_road_instance(spec.obj_type)
                road.add_point(wx, wy)
                setattr(game.player, attr, road)
            return True
        return False

    def _handle_stat_bar_click(self, mouse_x, mouse_y):
        game = self.game
        creature = game.selected_creature
        if creature is None:
            return False
        for stat_key, rect in game.ui.stat_bar_rects.items():
            if rect.collidepoint(mouse_x, mouse_y):
                direction = -1 if mouse_x < rect.centerx else 1
                creature.player_reactions.adjust_stat(stat_key, direction)
                return True
        return False

    def _handle_secondary_popup_click(self, mouse_x, mouse_y):
        game = self.game
        for spec in all_secondary_panel_specs():
            panel = getattr(game.ui, spec.attr_name)
            if not getattr(panel, "popup_active", False):
                continue
            panel.handle_popup_click(game, mouse_x, mouse_y)
            return True
        return False

    def _handle_secondary_panel_click(self, mouse_x, mouse_y):
        game = self.game
        for spec in all_secondary_panel_specs():
            panel = getattr(game.ui, spec.attr_name)
            if panel.selected is None:
                continue
            if panel.panel_rect.collidepoint(mouse_x, mouse_y):
                panel.handle_click(game, mouse_x, mouse_y)
                return True
        return False

    def _handle_collapse_handle_click(self, event, mouse_x, mouse_y):
        game = self.game
        if event.button != 1 or not game.world_loaded:
            return False
        any_secondary_selected = any(
            getattr(game.ui, spec.attr_name).selected is not None
            for spec in all_secondary_panel_specs()
        )
        if not (game.selected_creature or any_secondary_selected):
            return False
        if game.ui.collapse_handle_rect.collidepoint(mouse_x, mouse_y):
            game.right_panel_collapsed = not game.right_panel_collapsed
            return True
        return False

    def _handle_placement_click(self, event, mouse_x, mouse_y):
        game = self.game
        if game.ui.exit_placement_btn.collidepoint(mouse_x, mouse_y):
            game.object_manager.stop_placement()
            return
        if event.button == 1 and mouse_y > UI_HEIGHT:
            wx, wy = game.camera.world_from_screen(mouse_x, mouse_y)
            placement_lookup = creature_placement_lookup()
            if game.placement_mode in placement_lookup:
                if game.object_manager.check_creature_placement_valid(wx, wy):
                    _race_name, spawn_fn = placement_lookup[game.placement_mode]
                    spawn_fn(game.object_manager, wx, wy, game.placement_mode)
            else:
                if game.object_manager.check_object_placement_valid(wx, wy):
                    game.object_manager.place_object(wx, wy)

    def _handle_left_click(self, mouse_x, mouse_y):
        game = self.game
        ui = game.ui

        if ui.btn_game.collidepoint(mouse_x, mouse_y):
            self._toggle_menu("show_game_menu")

        elif ui.btn_settings.collidepoint(mouse_x, mouse_y):
            game.close_all_menus()
            game.open_settings_screen()

        elif game.world_loaded and ui.btn_landscape.collidepoint(mouse_x, mouse_y):
            self._toggle_menu("show_landscape_menu")

        elif game.world_loaded and ui.btn_lifes.collidepoint(mouse_x, mouse_y):
            self._toggle_menu("show_lifes_menu")

        elif game.world_loaded and ui.btn_objects.collidepoint(mouse_x, mouse_y):
            self._toggle_menu("show_objects_menu")

        elif game.world_loaded and ui.btn_nature.collidepoint(mouse_x, mouse_y):
            self._toggle_menu("show_nature_menu")

        elif game.world_loaded and ui.btn_player.collidepoint(mouse_x, mouse_y):
            self._toggle_menu("show_player_menu")

        elif game.show_game_menu and ui.btn_create_world.collidepoint(mouse_x, mouse_y):
            game.world_manager.open_create_screen()

        elif game.show_game_menu and ui.btn_load_world.collidepoint(mouse_x, mouse_y):
            game.world_manager.open_load_screen()

        elif game.world_loaded and game.show_game_menu and ui.btn_pause.collidepoint(mouse_x, mouse_y):
            game.toggle_pause()
            game.show_game_menu = False

        elif game.world_loaded and game.show_game_menu and ui.btn_save_world.collidepoint(mouse_x, mouse_y):
            game.world_manager.save_world_manual()

        elif game.show_game_menu and ui.btn_exit.collidepoint(mouse_x, mouse_y):
            game.request_exit()
            game.show_game_menu = False

        elif game.world_loaded and game.show_landscape_menu:
            self._handle_landscape_menu_click(mouse_x, mouse_y)

        elif game.world_loaded and game.show_lifes_menu and self._handle_lifes_menu_click(mouse_x, mouse_y):
            pass

        elif game.world_loaded and game.show_objects_menu:
            self._handle_objects_menu_click(mouse_x, mouse_y)

        elif game.world_loaded and game.show_nature_menu:
            self._handle_nature_menu_click(mouse_x, mouse_y)

        elif game.world_loaded and game.show_player_menu:
            self._handle_player_menu_click(mouse_x, mouse_y)

        elif (game.world_loaded and not game.right_panel_collapsed and game.selected_creature
              and not game.selected_creature.is_dead and ui.btn_creature_pet.collidepoint(mouse_x, mouse_y)):
            game.selected_creature.player_reactions.pet()

        elif (game.world_loaded and not game.right_panel_collapsed and game.selected_creature
              and not game.selected_creature.is_dead and ui.btn_creature_hit.collidepoint(mouse_x, mouse_y)):
            game.selected_creature.player_reactions.hit()

        elif (game.world_loaded and not game.right_panel_collapsed and game.selected_creature
              and not game.selected_creature.is_dead and self._handle_stat_bar_click(mouse_x, mouse_y)):
            pass

        elif (game.world_loaded and not game.right_panel_collapsed and game.selected_creature
              and ui.info_panel_rect.collidepoint(mouse_x, mouse_y)):
            panel = ui.creature_panel
            if ui.name_field_rect.collidepoint(mouse_x, mouse_y):
                game.start_name_editing()
            elif panel.relationships_header_rect and panel.relationships_header_rect.collidepoint(mouse_x, mouse_y):
                game.finish_name_editing()
                panel.show_relationships_section = not panel.show_relationships_section
                panel.relationships_scroll_offset = 0
            elif panel.psyche_header_rect and panel.psyche_header_rect.collidepoint(mouse_x, mouse_y):
                game.finish_name_editing()
                panel.show_psyche_section = not panel.show_psyche_section
            else:
                game.finish_name_editing()


        elif (game.world_loaded and not game.right_panel_collapsed and game.selected_creature
              and ui.creature_panel.show_psyche_section and ui.creature_panel.psyche_panel_rect
              and ui.creature_panel.psyche_panel_rect.collidepoint(mouse_x, mouse_y)):
            self._handle_stat_bar_click(mouse_x, mouse_y)


        elif game.world_loaded and self._handle_secondary_popup_click(mouse_x, mouse_y):
            pass
        elif game.world_loaded and not game.right_panel_collapsed and self._handle_secondary_panel_click(mouse_x, mouse_y):
            pass
        else:
            self._handle_world_click(mouse_x, mouse_y)

    def _handle_world_click(self, mouse_x, mouse_y):
        game = self.game

        if game.editing_name:
            game.finish_name_editing()

        if (game.world_loaded and mouse_y > UI_HEIGHT and not game.show_game_menu
                and not game.show_lifes_menu and not game.show_objects_menu
                and not game.show_player_menu):
            now = time.time()
            wx, wy = game.camera.world_from_screen(mouse_x, mouse_y)
            obj_here = game.object_manager.find_object_at(wx, wy)
            is_double_click = (
                    obj_here is not None and
                    obj_here is game.player.last_click_target and
                    now - game.player.last_click_time < Player.DOUBLE_CLICK_TIME and
                    math.hypot(mouse_x - game.player.last_click_pos[0],
                               mouse_y - game.player.last_click_pos[1]) < Player.DOUBLE_CLICK_DIST
            )
            if is_double_click:
                if obj_here and not isinstance(obj_here, (Wall, Fence)) and not self._is_road_object(obj_here):
                    if isinstance(obj_here, LivingEntity):
                        obj_here.on_grab_start(game.world)
                    game.player.grabbed_object = obj_here
                    game.player.last_click_target = None
                    game.close_all_menus()
                    game.clear_secondary_selections()
                    game.selected_object = None
                    game.selected_object_click_pos = None
                    game.selected_creature = None
                    return
                else:
                    game.player.last_click_target = None
                    return
            else:
                game.player.last_click_target = obj_here
                game.player.last_click_time = now
                game.player.last_click_pos = (mouse_x, mouse_y)

        game.close_all_menus()
        if game.world_loaded and mouse_y > UI_HEIGHT:
            wx, wy = game.camera.world_from_screen(mouse_x, mouse_y)
            mods = pygame.key.get_mods()
            ctrl_held = bool(mods & pygame.KMOD_CTRL)

            creature_hit = game.object_manager.find_creature_at(wx, wy)
            if creature_hit:
                game.selected_object = None
                game.selected_creature = creature_hit
                creature_hit.player_reactions.register_touch()
            else:
                obj_hit = game.object_manager.find_object_at(wx, wy)
                if obj_hit:
                    if isinstance(obj_hit, LivingEntity):
                        game.selected_creature = obj_hit
                        game.selected_object = None
                        game.clear_secondary_selections()
                    elif ctrl_held:
                        game.object_manager.delete_object(obj_hit)
                        game.selected_object = None
                        game.clear_secondary_selections()
                    else:
                        panel_attr = game.object_manager.find_secondary_panel_target(obj_hit)
                        if panel_attr is not None:
                            game.selected_creature = None
                            game.selected_object = None
                            panel = getattr(game.ui, panel_attr)
                            panel.clear(game)
                            panel.selected = obj_hit
                        else:
                            game.selected_creature = None
                            game.clear_secondary_selections()
                            game.selected_object = obj_hit
                            game.selected_object_click_pos = (wx, wy)
                else:
                    game.selected_creature = None
                    game.selected_object = None
                    game.clear_secondary_selections()
        else:
            game.selected_creature = None
            game.selected_object = None

    def _handle_lifes_menu_click(self, mouse_x, mouse_y):
        game = self.game
        for placement_mode, btn in game.ui.creature_placement_buttons.items():
            if btn.collidepoint(mouse_x, mouse_y):
                game.object_manager.start_placement(placement_mode)
                return True
        return False

    def _release_grabbed_object(self, obj):
        game = self.game
        if isinstance(obj, LivingEntity):
            if not obj.on_grab_release(game):
                game.selected_object = None
                game.clear_secondary_selections()
                game.selected_creature = obj
            return

        panel_attr = game.object_manager.find_secondary_panel_target(obj)
        if panel_attr is not None:
            panel = getattr(game.ui, panel_attr)
            panel.clear(game)
            panel.selected = obj
            game.selected_object = None
        else:
            game.selected_object = obj
            game.selected_object_click_pos = (obj.x, obj.y)
            game.clear_secondary_selections()

# =========================================================================
# Домен: клик мышью (кнопка вверх)
# =========================================================================

class _MouseUpMixin:

    def _handle_mouse_up(self, event):
        game = self.game
        if event.button == 3:
            game.dragging = False
        if event.button == 1:
            self.biome_paint.reset()

        if event.button == 1:
            for spec in all_road_networks():
                attr = f"drawing_{spec.obj_type}"
                drawing = getattr(game.player, attr, None)
                if drawing is not None:
                    game.object_manager.finalize_drawn_road(spec.obj_type, drawing)
                    setattr(game.player, attr, None)

        if event.button == 1 and game.player.drawing_landscape is not None:
            obj = game.player.drawing_landscape
            if len(obj.points) >= 2:
                last_x, last_y = obj.points[-1]
                obj.points[-1] = game.object_manager.snap_to_existing(
                    last_x, last_y, game.player.landscape_type, self_points=obj.points[:-1])
                if game.player.landscape_type == "wall":
                    game.world.walls.append(obj)
                else:
                    game.world.fences.append(obj)
                game.world.landscape_version += 1
            game.player.drawing_landscape = None
            game.player.landscape_type = None


# =========================================================================
# Домен: движение мыши
# =========================================================================

class _MouseMotionMixin:

    def _handle_mouse_motion(self, event):
        game = self.game
        mouse_x, mouse_y = event.pos

        if game.player.tool in BIOME_TOOL_MAP:
            mods = pygame.key.get_mods()
            shift_held = bool(mods & pygame.KMOD_SHIFT)

            if shift_held:
                if game.player.brush_adjust_start_y is None:
                    game.player.brush_adjust_start_y = mouse_y
                    game.player.brush_adjust_start_radius = game.player.brush_radius
                else:
                    delta = game.player.brush_adjust_start_y - mouse_y
                    new_radius = game.player.brush_adjust_start_radius + delta * BIOME_BRUSH_SENSITIVITY
                    game.player.brush_radius = max(BIOME_BRUSH_MIN_RADIUS,
                                                   min(BIOME_BRUSH_MAX_RADIUS, new_radius))
                return
            else:
                game.player.brush_adjust_start_y = None
                game.player.brush_adjust_start_radius = None

            if pygame.mouse.get_pressed()[0]:
                if mouse_y > UI_HEIGHT and not game.ui.exit_placement_btn.collidepoint(mouse_x, mouse_y):
                    wx, wy = game.camera.world_from_screen(mouse_x, mouse_y)
                    biome_type = BIOME_TOOL_MAP[game.player.tool]
                    game.object_manager.paint_biome(wx, wy, biome_type, game.player.brush_radius)

        if game.player.grabbed_creature is not None:
            if mouse_y > UI_HEIGHT:
                wx, wy = game.camera.world_from_screen(mouse_x, mouse_y)
                creature = game.player.grabbed_creature
                creature.x = max(15, min(wx, game.camera.world_w - 15))
                creature.y = max(15, min(wy, game.camera.world_h - 15))
            return

        if game.player.grabbed_object is not None:
            if mouse_y > UI_HEIGHT:
                wx, wy = game.camera.world_from_screen(mouse_x, mouse_y)
                obj = game.player.grabbed_object
                obj.x = max(10, min(wx, game.camera.world_w - 10))
                obj.y = max(10, min(wy, game.camera.world_h - 10))
            return

        if game.dragging and not game.placement_mode:
            dx = event.pos[0] - game.drag_start[0]
            dy = event.pos[1] - game.drag_start[1]
            game.camera.move(-dx, -dy)
            game.drag_start = event.pos

        if pygame.mouse.get_pressed()[0] and mouse_y > UI_HEIGHT:
            wx, wy = game.camera.world_from_screen(mouse_x, mouse_y)
            wx = max(0, min(wx, game.camera.world_w))
            wy = max(0, min(wy, game.camera.world_h))
            for spec in all_road_networks():
                attr = f"drawing_{spec.obj_type}"
                drawing = getattr(game.player, attr, None)
                if drawing is None:
                    continue
                last_x, last_y = drawing.points[-1]
                if math.hypot(wx - last_x, wy - last_y) >= game.player.road_min_point_dist:
                    drawing.add_point(wx, wy)

        if game.player.drawing_landscape is not None and pygame.mouse.get_pressed()[0]:
            if mouse_y > UI_HEIGHT:
                wx, wy = game.camera.world_from_screen(mouse_x, mouse_y)
                wx = max(0, min(wx, game.camera.world_w))
                wy = max(0, min(wy, game.camera.world_h))
                obj = game.player.drawing_landscape
                last_x, last_y = obj.points[-1]
                if math.hypot(wx - last_x, wy - last_y) >= game.player.road_min_point_dist:
                    obj.add_point(wx, wy)

        if game.placement_mode:
            if game.placement_mode != self.placement_hover.mode:
                self.placement_hover.mode = game.placement_mode
                self.placement_hover.check_pos = None

            if mouse_y > UI_HEIGHT and not game.ui.exit_placement_btn.collidepoint(mouse_x, mouse_y):
                last = self.placement_hover.check_pos
                moved_enough = (
                        last is None or
                        math.hypot(mouse_x - last[0], mouse_y - last[1]) >= PLACEMENT_CHECK_MIN_MOVE
                )
                if moved_enough:
                    self.placement_hover.check_pos = (mouse_x, mouse_y)
                    wx, wy = game.camera.world_from_screen(mouse_x, mouse_y)
                    game.placement_pos = (wx, wy)
                    if game.placement_mode in ("creature_male", "creature_female"):
                        game.placement_valid = game.object_manager.check_creature_placement_valid(wx, wy)
                    else:
                        game.placement_valid = game.object_manager.check_object_placement_valid(wx, wy)
            else:
                game.placement_pos = None
        else:
            self.placement_hover.mode = None
            self.placement_hover.check_pos = None


# =========================================================================
# Домен: экраны "Создание мира" / "Загрузка мира"
# =========================================================================

class _WorldScreenEventMixin:

    def _handle_create_world_event(self, event):
        game = self.game
        screen = game.create_world_screen
        ui = game.ui

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if ui.world_screen_back_btn_rect.collidepoint(event.pos):
                game.world_manager.cancel_create_screen()
                return

            for box in screen.all_inputs():
                box.try_focus(event.pos)

            if ui.ws_create_btn_rect.collidepoint(event.pos):
                game.world_manager.confirm_create_screen()

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                game.world_manager.cancel_create_screen()
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                game.world_manager.confirm_create_screen()
            else:
                for box in screen.all_inputs():
                    if box.handle_keydown(event):
                        screen.error_text = None
                        break

    def _handle_load_world_event(self, event):
        game = self.game
        screen = game.load_world_screen
        ui = game.ui

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            game.world_manager.cancel_load_screen()
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos

            if ui.world_screen_back_btn_rect.collidepoint(mouse_pos):
                game.world_manager.cancel_load_screen()
                return

            if ui.lw_list_rect and ui.lw_list_rect.collidepoint(mouse_pos):
                local_y = mouse_pos[1] - ui.lw_list_rect.y + screen.list_scroll.offset
                index = int(local_y // WORLD_LIST_ITEM_HEIGHT)
                if 0 <= index < len(screen.entries):
                    game.world_manager.select_entry(screen, index)
                return

            if screen.selected_index is not None:
                if ui.lw_load_btn_rect and ui.lw_load_btn_rect.collidepoint(mouse_pos):
                    game.world_manager.load_selected(screen)
                    return
                if ui.lw_delete_btn_rect and ui.lw_delete_btn_rect.collidepoint(mouse_pos):
                    game.world_manager.delete_selected(screen)
                    return

        elif event.type == pygame.MOUSEWHEEL:
            mouse_pos = pygame.mouse.get_pos()
            if ui.lw_list_rect and ui.lw_list_rect.collidepoint(mouse_pos):
                content_height = len(screen.entries) * WORLD_LIST_ITEM_HEIGHT
                screen.list_scroll.update_bounds(content_height, ui.lw_list_rect.height)
                screen.list_scroll.scroll_by_wheel(event.y)
            elif ui.lw_info_rect and ui.lw_info_rect.collidepoint(mouse_pos):
                screen.info_scroll.update_bounds(ui.lw_info_content_height, ui.lw_info_rect.height)
                screen.info_scroll.scroll_by_wheel(event.y)


# =========================================================================
# Домен: колёсико мыши
# =========================================================================

class _ScrollMixin:

    def _handle_mouse_wheel(self, event):
        game = self.game
        ui = game.ui
        mouse_x, mouse_y = pygame.mouse.get_pos()

        if game.right_panel_collapsed:
            return

        if (game.world_loaded and game.selected_creature
                and ui.show_relationships_section and ui.relationships_list_rect is not None
                and ui.relationships_list_rect.collidepoint(mouse_x, mouse_y)):
            ui.relationships_scroll_offset -= event.y * DEFAULT_SCROLL_SPEED
            ui.relationships_scroll_offset = max(0, min(ui.relationships_scroll_offset, ui.relationships_max_scroll))
            return

        if not game.world_loaded:
            return

        for spec in all_secondary_panel_specs():
            panel = getattr(ui, spec.attr_name)
            if panel.selected is None:
                continue
            if panel.handle_wheel(game, mouse_x, mouse_y, event.y):
                return

# =========================================================================
# Домен: экран "Настройки" - модальная панель, блокирующая весь остальной ввод
# =========================================================================

class _SettingsScreenEventMixin:

    def _handle_settings_event(self, event):
        game = self.game
        ui = game.ui
        state = game.settings_screen

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            game.close_settings_screen()
            return

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return

        if ui.settings_back_btn_rect.collidepoint(event.pos):
            game.close_settings_screen()
            return
        if ui.settings_save_btn_rect.collidepoint(event.pos):
            game.save_settings_screen()
            return
        if ui.settings_tab_display_rect.collidepoint(event.pos):
            state.active_tab = "display"
            return

        if state.active_tab == "display":
            for key, row_rect in ui.settings_checkbox_rows.items():
                if row_rect.collidepoint(event.pos):
                    state.toggle(key)
                    return

# =========================================================================
# Итоговый класс
# =========================================================================

class InputHandler(_KeyboardMixin, _CrashScreenMixin, _BiomePaintingMixin, _MenuMixin,
                    _MouseDownMixin, _MouseUpMixin, _MouseMotionMixin,
                    _WorldScreenEventMixin, _ScrollMixin, _SettingsScreenEventMixin):

    def __init__(self, game):
        self.game = game
        self.biome_paint = _BiomePaintState()
        self.placement_hover = _PlacementHoverState()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.game.running = False
            elif self.game.crashed:
                self._handle_crash_event(event)
            elif self.game.create_world_screen is not None:
                self._handle_create_world_event(event)
            elif self.game.load_world_screen is not None:
                self._handle_load_world_event(event)
            elif self.game.settings_screen is not None:
                self._handle_settings_event(event)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._handle_mouse_down(event)
            elif event.type == pygame.MOUSEBUTTONUP:
                self._handle_mouse_up(event)
            elif event.type == pygame.MOUSEMOTION:
                self._handle_mouse_motion(event)
            elif event.type == pygame.MOUSEWHEEL:
                self._handle_mouse_wheel(event)
            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event)
