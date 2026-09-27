"""Домен 'Сон' - принадлежит ai/brain.py:_ReflexMixin (переход в сон/
пробуждение), ai/circles_instincts.py:_SleepInstinctMixin.seek_sleep_spot()
(куда идти спать) и physiology.py:CreatureNeeds._update_energy() (расход/
восстановление энергии во сне). wake_threshold - порог энергии, при
котором существо просыпается само; sleep_forced отличает "упал от
бессилия" от осознанного отхода ко сну у костра/дома."""

import random
from dataclasses import dataclass

from .. import ci_settings
from .base import StateBlock

@dataclass
class SleepState(StateBlock):
    seeking_sleep: bool = False
    is_sleeping: bool = False
    sleep_forced: bool = False
    wake_threshold: float = 85.0

    @classmethod
    def rolled(cls, temperament=None):
        """Начальное состояние - порог пробуждения разыгрывается по
        темпераменту, всё остальное - дефолты."""
        return cls(wake_threshold=random.uniform(
            *ci_settings.WAKE_ENERGY_THRESHOLD.get(temperament, (85, 90))))

    def reset(self):
        """Смерть существа: в исходном die() эти поля не трогались вовсе -
        метод оставлен пустым намеренно, как и у LandmarkState/StuckState."""
        pass

    def to_persisted_dict(self) -> dict:
        return {
            "is_sleeping": self.is_sleeping,
            "sleep_forced": self.sleep_forced,
        }

    @classmethod
    def from_persisted_dict(cls, state: dict, temperament=None):
        obj = cls.rolled(temperament)
        obj.is_sleeping = state.get("is_sleeping", False)
        obj.sleep_forced = state.get("sleep_forced", False)
        return obj