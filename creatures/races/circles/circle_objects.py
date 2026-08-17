"""Игровые объекты, специфичные для расы 'Круг'."""

import math
import time
import uuid
import random
import pygame

from objects import PolylineRoad
from .ci_settings import *
from .ci_info import *
from ...all_needed import geometry

class StorageField:
    def __init__(self, x, y, owner_campfire_pos=None, owner_ids=None):
        self.x = x
        self.y = y
        self.radius = STORAGE_FIELD_RADIUS
        self.fruits = 0
        self.water = 0
        self.built_by = None
        self.owner_ids = set(owner_ids) if owner_ids else set()
        self.campfire_pos = owner_campfire_pos
        self.created = time.time()
        self.id = str(uuid.uuid4())[:8]
        self.owner_ids = set(list(owner_ids)[:STORAGE_FIELD_MAX_OWNERS]) if owner_ids else set()

    def get_type_name(self):
        return INFO_OBJECT_STORAGE_FIELD

    def has_space_for_fruit(self):
        return self.fruits < STORAGE_FIELD_MAX_FRUITS

    def has_space_for_water(self):
        return self.water < STORAGE_FIELD_MAX_WATER

    def is_public(self):
        return not self.owner_ids

    def add_owner(self, owner_id):
        if owner_id is None or owner_id in self.owner_ids:
            return
        if len(self.owner_ids) >= STORAGE_FIELD_MAX_OWNERS:
            return
        self.owner_ids.add(owner_id)

    def grants_full_access(self, creature, other_creatures=None):
        if self.is_public():
            return True
        if creature.id in self.owner_ids:
            return True
        for owner_id in self.owner_ids:
            if creature.partner_id == owner_id:
                return True
            if (creature.life_stage == LIFE_STAGE_CHILD and creature.parent_ids
                    and owner_id in creature.parent_ids):
                return True
        return False

    def punish_theft(self, thief, other_creatures):
        """Кража воспринимается владельцами очень болезненно. Исключение -
        старики: если вор - ребёнок, старик-владелец на него не обижается
        (остальные совладельцы, если среди них есть не-старики, всё равно реагируют)."""
        if not other_creatures:
            return
        thief_is_child = getattr(thief, "life_stage", None) == LIFE_STAGE_CHILD
        for owner_id in self.owner_ids:
            owner = next((o for o in other_creatures if o.id == owner_id), None)
            if owner is None or owner.is_dead:
                continue
            if thief_is_child and owner.life_stage == LIFE_STAGE_OLD:
                continue
            owner.social.adjust_relationship(thief, STORAGE_THEFT_RELATIONSHIP_PENALTY)

    def is_owned_by_campfire(self, campfire_pos, tolerance=10):
        if self.campfire_pos is None:
            return True
        if campfire_pos is None:
            return False
        return math.hypot(self.campfire_pos[0] - campfire_pos[0],
                          self.campfire_pos[1] - campfire_pos[1]) < tolerance

    def draw(self, screen, screen_pos):
        sx, sy = int(screen_pos[0]), int(screen_pos[1])
        pygame.draw.circle(screen, STORAGE_FIELD_COLOR_BORDER, (sx, sy), self.radius, 3)

    def to_dict(self):
        return {
            "x": self.x, "y": self.y,
            "fruits": self.fruits, "water": self.water,
            "built_by": self.built_by,
            "owner_ids": list(self.owner_ids),
            "campfire_pos": list(self.campfire_pos) if self.campfire_pos else None,
            "created": self.created,
            "id": self.id,
        }

    @staticmethod
    def from_dict(data):
        owner_ids = data.get("owner_ids")
        if owner_ids is None:
            # ---------- Миграция старых сохранений: единственный известный строитель становится владельцем ----------
            legacy_builder = data.get("built_by")
            owner_ids = [legacy_builder] if legacy_builder else []
        field = StorageField(
            data["x"], data["y"],
            owner_campfire_pos=tuple(data["campfire_pos"]) if data.get("campfire_pos") else None,
            owner_ids=owner_ids,
        )
        field.fruits = data.get("fruits", 0)
        field.water = data.get("water", 0)
        field.built_by = data.get("built_by")
        field.created = data.get("created", time.time())
        field.id = data.get("id", field.id)
        return field

class Graveyard:
    def __init__(self, x, y, name=None, graveyard_id=None):
        self.id = graveyard_id if graveyard_id else str(uuid.uuid4())[:8]
        self.x = x
        self.y = y
        self.width = GRAVEYARD_DEFAULT_SIZE[0]
        self.height = GRAVEYARD_DEFAULT_SIZE[1]
        self.name = name if name else INFO_GRAVEYARD_DEFAULT_NAME
        self.created = time.time()

        self.archive = []
        self.records = []

    def get_type_name(self):
        return INFO_OBJECT_GRAVEYARD

    def distance_to_point(self, px, py):
        dx = max(self.x - self.width / 2 - px, 0, px - (self.x + self.width / 2))
        dy = max(self.y - self.height / 2 - py, 0, py - (self.y + self.height / 2))
        return math.hypot(dx, dy)

    def bury(self, creature):
        self.archive.append({"id": creature.id, "name": creature.name, "gender": creature.gender})
        self.records.append({
            "id": creature.id,
            "name": creature.name,
            "gender": creature.gender,
            "temperament": creature.temperament,
            "age": creature.age,
            "death_cause": creature.death_cause,
            "time_since_burial": 0.0,
        })

    def update(self, dt):
        for rec in self.records:
            rec["time_since_burial"] = rec.get("time_since_burial", 0.0) + dt
        self.prune_expired_records()

    def get_fresh_record(self, creature_id):
        rec = next((r for r in self.records if r["id"] == creature_id), None)
        if rec is None:
            return None
        if rec.get("time_since_burial", 0.0) > GRAVEYARD_DATA_RETENTION:
            return None
        return rec

    def prune_expired_records(self):
        self.records = [r for r in self.records if r.get("time_since_burial", 0.0) <= GRAVEYARD_DATA_RETENTION]

    def draw(self, screen, screen_pos):
        sx, sy = int(screen_pos[0]), int(screen_pos[1])
        rect = pygame.Rect(sx - self.width // 2, sy - self.height // 2, self.width, self.height)
        pygame.draw.rect(screen, GRAVEYARD_COLOR_FILL, rect)
        pygame.draw.rect(screen, GRAVEYARD_COLOR_BORDER, rect, GRAVEYARD_BORDER_THICKNESS)

    def to_dict(self):
        return {
            "id": self.id, "x": self.x, "y": self.y, "name": self.name,
            "created": self.created, "archive": self.archive, "records": self.records,
        }

    @staticmethod
    def from_dict(data):
        gy = Graveyard(data["x"], data["y"], name=data.get("name"), graveyard_id=data.get("id"))
        gy.created = data.get("created", time.time())
        gy.archive = data.get("archive", [])
        gy.records = data.get("records", [])
        return gy


class ConstructionSite:
    def __init__(self, x, y, build_type, campfire_pos=None, site_id=None):
        self.id = site_id if site_id else str(uuid.uuid4())[:8]
        self.x = x
        self.y = y
        self.build_type = build_type  # "campfire" | "storage" | "graveyard"
        self.width, self.height = CONSTRUCTION_SITE_SIZE.get(build_type, (40, 40))

        req = BUILDING_REQUIREMENTS[build_type]
        self.required_wood = req["wood"]
        self.required_stone = req["stone"]
        self.build_time = req["build_time"]

        self.deposited_wood = 0
        self.deposited_stone = 0
        self.build_progress = 0.0
        self.is_building = False
        self.builder_ids = set()
        self.contributor_ids = set()
        self.campfire_pos = campfire_pos
        self.created = time.time()

    def get_type_name(self):
        return INFO_OBJECT_CONSTRUCTION_SITE

    def resources_complete(self):
        return self.deposited_wood >= self.required_wood and self.deposited_stone >= self.required_stone

    def needed(self, res_type):
        if res_type == "wood":
            return max(0, self.required_wood - self.deposited_wood)
        if res_type == "stone":
            return max(0, self.required_stone - self.deposited_stone)
        return 0

    def draw(self, screen, screen_pos):
        sx, sy = int(screen_pos[0]), int(screen_pos[1])
        ready = self.resources_complete()
        color = CONSTRUCTION_SITE_COLOR_READY if ready else CONSTRUCTION_SITE_COLOR_INCOMPLETE
        rect = pygame.Rect(sx - self.width // 2, sy - self.height // 2, self.width, self.height)
        pygame.draw.rect(screen, color, rect, CONSTRUCTION_SITE_BORDER_THICKNESS)

        if self.is_building and self.build_time > 0:
            ratio = max(0.0, min(1.0, self.build_progress / self.build_time))
            fill_rect = pygame.Rect(rect.x, rect.bottom + 3, int(self.width * ratio), 5)
            pygame.draw.rect(screen, color, fill_rect)

    def to_dict(self):
        return {
            "id": self.id, "x": self.x, "y": self.y, "build_type": self.build_type,
            "deposited_wood": self.deposited_wood, "deposited_stone": self.deposited_stone,
            "build_progress": self.build_progress, "is_building": self.is_building,
            "campfire_pos": list(self.campfire_pos) if self.campfire_pos else None,
            "created": self.created,
        }

    @staticmethod
    def from_dict(data):
        site = ConstructionSite(
            data["x"], data["y"], data["build_type"],
            campfire_pos=tuple(data["campfire_pos"]) if data.get("campfire_pos") else None,
            site_id=data.get("id"))
        site.deposited_wood = data.get("deposited_wood", 0)
        site.deposited_stone = data.get("deposited_stone", 0)
        site.build_progress = data.get("build_progress", 0.0)
        site.is_building = data.get("is_building", False)
        site.created = data.get("created", time.time())
        return site


class ChildRoad(PolylineRoad):

    def __init__(self, points=None, road_id=None):
        super().__init__(points=points, road_id=road_id)
        self.rating = "pending"
        self.checked_by = None
        self.verifier_id = None

    def get_type_name(self):
        return INFO_OBJECT_CHILD_ROAD

    def verify_safety(self, spikes):
        points = self.points
        if len(points) < 2:
            if not points:
                return True
            px, py = points[0]
            return all(
                math.hypot(s.x - px, s.y - py) >= CHILD_ROAD_SAFETY_CHECK_RADIUS
                for s in spikes
            )
        for i in range(len(points) - 1):
            ax, ay = points[i]
            bx, by = points[i + 1]
            for spike in spikes:
                if geometry.point_segment_distance(spike.x, spike.y, ax, ay, bx, by) < CHILD_ROAD_SAFETY_CHECK_RADIUS:
                    return False
        return True

    def draw(self, screen, camera):
        if len(self.points) < 2:
            return
        if self.rating == "safe":
            color = CHILD_ROAD_COLOR_SAFE
        elif self.rating == "dangerous":
            color = CHILD_ROAD_COLOR_DANGEROUS
        else:
            color = CHILD_ROAD_COLOR_PENDING
        screen_points = [camera.apply_pos(p) for p in self.points]
        pygame.draw.lines(screen, color, False, screen_points, 3)

    def to_dict(self):
        return {
            "id": self.id, "points": self.points, "rating": self.rating,
            "checked_by": self.checked_by, "created": self.created,
        }

    @staticmethod
    def from_dict(data):
        croad = ChildRoad(points=[tuple(p) for p in data.get("points", [])], road_id=data.get("id"))
        croad.rating = data.get("rating", "pending")
        croad.checked_by = data.get("checked_by")
        croad.created = data.get("created", time.time())
        return croad

class House:
    """Жилой дом. Пока только хранит данные (вместимость, внешность) -
    подключение к сну/защите/рождению детей будет добавлено отдельно,
    когда появятся соответствующие механики."""

    def __init__(self, x, y, capacity=None, owner_ids=None, house_id=None):
        self.id = house_id if house_id else str(uuid.uuid4())[:8]
        self.x = x
        self.y = y
        self.width, self.height = HOUSE_DEFAULT_SIZE
        # ---------- Вместимость "выбирает" самец-строитель в момент завершения стройки ----------
        self.capacity = capacity if capacity is not None else random.randint(
            HOUSE_MIN_RESIDENTS, HOUSE_MAX_RESIDENTS)
        self.owner_ids = set(owner_ids) if owner_ids else set()
        self.created = time.time()

        # ---------- Внешность фиксируется один раз при постройке ----------
        self.door_slot = random.choice(("left", "center", "right"))
        self.window_slots = self._roll_window_slots()

    def _roll_window_slots(self):
        free_slots = [slot for slot in ("left", "center", "right") if slot != self.door_slot]
        if random.random() < 0.5:
            return [random.choice(free_slots)]
        return list(free_slots)

    def get_type_name(self):
        return INFO_OBJECT_HOUSE

    def distance_to_point(self, px, py):
        dx = max(self.x - self.width / 2 - px, 0, px - (self.x + self.width / 2))
        dy = max(self.y - self.height / 2 - py, 0, py - (self.y + self.height / 2))
        return math.hypot(dx, dy)

    def _slot_positions(self, wall_rect):
        slot_width = self.width / 3
        return {
            "left": wall_rect.x + slot_width / 2,
            "center": wall_rect.x + slot_width * 1.5,
            "right": wall_rect.x + slot_width * 2.5,
        }

    def draw(self, screen, screen_pos):
        sx, sy = int(screen_pos[0]), int(screen_pos[1])
        half_w, half_h = self.width // 2, self.height // 2

        wall_rect = pygame.Rect(sx - half_w, sy - half_h, self.width, self.height)
        pygame.draw.rect(screen, HOUSE_COLOR_WALL, wall_rect)
        pygame.draw.rect(screen, HOUSE_COLOR_WALL_BORDER, wall_rect, 2)

        roof_points = [
            (sx - half_w - 6, sy - half_h),
            (sx + half_w + 6, sy - half_h),
            (sx, sy - half_h - HOUSE_ROOF_HEIGHT),
        ]
        pygame.draw.polygon(screen, HOUSE_COLOR_ROOF, roof_points)
        pygame.draw.polygon(screen, HOUSE_COLOR_ROOF_BORDER, roof_points, 2)

        slot_x = self._slot_positions(wall_rect)
        self._draw_door(screen, slot_x[self.door_slot], wall_rect)
        for slot in self.window_slots:
            self._draw_window(screen, slot_x[slot], wall_rect)

    def _draw_door(self, screen, center_x, wall_rect):
        door_w, door_h = 18, int(wall_rect.height * 0.65)
        door_rect = pygame.Rect(0, 0, door_w, door_h)
        door_rect.midbottom = (int(center_x), wall_rect.bottom)
        pygame.draw.rect(screen, HOUSE_COLOR_DOOR, door_rect)
        pygame.draw.rect(screen, HOUSE_COLOR_DOOR_BORDER, door_rect, 2)
        pygame.draw.circle(screen, HOUSE_COLOR_DOOR_HANDLE, (door_rect.right - 4, door_rect.centery), 2)

    def _draw_window(self, screen, center_x, wall_rect):
        size = 16
        rect = pygame.Rect(0, 0, size, size)
        rect.center = (int(center_x), wall_rect.centery)
        pygame.draw.rect(screen, HOUSE_COLOR_WINDOW, rect)
        pygame.draw.rect(screen, HOUSE_COLOR_WINDOW_BORDER, rect, 2)
        pygame.draw.line(screen, HOUSE_COLOR_WINDOW_BORDER, (rect.centerx, rect.top), (rect.centerx, rect.bottom), 2)
        pygame.draw.line(screen, HOUSE_COLOR_WINDOW_BORDER, (rect.left, rect.centery), (rect.right, rect.centery), 2)

    def to_dict(self):
        return {
            "id": self.id, "x": self.x, "y": self.y,
            "capacity": self.capacity, "owner_ids": list(self.owner_ids),
            "door_slot": self.door_slot, "window_slots": self.window_slots,
            "created": self.created,
        }

    @staticmethod
    def from_dict(data):
        house = House(data["x"], data["y"], capacity=data.get("capacity"),
                      owner_ids=data.get("owner_ids"), house_id=data.get("id"))
        house.door_slot = data.get("door_slot", house.door_slot)
        house.window_slots = data.get("window_slots", house.window_slots)
        house.created = data.get("created", time.time())
        return house