"""Домен 'флаги активного поиска базовых нужд' (голод/жажда/рассудок) -
принадлежит ai/patterns/survival.py:SurvivalNeeds._tick_seeking_flags().
Включаются, когда показатель падает ниже порога, выключаются, когда
показатель восстанавливается выше порога насыщения. Сон сюда намеренно
НЕ входит - в отличие от еды/воды/рассудка, у сна есть собственная
дальнейшая механика (is_sleeping/sleep_forced/wake_threshold), поэтому
seeking_sleep живёт рядом с ними в SleepState, а не здесь."""

from dataclasses import dataclass

from .base import StateBlock

@dataclass
class NeedsSeekingState(StateBlock):
    seeking_food: bool = False
    seeking_water: bool = False
    seeking_sanity: bool = False

    def reset(self):
        """Смерть существа: мёртвое существо ничего не ищет - как и было
        в исходном Creature.die()."""
        self.seeking_food = False
        self.seeking_water = False
        self.seeking_sanity = False