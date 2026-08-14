"""Private household storage rules for Circle adults."""

import math

from ..ci_settings import *
from ..circle_objects import ConstructionSite
from .circles_adult_patterns import Storage, Construction


def same_household(creature, owner_id, other_creatures=None):
    if owner_id is None or creature.id == owner_id:
        return True
    if creature.partner_id == owner_id:
        return True
    if creature.parent_ids and owner_id in creature.parent_ids:
        return True
    for other in other_creatures or ():
        if other.id == owner_id and other.parent_ids and creature.id in other.parent_ids:
            return True
    return False


def field_belongs_to(creature, field, other_creatures=None):
    return same_household(creature, getattr(field, "built_by", None), other_creatures)


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
        if self.instincts.nearest_known_campfire() is None:
            return [None]
        if self._owned_field(ctx) is None:
            return [None]
        return super().consider(ctx)

    def _pursue(self, ctx):
        c = self.c
        field = self._owned_field(ctx)
        if field is None:
            c.storage_supply_mode = False
            return None
        return self._pursue_supply(field, ctx)


class PrivateConstruction(Construction):
    """Construction rules with explicit ownership for storage sites."""

    def _storage_site_owner(self, site):
        return getattr(site, "storage_owner_id", None)

    def _site_belongs_to(self, site, ctx):
        if site.build_type != "storage":
            return True
        owner_id = self._storage_site_owner(site)
        return same_household(self.c, owner_id, ctx.other_creatures)

    def _determine_need(self, campfire_pos, ctx):
        c = self.c
        sites = ctx.construction_sites

        if campfire_pos is None:
            if not any(s.build_type == "campfire" for s in sites):
                return "campfire"
            return None

        # A storage is a household asset.  Do not require a pre-existing
        # family: the male who has a campfire but no storage is allowed to
        # establish his own one.
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
        if build_type != "storage":
            return super()._find_or_create_site(build_type, campfire_pos, ctx)

        c = self.c
        for site in ctx.construction_sites:
            if site.build_type != "storage":
                continue
            if math.hypot(c.x - site.x, c.y - site.y) >= CONSTRUCTION_SITE_SEARCH_RADIUS:
                continue
            if self._site_belongs_to(site, ctx):
                if getattr(site, "storage_owner_id", None) is None:
                    site.storage_owner_id = c.id
                return site

        site = super()._find_or_create_site(build_type, campfire_pos, ctx)
        site.storage_owner_id = c.id
        return site

    def _find_orphaned_site(self, ctx):
        c = self.c
        if not ctx.construction_sites:
            return None

        # Only adopt an unclaimed storage site; never steal a private one.
        storage_candidates = [s for s in ctx.construction_sites
                              if s.build_type == "storage"
                              and self._site_belongs_to(s, ctx)
                              and math.hypot(c.x - s.x, c.y - s.y)
                                  < CONSTRUCTION_SITE_SEARCH_RADIUS * ORPHAN_SITE_SEARCH_RADIUS_FACTOR]
        if storage_candidates:
            return min(storage_candidates, key=lambda s: math.hypot(c.x - s.x, c.y - s.y))

        return super()._find_orphaned_site(ctx)


# Persist the storage-site owner in worlds saved after this fix.
_original_site_to_dict = ConstructionSite.to_dict
_original_site_from_dict = ConstructionSite.from_dict


def _site_to_dict(site):
    data = _original_site_to_dict(site)
    if site.build_type == "storage":
        data["storage_owner_id"] = getattr(site, "storage_owner_id", None)
    return data


@staticmethod
def _site_from_dict(data):
    site = _original_site_from_dict(data)
    if site.build_type == "storage":
        site.storage_owner_id = data.get("storage_owner_id")
    return site


ConstructionSite.to_dict = _site_to_dict
ConstructionSite.from_dict = _site_from_dict
