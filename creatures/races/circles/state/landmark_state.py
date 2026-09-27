"""Домен 'Ориентиры' - знакомый костёр (координаты + id), привязанное к нему
место сна и зона комфорта (якорь для интуитивной памяти), плюс таймер
периодической регистрации видимых ориентиров. Владелец логики -
ai/circles_instincts.py:_LandmarkLookupMixin/_SleepInstinctMixin;
ai/brain.py:_ReflexMixin прерывает сон у костра при испуге/пробуждении;
social.py:CreatureCommunication делится знакомым костром и зоной комфорта
при разговоре."""

import random
from dataclasses import dataclass

from .. import ci_settings
from .base import StateBlock

@dataclass
class LandmarkState(StateBlock):
    comfort_point: tuple = (0.0, 0.0)
    known_campfire: tuple | None = None
    known_campfire_id: str | None = None
    sleep_spot: tuple | None = None
    sleep_spot_campfire: tuple | None = None
    landmark_register_timer: float = 0.0

    @classmethod
    def rolled(cls, x=0.0, y=0.0):
        """Начальное состояние для только что созданного существа -
        зона комфорта = точка появления, таймер регистрации разыгрывается
        случайно, всё остальное - дефолты."""
        return cls(
            comfort_point=(x, y),
            landmark_register_timer=random.uniform(0.0, 1.5),
        )

    def reset(self):
        """Смерть существа: в исходном die() эти поля не трогались вовсе -
        комфорт-точка и знакомый костёр переживают смерть, как и раньше.
        Метод оставлен пустым намеренно, а не удалён - единая точка вызова
        нужна на случай, если это когда-нибудь изменится."""
        pass

    def to_persisted_dict(self) -> dict:
        return {
            "comfort_point": list(self.comfort_point),
            "known_campfire": list(self.known_campfire) if self.known_campfire else None,
            "known_campfire_id": self.known_campfire_id,
        }

    @classmethod
    def from_persisted_dict(cls, state: dict, fallback_point=(0.0, 0.0)):
        obj = cls.rolled(*fallback_point)
        comfort_point = state.get("comfort_point")
        if comfort_point:
            obj.comfort_point = tuple(comfort_point)
        known_campfire = state.get("known_campfire")
        obj.known_campfire = tuple(known_campfire) if known_campfire else None
        obj.known_campfire_id = state.get("known_campfire_id")
        return obj