"""Домен 'Детские дороги: физическая проверка взрослым' - принадлежит
patterns/roads.py:ChildRoadVerification. Хранит, какую детскую дорогу
взрослый сейчас идёт проверять на безопасность, прогресс по ней и вердикт,
который он успел вынести по пути (нашёл ли шипы)."""

import random
from dataclasses import dataclass

from .. import ci_settings
from .base import StateBlock

@dataclass
class RoadVerifyState(StateBlock):
    target_id: str | None = None    # id проверяемой ChildRoad
    progress: int = 0
    direction: int = 1
    entry_reached: bool = False
    found_danger: bool = False
    check_timer: float = 0.0

    @classmethod
    def rolled(cls):
        """Начальное состояние для только что созданного существа."""
        return cls(check_timer=random.uniform(*ci_settings.CHILD_ROAD_VERIFY_CHECK_INTERVAL))

    def reset(self):
        """Единая точка сброса 'активной проверки' - используется и при
        смерти существа, и при завершении/отмене проверки (дорога исчезла,
        существо добралось до конца). Везде в старом коде это был один и
        тот же набор из 4 полей, поэтому отдельного cancel()-метода не нужно."""
        self.target_id = None
        self.progress = 0
        self.found_danger = False
        self.entry_reached = False

    # ---------- Реакция на исчезновение/правку дороги (creature.py делегирует сюда) ----------

    def on_deleted(self, road):
        """Дорога, которую мы, возможно, проверяем, удалена."""
        if self.target_id != road.id:
            return False
        self.reset()
        return True

    def on_progress_shift(self, road, inserted_index):
        if self.target_id == road.id and self.progress >= inserted_index:
            self.progress += 1