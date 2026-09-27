"""Домен 'что существо сейчас несёт и куда' - объединяет бывшие FeedingState
и StorageSupplyState."""

import random
from dataclasses import dataclass

from .. import ci_settings
from .base import StateBlock

@dataclass
class ResourceCarryState(StateBlock):
    # ---------- Что несёт и кому спешит доставить (донашивание еды/воды) ----------
    carried_fruit: bool = False
    carried_water: bool = False
    feed_target_id: str | None = None

    # ---------- Тревожный сигнал "мой ребёнок голодает/хочет пить" от child_ai.py ----------
    urgent_child_id: str | None = None
    urgent_child_timer: float = 0.0

    # ---------- Таймер периодической проверки "не нужно ли кому-то помочь" ----------
    parent_feed_check_timer: float = 0.0

    # ---------- Снабжение семейного склада: таймер проверки + "несу на склад" ----------
    storage_check_timer: float = 0.0
    storage_supply_mode: bool = False

    @classmethod
    def rolled(cls):
        """Начальное состояние - оба таймера периодических проверок
        разыгрываются случайно, всё остальное - дефолты."""
        return cls(
            parent_feed_check_timer=random.uniform(*ci_settings.PARENT_FEED_CHECK_INTERVAL),
            storage_check_timer=random.uniform(*ci_settings.STORAGE_SUPPLY_CHECK_INTERVAL),
        )

    def reset(self):
        """Смерть существа: брошенная ноша, цель кормления и режим
        снабжения склада сбрасываются - как и раньше в обоих исходных
        reset()."""
        self.carried_fruit = False
        self.carried_water = False
        self.feed_target_id = None
        self.urgent_child_id = None
        self.storage_supply_mode = False

    # ---------- Персистентность: ключи объединены из обоих исходных блоков ----------

    def to_persisted_dict(self) -> dict:
        return {
            "carried_fruit": self.carried_fruit,
            "carried_water": self.carried_water,
            "feed_target_id": self.feed_target_id,
            "urgent_child_id": self.urgent_child_id,
            "urgent_child_timer": self.urgent_child_timer,
            "storage_supply_mode": self.storage_supply_mode,
        }

    @classmethod
    def from_persisted_dict(cls, state: dict):
        obj = cls.rolled()
        obj.carried_fruit = state.get("carried_fruit", False)
        obj.carried_water = state.get("carried_water", False)
        obj.feed_target_id = state.get("feed_target_id")
        obj.urgent_child_id = state.get("urgent_child_id")
        obj.urgent_child_timer = state.get("urgent_child_timer", 0.0)
        obj.storage_supply_mode = state.get("storage_supply_mode", False)
        return obj