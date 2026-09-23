"""Домен 'Пубертат' (гормональный бум + активное ухаживание) - шаг 1
плана миграции Creature. Тик кулдаунов теперь живёт здесь (tick_cooldowns),
бизнес-логика - по-прежнему в ai/adult_ai.py:PubertyCourtship и
life_cycle.py:CreatureAging, как и было."""

import random
from dataclasses import dataclass, field

from .. import ci_settings
from .base import StateBlock

@dataclass
class PubertyState(StateBlock):
    # ---------- Собственно пубертат (гормональный бум) ----------
    trigger_age: float = 0.0
    done: bool = False
    active: bool = False
    timer: float = 0.0
    speed_bonus: float = 0.0
    orig_curiosity: float | None = None

    # ---------- Активное ухаживание за партнёром ----------
    courtship_cooldown: float = 0.0
    courtship_target_id: str | None = None
    courtship_timer: float = 0.0
    courtship_deadline: float = 0.0
    fail_streak: int = 0
    avoid: dict = field(default_factory=dict)

    @classmethod
    def rolled(cls):
        """Начальное состояние для только что созданного существа -
        trigger_age разыгрывается случайно, всё остальное - дефолты."""
        return cls(trigger_age=random.uniform(
            ci_settings.PUBERTY_TRIGGER_AGE_MIN, ci_settings.PUBERTY_TRIGGER_AGE_MAX))

    def reset(self):
        """Сбрасывает только текущую фазу пубертата/ухаживания. trigger_age
        и done НЕ трогает намеренно: смерть не должна "воскрешать" ещё
        не начавшийся пубертат или переигрывать уже пройденный."""
        self.active = False
        self.timer = 0.0
        self.speed_bonus = 0.0
        self.orig_curiosity = None
        self.courtship_cooldown = 0.0
        self.courtship_target_id = None
        self.courtship_timer = 0.0
        self.courtship_deadline = 0.0
        self.fail_streak = 0
        self.avoid = {}

    def tick_cooldowns(self, dt):
        """Единственная точка тика таймеров этого домена. Раньше
        courtship_cooldown не уменьшался вовсе (баг), а avoid тикал только
        внутри _pursue() - то есть лишь пока PubertyCourtship был выбранным
        компонентом. Теперь оба тикают централизованно каждый кадр,
        независимо от того, что выбрал Utility AI в этом тике."""
        if self.courtship_cooldown > 0:
            self.courtship_cooldown -= dt
        if self.avoid:
            self.avoid = {
                target_id: remaining - dt
                for target_id, remaining in self.avoid.items()
                if remaining - dt > 0
            }

    # ---------- Персистентность: формат совпадает 1:1 со старым state.json,
    # чтобы не ломать уже сохранённые миры. Ухаживание - эфемерная рабочая
    # память ИИ и раньше не сохранялось, поэтому здесь не участвует. ----------

    def to_persisted_dict(self) -> dict:
        return {
            "puberty_trigger_age": self.trigger_age,
            "puberty_done": self.done,
            "puberty_active": self.active,
            "puberty_timer": self.timer,
            "puberty_speed_bonus": self.speed_bonus,
            "puberty_orig_curiosity": self.orig_curiosity,
        }

    @classmethod
    def from_persisted_dict(cls, state: dict):
        obj = cls.rolled()
        obj.trigger_age = state.get("puberty_trigger_age", obj.trigger_age)
        obj.done = state.get("puberty_done", False)
        obj.active = state.get("puberty_active", False)
        obj.timer = state.get("puberty_timer", 0.0)
        obj.speed_bonus = state.get("puberty_speed_bonus", 0.0)
        obj.orig_curiosity = state.get("puberty_orig_curiosity")
        return obj