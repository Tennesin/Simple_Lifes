"""Домен 'Труп/кладбище': состояние живого существа (кого несёт, куда идёт)
и состояние трупа (кто его застолбил/несёт) - оба живут на одном и том же
Creature, поскольку труп - это тоже Creature с is_dead=True. Бизнес-логика
остаётся снаружи (circles_instincts.py, mechanics/input_events.py,
mechanics/tick.py) - этот класс только данные + reset()/персистентность."""

from dataclasses import dataclass

from .base import StateBlock

@dataclass
class BurialState(StateBlock):
    # ---------- Статус трупа: кто его несёт / застолбил (НЕ персистится -
    # труп на паузе между сессиями не бывает "в процессе переноски") ----------
    being_carried_by: str | None = None
    burial_claimant_id: str | None = None

    # ---------- Активность живого: кого несёт, куда идёт (персистится) ----------
    burial_target_id: str | None = None
    graveyard_target_id: str | None = None
    is_dragging_corpse: bool = False

    # ---------- Долгосрочная память о кладбище (персистится) ----------
    known_graveyard: tuple | None = None
    known_graveyard_id: str | None = None

    # ---------- Тревога "старику сообщили о теле" (НЕ персистится) ----------
    graveyard_alert_pos: tuple | None = None
    graveyard_alert_timer: float = 0.0

    def reset(self):
        """Вызывается при смерти существа - сбрасывает только его ЖИВУЮ активность."""
        self.burial_target_id = None
        self.graveyard_target_id = None
        self.is_dragging_corpse = False
        self.graveyard_alert_pos = None
        self.graveyard_alert_timer = 0.0

    def to_persisted_dict(self) -> dict:
        return {
            "burial_target_id": self.burial_target_id,
            "graveyard_target_id": self.graveyard_target_id,
            "known_graveyard": list(self.known_graveyard) if self.known_graveyard else None,
            "known_graveyard_id": self.known_graveyard_id,
        }

    @classmethod
    def from_persisted_dict(cls, state: dict):
        obj = cls()
        obj.burial_target_id = state.get("burial_target_id")
        obj.graveyard_target_id = state.get("graveyard_target_id")
        known_graveyard = state.get("known_graveyard")
        obj.known_graveyard = tuple(known_graveyard) if known_graveyard else None
        obj.known_graveyard_id = state.get("known_graveyard_id")
        return obj