"""Правая информационная панель конкретно для существа расы 'Круг'
(полоски здоровья/голода/жажды, психика, семья, взаимоотношения)."""

import time

import pygame

import info
import settings
from game.widgets import Button, draw_favorite_star

from .....all_needed.diet import DIET_DISPLAY_MAP
from .....all_needed.instruction import draw_wrapped_text, truncate_text
from ... import ci_info, ci_settings


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

        self.rebuild_layout(settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT)

    def rebuild_layout(self, window_w, window_h):
        self.window_h = window_h
        self.info_panel_rect = pygame.Rect(
            window_w - settings.INFO_PANEL_WIDTH, settings.UI_HEIGHT,
            settings.INFO_PANEL_WIDTH, window_h - settings.UI_HEIGHT
        )

        id_row_y = self.info_panel_rect.y + 8
        btn_width, btn_height, btn_gap = 85, settings.BUTTON_HEIGHT - 4, 6

        # ---------- Звезда "Избранное" - смещает кнопки Гладить/Ударить левее ----------
        star_size = btn_height
        self.favorite_star_rect = pygame.Rect(
            self.info_panel_rect.right - 10 - star_size, id_row_y, star_size, star_size)

        self.btn_creature_hit = Button(
            pygame.Rect(self.favorite_star_rect.x - btn_gap - btn_width, id_row_y, btn_width, btn_height),
            info.INFO_BTN_HIT)
        self.btn_creature_pet = Button(
            pygame.Rect(self.btn_creature_hit.rect.x - btn_gap - btn_width, id_row_y, btn_width, btn_height),
            info.INFO_BTN_PET)

        self.name_field_rect = pygame.Rect(
            self.info_panel_rect.x + 10, id_row_y + btn_height + 8,
            settings.INFO_PANEL_WIDTH - 20, 26
        )

    # ---------- Текстовые утилиты ----------

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

    def handle_click(self, game, mouse_x, mouse_y):
        """Единая точка входа для ЛКМ по панели существа и её левому окну психики.
        True - клик обработан и дальше по цепочке не идёт."""
        creature = game.selected_creature
        if creature is None:
            return False

        if not creature.is_dead:
            if self.btn_creature_pet.collidepoint(mouse_x, mouse_y):
                creature.receive_pet()
                return True
            if self.btn_creature_hit.collidepoint(mouse_x, mouse_y):
                creature.receive_hit()
                return True
            if self.favorite_star_rect.collidepoint(mouse_x, mouse_y):
                game.toggle_favorite(creature.id, entity=creature)
                return True
            if self._click_stat_bar(creature, mouse_x, mouse_y):
                return True

        if self.info_panel_rect.collidepoint(mouse_x, mouse_y):
            return self.handle_info_panel_click(game, mouse_x, mouse_y)
        if self.is_point_in_extra_panel(mouse_x, mouse_y):
            self._click_stat_bar(creature, mouse_x, mouse_y)
            return True
        return False

    def _click_stat_bar(self, creature, mouse_x, mouse_y):
        for stat_key, rect in self.stat_bar_rects.items():
            if rect.collidepoint(mouse_x, mouse_y):
                direction = -1 if mouse_x < rect.centerx else 1
                creature.player_reactions.adjust_stat(stat_key, direction)
                return True
        return False

    def is_point_in_extra_panel(self, mouse_x, mouse_y):
        return bool(self.show_psyche_section and self.psyche_panel_rect
                    and self.psyche_panel_rect.collidepoint(mouse_x, mouse_y))

    def _draw_stat_bar(self, screen, label, value, max_value, color, x, y, width, stat_key=None):
        label_txt = self.font.render(f"{label}: {value:.1f}/{max_value}", True, settings.TEXT_COLOR)
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
        pygame.draw.rect(screen, settings.INFO_PANEL_COLOR, panel)
        pygame.draw.rect(screen, settings.INFO_PANEL_BORDER, panel, 2)

        id_txt = self.font.render(
            ci_info.INFO_INFO_ID.format(creature_id=creature.id), True, settings.TEXT_COLOR)
        screen.blit(id_txt, (panel.x + 10, panel.y + 12))

        if not creature.is_dead:
            mouse_pos = pygame.mouse.get_pos()
            self.btn_creature_pet.draw(screen, mouse_pos)
            self.btn_creature_hit.draw(screen, mouse_pos)
            draw_favorite_star(screen, self.favorite_star_rect, game.favorite_id == creature.id, mouse_pos)

        field = self.name_field_rect
        field_color = settings.NAME_FIELD_EDIT_COLOR if game.editing_name else settings.NAME_FIELD_COLOR
        pygame.draw.rect(screen, field_color, field)
        pygame.draw.rect(screen, settings.INFO_PANEL_BORDER, field, 1)

        if game.editing_name:
            display_name = game.name_edit_buffer
            if int(time.time() * 2) % 2 == 0:
                display_name += "|"
            text_color = (0, 0, 0)
        else:
            display_name = creature.name if creature.name else ci_info.INFO_INFO_NO_NAME
            text_color = settings.TEXT_COLOR if creature.name else (180, 180, 180)

        name_txt = self.font.render(display_name, True, text_color)
        screen.blit(name_txt, (field.x + 5, field.y + 4))

        y = field.bottom + 16

        kind_txt = self.font.render(
            ci_info.INFO_INFO_KIND.format(kind=creature.get_type_name()), True, settings.TEXT_COLOR)
        screen.blit(kind_txt, (panel.x + 10, y))

        age_minutes = int(creature.age // 60)
        age_txt = self.font.render(
            ci_info.INFO_INFO_AGE_MINUTES.format(age=age_minutes), True, settings.TEXT_COLOR)
        screen.blit(age_txt, (panel.x + 150, y))
        y += 30

        col2_x = panel.x + 150
        col2_width = panel.width - 150 - 10
        row2_bottom = y + 30

        is_female = creature.gender == ci_settings.GENDER_FEMALE
        gender_label = info.INFO_GENDER_FEMALE if is_female else info.INFO_GENDER_MALE
        gender_color = ci_settings.CREATURE_COLOR_FEMALE if is_female else ci_settings.CREATURE_COLOR_MALE
        gender_txt = self.font.render(info.INFO_INFO_GENDER.format(gender=gender_label), True, gender_color)
        screen.blit(gender_txt, (panel.x + 10, y))

        if not creature.is_dead:
            temp_end_y = draw_wrapped_text(
                screen, self.font,
                ci_info.INFO_INFO_TEMPERAMENT.format(
                    temperament=ci_info.gendered_text(creature.temperament, creature.gender)),
                col2_x, y, col2_width, settings.TEXT_COLOR)
            row2_bottom = max(row2_bottom, temp_end_y)

        y = row2_bottom + 2

        diet_label = DIET_DISPLAY_MAP.get(creature.diet, creature.diet)
        diet_txt = self.font.render(info.INFO_INFO_DIET.format(diet=diet_label), True, (150, 210, 130))
        screen.blit(diet_txt, (panel.x + 10, y))
        if not creature.is_dead:
            self._draw_genealogy_button(screen, y - 3)
        y += 28

        if creature.is_dead:
            status_txt = self.font.render(ci_info.INFO_INFO_STATUS_DEAD, True, (210, 90, 90))
            screen.blit(status_txt, (panel.x + 10, y))
            self._draw_genealogy_button(screen, y - 3)
            y += 26

            if creature.death_cause:
                max_text_width = panel.width - 20
                y = draw_wrapped_text(
                    screen, self.font,
                    ci_info.gendered_text(
                        ci_info.DEATH_CAUSE_DISPLAY_MAP.get(creature.death_cause, ""), creature.gender),
                    panel.x + 10, y, max_text_width, settings.TEXT_COLOR)
                y += 8

            temp_txt = self.font.render(
                ci_info.INFO_INFO_TEMPERAMENT.format(
                    temperament=ci_info.gendered_text(creature.temperament, creature.gender)),
                True, settings.TEXT_COLOR)
            screen.blit(temp_txt, (panel.x + 10, y))
            y += 26

            timer_txt = self.font.render(
                ci_info.INFO_INFO_DEATH_TIMER.format(time=creature.death_timer), True, settings.TEXT_COLOR)
            screen.blit(timer_txt, (panel.x + 10, y))
            y += 30
            self._draw_relationships_section(screen, creature, panel.x + 10, y, panel.width - 20)
            self.psyche_panel_rect = None
            return

        y = self._draw_family_info(screen, creature, panel.x + 10, y, panel.width - 20)
        y = self._draw_psyche_toggle(screen, panel.x + 10, y, panel.width - 20)

        self._draw_stat_bar(screen, ci_info.INFO_INFO_HP, creature.hp, ci_settings.HP_MAX, (220, 60, 60),
                            panel.x + 10, y, panel.width - 20, stat_key="hp")
        y += 40
        self._draw_stat_bar(screen, ci_info.INFO_INFO_HUNGER, creature.hunger, ci_settings.HUNGER_MAX,
                            (200, 150, 40), panel.x + 10, y, panel.width - 20, stat_key="hunger")
        y += 40
        self._draw_stat_bar(screen, ci_info.INFO_INFO_THIRST, creature.thirst, ci_settings.THIRST_MAX,
                            (60, 140, 220), panel.x + 10, y, panel.width - 20, stat_key="thirst")
        y += 40
        self._draw_stat_bar(screen, ci_info.INFO_INFO_ENERGY, creature.energy, ci_settings.ENERGY_MAX,
                            (90, 200, 200), panel.x + 10, y, panel.width - 20, stat_key="energy")
        y += 40

        state_color_map = {
            ci_settings.STATE_CALM: (120, 220, 120),
            ci_settings.STATE_SEEKING: (230, 200, 60),
            ci_settings.STATE_PANIC: (230, 70, 70),
            ci_settings.STATE_SLEEP: (120, 160, 220)
        }
        state_txt = self.font.render(
            ci_info.INFO_INFO_STATE.format(state=ci_info.gendered_text(creature.state, creature.gender)),
            True, state_color_map.get(creature.state, settings.TEXT_COLOR))
        screen.blit(state_txt, (panel.x + 10, y))
        y += 24

        if creature.gender == ci_settings.GENDER_FEMALE and creature.family.is_pregnant:
            pregnant_txt = self.font.render(ci_info.INFO_INFO_PREGNANT, True, (255, 170, 210))
            screen.blit(pregnant_txt, (panel.x + 10, y))
            y += 24

        if creature.puberty.active:
            puberty_txt = self.font.render(
                ci_info.INFO_INFO_PUBERTY_ACTIVE, True, ci_settings.PUBERTY_RING_COLOR)
            screen.blit(puberty_txt, (panel.x + 10, y))
            y += 24

        max_text_width = panel.width - 20
        y = draw_wrapped_text(
            screen, self.font,
            ci_info.INFO_INFO_GOAL.format(goal=ci_info.gendered_text(creature.goal_text, creature.gender)),
            panel.x + 10, y, max_text_width, settings.TEXT_COLOR)
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
        return ci_info.INFO_INFO_UNKNOWN_PARENT

    def _draw_parent_line(self, screen, creature, label_template, index, x, y):
        if creature.family.parent_ids is None:
            name = ci_info.INFO_INFO_HEAVEN
        else:
            parent_id = creature.family.parent_ids[index] if index < len(creature.family.parent_ids) else None
            name = (ci_info.INFO_INFO_UNKNOWN_PARENT if parent_id is None
                    else self._resolve_parent_name(parent_id))
        txt = self.font.render(label_template.format(name=name), True, settings.TEXT_COLOR)
        screen.blit(txt, (x, y))
        return y + 24

    def _draw_family_info(self, screen, creature, x, y, max_width):
        game = self.game

        y = self._draw_parent_line(screen, creature, ci_info.INFO_INFO_MOTHER, 0, x, y)
        y = self._draw_parent_line(screen, creature, ci_info.INFO_INFO_FATHER, 1, x, y)

        partner = None
        if creature.family.partner_id:
            partner = next((c for c in game.world.creatures
                            if c.id == creature.family.partner_id and not c.is_dead), None)
        partner_label = (partner.name if partner and partner.name
                         else (partner.id if partner else ci_info.INFO_INFO_PARTNER_NONE))
        partner_txt = self.font.render(
            ci_info.INFO_INFO_PARTNER.format(name=partner_label), True, settings.TEXT_COLOR)
        screen.blit(partner_txt, (x, y))
        y += 24

        sons = [c for c in game.world.creatures
                if c.family.parent_ids and creature.id in c.family.parent_ids and not c.is_dead
                and c.gender == ci_settings.GENDER_MALE]
        daughters = [c for c in game.world.creatures
                     if c.family.parent_ids and creature.id in c.family.parent_ids and not c.is_dead
                     and c.gender == ci_settings.GENDER_FEMALE]

        if not sons and not daughters:
            children_txt = self.font.render(
                ci_info.INFO_INFO_CHILDREN.format(names=ci_info.INFO_INFO_CHILDREN_NONE),
                True, settings.TEXT_COLOR)
            screen.blit(children_txt, (x, y))
            y += 24
        else:
            sons_names = (", ".join(c.name if c.name else c.id for c in sons)
                          if sons else ci_info.INFO_INFO_CHILDREN_NONE)
            daughters_names = (", ".join(c.name if c.name else c.id for c in daughters)
                               if daughters else ci_info.INFO_INFO_CHILDREN_NONE)
            y = draw_wrapped_text(screen, self.font, ci_info.INFO_INFO_SONS.format(names=sons_names),
                                  x, y, max_width, settings.TEXT_COLOR)
            y = draw_wrapped_text(screen, self.font, ci_info.INFO_INFO_DAUGHTERS.format(names=daughters_names),
                                  x, y, max_width, settings.TEXT_COLOR)

        y += 10
        return y

    # ---------- Отношение к игроку ----------

    def _relationship_label(self, creature):
        gender = creature.gender
        if creature.player_fear_timer > 0:
            return ci_info.gendered_text(ci_info.INFO_RELATIONSHIP_FEAR, gender), (230, 70, 70)
        if creature.calm_timer > 0:
            return ci_info.gendered_text(ci_info.INFO_RELATIONSHIP_CALMED, gender), (255, 210, 120)

        r = creature.player_relationship
        if r <= -70:
            return ci_info.gendered_text(ci_info.INFO_RELATIONSHIP_DESPISE, gender), (210, 40, 40)
        elif r <= -30:
            return ci_info.gendered_text(ci_info.INFO_RELATIONSHIP_AFRAID, gender), (215, 100, 60)
        elif r <= -10:
            return ci_info.gendered_text(ci_info.INFO_RELATIONSHIP_WARY, gender), (210, 160, 70)
        elif r < 10:
            return ci_info.gendered_text(ci_info.INFO_RELATIONSHIP_NEUTRAL, gender), (190, 190, 190)
        elif r < 30:
            return ci_info.gendered_text(ci_info.INFO_RELATIONSHIP_FRIENDLY, gender), (150, 200, 120)
        elif r < 70:
            return ci_info.gendered_text(ci_info.INFO_RELATIONSHIP_TRUST, gender), (100, 210, 130)
        else:
            return ci_info.gendered_text(ci_info.INFO_RELATIONSHIP_DEVOTED, gender), (80, 230, 140)

    def _draw_relationship_bar(self, screen, creature, x, y, width):
        label, color = self._relationship_label(creature)
        label_txt = self.font.render(ci_info.INFO_INFO_RELATIONSHIP.format(label=label), True, color)
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
        pygame.draw.polygon(screen, settings.TEXT_COLOR, [
            (marker_x - tri_half, tri_top_y),
            (marker_x + tri_half, tri_top_y),
            (marker_x, tri_bottom_y),
        ])

        value_txt = self.font.render(f"{ratio:+.2f}", True, settings.TEXT_COLOR)
        screen.blit(value_txt, (x + width - value_txt.get_width(), bar_y + bar_height + 4))

        return bar_y + bar_height + 26

    # ---------- Секция "Взаимоотношения" ----------

    def _draw_relationships_section(self, screen, creature, x, y, width):
        header_rect = pygame.Rect(x, y, width, 26)

        mouse_pos = pygame.mouse.get_pos()
        header_color = settings.MENU_HOVER if header_rect.collidepoint(mouse_pos) else settings.BUTTON_COLOR
        pygame.draw.rect(screen, header_color, header_rect)
        arrow = "<" if self.show_relationships_section else "v"
        txt = self.font.render(f"{arrow} {ci_info.INFO_RELATIONSHIPS_TITLE}", True, settings.TEXT_COLOR)
        screen.blit(txt, (header_rect.x + 6, header_rect.y + 3))
        self.relationships_header_rect = header_rect
        y = header_rect.bottom + 8

        if not self.show_relationships_section:
            self.relationships_list_rect = None
            self.relationships_max_scroll = 0
            self.relationships_scrollbar_rect = None
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
                    other.id == creature.family.partner_id or
                    (other.family.parent_ids and creature.id in other.family.parent_ids) or
                    (creature.family.parent_ids and other.id in creature.family.parent_ids)
            )
            entry = (other, value, is_close)
            (females if other.gender == ci_settings.GENDER_FEMALE else males).append(entry)

        males.sort(key=lambda e: (e[0].name or "").lower())
        females.sort(key=lambda e: (e[0].name or "").lower())

        if not males and not females:
            empty_txt = self.font.render(ci_info.INFO_RELATIONSHIPS_EMPTY, True, (180, 180, 180))
            screen.blit(empty_txt, (x, y))
            self.relationships_list_rect = None
            self.relationships_max_scroll = 0
            self.relationships_scrollbar_rect = None
            return y + 24

        male_header = self.font.render(ci_info.INFO_RELATIONSHIPS_MALES, True, (170, 190, 230))
        screen.blit(male_header, (x, y))
        female_header = self.font.render(ci_info.INFO_RELATIONSHIPS_FEMALES, True, (230, 170, 210))
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
                color = (255, 210, 60) if is_close else settings.TEXT_COLOR
                name = other.name if other.name else other.id
                value_txt = self.font.render(f"{value:+.0f}", True, color)
                name_max_width = col_width - value_txt.get_width() - 8
                name_txt = self.font.render(truncate_text(self.font, name, name_max_width), True, color)
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
            self.relationships_scrollbar_rect = None

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

        pygame.draw.rect(screen, settings.INFO_PANEL_COLOR, rect)
        pygame.draw.rect(screen, settings.INFO_PANEL_BORDER, rect, 2)

        inner_x = rect.x + 10
        inner_y = rect.y + 10
        inner_width = rect.width - 20

        title_txt = self.font.render(
            f"{ci_info.INFO_PSYCHE_TITLE}: {creature.name if creature.name else creature.id}",
            True, settings.TEXT_COLOR)
        screen.blit(title_txt, (inner_x, inner_y))
        inner_y += title_h

        label, _color = self._relationship_label(creature)
        inner_y = self._draw_axis_bar(
            screen, f"{ci_info.INFO_PSYCHE_PLAYER_REL}: {label}", creature.player_relationship,
            ci_info.INFO_RELATIONSHIP_DESPISE, ci_info.INFO_RELATIONSHIP_DEVOTED,
            inner_x, inner_y, inner_width)

        self._draw_stat_bar(screen, ci_info.INFO_PSYCHE_CONSCIOUSNESS, creature.consciousness,
                            ci_settings.SANITY_MAX, (160, 100, 220),
                            inner_x, inner_y, inner_width, stat_key="consciousness")
        inner_y += stat_bar_h

        psyche = creature.psyche
        inner_y = self._draw_axis_bar(screen, ci_info.INFO_PSYCHE_JOY_TITLE, psyche.joy,
                                      ci_info.INFO_PSYCHE_JOY_LEFT, ci_info.INFO_PSYCHE_JOY_RIGHT,
                                      inner_x, inner_y, inner_width)
        inner_y = self._draw_axis_bar(screen, ci_info.INFO_PSYCHE_SATISFACTION_TITLE, psyche.satisfaction,
                                      ci_info.INFO_PSYCHE_SATISFACTION_LEFT,
                                      ci_info.INFO_PSYCHE_SATISFACTION_RIGHT,
                                      inner_x, inner_y, inner_width)
        inner_y = self._draw_axis_bar(screen, ci_info.INFO_PSYCHE_CALM_TITLE, psyche.calmness,
                                      ci_info.INFO_PSYCHE_CALM_LEFT, ci_info.INFO_PSYCHE_CALM_RIGHT,
                                      inner_x, inner_y, inner_width)
        inner_y = self._draw_axis_bar(screen, ci_info.INFO_PSYCHE_CONFIDENCE_TITLE, psyche.confidence,
                                      ci_info.INFO_PSYCHE_CONFIDENCE_LEFT,
                                      ci_info.INFO_PSYCHE_CONFIDENCE_RIGHT,
                                      inner_x, inner_y, inner_width)
        inner_y = self._draw_axis_bar(screen, ci_info.INFO_PSYCHE_ATTACHMENT_TITLE, psyche.attachment,
                                      ci_info.INFO_PSYCHE_ATTACHMENT_LEFT,
                                      ci_info.INFO_PSYCHE_ATTACHMENT_RIGHT,
                                      inner_x, inner_y, inner_width)

    def _draw_axis_bar(self, screen, title, value, left_label, right_label, x, y, width):
        if title:
            title_txt = self.font.render(title, True, settings.TEXT_COLOR)
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
        header_color = settings.MENU_HOVER if header_rect.collidepoint(mouse_pos) else settings.BUTTON_COLOR
        pygame.draw.rect(screen, header_color, header_rect)
        arrow = "<" if self.show_psyche_section else "v"
        txt = self.font.render(f"{arrow} {ci_info.INFO_PSYCHE_TOGGLE}", True, settings.TEXT_COLOR)
        screen.blit(txt, (header_rect.x + 6, header_rect.y + 3))
        self.psyche_header_rect = header_rect
        return header_rect.bottom + 10

    def _draw_genealogy_button(self, screen, y):
        panel = self.info_panel_rect
        btn_width, btn_height = 85, settings.BUTTON_HEIGHT - 4
        rect = pygame.Rect(panel.right - 10 - btn_width, y, btn_width, btn_height)
        mouse_pos = pygame.mouse.get_pos()
        color = settings.MENU_HOVER if rect.collidepoint(mouse_pos) else settings.BUTTON_COLOR
        pygame.draw.rect(screen, color, rect, border_radius=4)
        txt = self.font.render(ci_info.INFO_BTN_GENEALOGY, True, settings.TEXT_COLOR)
        screen.blit(txt, txt.get_rect(center=rect.center))
        self.genealogy_btn_rect = rect