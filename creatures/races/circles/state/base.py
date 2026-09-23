"""Общий контракт блоков состояния существа (state/*.py)."""

import dataclasses

class StateBlock:

    def reset(self):
        raise NotImplementedError(
            f"{type(self).__name__} должен переопределить reset()")

    def to_dict(self) -> dict:
        """Полный дамп всех полей dataclass'а."""
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        data = data or {}
        field_names = {f.name for f in dataclasses.fields(cls)}
        kwargs = {key: value for key, value in data.items() if key in field_names}
        return cls(**kwargs)