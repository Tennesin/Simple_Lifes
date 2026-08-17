"""Private household storage rules for Circle adults."""

import math

from ..ci_settings import *
from ..circle_objects import ConstructionSite
from .circles_adult_patterns import Storage, Construction
from ....all_needed.ai.utility import Consideration

def same_household(creature, owner_id, other_creatures=None):
    if owner_id is None or creature.id == owner_id:
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
        campfire_pos = self.instincts.nearest_known_campfire()
        if campfire_pos is None:
            return None
        for field in ctx.storage_fields:
            if field.is_owned_by_campfire(campfire_pos) and field_belongs_to(c, field, ctx.other_creatures):
                return field
        return None

    def consider(self, ctx):
        if self.instincts.nearest_known_campfire() is None or self._owned_field(ctx) is None:
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

    def _site_belongs_to(self, site, ctx):
        owner_attr = self._OWNER_ATTR_BY_TYPE.get(site.build_type)
        if owner_attr is None:
            return True
        return same_household(self.c, getattr(site, owner_attr, None), ctx.other_creatures)

    def _determine_need(self, campfire_pos, ctx):
        c = self.c
        sites = ctx.construction_sites

        if campfire_pos is None:
            nearby_campfire_site = any(
                s.build_type == "campfire"
                and math.hypot(c.x - s.x, c.y - s.y) < NEW_CAMPFIRE_JOIN_SEARCH_RADIUS
                for s in sites
            )
            if not nearby_campfire_site:
                return "campfire"
            return None

        owned_field = next((f for f in ctx.storage_fields
                            if f.is_owned_by_campfire(campfire_pos)
                            and field_belongs_to(c, f, ctx.other_creatures)), None)
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

        site = super()._find_or_create_site(build_type, campfire_pos, ctx)
        setattr(site, owner_attr, c.id)
        return site

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