import time
import math
import pygame
from settings import *
from creatures.all_needed.instruction import (
    InstructionHeader, InstructionParagraph, InstructionBullet, InstructionCallout,
    wrap_instruction_text, INSTRUCTION_COLOR_DEFAULT,
)

class TextInputBox:
    def __init__(self, rect, value="", max_len=24, digits_only=False, placeholder=""):
        self.rect = pygame.Rect(rect)
        self.text = value
        self.max_len = max_len
        self.digits_only = digits_only
        self.placeholder = placeholder
        self.focused = False
        self._cursor_visible = True
        self._last_blink = time.time()

    def try_focus(self, pos):
        hit = self.rect.collidepoint(pos)
        self.focused = hit
        return hit

    def handle_keydown(self, event):
        if not self.focused:
            return False
        if event.key == pygame.K_BACKSPACE:
            self.text = self.text[:-1]
            return True
        if event.unicode and event.unicode.isprintable() and len(self.text) < self.max_len:
            ch = event.unicode
            if self.digits_only and not ch.isdigit():
                return False
            self.text += ch
            return True
        return False

    def draw(self, surface, font):
        now = time.time()
        if now - self._last_blink >= 0.5:
            self._last_blink = now
            self._cursor_visible = not self._cursor_visible

        bg = WORLD_SCREEN_INPUT_BG_FOCUS if self.focused else WORLD_SCREEN_INPUT_BG
        border = WORLD_SCREEN_INPUT_BORDER_FOCUS if self.focused else WORLD_SCREEN_INPUT_BORDER
        pygame.draw.rect(surface, bg, self.rect, border_radius=4)
        pygame.draw.rect(surface, border, self.rect, 1, border_radius=4)

        text_x = self.rect.x + 8
        cy = self.rect.centery

        if self.text:
            txt_surf = font.render(self.text, True, WORLD_SCREEN_TEXT)
            surface.blit(txt_surf, txt_surf.get_rect(midleft=(text_x, cy)))
            cursor_x = text_x + txt_surf.get_width() + 2
        else:
            if self.placeholder:
                ph_surf = font.render(self.placeholder, True, WORLD_SCREEN_HINT_COLOR)
                surface.blit(ph_surf, ph_surf.get_rect(midleft=(text_x, cy)))
            cursor_x = text_x

        if self.focused and self._cursor_visible:
            pygame.draw.line(surface, WORLD_SCREEN_TEXT,
                             (cursor_x, self.rect.y + 6), (cursor_x, self.rect.bottom - 6), 1)

class Button:
    _font_cache = {}

    def __init__(self, rect, label, enabled=True):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.enabled = enabled

    @classmethod
    def _get_font(cls, size):
        font = cls._font_cache.get(size)
        if font is None:
            font = pygame.font.SysFont(FONT_NAME, size)
            cls._font_cache[size] = font
        return font

    def draw(self, surface, mouse_pos, font_size=None, colors=None):
        font_size = font_size or FONT_SIZE_BUTTON
        colors = colors or {
            "normal": BUTTON_COLOR, "hover": BUTTON_HOVER,
            "disabled": BUTTON_DISABLED, "text": TEXT_COLOR,
        }
        if not self.enabled:
            bg = colors["disabled"]
        elif self.rect.collidepoint(mouse_pos):
            bg = colors["hover"]
        else:
            bg = colors["normal"]

        pygame.draw.rect(surface, bg, self.rect, border_radius=4)
        txt_surf = self._get_font(font_size).render(self.label, True, colors["text"])
        surface.blit(txt_surf, txt_surf.get_rect(center=self.rect.center))

    def collidepoint(self, *args):
        return self.rect.collidepoint(*args)

class ScrollArea:
    THUMB_WIDTH = 4
    HIT_PADDING = 6
    SMOOTH_SPEED = 14.0        # чем больше, тем быстрее догоняет цель
    SMOOTH_SNAP_DISTANCE = 0.5 # ближе этого - просто прилипаем, хватит дрожать

    def __init__(self, smooth=False):
        self.offset = 0.0          # то, что реально рисуется
        self.target_offset = 0.0   # то, куда стремимся
        self.max_scroll = 0
        self.smooth = smooth
        self.track_rect = None
        self.thumb_rect = None
        self._dragging = False

    # ---------- Тик сглаживания: звать раз в кадр перед отрисовкой ----------

    def update(self, dt):
        if not self.smooth or self._dragging:
            self.offset = self.target_offset
            return
        delta = self.target_offset - self.offset
        if abs(delta) <= self.SMOOTH_SNAP_DISTANCE:
            self.offset = self.target_offset
            return
        # ---------- Кадронезависимое экспоненциальное сближение ----------
        factor = 1.0 - math.exp(-self.SMOOTH_SPEED * dt)
        self.offset += delta * factor

    def _clamp_target(self):
        self.target_offset = max(0.0, min(self.target_offset, self.max_scroll))

    def update_bounds(self, content_height, visible_height):
        self.max_scroll = max(0, content_height - visible_height)
        self._clamp_target()
        self.offset = max(0.0, min(self.offset, self.max_scroll))

    def scroll_by_wheel(self, wheel_y, speed=DEFAULT_SCROLL_SPEED):
        self.target_offset -= wheel_y * speed
        self._clamp_target()
        if not self.smooth:
            self.offset = self.target_offset

    def scroll_by_step(self, direction, step=DEFAULT_SCROLL_SPEED):
        self.target_offset += direction * step
        self._clamp_target()
        if not self.smooth:
            self.offset = self.target_offset

    def drag_to(self, mouse_y):
        if self.track_rect is None or self.max_scroll <= 0:
            return
        thumb_h = self.thumb_rect.height if self.thumb_rect is not None else 20
        usable = max(1, self.track_rect.height - thumb_h)
        ratio = (mouse_y - self.track_rect.y - thumb_h / 2) / usable
        ratio = max(0.0, min(1.0, ratio))
        self.target_offset = ratio * self.max_scroll
        self.offset = self.target_offset   # перетаскивание должно быть 1:1, без запаздывания

    def draw_scrollbar(self, surface, rect):
        if self.max_scroll <= 0:
            self.track_rect = None
            self.thumb_rect = None
            return
        track_rect = pygame.Rect(rect.right - self.THUMB_WIDTH, rect.y, self.THUMB_WIDTH, rect.height)
        pygame.draw.rect(surface, (30, 30, 30), track_rect)
        content_height = rect.height + self.max_scroll
        thumb_h = max(20, int(rect.height * rect.height / content_height))
        thumb_y = rect.y + int((rect.height - thumb_h) * (self.offset / self.max_scroll))
        thumb_rect = pygame.Rect(track_rect.x, thumb_y, self.THUMB_WIDTH, thumb_h)
        pygame.draw.rect(surface, (150, 150, 150), thumb_rect)

        self.track_rect = track_rect
        self.thumb_rect = thumb_rect

    # ---------- Перетаскивание бегунка мышью ----------

    def hit_test_scrollbar(self, mouse_pos):
        if self.track_rect is None:
            return False
        return self.track_rect.inflate(self.HIT_PADDING * 2, 0).collidepoint(mouse_pos)

    def begin_drag(self, mouse_y):
        if self.track_rect is None or self.max_scroll <= 0:
            return False
        self._dragging = True
        self.drag_to(mouse_y)
        return True

    def is_dragging(self):
        return self._dragging

    def end_drag(self):
        self._dragging = False

    def drag_to(self, mouse_y):
        if self.track_rect is None or self.max_scroll <= 0:
            return
        thumb_h = self.thumb_rect.height if self.thumb_rect is not None else 20
        usable = max(1, self.track_rect.height - thumb_h)
        ratio = (mouse_y - self.track_rect.y - thumb_h / 2) / usable
        ratio = max(0.0, min(1.0, ratio))
        self.offset = int(round(ratio * self.max_scroll))

class Slider:
    def __init__(self, rect, value=0.5, min_value=0.0, max_value=1.0, step=0.05):
        self.rect = pygame.Rect(rect)
        self.min_value = min_value
        self.max_value = max_value
        self.step = step
        self.value = max(min_value, min(max_value, value))
        self.dragging = False

    def set_from_mouse(self, mouse_x):
        if self.rect.width <= 0:
            return
        ratio = (mouse_x - self.rect.x) / self.rect.width
        ratio = max(0.0, min(1.0, ratio))
        raw_value = self.min_value + ratio * (self.max_value - self.min_value)
        steps = round((raw_value - self.min_value) / self.step)
        value = self.min_value + steps * self.step
        self.value = round(max(self.min_value, min(self.max_value, value)), 2)

    def draw(self, surface, fill_color, bg_color=(25, 25, 25), border_color=(15, 15, 15)):
        pygame.draw.rect(surface, bg_color, self.rect, border_radius=4)
        span = self.max_value - self.min_value
        ratio = (self.value - self.min_value) / span if span > 0 else 0.0
        fill_w = max(4, int(self.rect.width * ratio))
        fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_w, self.rect.height)
        pygame.draw.rect(surface, fill_color, fill_rect, border_radius=4)
        pygame.draw.rect(surface, border_color, self.rect, 1, border_radius=4)

        handle_rect = pygame.Rect(0, 0, 4, self.rect.height + 6)
        handle_rect.center = (self.rect.x + fill_w, self.rect.centery)
        pygame.draw.rect(surface, (240, 240, 240), handle_rect, border_radius=2)

# =====================================================================
# Кнопка "Избранное" (звезда)
# =====================================================================

def star_points(cx, cy, outer_r, inner_r, points=5, rotation=-math.pi / 2):
    result = []
    angle_step = math.pi / points
    angle = rotation
    for i in range(points * 2):
        r = outer_r if i % 2 == 0 else inner_r
        result.append((cx + math.cos(angle) * r, cy + math.sin(angle) * r))
        angle += angle_step
    return result

def draw_favorite_star(screen, rect, is_favorite, mouse_pos):
    cx, cy = rect.center
    outer_r = min(rect.width, rect.height) / 2
    inner_r = outer_r * 0.45
    points = star_points(cx, cy, outer_r, inner_r)
    hovered = rect.collidepoint(mouse_pos)

    if is_favorite:
        fill_color = FAVORITE_STAR_COLOR_HOVER if hovered else FAVORITE_STAR_COLOR
        pygame.draw.polygon(screen, fill_color, points)
        pygame.draw.polygon(screen, FAVORITE_STAR_BORDER, points, 2)
    else:
        border_color = FAVORITE_STAR_HOLLOW_HOVER if hovered else FAVORITE_STAR_HOLLOW_BORDER
        pygame.draw.polygon(screen, border_color, points, 2)

    return hovered

# =========================================================================
# Отрисовка блоков контента Инструкции (InstructionHeader/Paragraph/
# Bullet/Callout) - единая точка для любой панели, показывающей такой
# текст (флэт-категории "Основы"/"Полезное" и содержимое карточек
# аккордеона в "Расы"/"Животные").
# =========================================================================

_INSTRUCTION_LINE_HEIGHT = 22
_INSTRUCTION_HEADER_EXTRA = 8
_INSTRUCTION_BLOCK_GAP = 6

_BULLET_INDENT = 4
_BULLET_ICON_SIZE = 20
_BULLET_TEXT_GAP = 10
_BULLET_CONTENT_OFFSET = _BULLET_INDENT + _BULLET_ICON_SIZE + _BULLET_TEXT_GAP

_CALLOUT_PADDING = 8

def measure_instruction_blocks(font, blocks, max_width,
                                line_height=_INSTRUCTION_LINE_HEIGHT):
    """Суммарная высота списка блоков при данной ширине - используется,
    чтобы заранее посчитать content_height для ScrollArea/AccordionList,
    не рисуя ничего на экран."""
    total = 0
    for block in blocks:
        if isinstance(block, InstructionHeader):
            total += line_height + _INSTRUCTION_HEADER_EXTRA

        elif isinstance(block, InstructionParagraph):
            lines = wrap_instruction_text(font, block.text, max_width)
            total += len(lines) * line_height

        elif isinstance(block, InstructionBullet):
            bullet_width = max(10, max_width - _BULLET_CONTENT_OFFSET)
            lines = wrap_instruction_text(font, block.text, bullet_width)
            row_height = len(lines) * line_height
            if block.icon:
                row_height = max(row_height, _BULLET_ICON_SIZE)
            total += row_height

        elif isinstance(block, InstructionCallout):
            inner_width = max(10, max_width - _CALLOUT_PADDING * 2)
            lines = wrap_instruction_text(font, block.text, inner_width)
            total += len(lines) * line_height + _CALLOUT_PADDING * 2

        total += _INSTRUCTION_BLOCK_GAP
    return total

def draw_instruction_blocks(screen, font, blocks, x, y, max_width,
                             icon_provider=None, header_font=None,
                             line_height=_INSTRUCTION_LINE_HEIGHT):
    """Рисует список блоков начиная с (x, y)."""
    header_font = header_font or font

    for block in blocks:
        if isinstance(block, InstructionHeader):
            txt = header_font.render(block.text, True, TEXT_COLOR)
            screen.blit(txt, (x, y))
            y += line_height + _INSTRUCTION_HEADER_EXTRA

        elif isinstance(block, InstructionParagraph):
            color = block.color or INSTRUCTION_COLOR_DEFAULT
            for line in wrap_instruction_text(font, block.text, max_width):
                txt = font.render(line, True, color)
                screen.blit(txt, (x, y))
                y += line_height

        elif isinstance(block, InstructionBullet):
            color = block.color or INSTRUCTION_COLOR_DEFAULT
            marker_center = (x + _BULLET_INDENT + _BULLET_ICON_SIZE // 2, y + line_height // 2)
            icon_surf = icon_provider(block.icon) if (icon_provider and block.icon) else None
            if icon_surf is not None:
                screen.blit(icon_surf, icon_surf.get_rect(center=marker_center))
            else:
                marker_txt = font.render("•", True, color)
                screen.blit(marker_txt, marker_txt.get_rect(center=marker_center))

            text_x = x + _BULLET_CONTENT_OFFSET
            bullet_width = max(10, max_width - _BULLET_CONTENT_OFFSET)
            lines = wrap_instruction_text(font, block.text, bullet_width)
            line_y = y
            for line in lines:
                txt = font.render(line, True, color)
                screen.blit(txt, (text_x, line_y))
                line_y += line_height

            row_height = max(len(lines) * line_height, _BULLET_ICON_SIZE if block.icon else 0)
            y += row_height

        elif isinstance(block, InstructionCallout):
            inner_width = max(10, max_width - _CALLOUT_PADDING * 2)
            lines = wrap_instruction_text(font, block.text, inner_width)
            box_height = len(lines) * line_height + _CALLOUT_PADDING * 2
            box_rect = pygame.Rect(x, y, max_width, box_height)

            box_surf = pygame.Surface(box_rect.size, pygame.SRCALPHA)
            box_surf.fill((*block.color, 35))
            screen.blit(box_surf, box_rect.topleft)
            pygame.draw.rect(screen, block.color, box_rect, 1, border_radius=4)

            line_y = y + _CALLOUT_PADDING
            for line in lines:
                txt = font.render(line, True, block.color)
                screen.blit(txt, (x + _CALLOUT_PADDING, line_y))
                line_y += line_height
            y = box_rect.bottom

        y += _INSTRUCTION_BLOCK_GAP

    return y

class AccordionList:

    ROW_HEIGHT = 40
    ROW_GAP = 6
    ROW_COLOR = (55, 55, 55)
    ROW_HOVER_COLOR = (75, 75, 75)
    ROW_BORDER_COLOR = (30, 30, 30)
    ICON_MARGIN = 10
    ARROW_COLOR = (200, 200, 200)
    CONTENT_INDENT = 14

    def __init__(self):
        self.expanded_keys = set()
        self._row_rects = {}          # entry.key -> pygame.Rect (видимая часть строки-заголовка)
        self._content_heights = {}    # entry.key -> int (кэш высоты развёрнутого содержимого)

    def reset(self):
        """Сбрасывает раскрытые карточки - вызывать при смене категории/вкладки."""
        self.expanded_keys.clear()
        self._content_heights.clear()
        self._row_rects = {}

    def is_expanded(self, key):
        return key in self.expanded_keys

    def toggle(self, key):
        if key in self.expanded_keys:
            self.expanded_keys.discard(key)
        else:
            self.expanded_keys.add(key)

    def invalidate_content_heights(self):
        """Сбросить закэшированные высоты."""
        self._content_heights.clear()

    def handle_click(self, mouse_pos):
        """True, если клик попал по строке-заголовку (обработан)."""
        for key, rect in self._row_rects.items():
            if rect.collidepoint(mouse_pos):
                self.toggle(key)
                return True
        return False

    def ensure_content_heights(self, entries, content_measure_fn):
        """content_measure_fn(entry) -> высота развёрнутого содержимого в px."""
        for entry in entries:
            if entry.key in self.expanded_keys and entry.key not in self._content_heights:
                self._content_heights[entry.key] = content_measure_fn(entry)

    def total_height(self, entries):
        total = 0
        for entry in entries:
            total += self.ROW_HEIGHT + self.ROW_GAP
            if entry.key in self.expanded_keys:
                total += self._content_heights.get(entry.key, 0) + self.ROW_GAP
        return total

    def draw(self, screen, font, rect, scroll_offset, entries, icon_provider, content_draw_fn):
        """rect - видимая область списка (без учёта скролла)."""
        self._row_rects = {}
        mouse_pos = pygame.mouse.get_pos()
        y = rect.y - scroll_offset

        prev_clip = screen.get_clip()
        screen.set_clip(rect)

        for entry in entries:
            row_rect = pygame.Rect(rect.x, y, rect.width, self.ROW_HEIGHT)
            visible = row_rect.bottom >= rect.y and row_rect.y <= rect.bottom

            if visible:
                self._draw_row(screen, font, row_rect, entry, icon_provider, mouse_pos)
                clipped = row_rect.clip(rect)
                if clipped.width > 0 and clipped.height > 0:
                    self._row_rects[entry.key] = clipped

            y += self.ROW_HEIGHT + self.ROW_GAP

            if entry.key in self.expanded_keys:
                content_height = self._content_heights.get(entry.key, 0)
                content_x = rect.x + self.CONTENT_INDENT
                content_width = rect.width - self.CONTENT_INDENT * 2
                content_bottom = y + content_height
                if content_bottom >= rect.y and y <= rect.bottom:
                    content_draw_fn(screen, entry, content_x, y, content_width)
                y += content_height + self.ROW_GAP

        screen.set_clip(prev_clip)

    def _draw_row(self, screen, font, row_rect, entry, icon_provider, mouse_pos):
        hovered = row_rect.collidepoint(mouse_pos)
        color = self.ROW_HOVER_COLOR if hovered else self.ROW_COLOR
        pygame.draw.rect(screen, color, row_rect, border_radius=4)
        pygame.draw.rect(screen, self.ROW_BORDER_COLOR, row_rect, 1, border_radius=4)

        icon_surf = icon_provider(entry) if icon_provider is not None else None
        text_x = row_rect.x + self.ICON_MARGIN
        if icon_surf is not None:
            icon_rect = icon_surf.get_rect(midleft=(row_rect.x + self.ICON_MARGIN, row_rect.centery))
            screen.blit(icon_surf, icon_rect)
            text_x = icon_rect.right + self.ICON_MARGIN

        title_txt = font.render(entry.title, True, TEXT_COLOR)
        screen.blit(title_txt, title_txt.get_rect(midleft=(text_x, row_rect.centery)))

        arrow = "v" if entry.key in self.expanded_keys else ">"
        arrow_txt = font.render(arrow, True, self.ARROW_COLOR)
        screen.blit(arrow_txt, arrow_txt.get_rect(midright=(row_rect.right - self.ICON_MARGIN, row_rect.centery)))