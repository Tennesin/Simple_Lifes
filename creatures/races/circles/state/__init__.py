"""Пакет для новых блоков состояния существа (state/*.py), на которые
постепенно переносятся поля Creature (см. пошаговый план миграции).
Каждый блок - dataclass-наследник StateBlock с методами reset()/to_dict()/
from_dict(), владеющий одним доменом (пубертат, труп/кладбище, детские
дороги, стройка/добыча ресурсов, кормление и т.д.)."""

from .base import StateBlock
from .burial_state import BurialState
from .child_road_play_state import ChildRoadPlayState
from .construction_state import ConstructionState
from .elder_care_state import ElderCareState
from .feeding_state import FeedingState
from .puberty_state import PubertyState
from .road_state import RoadState
from .road_verify_state import RoadVerifyState
from .storage_supply_state import StorageSupplyState
from .housing_state import HousingState

__all__ = [
    "StateBlock", "BurialState", "ChildRoadPlayState", "ConstructionState",
    "ElderCareState", "FeedingState", "PubertyState", "RoadState",
    "RoadVerifyState",
]