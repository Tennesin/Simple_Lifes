"""Панель кладбища конкретно для расы 'Круг'."""

import time
import pygame

import settings
import info
from game.widgets import ScrollArea, edit_text_buffer, TEXT_EDIT_COMMIT, TEXT_EDIT_CANCEL
from ... import ci_settings, ci_info
from .....all_needed.instruction import truncate_text

class GraveyardPanel:

    ROW_HEIGHT = 30

    def __init__(self, game, font):
        self.game = game
        self.font = font
        self.archive_scroll = ScrollArea()
        self._last_graveyard_id = None
        self.list_rect = None
        self.details_buttons = {}
        self.details_close_rect = None
        self.genealogy_buttons = {}

        # ---------- Состояние выбора, раньше жившее в Game ----------
        self.selected = None
        self.editing_name = False
        self.name_edit_buffer = ""
        self.details_record = None

        self.rebuild_layout(settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT)

    def rebuild_layout(self, window_w, window_h):
        self.panel_rect = pygame.Rect(
            window_w - settings.INFO_PANEL_WIDTH, settings.UI_HEIGHT,
            settings.INFO_PANEL_WIDTH, window_h - settings.UI_HEIGHT
        )
        self.name_field_rect = pygame.Rect(
            self.panel_rect.x + 10, self.panel_rect.y + 40,
            settings.INFO_PANEL_WIDTH - 20, 26
        )

    # =====================================================================
    # Протокол SecondaryPanelSpec
    # =====================================================================

    @property
    def popup_active(self):
        return self.details_record is not None

    @property
    def text_editing(self):
        return self.editing_name

    def clear(self, game):
        self.selected = None
        self.editing_name = False
        self.name_edit_buffer = ""
        self.details_record = None

    def start_name_editing(self):
        if not self.selected:
            return
        self.editing_name = True
        self.name_edit_buffer = self.selected.name if self.selected.name else ""

    def finish_name_editing(self):
        if self.editing_name and self.selected:
            new_name = self.name_edit_buffer.strip()
            if new_name:
                self.selected.name = new_name
        self.editing_name = False
        self.name_edit_buffer = ""

    def handle_click(self, game, mouse_x, mouse_y):
        if self.selected is None:
            return
        if self.name_field_rect.collidepoint(mouse_x, mouse_y):
            self.start_name_editing()
            return
        self.finish_name_editing()
        for record_id, btn_rect in self.details_buttons.items():
            if btn_rect.collidepoint(mouse_x, mouse_y):
                record = self.selected.get_fresh_record(record_id)
                if record is not None:
                    self.details_record = record
                return
        for record_id, btn_rect in self.genealogy_buttons.items():
            if btn_rect.collidepoint(mouse_x, mouse_y):
                game.ui.genealogy_overlay.open(record_id)
                return

    def handle_popup_click(self, game, mouse_x, mouse_y):
        if self.details_close_rect and self.details_close_rect.collidepoint(mouse_x, mouse_y):
            self.details_record = None

    def handle_wheel(self, game, mouse_x, mouse_y, wheel_y):
        if self.list_rect is None or not self.list_rect.collidepoint(mouse_x, mouse_y):
            return False
        if self.selected is None:
            return False
        content_height = len(self.selected.archive) * self.ROW_HEIGHT
        self.archive_scroll.update_bounds(content_height, self.list_rect.height)
        self.archive_scroll.scroll_by_wheel(wheel_y, speed=settings.DEFAULT_SCROLL_SPEED)
        return True

    def handle_keydown(self, event):
        self.name_edit_buffer, action = edit_text_buffer(self.name_edit_buffer, event)
        if action == TEXT_EDIT_COMMIT:
            self.finish_name_editing()
        elif action == TEXT_EDIT_CANCEL:
            self.editing_name = False
            self.name_edit_buffer = ""
        elif event.key == pygame.K_BACKSPACE:
            self.name_edit_buffer = self.name_edit_buffer[:-1]
        else:
            if event.unicode and event.unicode.isprintable() and len(self.name_edit_buffer) < 24:
                self.name_edit_buffer += event.unicode

    def close_popup_or_deselect(self, game):
        if self.details_record is not None:
            self.details_record = None
            return True
        if self.selected is not None:
            self.selected = None
            return True
        return False

    def draw(self, screen):
        game = self.game
        gy = self.selected
        if gy is None:
            return

        if gy.id != self._last_graveyard_id:
            self._last_graveyard_id = gy.id
            self.archive_scroll.offset = 0

        gy.prune_expired_records()

        panel = self.panel_rect
        pygame.draw.rect(screen, settings.INFO_PANEL_COLOR, panel)

        id_txt = self.font.render(
            ci_info.INFO_GRAVEYARD_ID.format(graveyard_id=gy.id), True, settings.TEXT_COLOR)
        screen.blit(id_txt, (panel.x + 10, panel.y + 12))

        field = self.name_field_rect
        field_color = settings.NAME_FIELD_EDIT_COLOR if self.editing_name else settings.NAME_FIELD_COLOR
        pygame.draw.rect(screen, field_color, field)
        pygame.draw.rect(screen, settings.INFO_PANEL_BORDER, field, 1)

        if self.editing_name:
            display_name = self.name_edit_buffer
            if int(time.time() * 2) % 2 == 0:
                display_name += "|"
            text_color = (0, 0, 0)
        else:
            display_name = gy.name if gy.name else ci_info.INFO_GRAVEYARD_DEFAULT_NAME
            text_color = settings.TEXT_COLOR

        name_txt = self.font.render(display_name, True, text_color)
        screen.blit(name_txt, (field.x + 5, field.y + 4))

        list_top = field.bottom + 16
        list_rect = pygame.Rect(panel.x + 10, list_top, panel.width - 20, panel.bottom - list_top - 10)
        self.list_rect = list_rect

        if not gy.archive:
            empty_txt = self.font.render(ci_info.INFO_GRAVEYARD_ARCHIVE_EMPTY, True, (180, 180, 180))
            screen.blit(empty_txt, (list_rect.x, list_rect.y))
            self.details_buttons = {}
            self.genealogy_buttons = {}
            return

        content_height = len(gy.archive) * self.ROW_HEIGHT
        self.archive_scroll.update_bounds(content_height, list_rect.height)
        scroll = self.archive_scroll.offset

        prev_clip = screen.get_clip()
        screen.set_clip(list_rect)

        self.details_buttons = {}
        self.genealogy_buttons = {}
        mouse_pos = pygame.mouse.get_pos()

        for index, entry in enumerate(gy.archive):
            row_y = list_rect.y + index * self.ROW_HEIGHT - scroll
            if row_y + self.ROW_HEIGHT < list_rect.y or row_y > list_rect.bottom:
                continue

            fresh_record = gy.get_fresh_record(entry["id"])
            label = ci_info.INFO_GRAVEYARD_ARCHIVE_ENTRY.format(name=entry["name"], id=entry["id"])
            max_name_width = list_rect.width - (134 if fresh_record else 0)
            name_txt = self.font.render(
                truncate_text(self.font, label, max_name_width), True, settings.TEXT_COLOR)
            screen.blit(name_txt, (list_rect.x, row_y + 4))

            if fresh_record:
                details_rect = pygame.Rect(list_rect.right - 178, row_y + 2, 112, self.ROW_HEIGHT - 6)
                genealogy_rect = pygame.Rect(list_rect.right - 64, row_y + 2, 62, self.ROW_HEIGHT - 6)

                details_color = (settings.BUTTON_HOVER if details_rect.collidepoint(mouse_pos)
                                 else settings.BUTTON_COLOR)
                pygame.draw.rect(screen, details_color, details_rect, border_radius=4)
                details_txt = self.font.render(
                    ci_info.INFO_GRAVEYARD_DETAILS_BTN, True, settings.TEXT_COLOR)
                screen.blit(details_txt, details_txt.get_rect(center=details_rect.center))
                self.details_buttons[entry["id"]] = details_rect

                genealogy_color = (settings.BUTTON_HOVER if genealogy_rect.collidepoint(mouse_pos)
                                   else settings.BUTTON_COLOR)
                pygame.draw.rect(screen, genealogy_color, genealogy_rect, border_radius=4)
                genealogy_txt = self.font.render(
                    ci_info.INFO_BTN_GENEALOGY, True, settings.TEXT_COLOR)
                screen.blit(genealogy_txt, genealogy_txt.get_rect(center=genealogy_rect.center))
                self.genealogy_buttons[entry["id"]] = genealogy_rect

        screen.set_clip(prev_clip)

        if self.archive_scroll.max_scroll > 0:
            self.archive_scroll.draw_scrollbar(screen, list_rect)

    def draw_popup(self, screen):
        record = self.details_record
        if record is None:
            return

        window_w, window_h = screen.get_width(), screen.get_height()
        width, height = 300, 230
        rect = pygame.Rect((window_w - width) // 2, (window_h - height) // 2, width, height)

        overlay = pygame.Surface((window_w, window_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        screen.blit(overlay, (0, 0))

        pygame.draw.rect(screen, settings.INFO_PANEL_COLOR, rect)
        pygame.draw.rect(screen, settings.INFO_PANEL_BORDER, rect, 2)

        title_txt = self.font.render(ci_info.INFO_GRAVEYARD_DETAILS_TITLE, True, settings.TEXT_COLOR)
        screen.blit(title_txt, (rect.x + 12, rect.y + 10))

        y = rect.y + 40
        gender_label = (info.INFO_GENDER_FEMALE if record["gender"] == ci_settings.GENDER_FEMALE
                        else info.INFO_GENDER_MALE)

        raw_cause = record["death_cause"]
        if raw_cause in ci_info.DEATH_CAUSE_DISPLAY_MAP:
            cause_display = ci_info.gendered_text(ci_info.DEATH_CAUSE_DISPLAY_MAP[raw_cause], record["gender"])
        else:
            cause_display = ci_info.INFO_GRAVEYARD_DETAILS_CAUSE.format(cause=raw_cause or "-")

        lines = [
            ci_info.INFO_GRAVEYARD_DETAILS_NAME.format(name=record["name"]),
            ci_info.INFO_GRAVEYARD_DETAILS_ID.format(id=record["id"]),
            ci_info.INFO_GRAVEYARD_DETAILS_GENDER.format(gender=gender_label),
            ci_info.INFO_GRAVEYARD_DETAILS_TEMPERAMENT.format(
                temperament=ci_info.gendered_text(record["temperament"], record["gender"])),
            ci_info.INFO_GRAVEYARD_DETAILS_AGE.format(age=int(record["age"] // 60)),
            cause_display,
        ]
        for line in lines:
            line_txt = self.font.render(line, True, settings.TEXT_COLOR)
            screen.blit(line_txt, (rect.x + 12, y))
            y += 24

        remaining = max(0.0, ci_settings.GRAVEYARD_DATA_RETENTION - record.get("time_since_burial", 0.0))
        minutes_left = int(remaining // 60)
        seconds_left = int(remaining % 60)
        time_txt = self.font.render(
            ci_info.INFO_GRAVEYARD_DETAILS_TIME_LEFT.format(time=f"{minutes_left}:{seconds_left:02d}"),
            True, (200, 200, 120))
        screen.blit(time_txt, (rect.x + 12, y))

        self.details_close_rect = pygame.Rect(rect.x + 12, rect.bottom + 5, width - 24, 28)
        mouse_pos = pygame.mouse.get_pos()
        close_color = (settings.CLOSE_BUTTON_HOVER if self.details_close_rect.collidepoint(mouse_pos)
                       else settings.CLOSE_BUTTON_COLOR)
        pygame.draw.rect(screen, close_color, self.details_close_rect, border_radius=4)
        close_txt = self.font.render(ci_info.INFO_GRAVEYARD_DETAILS_CLOSE, True, settings.TEXT_COLOR)
        screen.blit(close_txt, close_txt.get_rect(center=self.details_close_rect.center))