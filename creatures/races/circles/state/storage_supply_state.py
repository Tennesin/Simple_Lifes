"""Домен 'Семейный склад запасов: снабжение' - когда взрослый идёт
пополнять семейный склад и несёт ли уже что-то на него."""

import random
from dataclasses import dataclass

from .. import ci_settings
from .base import StateBlock

@dataclass
class StorageSupplyState(StateBlock):
    check_timer: float = 0.0
    mode: bool = False

    @classmethod
    def rolled(cls):
        """Начальное состояние для только что созданного существа."""
        return cls(check_timer=random.uniform(*ci_settings.STORAGE_SUPPLY_CHECK_INTERVAL))

    def reset(self):
        """Смерть существа: снимается только активный режим снабжения -
        таймер проверки не персистится и не трогается, как и раньше."""
        self.mode = False

    def to_persisted_dict(self) -> dict:
        return {"storage_supply_mode": self.mode}

    @classmethod
    def from_persisted_dict(cls, state: dict):
        obj = cls.rolled()
        obj.mode = state.get("storage_supply_mode", False)
        return obj