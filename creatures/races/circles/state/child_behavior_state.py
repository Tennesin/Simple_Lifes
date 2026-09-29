"""Домен 'Поведение ребёнка' - испуг от одиночества (distress_timer) и игра
в догонялки со сверстником (роль, партнёр, таймер, кулдаун). Владелец логики -
ai/child_ai.py:_ChildDistressMixin/_ChildTagGameMixin. Игра затрагивает сразу
двух существ, поэтому запись в блок партнёра идёт через методы блока
(become_chaser/stop_game), а не прямым присваиванием полей.
Состояние не персистится (как и раньше): при загрузке мира заново разыгрывается."""

import random
from dataclasses import dataclass

from .. import ci_settings
from .base import StateBlock

@dataclass
class ChildBehaviorState(StateBlock):
    # ---------- Испуг от одиночества ----------
    distress_timer: float = 0.0

    # ---------- Игра в догонялки ----------
    play_target_id: str | None = None
    play_role: str | None = None          # None | "chaser" | "runner"
    play_timer: float = 0.0
    play_cooldown: float = 0.0

    @classmethod
    def rolled(cls):
        """Начальное состояние для только что созданного существа -
        кулдаун игры разыгрывается случайно (тот же диапазон, что был
        литералом 2.0-4.0), всё остальное - дефолты."""
        return cls(play_cooldown=random.uniform(*ci_settings.CHILD_PLAY_CHECK_INTERVAL))

    @property
    def is_playing(self):
        return self.play_target_id is not None and self.play_role is not None

    def reset(self):
        """Смерть существа: сбрасывается только игра - как и было в
        Creature.die(). distress_timer/play_timer/play_cooldown не трогаем."""
        self.play_target_id = None
        self.play_role = None

    def on_grown_up(self):
        """Переход Ребёнок -> Взрослый (CreatureAging._on_stage_changed).
        Кулдаун намеренно не сбрасывается - как и раньше."""
        self.distress_timer = 0.0
        self.play_target_id = None
        self.play_role = None
        self.play_timer = 0.0

    # ---------- Игра: единые точки входа/выхода ----------

    def start_tag(self, playmate_id):
        self.play_target_id = playmate_id
        self.play_role = "chaser"
        self.play_timer = 0.0

    def become_chaser(self, partner_id, timer):
        """Вызывается у ПАРТНЁРА, которого только что 'осалили'."""
        self.play_target_id = partner_id
        self.play_role = "chaser"
        self.play_timer = timer

    def stop_game(self):
        self.play_target_id = None
        self.play_role = None
        self.play_timer = 0.0
        self.play_cooldown = random.uniform(*ci_settings.CHILD_PLAY_CHECK_INTERVAL)