"""Домен 'Осведомлённость' - что существо знает о типах объектов мира (known)
и куда оно идёт по свежему воспоминанию о еде/воде, чтобы проверить, есть ли
там ещё что-то (цели-воспоминания). Владельцы логики: interactions.py (узнавание
при контакте), ai/patterns/curiosity.py (что ещё неизвестно), social.py (обмен
знаниями), ai/circles_instincts.py:_ResourceMemoryMixin (цели-воспоминания)."""

from dataclasses import dataclass, field

from .base import StateBlock

def _default_known():
    return {"fruit": False, "spike": False, "water": False,
            "bush": False, "campfire": False}

@dataclass
class AwarenessState(StateBlock):
    # ---------- Знакомство с типами объектов: тип -> знает ли (персистится) ----------
    known: dict = field(default_factory=_default_known)

    # ---------- Текущая цель "иду проверить воспоминание" (НЕ персистится) ----------
    food_memory_target: tuple | None = None
    water_memory_target: tuple | None = None

    def reset(self):
        """Смерть существа: в исходном die() эти поля не трогались вовсе - знания
        переживают смерть. Метод оставлен пустым намеренно (как у LandmarkState/
        SleepState): единая точка вызова нужна на случай, если это изменится."""
        pass

    # ---------- Персистентность: ключ совпадает 1:1 со старым state.json ----------

    def to_persisted_dict(self) -> dict:
        return {"knowledge": self.known}

    @classmethod
    def from_persisted_dict(cls, state: dict):
        obj = cls()
        obj.known = {**obj.known, **state.get("knowledge", {})}
        return obj