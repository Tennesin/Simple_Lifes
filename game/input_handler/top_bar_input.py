"""Клики по верхней панели и её выпадающим меню - пара к ui/top_bar.py."""

from functools import partial

from player import Player

_MENU_BUTTONS = (
    ("btn_landscape", "show_landscape_menu"),
    ("btn_lifes", "show_lifes_menu"),
    ("btn_animals", "show_animals_menu"),
    ("btn_objects", "show_objects_menu"),
    ("btn_nature", "show_nature_menu"),
    ("btn_player", "show_player_menu"),
)
_LANDSCAPE_TOOLS = (
    ("btn_wall", Player.TOOL_WALL),
    ("btn_fence", Player.TOOL_FENCE),
    ("btn_biome_plains", Player.TOOL_BIOME_PLAINS),
    ("btn_biome_desert", Player.TOOL_BIOME_DESERT),
    ("btn_biome_river", Player.TOOL_BIOME_RIVER),
    ("btn_biome_sea", Player.TOOL_BIOME_SEA),
)
_NATURE_PLACEMENTS = (
    ("btn_fruit", "fruit"), ("btn_bush", "bush"), ("btn_water", "water"), ("btn_tree", "tree"),
    ("btn_stone", "stone"), ("btn_grass", "grass"), ("btn_meat", "meat"),
)

class TopBarController:

    def __init__(self, game):
        self.game = game
        # (флаг меню, источник пар "кнопка -> действие", съедать ли клик мимо кнопок)
        self._dropdowns = (
            ("show_landscape_menu", self._landscape_actions, True),
            ("show_lifes_menu", self._lifes_actions, False),
            ("show_animals_menu", self._animals_actions, False),
            ("show_objects_menu", self._objects_actions, True),
            ("show_nature_menu", self._nature_actions, True),
            ("show_player_menu", self._player_actions, True),
        )
        self._game_menu_items = (
            ("btn_create_world", False, lambda: self.game.world_manager.open_create_screen()),
            ("btn_load_world", False, lambda: self.game.world_manager.open_load_screen()),
            ("btn_pause", True, self._pause),
            ("btn_save_world", True, lambda: self.game.world_manager.save_world_manual()),
            ("btn_instruction", False, lambda: self.game.open_instruction_screen()),
            ("btn_exit", False, self._exit),
        )

    def on_left_click(self, x, y):
        return (self._click_main_bar(x, y)
                or self._click_game_menu(x, y)
                or self._click_open_dropdown(x, y))

    def _click_main_bar(self, x, y):
        game = self.game
        top_bar = game.ui.top_bar
        if top_bar.btn_game.collidepoint(x, y):
            self._toggle_menu("show_game_menu")
            return True
        if top_bar.btn_settings.collidepoint(x, y):
            game.close_all_menus()
            game.open_settings_screen()
            return True
        if not game.world_loaded:
            return False
        for attr, flag in _MENU_BUTTONS:
            if getattr(top_bar, attr).collidepoint(x, y):
                self._toggle_menu(flag)
                return True
        return False

    def _toggle_menu(self, flag):
        game = self.game
        was_open = getattr(game, flag)
        game.close_all_menus()
        setattr(game, flag, not was_open)

    def _click_game_menu(self, x, y):
        game = self.game
        if not game.show_game_menu:
            return False
        top_bar = game.ui.top_bar
        for attr, needs_world, action in self._game_menu_items:
            if needs_world and not game.world_loaded:
                continue
            if getattr(top_bar, attr).collidepoint(x, y):
                action()
                return True
        return False

    def _pause(self):
        self.game.toggle_pause()
        self.game.show_game_menu = False

    def _exit(self):
        self.game.request_exit()
        self.game.show_game_menu = False

    def _click_open_dropdown(self, x, y):
        game = self.game
        if not game.world_loaded:
            return False
        for flag, actions_fn, swallow_miss in self._dropdowns:
            if not getattr(game, flag):
                continue
            for button, action in actions_fn():
                if button.collidepoint(x, y):
                    action()
                    game.close_all_menus()
                    return True
            if swallow_miss:
                game.close_all_menus()
                return True
            return False
        return False

    def _landscape_actions(self):
        top_bar = self.game.ui.top_bar
        return [(getattr(top_bar, attr), partial(self.game.activate_player_tool, tool))
                for attr, tool in _LANDSCAPE_TOOLS]

    def _lifes_actions(self):
        game = self.game
        return [(btn, partial(game.object_manager.start_placement, mode))
                for mode, btn in game.ui.top_bar.creature_placement_buttons.items()]

    def _animals_actions(self):
        game = self.game
        return [(btn, partial(game.object_manager.start_placement, mode))
                for mode, btn in game.ui.top_bar.animal_placement_buttons.items()]

    def _objects_actions(self):
        game = self.game
        top_bar = game.ui.top_bar
        actions = [(btn, partial(game.object_manager.start_placement, obj_type))
                   for obj_type, btn in top_bar.object_placement_buttons.items()]
        actions += [(btn, partial(game.activate_player_tool, obj_type))
                    for obj_type, btn in top_bar.road_tool_buttons.items()]
        return actions

    def _nature_actions(self):
        game = self.game
        top_bar = game.ui.top_bar
        return [(getattr(top_bar, attr), partial(game.object_manager.start_placement, obj_type))
                for attr, obj_type in _NATURE_PLACEMENTS]

    def _player_actions(self):
        game = self.game
        return [(btn, partial(game.activate_player_tool, tool))
                for tool, btn in game.ui.top_bar.player_tool_buttons.items()]

    def close_menus_on_escape(self):
        self.game.close_all_menus()
        return True