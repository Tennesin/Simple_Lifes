import pygame
import sys
import time
import traceback
import json

from renderer import Camera, WorldRenderer
from ui import UIManager
from player import Player
from settings import *
import settings

from biome import BiomeManager
from .world_manager import WorldManager
from .object_manager import ObjectManager
from .input_handler import InputHandler
from .simulation import Simulation
from .world_context import WorldState

class SettingsScreen:
    def __init__(self, base_settings):
        self.active_tab = "display"
        self.draft = dict(base_settings)

    def toggle(self, key):
        if key in self.draft:
            self.draft[key] = not self.draft[key]

class Game:
    def __init__(self):
        pygame.init()

        try:
            display_info = pygame.display.Info()
            self.desktop_w = display_info.current_w
            self.desktop_h = display_info.current_h
        except pygame.error:
            self.desktop_w, self.desktop_h = WINDOW_MAX_WIDTH, WINDOW_MAX_HEIGHT

        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Simple_Lifes")
        self.clock = pygame.time.Clock()
        self.running = True

        self.camera = Camera(WORLD_WIDTH, WORLD_HEIGHT)

        self.world_loaded = False
        self.world_path = None
        self.world = WorldState()
        self.biome_manager = BiomeManager(self)
        self.world_seed = None
        self.paused = False

        self.selected_creature = None
        self.selected_object = None
        self.selected_object_click_pos = None
        self.editing_name = False
        self.name_edit_buffer = ""

        self.dragging = False
        self.drag_start = (0, 0)

        self.renderer = WorldRenderer(self)
        self.ui = UIManager(self)

        self.placement_mode = None
        self.show_game_menu = False
        self.show_lifes_menu = False
        self.show_landscape_menu = False
        self.show_objects_menu = False
        self.show_player_menu = False
        self.show_nature_menu = False
        self.placement_pos = None
        self.placement_valid = False

        # ---------- Экраны создания/загрузки мира ----------
        self.create_world_screen = None
        self.load_world_screen = None
        self.settings_screen = None

        self.player = Player()
        self.display_settings = self._load_display_settings()
        self.show_minimap = True
        self.right_panel_collapsed = False
        self.last_manual_save_time = None

        # ---------- Специализированные подсистемы ----------
        self.world_manager = WorldManager(self)
        self.object_manager = ObjectManager(self)
        self.input_handler = InputHandler(self)
        self.simulation = Simulation(self)

        os.makedirs(BASE_WORLDS_DIR, exist_ok=True)

        # ---------- Защита от критических ошибок ----------
        self.crashed = False
        self.crash_message = None
        self.crash_traceback = None
        self.crash_log_written = False
        self.crash_log_btn_rect = pygame.Rect(0, 0, 0, 0)
        self._crash_world_path = None
        self._crash_creature_count = 0

    # ---------- Состояние меню ----------

    def close_all_menus(self):
        self.show_game_menu = False
        self.show_landscape_menu = False
        self.show_lifes_menu = False
        self.show_objects_menu = False
        self.show_player_menu = False
        self.show_nature_menu = False

    def toggle_pause(self):
        self.paused = not self.paused

    def open_settings_screen(self):
        self.close_all_menus()
        self.settings_screen = SettingsScreen(self.display_settings)

    def save_settings_screen(self):
        if self.settings_screen is None:
            return
        self.display_settings.update(self.settings_screen.draft)
        self.settings_screen = None
        self._save_display_settings()

    # ---------- Персистентность настроек отображения (переживает перезапуск игры) ----------

    SETTINGS_FILENAME = "settings.json"

    def _settings_file_path(self):
        return os.path.join(BASE_WORLDS_DIR, self.SETTINGS_FILENAME)

    def _load_display_settings(self):
        from game.race_registry import full_default_display_settings
        merged = full_default_display_settings()
        path = self._settings_file_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                # ---------- Берём только известные ключи - если в будущем добавят
                # новую настройку, старый файл её просто не перекроет дефолт ----------
                for key in merged:
                    if key in saved:
                        merged[key] = saved[key]
            except (OSError, json.JSONDecodeError):
                pass
        return merged

    def _save_display_settings(self):
        os.makedirs(BASE_WORLDS_DIR, exist_ok=True)
        try:
            with open(self._settings_file_path(), "w", encoding="utf-8") as f:
                json.dump(self.display_settings, f, indent=2, ensure_ascii=False)
        except OSError:
            pass

    def close_settings_screen(self):
        self.settings_screen = None

    def activate_player_tool(self, tool):
        self.object_manager.stop_placement()
        self.player.tool = tool

    def resize_for_world(self, world_w, world_h):
        screen_limit_w = self.desktop_w - WINDOW_SCREEN_MARGIN
        screen_limit_h = self.desktop_h - WINDOW_SCREEN_MARGIN

        max_w = max(WINDOW_MIN_WIDTH, min(WINDOW_MAX_WIDTH, screen_limit_w))
        max_h = max(WINDOW_MIN_HEIGHT, min(WINDOW_MAX_HEIGHT, screen_limit_h))
        available_h = max_h - UI_HEIGHT

        new_w = min(world_w, max_w)
        new_h = min(world_h, available_h) + UI_HEIGHT

        new_w = max(WINDOW_MIN_WIDTH, new_w)
        new_h = max(WINDOW_MIN_HEIGHT, new_h)

        settings.WINDOW_WIDTH = new_w
        settings.WINDOW_HEIGHT = new_h

        self.screen = pygame.display.set_mode((new_w, new_h))
        self.camera = Camera(world_w, world_h, new_w, new_h - UI_HEIGHT)
        self.ui.rebuild_layout(new_w, new_h)

    def restore_default_window(self):
        settings.WINDOW_WIDTH = settings.WINDOW_DEFAULT_WIDTH
        settings.WINDOW_HEIGHT = settings.WINDOW_DEFAULT_HEIGHT

        self.screen = pygame.display.set_mode(
            (settings.WINDOW_DEFAULT_WIDTH, settings.WINDOW_DEFAULT_HEIGHT)
        )
        self.camera = Camera(
            settings.WORLD_WIDTH, settings.WORLD_HEIGHT,
            settings.WINDOW_DEFAULT_WIDTH, settings.WINDOW_DEFAULT_HEIGHT - UI_HEIGHT
        )
        self.ui.rebuild_layout(settings.WINDOW_DEFAULT_WIDTH, settings.WINDOW_DEFAULT_HEIGHT)

    # ---------- Редактирование имени существа ----------

    def start_name_editing(self):
        if not self.selected_creature:
            return
        self.editing_name = True
        self.name_edit_buffer = self.selected_creature.begin_name_edit()

    def finish_name_editing(self):
        if self.editing_name and self.selected_creature:
            new_name = self.name_edit_buffer.strip()
            if new_name:
                self.selected_creature.commit_name_edit(new_name)
        self.editing_name = False
        self.name_edit_buffer = ""

    def clear_secondary_selections(self):
        from game.race_registry import all_secondary_panel_specs
        for spec in all_secondary_panel_specs():
            panel = getattr(self.ui, spec.attr_name, None)
            if panel is not None:
                panel.clear(self)

    # ---------- Отрисовка ----------

    def draw(self):
        if self.crashed:
            self.draw_crash_screen()
            pygame.display.flip()
            return

        if self.create_world_screen is not None:
            self.ui.draw_create_world_screen(self.screen, self.create_world_screen)
        elif self.load_world_screen is not None:
            self.ui.draw_load_world_screen(self.screen, self.load_world_screen)
        else:
            self.renderer.draw(self.screen)
            self.ui.draw(self.screen)

        if self.settings_screen is not None:
            self.ui.draw_settings_screen(self.screen, self.settings_screen)

        pygame.display.flip()

    def draw_crash_screen(self):
        self.screen.fill((15, 15, 15))
        window_w, window_h = self.screen.get_width(), self.screen.get_height()

        title_font = pygame.font.SysFont(FONT_NAME, 36, bold=True)
        text_font = pygame.font.SysFont(FONT_NAME, 20)
        btn_font = pygame.font.SysFont(FONT_NAME, 18)

        title_surf = title_font.render("UNEXPECTED CRITICAL ERROR!", True, (255, 40, 40))
        self.screen.blit(title_surf, (window_w // 2 - title_surf.get_width() // 2, 60))

        max_width = window_w - 80
        lines = self._wrap_crash_text(self.crash_message or "", text_font, max_width)
        y = 140
        for line in lines:
            line_surf = text_font.render(line, True, (255, 200, 200))
            self.screen.blit(line_surf, (window_w // 2 - line_surf.get_width() // 2, y))
            y += 26

        hint_surf = text_font.render(
            "Мир сохранён (если это было возможно). Игра возвращена в главное меню.",
            True, (200, 200, 200))
        self.screen.blit(hint_surf, (window_w // 2 - hint_surf.get_width() // 2, y + 20))

        btn_w, btn_h = 220, 40
        self.crash_log_btn_rect = pygame.Rect(
            window_w // 2 - btn_w // 2, window_h - 100, btn_w, btn_h)

        if self.crash_log_written:
            btn_color = (70, 70, 70)
            btn_label = "LOG SAVED -> err/"
        else:
            mouse_pos = pygame.mouse.get_pos()
            btn_color = (200, 60, 60) if self.crash_log_btn_rect.collidepoint(mouse_pos) else (150, 40, 40)
            btn_label = "MAKE TXT-LOG"

        pygame.draw.rect(self.screen, btn_color, self.crash_log_btn_rect, border_radius=4)
        btn_txt = btn_font.render(btn_label, True, (255, 255, 255))
        self.screen.blit(btn_txt, btn_txt.get_rect(center=self.crash_log_btn_rect.center))

    @staticmethod
    def _wrap_crash_text(text, font, max_width):
        words = text.split(' ')
        lines = []
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            if font.size(test)[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines if lines else [""]

    # ---------- Главный цикл ----------

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            try:
                self.input_handler.handle_events()
                if not self.crashed:
                    self.simulation.update(dt)
                self.draw()
            except Exception:
                self._handle_crash(traceback.format_exc())

        if self.world_loaded:
            suppress_autosave = (
                self.last_manual_save_time is not None and
                time.time() - self.last_manual_save_time < MANUAL_SAVE_AUTOSAVE_SUPPRESS_TIME
            )
            if not suppress_autosave:
                self.world_manager.save_world()
        pygame.quit()
        sys.exit()

    def _handle_crash(self, error_text):
        lines = [l for l in error_text.strip().splitlines() if l.strip()]
        crash_message = lines[-1] if lines else "UNKNOWN ERROR"

        self._crash_world_path = self.world_path
        self._crash_creature_count = len(self.world.creatures)

        try:
            if self.world_loaded and self.world_path:
                self.world_manager.close_world()
            else:
                self.world_loaded = False
        except Exception:
            self.world_loaded = False
            self.world_path = None

        self.crashed = True
        self.crash_message = crash_message
        self.crash_traceback = error_text
        self.crash_log_written = False
        self.crash_log_btn_rect = pygame.Rect(0, 0, 0, 0)

        self.paused = False
        self.close_all_menus()
        self.create_world_screen = None
        self.load_world_screen = None
        self.settings_screen = None
        self.placement_mode = None
        self.selected_creature = None
        self.selected_object = None
        self.clear_secondary_selections()
        self.editing_name = False

    def write_crash_log(self):
        if self.crash_log_written:
            return
        os.makedirs("err", exist_ok=True)
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.join("err", f"crash_{timestamp}.txt")
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write("=== Simple_Lifes CRASH LOG ===\n")
                f.write(f"Время: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Путь к миру: {self._crash_world_path}\n")
                f.write(f"Существ на момент падения: {self._crash_creature_count}\n")
                f.write(f"Python: {sys.version}\n")
                f.write(f"Pygame: {pygame.version.ver}\n")
                f.write(f"Размер окна: {settings.WINDOW_WIDTH}x{settings.WINDOW_HEIGHT}\n")
                f.write(f"Размер мира: {settings.WORLD_WIDTH}x{settings.WORLD_HEIGHT}\n")
                f.write("\n--- ПОЛНЫЙ TRACEBACK ---\n")
                f.write(self.crash_traceback or "(нет данных)")
            self.crash_log_written = True
        except OSError:
            pass

        self._recover_from_crash()

    def _recover_from_crash(self):
        self.crashed = False
        self.crash_message = None
        self.crash_traceback = None
        self.crash_log_written = False
        self.crash_log_btn_rect = pygame.Rect(0, 0, 0, 0)
        self._crash_world_path = None
        self._crash_creature_count = 0
        self.restore_default_window()

    def request_exit(self):
        if self.world_loaded:
            self.world_manager.close_world()
        else:
            self.running = False