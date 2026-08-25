"""Слабая обратная ссылка подсистемы на владельца (существо/животное)."""

import weakref

class WeakOwnerMixin:
    """Для подсистем существа: атрибут-владелец называется 'c' (уже принятое
    в проекте соглашение self.c = creature)."""

    def __init__(self, owner):
        self._owner_ref = weakref.ref(owner) if owner is not None else None

    @property
    def c(self):
        return self._owner_ref() if self._owner_ref is not None else None

    @c.setter
    def c(self, value):
        self._owner_ref = weakref.ref(value) if value is not None else None


class WeakEntityMixin:
    """Для generic-ИИ животных (GrazerAI/WolfAI и т.п.): атрибут-владелец
    называется 'entity' (уже принятое в проекте соглашение self.entity = animal)."""

    def __init__(self, entity):
        self._entity_ref = weakref.ref(entity) if entity is not None else None

    @property
    def entity(self):
        return self._entity_ref() if self._entity_ref is not None else None

    @entity.setter
    def entity(self, value):
        self._entity_ref = weakref.ref(value) if value is not None else None