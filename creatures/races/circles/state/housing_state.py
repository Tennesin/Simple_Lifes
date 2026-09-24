"""Домен 'Жильё' - в каком доме живёт существо, отсрочка перед выселением
и признак 'существо прямо сейчас физически внутри своего дома'. at_home
пересчитывается каждый тик в mechanics/tick.py и никогда не персистится -
в отличие от home_id/home_eviction_timer."""

from dataclasses import dataclass

from .base import StateBlock

@dataclass
class HousingState(StateBlock):
    home_id: str | None = None
    home_eviction_timer: float = 0.0
    at_home: bool = False

    def reset(self):
        """Смерть существа: сбрасывается только at_home - как и было раньше.
        home_id намеренно НЕ трогаем, это не входило в исходное поведение die()."""
        self.at_home = False

    def to_persisted_dict(self) -> dict:
        return {
            "home_id": self.home_id,
            "home_eviction_timer": self.home_eviction_timer,
        }

    @classmethod
    def from_persisted_dict(cls, state: dict):
        obj = cls()
        obj.home_id = state.get("home_id")
        obj.home_eviction_timer = state.get("home_eviction_timer", 0.0)
        return obj