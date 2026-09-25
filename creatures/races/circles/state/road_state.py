"""Домен 'Дороги игрока' (не детские) - какие дороги существо уже знает
(useful/useless/dangerous), выученные маршруты-связки к ресурсам
(known_road_links) и текущее следование по дороге (following_road и
сопутствующий прогресс). Персистятся только known_roads/known_road_links -
следование по дороге не переживает сохранение/загрузку, как и раньше."""

import random
from dataclasses import dataclass, field

from .. import ci_settings
from .base import StateBlock

@dataclass
class RoadState(StateBlock):
    # ---------- Знания о дорогах игрока (переживают сохранение) ----------
    known_roads: dict = field(default_factory=dict)
    known_road_links: dict = field(default_factory=dict)

    # ---------- Текущее следование по дороге (НЕ персистится) ----------
    following_road: object = None
    following_road_active: bool = False
    road_progress: int = 0
    road_direction: int = 1
    road_entry_reached: bool = False

    # ---------- Таймер повторного броска "свернуть на дорогу" ----------
    road_follow_check_timer: float = 0.0

    @classmethod
    def rolled(cls):
        """Начальное состояние для только что созданного существа -
        таймер разыгрывается случайно, всё остальное - дефолты."""
        return cls(road_follow_check_timer=random.uniform(*ci_settings.ROAD_FOLLOW_REROLL_INTERVAL))

    def reset(self):
        """Смерть существа: брошенное следование по дороге сбрасывается -
        как и было в Creature.die(). known_roads/known_road_links - долгосрочная
        память, смертью не стирается; road_progress/road_direction тоже не
        трогаем - в исходном die() они не сбрасывались."""
        self.following_road = None
        self.following_road_active = False
        self.road_entry_reached = False

    # ---------- Реакция на исчезновение/правку дороги (creature.py делегирует сюда) ----------

    def on_deleted(self, road):
        """Дорога, за которой мы, возможно, следуем, удалена.
        Возвращает True, если это была именно наша дорога."""
        if self.following_road is not road:
            return False
        self.following_road = None
        self.following_road_active = False
        self.road_entry_reached = False
        self.road_progress = 0
        return True

    def on_progress_shift(self, road, inserted_index):
        """В road вставлена новая точка перекрёстка на месте inserted_index -
        наш индекс прогресса нужно сдвинуть, если мы уже прошли эту точку."""
        if self.following_road is road and self.road_progress >= inserted_index:
            self.road_progress += 1

    # ---------- Персистентность: те же ключи, что были у плоских полей Creature ----------

    def to_persisted_dict(self) -> dict:
        return {
            "known_roads": self.known_roads,
            "known_road_links": self.known_road_links,
        }

    @classmethod
    def from_persisted_dict(cls, state: dict):
        obj = cls.rolled()
        obj.known_roads = state.get("known_roads", {})
        obj.known_road_links = state.get("known_road_links", {})
        return obj