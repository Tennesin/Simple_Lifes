import json
import time
import math
import random

from settings import INTUITIVE_DECAY_TIME

class Memory:
    _BUCKET_NEAR, _BUCKET_MEDIUM, _BUCKET_FAR = "near", "medium", "far"
    _BUCKET_DISTANCE_VALUE = {_BUCKET_NEAR: 200, _BUCKET_MEDIUM: 550, _BUCKET_FAR: 1100}

    def __init__(self):
        self.memories = []
        self._memories_by_type = {}
        self.decay_time = 120

        self.intuitive_memories = []
        self.intuitive_decay_time = INTUITIVE_DECAY_TIME

        self._prune_timer = 0.0
        self._prune_interval = 45.0

        self._position_cache = {}
        self._version = 0

    def maybe_prune(self, dt):
        self._prune_timer += dt
        if self._prune_timer < self._prune_interval:
            return
        self._prune_timer = 0.0

        now = time.time()
        self.memories = [m for m in self.memories if now - m["timestamp"] < self.decay_time]
        self._memories_by_type = {}
        for m in self.memories:
            self._memories_by_type.setdefault(m["type"], []).append(m)

        self.intuitive_memories = [
            m for m in self.intuitive_memories
            if now - m["timestamp"] < self.intuitive_decay_time
        ]
        self._version += 1   # НОВОЕ

    # ---------- Точная память ----------

    def add_memory(self, mem_type, x, y, importance=1.0):
        bucket = self._memories_by_type.setdefault(mem_type, [])
        for mem in bucket:
            if abs(mem["x"] - x) < 5 and abs(mem["y"] - y) < 5:
                if abs(importance) > abs(mem["importance"]):
                    mem["importance"] = importance
                mem["timestamp"] = time.time()
                self._version += 1
                return
        entry = {
            "type": mem_type,
            "x": x,
            "y": y,
            "importance": importance,
            "timestamp": time.time()
        }
        self.memories.append(entry)
        bucket.append(entry)
        self._version += 1

    def _get_positions(self, mem_type, allow_negative=False):
        now = time.time()
        cached = self._position_cache.get(mem_type)
        if cached is not None:
            version, cache_time, positions = cached
            if version == self._version and now - cache_time < 0.5:
                return positions

        result = []
        for mem in self._memories_by_type.get(mem_type, []):
            age = now - mem["timestamp"]
            decay_factor = max(0.0, 1 - age / self.decay_time)
            effective_imp = mem["importance"] * decay_factor
            if abs(effective_imp) > 0.1:
                result.append((mem["x"], mem["y"]))

        self._position_cache[mem_type] = (self._version, now, result)
        return result

    def get_food_memories(self):
        return self._get_positions("fruit")

    def get_water_memories(self):
        return self._get_positions("water")

    def get_danger_memories(self):
        return self._get_positions("spike", allow_negative=True)

    def forget_memory(self, mem_type, x, y, radius=8):
        def _keep(m):
            return not (m["type"] == mem_type and abs(m["x"] - x) < radius and abs(m["y"] - y) < radius)
        self.memories = [m for m in self.memories if _keep(m)]
        if mem_type in self._memories_by_type:
            self._memories_by_type[mem_type] = [m for m in self._memories_by_type[mem_type] if _keep(m)]
        self._version += 1

    def get_campfire_memories(self):
        return self._get_positions("campfire")

    def get_graveyard_memories(self):
        return self._get_positions("graveyard")

    def get_best_memory(self, mem_type, allow_negative=False):
        now = time.time()
        best = None
        best_score = 0.1
        for mem in self._memories_by_type.get(mem_type, []):
            age = now - mem["timestamp"]
            decay_factor = max(0.0, 1 - age / self.decay_time)
            effective_imp = mem["importance"] * decay_factor
            score = abs(effective_imp) if allow_negative else effective_imp
            if score > best_score:
                best_score = score
                best = (mem["x"], mem["y"], effective_imp)
        return best

    # ---------- Интуитивная (нечёткая) память ----------

    @staticmethod
    def _compass_sector(dx, dy):
        """Индекс сектора 0..7 (шаг 45°), а не локализованная строка."""
        angle = math.degrees(math.atan2(-dy, dx)) % 360
        return int((angle + 22.5) // 45) % 8

    @staticmethod
    def _distance_bucket(dist):
        if dist < 300:
            return Memory._BUCKET_NEAR
        elif dist < 900:
            return Memory._BUCKET_MEDIUM
        else:
            return Memory._BUCKET_FAR

    def add_intuitive_memory(self, mem_type, origin_x, origin_y, target_x, target_y, importance=1.0):
        dx, dy = target_x - origin_x, target_y - origin_y
        dist = math.hypot(dx, dy)
        if dist < 10:
            return
        sector = self._compass_sector(dx, dy)
        bucket = self._distance_bucket(dist)
        for mem in self.intuitive_memories:
            if mem["type"] == mem_type and mem["direction"] == sector and mem["distance_bucket"] == bucket:
                mem["importance"] = max(mem["importance"], importance)
                mem["timestamp"] = time.time()
                mem["origin_x"] = origin_x
                mem["origin_y"] = origin_y
                return
        self.intuitive_memories.append({
            "type": mem_type,
            "direction": sector,
            "distance_bucket": bucket,
            "importance": importance,
            "timestamp": time.time(),
            "origin_x": origin_x,
            "origin_y": origin_y,
        })

    def get_intuitive_target(self, mem_type, origin_x, origin_y):
        now = time.time()
        best = None
        best_imp = 0.1
        for mem in self.intuitive_memories:
            if mem["type"] != mem_type:
                continue
            age = now - mem["timestamp"]
            effective_imp = mem["importance"] * (1 - age / self.intuitive_decay_time)
            if effective_imp > best_imp:
                best_imp = effective_imp
                best = mem
        if not best:
            return None

        base_dist = self._BUCKET_DISTANCE_VALUE.get(best["distance_bucket"], 550)
        sector = best["direction"]
        # ---------- Защита от старых сохранений, где direction был строкой ----------
        if not isinstance(sector, int):
            sector = 0
        angle = math.radians(sector * 45 + random.uniform(-18, 18))
        dist = base_dist * random.uniform(0.8, 1.2)
        anchor_x = best.get("origin_x", origin_x)
        anchor_y = best.get("origin_y", origin_y)
        tx = anchor_x + math.cos(angle) * dist
        ty = anchor_y - math.sin(angle) * dist
        return (tx, ty)

    def get_bush_intuitive_target(self, origin_x, origin_y):
        return self.get_intuitive_target("bush", origin_x, origin_y)

    def get_water_intuitive_target(self, origin_x, origin_y):
        return self.get_intuitive_target("water", origin_x, origin_y)

    def get_campfire_intuitive_target(self, origin_x, origin_y):
        return self.get_intuitive_target("campfire", origin_x, origin_y)

    # ---------- Сохранение/загрузка ----------

    def save(self, path):
        with open(path, 'w', encoding="utf-8") as f:
            json.dump({
                "memories": self.memories,
                "intuitive_memories": self.intuitive_memories,
            }, f, indent=2)

    def load(self, path):
        with open(path, 'r', encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            self.memories = data
            self.intuitive_memories = []
        else:
            self.memories = data.get("memories", [])
            self.intuitive_memories = data.get("intuitive_memories", [])
        self._memories_by_type = {}
        for m in self.memories:
            self._memories_by_type.setdefault(m["type"], []).append(m)