"""Кисть биомов: покраска клеток + уничтожение объектов, которым новый биом не подходит."""

import math
from dataclasses import dataclass

import settings

from .removal import CoreClear


@dataclass(frozen=True)
class _Cascade:
    core: CoreClear          # что чистим среди объектов ядра
    is_flood: bool           # True - по флагу clear_on_flood у рас, False - по clear_on_desert
    flood_roads: bool        # помечать ли дороги опасными


# Что происходит с миром при покраске каждым биомом (равнина ничего не уничтожает)
CASCADE_RULES = {
    # море смывает всё, включая камни и траву
    settings.BIOME_SEA: _Cascade(CoreClear(stones=True, grass=True), is_flood=True, flood_roads=True),
    # у реки трава на берегу и камни - обычное дело
    settings.BIOME_RIVER: _Cascade(CoreClear(stones=False, grass=False), is_flood=True, flood_roads=True),
    # на песке не растут трава, кусты, деревья; фрукты, шипы и камни остаются
    settings.BIOME_DESERT: _Cascade(
        CoreClear(fruits=False, spikes=False, stones=False, grass=True), is_flood=False, flood_roads=False),
}


class BiomePainter:

    def __init__(self, game, remover, roads):
        self.game = game
        self.remover = remover      # ObjectRemover
        self.roads = roads          # RoadNetworkService

    def paint(self, wx, wy, biome_type, radius, bump_version=True):
        game = self.game
        grid = game.biome_manager.grid
        if grid is None:
            return
        game.biome_manager.paint(wx, wy, biome_type, radius)
        if bump_version:
            game.world.landscape_version += 1
        self._apply_cascade(grid, wx, wy, radius, biome_type)

    def _apply_cascade(self, grid, wx, wy, radius, biome_type):
        rule = CASCADE_RULES.get(biome_type)
        if rule is None:
            return

        # ---------- Зона = внутри круга кисти И клетка реально перекрашена в этот биом.
        # (Раньше объект в круге, но на непокрашенной клетке, погибал зря.) ----------
        def point_in_zone(px, py):
            return math.hypot(px - wx, py - wy) <= radius and grid.get_at(px, py) == biome_type

        def obj_in_zone(obj):
            return point_in_zone(obj.x, obj.y)

        self.remover.clear_in_zone(obj_in_zone, rule.core)
        self.remover.clear_race_objects(obj_in_zone, flood=rule.is_flood)
        if rule.flood_roads:
            self.roads.mark_flooded(point_in_zone)