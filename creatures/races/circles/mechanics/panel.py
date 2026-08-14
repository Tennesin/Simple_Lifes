"""Правая информационная панель конкретно для существа расы 'Круг'
(полоски здоровья/голода/жажды, психика, семья, взаимоотношения)."""

import time
import pygame
import math

from objects import Bush, WaterPuddle
from settings import *
from info import *
from game.widgets import Button, ScrollArea
from ..ci_settings import *
from ..ci_info import *
from ....all_needed.diet import DIET_DISPLAY_MAP

class CreaturePanel:

    def __init__(self, game, font):
        self.game = game
        self.font = font

        # ---------- Раскрывающаяся секция "Взаимоотношения" ----------
        self.show_relationships_section = False
        self.relationships_scroll_offset = 0
        self.relationships_header_rect = None
        self.relationships_list_rect = None
        self.relationships_max_scroll = 0
        # ---------- Перетаскивание ползунка мышью ----------
        self.relationships_scrollbar_rect = None
        self._relationships_scrollbar_dragging = False
        self._relationships_track_top = 0
        self._relationships_track_height = 0
        self.stat_bar_rects = {}

        self._last_creature_id = None
        self.genealogy_btn_rect = None

        # ---------- Левое окно психики ----------
        self.show_psyche_section = False
        self.psyche_header_rect = None
        self.psyche_panel_rect = None

        self.rebuild_layout(WINDOW_WIDTH, WINDOW_HEIGHT)

    def rebuild_layout(self, window_w, window_h):
        self.window_h = window_h
        self.info_panel_rect = pygame.Rect(
            window_w - INFO_PANEL_WIDTH, UI_HEIGHT,
            INFO_PANEL_WIDTH, window_h - UI_HEIGHT
        )

        id_row_y = self.info_panel_rect.y + 8
        btn_width, btn_height, btn_gap = 85, BUTTON_HEIGHT - 4, 6
        self.btn_creature_hit = Button(
            pygame.Rect(self.info_panel_rect.right - 10 - btn_width, id_row_y, btn_width, btn_height),
            INFO_BTN_HIT)
        self.btn_creature_pet = Button(
            pygame.Rect(self.btn_creature_hit.rect.x - btn_gap - btn_width, id_row_y, btn_width, btn_height),
            INFO_BTN_PET)

        self.name_field_rect = pygame.Rect(
            self.info_panel_rect.x + 10, id_row_y + btn_height + 8,
            INFO_PANEL_WIDTH - 20, 26
        )

    # ---------- Текстовые утилиты ----------

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

    def _draw_wrapped_text(self, screen, text, x, y, max_width, color, line_height=22):
        for line in self._wrap_text(text, max_width):
            txt = self.font.render(line, True, color)
            screen.blit(txt, (x, y))
            y += line_height
        return y

    def _truncate_text(self, text, max_width):
        if self.font.size(text)[0] <= max_width:
            return text
        while text and self.font.size(text + "…")[0] > max_width:
            text = text[:-1]
        return (text + "…") if text else "…"

    def _check_creature_changed(self, creature):
        if creature.id != self._last_creature_id:
            self._last_creature_id = creature.id
            self.show_relationships_section = False
            self.relationships_scroll_offset = 0
            self.show_psyche_section = False
            self._relationships_scrollbar_dragging = False

    def handle_info_panel_click(self, game, mouse_x, mouse_y):
        """Клик внутри info_panel_rect выбранного существа этой расы."""
        if self.name_field_rect.collidepoint(mouse_x, mouse_y):
            game.start_name_editing()
            return True
        if self.relationships_header_rect and self.relationships_header_rect.collidepoint(mouse_x, mouse_y):
            game.finish_name_editing()
            self.show_relationships_section = not self.show_relationships_section
            self.relationships_scroll_offset = 0
            return True
        if self.psyche_header_rect and self.psyche_header_rect.collidepoint(mouse_x, mouse_y):
            game.finish_name_editing()
            self.show_psyche_section = not self.show_psyche_section
            return True
        if self.genealogy_btn_rect and self.genealogy_btn_rect.collidepoint(mouse_x, mouse_y):
            game.finish_name_editing()
            game.ui.genealogy_overlay.open(game.selected_creature.id)
            return True
        game.finish_name_editing()
        return True

    def is_point_in_extra_panel(self, mouse_x, mouse_y):
        return bool(self.show_psyche_section and self.psyche_panel_rect
                    and self.psyche_panel_rect.collidepoint(mouse_x, mouse_y))

    def _draw_stat_bar(self, screen, label, value, max_value, color, x, y, width, stat_key=None):
        label_txt = self.font.render(f"{label}: {value:.1f}/{max_value}", True, TEXT_COLOR)
        screen.blit(label_txt, (x, y))
        bar_rect = pygame.Rect(x, y + 20, width, 10)
        pygame.draw.rect(screen, (30, 30, 30), bar_rect)
        ratio = max(0, min(1, value / max_value))
        fill_rect = pygame.Rect(x, y + 20, width * ratio, 10)
        pygame.draw.rect(screen, color, fill_rect)

        # ---------- Центральная линия - порог "уменьшить слева / увеличить справа" ----------
        center_x = x + width // 2
        pygame.draw.line(screen, (255, 255, 255), (center_x, bar_rect.y - 2), (center_x, bar_rect.bottom + 2), 2)

        if stat_key is not None:
            self.stat_bar_rects[stat_key] = bar_rect

    # ---------- Основная отрисовка ----------

    def draw(self, screen):
        game = self.game
        self.stat_bar_rects = {}
        creature = game.selected_creature
        if not creature:
            self.psyche_panel_rect = None
            self.relationships_scrollbar_rect = None
            return
        self._check_creature_changed(creature)
        panel = self.info_panel_rect
        pygame.draw.rect(screen, INFO_PANEL_COLOR, panel)
        pygame.draw.rect(screen, INFO_PANEL_BORDER, panel, 2)

        id_txt = self.font.render(INFO_INFO_ID.format(creature_id=creature.id), True, TEXT_COLOR)
        screen.blit(id_txt, (panel.x + 10, panel.y + 12))

        if not creature.is_dead:
            mouse_pos = pygame.mouse.get_pos()
            self.btn_creature_pet.draw(screen, mouse_pos)
            self.btn_creature_hit.draw(screen, mouse_pos)

        field = self.name_field_rect
        field_color = NAME_FIELD_EDIT_COLOR if game.editing_name else NAME_FIELD_COLOR
        pygame.draw.rect(screen, field_color, field)
        pygame.draw.rect(screen, INFO_PANEL_BORDER, field, 1)

        if game.editing_name:
            display_name = game.name_edit_buffer
            if int(time.time() * 2) % 2 == 0:
                display_name += "|"
            text_color = (0, 0, 0)
        else:
            display_name = creature.name if creature.name else INFO_INFO_NO_NAME
            text_color = TEXT_COLOR if creature.name else (180, 180, 180)

        name_txt = self.font.render(display_name, True, text_color)
        screen.blit(name_txt, (field.x + 5, field.y + 4))

        y = field.bottom + 16

        kind_txt = self.font.render(INFO_INFO_KIND.format(kind=creature.get_type_name()), True, TEXT_COLOR)
        screen.blit(kind_txt, (panel.x + 10, y))

        age_minutes = int(creature.age // 60)
        age_txt = self.font.render(INFO_INFO_AGE_MINUTES.format(age=age_minutes), True, TEXT_COLOR)
        screen.blit(age_txt, (panel.x + 150, y))
        y += 30

        col2_x = panel.x + 150
        col2_width = panel.width - 150 - 10
        row2_bottom = y + 30

        gender_label = INFO_GENDER_FEMALE if creature.gender == GENDER_FEMALE else INFO_GENDER_MALE
        gender_color = CREATURE_COLOR_FEMALE if creature.gender == GENDER_FEMALE else CREATURE_COLOR_MALE
        gender_txt = self.font.render(INFO_INFO_GENDER.format(gender=gender_label), True, gender_color)
        screen.blit(gender_txt, (panel.x + 10, y))

        if not creature.is_dead:
            temp_end_y = self._draw_wrapped_text(
                screen, INFO_INFO_TEMPERAMENT.format(temperament=gendered_text(creature.temperament, creature.gender)),
                col2_x, y, col2_width, TEXT_COLOR)
            row2_bottom = max(row2_bottom, temp_end_y)

        y = row2_bottom + 2

        diet_label = DIET_DISPLAY_MAP.get(creature.diet, creature.diet)
        diet_txt = self.font.render(INFO_INFO_DIET.format(diet=diet_label), True, (150, 210, 130))
        screen.blit(diet_txt, (panel.x + 10, y))
        if not creature.is_dead:
            self._draw_genealogy_button(screen, y - 3)
        y += 28

        if creature.is_dead:
            status_txt = self.font.render(INFO_INFO_STATUS_DEAD, True, (210, 90, 90))
            screen.blit(status_txt, (panel.x + 10, y))
            y += 26
            if creature.death_cause:
                max_text_width = panel.width - 20
                y = self._draw_wrapped_text(
                    screen, gendered_text(DEATH_CAUSE_DISPLAY_MAP.get(creature.death_cause, ""), creature.gender),
                    panel.x + 10, y, max_text_width, TEXT_COLOR)
                y += 8
            timer_txt = self.font.render(INFO_INFO_DEATH_TIMER.format(time=creature.death_timer), True, TEXT_COLOR)
            screen.blit(timer_txt, (panel.x + 10, y))
            y += 30
            self._draw_relationships_section(screen, creature, panel.x + 10, y, panel.width - 20)
            self.psyche_panel_rect = None
            return

        y = self._draw_family_info(screen, creature, panel.x + 10, y, panel.width - 20)
        y = self._draw_psyche_toggle(screen, panel.x + 10, y, panel.width - 20)

        self._draw_stat_bar(screen, INFO_INFO_HP, creature.hp, HP_MAX, (220, 60, 60),
                            panel.x + 10, y, panel.width - 20, stat_key="hp")
        y += 40
        self._draw_stat_bar(screen, INFO_INFO_HUNGER, creature.hunger, HUNGER_MAX, (200, 150, 40),
                            panel.x + 10, y, panel.width - 20, stat_key="hunger")
        y += 40
        self._draw_stat_bar(screen, INFO_INFO_THIRST, creature.thirst, THIRST_MAX, (60, 140, 220),
                            panel.x + 10, y, panel.width - 20, stat_key="thirst")
        y += 40
        self._draw_stat_bar(screen, INFO_INFO_ENERGY, creature.energy, ENERGY_MAX, (90, 200, 200),
                            panel.x + 10, y, panel.width - 20, stat_key="energy")
        y += 40

        state_color_map = {
            STATE_CALM: (120, 220, 120),
            STATE_SEEKING: (230, 200, 60),
            STATE_PANIC: (230, 70, 70),
            STATE_SLEEP: (120, 160, 220)
        }
        state_txt = self.font.render(
            INFO_INFO_STATE.format(state=gendered_text(creature.state, creature.gender)),
            True, state_color_map.get(creature.state, TEXT_COLOR))
        screen.blit(state_txt, (panel.x + 10, y))
        y += 24

        if creature.gender == GENDER_FEMALE and creature.is_pregnant:
            pregnant_txt = self.font.render(INFO_INFO_PREGNANT, True, (255, 170, 210))
            screen.blit(pregnant_txt, (panel.x + 10, y))
            y += 24

        if creature.puberty_active:
            puberty_txt = self.font.render(INFO_INFO_PUBERTY_ACTIVE, True, PUBERTY_RING_COLOR)
            screen.blit(puberty_txt, (panel.x + 10, y))
            y += 24

        max_text_width = panel.width - 20
        y = self._draw_wrapped_text(
            screen, INFO_INFO_GOAL.format(goal=gendered_text(creature.goal_text, creature.gender)),
            panel.x + 10, y, max_text_width, TEXT_COLOR)
        y += 12
        self._draw_relationships_section(screen, creature, panel.x + 10, y, panel.width - 20)

        if self.show_psyche_section:
            self._draw_psyche_panel(screen, creature)
        else:
            self.psyche_panel_rect = None

    # ---------- Семья ----------

    def _resolve_parent_name(self, parent_id):
        game = self.game
        if parent_id is None:
            return None
        found = next((c for c in game.world.creatures if c.id == parent_id), None)
        if found is not None:
            return found.name if found.name else found.id
        for gy in game.world.graveyards:
            entry = next((a for a in gy.archive if a["id"] == parent_id), None)
            if entry is not None:
                return entry["name"] if entry["name"] else entry["id"]
        return INFO_INFO_UNKNOWN_PARENT

    def _draw_parent_line(self, screen, creature, label_template, index, x, y):
        if creature.parent_ids is None:
            name = INFO_INFO_HEAVEN
        else:
            parent_id = creature.parent_ids[index] if index < len(creature.parent_ids) else None
            name = INFO_INFO_UNKNOWN_PARENT if parent_id is None else self._resolve_parent_name(parent_id)
        txt = self.font.render(label_template.format(name=name), True, TEXT_COLOR)
        screen.blit(txt, (x, y))
        return y + 24

    def _draw_family_info(self, screen, creature, x, y, max_width):
        game = self.game

        y = self._draw_parent_line(screen, creature, INFO_INFO_MOTHER, 0, x, y)
        y = self._draw_parent_line(screen, creature, INFO_INFO_FATHER, 1, x, y)

        partner = None
        if creature.partner_id:
            partner = next((c for c in game.world.creatures
                            if c.id == creature.partner_id and not c.is_dead), None)
        partner_label = (partner.name if partner and partner.name
                         else (partner.id if partner else INFO_INFO_PARTNER_NONE))
        partner_txt = self.font.render(INFO_INFO_PARTNER.format(name=partner_label), True, TEXT_COLOR)
        screen.blit(partner_txt, (x, y))
        y += 24

        sons = [c for c in game.world.creatures
                if c.parent_ids and creature.id in c.parent_ids and not c.is_dead and c.gender == GENDER_MALE]
        daughters = [c for c in game.world.creatures
                     if c.parent_ids and creature.id in c.parent_ids and not c.is_dead and c.gender == GENDER_FEMALE]

        if not sons and not daughters:
            children_txt = self.font.render(INFO_INFO_CHILDREN.format(names=INFO_INFO_CHILDREN_NONE), True, TEXT_COLOR)
            screen.blit(children_txt, (x, y))
            y += 24
        else:
            sons_names = ", ".join(c.name if c.name else c.id for c in sons) if sons else INFO_INFO_CHILDREN_NONE
            daughters_names = ", ".join(
                c.name if c.name else c.id for c in daughters) if daughters else INFO_INFO_CHILDREN_NONE
            y = self._draw_wrapped_text(screen, INFO_INFO_SONS.format(names=sons_names), x, y, max_width, TEXT_COLOR)
            y = self._draw_wrapped_text(screen, INFO_INFO_DAUGHTERS.format(names=daughters_names), x, y, max_width,
                                        TEXT_COLOR)

        y += 10
        return y

    # ---------- Отношение к игроку ----------

    def _relationship_label(self, creature):
        if creature.player_fear_timer > 0:
            return gendered_text(INFO_RELATIONSHIP_FEAR, creature.gender), (230, 70, 70)
        if creature.calm_timer > 0:
            return gendered_text(INFO_RELATIONSHIP_CALMED, creature.gender), (255, 210, 120)

        r = creature.player_relationship
        if r <= -70:
            return gendered_text(INFO_RELATIONSHIP_DESPISE, creature.gender), (210, 40, 40)
        elif r <= -30:
            return gendered_text(INFO_RELATIONSHIP_AFRAID, creature.gender), (215, 100, 60)
        elif r <= -10:
            return gendered_text(INFO_RELATIONSHIP_WARY, creature.gender), (210, 160, 70)
        elif r < 10:
            return gendered_text(INFO_RELATIONSHIP_NEUTRAL, creature.gender), (190, 190, 190)
        elif r < 30:
            return gendered_text(INFO_RELATIONSHIP_FRIENDLY, creature.gender), (150, 200, 120)
        elif r < 70:
            return gendered_text(INFO_RELATIONSHIP_TRUST, creature.gender), (100, 210, 130)
        else:
            return gendered_text(INFO_RELATIONSHIP_DEVOTED, creature.gender), (80, 230, 140)

    def _draw_relationship_bar(self, screen, creature, x, y, width):
        label, color = self._relationship_label(creature)
        label_txt = self.font.render(INFO_INFO_RELATIONSHIP.format(label=label), True, color)
        screen.blit(label_txt, (x, y))

        bar_y = y + 22
        bar_height = 10
        bar_rect = pygame.Rect(x, bar_y, width, bar_height)
        pygame.draw.rect(screen, (30, 30, 30), bar_rect)

        mid_x = x + width // 2
        pygame.draw.line(screen, (110, 110, 110), (mid_x, bar_y), (mid_x, bar_y + bar_height), 1)

        ratio = max(-1.0, min(1.0, creature.player_relationship / 100.0))
        marker_x = mid_x + ratio * (width // 2)

        if ratio >= 0:
            fill_rect = pygame.Rect(mid_x, bar_y, marker_x - mid_x, bar_height)
            fill_color = (90, 200, 120)
        else:
            fill_rect = pygame.Rect(marker_x, bar_y, mid_x - marker_x, bar_height)
            fill_color = (200, 80, 80)
        pygame.draw.rect(screen, fill_color, fill_rect)
        pygame.draw.rect(screen, (15, 15, 15), bar_rect, 1)

        tri_half = 6
        tri_bottom_y = bar_y - 2
        tri_top_y = tri_bottom_y - tri_half - 2
        pygame.draw.polygon(screen, TEXT_COLOR, [
            (marker_x - tri_half, tri_top_y),
            (marker_x + tri_half, tri_top_y),
            (marker_x, tri_bottom_y),
        ])

        value_txt = self.font.render(f"{ratio:+.2f}", True, TEXT_COLOR)
        screen.blit(value_txt, (x + width - value_txt.get_width(), bar_y + bar_height + 4))

        return bar_y + bar_height + 26

    # ---------- Секция "Взаимоотношения" ----------

    def _draw_relationships_section(self, screen, creature, x, y, width):
        header_rect = pygame.Rect(x, y, width, 26)

        mouse_pos = pygame.mouse.get_pos()
        header_color = MENU_HOVER if header_rect.collidepoint(mouse_pos) else BUTTON_COLOR
        pygame.draw.rect(screen, header_color, header_rect)
        arrow = "<" if self.show_relationships_section else "v"
        txt = self.font.render(f"{arrow} {INFO_RELATIONSHIPS_TITLE}", True, TEXT_COLOR)
        screen.blit(txt, (header_rect.x + 6, header_rect.y + 3))
        self.relationships_header_rect = header_rect
        y = header_rect.bottom + 8

        if not self.show_relationships_section:
            self.relationships_list_rect = None
            self.relationships_max_scroll = 0
            self.relationships_scrollbar_rect = None  # NEW
            return y

        SCROLLBAR_RESERVE = 10
        col_gap = 10
        col_width = (width - col_gap - SCROLLBAR_RESERVE) // 2

        game = self.game
        males, females = [], []
        for other_id, value in creature.relationships.items():
            other = next((o for o in game.world.creatures if o.id == other_id), None)
            if other is None or other is creature:
                continue
            is_close = (
                    other.id == creature.partner_id or
                    (other.parent_ids and creature.id in other.parent_ids) or
                    (creature.parent_ids and other.id in creature.parent_ids)
            )
            entry = (other, value, is_close)
            (females if other.gender == GENDER_FEMALE else males).append(entry)

        males.sort(key=lambda e: (e[0].name or "").lower())
        females.sort(key=lambda e: (e[0].name or "").lower())

        if not males and not females:
            empty_txt = self.font.render(INFO_RELATIONSHIPS_EMPTY, True, (180, 180, 180))
            screen.blit(empty_txt, (x, y))
            self.relationships_list_rect = None
            self.relationships_max_scroll = 0
            self.relationships_scrollbar_rect = None  # NEW
            return y + 24

        male_header = self.font.render(INFO_RELATIONSHIPS_MALES, True, (170, 190, 230))
        screen.blit(male_header, (x, y))
        female_header = self.font.render(INFO_RELATIONSHIPS_FEMALES, True, (230, 170, 210))
        screen.blit(female_header, (x + col_width + col_gap, y))
        y += 24

        row_height = 22
        available_height = max(50, self.window_h - y - 10)
        max_rows = max(len(males), len(females), 1)
        content_height = max_rows * row_height
        max_scroll = max(0, content_height - available_height)
        self.relationships_scroll_offset = max(0, min(self.relationships_scroll_offset, max_scroll))
        self.relationships_max_scroll = max_scroll
        scroll = self.relationships_scroll_offset

        list_rect = pygame.Rect(x, y, width, available_height)
        self.relationships_list_rect = list_rect

        prev_clip = screen.get_clip()
        screen.set_clip(list_rect)

        for col_index, entries in enumerate((males, females)):
            col_x = x + col_index * (col_width + col_gap)
            for row_index, (other, value, is_close) in enumerate(entries):
                row_y = y + row_index * row_height - scroll
                if row_y + row_height < y or row_y > y + available_height:
                    continue
                color = (255, 210, 60) if is_close else TEXT_COLOR
                name = other.name if other.name else other.id
                value_txt = self.font.render(f"{value:+.0f}", True, color)
                name_max_width = col_width - value_txt.get_width() - 8
                name_txt = self.font.render(self._truncate_text(name, name_max_width), True, color)
                screen.blit(name_txt, (col_x, row_y))
                screen.blit(value_txt, (col_x + col_width - value_txt.get_width(), row_y))

        screen.set_clip(prev_clip)

        if max_scroll > 0:
            track_rect = pygame.Rect(x + width - 4, y, 4, available_height)
            pygame.draw.rect(screen, (30, 30, 30), track_rect)
            thumb_h = max(20, int(available_height * available_height / content_height))
            thumb_y = y + int((available_height - thumb_h) * (scroll / max_scroll))
            pygame.draw.rect(screen, (150, 150, 150), (track_rect.x, thumb_y, 4, thumb_h))

            self.relationships_scrollbar_rect = track_rect.inflate(10, 0)
            self._relationships_track_top = y
            self._relationships_track_height = available_height
        else:
            self.relationships_scrollbar_rect = None  # NEW

        return y + available_height

    def set_relationships_scroll_from_mouse(self, mouse_y):
        if self.relationships_max_scroll <= 0:
            return
        track_top = self._relationships_track_top
        track_height = self._relationships_track_height
        content_height = self.relationships_max_scroll + track_height
        thumb_h = max(20, int(track_height * track_height / content_height))
        usable = max(1, track_height - thumb_h)
        ratio = (mouse_y - track_top - thumb_h / 2) / usable
        ratio = max(0.0, min(1.0, ratio))
        self.relationships_scroll_offset = int(round(ratio * self.relationships_max_scroll))

    def _draw_psyche_panel(self, screen, creature):
        panel = self.info_panel_rect
        width = 250

        # ---------- Соприкасается правым краем с левой границей панели существа ----------
        x = max(10, panel.x - width)
        y = panel.y

        # ---------- Точный расчёт высоты содержимого, без магических чисел ----------
        line_h = self.font.get_height()
        axis_bar_h = 48 + line_h   # см. _draw_axis_bar: 20(заголовок)+14+high+14
        title_h = 28
        stat_bar_h = 40

        # заголовок + (К игроку) + Сознание + 5 показателей психики
        content_height = title_h + axis_bar_h + stat_bar_h + 5 * axis_bar_h
        height = min(content_height + 20, self.window_h - y - 10)

        rect = pygame.Rect(x, y, width, height)
        self.psyche_panel_rect = rect

        pygame.draw.rect(screen, INFO_PANEL_COLOR, rect)
        pygame.draw.rect(screen, INFO_PANEL_BORDER, rect, 2)

        inner_x = rect.x + 10
        inner_y = rect.y + 10
        inner_width = rect.width - 20

        title_txt = self.font.render(
            f"{INFO_PSYCHE_TITLE}: {creature.name if creature.name else creature.id}", True, TEXT_COLOR)
        screen.blit(title_txt, (inner_x, inner_y))
        inner_y += title_h

        label, _color = self._relationship_label(creature)
        inner_y = self._draw_axis_bar(
            screen, f"{INFO_PSYCHE_PLAYER_REL}: {label}", creature.player_relationship,
            INFO_RELATIONSHIP_DESPISE, INFO_RELATIONSHIP_DEVOTED, inner_x, inner_y, inner_width)

        self._draw_stat_bar(screen, INFO_PSYCHE_CONSCIOUSNESS, creature.consciousness, SANITY_MAX,
                            (160, 100, 220), inner_x, inner_y, inner_width, stat_key="consciousness")
        inner_y += stat_bar_h

        psyche = creature.psyche
        inner_y = self._draw_axis_bar(screen, INFO_PSYCHE_JOY_TITLE, psyche.joy,
                                      INFO_PSYCHE_JOY_LEFT, INFO_PSYCHE_JOY_RIGHT, inner_x, inner_y, inner_width)
        inner_y = self._draw_axis_bar(screen, INFO_PSYCHE_SATISFACTION_TITLE, psyche.satisfaction,
                                      INFO_PSYCHE_SATISFACTION_LEFT, INFO_PSYCHE_SATISFACTION_RIGHT,
                                      inner_x, inner_y, inner_width)
        inner_y = self._draw_axis_bar(screen, INFO_PSYCHE_CALM_TITLE, psyche.calmness,
                                      INFO_PSYCHE_CALM_LEFT, INFO_PSYCHE_CALM_RIGHT, inner_x, inner_y, inner_width)
        inner_y = self._draw_axis_bar(screen, INFO_PSYCHE_CONFIDENCE_TITLE, psyche.confidence,
                                      INFO_PSYCHE_CONFIDENCE_LEFT, INFO_PSYCHE_CONFIDENCE_RIGHT,
                                      inner_x, inner_y, inner_width)
        inner_y = self._draw_axis_bar(screen, INFO_PSYCHE_ATTACHMENT_TITLE, psyche.attachment,
                                      INFO_PSYCHE_ATTACHMENT_LEFT, INFO_PSYCHE_ATTACHMENT_RIGHT,
                                      inner_x, inner_y, inner_width)

    def _draw_axis_bar(self, screen, title, value, left_label, right_label, x, y, width):
        if title:
            title_txt = self.font.render(title, True, TEXT_COLOR)
            screen.blit(title_txt, (x, y))
            y += 20

        bar_height = 10
        bar_rect = pygame.Rect(x, y, width, bar_height)
        pygame.draw.rect(screen, (30, 30, 30), bar_rect)

        mid_x = x + width // 2
        pygame.draw.line(screen, (110, 110, 110), (mid_x, y), (mid_x, y + bar_height), 1)

        ratio = max(-1.0, min(1.0, value / 100.0))
        marker_x = mid_x + ratio * (width // 2)

        if ratio >= 0:
            fill_rect = pygame.Rect(mid_x, y, marker_x - mid_x, bar_height)
            fill_color = (90, 200, 120)
        else:
            fill_rect = pygame.Rect(marker_x, y, mid_x - marker_x, bar_height)
            fill_color = (200, 80, 80)
        pygame.draw.rect(screen, fill_color, fill_rect)
        pygame.draw.rect(screen, (15, 15, 15), bar_rect, 1)

        labels_y = y + bar_height + 4
        left_txt = self.font.render(left_label, True, (210, 130, 130))
        right_txt = self.font.render(right_label, True, (130, 210, 150))
        screen.blit(left_txt, (x, labels_y))
        screen.blit(right_txt, (x + width - right_txt.get_width(), labels_y))

        return labels_y + right_txt.get_height() + 14

    def _draw_psyche_toggle(self, screen, x, y, width):
        header_rect = pygame.Rect(x, y, width, 26)
        mouse_pos = pygame.mouse.get_pos()
        header_color = MENU_HOVER if header_rect.collidepoint(mouse_pos) else BUTTON_COLOR
        pygame.draw.rect(screen, header_color, header_rect)
        arrow = "<" if self.show_psyche_section else "v"
        txt = self.font.render(f"{arrow} {INFO_PSYCHE_TOGGLE}", True, TEXT_COLOR)
        screen.blit(txt, (header_rect.x + 6, header_rect.y + 3))
        self.psyche_header_rect = header_rect
        return header_rect.bottom + 10

    def _draw_genealogy_button(self, screen, y):
        panel = self.info_panel_rect
        btn_width, btn_height = 85, BUTTON_HEIGHT - 4
        rect = pygame.Rect(panel.right - 10 - btn_width, y, btn_width, btn_height)
        mouse_pos = pygame.mouse.get_pos()
        color = MENU_HOVER if rect.collidepoint(mouse_pos) else BUTTON_COLOR
        pygame.draw.rect(screen, color, rect, border_radius=4)
        txt = self.font.render(INFO_BTN_GENEALOGY, True, TEXT_COLOR)
        screen.blit(txt, txt.get_rect(center=rect.center))
        self.genealogy_btn_rect = rect

# =========================================================================
# Панель кладбища конкретно для расы 'Круг'
# =========================================================================

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

        self.rebuild_layout(WINDOW_WIDTH, WINDOW_HEIGHT)

    def rebuild_layout(self, window_w, window_h):
        self.panel_rect = pygame.Rect(
            window_w - INFO_PANEL_WIDTH, UI_HEIGHT,
            INFO_PANEL_WIDTH, window_h - UI_HEIGHT
        )
        self.name_field_rect = pygame.Rect(
            self.panel_rect.x + 10, self.panel_rect.y + 40,
            INFO_PANEL_WIDTH - 20, 26
        )

    def _truncate(self, text, max_width):
        if self.font.size(text)[0] <= max_width:
            return text
        while text and self.font.size(text + "…")[0] > max_width:
            text = text[:-1]
        return (text + "…") if text else "…"

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
        self.archive_scroll.scroll_by_wheel(wheel_y, speed=DEFAULT_SCROLL_SPEED)
        return True

    def handle_keydown(self, event):
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.finish_name_editing()
        elif event.key == pygame.K_ESCAPE:
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
        pygame.draw.rect(screen, INFO_PANEL_COLOR, panel)

        id_txt = self.font.render(INFO_GRAVEYARD_ID.format(graveyard_id=gy.id), True, TEXT_COLOR)
        screen.blit(id_txt, (panel.x + 10, panel.y + 12))

        field = self.name_field_rect
        field_color = NAME_FIELD_EDIT_COLOR if self.editing_name else NAME_FIELD_COLOR
        pygame.draw.rect(screen, field_color, field)
        pygame.draw.rect(screen, INFO_PANEL_BORDER, field, 1)

        if self.editing_name:
            display_name = self.name_edit_buffer
            if int(time.time() * 2) % 2 == 0:
                display_name += "|"
            text_color = (0, 0, 0)
        else:
            display_name = gy.name if gy.name else INFO_GRAVEYARD_DEFAULT_NAME
            text_color = TEXT_COLOR

        name_txt = self.font.render(display_name, True, text_color)
        screen.blit(name_txt, (field.x + 5, field.y + 4))

        list_top = field.bottom + 16
        list_rect = pygame.Rect(panel.x + 10, list_top, panel.width - 20, panel.bottom - list_top - 10)
        self.list_rect = list_rect

        if not gy.archive:
            empty_txt = self.font.render(INFO_GRAVEYARD_ARCHIVE_EMPTY, True, (180, 180, 180))
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
            label = INFO_GRAVEYARD_ARCHIVE_ENTRY.format(name=entry["name"], id=entry["id"])
            max_name_width = list_rect.width - (134 if fresh_record else 0)
            name_txt = self.font.render(self._truncate(label, max_name_width), True, TEXT_COLOR)
            screen.blit(name_txt, (list_rect.x, row_y + 4))

            if fresh_record:
                details_rect = pygame.Rect(list_rect.right - 178, row_y + 2, 112, self.ROW_HEIGHT - 6)
                genealogy_rect = pygame.Rect(list_rect.right - 64, row_y + 2, 62, self.ROW_HEIGHT - 6)

                details_color = BUTTON_HOVER if details_rect.collidepoint(mouse_pos) else BUTTON_COLOR
                pygame.draw.rect(screen, details_color, details_rect, border_radius=4)
                details_txt = self.font.render(INFO_GRAVEYARD_DETAILS_BTN, True, TEXT_COLOR)
                screen.blit(details_txt, details_txt.get_rect(center=details_rect.center))
                self.details_buttons[entry["id"]] = details_rect

                genealogy_color = BUTTON_HOVER if genealogy_rect.collidepoint(mouse_pos) else BUTTON_COLOR
                pygame.draw.rect(screen, genealogy_color, genealogy_rect, border_radius=4)
                genealogy_txt = self.font.render(INFO_BTN_GENEALOGY, True, TEXT_COLOR)
                screen.blit(genealogy_txt, genealogy_txt.get_rect(center=genealogy_rect.center))
                self.genealogy_buttons[entry["id"]] = genealogy_rect

        screen.set_clip(prev_clip)

        if self.archive_scroll.max_scroll > 0:
            self.archive_scroll.draw_scrollbar(screen, list_rect)

    def draw_popup(self, screen):
        record = self.details_record
        if record is None:
            return

        width, height = 300, 230
        rect = pygame.Rect((WINDOW_WIDTH - width) // 2, (WINDOW_HEIGHT - height) // 2, width, height)

        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        screen.blit(overlay, (0, 0))

        pygame.draw.rect(screen, INFO_PANEL_COLOR, rect)
        pygame.draw.rect(screen, INFO_PANEL_BORDER, rect, 2)

        title_txt = self.font.render(INFO_GRAVEYARD_DETAILS_TITLE, True, TEXT_COLOR)
        screen.blit(title_txt, (rect.x + 12, rect.y + 10))

        y = rect.y + 40
        gender_label = INFO_GENDER_FEMALE if record["gender"] == GENDER_FEMALE else INFO_GENDER_MALE

        raw_cause = record["death_cause"]
        if raw_cause in DEATH_CAUSE_DISPLAY_MAP:
            cause_display = gendered_text(DEATH_CAUSE_DISPLAY_MAP[raw_cause], record["gender"])
        else:
            cause_display = INFO_GRAVEYARD_DETAILS_CAUSE.format(cause=raw_cause or "-")

        lines = [
            INFO_GRAVEYARD_DETAILS_NAME.format(name=record["name"]),
            INFO_GRAVEYARD_DETAILS_ID.format(id=record["id"]),
            INFO_GRAVEYARD_DETAILS_GENDER.format(gender=gender_label),
            INFO_GRAVEYARD_DETAILS_TEMPERAMENT.format(
                temperament=gendered_text(record["temperament"], record["gender"])),
            INFO_GRAVEYARD_DETAILS_AGE.format(age=int(record["age"] // 60)),
            cause_display,
        ]
        for line in lines:
            line_txt = self.font.render(line, True, TEXT_COLOR)
            screen.blit(line_txt, (rect.x + 12, y))
            y += 24

        remaining = max(0.0, GRAVEYARD_DATA_RETENTION - record.get("time_since_burial", 0.0))
        minutes_left = int(remaining // 60)
        seconds_left = int(remaining % 60)
        time_txt = self.font.render(
            INFO_GRAVEYARD_DETAILS_TIME_LEFT.format(time=f"{minutes_left}:{seconds_left:02d}"),
            True, (200, 200, 120))
        screen.blit(time_txt, (rect.x + 12, y))

        self.details_close_rect = pygame.Rect(rect.x + 12, rect.bottom + 5, width - 24, 28)
        mouse_pos = pygame.mouse.get_pos()
        close_color = CLOSE_BUTTON_HOVER if self.details_close_rect.collidepoint(mouse_pos) else CLOSE_BUTTON_COLOR
        pygame.draw.rect(screen, close_color, self.details_close_rect, border_radius=4)
        close_txt = self.font.render(INFO_GRAVEYARD_DETAILS_CLOSE, True, TEXT_COLOR)
        screen.blit(close_txt, close_txt.get_rect(center=self.details_close_rect.center))


# =========================================================================
# Древо Родословной - модальный оверлей
# =========================================================================

class GenealogyTreeOverlay:

    def __init__(self, game, font):
        self.game = game
        self.font = font
        self.title_font = pygame.font.SysFont(FONT_NAME, FONT_SIZE_TITLE)
        self.name_font = pygame.font.SysFont(FONT_NAME, 13)

        self.selected = None  # чтобы не попадать в протокол боковой панели существа
        self.active = False
        self.root_id = None
        self.pan_x = 0.0
        self.pan_y = 0.0
        self._dragging = False
        self._drag_last = (0, 0)

        self.panel_rect = pygame.Rect(0, 0, 0, 0)
        self.close_btn_rect = pygame.Rect(0, 0, 0, 0)
        self.viewport_rect = pygame.Rect(0, 0, 0, 0)
        self._node_screen_rects = {}

    # ---------- Протокол, который читают core-файлы обобщённо ----------

    @property
    def modal_active(self):
        return self.active

    def clear(self, game):
        self.close()

    # ---------- Открытие / закрытие ----------

    def open(self, root_id):
        self.active = True
        self.root_id = root_id
        self.pan_x = 0.0
        self.pan_y = 0.0
        self._dragging = False

    def close(self):
        self.active = False
        self.root_id = None
        self._dragging = False

    def _registry(self):
        manager = self.game.object_manager.spawn_managers.get("circle")
        return manager.genealogy if manager is not None else None

    # ---------- Ввод ----------

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.close_btn_rect.collidepoint(event.pos):
                self.close()
                return
            if self.viewport_rect.collidepoint(event.pos):
                self._dragging = True
                self._drag_last = event.pos
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._dragging = False
        elif event.type == pygame.MOUSEMOTION and self._dragging:
            dx = event.pos[0] - self._drag_last[0]
            dy = event.pos[1] - self._drag_last[1]
            self.pan_x += dx
            self.pan_y += dy
            self._drag_last = event.pos

    # ---------- Построение узлов: предки (бинарно, пост-order) ----------

    def _build_ancestors(self, registry, root_id):
        nodes = {}
        edges = []
        counter = [0]

        def assign(cid, generation):
            if cid is None or generation > GENEALOGY_MAX_DEPTH:
                return None
            rec = registry.get(cid)
            if rec is None:
                return None
            parent_ids = rec["parent_ids"]
            mother_x = father_x = None
            if parent_ids and generation < GENEALOGY_MAX_DEPTH:
                mother_id = parent_ids[0] if len(parent_ids) > 0 else None
                father_id = parent_ids[1] if len(parent_ids) > 1 else None
                mother_x = assign(mother_id, generation + 1)
                father_x = assign(father_id, generation + 1)

            if mother_x is not None and father_x is not None:
                x = (mother_x + father_x) / 2
            elif mother_x is not None:
                x = mother_x
            elif father_x is not None:
                x = father_x
            else:
                x = float(counter[0])
                counter[0] += 1

            nodes[cid] = {"id": cid, "generation": -generation, "x": x, "is_root": generation == 0}
            if mother_x is not None:
                edges.append((parent_ids[0], cid))
            if father_x is not None:
                edges.append((parent_ids[1], cid))
            return x

        assign(root_id, 0)
        nodes.pop(root_id, None)
        return nodes, edges

    # ---------- Построение узлов: потомки (n-арно, пост-order) ----------

    def _build_descendants(self, registry, root_id):
        nodes = {}
        edges = []
        counter = [0]

        def assign(cid, generation):
            rec = registry.get(cid)
            if rec is None:
                return None
            children = registry.children_of(cid) if generation < GENEALOGY_MAX_DEPTH else []
            if children:
                child_xs = []
                for child_id in children:
                    cx = assign(child_id, generation + 1)
                    if cx is not None:
                        child_xs.append(cx)
                        edges.append((cid, child_id))
                x = sum(child_xs) / len(child_xs) if child_xs else float(counter[0])
                if not child_xs:
                    counter[0] += 1
            else:
                x = float(counter[0])
                counter[0] += 1

            if generation > 0:
                nodes[cid] = {"id": cid, "generation": generation, "x": x, "is_root": False}
            return x

        assign(root_id, 0)
        return nodes, edges

    # ---------- Партнёр: только текущий/последний известный, без своей ветки ----------

    def _display_partner_id(self, registry, creature_id):
        live = next((c for c in self.game.world.creatures
                     if c.id == creature_id and not c.is_dead), None)
        if live is not None and live.partner_id is not None:
            return live.partner_id
        partners = registry.partners_of(creature_id)
        return partners[-1] if partners else None

    # ---------- Итоговая сборка + центрирование относительно корня ----------

    def _build_layout(self):
        registry = self._registry()
        if registry is None or self.root_id is None or registry.get(self.root_id) is None:
            return [], [], (0, 0, 0, 0)

        ancestor_nodes, ancestor_edges = self._build_ancestors(registry, self.root_id)
        descendant_nodes, descendant_edges = self._build_descendants(registry, self.root_id)

        root_rec = registry.get(self.root_id)
        parent_ids = root_rec["parent_ids"] or []
        direct_parent_xs = [ancestor_nodes[pid]["x"] for pid in parent_ids
                            if pid is not None and pid in ancestor_nodes]
        if direct_parent_xs:
            shift = -sum(direct_parent_xs) / len(direct_parent_xs)
            for node in ancestor_nodes.values():
                node["x"] += shift

        direct_children_ids = registry.children_of(self.root_id)
        direct_child_xs = [descendant_nodes[cid]["x"] for cid in direct_children_ids
                           if cid in descendant_nodes]
        if direct_child_xs:
            shift = -sum(direct_child_xs) / len(direct_child_xs)
            for node in descendant_nodes.values():
                node["x"] += shift

        all_nodes = {self.root_id: {"id": self.root_id, "generation": 0, "x": 0.0, "is_root": True}}
        all_nodes.update(ancestor_nodes)
        all_nodes.update(descendant_nodes)
        all_edges = [(a, b, "blood") for a, b in ancestor_edges + descendant_edges]

        for node in list(all_nodes.values()):
            partner_id = self._display_partner_id(registry, node["id"])
            if partner_id is None or partner_id in all_nodes or registry.get(partner_id) is None:
                continue
            key = partner_id + "::partner_of::" + node["id"]
            all_nodes[key] = {
                "id": partner_id, "generation": node["generation"],
                "x": node["x"] + GENEALOGY_PARTNER_OFFSET / GENEALOGY_SLOT_WIDTH,
                "is_root": False,
            }
            all_edges.append((node["id"], partner_id, "partner"))

        self._resolve_overlaps(all_nodes)
        nodes_list = list(all_nodes.values())
        if not nodes_list:
            bbox = (0, 0, 0, 0)
        else:
            xs = [n["x"] for n in nodes_list]
            gens = [n["generation"] for n in nodes_list]
            bbox = (min(xs), max(xs), min(gens), max(gens))
        return nodes_list, all_edges, bbox

    def _any_node_offscreen(self, nodes):
        if not nodes:
            return False
        center_x, center_y = self.viewport_rect.centerx, self.viewport_rect.centery
        for node in nodes:
            sx = center_x + node["x"] * GENEALOGY_SLOT_WIDTH
            sy = center_y + node["generation"] * GENEALOGY_ROW_HEIGHT
            node_rect = pygame.Rect(
                int(sx - GENEALOGY_NODE_RADIUS), int(sy - GENEALOGY_NODE_RADIUS),
                GENEALOGY_NODE_RADIUS * 2, GENEALOGY_NODE_RADIUS * 2)
            if not self.viewport_rect.contains(node_rect):
                return True
        return False

    # ---------- Отрисовка ----------

    def _screen_pos(self, node, center_x, center_y):
        sx = center_x + node["x"] * GENEALOGY_SLOT_WIDTH + self.pan_x
        sy = center_y + node["generation"] * GENEALOGY_ROW_HEIGHT + self.pan_y
        return sx, sy

    def draw(self, screen):
        window_w, window_h = screen.get_width(), screen.get_height()
        overlay = pygame.Surface((window_w, window_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, SETTINGS_OVERLAY_ALPHA))
        screen.blit(overlay, (0, 0))

        width = min(GENEALOGY_PANEL_WIDTH, window_w - 40)
        height = min(GENEALOGY_PANEL_HEIGHT, window_h - 40)
        self.panel_rect = pygame.Rect((window_w - width) // 2, (window_h - height) // 2, width, height)
        panel = self.panel_rect
        pygame.draw.rect(screen, SETTINGS_PANEL_BG, panel)
        pygame.draw.rect(screen, SETTINGS_PANEL_BORDER, panel, 2)

        registry = self._registry()
        root_rec = registry.get(self.root_id) if registry else None
        root_name = (root_rec["name"] if root_rec and root_rec["name"] else self.root_id) if root_rec else "?"
        title_txt = self.title_font.render(INFO_GENEALOGY_TITLE.format(name=root_name), True, WORLD_SCREEN_TEXT)
        screen.blit(title_txt, (panel.x + 16, panel.y + 12))

        viewport_top = panel.y + 14 + title_txt.get_height() + 10
        self.viewport_rect = pygame.Rect(panel.x + 10, viewport_top, panel.width - 20,
                                         panel.bottom - 56 - viewport_top)
        pygame.draw.rect(screen, (20, 20, 20), self.viewport_rect)

        nodes, edges, _bbox = self._build_layout()

        needs_drag_support = self._any_node_offscreen(nodes)
        if not needs_drag_support:
            self.pan_x = 0.0
            self.pan_y = 0.0

        prev_clip = screen.get_clip()
        screen.set_clip(self.viewport_rect)

        center_x, center_y = self.viewport_rect.centerx, self.viewport_rect.centery
        by_id = {}
        for node in nodes:
            by_id.setdefault(node["id"], node)

        for a_id, b_id, kind in edges:
            node_a, node_b = by_id.get(a_id), by_id.get(b_id)
            if node_a is None or node_b is None:
                continue
            pa = self._screen_pos(node_a, center_x, center_y)
            pb = self._screen_pos(node_b, center_x, center_y)
            color = GENEALOGY_PARTNER_LINE_COLOR if kind == "partner" else GENEALOGY_LINE_COLOR
            pygame.draw.line(screen, color, pa, pb, 2)

        self._node_screen_rects = {}
        for node in nodes:
            sx, sy = self._screen_pos(node, center_x, center_y)
            self._draw_node(screen, registry, node, sx, sy)

        screen.set_clip(prev_clip)
        self._draw_offscreen_indicator(screen)

        self.close_btn_rect = pygame.Rect(panel.right - 12 - 130, panel.bottom - 12 - 34, 130, 34)
        mouse_pos = pygame.mouse.get_pos()
        close_color = CLOSE_BUTTON_HOVER if self.close_btn_rect.collidepoint(mouse_pos) else CLOSE_BUTTON_COLOR
        pygame.draw.rect(screen, close_color, self.close_btn_rect, border_radius=4)
        close_txt = self.font.render(INFO_GENEALOGY_CLOSE, True, TEXT_COLOR)
        screen.blit(close_txt, close_txt.get_rect(center=self.close_btn_rect.center))

    def _draw_node(self, screen, registry, node, sx, sy):
        rec = registry.get(node["id"]) if registry else None
        gender = rec["gender"] if rec else None
        is_dead = rec["is_dead"] if rec else False
        name = (rec["name"] if rec and rec["name"] else node["id"]) if rec else INFO_GENEALOGY_UNKNOWN

        color = CREATURE_COLOR_FEMALE if gender == GENDER_FEMALE else CREATURE_COLOR_MALE
        radius = GENEALOGY_NODE_RADIUS

        if node.get("is_root"):
            pygame.draw.circle(screen, GENEALOGY_ROOT_RING_COLOR, (int(sx), int(sy)), radius + 5, 3)

        if is_dead:
            cross_x = sx - radius - 10
            half = 5
            pygame.draw.line(screen, GENEALOGY_CROSS_COLOR,
                             (cross_x - half, sy - half), (cross_x + half, sy + half), 2)
            pygame.draw.line(screen, GENEALOGY_CROSS_COLOR,
                             (cross_x - half, sy + half), (cross_x + half, sy - half), 2)

        pygame.draw.circle(screen, color, (int(sx), int(sy)), radius)
        pygame.draw.circle(screen, (20, 20, 20), (int(sx), int(sy)), radius, 2)

        name_txt = self.name_font.render(name, True, WORLD_SCREEN_TEXT)
        screen.blit(name_txt, name_txt.get_rect(center=(int(sx), int(sy) + radius + 12)))

        self._node_screen_rects[node["id"]] = pygame.Rect(
            int(sx - radius), int(sy - radius), radius * 2, radius * 2)

    def _draw_offscreen_indicator(self, screen):
        if self.root_id not in self._node_screen_rects:
            return
        root_rect = self._node_screen_rects[self.root_id]
        vp = self.viewport_rect
        if vp.colliderect(root_rect):
            return
        cx, cy = vp.centerx, vp.centery
        rx, ry = root_rect.centerx, root_rect.centery
        dx, dy = rx - cx, ry - cy
        dist = math.hypot(dx, dy)
        if dist == 0:
            return
        dx, dy = dx / dist, dy / dist
        edge_x = max(vp.left + 16, min(vp.right - 16, cx + dx * (vp.width // 2 - 20)))
        edge_y = max(vp.top + 16, min(vp.bottom - 16, cy + dy * (vp.height // 2 - 20)))
        tip = (edge_x + dx * 12, edge_y + dy * 12)
        left = (edge_x - dy * 8, edge_y + dx * 8)
        right = (edge_x + dy * 8, edge_y - dx * 8)
        pygame.draw.polygon(screen, GENEALOGY_ROOT_RING_COLOR, [tip, left, right])

    # ---------- Разрешение перекрытий: раздвигаем круги одного поколения, если они соприкасаются ----------

    def _resolve_overlaps(self, nodes_dict):
        min_gap = (GENEALOGY_NODE_RADIUS * 2 + 6) / GENEALOGY_SLOT_WIDTH

        by_generation = {}
        for node in nodes_dict.values():
            by_generation.setdefault(node["generation"], []).append(node)

        for group in by_generation.values():
            if len(group) < 2:
                continue
            group.sort(key=lambda n: n["x"])
            for _ in range(len(group)):
                changed = False
                for i in range(1, len(group)):
                    prev_node, cur_node = group[i - 1], group[i]
                    overlap = min_gap - (cur_node["x"] - prev_node["x"])
                    if overlap > 0:
                        shift = overlap / 2
                        prev_node["x"] -= shift
                        cur_node["x"] += shift
                        changed = True
                if not changed:
                    break

# =========================================================================
# Расширение ObjectPanel (ядровое, core ui.py) строками для объектов
# =========================================================================

def circle_object_panel_extra_lines(obj, creatures):
    lines = []

    if isinstance(obj, (Bush, WaterPuddle)):
        claimed_by = getattr(obj, "claimed_by", None)
        if claimed_by:
            claimant = next((c for c in creatures if c.id == claimed_by), None)
            if claimant is not None:
                name = claimant.name if claimant.name else claimant.id
                lines.append((INFO_INFO_CLAIMED_BY.format(name=name), (255, 210, 60)))

    if hasattr(obj, "fruits") and hasattr(obj, "water"):
        owner_ids = getattr(obj, "owner_ids", None)
        if owner_ids:
            owner_names = []
            for owner_id in owner_ids:
                owner = next((c for c in creatures if c.id == owner_id), None)
                owner_names.append(owner.name if owner and owner.name else owner_id)
            lines.append((INFO_INFO_STORAGE_OWNER.format(name=", ".join(owner_names)), (255, 210, 60)))
        else:
            lines.append((INFO_INFO_STORAGE_OWNER_PUBLIC, (190, 190, 190)))
        lines.append((INFO_INFO_STORAGE_FRUITS.format(count=obj.fruits), (255, 190, 40)))
        lines.append((INFO_INFO_STORAGE_WATER.format(count=obj.water), (100, 170, 230)))

    if hasattr(obj, "build_type"):
        lines.append((
            INFO_INFO_CONSTRUCTION_WOOD.format(deposited=obj.deposited_wood, required=obj.required_wood),
            (200, 170, 120)))
        lines.append((
            INFO_INFO_CONSTRUCTION_STONE.format(deposited=obj.deposited_stone, required=obj.required_stone),
            (200, 200, 200)))
        if obj.is_building:
            percent = int(min(100, obj.build_progress / obj.build_time * 100)) if obj.build_time > 0 else 0
            lines.append((INFO_INFO_CONSTRUCTION_PROGRESS.format(percent=percent), (235, 140, 30)))

    return lines