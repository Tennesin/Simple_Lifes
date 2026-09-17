"""Алгоритм раскладки древа родословной: строит координаты узлов
(x, generation) и список рёбер по записям GenealogyRegistry."""

from ......all_needed import geometry
from ....ci_settings import (
    GENEALOGY_MAX_DEPTH, GENEALOGY_SLOT_WIDTH, GENEALOGY_ROW_HEIGHT, GENEALOGY_PARTNER_OFFSET,
    GENEALOGY_MIN_NODE_GAP, GENEALOGY_CROSS_RESERVED_WIDTH, GENEALOGY_CROSS_LINE_CLEARANCE,
    GENEALOGY_NODE_RADIUS,
)
from ....ci_info import INFO_GENEALOGY_UNKNOWN


class GenealogyLayoutBuilder:
    """Единственная задача - превратить (registry, root_id, живые существа)
    в (nodes_list, edges, bbox). name_font нужен только для расчёта
    горизонтального зазора между узлами по ширине текста имени."""

    def __init__(self, name_font):
        self.name_font = name_font

    # ---------- Точка входа ----------

    def build(self, registry, root_id, live_creatures):
        if registry is None or root_id is None or registry.get(root_id) is None:
            return [], [], (0, 0, 0, 0)

        ancestor_nodes, ancestor_edges = self._build_ancestors(registry, root_id)
        descendant_nodes, descendant_edges = self._build_descendants(registry, root_id)

        root_rec = registry.get(root_id)
        parent_ids = root_rec["parent_ids"] or []
        direct_parent_xs = [ancestor_nodes[pid]["x"] for pid in parent_ids
                            if pid is not None and pid in ancestor_nodes]
        if direct_parent_xs:
            shift = -sum(direct_parent_xs) / len(direct_parent_xs)
            for node in ancestor_nodes.values():
                node["x"] += shift

        direct_children_ids = registry.children_of(root_id)
        direct_child_xs = [descendant_nodes[cid]["x"] for cid in direct_children_ids
                           if cid in descendant_nodes]
        if direct_child_xs:
            shift = -sum(direct_child_xs) / len(direct_child_xs)
            for node in descendant_nodes.values():
                node["x"] += shift

        all_nodes = {root_id: {"id": root_id, "generation": 0, "x": 0.0, "is_root": True}}
        all_nodes.update(ancestor_nodes)
        all_nodes.update(descendant_nodes)
        all_edges = [(a, b, "blood") for a, b in ancestor_edges + descendant_edges]

        for node in list(all_nodes.values()):
            partner_id = self._display_partner_id(registry, node["id"], live_creatures)
            if partner_id is None or partner_id in all_nodes or registry.get(partner_id) is None:
                continue
            key = partner_id + "::partner_of::" + node["id"]
            all_nodes[key] = {
                "id": partner_id, "generation": node["generation"],
                "x": node["x"] + GENEALOGY_PARTNER_OFFSET / GENEALOGY_SLOT_WIDTH,
                "is_root": False,
            }
            all_edges.append((node["id"], partner_id, "partner"))

        self._resolve_overlaps(all_nodes, registry)
        self._resolve_cross_line_overlaps(list(all_nodes.values()), all_edges, registry)
        self._resolve_overlaps(all_nodes, registry)

        nodes_list = list(all_nodes.values())
        if not nodes_list:
            bbox = (0, 0, 0, 0)
        else:
            xs = [n["x"] for n in nodes_list]
            gens = [n["generation"] for n in nodes_list]
            bbox = (min(xs), max(xs), min(gens), max(gens))

        return nodes_list, all_edges, bbox

    # ---------- Предки (бинарно, пост-order) ----------

    def _build_ancestors(self, registry, root_id):
        nodes = {}
        edges = []
        counter = [0]

        def assign(cid, generation):
            if cid is None or generation > GENEALOGY_MAX_DEPTH:
                return None
            rec = registry.get(cid)
            if rec is None:
                return None
            parent_ids = rec["parent_ids"]
            mother_x = father_x = None
            if parent_ids and generation < GENEALOGY_MAX_DEPTH:
                mother_id = parent_ids[0] if len(parent_ids) > 0 else None
                father_id = parent_ids[1] if len(parent_ids) > 1 else None
                mother_x = assign(mother_id, generation + 1)
                father_x = assign(father_id, generation + 1)

            if mother_x is not None and father_x is not None:
                x = (mother_x + father_x) / 2
            elif mother_x is not None:
                x = mother_x
            elif father_x is not None:
                x = father_x
            else:
                x = float(counter[0])
                counter[0] += 1

            nodes[cid] = {"id": cid, "generation": -generation, "x": x, "is_root": generation == 0}
            if mother_x is not None:
                edges.append((parent_ids[0], cid))
            if father_x is not None:
                edges.append((parent_ids[1], cid))
            return x

        assign(root_id, 0)
        nodes.pop(root_id, None)
        return nodes, edges

    # ---------- Потомки (n-арно, пост-order) ----------

    def _build_descendants(self, registry, root_id):
        nodes = {}
        edges = []
        counter = [0]

        def assign(cid, generation):
            rec = registry.get(cid)
            if rec is None:
                return None
            children = registry.children_of(cid) if generation < GENEALOGY_MAX_DEPTH else []
            if children:
                child_xs = []
                for child_id in children:
                    cx = assign(child_id, generation + 1)
                    if cx is not None:
                        child_xs.append(cx)
                        edges.append((cid, child_id))
                x = sum(child_xs) / len(child_xs) if child_xs else float(counter[0])
                if not child_xs:
                    counter[0] += 1
            else:
                x = float(counter[0])
                counter[0] += 1

            if generation > 0:
                nodes[cid] = {"id": cid, "generation": generation, "x": x, "is_root": False}
            return x

        assign(root_id, 0)
        return nodes, edges

    # ---------- Партнёр: только текущий/последний известный, без своей ветки ----------

    def _display_partner_id(self, registry, creature_id, live_creatures):
        live = next((c for c in live_creatures if c.id == creature_id and not c.is_dead), None)
        if live is not None and live.partner_id is not None:
            return live.partner_id
        partners = registry.partners_of(creature_id)
        return partners[-1] if partners else None

    # ---------- Разрешение перекрытий: раздвигаем круги одного поколения, если они соприкасаются ----------

    def _resolve_overlaps(self, nodes_dict, registry):
        nodes = list(nodes_dict.values())
        extents = {id(node): self._node_extents(registry, node) for node in nodes}

        by_generation = {}
        for node in nodes:
            by_generation.setdefault(node["generation"], []).append(node)

        for group in by_generation.values():
            if len(group) < 2:
                continue
            group.sort(key=lambda n: n["x"])
            for _ in range(len(group) * 2 + 2):
                changed = False
                for i in range(1, len(group)):
                    prev_node, cur_node = group[i - 1], group[i]
                    prev_left, prev_right = extents[id(prev_node)]
                    cur_left, cur_right = extents[id(cur_node)]
                    min_gap_px = prev_right + cur_left + GENEALOGY_MIN_NODE_GAP
                    min_gap = min_gap_px / GENEALOGY_SLOT_WIDTH
                    overlap = min_gap - (cur_node["x"] - prev_node["x"])
                    if overlap > 0:
                        shift = overlap / 2
                        prev_node["x"] -= shift
                        cur_node["x"] += shift
                        changed = True
                if not changed:
                    break

    def _local_pos(self, node):
        return node["x"] * GENEALOGY_SLOT_WIDTH, node["generation"] * GENEALOGY_ROW_HEIGHT

    def _node_extents(self, registry, node):
        rec = registry.get(node["id"]) if registry else None
        name = (rec["name"] if rec and rec["name"] else node["id"]) if rec else INFO_GENEALOGY_UNKNOWN
        is_dead = bool(rec and rec.get("is_dead"))

        name_half_width = self.name_font.size(name)[0] / 2.0
        base = max(GENEALOGY_NODE_RADIUS, name_half_width) + 4

        left_extent = base
        if is_dead:
            left_extent = max(left_extent, GENEALOGY_NODE_RADIUS + GENEALOGY_CROSS_RESERVED_WIDTH)
        right_extent = base
        return left_extent, right_extent

    def _resolve_cross_line_overlaps(self, nodes_list, edges, registry, iterations=4):
        by_id = {}
        for node in nodes_list:
            by_id.setdefault(node["id"], node)

        dead_nodes = []
        for node in nodes_list:
            rec = registry.get(node["id"]) if registry else None
            if rec and rec.get("is_dead"):
                dead_nodes.append(node)
        if not dead_nodes:
            return

        for _ in range(iterations):
            changed = False
            for node in dead_nodes:
                nx, ny = self._local_pos(node)
                cross_x = nx - GENEALOGY_NODE_RADIUS - 12
                cross_y = ny

                for a_id, b_id, _kind in edges:
                    node_a, node_b = by_id.get(a_id), by_id.get(b_id)
                    if node_a is None or node_b is None or node_a is node or node_b is node:
                        continue
                    ax, ay = self._local_pos(node_a)
                    bx, by_ = self._local_pos(node_b)
                    dist = geometry.point_segment_distance(cross_x, cross_y, ax, ay, bx, by_)
                    if dist < GENEALOGY_CROSS_LINE_CLEARANCE:
                        node["x"] += (GENEALOGY_CROSS_LINE_CLEARANCE - dist) / GENEALOGY_SLOT_WIDTH * 0.6
                        changed = True
            if not changed:
                break