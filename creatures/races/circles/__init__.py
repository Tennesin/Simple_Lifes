"""Runtime fixes for the Circle race package.

Storage fields are private household resources when they have an owner.  The
legacy ``built_by is None`` case remains public for backwards compatibility.
Construction sites for storage are claimed by the first adult male that
starts working on them, so another Circle cannot silently adopt that private
site as its own.
"""

from .ai.circles_instincts import UniversalInstincts
from .ai.circles_adult_patterns import Construction


def _same_household(creature, owner_id, creatures=None):
    """Return True when ``creature`` belongs to the storage owner's household."""
    if owner_id is None:
        return True
    if creature.id == owner_id:
        return True
    if creature.partner_id == owner_id:
        return True
    if creature.parent_ids and owner_id in creature.parent_ids:
        return True

    for other in creatures or ():
        if other.id == owner_id and other.parent_ids and creature.id in other.parent_ids:
            return True
    return False


def _find_storage_field_private(self, storage_fields):
    """Find only a storage usable by this Circle's household.

    Previously ownership was reduced to the campfire position.  That made a
    storage linked to the same campfire effectively public because every
    creature could resolve the same campfire position.  ``built_by`` is the
    actual owner, so it must participate in access checks.
    """
    c = self.c
    campfire_pos = self.nearest_known_campfire()
    if campfire_pos is None or not storage_fields:
        return None

    # ``other_creatures`` is not available here, so child access is handled
    # from the child's parent_ids.  A parent's use by a child is covered by
    # the child's own parent_ids check above.
    for field in storage_fields:
        if not field.is_owned_by_campfire(campfire_pos):
            continue
        owner_id = getattr(field, "built_by", None)
        if owner_id is None:
            # Preserve old worlds where storage had no owner yet.
            return field
        if _same_household(c, owner_id):
            return field
    return None


UniversalInstincts.find_storage_field = _find_storage_field_private


_original_find_or_create_site = Construction._find_or_create_site


def _find_or_create_site_private_storage(self, build_type, campfire_pos, ctx):
    """Keep storage construction sites private once claimed by a builder."""
    if build_type != "storage":
        return _original_find_or_create_site(self, build_type, campfire_pos, ctx)

    c = self.c
    sites = ctx.construction_sites
    search_radius = CONSTRUCTION_SITE_SEARCH_RADIUS

    for site in sites:
        if site.build_type != "storage":
            continue
        if math.hypot(c.x - site.x, c.y - site.y) >= search_radius:
            continue

        owner_id = getattr(site, "storage_owner_id", None)
        if owner_id is None:
            site.storage_owner_id = c.id
            return site
        if _same_household(c, owner_id, ctx.other_creatures):
            return site

    site = _original_find_or_create_site(self, build_type, campfire_pos, ctx)
    site.storage_owner_id = c.id
    return site


# ``math`` is intentionally imported here instead of changing the large AI
# module just for this ownership fix.
import math

Construction._find_or_create_site = _find_or_create_site_private_storage


_original_find_orphaned_site = Construction._find_orphaned_site


def _find_orphaned_site_private_storage(self, ctx):
    site = _original_find_orphaned_site(self, ctx)
    if site is None or site.build_type != "storage":
        return site

    owner_id = getattr(site, "storage_owner_id", None)
    if owner_id is None or _same_household(self.c, owner_id, ctx.other_creatures):
        if owner_id is None:
            site.storage_owner_id = self.c.id
        return site
    return None


Construction._find_orphaned_site = _find_orphaned_site_private_storage
