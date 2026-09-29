"""Домен 'Социальные запросы и помощь' - просьба о компании (кто-то просит
подойти и поговорить), таймер обмена информацией при разговоре и обязательство
помочь конкретному нуждающемуся сородичу. Владельцы логики -
social.py:CreatureSocial.request_company, ai/patterns/social.py:EmpathyHelp/
SocialResponse, interactions.py:_talk_to_companions; таймеры запроса тикает
ai/brain.py:_TimerTickMixin. relationships сюда НЕ входит: это накопленные
данные, читаются панелью, скорбью и спавном напрямую.
Состояние не персистится (как и раньше)."""

from dataclasses import dataclass

from .. import ci_settings
from .base import StateBlock

@dataclass
class SocialState(StateBlock):
    # ---------- Просьба о компании (кто-то позвал нас подойти) ----------
    request_timer: float = 0.0
    request_point: tuple | None = None

    # ---------- Обмен информацией при разговоре ----------
    share_info_timer: float = 0.0

    # ---------- Обязательство помочь нуждающемуся сородичу ----------
    helping_target_id: str | None = None
    helping_commit_timer: float = 0.0

    def reset(self):
        """Смерть существа: сбрасывается только просьба о компании - как и
        было в Creature.die(). helping_*/share_info_timer не трогаем."""
        self.request_timer = 0.0
        self.request_point = None

    def set_request(self, point):
        """Единая точка записи просьбы о компании (вызывается и у ДРУГОГО
        существа - см. CreatureSocial.request_company)."""
        self.request_timer = ci_settings.SOCIAL_REQUEST_HOLD_TIME
        self.request_point = point