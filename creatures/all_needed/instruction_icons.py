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

def make_singleton_icon_factory(cls, size_attrs, icon_cache=None):
    """Общая фабрика 'манекен + реальный draw() существа, вписанный в
    квадрат' для иконок Инструкции. size_attrs = (width, height, leg_height|None)."""
    cache = icon_cache if icon_cache is not None else IconCache()
    _sample = []

    def _get_sample():
        if not _sample:
            _sample.append(cls("icon", 0, 0))
        return _sample[0]

    width, height, leg_height = size_attrs

    def factory(variant_key=None, size=20):
        def _build():
            extra = leg_height if leg_height is not None else 0
            source = (width + 12, height + extra + 12)
            return render_scaled_icon(
                lambda surface, center: _get_sample().draw(surface, center), source, size)
        return cache.get(size, _build)

    return factory