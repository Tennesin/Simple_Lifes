"""Private household storage rules for Circle adults."""

import math
import random

from ..ci_settings import *
from ..circle_objects import ConstructionSite
from .circles_adult_patterns import Storage, Construction
from ....all_needed import geometry
from ....all_needed.ai.utility import Consideration

def same_household(creature, owner_id, other_creatures=None):
    if owner_id is None:
        return False
    if creature.id == owner_id:
        return True
    if creature.partner_id == owner_id:
        return True
    if (creature.life_stage == LIFE_STAGE_CHILD and creature.parent_ids
            and owner_id in creature.parent_ids):
        return True
    for other in other_creatures or ():
        if (other.id == owner_id and other.life_stage == LIFE_STAGE_CHILD
                and other.parent_ids and creature.id in other.parent_ids):
            return True
    return False

def field_belongs_to(creature, field, other_creatures=None):
    owner_ids = getattr(field, "owner_ids", None)
    if not owner_ids:
        return True
    return any(same_household(creature, owner_id, other_creatures) for owner_id in owner_ids)

class PrivateStorage(Storage):
    """Storage behaviour that never treats another household's field as public."""

    def _owned_field(self, ctx):
        c = self.c
        house = next((h for h in ctx.houses if c.id in h.owner_ids or c.home_id == h.id), None)
        if house is not None:
            return house.storage_field(ctx.storage_fields)
        campfire_pos = self.instincts.nearest_known_campfire()
        if campfire_pos is None:
            return None
        for field in ctx.storage_fields:
            if field.is_owned_by_campfire(campfire_pos) and field_belongs_to(c, field, ctx.other_creatures):
                return field
        return None

    def consider(self, ctx):
        if self._owned_field(ctx) is None:
            return [None]
        return [Consideration("storage", self.SCORE, lambda: self._pursue(ctx))]

    def _pursue(self, ctx):
        c = self.c
        field = self._owned_field(ctx)
        if field is None:
            c.storage_supply_mode = False
            return None
        return self._pursue_supply(field, ctx)


class PrivateConstruction(Construction):
    _OWNER_ATTR_BY_TYPE = {"storage": "storage_owner_id", "house": "house_owner_id"}

    # ---------- Расстояние, в пределах которого разные найденные точки костра
    # считаются "тем же самым" ориентиром (не плодим дубликаты-якоря) ----------
    CAMPFIRE_ANCHOR_MERGE_RADIUS = 5

    def _site_belongs_to(self, site, ctx):
        owner_attr = self._OWNER_ATTR_BY_TYPE.get(site.build_type)
        if owner_attr is None:
            return True
        return same_household(self.c, getattr(site, owner_attr, None), ctx.other_creatures)

    def _determine_need(self, campfire_pos, ctx):
        c = self.c
        sites = ctx.construction_sites

        owns_house = any(c.id in h.owner_ids for h in ctx.houses)
        if not owns_house:
            already_building = any(
                s.build_type == "house" and self._site_belongs_to(s, ctx)
                for s in sites
            )
            if already_building:
                return None  # дом уже в процессе - на остальное пока не отвлекаемся
            return "house"

        if campfire_pos is None:
            nearby_campfire_site = any(
                s.build_type == "campfire"
                and math.hypot(c.x - s.x, c.y - s.y) < NEW_CAMPFIRE_JOIN_SEARCH_RADIUS
                for s in sites
            )
            if not nearby_campfire_site:
                return "campfire"
            return None

        house = next((h for h in ctx.houses if c.id in h.owner_ids), None)
        owned_field = next((f for f in ctx.storage_fields
                            if house is not None and f.house_id == house.id), None)
        if owned_field is None:
            owned_site = next((s for s in sites
                               if s.build_type == "storage"
                               and math.hypot(c.x - s.x, c.y - s.y) < CONSTRUCTION_SITE_SEARCH_RADIUS
                               and self._site_belongs_to(s, ctx)), None)
            if owned_site is None:
                return "storage"

        if c.known_graveyard is None:
            linked = self._find_campfire_linked_graveyard(campfire_pos, ctx.graveyards)
            if linked is not None:
                c.known_graveyard = (linked.x, linked.y)
            elif not any(s.build_type == "graveyard" for s in sites):
                return "graveyard"
        return None

    # =====================================================================
    # Домен: место для дома - сперва пробуем "встроиться в общество" рядом
    # с уже существующим или строящимся костром. Если анкеров нет вообще
    # (костров ещё не построено) или ни у одного не нашлось свободного
    # места - _find_or_create_site ниже сам переключит самца на постройку
    # нового костра в другом месте.
    # =====================================================================

    def _collect_campfire_anchors(self, campfire_pos, ctx):
        anchors = []

        def _add(pos):
            if pos is None:
                return
            if any(math.hypot(pos[0] - a[0], pos[1] - a[1]) < self.CAMPFIRE_ANCHOR_MERGE_RADIUS
                   for a in anchors):
                return
            anchors.append(pos)

        _add(campfire_pos)
        for fire in ctx.campfires:
            _add((fire.x, fire.y))
        for site in ctx.construction_sites:
            if site.build_type == "campfire":
                _add((site.x, site.y))
        return anchors

    def _score_best_house_site_near(self, anchor, biome_grid, ctx):
        best_point, best_score = None, None
        for _ in range(HOUSE_SITE_SCORE_ATTEMPTS):
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(*HOUSE_BUILD_OFFSET_RANGE)
            point = geometry.clamped_point(anchor[0], anchor[1], angle, dist)
            if not self._point_clear(point, "house", biome_grid, ctx):
                continue
            score = self._score_house_site(point, anchor, biome_grid, ctx)
            if best_score is None or score > best_score:
                best_score, best_point = score, point
        return best_point, best_score

    def _pick_house_point(self, campfire_pos, biome_grid, ctx):
        anchors = self._collect_campfire_anchors(campfire_pos, ctx)

        best_point, best_score = None, None
        for anchor in anchors:
            point, score = self._score_best_house_site_near(anchor, biome_grid, ctx)
            if point is None:
                continue
            if best_score is None or score > best_score:
                best_score, best_point = score, point
        return best_point

    def _find_or_create_site(self, build_type, campfire_pos, ctx):
        owner_attr = self._OWNER_ATTR_BY_TYPE.get(build_type)
        if owner_attr is None:
            return super()._find_or_create_site(build_type, campfire_pos, ctx)

        c = self.c
        for site in ctx.construction_sites:
            if site.build_type != build_type:
                continue
            if math.hypot(c.x - site.x, c.y - site.y) >= CONSTRUCTION_SITE_SEARCH_RADIUS:
                continue
            if self._site_belongs_to(site, ctx):
                if getattr(site, owner_attr, None) is None:
                    setattr(site, owner_attr, c.id)
                return site

        if build_type == "house":
            # ---------- Миграция: если у самца уже есть свой (осиротевший) склад без дома -
            # строим дом вплотную к нему, а не в произвольном месте ----------
            orphan = next((f for f in ctx.storage_fields
                           if c.id in f.owner_ids and getattr(f, "house_id", None) is None), None)
            if orphan is not None:
                point = self._pick_house_point_near_storage(orphan, ctx)
                if point is not None:
                    site = ConstructionSite(point[0], point[1], "house", campfire_pos=campfire_pos)
                    ctx.construction_sites.append(site)
                    setattr(site, owner_attr, c.id)
                    return site

        site = super()._find_or_create_site(build_type, campfire_pos, ctx)
        if site is None:
            if build_type == "house":
                # ---------- Рядом с костром (или костров вообще нет) не нашлось
                # свободного места - самец сам закладывает новый костёр в другом месте ----------
                return self._find_or_create_site("campfire", campfire_pos, ctx)
            return None

        setattr(site, owner_attr, c.id)
        if build_type == "storage":
            house = next((h for h in ctx.houses if c.id in h.owner_ids), None)
            if house is not None:
                site.linked_house_id = house.id
        return site

    def _pick_house_point_near_storage(self, storage, ctx):
        half_house_w = HOUSE_DEFAULT_SIZE[0] / 2
        for side_sign in (1, -1):
            px = storage.x + side_sign * (storage.radius + STORAGE_HOUSE_GAP + half_house_w)
            point = (px, storage.y)
            if self._point_clear(point, "house", ctx.biome_grid, ctx):
                return point
        return None

    def _find_orphaned_site(self, ctx):
        c = self.c
        candidates = []
        for build_type in self._OWNER_ATTR_BY_TYPE:
            candidates.extend(
                s for s in ctx.construction_sites
                if s.build_type == build_type
                and self._site_belongs_to(s, ctx)
                and math.hypot(c.x - s.x, c.y - s.y)
                    < CONSTRUCTION_SITE_SEARCH_RADIUS * ORPHAN_SITE_SEARCH_RADIUS_FACTOR
            )
        if candidates:
            site = min(candidates, key=lambda s: math.hypot(c.x - s.x, c.y - s.y))
            owner_attr = self._OWNER_ATTR_BY_TYPE[site.build_type]
            if getattr(site, owner_attr, None) is None:
                setattr(site, owner_attr, c.id)
            return site
        return super()._find_orphaned_site(ctx)

_original_site_to_dict = ConstructionSite.to_dict
_original_site_from_dict = ConstructionSite.from_dict

_OWNER_ATTR_BY_TYPE = PrivateConstruction._OWNER_ATTR_BY_TYPE

def _site_to_dict(site):
    data = _original_site_to_dict(site)
    owner_attr = _OWNER_ATTR_BY_TYPE.get(site.build_type)
    if owner_attr is not None:
        data[owner_attr] = getattr(site, owner_attr, None)
    return data

@staticmethod
def _site_from_dict(data):
    site = _original_site_from_dict(data)
    owner_attr = _OWNER_ATTR_BY_TYPE.get(site.build_type)
    if owner_attr is not None:
        setattr(site, owner_attr, data.get(owner_attr))
    return site

ConstructionSite.to_dict = _site_to_dict
ConstructionSite.from_dict = _site_from_dict