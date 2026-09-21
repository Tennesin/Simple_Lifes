"""Экран "Инструкция" — левая колонка категорий + правая прокручиваемая
область. "Расы"/"Животные" рисуются списком сворачиваемых карточек."""

import pygame

import info
import settings
from game.instruction_content import core_instruction_icon
from game.widgets import (
    AccordionList,
    draw_instruction_blocks,
    measure_instruction_blocks,
)


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
        self.title_font = pygame.font.SysFont(settings.FONT_NAME, settings.FONT_SIZE_TITLE)
        self.header_font = pygame.font.SysFont(settings.FONT_NAME, settings.FONT_SIZE_LABEL)

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
        overlay.fill((0, 0, 0, settings.SETTINGS_OVERLAY_ALPHA))
        screen.blit(overlay, (0, 0))

        panel = self.panel_rect
        pygame.draw.rect(screen, settings.SETTINGS_PANEL_BG, panel)
        pygame.draw.rect(screen, settings.SETTINGS_PANEL_BORDER, panel, 2)

        title_txt = self.title_font.render(info.INFO_INSTRUCTION_TITLE, True, settings.WORLD_SCREEN_TEXT)
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

        pygame.draw.rect(screen, settings.SETTINGS_SIDEBAR_BG, sidebar_rect)

        self._draw_tabs(screen, state, sidebar_rect, mouse_pos)
        self._draw_body(screen, state, body_rect)
        self._draw_close_button(screen, panel, mouse_pos)

    def _draw_tabs(self, screen, state, sidebar_rect, mouse_pos):
        self.tab_rects = {}
        y = sidebar_rect.y + 8
        for category in state.categories:
            rect = pygame.Rect(sidebar_rect.x + 6, y, sidebar_rect.width - 12, settings.BUTTON_HEIGHT)
            self.tab_rects[category.key] = rect

            if state.active_key == category.key:
                color = settings.SETTINGS_TAB_SELECTED
            elif rect.collidepoint(mouse_pos):
                color = settings.SETTINGS_TAB_HOVER
            else:
                color = settings.SETTINGS_TAB_COLOR
            pygame.draw.rect(screen, color, rect, border_radius=4)

            label_txt = self.font.render(category.label, True, settings.TEXT_COLOR)
            screen.blit(label_txt, label_txt.get_rect(center=rect.center))
            y += settings.BUTTON_HEIGHT + self.TAB_GAP

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
            accordion.draw(screen, self.font, list_rect, int(scroll.offset), category.entries,
                           self._entry_row_icon, self._draw_entry_content)
        else:
            scroll.update_bounds(self._measure_flat(category, text_width), body_rect.height)
            clip_rect = pygame.Rect(body_rect.x, body_rect.y, text_width, body_rect.height)
            prev_clip = screen.get_clip()
            screen.set_clip(clip_rect)
            draw_instruction_blocks(
                screen, self.font, category.sections,
                body_rect.x, body_rect.y - int(scroll.offset), text_width,
                icon_provider=self._core_icon_provider,
                header_font=self.header_font)
            screen.set_clip(prev_clip)

        scroll.draw_scrollbar(screen, body_rect)

    def _draw_close_button(self, screen, panel, mouse_pos):
        btn_w, btn_h = 130, 34
        self.close_btn_rect = pygame.Rect(
            panel.right - 12 - btn_w, panel.bottom - 12 - btn_h, btn_w, btn_h)
        color = settings.CLOSE_BUTTON_HOVER if self.close_btn_rect.collidepoint(mouse_pos) else settings.CLOSE_BUTTON_COLOR
        pygame.draw.rect(screen, color, self.close_btn_rect, border_radius=4)
        txt = self.font.render(info.INFO_INSTRUCTION_CLOSE, True, settings.TEXT_COLOR)
        screen.blit(txt, txt.get_rect(center=self.close_btn_rect.center))