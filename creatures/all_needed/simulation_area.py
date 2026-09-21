"""Общая логика ДОС (Дополнительной Области Симуляции) для сущностей без
собственного 'умного' поведения вне активной зоны, а также общая логика
спасения/гибели животных, оказавшихся в море."""

import settings


def tick_frozen_state(entity, dt, active_ids):
    """Тикает таймер заморозки, если сущность вне активной области ДОС."""
    if active_ids is None or entity.id in active_ids:
        entity.frozen_timer = 0.0
        return False
    entity.frozen_timer += dt
    return True

def should_be_removed(entity):
    """Замороженная сущность исчезает по истечении срока, если её ни разу не трогал игрок"""
    return (entity.frozen_timer > settings.ANIMAL_FROZEN_DISAPPEAR_TIME
            and not getattr(entity, "player_touched", False))

def rescue_from_sea_or_kill(entity, biome_grid, search_radius):
    """Возвращает True, если сущность была найдена в море и обработана."""
    if biome_grid is None or entity.hp <= 0:
        return False
    if biome_grid.get_at(entity.x, entity.y) != settings.BIOME_SEA:
        return False
    land = biome_grid.find_nearest_land(entity.x, entity.y, search_radius)
    if land is not None:
        entity.x, entity.y = land
    entity.hp = 0
    return True