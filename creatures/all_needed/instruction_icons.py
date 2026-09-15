"""Общие утилиты отрисовки маленьких иконок для Инструкции."""

import pygame

class IconCache:
    """Иконки статичны на всё время работы приложения."""

    def __init__(self):
        self._cache = {}

    def get(self, key, factory):
        surf = self._cache.get(key)
        if surf is None:
            surf = factory()
            self._cache[key] = surf
        return surf

    def clear(self):
        self._cache.clear()


def render_scaled_icon(draw_fn, source_size, icon_size):
    """draw_fn(surface, center_pos) - рисует объект в натуральную величину
    на временной поверхности source_size, после чего результат вписывается
    в квадрат icon_size x icon_size с сохранением пропорций."""
    src_w, src_h = source_size
    src_w, src_h = max(1, int(src_w)), max(1, int(src_h))

    surf = pygame.Surface((src_w, src_h), pygame.SRCALPHA)
    draw_fn(surf, (src_w // 2, src_h // 2))

    scale = min(icon_size / src_w, icon_size / src_h)
    new_w = max(1, int(src_w * scale))
    new_h = max(1, int(src_h * scale))
    scaled = pygame.transform.smoothscale(surf, (new_w, new_h))

    out = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
    out.blit(scaled, scaled.get_rect(center=(icon_size // 2, icon_size // 2)))
    return out