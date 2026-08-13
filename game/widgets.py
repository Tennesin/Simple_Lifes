import time
import pygame
from settings import *

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
    def __init__(self):
        self.offset = 0
        self.max_scroll = 0

    def update_bounds(self, content_height, visible_height):
        self.max_scroll = max(0, content_height - visible_height)
        self.offset = max(0, min(self.offset, self.max_scroll))

    def scroll_by_wheel(self, wheel_y, speed=DEFAULT_SCROLL_SPEED):
        self.offset -= wheel_y * speed
        self.offset = max(0, min(self.offset, self.max_scroll))

    def draw_scrollbar(self, surface, rect):
        if self.max_scroll <= 0:
            return
        track_rect = pygame.Rect(rect.right - 4, rect.y, 4, rect.height)
        pygame.draw.rect(surface, (30, 30, 30), track_rect)
        content_height = rect.height + self.max_scroll
        thumb_h = max(20, int(rect.height * rect.height / content_height))
        thumb_y = rect.y + int((rect.height - thumb_h) * (self.offset / self.max_scroll))
        pygame.draw.rect(surface, (150, 150, 150), (track_rect.x, thumb_y, 4, thumb_h))