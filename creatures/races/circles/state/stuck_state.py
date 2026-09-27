"""Домен 'Застревание' - принадлежит
ai/circles_instincts.py:_NavigationInstinctMixin.check_if_stuck() (тик
таймера - ai/brain.py:_TimerTickMixin). Периодически (раз в
ci_settings.STUCK_CHECK_INTERVAL) сверяет, насколько существо реально
сдвинулось и продвинулся ли его nav-путь; если оно застряло - копит
stuck_level и по эскалации делает аварийный рывок в сторону."""

from dataclasses import dataclass

from .. import ci_settings
from .base import StateBlock

@dataclass
class StuckState(StateBlock):
    stuck_check_timer: float = ci_settings.STUCK_CHECK_INTERVAL
    position_at_last_check: tuple = (0.0, 0.0)
    stuck_level: int = 0
    stuck_last_nav_index: int = 0

    @classmethod
    def rolled(cls, x=0.0, y=0.0):
        """Начальное состояние для только что созданного существа -
        точка последней проверки = точка появления, всё остальное - дефолты."""
        return cls(position_at_last_check=(x, y))

    def reset(self):
        """Смерть существа: в исходном die() эти поля не трогались вовсе -
        метод оставлен пустым намеренно, как и в LandmarkState.reset() -
        единая точка вызова нужна на случай, если это когда-нибудь изменится."""
        pass