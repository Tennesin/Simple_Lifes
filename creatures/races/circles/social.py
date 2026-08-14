from .ci_settings import *
from ...all_needed import geometry

class CreatureSocial:
    def __init__(self, creature):
        self.c = creature

    def get_relationship(self, other):
        return self.c.relationships.get(other.id, 0.0)

    def adjust_relationship(self, other, delta):
        c = self.c
        current = c.relationships.get(other.id, 0.0)
        c.relationships[other.id] = geometry.clamp(current + delta, -100.0, 100.0)

    def adjust_mutual_relationship(self, other, delta_self, delta_other=None):
        if delta_other is None:
            delta_other = delta_self
        self.adjust_relationship(other, delta_self)
        other.social.adjust_relationship(self.c, delta_other)

    def companion_score(self, other) -> float:
        c = self.c
        rel = self.get_relationship(other)
        return c.distance_to(other) - rel * RELATIONSHIP_COMPANION_WEIGHT

    def best_companion(self, companions):
        if not companions:
            return None
        return min(companions, key=self.companion_score)

    def mate_attractiveness_bonus(self, candidate, storage_fields):
        c = self.c
        if c.gender != GENDER_FEMALE or candidate.gender != GENDER_MALE or not storage_fields:
            return 0.0
        is_provider = any(
            candidate.id in field.owner_ids
            and field.fruits >= STORAGE_ATTRACTIVENESS_MIN_FRUITS
            and field.water >= STORAGE_ATTRACTIVENESS_MIN_WATER
            for field in storage_fields
        )
        return MATE_STORAGE_ATTRACTIVENESS_BONUS if is_provider else 0.0

    def pairing_score(self, other, storage_fields=None):
        score = self.companion_score(other)
        if storage_fields:
            score -= self.mate_attractiveness_bonus(other, storage_fields)
        return score

    def request_company(self, point):
        c = self.c
        c.social_request_timer = SOCIAL_REQUEST_HOLD_TIME
        c.social_request_point = point

class CreatureCommunication:
    def __init__(self, creature):
        self.c = creature

    def share_information(self, other):
        c = self.c
        relationship = c.social.get_relationship(other)

        if relationship >= SHARE_RESOURCE_MIN_RELATIONSHIP:
            self._share_memory_type(other, "fruit")
            self._share_memory_type(other, "water")
            self._share_memory_type(other, "campfire")
            self._share_bush_hint(other)
            self._share_road_links(other)

        # Опасности передаются вне зависимости от отношений — инстинкт сильнее неприязни
        self._share_danger_memory(other)
        self._share_road_knowledge(other)

    # ---------- Точные ориентиры (еда/вода/костёр) ----------

    def _share_memory_type(self, other, mem_type):
        c = self.c
        best = other.memory.get_best_memory(mem_type)
        if best is None:
            return
        x, y, importance = best
        shared_importance = importance * SHARE_IMPORTANCE_FACTOR
        c.memory.add_memory(mem_type, x, y, importance=shared_importance)
        c.memory.add_intuitive_memory(mem_type, *c.comfort_point, x, y, importance=shared_importance)
        if mem_type in c.knowledge:
            c.knowledge[mem_type] = True
        if mem_type == "campfire" and c.known_campfire is None:
            c.known_campfire = (x, y)

    # ---------- Куст (только нечёткая память, точной для него нет) ----------

    def _share_bush_hint(self, other):
        c = self.c
        target = other.memory.get_intuitive_target("bush", *other.comfort_point)
        if target is None:
            return
        ox, oy = other.comfort_point
        c.memory.add_intuitive_memory("bush", ox, oy, target[0], target[1], importance=1.0)
        c.knowledge["bush"] = True

    # ---------- Соединения: маршруты до ресурсов через дорожную сеть ----------

    def _share_road_links(self, other):
        c = self.c
        for resource, link in other.known_road_links.items():
            if resource not in c.known_road_links:
                c.known_road_links[resource] = dict(link)

    # ---------- Опасность (шипы) ----------

    def _share_danger_memory(self, other):
        c = self.c
        best = other.memory.get_best_memory("spike", allow_negative=True)
        if best is None:
            return
        x, y, importance = best
        c.memory.add_memory("spike", x, y, importance=importance * SHARE_IMPORTANCE_FACTOR)
        c.knowledge["spike"] = True

    # ---------- Дороги ----------

    _ROAD_VERDICT_PRIORITY = {"dangerous": 2, "useful": 1, "useless": 0}

    def _share_road_knowledge(self, other):
        c = self.c
        for road_id, verdict in other.known_roads.items():
            current = c.known_roads.get(road_id)
            if current == verdict:
                continue
            if self._ROAD_VERDICT_PRIORITY.get(verdict, -1) > self._ROAD_VERDICT_PRIORITY.get(current, -1):
                c.known_roads[road_id] = verdict