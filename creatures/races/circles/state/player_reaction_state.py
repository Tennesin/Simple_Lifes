"""Домен 'Реакция на игрока' - отношение существа к игроку, краткая история
его действий над существом, флаги 'получил имя'/'назначен избранным', а также
краткосрочные состояния, вызванные игроком: успокоение, страх перед игроком,
удержание в руке. Владелец логики - player_reactions.py:PlayerReactionHandler;
таймеры тикает ai/brain.py:_TimerTickMixin.

Общий страх (fear_timer/fear_source) сюда НЕ входит: его вызывают не только
действия игрока (территория, разрушенный дом, опасная детская дорога)."""

from dataclasses import dataclass, field

from .base import StateBlock

@dataclass
class PlayerReactionState(StateBlock):
    # ---------- Долгосрочное (персистится) ----------
    relationship: float = 0.0                 # -100..+100
    named: bool = False
    favorite_bonus_applied: bool = False
    history: list = field(default_factory=list)   # последние MAX_PLAYER_MEMORY событий

    # ---------- Краткосрочное (НЕ персистится) ----------
    calm_timer: float = 0.0
    player_fear_timer: float = 0.0
    is_grabbed: bool = False
    grab_before_state: dict | None = None

    def reset(self):
        """Смерть существа: сбрасываются только краткосрочные состояния - как и
        было в Creature.die(). Отношение к игроку, история и флаги переживают
        смерть (панель трупа по-прежнему показывает отношение)."""
        self.calm_timer = 0.0
        self.player_fear_timer = 0.0
        self.is_grabbed = False
        self.grab_before_state = None

    # ---------- Персистентность: ключи совпадают 1:1 со старым state.json ----------

    def to_persisted_dict(self) -> dict:
        return {
            "player_relationship": self.relationship,
            "player_named": self.named,
            "favorite_bonus_applied": self.favorite_bonus_applied,
            "player_memory": self.history,
        }

    @classmethod
    def from_persisted_dict(cls, state: dict):
        obj = cls()
        obj.relationship = state.get("player_relationship", 0.0)
        obj.named = state.get("player_named", False)
        obj.favorite_bonus_applied = state.get("favorite_bonus_applied", False)
        obj.history = state.get("player_memory", [])
        return obj