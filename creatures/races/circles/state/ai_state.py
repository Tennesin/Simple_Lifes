"""Инфраструктурный домен мозга - не игровое поведение существа, а то, как
мозг сам себя регулирует: троттлинг пересчёта решений (см. Creature.decide()),
обнаружение физического застревания (ai/circles_instincts.py:
_NavigationInstinctMixin.check_if_stuck()) и заморозка - случайная пауза в
fallback-поведении (ai/brain.py:_DispatchMixin._fallback_goal())."""

import random
from dataclasses import dataclass

from .. import ci_settings
from .base import StateBlock

@dataclass
class AIState(StateBlock):
    # ---------- Троттлинг принятия решений ----------
    ai_dt_debt: float = 0.0
    ai_last_goal: object = None
    ai_plan_valid: bool = False

    # ---------- Застревание ----------
    stuck_check_timer: float = ci_settings.STUCK_CHECK_INTERVAL
    position_at_last_check: tuple = (0.0, 0.0)
    stuck_level: int = 0
    stuck_last_nav_index: int = 0

    # ---------- Заморозка (fallback-поведение) ----------
    freeze_timer: float = 0.0

    @classmethod
    def rolled(cls, x=0.0, y=0.0):
        """Начальное состояние для только что созданного существа."""
        return cls(
            ai_dt_debt=random.uniform(0.0, ci_settings.AI_DECISION_INTERVAL),
            position_at_last_check=(x, y),
        )

    def reset(self):
        """Смерть существа: мёртвое существо больше не решает (кэш плана
        сбрасывается, как раньше в AIThrottleState.reset()) и не мечется в
        fallback-поведении (freeze_timer сбрасывается, как раньше в
        Creature.die())."""
        self.ai_plan_valid = False
        self.ai_last_goal = None
        self.freeze_timer = 0.0