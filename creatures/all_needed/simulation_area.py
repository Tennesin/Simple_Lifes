"""Общая логика ДОС (Дополнительной Области Симуляции) для сущностей без
собственного 'умного' поведения вне активной зоны."""

import settings

def tick_frozen_state(entity, dt, active_ids):
    """Тикает таймер заморозки, если сущность вне активной области ДОС."""
    if active_ids is None or entity.id in active_ids:
        entity.frozen_timer = 0.0
        return False
    entity.frozen_timer += dt
    return True

def should_be_removed(entity):
    """Замороженная сущность исчезает по истечении срока, если её ни разу
    не трогал игрок (player_touched выставляется в шаге 8)."""
    return (entity.frozen_timer > settings.ANIMAL_FROZEN_DISAPPEAR_TIME
            and not getattr(entity, "player_touched", False))