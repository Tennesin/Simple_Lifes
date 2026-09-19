"""Экраны "Создание мира" / "Загрузка мира" — без изменений (core)."""

import time
import pygame

import settings
import info
from game.animal_registry import all_animals

from .constants import BIOME_LABELS

class WorldScreensPanel:

    def __init__(self, game):
        self.game = game
        self.title_font = pygame.font.SysFont(settings.FONT_NAME, settings.FONT_SIZE_TITLE)
        self.label_font = pygame.font.SysFont(settings.FONT_NAME, settings.FONT_SIZE_LABEL)
        self.small_font = pygame.font.SysFont(settings.FONT_NAME, settings.FONT_SIZE_SMALL)
        self.lw_title_font = pygame.font.SysFont(settings.FONT_NAME, 26)
        self.lw_label_font = pygame.font.SysFont(settings.FONT_NAME, 18)
        self.lw_small_font = pygame.font.SysFont(settings.FONT_NAME, 16)

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
        pygame.draw.rect(screen, settings.WORLD_SCREEN_BG, content_rect)
        margin = settings.WORLD_SCREEN_MARGIN
        base_x = content_rect.x + margin
        base_y = content_rect.y + margin

        title_txt = self.title_font.render(info.INFO_WS_SCREEN_TITLE, True, settings.WORLD_SCREEN_TEXT)
        screen.blit(title_txt, (base_x, base_y))

        # ---------- Строка 1: название мира + сид (в одной строке) ----------
        row1_y = base_y + 60
        name_label = self.label_font.render(info.INFO_WS_TITLE_NAME, True, settings.WORLD_SCREEN_TEXT)
        screen.blit(name_label, (base_x, row1_y + 6))
        state.name_input.rect = pygame.Rect(base_x + 150, row1_y, 230, 34)
        state.name_input.draw(screen, self.label_font)

        seed_x = base_x + 150 + 230 + 30
        seed_label = self.label_font.render(info.INFO_WS_TITLE_SEED, True, settings.WORLD_SCREEN_TEXT)
        screen.blit(seed_label, (seed_x, row1_y + 6))
        state.seed_input.rect = pygame.Rect(seed_x + 110, row1_y, 160, 34)
        state.seed_input.draw(screen, self.label_font)

        # ---------- Строка 2: размер мира ----------
        row2_y = row1_y + 60
        size_label = self.label_font.render(info.INFO_WS_TITLE_SIZE, True, settings.WORLD_SCREEN_TEXT)
        screen.blit(size_label, (base_x, row2_y + 6))

        length_label = self.label_font.render(info.INFO_WS_LENGTH, True, settings.WORLD_SCREEN_TEXT)
        screen.blit(length_label, (base_x + 150, row2_y + 6))
        state.width_input.rect = pygame.Rect(base_x + 230, row2_y, 100, 34)
        state.width_input.draw(screen, self.label_font)

        width_label = self.label_font.render(info.INFO_WS_WIDTH, True, settings.WORLD_SCREEN_TEXT)
        screen.blit(width_label, (base_x + 360, row2_y + 6))
        state.height_input.rect = pygame.Rect(base_x + 430, row2_y, 100, 34)
        state.height_input.draw(screen, self.label_font)

        # ---------- Строка 3: автогенерация животных ----------
        row3_y = row2_y + 60
        self.ws_animals_checkbox_rect = pygame.Rect(base_x, row3_y, 20, 20)
        self._draw_checkbox(screen, self.ws_animals_checkbox_rect, state.generate_animals)
        animals_label = self.label_font.render(info.INFO_WS_GENERATE_ANIMALS, True, settings.WORLD_SCREEN_TEXT)
        screen.blit(animals_label, (self.ws_animals_checkbox_rect.right + 10, row3_y - 1))

        # ---------- Строка 4+: соотношение биомов ----------
        row4_y = row3_y + 40
        biome_title = self.label_font.render(info.INFO_WS_TITLE_BIOME_RATIOS, True, settings.WORLD_SCREEN_TEXT)
        screen.blit(biome_title, (base_x, row4_y))

        self.ws_biome_slider_rects = {}
        slider_y = row4_y + 34
        name_col_w = 130
        percent_col_w = 55
        available_width = content_rect.right - margin - (base_x + name_col_w + percent_col_w)
        slider_w = max(120, min(360, available_width))

        for biome, slider in state.biome_sliders.items():
            biome_label = self.small_font.render(BIOME_LABELS.get(biome, biome), True, settings.WORLD_SCREEN_TEXT)
            screen.blit(biome_label, (base_x, slider_y + 6))

            percent_txt = self.small_font.render(f"{int(round(slider.value * 100))}%", True, settings.WORLD_SCREEN_TEXT)
            screen.blit(percent_txt, (base_x + name_col_w, slider_y + 6))

            slider.rect = pygame.Rect(base_x + name_col_w + percent_col_w, slider_y, slider_w, 18)
            slider.draw(screen, settings.MINIMAP_BIOME_COLOR.get(biome, (150, 150, 150)))
            self.ws_biome_slider_rects[biome] = slider.rect

            slider_y += 30

        total_ratio = sum(s.value for s in state.biome_sliders.values())
        total_color = settings.WORLD_SCREEN_ERROR_COLOR if total_ratio > 1.001 else settings.WORLD_SCREEN_HINT_COLOR
        total_txt = self.small_font.render(f"Сумма: {int(round(total_ratio * 100))}%", True, total_color)
        screen.blit(total_txt, (base_x, slider_y + 4))

        if state.error_text:
            err_txt = self.small_font.render(state.error_text, True, settings.WORLD_SCREEN_ERROR_COLOR)
            screen.blit(err_txt, (base_x, content_rect.bottom - margin - 36 - 26))

        self.ws_create_btn_rect = pygame.Rect(base_x, content_rect.bottom - margin - 36, 150, 36)
        mouse_pos = pygame.mouse.get_pos()
        btn_color = settings.BUTTON_HOVER if self.ws_create_btn_rect.collidepoint(mouse_pos) else settings.BUTTON_COLOR
        pygame.draw.rect(screen, btn_color, self.ws_create_btn_rect, border_radius=4)
        btn_txt = self.label_font.render(info.INFO_BTN_WS_CREATE, True, settings.TEXT_COLOR)
        screen.blit(btn_txt, btn_txt.get_rect(center=self.ws_create_btn_rect.center))
        self._draw_back_button(screen, self.label_font, content_rect)

    def _draw_checkbox(self, screen, rect, checked):
        mouse_pos = pygame.mouse.get_pos()
        bg = (55, 55, 55) if rect.collidepoint(mouse_pos) else (40, 40, 40)
        pygame.draw.rect(screen, bg, rect)
        pygame.draw.rect(screen, settings.WORLD_SCREEN_TEXT, rect, 1)
        if checked:
            pygame.draw.line(screen, (120, 230, 120), (rect.x + 3, rect.y + 10), (rect.x + 8, rect.y + 15), 2)
            pygame.draw.line(screen, (120, 230, 120), (rect.x + 8, rect.y + 15), (rect.x + 17, rect.y + 3), 2)

    def draw_load_world_screen(self, screen, state, content_rect):
        pygame.draw.rect(screen, settings.WORLD_SCREEN_BG, content_rect)
        margin = settings.WORLD_SCREEN_MARGIN

        title_txt = self.lw_title_font.render(info.INFO_LW_SCREEN_TITLE, True, settings.WORLD_SCREEN_TEXT)
        screen.blit(title_txt, (content_rect.x + margin, content_rect.y + margin))
        if state.error_text:
            err_txt = self.lw_small_font.render(state.error_text, True, settings.WORLD_SCREEN_ERROR_COLOR)
            screen.blit(err_txt, (content_rect.x + margin, content_rect.y + margin + 36))

        list_top = content_rect.y + margin + 60
        list_width = content_rect.width // 2 - margin - 15
        list_height = content_rect.bottom - list_top - margin
        self.lw_list_rect = pygame.Rect(content_rect.x + margin, list_top, list_width, list_height)
        pygame.draw.rect(screen, settings.WORLD_SCREEN_PANEL_BG, self.lw_list_rect)
        pygame.draw.rect(screen, settings.WORLD_SCREEN_PANEL_BORDER, self.lw_list_rect, 2)

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
            hint_txt = self.lw_label_font.render(info.INFO_LW_SELECT_HINT, True, settings.WORLD_SCREEN_HINT_COLOR)
            screen.blit(hint_txt, (info_x + 10, list_top + 10))

        self._draw_back_button(screen, self.lw_label_font, content_rect)

    def _draw_world_list(self, screen, state, font):
        rect = self.lw_list_rect

        if not state.entries:
            empty_txt = font.render(info.INFO_LW_EMPTY_LIST, True, settings.WORLD_SCREEN_HINT_COLOR)
            screen.blit(empty_txt, (rect.x + 10, rect.y + 10))
            return

        prev_clip = screen.get_clip()
        screen.set_clip(rect)

        content_height = len(state.entries) * settings.WORLD_LIST_ITEM_HEIGHT
        state.list_scroll.update_bounds(content_height, rect.height)
        scroll = state.list_scroll.offset
        mouse_pos = pygame.mouse.get_pos()

        for index, entry in enumerate(state.entries):
            item_y = rect.y + index * settings.WORLD_LIST_ITEM_HEIGHT - scroll
            if item_y + settings.WORLD_LIST_ITEM_HEIGHT < rect.y or item_y > rect.bottom:
                continue
            item_rect = pygame.Rect(rect.x, item_y, rect.width, settings.WORLD_LIST_ITEM_HEIGHT)
            if index == state.selected_index:
                color = settings.WORLD_LIST_ITEM_SELECTED_COLOR
            elif item_rect.collidepoint(mouse_pos):
                color = settings.WORLD_LIST_ITEM_HOVER_COLOR
            else:
                color = settings.WORLD_LIST_ITEM_COLOR
            pygame.draw.rect(screen, color, item_rect)
            pygame.draw.rect(screen, settings.WORLD_SCREEN_PANEL_BORDER, item_rect, 1)
            name_txt = font.render(entry.display_name, True, settings.WORLD_SCREEN_TEXT)
            screen.blit(name_txt, (item_rect.x + 10,
                                   item_rect.y + (settings.WORLD_LIST_ITEM_HEIGHT - name_txt.get_height()) // 2))

        screen.set_clip(prev_clip)
        state.list_scroll.draw_scrollbar(screen, rect)

    def _draw_back_button(self, screen, font, content_rect):
        margin = settings.WORLD_SCREEN_MARGIN
        width, height = 110, 34
        rect = pygame.Rect(content_rect.right - margin - width, content_rect.y + margin, width, height)
        self.world_screen_back_btn_rect = rect

        mouse_pos = pygame.mouse.get_pos()
        color = settings.CLOSE_BUTTON_HOVER if rect.collidepoint(mouse_pos) else settings.CLOSE_BUTTON_COLOR
        pygame.draw.rect(screen, color, rect, border_radius=4)
        txt = font.render(info.INFO_BTN_BACK, True, settings.TEXT_COLOR)
        screen.blit(txt, txt.get_rect(center=rect.center))

    def _build_world_info_lines(self, entry):
        meta = entry.meta
        lines = [info.INFO_LW_INFO_NAME.format(name=entry.display_name)]

        created_ts = meta.get("created")
        if created_ts:
            created_str = time.strftime("%H:%M:%S %d.%m.%Y", time.localtime(created_ts))
            lines.append(info.INFO_LW_INFO_CREATED.format(created=created_str))

        version = meta.get("game_version")
        if version is not None:
            lines.append(info.INFO_LW_INFO_VERSION.format(version=version))

        width = meta.get("world_width", settings.WORLD_DEFAULT_SIZE[0])
        height = meta.get("world_height", settings.WORLD_DEFAULT_SIZE[1])
        lines.append(info.INFO_LW_INFO_SIZE.format(w=width, h=height))

        seed = meta.get("seed")
        if seed is not None:
            lines.append(info.INFO_LW_INFO_SEED.format(seed=seed))

        counts = entry.counts or {}
        lines.append(info.INFO_LW_INFO_CREATURES.format(count=counts.get("creatures", 0)))
        lines.append(info.INFO_LW_INFO_FRUITS.format(count=counts.get("fruits", 0)))
        lines.append(info.INFO_LW_INFO_SPIKES.format(count=counts.get("spikes", 0)))
        lines.append(info.INFO_LW_INFO_WATER.format(count=counts.get("water", 0)))
        lines.append(info.INFO_LW_INFO_BUSHES.format(count=counts.get("bushes", 0)))
        lines.append(info.INFO_LW_INFO_CAMPFIRES.format(count=counts.get("campfires", 0)))
        lines.append(info.INFO_LW_INFO_ROADS.format(count=counts.get("roads", 0)))

        lines.append(info.INFO_LW_INFO_ANIMALS_TOTAL.format(count=counts.get("animals_total", 0)))
        animals_by_type = counts.get("animals_by_type", {})
        for descriptor in all_animals():
            lines.append(info.INFO_LW_INFO_ANIMAL_TYPE.format(
                label=descriptor.placement_label,
                count=animals_by_type.get(descriptor.animal_name, 0)))

        return lines

    def _draw_world_info_panel(self, screen, state, entry, label_font, small_font, content_rect):
        margin = settings.WORLD_SCREEN_MARGIN
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
        pygame.draw.rect(screen, settings.WORLD_SCREEN_PANEL_BG, info_rect)
        pygame.draw.rect(screen, settings.WORLD_SCREEN_PANEL_BORDER, info_rect, 2)

        text_area_height = max(0, info_height - buttons_area_height)
        text_rect = pygame.Rect(info_rect.x, info_rect.y, info_rect.width, text_area_height)
        prev_clip = screen.get_clip()
        screen.set_clip(text_rect)

        state.info_scroll.update_bounds(content_height, text_area_height)
        scroll = state.info_scroll.offset

        y = info_rect.y + 12 - scroll
        for line in lines:
            line_txt = small_font.render(line, True, settings.WORLD_SCREEN_TEXT)
            screen.blit(line_txt, (info_rect.x + 12, y))
            y += line_height

        screen.set_clip(prev_clip)
        if content_height > text_area_height:
            state.info_scroll.draw_scrollbar(screen, text_rect)

        btn_area_top = info_rect.bottom - buttons_area_height + 8
        btn_y = btn_area_top

        if state.confirm_delete:
            warn_txt = small_font.render(info.INFO_LW_CONFIRM_DELETE, True, settings.WORLD_SCREEN_ERROR_COLOR)
            screen.blit(warn_txt, (info_rect.x + 12, btn_area_top))
            btn_y = btn_area_top + warn_txt.get_height() + 8

        self.lw_load_btn_rect = pygame.Rect(info_rect.x + 12, btn_y, 130, 32)
        self.lw_delete_btn_rect = pygame.Rect(info_rect.x + 152, btn_y, 130, 32)

        mouse_pos = pygame.mouse.get_pos()
        load_color = settings.BUTTON_HOVER if self.lw_load_btn_rect.collidepoint(mouse_pos) else settings.BUTTON_COLOR
        pygame.draw.rect(screen, load_color, self.lw_load_btn_rect, border_radius=4)
        load_txt = label_font.render(info.INFO_BTN_LW_LOAD, True, settings.TEXT_COLOR)
        screen.blit(load_txt, load_txt.get_rect(center=self.lw_load_btn_rect.center))

        delete_color = settings.CLOSE_BUTTON_HOVER if self.lw_delete_btn_rect.collidepoint(mouse_pos) else settings.CLOSE_BUTTON_COLOR
        pygame.draw.rect(screen, delete_color, self.lw_delete_btn_rect, border_radius=4)
        delete_txt = label_font.render(info.INFO_BTN_LW_DELETE, True, settings.TEXT_COLOR)
        screen.blit(delete_txt, delete_txt.get_rect(center=self.lw_delete_btn_rect.center))