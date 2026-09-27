"""Домен 'Троттлинг принятия решений ИИ' - принадлежит Creature.decide()/
invalidate_plan(). Мозг реально считает раз в ci_settings.AI_DECISION_INTERVAL
секунд, а не каждый кадр: ai_dt_debt копит прошедшее между пересчётами время,
ai_last_goal/ai_plan_valid - закэшированный результат последнего решения,
отдаваемый на кадрах без пересчёта."""

import random
from dataclasses import dataclass

from .. import ci_settings
from .base import StateBlock

@dataclass
class AIThrottleState(StateBlock):
    ai_dt_debt: float = 0.0
    ai_last_goal: object = None
    ai_plan_valid: bool = False

    @classmethod
    def rolled(cls):
        """Начальное состояние для только что созданного существа -
        накопленный долг времени разыгрывается случайно (чтобы существа не
        пересчитывали решения синхронно один кадр в кадр), всё остальное -
        дефолты."""
        return cls(ai_dt_debt=random.uniform(0.0, ci_settings.AI_DECISION_INTERVAL))

    def reset(self):
        """Смерть существа: мёртвое существо больше не решает - кэш плана
        сбрасывается, как и было в исходном Creature.die(). ai_dt_debt
        НЕ трогаем намеренно: в исходном die() он не сбрасывался."""
        self.ai_plan_valid = False
        self.ai_last_goal = None