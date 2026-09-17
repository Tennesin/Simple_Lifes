"""Древо Родословной - модальный оверлей: отрисовка + обработка ввода."""

import math
import pygame

from settings import *
from ....ci_settings import *
from ....ci_info import *
from .layout import GenealogyLayoutBuilder

class GenealogyTreeOverlay:

    def __init__(self, game, font):
        self.game = game
        self.font = font
        self.title_font = pygame.font.SysFont(FONT_NAME, FONT_SIZE_TITLE)
        self.name_font = pygame.font.SysFont(FONT_NAME, 13)

        self._layout_builder = GenealogyLayoutBuilder(self.name_font)

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

        self._layout_cache_key = None
        self._layout_cache = ([], [], (0, 0, 0, 0))

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

    # ---------- Раскладка: только кэш, сам расчёт - у GenealogyLayoutBuilder ----------

    def _build_layout(self):
        registry = self._registry()
        if registry is None or self.root_id is None or registry.get(self.root_id) is None:
            self._layout_cache_key = None
            return [], [], (0, 0, 0, 0)

        cache_key = (self.root_id, len(registry.records))
        if cache_key == self._layout_cache_key:
            return self._layout_cache

        result = self._layout_builder.build(registry, self.root_id, self.game.world.creatures)

        self._layout_cache_key = cache_key
        self._layout_cache = result
        return self._layout_cache

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
            cross_x = sx - radius - 12
            cross_top = sy - 9
            cross_bottom = sy + 9
            crossbar_y = sy - 3
            crossbar_half = 5
            pygame.draw.line(screen, GENEALOGY_CROSS_COLOR,
                             (cross_x, cross_top), (cross_x, cross_bottom), 2)
            pygame.draw.line(screen, GENEALOGY_CROSS_COLOR,
                             (cross_x - crossbar_half, crossbar_y), (cross_x + crossbar_half, crossbar_y), 2)

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