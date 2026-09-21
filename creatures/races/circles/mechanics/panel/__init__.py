"""Правая информационная панель и связанные оверлеи расы 'Круг'.
Разбито по файлам: панель существа / панель кладбища / древо родословной /
доп.строки generic ObjectPanel. Наружу отдаёт тот же набор имён, что раньше
отдавал единый panel.py — импорты в race.py менять не нужно."""

from .creature_panel import CreaturePanel
from .genealogy import GenealogyTreeOverlay
from .graveyard_panel import GraveyardPanel
from .object_extra_lines import circle_object_panel_extra_lines

__all__ = [
    "CreaturePanel",
    "GenealogyTreeOverlay",
    "GraveyardPanel",
    "circle_object_panel_extra_lines",
]