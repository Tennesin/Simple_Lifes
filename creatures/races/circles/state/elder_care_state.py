"""Домен 'Опека старика над чужим (не своим) ребёнком' - принадлежит
ai/older_ai.py:ElderWardCare. elder_ward_check_timer не персистится
(как и все прочие таймеры периодических проверок в проекте - см.
StorageSupplyState/ConstructionState) - при загрузке мира просто
разыгрывается заново."""

import random
from dataclasses import dataclass

from .. import ci_settings
from .base import StateBlock

@dataclass
class ElderCareState(StateBlock):
    elder_ward_id: str | None = None
    elder_ward_check_timer: float = 0.0

    @classmethod
    def rolled(cls):
        """Начальное состояние для только что созданного существа -
        таймер проверки разыгрывается случайно, всё остальное - дефолты."""
        return cls(elder_ward_check_timer=random.uniform(*ci_settings.ELDER_WARD_CHECK_INTERVAL))

    def reset(self):
        """Смерть существа: подопечный остаётся без присмотра - как и раньше."""
        self.elder_ward_id = None

    def to_persisted_dict(self) -> dict:
        return {"elder_ward_id": self.elder_ward_id}

    @classmethod
    def from_persisted_dict(cls, state: dict):
        obj = cls.rolled()
        obj.elder_ward_id = state.get("elder_ward_id")
        return obj