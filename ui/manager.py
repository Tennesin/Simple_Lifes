"""Фасад: то, что реально импортирует game.py и дёргает input_handler.py."""

import pygame

import settings
import info
from game.race_registry import (
    all_races, all_player_tools, all_secondary_panel_specs, all_road_networks,
)
from game.animal_registry import animal_classes
from game.animal_panel import AnimalPanel

from .constants import BIOME_PREVIEW_COLOR, _CORE_PLAYER_TOOLS, _CORE_TOOL_HINTS
from .top_bar import TopBarPanel
from .object_panel import ObjectPanel
from .minimap import MinimapPanel
from .world_screens import WorldScreensPanel
from .settings_panel import SettingsPanel
from .instruction_panel import InstructionPanel
from .exit_confirm import ExitConfirmPanel

class UIManager:

    def __init__(self, game):
        self.game = game
        self.font = pygame.font.SysFont(settings.FONT_NAME, settings.FONT_SIZE_PANEL)

        self.top_bar = TopBarPanel(game, self.font)

        self._creature_panels = {
            descriptor.race_name: descriptor.panel_cls(game, self.font)
            for descriptor in all_races()
            if descriptor.panel_cls is not None
        }
        self._default_race_name = next(iter(self._creature_panels), None)

        # ---------- Доп. боковые панели (кладбище и т.п.) - полностью generic ----------
        self._secondary_panels = {}
        for spec in all_secondary_panel_specs():
            self._secondary_panels[spec.attr_name] = (spec, spec.panel_cls(game, self.font))

        self.object_panel = ObjectPanel(game, self.font)
        self.animal_panel = AnimalPanel(game, self.font)
        self.minimap = MinimapPanel(game, self.font)
        self.world_screens = WorldScreensPanel(game)
        self.settings_panel = SettingsPanel(game, self.font)
        self.instruction_panel = InstructionPanel(game, self.font)
        self.exit_confirm_panel = ExitConfirmPanel(game, self.font)

        self.exit_placement_btn = pygame.Rect(10, settings.UI_HEIGHT + 10, 30, 30)
        self._biome_preview_surfaces = {}
        self.collapse_handle_rect = pygame.Rect(0, 0, 0, 0)

    # ---------- Панель существа: динамический выбор по расе ----------

    @property
    def creature_panel(self):
        game = self.game
        if game.selected_creature is not None:
            return self._panel_for_creature(game.selected_creature)
        return self._creature_panels.get(self._default_race_name)

    def _panel_for_creature(self, creature):
        race_name = getattr(creature, "race_name", None) or self._default_race_name
        return self._creature_panels.get(race_name) or self._creature_panels.get(self._default_race_name)

    def has_creature_panel(self, entity):
        """True, если у расы сущности есть собственная боковая панель (разумное существо, не животное/объект)."""
        return getattr(entity, "race_name", None) in self._creature_panels

    def _delegate_objects(self):
        return (self.top_bar, self.creature_panel, self.world_screens, self.minimap, self.settings_panel,
                self.exit_confirm_panel)

    def __getattr__(self, name):
        if "_creature_panels" not in self.__dict__:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}' "
                f"(обращение до завершения __init__)"
            )

        secondary = self.__dict__.get("_secondary_panels", {})
        if name in secondary:
            return secondary[name][1]

        for delegate in self._delegate_objects():
            if hasattr(delegate, name):
                return getattr(delegate, name)

        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def rebuild_layout(self, window_w, window_h):
        for panel in self._creature_panels.values():
            panel.rebuild_layout(window_w, window_h)
        for _spec, panel in self._secondary_panels.values():
            if hasattr(panel, "rebuild_layout"):
                panel.rebuild_layout(window_w, window_h)
        self.minimap.rebuild_layout(window_w, window_h)
        self.animal_panel.rebuild_layout(window_w, window_h)
        self.instruction_panel.rebuild_layout(window_w, window_h)

    def active_modal_panel(self):
        for _spec, panel in self._secondary_panels.values():
            if getattr(panel, "modal_active", False):
                return panel
        return None

    # ---------- Оркестрация отрисовки ----------

    def _content_rect(self, screen):
        return pygame.Rect(0, settings.UI_HEIGHT, screen.get_width(), screen.get_height() - settings.UI_HEIGHT)

    def draw(self, screen):
        game = self.game
        self.top_bar.draw(screen)

        if game.create_world_screen is not None:
            self.world_screens.draw_create_world_screen(
                screen, game.create_world_screen, self._content_rect(screen))
            return
        if game.load_world_screen is not None:
            self.world_screens.draw_load_world_screen(
                screen, game.load_world_screen, self._content_rect(screen))
            return

        if game.placement_mode:
            self.draw_placement_overlay(screen)
        elif (game.player.tool is not None or game.player.grabbed_creature is not None
              or game.player.grabbed_object is not None):
            self.draw_player_tool_overlay(screen)

        active_secondary = [(spec, panel) for spec, panel in self._secondary_panels.values()
                            if panel.selected is not None]
        side_panel_active = bool(game.selected_creature) or bool(active_secondary)

        if side_panel_active:
            self._draw_collapse_handle(screen)
            if not game.right_panel_collapsed:
                if game.selected_creature:
                    self._panel_for_creature(game.selected_creature).draw(screen)
                for _spec, panel in active_secondary:
                    panel.draw(screen)

        if game.selected_object:
            if isinstance(game.selected_object, animal_classes()):
                self.animal_panel.draw(screen)
            else:
                self.object_panel.draw(screen)
        if game.show_minimap and game.world_loaded:
            self.minimap.draw(screen)

        for _spec, panel in self._secondary_panels.values():
            if getattr(panel, "popup_active", False):
                panel.draw_popup(screen)

        for _spec, panel in self._secondary_panels.values():
            if getattr(panel, "modal_active", False):
                panel.draw(screen)

    # ---------- Ручка сворачивания правой панели ----------

    def _compute_collapse_handle_rect(self, screen_width):
        panel_rect = self.creature_panel.info_panel_rect
        handle_y = panel_rect.y + (panel_rect.height - settings.COLLAPSE_HANDLE_HEIGHT) // 2

        if self.game.right_panel_collapsed:
            handle_x = screen_width - settings.COLLAPSE_HANDLE_WIDTH
        else:
            handle_x = panel_rect.x - settings.COLLAPSE_HANDLE_WIDTH

        return pygame.Rect(handle_x, handle_y, settings.COLLAPSE_HANDLE_WIDTH, settings.COLLAPSE_HANDLE_HEIGHT)

    def _draw_collapse_handle(self, screen):
        game = self.game
        handle_rect = self._compute_collapse_handle_rect(screen.get_width())
        self.collapse_handle_rect = handle_rect

        mouse_pos = pygame.mouse.get_pos()
        hovered = handle_rect.collidepoint(mouse_pos)

        pygame.draw.rect(screen, settings.COLLAPSE_HANDLE_COLOR, handle_rect, border_radius=3)
        pygame.draw.rect(screen, settings.COLLAPSE_HANDLE_BORDER, handle_rect, 1, border_radius=3)

        arrow_color = settings.COLLAPSE_HANDLE_ARROW_HOVER_COLOR if hovered else settings.COLLAPSE_HANDLE_ARROW_COLOR
        cx, cy = handle_rect.center
        half_h = handle_rect.height * 0.30
        half_w = handle_rect.width * 0.34

        if game.right_panel_collapsed:
            points = [(cx + half_w, cy - half_h), (cx + half_w, cy + half_h), (cx - half_w, cy)]
        else:
            points = [(cx - half_w, cy - half_h), (cx - half_w, cy + half_h), (cx + half_w, cy)]
        pygame.draw.polygon(screen, arrow_color, points)

    def draw_placement_overlay(self, screen):
        game = self.game
        mouse_pos = pygame.mouse.get_pos()
        cross_color = settings.CLOSE_BUTTON_HOVER if self.exit_placement_btn.collidepoint(mouse_pos) else settings.CLOSE_BUTTON_COLOR
        pygame.draw.rect(screen, cross_color, self.exit_placement_btn)
        cx, cy = self.exit_placement_btn.center
        pygame.draw.line(screen, settings.TEXT_COLOR, (cx - 6, cy - 6), (cx + 6, cy + 6), 2)
        pygame.draw.line(screen, settings.TEXT_COLOR, (cx + 6, cy - 6), (cx - 6, cy + 6), 2)

        if game.placement_pos:
            screen_pos = game.camera.apply_pos(game.placement_pos)
            color = (0, 255, 0) if game.placement_valid else (255, 0, 0)
            pygame.draw.circle(screen, color, (int(screen_pos[0]), int(screen_pos[1])), 12, 2)
            screen.blit(self.font.render(info.INFO_PLACEMENT_HINT, True, settings.TEXT_COLOR), (10, settings.UI_HEIGHT + 50))

    def draw_player_tool_overlay(self, screen):
        game = self.game
        mouse_pos = pygame.mouse.get_pos()
        cross_color = settings.CLOSE_BUTTON_HOVER if self.exit_placement_btn.collidepoint(mouse_pos) else settings.CLOSE_BUTTON_COLOR
        pygame.draw.rect(screen, cross_color, self.exit_placement_btn)
        cx, cy = self.exit_placement_btn.center
        pygame.draw.line(screen, settings.TEXT_COLOR, (cx - 6, cy - 6), (cx + 6, cy + 6), 2)
        pygame.draw.line(screen, settings.TEXT_COLOR, (cx + 6, cy - 6), (cx - 6, cy + 6), 2)

        hint_map = dict(_CORE_TOOL_HINTS)
        for spec in _CORE_PLAYER_TOOLS + all_player_tools():
            hint_map[spec.tool_value] = spec.hint
        for spec in all_road_networks():
            if spec.menu_hint:
                hint_map[spec.obj_type] = spec.menu_hint

        if game.player.grabbed_creature is not None:
            hint = info.INFO_TOOL_GRAB_RELEASE_HINT
        elif game.player.grabbed_object is not None:
            hint = info.INFO_TOOL_GRAB_OBJECT_HINT
        else:
            hint = hint_map.get(game.player.tool, "")
        if hint:
            screen.blit(self.font.render(hint, True, settings.TEXT_COLOR), (10, settings.UI_HEIGHT + 50))

        # ---------- Предпросмотр рисуемой дороги (любого зарегистрированного типа) ----------
        for spec in all_road_networks():
            drawing_road = getattr(game.player, f"drawing_{spec.obj_type}", None)
            if drawing_road is not None and drawing_road.points:
                last_x, last_y = drawing_road.points[-1]
                last_screen = game.camera.apply_pos((last_x, last_y))
                pygame.draw.line(screen, spec.preview_color, last_screen, mouse_pos, 2)

        if game.player.tool in ("biome_plains", "biome_desert", "biome_river", "biome_sea"):
            grid = game.biome_manager.grid
            if (mouse_pos[1] > settings.UI_HEIGHT and not self.exit_placement_btn.collidepoint(mouse_pos)
                    and grid is not None):
                wx, wy = game.camera.world_from_screen(*mouse_pos)
                color = BIOME_PREVIEW_COLOR.get(game.player.tool, (255, 255, 255))
                preview_surf = self._get_biome_preview_surface(color, grid.cell_size)
                for cx, cy in grid.cells_in_radius(wx, wy, game.player.brush_radius):
                    screen_pos = game.camera.apply_pos((cx * grid.cell_size, cy * grid.cell_size))
                    screen.blit(preview_surf, screen_pos)
                pygame.draw.circle(screen, (255, 255, 255), mouse_pos, int(game.player.brush_radius), 1)
            radius_txt = self.font.render(
                info.INFO_BRUSH_RADIUS.format(radius=int(game.player.brush_radius)), True, settings.TEXT_COLOR)
            screen.blit(radius_txt, (10, settings.UI_HEIGHT + 70))

    def _get_biome_preview_surface(self, color, cell_size):
        key = (color, cell_size)
        surf = self._biome_preview_surfaces.get(key)
        if surf is None:
            surf = pygame.Surface((cell_size, cell_size), pygame.SRCALPHA)
            surf.fill((*color, 110))
            self._biome_preview_surfaces[key] = surf
        return surf

    def draw_settings_screen(self, screen, state):
        self.settings_panel.draw(screen, state)

    def draw_instruction_screen(self, screen, state):
        self.instruction_panel.draw(screen, state)

    def draw_exit_confirm_dialog(self, screen):
        self.exit_confirm_panel.draw(screen)