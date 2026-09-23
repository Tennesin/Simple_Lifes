"""Домен 'Добыча ресурсов и строительство' - переносная ёмкость тела,
текущая добыча дерева/камня и участие в стройке (своей или чужой).
Владелец логики - ai/patterns/construction.py:Construction/PrivateConstruction;
mechanics/tick.py забирает одноразовые pending_*-сигналы сразу после decide(),
mechanics/input_events.py сбрасывает цель при исчезновении стройплощадки."""

import random
from dataclasses import dataclass, field

from .. import ci_settings
from .base import StateBlock

@dataclass
class ConstructionState(StateBlock):
    # ---------- Переносная ёмкость - характеристика тела, разыгрывается один раз ----------
    carry_capacity: int = 0
    carried_resources: dict = field(default_factory=lambda: {"wood": 0, "stone": 0})

    # ---------- Текущая добыча дерева/камня ----------
    gather_target_id: str | None = None
    gather_type: str | None = None            # "wood" | "stone"
    gather_progress: float = 0.0
    gather_needed_amount: int | None = None

    # ---------- Участие в стройке (своей или чужой) ----------
    construction_target_id: str | None = None
    construction_phase: str | None = None     # None | "deposit" | "build"

    # ---------- Одноразовые сигналы "только что завершил" - забираются
    # mechanics/tick.py в тот же тик, что и появились, и им же обнуляются ----------
    pending_construction_cleanup: tuple | None = None
    pending_site_cleanup: object = None

    # ---------- Таймеры периодических проверок ----------
    construction_check_timer: float = 0.0
    build_help_check_timer: float = 0.0

    @classmethod
    def rolled(cls):
        """Начальное состояние для только что созданного существа -
        ёмкость и таймеры проверок разыгрываются случайно, всё остальное - дефолты."""
        return cls(
            carry_capacity=random.randint(*ci_settings.CREATURE_CARRY_CAPACITY_RANGE),
            construction_check_timer=random.uniform(*ci_settings.CONSTRUCTION_CHECK_INTERVAL),
            build_help_check_timer=random.uniform(*ci_settings.BUILD_HELP_CHECK_INTERVAL),
        )

    def reset(self):
        """Смерть существа: брошенная добыча и стройка сбрасываются - как и раньше."""
        self.carried_resources = {"wood": 0, "stone": 0}
        self.gather_target_id = None
        self.gather_type = None
        self.gather_progress = 0.0
        self.construction_target_id = None
        self.construction_phase = None

    # ---------- Персистентность: те же ключи, что были у плоских полей Creature ----------

    def to_persisted_dict(self) -> dict:
        return {
            "carry_capacity": self.carry_capacity,
            "carried_resources": self.carried_resources,
            "construction_target_id": self.construction_target_id,
            "construction_phase": self.construction_phase,
            "gather_target_id": self.gather_target_id,
            "gather_type": self.gather_type,
            "gather_progress": self.gather_progress,
            "gather_needed_amount": self.gather_needed_amount,
        }

    @classmethod
    def from_persisted_dict(cls, state: dict):
        obj = cls.rolled()
        obj.carry_capacity = state.get("carry_capacity", obj.carry_capacity)
        obj.carried_resources = state.get("carried_resources", {"wood": 0, "stone": 0})
        obj.construction_target_id = state.get("construction_target_id")
        obj.construction_phase = state.get("construction_phase")
        obj.gather_target_id = state.get("gather_target_id")
        obj.gather_type = state.get("gather_type")
        obj.gather_progress = state.get("gather_progress", 0.0)
        obj.gather_needed_amount = state.get("gather_needed_amount")
        return obj