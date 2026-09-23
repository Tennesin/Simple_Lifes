"""Пакет для новых блоков состояния существа (state/*.py), на которые
постепенно переносятся поля Creature (см. пошаговый план миграции).
Каждый блок - dataclass-наследник StateBlock с методами reset()/to_dict()/
from_dict(), владеющий одним доменом (пубертат, труп/кладбище и т.д.)."""

from .base import StateBlock
from .burial_state import BurialState
from .puberty_state import PubertyState

__all__ = ["StateBlock", "BurialState", "PubertyState"]