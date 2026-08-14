"""Реестр родословной расы 'Круг'."""

import json
import os
from ..genealogy import GenealogyRegistry

class GenealogyRegistry:

    def __init__(self):
        # id -> {"name", "gender", "parent_ids": [mother_id, father_id]|None,
        #        "partner_ids": [id, ...], "is_dead": bool}
        self.records = {}

    # ---------- Регистрация / обновление ----------

    def register_creature(self, creature):
        if creature.id in self.records:
            return
        self.records[creature.id] = {
            "name": creature.name,
            "gender": creature.gender,
            "parent_ids": list(creature.parent_ids) if creature.parent_ids else None,
            "partner_ids": [],
            "is_dead": creature.is_dead,
        }

    def update_name(self, creature_id, name):
        rec = self.records.get(creature_id)
        if rec is not None:
            rec["name"] = name

    def register_pair(self, id_a, id_b):
        rec_a = self.records.get(id_a)
        rec_b = self.records.get(id_b)
        if rec_a is not None and id_b not in rec_a["partner_ids"]:
            rec_a["partner_ids"].append(id_b)
        if rec_b is not None and id_a not in rec_b["partner_ids"]:
            rec_b["partner_ids"].append(id_a)

    def mark_dead(self, creature_id, creature=None):
        rec = self.records.get(creature_id)
        if rec is None and creature is not None:
            self.register_creature(creature)
            rec = self.records.get(creature_id)
        if rec is not None:
            rec["is_dead"] = True

    # ---------- Запросы ----------

    def get(self, creature_id):
        return self.records.get(creature_id)

    def children_of(self, creature_id):
        return [cid for cid, rec in self.records.items()
                if rec["parent_ids"] and creature_id in rec["parent_ids"]]

    def partners_of(self, creature_id):
        rec = self.records.get(creature_id)
        return list(rec["partner_ids"]) if rec else []

    # ---------- Сохранение ----------

    def to_dict(self):
        return self.records

    @staticmethod
    def from_dict(data):
        reg = GenealogyRegistry()
        reg.records = data or {}
        for rec in reg.records.values():
            rec.setdefault("partner_ids", [])
        return reg

    def save(self, world_path):
        with open(os.path.join(world_path, "genealogy.json"), "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    def load(self, world_path):
        path = os.path.join(world_path, "genealogy.json")
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        loaded = GenealogyRegistry.from_dict(data)
        self.records = loaded.records