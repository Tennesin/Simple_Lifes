import time
import math
import pygame

from settings import *
from info import *
from player import Player
from game.widgets import (
    Button, star_points, AccordionList,
    measure_instruction_blocks, draw_instruction_blocks,
)
from game.instruction_content import core_instruction_icon
from game.race_registry import (
    all_races, all_player_tools,
    all_minimap_layers, all_object_panel_extensions,
    all_secondary_panel_specs, PlayerToolSpec, all_road_networks,
)
from game.animal_registry import (
    all_animals, all_animal_object_panel_extensions, animal_classes,
)
from game.display_settings import (
    all_display_checkbox_specs, all_technical_checkbox_specs, all_technical_slider_specs
)
from game.animal_panel import AnimalPanel

BIOME_PREVIEW_COLOR = {
    "biome_plains": COLOR_LIGHT,
    "biome_desert": BIOME_BASE_COLOR[BIOME_DESERT],
    "biome_river": BIOME_BASE_COLOR[BIOME_RIVER],
    "biome_sea": BIOME_BASE_COLOR[BIOME_SEA],
}
BIOME_LABELS = {
    BIOME_PLAINS: INFO_BTN_BIOME_PLAINS,
    BIOME_DESERT: INFO_BTN_BIOME_DESERT,
    BIOME_RIVER: INFO_BTN_BIOME_RIVER,
    BIOME_SEA: INFO_BTN_BIOME_SEA,
}
_CORE_OBJECT_MENU_ITEMS = (
    ("spike", INFO_BTN_SPIKE),
)

# ---------- Базовые инструменты игрока (core), к ним добавляются расовые ----------
_CORE_PLAYER_TOOLS = (
    PlayerToolSpec(Player.TOOL_PET, INFO_BTN_PET, INFO_TOOL_PET_HINT),
    PlayerToolSpec(Player.TOOL_HIT, INFO_BTN_HIT, INFO_TOOL_HIT_HINT),
    PlayerToolSpec(Player.TOOL_GRAB, INFO_BTN_GRAB, INFO_TOOL_GRAB_HINT),
    PlayerToolSpec(Player.TOOL_FAVORITE, INFO_BTN_FAVORITE, INFO_TOOL_FAVORITE_HINT),
)

_CORE_TOOL_HINTS = {
    "wall": INFO_TOOL_WALL_HINT,
    "fence": INFO_TOOL_FENCE_HINT,
    "biome_plains": INFO_TOOL_BIOME_HINT,
    "biome_desert": INFO_TOOL_BIOME_HINT,
    "biome_river": INFO_TOOL_BIOME_HINT,
    "biome_sea": INFO_TOOL_BIOME_HINT,
}

# =====================================================================
# Верхняя панель: главное меню + 5 выпадающих подменю
# =====================================================================

class TopBarPanel:
    _MENU_COLORS = {
        "normal": BUTTON_COLOR, "hover": BUTTON_HOVER,
        "disabled": BUTTON_DISABLED, "text": TEXT_COLOR,
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
        text_w = Button._get_font(FONT_SIZE_BUTTON).size(label)[0]
        return max(min_width, text_w + 24)

    def _build_layout(self):
        gap = 4

        x = 10
        for attr, label in (
                ("btn_game", INFO_BTN_GAME),
                ("btn_landscape", INFO_BTN_LANDSCAPE),
                ("btn_lifes", INFO_BTN_LIFES),
                ("btn_animals", INFO_BTN_ANIMALS),
                ("btn_objects", INFO_BTN_OBJECTS),
                ("btn_nature", INFO_BTN_NATURE),
                ("btn_player", INFO_BTN_PLAYER),
        ):
            width = self._button_width(label)
            setattr(self, attr, Button(pygame.Rect(x, 5, width, BUTTON_HEIGHT), label))
            x += width + self.BUTTON_GAP

        menu_top = 35

        # ---------- Меню "Игра" ----------
        item_x, item_w = self.btn_game.rect.x + 5, 130
        self.btn_create_world = Button(pygame.Rect(item_x, menu_top + 5, item_w, BUTTON_HEIGHT), INFO_BTN_CREATE_WORLD)
        self.btn_load_world = Button(
            pygame.Rect(item_x, menu_top + 5 + (BUTTON_HEIGHT + gap), item_w, BUTTON_HEIGHT), INFO_BTN_LOAD_WORLD)
        self.btn_save_world = Button(
            pygame.Rect(item_x, menu_top + 5 + 2 * (BUTTON_HEIGHT + gap), item_w, BUTTON_HEIGHT), INFO_BTN_SAVE_WORLD)
        self.btn_pause = Button(
            pygame.Rect(item_x, menu_top + 5 + 3 * (BUTTON_HEIGHT + gap), item_w, BUTTON_HEIGHT), INFO_BTN_PAUSE)
        self.btn_instruction = Button(
            pygame.Rect(item_x, menu_top + 5 + 4 * (BUTTON_HEIGHT + gap), item_w, BUTTON_HEIGHT), INFO_BTN_INSTRUCTION)
        self.btn_exit = Button(
            pygame.Rect(item_x, menu_top + 5 + 5 * (BUTTON_HEIGHT + gap), item_w, BUTTON_HEIGHT), INFO_BTN_EXIT)
        self.menu_game_rect = pygame.Rect(
            self.btn_game.rect.x, menu_top, item_w + 10, self.btn_exit.rect.bottom + 5 - menu_top)

        # ---------- Меню "Ландшафт" ----------
        item_x, item_w = self.btn_landscape.rect.x + 5, 110
        self.btn_wall = Button(pygame.Rect(item_x, menu_top + 5, item_w, BUTTON_HEIGHT), INFO_BTN_WALL)
        self.btn_fence = Button(
            pygame.Rect(item_x, menu_top + 5 + (BUTTON_HEIGHT + gap), item_w, BUTTON_HEIGHT), INFO_BTN_FENCE)
        self.btn_biome_plains = Button(
            pygame.Rect(item_x, menu_top + 5 + 2 * (BUTTON_HEIGHT + gap), item_w, BUTTON_HEIGHT), INFO_BTN_BIOME_PLAINS)
        self.btn_biome_desert = Button(
            pygame.Rect(item_x, menu_top + 5 + 3 * (BUTTON_HEIGHT + gap), item_w, BUTTON_HEIGHT), INFO_BTN_BIOME_DESERT)
        self.btn_biome_river = Button(
            pygame.Rect(item_x, menu_top + 5 + 4 * (BUTTON_HEIGHT + gap), item_w, BUTTON_HEIGHT), INFO_BTN_BIOME_RIVER)
        self.btn_biome_sea = Button(
            pygame.Rect(item_x, menu_top + 5 + 5 * (BUTTON_HEIGHT + gap), item_w, BUTTON_HEIGHT), INFO_BTN_BIOME_SEA)
        self.menu_landscape_rect = pygame.Rect(
            self.btn_landscape.rect.x, menu_top, item_w + 10, self.btn_biome_sea.rect.bottom + 5 - menu_top)

        # ---------- Меню "Расы" (generic) ----------
        item_x = self.btn_lifes.rect.x + 5
        self.creature_placement_buttons = {}
        y = menu_top + 5
        lifes_bottom = y
        for descriptor in all_races():
            for placement_mode, label in descriptor.creature_placement_modes:
                btn = Button(pygame.Rect(item_x, y, 90, BUTTON_HEIGHT), label)
                self.creature_placement_buttons[placement_mode] = btn
                lifes_bottom = btn.rect.bottom
                y += BUTTON_HEIGHT + gap
        self.menu_lifes_rect = pygame.Rect(self.btn_lifes.rect.x, menu_top, 100, lifes_bottom + 5 - menu_top)

        # ---------- Меню "Животные" ----------
        item_x = self.btn_animals.rect.x + 5
        self.animal_placement_buttons = {}
        y = menu_top + 5
        animals_bottom = y
        for descriptor in all_animals():
            btn = Button(pygame.Rect(item_x, y, 90, BUTTON_HEIGHT), descriptor.placement_label)
            self.animal_placement_buttons[descriptor.placement_mode] = btn
            animals_bottom = btn.rect.bottom
            y += BUTTON_HEIGHT + gap
        self.menu_animals_rect = pygame.Rect(self.btn_animals.rect.x, menu_top, 100, animals_bottom + 5 - menu_top)

        # ---------- Меню "Объект" ----------
        item_x = self.btn_objects.rect.x + 5
        self.object_placement_buttons = {}
        self.road_tool_buttons = {}
        y = menu_top + 5
        objects_bottom = y

        for obj_type, label in _CORE_OBJECT_MENU_ITEMS:
            btn = Button(pygame.Rect(item_x, y, 130, BUTTON_HEIGHT), label)
            self.object_placement_buttons[obj_type] = btn
            objects_bottom = btn.rect.bottom
            y += BUTTON_HEIGHT + gap

        for descriptor in all_races():
            for spec in descriptor.placeable_objects:
                if not spec.manually_placeable:
                    continue
                btn = Button(pygame.Rect(item_x, y, 130, BUTTON_HEIGHT), spec.label)
                self.object_placement_buttons[spec.obj_type] = btn
                objects_bottom = btn.rect.bottom
                y += BUTTON_HEIGHT + gap

        for spec in all_road_networks():
            if not spec.menu_label:
                continue
            btn = Button(pygame.Rect(item_x, y, 130, BUTTON_HEIGHT), spec.menu_label)
            self.road_tool_buttons[spec.obj_type] = btn
            objects_bottom = btn.rect.bottom
            y += BUTTON_HEIGHT + gap

        self.menu_objects_rect = pygame.Rect(self.btn_objects.rect.x, menu_top, 140, objects_bottom + 5 - menu_top)

        # ---------- Меню "Природа" ----------
        item_x = self.btn_nature.rect.x + 5
        nature_labels = [
            ("btn_fruit", INFO_BTN_FRUIT),
            ("btn_bush", INFO_BTN_BUSH),
            ("btn_water", INFO_BTN_WATER),
            ("btn_tree", INFO_BTN_TREE),
            ("btn_stone", INFO_BTN_STONE),
            ("btn_grass", INFO_BTN_GRASS),
            ("btn_meat", INFO_BTN_MEAT),
        ]
        for i, (attr, label) in enumerate(nature_labels):
            y = menu_top + 5 + i * (BUTTON_HEIGHT + gap)
            setattr(self, attr, Button(pygame.Rect(item_x, y, 90, BUTTON_HEIGHT), label))
        self.menu_nature_rect = pygame.Rect(
            self.btn_nature.rect.x, menu_top, 100, self.btn_meat.rect.bottom + 5 - menu_top)

        # ---------- Меню "Игрок" ----------
        item_x = self.btn_player.rect.x + 5
        self.player_tool_buttons = {}
        all_tools = _CORE_PLAYER_TOOLS + all_player_tools()
        y = menu_top + 5
        player_bottom = y
        for spec in all_tools:
            btn = Button(pygame.Rect(item_x, y, 90, BUTTON_HEIGHT), spec.label)
            self.player_tool_buttons[spec.tool_value] = btn
            player_bottom = btn.rect.bottom
            y += BUTTON_HEIGHT + gap
        self.menu_player_rect = pygame.Rect(self.btn_player.rect.x, menu_top, 100, player_bottom + 5 - menu_top)

        # ---------- Минимально необходимая ширина окна: кнопка "Игрок" + буфер под
        # "Мир: X" + кнопка "Настройки" + отступ от правого края. Больше руками не считаем ----------
        self._settings_btn_width = self._button_width(INFO_BTN_SETTINGS, min_width=90)
        self.min_required_width = (
                self.btn_player.rect.right + self.WORLD_NAME_BUFFER
                + self.BUTTON_GAP + self._settings_btn_width + 10
        )

    def draw(self, screen):
        game = self.game
        pygame.draw.rect(screen, PANEL_COLOR, pygame.Rect(0, 0, screen.get_width(), UI_HEIGHT))
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
            pygame.draw.rect(screen, MENU_BG, self.menu_game_rect)
            self.btn_create_world.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_load_world.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_save_world.enabled = game.world_loaded
            self.btn_save_world.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_pause.enabled = game.world_loaded
            self.btn_pause.label = INFO_BTN_RESUME if game.paused else INFO_BTN_PAUSE
            self.btn_pause.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_instruction.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_exit.draw(screen, mouse_pos, colors=self._MENU_COLORS)

        if game.world_loaded and game.show_landscape_menu:
            pygame.draw.rect(screen, MENU_BG, self.menu_landscape_rect)
            self.btn_wall.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_fence.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_biome_plains.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_biome_desert.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_biome_river.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_biome_sea.draw(screen, mouse_pos, colors=self._MENU_COLORS)

        if game.world_loaded and game.show_lifes_menu:
            pygame.draw.rect(screen, MENU_BG, self.menu_lifes_rect)
            for btn in self.creature_placement_buttons.values():
                btn.draw(screen, mouse_pos, colors=self._MENU_COLORS)

        if game.world_loaded and game.show_animals_menu:
            pygame.draw.rect(screen, MENU_BG, self.menu_animals_rect)
            for btn in self.animal_placement_buttons.values():
                btn.draw(screen, mouse_pos, colors=self._MENU_COLORS)

        if game.world_loaded and game.show_objects_menu:
            pygame.draw.rect(screen, MENU_BG, self.menu_objects_rect)
            for btn in self.object_placement_buttons.values():
                btn.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            for btn in self.road_tool_buttons.values():
                btn.draw(screen, mouse_pos, colors=self._MENU_COLORS)

        if game.world_loaded and game.show_nature_menu:
            pygame.draw.rect(screen, MENU_BG, self.menu_nature_rect)
            self.btn_fruit.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_bush.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_water.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_tree.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_stone.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_grass.draw(screen, mouse_pos, colors=self._MENU_COLORS)
            self.btn_meat.draw(screen, mouse_pos, colors=self._MENU_COLORS)

        if game.world_loaded and game.show_player_menu:
            pygame.draw.rect(screen, MENU_BG, self.menu_player_rect)
            for btn in self.player_tool_buttons.values():
                btn.draw(screen, mouse_pos, colors=self._MENU_COLORS)

        self._draw_settings_button(screen, mouse_pos)

        if game.world_loaded and game.world_path:
            self._draw_world_name(screen)

    def _draw_settings_button(self, screen, mouse_pos):
        window_w = screen.get_width()
        btn_w, btn_h = self._settings_btn_width, BUTTON_HEIGHT
        rect = pygame.Rect(window_w - 10 - btn_w, 5, btn_w, btn_h)
        self.btn_settings = rect

        color = BUTTON_HOVER if rect.collidepoint(mouse_pos) else BUTTON_COLOR
        pygame.draw.rect(screen, color, rect, border_radius=4)
        txt = self.font.render(INFO_BTN_SETTINGS, True, TEXT_COLOR)
        screen.blit(txt, txt.get_rect(center=rect.center))

    def _draw_world_name(self, screen):
        game = self.game
        world_name = os.path.basename(game.world_path)
        if world_name.endswith(WORLD_EXTENSION):
            world_name = world_name[:-len(WORLD_EXTENSION)]
        name_full = INFO_WORLD_NAME_TEMPLATE.format(world_name=world_name)

        min_x = self.btn_player.rect.right + 20
        right_limit = self.btn_settings.x - 10
        available_for_name = right_limit - min_x
        if available_for_name <= 30:
            return

        name_txt = self.font.render(name_full, True, TEXT_COLOR)
        if name_txt.get_width() > available_for_name:
            truncated = name_full
            while truncated and self.font.size(truncated + "…")[0] > available_for_name:
                truncated = truncated[:-1]
            name_txt = self.font.render((truncated + "…") if truncated else "", True, TEXT_COLOR)
        if name_txt.get_width() > 0:
            name_x = right_limit - name_txt.get_width()
            screen.blit(name_txt, (name_x, 10))

# =====================================================================
# Плашка выбранного объекта (не существа) — core-часть + расовые расширения
# =====================================================================

class ObjectPanel:

    MIN_WIDTH = 200
    MAX_WIDTH = 420
    LINE_HEIGHT = 22

    def __init__(self, game, font):
        self.game = game
        self.font = font

    def _wrap_text(self, text, max_width):
        words = text.split(' ')
        lines = []
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            if self.font.size(test)[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines if lines else [""]

    def _get_object_anchor_pos(self, obj):
        if hasattr(obj, "x"):
            return (obj.x, obj.y)
        if hasattr(obj, "points") and obj.points:
            avg_x = sum(p[0] for p in obj.points) / len(obj.points)
            avg_y = sum(p[1] for p in obj.points) / len(obj.points)
            return (avg_x, avg_y)
        return (0, 0)

    def _get_resource_label(self, obj):
        if hasattr(obj, "wood"):
            return INFO_INFO_TREE_WOOD.format(count=int(obj.wood))
        if hasattr(obj, "stone") and not hasattr(obj, "fruits") and not hasattr(obj, "build_type"):
            return INFO_INFO_STONE_AMOUNT.format(count=int(obj.stone))
        if hasattr(obj, "charges") and hasattr(obj, "max_charges"):
            return INFO_INFO_WATER_CHARGES.format(count=int(obj.charges))
        if hasattr(obj, "food"):
            return INFO_INFO_FOOD_AMOUNT.format(count=int(obj.food))
        if hasattr(obj, "amount"):
            return INFO_INFO_RESOURCE_AMOUNT.format(count=int(obj.amount))
        return None

    def _collect_extra_lines(self, obj):
        lines = []
        for extra_fn in all_object_panel_extensions():
            lines.extend(extra_fn(obj, self.game.world.creatures))
        for extra_fn in all_animal_object_panel_extensions():
            lines.extend(extra_fn(obj, self.game.world.creatures))
        return lines

    def draw(self, screen):
        game = self.game
        obj = game.selected_object
        if not obj:
            return

        resource_label = self._get_resource_label(obj)
        extra_lines = self._collect_extra_lines(obj)

        type_name = obj.get_type_name()
        created_str = time.strftime("%H:%M:%S %d.%m", time.localtime(obj.created))
        created_label = INFO_INFO_CREATED.format(created=created_str)
        hint_label = INFO_INFO_DELETE_HINT

        # ---------- Ширина подгоняется под самый длинный текст, но с потолком под размер окна ----------
        screen_w, screen_h = screen.get_width(), screen.get_height()
        max_box_width = max(self.MIN_WIDTH, min(self.MAX_WIDTH, screen_w - 40))

        natural_widths = [
            self.font.size(type_name)[0],
            self.font.size(created_label)[0],
            self.font.size(hint_label)[0],
        ]
        if resource_label:
            natural_widths.append(self.font.size(resource_label)[0])
        for text, _color in extra_lines:
            natural_widths.append(self.font.size(text)[0])

        content_max = max(natural_widths) if natural_widths else 0
        box_width = int(max(self.MIN_WIDTH, min(max_box_width, content_max + 20)))
        text_max_width = box_width - 20

        # ---------- То, что не влезло даже на максимальной ширине, переносим на несколько строк ----------
        resource_sub_lines = self._wrap_text(resource_label, text_max_width) if resource_label else []
        extra_sub_lines = []
        for text, color in extra_lines:
            for sub in self._wrap_text(text, text_max_width):
                extra_sub_lines.append((sub, color))

        body_line_count = len(resource_sub_lines) + len(extra_sub_lines)
        box_height = 78 + self.LINE_HEIGHT * body_line_count

        anchor = game.selected_object_click_pos or self._get_object_anchor_pos(obj)
        screen_pos = game.camera.apply_pos(anchor)

        box_x = screen_pos[0] + 20
        box_y = screen_pos[1] - 15
        box_x = max(5, min(box_x, screen_w - box_width - 5))
        box_y = max(UI_HEIGHT + 5, min(box_y, screen_h - box_height - 5))

        rect = pygame.Rect(int(box_x), int(box_y), box_width, box_height)
        pygame.draw.rect(screen, INFO_PANEL_COLOR, rect)
        pygame.draw.rect(screen, INFO_PANEL_BORDER, rect, 2)

        type_txt = self.font.render(type_name, True, TEXT_COLOR)
        screen.blit(type_txt, (rect.x + 10, rect.y + 8))

        created_txt = self.font.render(created_label, True, TEXT_COLOR)
        screen.blit(created_txt, (rect.x + 10, rect.y + 34))

        next_y = rect.y + 56

        for line in resource_sub_lines:
            line_txt = self.font.render(line, True, (200, 200, 200))
            screen.blit(line_txt, (rect.x + 10, next_y))
            next_y += self.LINE_HEIGHT

        for line, color in extra_sub_lines:
            line_txt = self.font.render(line, True, color)
            screen.blit(line_txt, (rect.x + 10, next_y))
            next_y += self.LINE_HEIGHT

        hint_txt = self.font.render(hint_label, True, (190, 190, 190))
        screen.blit(hint_txt, (rect.x + 10, next_y))

# =====================================================================
# Миникарта — core-пайплайн слоёв + расовые слои через insert_after
# (по образцу WorldRenderer._build_render_pipeline)
# =====================================================================

def _mm_draw_roads(panel, screen, game, to_minimap, scale, display):
    if display["minimap_show_roads"]:
        for road in game.world.roads:
            if road.rating == "useful" and len(road.points) >= 2:
                pts = [to_minimap(px, py) for px, py in road.points]
                pygame.draw.lines(screen, (255, 255, 255), False, pts, 1)

def _mm_draw_landscape(panel, screen, game, to_minimap, scale, display):
    for wall in game.world.walls:
        if len(wall.points) >= 2:
            pts = [to_minimap(px, py) for px, py in wall.points]
            pygame.draw.lines(screen, WALL_COLOR, False, pts, 2)
    for fence in game.world.fences:
        if len(fence.points) >= 2:
            pts = [to_minimap(px, py) for px, py in fence.points]
            pygame.draw.lines(screen, FENCE_COLOR, False, pts, 1)

def _mm_draw_water(panel, screen, game, to_minimap, scale, display):
    if display["minimap_show_water"]:
        for water in game.world.water_puddles:
            pos = to_minimap(water.x, water.y)
            pygame.draw.circle(screen, (60, 140, 220), (int(pos[0]), int(pos[1])), 2)

def _mm_draw_bushes(panel, screen, game, to_minimap, scale, display):
    if display["minimap_show_bushes"]:
        for bush in game.world.bushes:
            pos = to_minimap(bush.x, bush.y)
            pygame.draw.circle(screen, BUSH_COLOR, (int(pos[0]), int(pos[1])), 2)

def _mm_draw_trees(panel, screen, game, to_minimap, scale, display):
    if display["minimap_show_trees"]:
        for tree in game.world.trees:
            pos = to_minimap(tree.x, tree.y)
            pygame.draw.circle(screen, TREE_COLOR_LEAVES, (int(pos[0]), int(pos[1])), 2)

def _mm_draw_stones(panel, screen, game, to_minimap, scale, display):
    if display["minimap_show_stones"]:
        for stone in game.world.stones:
            pos = to_minimap(stone.x, stone.y)
            pygame.draw.circle(screen, STONE_COLOR, (int(pos[0]), int(pos[1])), 2)

def _mm_draw_fruits(panel, screen, game, to_minimap, scale, display):
    if display["minimap_show_fruits"]:
        for fruit in game.world.fruits:
            if fruit.active:
                pos = to_minimap(fruit.x, fruit.y)
                pygame.draw.circle(screen, FRUIT_COLOR, (int(pos[0]), int(pos[1])), 2)

def _mm_draw_spikes(panel, screen, game, to_minimap, scale, display):
    if display["minimap_show_spikes"]:
        for spike in game.world.spikes:
            pos = to_minimap(spike.x, spike.y)
            pygame.draw.circle(screen, (255, 165, 0), (int(pos[0]), int(pos[1])), 2)

def _mm_draw_creatures(panel, screen, game, to_minimap, scale, display):
    for creature in game.world.creatures:
        pos = to_minimap(creature.x, creature.y)
        color = creature.draw_minimap_color() if hasattr(creature, "draw_minimap_color") else (200, 30, 30)
        pygame.draw.circle(screen, color, (int(pos[0]), int(pos[1])), 2)

def _default_animal_minimap_marker(screen, pos):
    pygame.draw.circle(screen, (225, 205, 90), (int(pos[0]), int(pos[1])), 2)

def _mm_draw_animals(panel, screen, game, to_minimap, scale, display):
    for descriptor in all_animals():
        checkbox_key = f"minimap_show_animal_{descriptor.animal_name}"
        if not display.get(checkbox_key, True):
            continue
        draw_marker = descriptor.minimap_marker_fn or _default_animal_minimap_marker
        for animal in getattr(game.world, descriptor.world_collection):
            pos = to_minimap(animal.x, animal.y)
            draw_marker(screen, pos)

_CORE_MINIMAP_LAYERS = (
    ("roads", _mm_draw_roads),
    ("landscape", _mm_draw_landscape),
    ("water", _mm_draw_water),
    ("bushes", _mm_draw_bushes),
    ("trees", _mm_draw_trees),
    ("stones", _mm_draw_stones),
    ("fruits", _mm_draw_fruits),
    ("spikes", _mm_draw_spikes),
    ("creatures", _mm_draw_creatures),
    ("animals", _mm_draw_animals),
)

class MinimapPanel:

    def __init__(self, game, font):
        self.game = game
        self.font = font
        self.rect = pygame.Rect(0, 0, MINIMAP_MAX_WIDTH, MINIMAP_MAX_HEIGHT)
        self._biome_layer = None
        self._biome_layer_key = None
        self._pipeline = self._build_pipeline()
        self._dos_overlay_surface = None
        self._dos_cut_surface = None
        self._dos_surfaces_size = None
        self.rebuild_layout(WINDOW_WIDTH, WINDOW_HEIGHT)

    @staticmethod
    def _build_pipeline():
        race_layers_by_anchor = {}
        for layer in all_minimap_layers():
            race_layers_by_anchor.setdefault(layer.insert_after, []).append(layer)

        pipeline = []
        for key, fn in _CORE_MINIMAP_LAYERS:
            pipeline.append(fn)
            for layer in race_layers_by_anchor.get(key, []):
                pipeline.append(layer.draw_fn)
        return pipeline

    def rebuild_layout(self, window_w, window_h):
        world_w = self.game.camera.world_w
        world_h = self.game.camera.world_h
        ratio = world_w / world_h

        if ratio >= 1:
            mm_w = MINIMAP_MAX_WIDTH
            mm_h = int(mm_w / ratio)
            if mm_h < MINIMAP_MIN_HEIGHT:
                mm_h = MINIMAP_MIN_HEIGHT
                mm_w = int(mm_h * ratio)
        else:
            mm_h = MINIMAP_MAX_HEIGHT
            mm_w = int(mm_h * ratio)
            if mm_w < MINIMAP_MIN_WIDTH:
                mm_w = MINIMAP_MIN_WIDTH
                mm_h = int(mm_w / ratio)

        mm_w = min(mm_w, MINIMAP_MAX_WIDTH)
        mm_h = min(mm_h, MINIMAP_MAX_HEIGHT)

        self.rect = pygame.Rect(
            MINIMAP_MARGIN, window_h - mm_h - MINIMAP_MARGIN,
            mm_w, mm_h
        )

    def _draw_biomes(self, screen, rect):
        game = self.game
        grid = game.biome_manager.grid
        if grid is None:
            return

        cache_key = (id(grid), game.world.landscape_version, rect.width, rect.height)
        if self._biome_layer is None or self._biome_layer_key != cache_key:
            self._biome_layer = self._build_biome_layer(grid, rect.width, rect.height)
            self._biome_layer_key = cache_key

        screen.blit(self._biome_layer, rect.topleft)

    def _build_biome_layer(self, grid, width, height):
        layer = pygame.Surface((width, height))
        scale_x = width / self.game.camera.world_w
        scale_y = height / self.game.camera.world_h
        cell_w = max(1, int(math.ceil(grid.cell_size * scale_x)))
        cell_h = max(1, int(math.ceil(grid.cell_size * scale_y)))

        for row in range(grid.rows):
            py = int(row * grid.cell_size * scale_y)
            for col in range(grid.cols):
                biome = grid.cells[row * grid.cols + col]
                color = MINIMAP_BIOME_COLOR.get(biome, MINIMAP_BIOME_COLOR[BIOME_PLAINS])
                px = int(col * grid.cell_size * scale_x)
                pygame.draw.rect(layer, color, (px, py, cell_w, cell_h))
        return layer

    def draw(self, screen):
        game = self.game
        display = game.display_settings
        rect = self.rect
        pygame.draw.rect(screen, MINIMAP_BG_COLOR, rect)

        self._draw_biomes(screen, rect)

        scale_x = rect.width / game.camera.world_w
        scale_y = rect.height / game.camera.world_h

        def to_minimap(wx, wy):
            return (rect.x + wx * scale_x, rect.y + wy * scale_y)

        for draw_fn in self._pipeline:
            draw_fn(self, screen, game, to_minimap, (scale_x, scale_y), display)

        favorite = self._find_favorite_entity(game.favorite_id)
        self._draw_dos_overlay(screen, rect, (scale_x, scale_y), favorite)
        if favorite is not None:
            self._draw_favorite_marker(screen, to_minimap, favorite)

        cam = game.camera
        view_x = rect.x + cam.x * scale_x
        view_y = rect.y + cam.y * scale_y
        view_w = max(2, cam.camera.width * scale_x)
        view_h = max(2, cam.camera.height * scale_y)
        view_rect = pygame.Rect(int(view_x), int(view_y), int(view_w), int(view_h))
        pygame.draw.rect(screen, MINIMAP_VIEWPORT_COLOR, view_rect, 2)

        pygame.draw.rect(screen, MINIMAP_BORDER_COLOR, rect, 2)

        hint_txt = self.font.render("Tab", True, (170, 170, 170))
        screen.blit(hint_txt, (rect.right - hint_txt.get_width() - 4, rect.y - 20))

    def _find_favorite_entity(self, favorite_id):
        if favorite_id is None:
            return None
        game = self.game
        for c in game.world.creatures:
            if c.id == favorite_id and not c.is_dead:
                return c
        for descriptor in all_animals():
            for animal in getattr(game.world, descriptor.world_collection):
                if animal.id == favorite_id:
                    return animal
        return None

    def _get_dos_surfaces(self, size):
        if self._dos_surfaces_size != size:
            self._dos_overlay_surface = pygame.Surface(size, pygame.SRCALPHA)
            self._dos_cut_surface = pygame.Surface(size, pygame.SRCALPHA)
            self._dos_surfaces_size = size
        return self._dos_overlay_surface, self._dos_cut_surface

    def _draw_dos_overlay(self, screen, rect, scale, favorite):
        game = self.game
        scale_x, scale_y = scale

        overlay, cut = self._get_dos_surfaces(rect.size)
        overlay.fill((0, 0, 0, MINIMAP_SIMULATION_AREA_ALPHA))
        cut.fill((0, 0, 0, 0))

        units = game.display_settings.get("simulation_area_units", SIMULATION_AREA_DEFAULT_UNITS)
        units = max(SIMULATION_AREA_MIN_UNITS, min(SIMULATION_AREA_MAX_UNITS, units))
        margin = units * SIMULATION_AREA_PX_PER_UNIT
        cam = game.camera

        sim_x = (cam.x - margin) * scale_x
        sim_y = (cam.y - margin) * scale_y
        sim_w = (cam.camera.width + margin * 2) * scale_x
        sim_h = (cam.camera.height + margin * 2) * scale_y
        pygame.draw.rect(cut, (255, 255, 255, 255),
                         pygame.Rect(int(sim_x), int(sim_y), int(sim_w), int(sim_h)))

        if favorite is not None:
            vision = (favorite.effective_vision_radius()
                      if hasattr(favorite, "effective_vision_radius") else DEFAULT_VISION_RADIUS)
            local_x = favorite.x * scale_x
            local_y = favorite.y * scale_y
            radius_px = vision * scale_x
            pygame.draw.circle(cut, (255, 255, 255, 255), (int(local_x), int(local_y)), int(radius_px))

        overlay.blit(cut, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
        screen.blit(overlay, rect.topleft)

    def _draw_favorite_marker(self, screen, to_minimap, favorite):
        fx, fy = to_minimap(favorite.x, favorite.y)
        size = MINIMAP_FAVORITE_STAR_SIZE
        points = star_points(fx, fy, size, size * 0.45)
        pygame.draw.polygon(screen, FAVORITE_STAR_COLOR, points)
        pygame.draw.polygon(screen, FAVORITE_STAR_BORDER, points, 1)

# =====================================================================
# Экраны "Создание мира" / "Загрузка мира" — без изменений (core)
# =====================================================================

class WorldScreensPanel:

    def __init__(self, game):
        self.game = game
        self.title_font = pygame.font.SysFont(FONT_NAME, FONT_SIZE_TITLE)
        self.label_font = pygame.font.SysFont(FONT_NAME, FONT_SIZE_LABEL)
        self.small_font = pygame.font.SysFont(FONT_NAME, FONT_SIZE_SMALL)
        self.lw_title_font = pygame.font.SysFont(FONT_NAME, 26)
        self.lw_label_font = pygame.font.SysFont(FONT_NAME, 18)
        self.lw_small_font = pygame.font.SysFont(FONT_NAME, 16)

        self.ws_create_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.lw_list_rect = None
        self.lw_info_rect = None
        self.lw_load_btn_rect = None
        self.lw_delete_btn_rect = None
        self.lw_info_content_height = 0
        self.world_screen_back_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.ws_animals_checkbox_rect = pygame.Rect(0, 0, 0, 0)
        self.ws_biome_slider_rects = {}

    def draw_create_world_screen(self, screen, state, content_rect):
        pygame.draw.rect(screen, WORLD_SCREEN_BG, content_rect)
        margin = WORLD_SCREEN_MARGIN
        base_x = content_rect.x + margin
        base_y = content_rect.y + margin

        title_txt = self.title_font.render(INFO_WS_SCREEN_TITLE, True, WORLD_SCREEN_TEXT)
        screen.blit(title_txt, (base_x, base_y))

        # ---------- Строка 1: название мира + сид (в одной строке) ----------
        row1_y = base_y + 60
        name_label = self.label_font.render(INFO_WS_TITLE_NAME, True, WORLD_SCREEN_TEXT)
        screen.blit(name_label, (base_x, row1_y + 6))
        state.name_input.rect = pygame.Rect(base_x + 150, row1_y, 230, 34)
        state.name_input.draw(screen, self.label_font)

        seed_x = base_x + 150 + 230 + 30
        seed_label = self.label_font.render(INFO_WS_TITLE_SEED, True, WORLD_SCREEN_TEXT)
        screen.blit(seed_label, (seed_x, row1_y + 6))
        state.seed_input.rect = pygame.Rect(seed_x + 110, row1_y, 160, 34)
        state.seed_input.draw(screen, self.label_font)

        # ---------- Строка 2: размер мира ----------
        row2_y = row1_y + 60
        size_label = self.label_font.render(INFO_WS_TITLE_SIZE, True, WORLD_SCREEN_TEXT)
        screen.blit(size_label, (base_x, row2_y + 6))

        length_label = self.label_font.render(INFO_WS_LENGTH, True, WORLD_SCREEN_TEXT)
        screen.blit(length_label, (base_x + 150, row2_y + 6))
        state.width_input.rect = pygame.Rect(base_x + 230, row2_y, 100, 34)
        state.width_input.draw(screen, self.label_font)

        width_label = self.label_font.render(INFO_WS_WIDTH, True, WORLD_SCREEN_TEXT)
        screen.blit(width_label, (base_x + 360, row2_y + 6))
        state.height_input.rect = pygame.Rect(base_x + 430, row2_y, 100, 34)
        state.height_input.draw(screen, self.label_font)

        # ---------- Строка 3: автогенерация животных ----------
        row3_y = row2_y + 60
        self.ws_animals_checkbox_rect = pygame.Rect(base_x, row3_y, 20, 20)
        self._draw_checkbox(screen, self.ws_animals_checkbox_rect, state.generate_animals)
        animals_label = self.label_font.render(INFO_WS_GENERATE_ANIMALS, True, WORLD_SCREEN_TEXT)
        screen.blit(animals_label, (self.ws_animals_checkbox_rect.right + 10, row3_y - 1))

        # ---------- Строка 4+: соотношение биомов ----------
        row4_y = row3_y + 40
        biome_title = self.label_font.render(INFO_WS_TITLE_BIOME_RATIOS, True, WORLD_SCREEN_TEXT)
        screen.blit(biome_title, (base_x, row4_y))

        self.ws_biome_slider_rects = {}
        slider_y = row4_y + 34
        name_col_w = 130
        percent_col_w = 55
        available_width = content_rect.right - margin - (base_x + name_col_w + percent_col_w)
        slider_w = max(120, min(360, available_width))

        for biome, slider in state.biome_sliders.items():
            biome_label = self.small_font.render(BIOME_LABELS.get(biome, biome), True, WORLD_SCREEN_TEXT)
            screen.blit(biome_label, (base_x, slider_y + 6))

            percent_txt = self.small_font.render(f"{int(round(slider.value * 100))}%", True, WORLD_SCREEN_TEXT)
            screen.blit(percent_txt, (base_x + name_col_w, slider_y + 6))

            slider.rect = pygame.Rect(base_x + name_col_w + percent_col_w, slider_y, slider_w, 18)
            slider.draw(screen, MINIMAP_BIOME_COLOR.get(biome, (150, 150, 150)))
            self.ws_biome_slider_rects[biome] = slider.rect

            slider_y += 30

        total_ratio = sum(s.value for s in state.biome_sliders.values())
        total_color = WORLD_SCREEN_ERROR_COLOR if total_ratio > 1.001 else WORLD_SCREEN_HINT_COLOR
        total_txt = self.small_font.render(f"Сумма: {int(round(total_ratio * 100))}%", True, total_color)
        screen.blit(total_txt, (base_x, slider_y + 4))

        if state.error_text:
            err_txt = self.small_font.render(state.error_text, True, WORLD_SCREEN_ERROR_COLOR)
            screen.blit(err_txt, (base_x, content_rect.bottom - margin - 36 - 26))

        self.ws_create_btn_rect = pygame.Rect(base_x, content_rect.bottom - margin - 36, 150, 36)
        mouse_pos = pygame.mouse.get_pos()
        btn_color = BUTTON_HOVER if self.ws_create_btn_rect.collidepoint(mouse_pos) else BUTTON_COLOR
        pygame.draw.rect(screen, btn_color, self.ws_create_btn_rect, border_radius=4)
        btn_txt = self.label_font.render(INFO_BTN_WS_CREATE, True, TEXT_COLOR)
        screen.blit(btn_txt, btn_txt.get_rect(center=self.ws_create_btn_rect.center))
        self._draw_back_button(screen, self.label_font, content_rect)

    def _draw_checkbox(self, screen, rect, checked):
        mouse_pos = pygame.mouse.get_pos()
        bg = (55, 55, 55) if rect.collidepoint(mouse_pos) else (40, 40, 40)
        pygame.draw.rect(screen, bg, rect)
        pygame.draw.rect(screen, WORLD_SCREEN_TEXT, rect, 1)
        if checked:
            pygame.draw.line(screen, (120, 230, 120), (rect.x + 3, rect.y + 10), (rect.x + 8, rect.y + 15), 2)
            pygame.draw.line(screen, (120, 230, 120), (rect.x + 8, rect.y + 15), (rect.x + 17, rect.y + 3), 2)

    def draw_load_world_screen(self, screen, state, content_rect):
        pygame.draw.rect(screen, WORLD_SCREEN_BG, content_rect)
        margin = WORLD_SCREEN_MARGIN

        title_txt = self.lw_title_font.render(INFO_LW_SCREEN_TITLE, True, WORLD_SCREEN_TEXT)
        screen.blit(title_txt, (content_rect.x + margin, content_rect.y + margin))

        list_top = content_rect.y + margin + 60
        list_width = content_rect.width // 2 - margin - 15
        list_height = content_rect.bottom - list_top - margin
        self.lw_list_rect = pygame.Rect(content_rect.x + margin, list_top, list_width, list_height)
        pygame.draw.rect(screen, WORLD_SCREEN_PANEL_BG, self.lw_list_rect)
        pygame.draw.rect(screen, WORLD_SCREEN_PANEL_BORDER, self.lw_list_rect, 2)

        self._draw_world_list(screen, state, self.lw_label_font)

        self.lw_info_rect = None
        self.lw_load_btn_rect = None
        self.lw_delete_btn_rect = None
        self.lw_info_content_height = 0

        info_x = content_rect.x + content_rect.width // 2 + 15
        if state.selected_index is not None and 0 <= state.selected_index < len(state.entries):
            entry = state.entries[state.selected_index]
            self._draw_world_info_panel(screen, state, entry, self.lw_label_font, self.lw_small_font, content_rect)
        else:
            hint_txt = self.lw_label_font.render(INFO_LW_SELECT_HINT, True, WORLD_SCREEN_HINT_COLOR)
            screen.blit(hint_txt, (info_x + 10, list_top + 10))

        self._draw_back_button(screen, self.lw_label_font, content_rect)

    def _draw_world_list(self, screen, state, font):
        rect = self.lw_list_rect

        if not state.entries:
            empty_txt = font.render(INFO_LW_EMPTY_LIST, True, WORLD_SCREEN_HINT_COLOR)
            screen.blit(empty_txt, (rect.x + 10, rect.y + 10))
            return

        prev_clip = screen.get_clip()
        screen.set_clip(rect)

        content_height = len(state.entries) * WORLD_LIST_ITEM_HEIGHT
        state.list_scroll.update_bounds(content_height, rect.height)
        scroll = state.list_scroll.offset
        mouse_pos = pygame.mouse.get_pos()

        for index, entry in enumerate(state.entries):
            item_y = rect.y + index * WORLD_LIST_ITEM_HEIGHT - scroll
            if item_y + WORLD_LIST_ITEM_HEIGHT < rect.y or item_y > rect.bottom:
                continue
            item_rect = pygame.Rect(rect.x, item_y, rect.width, WORLD_LIST_ITEM_HEIGHT)
            if index == state.selected_index:
                color = WORLD_LIST_ITEM_SELECTED_COLOR
            elif item_rect.collidepoint(mouse_pos):
                color = WORLD_LIST_ITEM_HOVER_COLOR
            else:
                color = WORLD_LIST_ITEM_COLOR
            pygame.draw.rect(screen, color, item_rect)
            pygame.draw.rect(screen, WORLD_SCREEN_PANEL_BORDER, item_rect, 1)
            name_txt = font.render(entry.display_name, True, WORLD_SCREEN_TEXT)
            screen.blit(name_txt, (item_rect.x + 10,
                                   item_rect.y + (WORLD_LIST_ITEM_HEIGHT - name_txt.get_height()) // 2))

        screen.set_clip(prev_clip)
        state.list_scroll.draw_scrollbar(screen, rect)

    def _draw_back_button(self, screen, font, content_rect):
        margin = WORLD_SCREEN_MARGIN
        width, height = 110, 34
        rect = pygame.Rect(content_rect.right - margin - width, content_rect.y + margin, width, height)
        self.world_screen_back_btn_rect = rect

        mouse_pos = pygame.mouse.get_pos()
        color = CLOSE_BUTTON_HOVER if rect.collidepoint(mouse_pos) else CLOSE_BUTTON_COLOR
        pygame.draw.rect(screen, color, rect, border_radius=4)
        txt = font.render(INFO_BTN_BACK, True, TEXT_COLOR)
        screen.blit(txt, txt.get_rect(center=rect.center))

    def _build_world_info_lines(self, entry):
        meta = entry.meta
        lines = [INFO_LW_INFO_NAME.format(name=entry.display_name)]

        created_ts = meta.get("created")
        if created_ts:
            created_str = time.strftime("%H:%M:%S %d.%m.%Y", time.localtime(created_ts))
            lines.append(INFO_LW_INFO_CREATED.format(created=created_str))

        width = meta.get("world_width", WORLD_DEFAULT_SIZE[0])
        height = meta.get("world_height", WORLD_DEFAULT_SIZE[1])
        lines.append(INFO_LW_INFO_SIZE.format(w=width, h=height))

        seed = meta.get("seed")
        if seed is not None:
            lines.append(INFO_LW_INFO_SEED.format(seed=seed))

        counts = entry.counts or {}
        lines.append(INFO_LW_INFO_CREATURES.format(count=counts.get("creatures", 0)))
        lines.append(INFO_LW_INFO_FRUITS.format(count=counts.get("fruits", 0)))
        lines.append(INFO_LW_INFO_SPIKES.format(count=counts.get("spikes", 0)))
        lines.append(INFO_LW_INFO_WATER.format(count=counts.get("water", 0)))
        lines.append(INFO_LW_INFO_BUSHES.format(count=counts.get("bushes", 0)))
        lines.append(INFO_LW_INFO_CAMPFIRES.format(count=counts.get("campfires", 0)))
        lines.append(INFO_LW_INFO_ROADS.format(count=counts.get("roads", 0)))

        lines.append(INFO_LW_INFO_ANIMALS_TOTAL.format(count=counts.get("animals_total", 0)))
        animals_by_type = counts.get("animals_by_type", {})
        for descriptor in all_animals():
            lines.append(INFO_LW_INFO_ANIMAL_TYPE.format(
                label=descriptor.placement_label,
                count=animals_by_type.get(descriptor.animal_name, 0)))

        return lines

    def _draw_world_info_panel(self, screen, state, entry, label_font, small_font, content_rect):
        margin = WORLD_SCREEN_MARGIN
        info_x = content_rect.x + content_rect.width // 2 + 15
        info_width = content_rect.right - margin - info_x
        info_top = content_rect.y + margin + 60
        max_height = content_rect.bottom - info_top - margin

        lines = self._build_world_info_lines(entry)
        line_height = 22

        buttons_area_height = 76 if state.confirm_delete else 50

        content_height = len(lines) * line_height + 16 + buttons_area_height
        info_height = min(content_height, max_height)

        info_rect = pygame.Rect(info_x, info_top, info_width, info_height)
        self.lw_info_rect = info_rect
        self.lw_info_content_height = content_height
        pygame.draw.rect(screen, WORLD_SCREEN_PANEL_BG, info_rect)
        pygame.draw.rect(screen, WORLD_SCREEN_PANEL_BORDER, info_rect, 2)

        text_area_height = max(0, info_height - buttons_area_height)
        text_rect = pygame.Rect(info_rect.x, info_rect.y, info_rect.width, text_area_height)
        prev_clip = screen.get_clip()
        screen.set_clip(text_rect)

        state.info_scroll.update_bounds(content_height, text_area_height)
        scroll = state.info_scroll.offset

        y = info_rect.y + 12 - scroll
        for line in lines:
            line_txt = small_font.render(line, True, WORLD_SCREEN_TEXT)
            screen.blit(line_txt, (info_rect.x + 12, y))
            y += line_height

        screen.set_clip(prev_clip)
        if content_height > text_area_height:
            state.info_scroll.draw_scrollbar(screen, text_rect)

        btn_area_top = info_rect.bottom - buttons_area_height + 8
        btn_y = btn_area_top

        if state.confirm_delete:
            warn_txt = small_font.render(INFO_LW_CONFIRM_DELETE, True, WORLD_SCREEN_ERROR_COLOR)
            screen.blit(warn_txt, (info_rect.x + 12, btn_area_top))
            btn_y = btn_area_top + warn_txt.get_height() + 8

        self.lw_load_btn_rect = pygame.Rect(info_rect.x + 12, btn_y, 130, 32)
        self.lw_delete_btn_rect = pygame.Rect(info_rect.x + 152, btn_y, 130, 32)

        mouse_pos = pygame.mouse.get_pos()
        load_color = BUTTON_HOVER if self.lw_load_btn_rect.collidepoint(mouse_pos) else BUTTON_COLOR
        pygame.draw.rect(screen, load_color, self.lw_load_btn_rect, border_radius=4)
        load_txt = label_font.render(INFO_BTN_LW_LOAD, True, TEXT_COLOR)
        screen.blit(load_txt, load_txt.get_rect(center=self.lw_load_btn_rect.center))

        delete_color = CLOSE_BUTTON_HOVER if self.lw_delete_btn_rect.collidepoint(mouse_pos) else CLOSE_BUTTON_COLOR
        pygame.draw.rect(screen, delete_color, self.lw_delete_btn_rect, border_radius=4)
        delete_txt = label_font.render(INFO_BTN_LW_DELETE, True, TEXT_COLOR)
        screen.blit(delete_txt, delete_txt.get_rect(center=self.lw_delete_btn_rect.center))

# =====================================================================
# Экран "Настройки" — core-чекбоксы + расовые (через display_checkboxes)
# =====================================================================

SETTINGS_TABS = (
    ("technical", INFO_SETTINGS_TAB_TECHNICAL),
    ("display", INFO_SETTINGS_TAB_DISPLAY),
)

class SettingsPanel:

    PANEL_WIDTH = 700
    PANEL_HEIGHT = 650
    SIDEBAR_RATIO = 0.20
    ROW_HEIGHT = 34
    CHECKBOX_SIZE = 18

    def __init__(self, game, font):
        self.game = game
        self.font = font
        self.title_font = pygame.font.SysFont(FONT_NAME, FONT_SIZE_TITLE)

        self._checkboxes = all_display_checkbox_specs()
        self._technical_checkboxes = all_technical_checkbox_specs()
        self._technical_sliders = all_technical_slider_specs()

        self.panel_rect = pygame.Rect(0, 0, 0, 0)
        self.settings_tab_technical_rect = pygame.Rect(0, 0, 0, 0)
        self.settings_tab_display_rect = pygame.Rect(0, 0, 0, 0)
        self.settings_save_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.settings_back_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.settings_checkbox_rows = {}
        self.settings_slider_rows = {}
        self._slider_dragging_key = None

    def _layout_panel(self, screen):
        window_w, window_h = screen.get_width(), screen.get_height()
        width = min(self.PANEL_WIDTH, window_w - 40)
        height = min(self.PANEL_HEIGHT, window_h - 40)
        x = (window_w - width) // 2
        y = (window_h - height) // 2
        self.panel_rect = pygame.Rect(x, y, width, height)

    def draw(self, screen, state):
        self._layout_panel(screen)
        mouse_pos = pygame.mouse.get_pos()

        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, SETTINGS_OVERLAY_ALPHA))
        screen.blit(overlay, (0, 0))

        panel = self.panel_rect
        pygame.draw.rect(screen, SETTINGS_PANEL_BG, panel)
        pygame.draw.rect(screen, SETTINGS_PANEL_BORDER, panel, 2)

        title_txt = self.title_font.render(INFO_SETTINGS_TITLE, True, WORLD_SCREEN_TEXT)
        screen.blit(title_txt, (panel.x + 16, panel.y + 14))

        content_top = panel.y + 14 + title_txt.get_height() + 14
        buttons_area_height = 56
        content_rect = pygame.Rect(
            panel.x + 12, content_top,
            panel.width - 24, panel.bottom - buttons_area_height - content_top - 10
        )

        sidebar_width = int(content_rect.width * self.SIDEBAR_RATIO)
        sidebar_rect = pygame.Rect(content_rect.x, content_rect.y, sidebar_width, content_rect.height)
        body_rect = pygame.Rect(
            sidebar_rect.right + 12, content_rect.y,
            content_rect.width - sidebar_width - 12, content_rect.height
        )

        pygame.draw.rect(screen, SETTINGS_SIDEBAR_BG, sidebar_rect)

        self._draw_tabs(screen, state, sidebar_rect, mouse_pos)
        self._draw_body(screen, state, body_rect, mouse_pos)
        self._draw_buttons(screen, panel, mouse_pos)

    def _draw_tabs(self, screen, state, sidebar_rect, mouse_pos):
        y = sidebar_rect.y + 8
        for tab_key, tab_label in SETTINGS_TABS:
            rect = pygame.Rect(sidebar_rect.x + 6, y, sidebar_rect.width - 12, BUTTON_HEIGHT)
            if tab_key == "display":
                self.settings_tab_display_rect = rect
            elif tab_key == "technical":
                self.settings_tab_technical_rect = rect

            if state.active_tab == tab_key:
                color = SETTINGS_TAB_SELECTED
            elif rect.collidepoint(mouse_pos):
                color = SETTINGS_TAB_HOVER
            else:
                color = SETTINGS_TAB_COLOR
            pygame.draw.rect(screen, color, rect, border_radius=4)

            label_txt = self.font.render(tab_label, True, TEXT_COLOR)
            screen.blit(label_txt, label_txt.get_rect(center=rect.center))
            y += BUTTON_HEIGHT + 6

    def _draw_body(self, screen, state, body_rect, mouse_pos):
        self.settings_checkbox_rows = {}
        self.settings_slider_rows = {}
        if state.active_tab == "display":
            checkboxes = self._checkboxes
            sliders = ()
        elif state.active_tab == "technical":
            checkboxes = self._technical_checkboxes
            sliders = self._technical_sliders
        else:
            return

        y = body_rect.y
        for key, label in checkboxes:
            row_rect = pygame.Rect(body_rect.x, y, body_rect.width, self.ROW_HEIGHT)
            self.settings_checkbox_rows[key] = row_rect

            cb_y = row_rect.y + (row_rect.height - self.CHECKBOX_SIZE) // 2
            cb_rect = pygame.Rect(row_rect.x, cb_y, self.CHECKBOX_SIZE, self.CHECKBOX_SIZE)

            hovered = row_rect.collidepoint(mouse_pos)
            box_bg = (55, 55, 55) if hovered else (40, 40, 40)
            pygame.draw.rect(screen, box_bg, cb_rect)
            pygame.draw.rect(screen, WORLD_SCREEN_TEXT, cb_rect, 1)
            if state.draft.get(key):
                pygame.draw.line(screen, (120, 230, 120),
                                 (cb_rect.x + 3, cb_rect.y + 9), (cb_rect.x + 7, cb_rect.y + 13), 2)
                pygame.draw.line(screen, (120, 230, 120),
                                 (cb_rect.x + 7, cb_rect.y + 13), (cb_rect.x + 15, cb_rect.y + 3), 2)

            label_txt = self.font.render(label, True, TEXT_COLOR)
            screen.blit(label_txt, (cb_rect.right + 10,
                                    row_rect.y + (row_rect.height - label_txt.get_height()) // 2))

            y += self.ROW_HEIGHT

        if sliders:
            y += 12
            for key, label_template, min_v, max_v, step in sliders:
                y = self._draw_slider_row(screen, state, key, label_template, min_v, max_v, step,
                                          body_rect.x, y, body_rect.width, mouse_pos)

    def _draw_slider_row(self, screen, state, key, label_template, min_v, max_v, step, x, y, width, mouse_pos):
        value = state.draft.get(key, min_v)
        label_txt = self.font.render(label_template.format(value=value), True, TEXT_COLOR)
        screen.blit(label_txt, (x, y))

        bar_y = y + label_txt.get_height() + 6
        bar_rect = pygame.Rect(x, bar_y, width, 10)
        pygame.draw.rect(screen, (30, 30, 30), bar_rect)

        ratio = (value - min_v) / (max_v - min_v) if max_v > min_v else 0.0
        fill_w = max(4, int(bar_rect.width * max(0.0, min(1.0, ratio))))
        fill_rect = pygame.Rect(bar_rect.x, bar_rect.y, fill_w, bar_rect.height)
        fill_color = (100, 160, 210) if self._slider_dragging_key == key else BUTTON_COLOR
        pygame.draw.rect(screen, fill_color, fill_rect)
        pygame.draw.rect(screen, (15, 15, 15), bar_rect, 1)

        handle_rect = pygame.Rect(0, 0, 4, bar_rect.height + 6)
        handle_rect.center = (bar_rect.x + fill_w, bar_rect.centery)
        pygame.draw.rect(screen, (240, 240, 240), handle_rect, border_radius=2)

        self.settings_slider_rows[key] = bar_rect
        return bar_rect.bottom + 16

    def slider_value_from_mouse(self, key, mouse_x):
        for spec_key, _label, min_v, max_v, step in self._technical_sliders:
            if spec_key != key:
                continue
            rect = self.settings_slider_rows.get(key)
            if rect is None or rect.width <= 0:
                return None
            ratio = (mouse_x - rect.x) / rect.width
            ratio = max(0.0, min(1.0, ratio))
            raw = min_v + ratio * (max_v - min_v)
            stepped = round(raw / step) * step
            return int(max(min_v, min(max_v, stepped)))
        return None

    def _draw_buttons(self, screen, panel, mouse_pos):
        btn_w, btn_h = 130, 34
        gap = 12
        self.settings_save_btn_rect = pygame.Rect(
            panel.right - 12 - btn_w, panel.bottom - 12 - btn_h, btn_w, btn_h)
        self.settings_back_btn_rect = pygame.Rect(
            self.settings_save_btn_rect.x - gap - btn_w, panel.bottom - 12 - btn_h, btn_w, btn_h)

        save_color = BUTTON_HOVER if self.settings_save_btn_rect.collidepoint(mouse_pos) else BUTTON_COLOR
        pygame.draw.rect(screen, save_color, self.settings_save_btn_rect, border_radius=4)
        save_txt = self.font.render(INFO_BTN_SETTINGS_SAVE, True, TEXT_COLOR)
        screen.blit(save_txt, save_txt.get_rect(center=self.settings_save_btn_rect.center))

        back_color = CLOSE_BUTTON_HOVER if self.settings_back_btn_rect.collidepoint(mouse_pos) else CLOSE_BUTTON_COLOR
        pygame.draw.rect(screen, back_color, self.settings_back_btn_rect, border_radius=4)
        back_txt = self.font.render(INFO_BTN_BACK, True, TEXT_COLOR)
        screen.blit(back_txt, back_txt.get_rect(center=self.settings_back_btn_rect.center))

# =====================================================================
# Диалог "Сохранить игру?" при выходе (X окна / кнопка "Выйти")
# =====================================================================

class ExitConfirmPanel:

    WIDTH = 360
    HEIGHT = 160
    BTN_WIDTH = 100
    BTN_HEIGHT = 36
    BTN_GAP = 16

    def __init__(self, game, font):
        self.game = game
        self.font = font
        self.title_font = pygame.font.SysFont(FONT_NAME, FONT_SIZE_TITLE)
        self.exit_confirm_yes_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.exit_confirm_no_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.exit_confirm_back_btn_rect = pygame.Rect(0, 0, 0, 0)

    def draw(self, screen):
        window_w, window_h = screen.get_width(), screen.get_height()

        overlay = pygame.Surface((window_w, window_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, SETTINGS_OVERLAY_ALPHA))
        screen.blit(overlay, (0, 0))

        width = min(self.WIDTH, window_w - 40)
        height = min(self.HEIGHT, window_h - 40)
        rect = pygame.Rect((window_w - width) // 2, (window_h - height) // 2, width, height)

        pygame.draw.rect(screen, SETTINGS_PANEL_BG, rect)
        pygame.draw.rect(screen, SETTINGS_PANEL_BORDER, rect, 2)

        title_txt = self.title_font.render(INFO_EXIT_CONFIRM_TITLE, True, WORLD_SCREEN_TEXT)
        screen.blit(title_txt, title_txt.get_rect(centerx=rect.centerx, y=rect.y + 22))

        mouse_pos = pygame.mouse.get_pos()
        btn_y = rect.bottom - 20 - self.BTN_HEIGHT
        total_w = self.BTN_WIDTH * 3 + self.BTN_GAP * 2
        start_x = rect.centerx - total_w // 2

        self.exit_confirm_yes_btn_rect = pygame.Rect(start_x, btn_y, self.BTN_WIDTH, self.BTN_HEIGHT)
        self.exit_confirm_no_btn_rect = pygame.Rect(
            start_x + self.BTN_WIDTH + self.BTN_GAP, btn_y, self.BTN_WIDTH, self.BTN_HEIGHT)
        self.exit_confirm_back_btn_rect = pygame.Rect(
            start_x + 2 * (self.BTN_WIDTH + self.BTN_GAP), btn_y, self.BTN_WIDTH, self.BTN_HEIGHT)

        self._draw_button(screen, self.exit_confirm_yes_btn_rect, INFO_EXIT_CONFIRM_YES, mouse_pos)
        self._draw_button(screen, self.exit_confirm_no_btn_rect, INFO_EXIT_CONFIRM_NO, mouse_pos)
        self._draw_button(screen, self.exit_confirm_back_btn_rect, INFO_EXIT_CONFIRM_BACK, mouse_pos,
                          close_style=True)

    def _draw_button(self, screen, rect, label, mouse_pos, close_style=False):
        if close_style:
            color = CLOSE_BUTTON_HOVER if rect.collidepoint(mouse_pos) else CLOSE_BUTTON_COLOR
        else:
            color = BUTTON_HOVER if rect.collidepoint(mouse_pos) else BUTTON_COLOR
        pygame.draw.rect(screen, color, rect, border_radius=4)
        txt = self.font.render(label, True, TEXT_COLOR)
        screen.blit(txt, txt.get_rect(center=rect.center))

# =====================================================================
# Экран "Инструкция" — левая колонка категорий + правая прокручиваемая
# область. "Расы"/"Животные" рисуются списком сворачиваемых карточек.
# =====================================================================

class InstructionPanel:

    PANEL_WIDTH = 900
    PANEL_HEIGHT = 700
    SIDEBAR_RATIO = 0.20
    SCROLLBAR_RESERVE = 14
    TAB_GAP = 6
    ROW_ICON_SIZE = 24
    BULLET_ICON_SIZE = 20

    def __init__(self, game, font):
        self.game = game
        self.font = font
        self.title_font = pygame.font.SysFont(FONT_NAME, FONT_SIZE_TITLE)
        self.header_font = pygame.font.SysFont(FONT_NAME, FONT_SIZE_LABEL)

        self.panel_rect = pygame.Rect(0, 0, 0, 0)
        self.body_rect = pygame.Rect(0, 0, 0, 0)
        self.close_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.tab_rects = {}

        self._measure_cache = {}
        self._icon_cache = {}
        self._last_content_width = None

    def rebuild_layout(self, window_w, window_h):
        # ---------- Ширина правой колонки меняется вместе с окном -> перенос
        # текста другой -> все посчитанные высоты устарели ----------
        self._measure_cache = {}
        self._last_content_width = None

    # ---------- Иконки ----------

    def _resolve_icon(self, entry, icon_key, size):
        """Сначала core-иконки (у них фиксированный набор ключей и None для
        чужих), затем фабрика конкретной расы/животного."""
        if not icon_key:
            return None
        cache_key = (entry.key if entry is not None else "_core", icon_key, size)
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]

        surf = core_instruction_icon(icon_key, size)
        if surf is None and entry is not None and entry.icon_factory is not None:
            surf = entry.icon_factory(icon_key, size)

        self._icon_cache[cache_key] = surf
        return surf

    def _core_icon_provider(self, icon_key):
        return self._resolve_icon(None, icon_key, self.BULLET_ICON_SIZE)

    def _entry_icon_provider(self, entry):
        def provider(icon_key):
            return self._resolve_icon(entry, icon_key, self.BULLET_ICON_SIZE)
        return provider

    def _entry_row_icon(self, entry):
        return self._resolve_icon(entry, entry.preview_icon, self.ROW_ICON_SIZE)

    # ---------- Раскладка ----------

    def _layout_panel(self, screen):
        window_w, window_h = screen.get_width(), screen.get_height()
        width = min(self.PANEL_WIDTH, window_w - 40)
        height = min(self.PANEL_HEIGHT, window_h - 40)
        self.panel_rect = pygame.Rect((window_w - width) // 2, (window_h - height) // 2, width, height)

    def draw(self, screen, state):
        self._layout_panel(screen)
        mouse_pos = pygame.mouse.get_pos()

        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, SETTINGS_OVERLAY_ALPHA))
        screen.blit(overlay, (0, 0))

        panel = self.panel_rect
        pygame.draw.rect(screen, SETTINGS_PANEL_BG, panel)
        pygame.draw.rect(screen, SETTINGS_PANEL_BORDER, panel, 2)

        title_txt = self.title_font.render(INFO_INSTRUCTION_TITLE, True, WORLD_SCREEN_TEXT)
        screen.blit(title_txt, (panel.x + 16, panel.y + 14))

        content_top = panel.y + 14 + title_txt.get_height() + 14
        buttons_area_height = 56
        content_rect = pygame.Rect(
            panel.x + 12, content_top,
            panel.width - 24, panel.bottom - buttons_area_height - content_top - 10
        )

        sidebar_width = int(content_rect.width * self.SIDEBAR_RATIO)
        sidebar_rect = pygame.Rect(content_rect.x, content_rect.y, sidebar_width, content_rect.height)
        body_rect = pygame.Rect(
            sidebar_rect.right + 12, content_rect.y,
            content_rect.width - sidebar_width - 12, content_rect.height
        )

        pygame.draw.rect(screen, SETTINGS_SIDEBAR_BG, sidebar_rect)

        self._draw_tabs(screen, state, sidebar_rect, mouse_pos)
        self._draw_body(screen, state, body_rect)
        self._draw_close_button(screen, panel, mouse_pos)

    def _draw_tabs(self, screen, state, sidebar_rect, mouse_pos):
        self.tab_rects = {}
        y = sidebar_rect.y + 8
        for category in state.categories:
            rect = pygame.Rect(sidebar_rect.x + 6, y, sidebar_rect.width - 12, BUTTON_HEIGHT)
            self.tab_rects[category.key] = rect

            if state.active_key == category.key:
                color = SETTINGS_TAB_SELECTED
            elif rect.collidepoint(mouse_pos):
                color = SETTINGS_TAB_HOVER
            else:
                color = SETTINGS_TAB_COLOR
            pygame.draw.rect(screen, color, rect, border_radius=4)

            label_txt = self.font.render(category.label, True, TEXT_COLOR)
            screen.blit(label_txt, label_txt.get_rect(center=rect.center))
            y += BUTTON_HEIGHT + self.TAB_GAP

    def _measure_flat(self, category, width):
        key = (category.key, width)
        value = self._measure_cache.get(key)
        if value is None:
            value = measure_instruction_blocks(self.font, category.sections, width)
            self._measure_cache[key] = value
        return value

    def _draw_entry_content(self, screen, entry, x, y, width):
        draw_instruction_blocks(
            screen, self.font, entry.sections, x, y, width,
            icon_provider=self._entry_icon_provider(entry),
            header_font=self.header_font)

    def _draw_body(self, screen, state, body_rect):
        self.body_rect = body_rect
        category = state.active_category()
        scroll = state.active_scroll()
        if category is None or scroll is None:
            return

        text_width = max(40, body_rect.width - self.SCROLLBAR_RESERVE)

        if category.is_list:
            accordion = state.active_accordion()
            list_rect = pygame.Rect(body_rect.x, body_rect.y, text_width, body_rect.height)
            content_width = max(40, list_rect.width - AccordionList.CONTENT_INDENT * 2)

            # ---------- Высоты карточек кэшируются по ключу записи, без учёта
            # ширины - поэтому при её смене кэш сбрасываем вручную ----------
            if self._last_content_width != content_width:
                for acc in state.accordions.values():
                    acc.invalidate_content_heights()
                self._last_content_width = content_width

            accordion.ensure_content_heights(
                category.entries,
                lambda e: measure_instruction_blocks(self.font, e.sections, content_width))
            scroll.update_bounds(accordion.total_height(category.entries), list_rect.height)
            accordion.draw(screen, self.font, list_rect, scroll.offset, category.entries,
                           self._entry_row_icon, self._draw_entry_content)
        else:
            scroll.update_bounds(self._measure_flat(category, text_width), body_rect.height)
            clip_rect = pygame.Rect(body_rect.x, body_rect.y, text_width, body_rect.height)
            prev_clip = screen.get_clip()
            screen.set_clip(clip_rect)
            draw_instruction_blocks(
                screen, self.font, category.sections,
                body_rect.x, body_rect.y - scroll.offset, text_width,
                icon_provider=self._core_icon_provider,
                header_font=self.header_font)
            screen.set_clip(prev_clip)

        scroll.draw_scrollbar(screen, body_rect)

    def _draw_close_button(self, screen, panel, mouse_pos):
        btn_w, btn_h = 130, 34
        self.close_btn_rect = pygame.Rect(
            panel.right - 12 - btn_w, panel.bottom - 12 - btn_h, btn_w, btn_h)
        color = CLOSE_BUTTON_HOVER if self.close_btn_rect.collidepoint(mouse_pos) else CLOSE_BUTTON_COLOR
        pygame.draw.rect(screen, color, self.close_btn_rect, border_radius=4)
        txt = self.font.render(INFO_INSTRUCTION_CLOSE, True, TEXT_COLOR)
        screen.blit(txt, txt.get_rect(center=self.close_btn_rect.center))

# =====================================================================
# Фасад: то, что реально импортирует game.py и дёргает input_handler.py
# =====================================================================

class UIManager:

    def __init__(self, game):
        self.game = game
        self.font = pygame.font.SysFont(FONT_NAME, FONT_SIZE_PANEL)

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

        self.exit_placement_btn = pygame.Rect(10, UI_HEIGHT + 10, 30, 30)
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
        return pygame.Rect(0, UI_HEIGHT, screen.get_width(), screen.get_height() - UI_HEIGHT)

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
        handle_y = panel_rect.y + (panel_rect.height - COLLAPSE_HANDLE_HEIGHT) // 2

        if self.game.right_panel_collapsed:
            handle_x = screen_width - COLLAPSE_HANDLE_WIDTH
        else:
            handle_x = panel_rect.x - COLLAPSE_HANDLE_WIDTH

        return pygame.Rect(handle_x, handle_y, COLLAPSE_HANDLE_WIDTH, COLLAPSE_HANDLE_HEIGHT)

    def _draw_collapse_handle(self, screen):
        game = self.game
        handle_rect = self._compute_collapse_handle_rect(screen.get_width())
        self.collapse_handle_rect = handle_rect

        mouse_pos = pygame.mouse.get_pos()
        hovered = handle_rect.collidepoint(mouse_pos)

        pygame.draw.rect(screen, COLLAPSE_HANDLE_COLOR, handle_rect, border_radius=3)
        pygame.draw.rect(screen, COLLAPSE_HANDLE_BORDER, handle_rect, 1, border_radius=3)

        arrow_color = COLLAPSE_HANDLE_ARROW_HOVER_COLOR if hovered else COLLAPSE_HANDLE_ARROW_COLOR
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
        cross_color = CLOSE_BUTTON_HOVER if self.exit_placement_btn.collidepoint(mouse_pos) else CLOSE_BUTTON_COLOR
        pygame.draw.rect(screen, cross_color, self.exit_placement_btn)
        cx, cy = self.exit_placement_btn.center
        pygame.draw.line(screen, TEXT_COLOR, (cx - 6, cy - 6), (cx + 6, cy + 6), 2)
        pygame.draw.line(screen, TEXT_COLOR, (cx + 6, cy - 6), (cx - 6, cy + 6), 2)

        if game.placement_pos:
            screen_pos = game.camera.apply_pos(game.placement_pos)
            color = (0, 255, 0) if game.placement_valid else (255, 0, 0)
            pygame.draw.circle(screen, color, (int(screen_pos[0]), int(screen_pos[1])), 12, 2)
            screen.blit(self.font.render(INFO_PLACEMENT_HINT, True, TEXT_COLOR), (10, UI_HEIGHT + 50))

    def draw_player_tool_overlay(self, screen):
        game = self.game
        mouse_pos = pygame.mouse.get_pos()
        cross_color = CLOSE_BUTTON_HOVER if self.exit_placement_btn.collidepoint(mouse_pos) else CLOSE_BUTTON_COLOR
        pygame.draw.rect(screen, cross_color, self.exit_placement_btn)
        cx, cy = self.exit_placement_btn.center
        pygame.draw.line(screen, TEXT_COLOR, (cx - 6, cy - 6), (cx + 6, cy + 6), 2)
        pygame.draw.line(screen, TEXT_COLOR, (cx + 6, cy - 6), (cx - 6, cy + 6), 2)

        hint_map = dict(_CORE_TOOL_HINTS)
        for spec in _CORE_PLAYER_TOOLS + all_player_tools():
            hint_map[spec.tool_value] = spec.hint
        for spec in all_road_networks():
            if spec.menu_hint:
                hint_map[spec.obj_type] = spec.menu_hint

        if game.player.grabbed_creature is not None:
            hint = INFO_TOOL_GRAB_RELEASE_HINT
        elif game.player.grabbed_object is not None:
            hint = INFO_TOOL_GRAB_OBJECT_HINT
        else:
            hint = hint_map.get(game.player.tool, "")
        if hint:
            screen.blit(self.font.render(hint, True, TEXT_COLOR), (10, UI_HEIGHT + 50))

        # ---------- Предпросмотр рисуемой дороги (любого зарегистрированного типа) ----------
        for spec in all_road_networks():
            drawing_road = getattr(game.player, f"drawing_{spec.obj_type}", None)
            if drawing_road is not None and drawing_road.points:
                last_x, last_y = drawing_road.points[-1]
                last_screen = game.camera.apply_pos((last_x, last_y))
                pygame.draw.line(screen, spec.preview_color, last_screen, mouse_pos, 2)

        if game.player.tool in ("biome_plains", "biome_desert", "biome_river", "biome_sea"):
            grid = game.biome_manager.grid
            if (mouse_pos[1] > UI_HEIGHT and not self.exit_placement_btn.collidepoint(mouse_pos)
                    and grid is not None):
                wx, wy = game.camera.world_from_screen(*mouse_pos)
                color = BIOME_PREVIEW_COLOR.get(game.player.tool, (255, 255, 255))
                preview_surf = self._get_biome_preview_surface(color, grid.cell_size)
                for cx, cy in grid.cells_in_radius(wx, wy, game.player.brush_radius):
                    screen_pos = game.camera.apply_pos((cx * grid.cell_size, cy * grid.cell_size))
                    screen.blit(preview_surf, screen_pos)
                pygame.draw.circle(screen, (255, 255, 255), mouse_pos, int(game.player.brush_radius), 1)
            radius_txt = self.font.render(
                INFO_BRUSH_RADIUS.format(radius=int(game.player.brush_radius)), True, TEXT_COLOR)
            screen.blit(radius_txt, (10, UI_HEIGHT + 70))

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