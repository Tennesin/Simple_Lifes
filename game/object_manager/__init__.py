"""Менеджер объектов мира. Публичное имя - ObjectManager (фасад); реальная работа -
в модулях пакета (placement, generation, growth, biome_paint, roads, lookup, removal, animals)."""

# footprint_* переехали в creatures/all_needed/geometry.py; реэкспорт оставлен, чтобы
# старые "from game.object_manager import footprint_radius" продолжали работать
from creatures.all_needed.geometry import distance_to_footprint, footprint_radius

from .manager import ObjectManager

__all__ = ["ObjectManager", "distance_to_footprint", "footprint_radius"]