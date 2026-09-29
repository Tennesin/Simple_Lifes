"""Пакет для новых блоков состояния существа (state/*.py), на которые
постепенно переносятся поля Creature (см. пошаговый план миграции).
Каждый блок - dataclass-наследник StateBlock с методами reset()/to_dict()/
from_dict(), владеющий одним доменом (пубертат, труп/кладбище, детские
дороги, стройка/добыча ресурсов, донашивание ресурсов, инфраструктура
ИИ и т.д.)."""

from .base import StateBlock
from .ai_state import AIState
from .awareness_state import AwarenessState
from .burial_state import BurialState
from .child_road_play_state import ChildRoadPlayState
from .construction_state import ConstructionState
from .elder_care_state import ElderCareState
from .housing_state import HousingState
from .landmark_state import LandmarkState
from .needs_seeking_state import NeedsSeekingState
from .player_reaction_state import PlayerReactionState
from .puberty_state import PubertyState
from .resource_carry_state import ResourceCarryState
from .road_state import RoadState
from .road_verify_state import RoadVerifyState
from .sleep_state import SleepState
from .child_behavior_state import ChildBehaviorState
from .social_state import SocialState

__all__ = [
    "StateBlock", "AIState", "AwarenessState", "BurialState", "ChildRoadPlayState",
    "ConstructionState", "ElderCareState", "HousingState", "LandmarkState",
    "NeedsSeekingState", "PlayerReactionState", "PubertyState", "ResourceCarryState",
    "RoadState", "RoadVerifyState", "SleepState", "ChildBehaviorState", "SocialState",
]