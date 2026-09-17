"""Расширение ядрового ObjectPanel строками, специфичными для объектов расы
'Круг' (куст/водоём с приватизацией, костёр, склад, стройплощадка, дом).
Регистрируется в race.py как object_panel_extra_fn."""

import math

from objects import Bush, WaterPuddle
from ...circle_objects import Campfire
from ...ci_settings import *
from ...ci_info import *


def circle_object_panel_extra_lines(obj, creatures):
    lines = []

    if isinstance(obj, (Bush, WaterPuddle)):
        claimed_by = getattr(obj, "claimed_by", None)
        if claimed_by:
            claimant = next((c for c in creatures if c.id == claimed_by), None)
            if claimant is not None:
                name = claimant.name if claimant.name else claimant.id
                lines.append((INFO_INFO_CLAIMED_BY.format(name=name), (255, 210, 60)))

    if isinstance(obj, Campfire):
        residents = [
            c for c in creatures
            if not c.is_dead and c.known_campfire is not None
            and math.hypot(c.known_campfire[0] - obj.x, c.known_campfire[1] - obj.y) < 5
        ]
        occupancy_color = (255, 120, 90) if len(residents) >= CAMPFIRE_MAX_OCCUPANTS else (190, 190, 190)
        lines.append((
            INFO_INFO_CAMPFIRE_OCCUPANCY.format(count=len(residents), max=CAMPFIRE_MAX_OCCUPANTS),
            occupancy_color
        ))
        if residents:
            names = ", ".join(r.name if r.name else r.id for r in residents)
            lines.append((INFO_INFO_CAMPFIRE_RESIDENTS.format(names=names), (200, 200, 200)))
        else:
            lines.append((INFO_INFO_CAMPFIRE_RESIDENTS_NONE, (150, 150, 150)))

    if hasattr(obj, "fruits") and hasattr(obj, "water"):
        owner_ids = getattr(obj, "owner_ids", None)
        if owner_ids:
            owner_names = []
            for owner_id in owner_ids:
                owner = next((c for c in creatures if c.id == owner_id), None)
                owner_names.append(owner.name if owner and owner.name else owner_id)
            lines.append((INFO_INFO_STORAGE_OWNER.format(name=", ".join(owner_names)), (255, 210, 60)))
        else:
            lines.append((INFO_INFO_STORAGE_OWNER_PUBLIC, (190, 190, 190)))
        lines.append((INFO_INFO_STORAGE_FRUITS.format(count=obj.fruits), (255, 190, 40)))
        lines.append((INFO_INFO_STORAGE_WATER.format(count=obj.water), (100, 170, 230)))

    if hasattr(obj, "build_type"):
        lines.append((
            INFO_INFO_CONSTRUCTION_WOOD.format(deposited=int(obj.deposited_wood), required=obj.required_wood),
            (200, 170, 120)))
        lines.append((
            INFO_INFO_CONSTRUCTION_STONE.format(deposited=int(obj.deposited_stone), required=obj.required_stone),
            (200, 200, 200)))
        if obj.is_building:
            percent = int(min(100, obj.build_progress / obj.build_time * 100)) if obj.build_time > 0 else 0
            lines.append((INFO_INFO_CONSTRUCTION_PROGRESS.format(percent=percent), (235, 140, 30)))

    if hasattr(obj, "capacity") and hasattr(obj, "door_slot"):
        owner_ids = getattr(obj, "owner_ids", None)
        if owner_ids:
            owner_names = []
            for owner_id in owner_ids:
                owner = next((c for c in creatures if c.id == owner_id), None)
                owner_names.append(owner.name if owner and owner.name else owner_id)
            lines.append((INFO_INFO_HOUSE_OWNER.format(name=", ".join(owner_names)), (255, 210, 60)))
        resident_count = len(getattr(obj, "resident_ids", ()))
        lines.append((INFO_INFO_HOUSE_CAPACITY.format(count=f"{resident_count}/{obj.capacity}"), (200, 200, 200)))

        inside_now = [c for c in creatures
                      if not c.is_dead and getattr(c, "home_id", None) == obj.id
                      and hasattr(c, "is_in_own_house") and c.is_in_own_house([obj])]
        if inside_now:
            names = ", ".join(c.name if c.name else c.id for c in inside_now)
            lines.append((INFO_INFO_HOUSE_INSIDE_NOW.format(names=names), (150, 220, 150)))
        else:
            lines.append((INFO_INFO_HOUSE_INSIDE_EMPTY, (150, 150, 150)))

    return lines