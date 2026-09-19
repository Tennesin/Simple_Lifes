"""Верхняя панель: главное меню + 5 выпадающих подменю."""

import os
import pygame

import settings
import info
from game.widgets import Button
from game.race_registry import all_races, all_player_tools, all_road_networks
from game.animal_registry import all_animals

from .constants import _CORE_PLAYER_TOOLS, _CORE_OBJECT_MENU_ITEMS

class TopBarPanel:
    _MENU_COLORS = {
        "normal": settings.BUTTON_COLOR, "hover": settings.BUTTON_HOVER,
        "disabled": settings.BUTTON_DISABLED, "text": settings.TEXT_COLOR,
    }
    BUTTON_GAP = 10
    WORLD_NAME_BUFFER = 220

    def __init__(self, game, font):
        self.game = game
        self.font = font
        self.btn_settings = pygame.Rect(0, 0, 0, 0)
        self._settings_btn_width = 0
        self.min_required_width = 0
        self._build_layout()

    @staticmethod
    def _button_width(label, min_width=90):
        text_w = Button._get_font(settings.FONT_SIZE_BUTTON).size(label)[0]
        return max(min_width, text_w + 24)

    def _build_layout(self):
        gap = 4

        x = 10
        for attr, label in (
                ("btn_game", info.INFO_BTN_GAME),
                ("btn_landscape", info.INFO_BTN_LANDSCAPE),
                ("btn_lifes", info.INFO_BTN_LIFES),
                ("btn_animals", info.INFO_BTN_ANIMALS),
                ("btn_objects", info.INFO_BTN_OBJECTS),
                ("btn_nature", info.INFO_BTN_NATURE),
                ("btn_player", info.INFO_BTN_PLAYER),
        ):
            width = self._button_width(label)
            setattr(self, attr, Button(pygame.Rect(x, 5, width, settings.BUTTON_HEIGHT), label))
            x += width + self.BUTTON_GAP

        menu_top = 35

        # ---------- Меню "Игра" ----------
        item_x, item_w = self.btn_game.rect.x + 5, 130
        self.btn_create_world = Button(pygame.Rect(item_x, menu_top + 5, item_w, settings.BUTTON_HEIGHT), info.INFO_BTN_CREATE_WORLD)
        self.btn_load_world = Button(
            pygame.Rect(item_x, menu_top + 5 + (settings.BUTTON_HEIGHT + gap), item_w, settings.BUTTON_HEIGHT), info.INFO_BTN_LOAD_WORLD)
        self.btn_save_world = Button(
            pygame.Rect(item_x, menu_top + 5 + 2 * (settings.BUTTON_HEIGHT + gap), item_w, settings.BUTTON_HEIGHT), info.INFO_BTN_SAVE_WORLD)
        self.btn_pause = Button(
            pygame.Rect(item_x, menu_top + 5 + 3 * (settings.BUTTON_HEIGHT + gap), item_w, settings.BUTTON_HEIGHT), info.INFO_BTN_PAUSE)
        self.btn_instruction = Button(
            pygame.Rect(item_x, menu_top + 5 + 4 * (settings.BUTTON_HEIGHT + gap), item_w, settings.BUTTON_HEIGHT), info.INFO_BTN_INSTRUCTION)
        self.btn_exit = Button(
            pygame.Rect(item_x, menu_top + 5 + 5 * (settings.BUTTON_HEIGHT + gap), item_w, settings.BUTTON_HEIGHT), info.INFO_BTN_EXIT)
        self.menu_game_rect = pygame.Rect(
            self.btn_game.rect.x, menu_top, item_w + 10, self.btn_exit.rect.bottom + 5 - menu_top)

        # ---------- Меню "Ландшафт" ----------
        item_x, item_w = self.btn_landscape.rect.x + 5, 110
        self.btn_wall = Button(pygame.Rect(item_x, menu_top + 5, item_w, settings.BUTTON_HEIGHT), info.INFO_BTN_WALL)
        self.btn_fence = Button(
            pygame.Rect(item_x, menu_top + 5 + (settings.BUTTON_HEIGHT + gap), item_w, settings.BUTTON_HEIGHT), info.INFO_BTN_FENCE)
        self.btn_biome_plains = Button(
            pygame.Rect(item_x, menu_top + 5 + 2 * (settings.BUTTON_HEIGHT + gap), item_w, settings.BUTTON_HEIGHT), info.INFO_BTN_BIOME_PLAINS)
        self.btn_biome_desert = Button(
            pygame.Rect(item_x, menu_top + 5 + 3 * (settings.BUTTON_HEIGHT + gap), item_w, settings.BUTTON_HEIGHT), info.INFO_BTN_BIOME_DESERT)
        self.btn_biome_river = Button(
            pygame.Rect(item_x, menu_top + 5 + 4 * (settings.BUTTON_HEIGHT + gap), item_w, settings.BUTTON_HEIGHT), info.INFO_BTN_BIOME_RIVER)
        self.btn_biome_sea = Button(
            pygame.Rect(item_x, menu_top + 5 + 5 * (settings.BUTTON_HEIGHT + gap), item_w, settings.BUTTON_HEIGHT), info.INFO_BTN_BIOME_SEA)
        self.menu_landscape_rect = pygame.Rect(
            self.btn_landscape.rect.x, menu_top, item_w + 10, self.btn_biome_sea.rect.bottom + 5 - menu_top)

        # ---------- Меню "Расы" (generic) ----------
        item_x = self.btn_lifes.rect.x + 5
        self.creature_placement_buttons = {}
        y = menu_top + 5
        lifes_bottom = y
        for descriptor in all_races():
            for placement_mode, label in descriptor.creature_placement_modes:
                btn = Button(pygame.Rect(item_x, y, 90, settings.BUTTON_HEIGHT), label)
                self.creature_placement_buttons[placement_mode] = btn
                lifes_bottom = btn.rect.bottom
                y += settings.BUTTON_HEIGHT + gap
        self.menu_lifes_rect = pygame.Rect(self.btn_lifes.rect.x, menu_top, 100, lifes_bottom + 5 - menu_top)

        # ---------- Меню "Животные" ----------
        item_x = self.btn_animals.rect.x + 5
        self.animal_placement_buttons = {}
        y = menu_top + 5
        animals_bottom = y
        for descriptor in all_animals():
            btn = Button(pygame.Rect(item_x, y, 90, settings.BUTTON_HEIGHT), descriptor.placement_label)
            self.animal_placement_buttons[descriptor.placement_mode] = btn
            animals_bottom = btn.rect.bottom
            y += settings.BUTTON_HEIGHT + gap
        self.menu_animals_rect = pygame.Rect(self.btn_animals.rect.x, menu_top, 100, animals_bottom + 5 - menu_top)

        # ---------- Меню "Объект" ----------
        item_x = self.btn_objects.rect.x + 5
        self.object_placement_buttons = {}
        self.road_tool_buttons = {}
        y = menu_top + 5
        objects_bottom = y

        for obj_type, label in _CORE_OBJECT_MENU_ITEMS:
            btn = Button(pygame.Rect(item_x, y, 130, settings.BUTTON_HEIGHT), label)
            self.object_placement_buttons[obj_type] = btn
            objects_bottom = btn.rect.bottom
            y += settings.BUTTON_HEIGHT + gap

        for descriptor in all_races():
            for spec in descriptor.placeable_objects:
                if not spec.manually_placeable:
                    continue
                btn = Button(pygame.Rect(item_x, y, 130, settings.BUTTON_HEIGHT), spec.label)
                self.object_placement_buttons[spec.obj_type] = btn
                objects_bottom = btn.rect.bottom
                y += settings.BUTTON_HEIGHT + gap

        for spec in all_road_networks():
            if not spec.menu_label:
                continue
            btn = Button(pygame.Rect(item_x, y, 130, settings.BUTTON_HEIGHT), spec.menu_label)
            self.road_tool_buttons[spec.obj_type] = btn
            objects_bottom = btn.rect.bottom
            y += settings.BUTTON_HEIGHT + gap

        self.menu_objects_rect = pygame.Rect(self.btn_objects.rect.x, menu_top, 140, objects_bottom + 5 - menu_top)

        # ---------- Меню "Природа" ----------
        item_x = self.btn_nature.rect.x + 5
        nature_labels = [
            ("btn_fruit", info.INFO_BTN_FRUIT),
            ("btn_bush", info.INFO_BTN_BUSH),
            ("btn_water", info.INFO_BTN_WATER),
            ("btn_tree", info.INFO_BTN_TREE),
            ("btn_stone", info.INFO_BTN_STONE),
            ("btn_grass", info.INFO_BTN_GRASS),
            ("btn_meat", info.INFO_BTN_MEAT),
        ]
        for i, (attr, label) in enumerate(nature_labels):
            y = menu_top + 5 + i * (settings.BUTTON_HEIGHT + gap)
            setattr(self, attr, Button(pygame.Rect(item_x, y, 90, settings.BUTTON_HEIGHT), label))
        self.menu_nature_rect = pygame.Rect(
            self.btn_nature.rect.x, menu_top, 100, self.btn_meat.rect.bottom + 5 - menu_top)

        # ---------- Меню "Игрок" ----------
        item_x = self.btn_player.rect.x + 5
        self.player_tool_buttons = {}
        all_tools = _CORE_PLAYER_TOOLS + all_player_tools()
        y = menu_top + 5
        player_bottom = y
        for spec in all_tools:
            btn = Button(pygame.Rect(item_x, y, 90, settings.BUTTON_HEIGHT), spec.label)
            self.player_tool_buttons[spec.tool_value] = btn
            player_bottom = btn.rect.bottom
            y += settings.BUTTON_HEIGHT + gap
        self.menu_player_rect = pygame.Rect(self.btn_player.rect.x, menu_top, 100, player_bottom + 5 - menu_top)

        # ---------- Минимально необходимая ширина окна: кнопка "Игрок" + буфер под
        # "Мир: X" + кнопка "Настройки" + отступ от правого края. Больше руками не считаем ----------
        self._settings_btn_width = self._button_width(info.INFO_BTN_SETTINGS, min_width=90)
        self.min_required_width = (
                self.btn_player.rect.right + self.WORLD_NAME_BUFFER
                + self.BUTTON_GAP + self._settings_btn_width + 10
        )

    def draw(self, screen):
        game = self.game
        pygame.draw.rect(screen, settings.PANEL_COLOR, pygame.Rect(0, 0, screen.get_width(), settings.UI_HEIGHT))
        mouse_pos = pygame.mouse.get_pos()

        self.btn_game.draw(screen, mouse_pos)

        self.btn_landscape.enabled = game.world_loaded
        self.btn_landscape.draw(screen, mouse_pos)

        self.btn_lifes.enabled = game.world_loaded
        self.btn_lifes.draw(screen, mouse_pos)

        self.btn_animals.enabled = game.world_loaded
        self.btn_animals.draw(screen, mouse_pos)

        self.btn_objects.enabled = game.world_loaded
        self.btn_objects.draw(screen, mouse_pos)

        self.btn_nature.enabled = game.world_loaded
        self.btn_nature.draw(screen, mouse_pos)

        self.btn_player.enabled = game.world_loaded
        self.btn_player.draw(screen, mouse_pos)

        if game.show_game_menu:
            pygame.draw.rect(screen, settings.MENU_BG, self.menu_game_rect)
            self.btn_create_world.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_load_world.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_save_world.enabled = game.world_loaded
            self.btn_save_world.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_pause.enabled = game.world_loaded
            self.btn_pause.label = info.INFO_BTN_RESUME if game.paused else info.INFO_BTN_PAUSE
            self.btn_pause.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_instruction.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_exit.draw(screen, mouse_pos, colors=self._MENU_COLORS)

        if game.world_loaded and game.show_landscape_menu:
            pygame.draw.rect(screen, settings.MENU_BG, self.menu_landscape_rect)
            self.btn_wall.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_fence.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_biome_plains.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_biome_desert.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_biome_river.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_biome_sea.draw(screen, mouse_pos, colors=self._MENU_COLORS)

        if game.world_loaded and game.show_lifes_menu:
            pygame.draw.rect(screen, settings.MENU_BG, self.menu_lifes_rect)
            for btn in self.creature_placement_buttons.values():
                btn.draw(screen, mouse_pos, colors=self._MENU_COLORS)

        if game.world_loaded and game.show_animals_menu:
            pygame.draw.rect(screen, settings.MENU_BG, self.menu_animals_rect)
            for btn in self.animal_placement_buttons.values():
                btn.draw(screen, mouse_pos, colors=self._MENU_COLORS)

        if game.world_loaded and game.show_objects_menu:
            pygame.draw.rect(screen, settings.MENU_BG, self.menu_objects_rect)
            for btn in self.object_placement_buttons.values():
                btn.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            for btn in self.road_tool_buttons.values():
                btn.draw(screen, mouse_pos, colors=self._MENU_COLORS)

        if game.world_loaded and game.show_nature_menu:
            pygame.draw.rect(screen, settings.MENU_BG, self.menu_nature_rect)
            self.btn_fruit.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_bush.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_water.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_tree.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_stone.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_grass.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_meat.draw(screen, mouse_pos, colors=self._MENU_COLORS)

        if game.world_loaded and game.show_player_menu:
            pygame.draw.rect(screen, settings.MENU_BG, self.menu_player_rect)
            for btn in self.player_tool_buttons.values():
                btn.draw(screen, mouse_pos, colors=self._MENU_COLORS)

        self._draw_settings_button(screen, mouse_pos)

        if game.world_loaded and game.world_path:
            self._draw_world_name(screen)

    def _draw_settings_button(self, screen, mouse_pos):
        window_w = screen.get_width()
        btn_w, btn_h = self._settings_btn_width, settings.BUTTON_HEIGHT
        rect = pygame.Rect(window_w - 10 - btn_w, 5, btn_w, btn_h)
        self.btn_settings = rect

        color = settings.BUTTON_HOVER if rect.collidepoint(mouse_pos) else settings.BUTTON_COLOR
        pygame.draw.rect(screen, color, rect, border_radius=4)
        txt = self.font.render(info.INFO_BTN_SETTINGS, True, settings.TEXT_COLOR)
        screen.blit(txt, txt.get_rect(center=rect.center))

    def _draw_world_name(self, screen):
        game = self.game
        world_name = os.path.basename(game.world_path)
        if world_name.endswith(settings.WORLD_EXTENSION):
            world_name = world_name[:-len(settings.WORLD_EXTENSION)]
        name_full = info.INFO_WORLD_NAME_TEMPLATE.format(world_name=world_name)

        min_x = self.btn_player.rect.right + 20
        right_limit = self.btn_settings.x - 10
        available_for_name = right_limit - min_x
        if available_for_name <= 30:
            return

        name_txt = self.font.render(name_full, True, settings.TEXT_COLOR)
        if name_txt.get_width() > available_for_name:
            truncated = name_full
            while truncated and self.font.size(truncated + "…")[0] > available_for_name:
                truncated = truncated[:-1]
            name_txt = self.font.render((truncated + "…") if truncated else "", True, settings.TEXT_COLOR)
        if name_txt.get_width() > 0:
            name_x = right_limit - name_txt.get_width()
            screen.blit(name_txt, (name_x, 10))