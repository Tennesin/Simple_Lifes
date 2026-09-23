"""Домен 'Детские дороги: игра' - принадлежит child_ai.py:_ChildRoadPlayMixin.
Хранит текущую дорогу, по которой ребёнок бегает ради удовольствия, прогресс
по ней, кулдаун между попытками начать новую игру и память о скуке
(сколько раз подряд отыграна каждая конкретная дорога)."""

import random
from dataclasses import dataclass, field

from .. import ci_settings
from .base import StateBlock

@dataclass
class ChildRoadPlayState(StateBlock):
    road: object = None             # ChildRoad | None - дорога, по которой сейчас играем
    progress: int = 0
    direction: int = 1
    entry_reached: bool = False
    play_cooldown: float = 0.0
    play_counts: dict = field(default_factory=dict)     # road_id -> сколько раз подряд отыграна
    disinterest: dict = field(default_factory=dict)     # road_id -> оставшееся время "надоело"

    @classmethod
    def rolled(cls):
        """Начальное состояние для только что созданного существа -
        play_cooldown разыгрывается случайно, всё остальное - дефолты."""
        return cls(play_cooldown=random.uniform(1.0, 3.0))

    def reset(self):
        """Смерть существа."""
        self.road = None
        self.entry_reached = False

    def stop_playing(self):
        """Игра прервана НЕ смертью (дошли до конца дороги / дорога стала
        опасной / дорога удалена) - в отличие от reset(), здесь сбрасывается
        и progress, как и было во всех этих местах в исходном коде."""
        self.road = None
        self.progress = 0
        self.entry_reached = False

    def start(self, road, progress, direction):
        self.road = road
        self.progress = progress
        self.direction = direction
        self.entry_reached = False

    # ---------- Реакция на исчезновение/правку дороги (creature.py делегирует сюда) ----------

    def on_deleted(self, road):
        """Дорога, за которой мы, возможно, следим, удалена.
        Возвращает True, если это была именно наша дорога (тогда
        creature.py должен дополнительно сбросить общий following_road_active)."""
        if self.road is not road:
            return False
        self.stop_playing()
        return True

    def on_progress_shift(self, road, inserted_index):
        """В road вставлена новая точка перекрёстка на месте inserted_index -
        наш индекс прогресса нужно сдвинуть, если мы уже прошли эту точку."""
        if self.road is road and self.progress >= inserted_index:
            self.progress += 1

    # ---------- Скука: конкретная дорога временно перестаёт быть интересной ----------

    def register_play_session(self, road):
        road_id = road.id
        count = self.play_counts.get(road_id, 0) + 1
        if count >= ci_settings.CHILD_ROAD_DISINTEREST_THRESHOLD:
            self.disinterest[road_id] = ci_settings.CHILD_ROAD_DISINTEREST_DURATION
            self.play_counts[road_id] = 0
        else:
            self.play_counts[road_id] = count

    def tick_disinterest(self, dt):
        if not self.disinterest:
            return
        expired = []
        for road_id in list(self.disinterest.keys()):
            self.disinterest[road_id] -= dt
            if self.disinterest[road_id] <= 0:
                expired.append(road_id)
        for road_id in expired:
            del self.disinterest[road_id]
            self.play_counts.pop(road_id, None)