"""Домен 'Донашивание еды/воды детям и сородичам' - что несёт с собой
существо и кому спешит доставить ресурс. Владелец логики -
ai/patterns/feeding.py:Feeding/ResourceActions и ai/patterns/storage.py
(попутная доставка со склада); child_ai.py читает carried_fruit/carried_water
и feed_target_id ЧУЖОГО существа, чтобы понять, что за ним уже идёт кормилец."""

import random
from dataclasses import dataclass

from .. import ci_settings
from .base import StateBlock

@dataclass
class FeedingState(StateBlock):
    carried_fruit: bool = False
    carried_water: bool = False
    feed_target_id: str | None = None

    # ---------- Тревожный сигнал "мой ребёнок голодает/хочет пить" от child_ai.py ----------
    urgent_child_id: str | None = None
    urgent_child_timer: float = 0.0

    # ---------- Таймер периодической проверки "не нужно ли кому-то помочь" ----------
    parent_feed_check_timer: float = 0.0

    @classmethod
    def rolled(cls):
        """Начальное состояние для только что созданного существа -
        таймер проверки разыгрывается случайно, всё остальное - дефолты."""
        return cls(parent_feed_check_timer=random.uniform(*ci_settings.PARENT_FEED_CHECK_INTERVAL))

    def reset(self):
        """Смерть существа: брошенная ноша и цель кормления сбрасываются - как и раньше."""
        self.carried_fruit = False
        self.carried_water = False
        self.feed_target_id = None
        self.urgent_child_id = None

    # ---------- Персистентность: те же ключи, что были у плоских полей Creature ----------

    def to_persisted_dict(self) -> dict:
        return {
            "carried_fruit": self.carried_fruit,
            "carried_water": self.carried_water,
            "feed_target_id": self.feed_target_id,
            "urgent_child_id": self.urgent_child_id,
            "urgent_child_timer": self.urgent_child_timer,
        }

    @classmethod
    def from_persisted_dict(cls, state: dict):
        obj = cls.rolled()
        obj.carried_fruit = state.get("carried_fruit", False)
        obj.carried_water = state.get("carried_water", False)
        obj.feed_target_id = state.get("feed_target_id")
        obj.urgent_child_id = state.get("urgent_child_id")
        obj.urgent_child_timer = state.get("urgent_child_timer", 0.0)
        return obj