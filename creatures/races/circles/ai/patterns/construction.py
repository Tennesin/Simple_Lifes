import math
import random

from settings import *
from ...ci_settings import *
from ...ci_info import *
from .....all_needed import geometry
from .....all_needed.ai.utility import Consideration, GoalComponent
from ...circle_objects import StorageField, Graveyard, ConstructionSite, House, Campfire

# =========================================================================
# Добыча ресурсов и строительство
# =========================================================================

class Construction(GoalComponent):
    SCORE_COMMITTED = 62.0
    SCORE_NEW = 42.0

    _BUILDING_FINAL_FOOTPRINT = {
        "campfire": 20,
        "storage": max(STORAGE_FIELD_WIDTH, STORAGE_FIELD_HEIGHT) / 2 + 8,
        "graveyard": max(GRAVEYARD_DEFAULT_SIZE) / 2 + 10,
        "house": max(HOUSE_DEFAULT_SIZE) / 2 + 10,
    }

    def __init__(self, creature, instincts, roads=None):
        self.c = creature
        self.instincts = instincts
        self.roads = roads

    def consider(self, ctx):
        c = self.c
        if c.gender != GENDER_MALE or c.life_stage != LIFE_STAGE_ADULT:
            return [None]
        if c.panic_active or c.fear_timer > 0 or c.is_sleeping:
            return [None]

        committed = c.construction_target_id is not None or c.gather_target_id is not None
        if not committed and c.needs.wellbeing_score() < PARENT_FEED_MIN_WELLBEING:
            return [None]

        score = self.SCORE_COMMITTED if committed else self.SCORE_NEW
        if c.puberty_active and not self._owns_any_storage(ctx.storage_fields):
            score += CONSTRUCTION_PUBERTY_DRIVE_BONUS

        def execute():
            return self._pursue(ctx)

        return [Consideration("construction", score, execute)]

    def _owns_any_storage(self, storage_fields):
        c = self.c
        return any(c.id in field.owner_ids for field in storage_fields)

    def _pursue(self, ctx):
        c = self.c

        if c.gather_target_id is not None:
            return self._continue_gathering(ctx)

        if c.construction_target_id is not None:
            site = next((s for s in ctx.construction_sites if s.id == c.construction_target_id), None)
            if site is not None:
                return self._work_on(site, ctx)
            c.construction_target_id = None
            c.construction_phase = None

        orphan_site = self._find_orphaned_site(ctx)
        if orphan_site is not None:
            c.construction_target_id = orphan_site.id
            c.construction_phase = "build" if orphan_site.is_building else "deposit"
            return self._work_on(orphan_site, ctx)

        help_goal = self._try_join_help(ctx)
        if help_goal is not None:
            return help_goal

        if c.construction_check_timer > 0:
            c.construction_check_timer -= ctx.dt
            return None
        c.construction_check_timer = random.uniform(*CONSTRUCTION_CHECK_INTERVAL)

        campfire_pos = c.known_campfire
        build_type = self._determine_need(campfire_pos, ctx)
        if build_type is None:
            return None

        site = self._find_or_create_site(build_type, campfire_pos, ctx)
        if site is None:
            return None
        c.construction_target_id = site.id
        c.construction_phase = "deposit"
        return self._work_on(site, ctx)

    # ---------- Добыча дерева/камня ----------

    def _find_gather_source(self, res_type, ctx):
        c = self.c
        pool = ctx.visible_trees if res_type == "wood" else ctx.visible_stones
        candidates = [o for o in pool if (o.has_wood() if res_type == "wood" else o.has_stone())]
        if not candidates:
            return None
        return min(candidates, key=c.distance_to)

    def _start_gathering(self, res_type, source, needed_amount=None):
        c = self.c
        c.gather_type = res_type
        c.gather_target_id = source.id
        c.gather_progress = 0.0
        c.gather_needed_amount = needed_amount

    def _cancel_gathering(self):
        c = self.c
        c.gather_target_id = None
        c.gather_type = None
        c.gather_progress = 0.0
        c.gather_needed_amount = None

    def _continue_gathering(self, ctx):
        c = self.c
        pool = ctx.all_trees if c.gather_type == "wood" else ctx.all_stones
        source = next((o for o in pool if o.id == c.gather_target_id), None)

        if source is None:
            self._cancel_gathering()
            return None

        has_resource = source.has_wood() if c.gather_type == "wood" else source.has_stone()
        if not has_resource or c.carry_free_space() <= 0:
            self._cancel_gathering()
            return None

        if (c.gather_needed_amount is not None
                and c.carried_resources[c.gather_type] >= c.gather_needed_amount):
            self._cancel_gathering()
            return None

        if c.distance_to(source) > GATHER_APPROACH_DISTANCE:
            c.state = STATE_SEEKING
            c.goal_text = (INFO_CREATURE_GOAL_GATHER_WOOD if c.gather_type == "wood"
                           else INFO_CREATURE_GOAL_GATHER_STONE)
            c.target = (source.x, source.y)
            return c.target

        c.state = STATE_SEEKING
        c.goal_text = (INFO_CREATURE_GOAL_GATHERING_WOOD if c.gather_type == "wood"
                       else INFO_CREATURE_GOAL_GATHERING_STONE)
        c.target = (c.x, c.y)

        c.gather_progress += ctx.dt
        tick = 1.0 / RESOURCE_GATHER_RATE
        while (c.gather_progress >= tick and c.carry_free_space() > 0 and has_resource
               and (c.gather_needed_amount is None
                    or c.carried_resources[c.gather_type] < c.gather_needed_amount)):
            c.gather_progress -= tick
            if c.gather_type == "wood":
                source.wood -= 1
            else:
                source.stone -= 1
            c.carried_resources[c.gather_type] += 1
            has_resource = source.has_wood() if c.gather_type == "wood" else source.has_stone()

        reached_needed = (c.gather_needed_amount is not None
                          and c.carried_resources[c.gather_type] >= c.gather_needed_amount)
        if not has_resource or c.carry_free_space() <= 0 or reached_needed:
            self._cancel_gathering()

        return c.target

    # ---------- Потребность и точка стройки ----------

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
                return None
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
        if house is not None and house.storage_field(ctx.storage_fields) is None:
            already_building_storage = any(
                s.build_type == "storage" and getattr(s, "storage_owner_id", None) == c.id
                for s in sites
            )
            if not already_building_storage:
                return "storage"

        if c.known_graveyard is None:
            linked = self._find_campfire_linked_graveyard(campfire_pos, ctx.graveyards)
            if linked is not None:
                c.known_graveyard = (linked.x, linked.y)
            elif not any(s.build_type == "graveyard" for s in sites):
                return "graveyard"
        return None

    def _find_campfire_linked_graveyard(self, campfire_pos, graveyards):
        if campfire_pos is None or not graveyards:
            return None
        for gy in graveyards:
            if math.hypot(gy.x - campfire_pos[0], gy.y - campfire_pos[1]) < GRAVEYARD_CAMPFIRE_LINK_RADIUS:
                return gy
        return None

    def _footprint_radius(self, build_type):
        return self._BUILDING_FINAL_FOOTPRINT.get(build_type, 30)

    def _point_clear(self, point, build_type, biome_grid, ctx, skip_house_id=None):
        px, py = point
        if biome_grid is not None and biome_grid.get_at(px, py) in (BIOME_SEA, BIOME_RIVER):
            return False

        footprint = self._footprint_radius(build_type) + CONSTRUCTION_CLEARANCE_MARGIN

        def _blocked(objects, radius_attr=None):
            for obj in objects:
                other_radius = getattr(obj, radius_attr, 0) if radius_attr else 0
                if math.hypot(px - obj.x, py - obj.y) < footprint + other_radius:
                    return True
            return False

        if _blocked(ctx.visible_fruits, "radius") or _blocked(ctx.visible_spikes, "radius"):
            return False
        if _blocked(ctx.visible_water, "radius") or _blocked(ctx.visible_bushes, "radius"):
            return False
        if _blocked(ctx.visible_trees, "radius") or _blocked(ctx.visible_stones, "radius"):
            return False
        if _blocked(ctx.campfires, "radius") or _blocked(ctx.storage_fields, "radius"):
            return False
        for gy in ctx.graveyards:
            if gy.distance_to_point(px, py) < footprint:
                return False
        for house in ctx.houses:
            if house.id == skip_house_id:
                continue
            house_radius = max(house.width, house.height) / 2
            if math.hypot(px - house.x, py - house.y) < footprint + house_radius:
                return False
        for site in ctx.construction_sites:
            site_radius = max(site.width, site.height) / 2
            if math.hypot(px - site.x, py - site.y) < footprint + site_radius:
                return False
        return True

    def _pick_point(self, build_type, campfire_pos, biome_grid, ctx, attempts=20):
        c = self.c
        if build_type == "campfire":
            return self._pick_new_campfire_point(ctx, attempts=max(attempts, 30))
        if build_type == "house":
            return self._pick_house_point(campfire_pos, biome_grid, ctx)
        if build_type == "storage":
            return self._pick_storage_point(ctx)

        anchor = campfire_pos if campfire_pos is not None else (c.x, c.y)
        dist_range = GRAVEYARD_BUILD_OFFSET_RANGE
        for _ in range(attempts):
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(*dist_range)
            point = geometry.clamped_point(anchor[0], anchor[1], angle, dist)
            if self._point_clear(point, build_type, biome_grid, ctx):
                return point
        return None

    def _pick_house_point(self, campfire_pos, biome_grid, ctx):
        c = self.c
        anchor = campfire_pos if campfire_pos is not None else (c.x, c.y)
        best_point, best_score = None, None
        for _ in range(HOUSE_SITE_SCORE_ATTEMPTS):
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(*HOUSE_BUILD_OFFSET_RANGE)
            point = geometry.clamped_point(anchor[0], anchor[1], angle, dist)
            if not self._point_clear(point, "house", biome_grid, ctx):
                continue
            score = self._score_house_site(point, campfire_pos, biome_grid, ctx)
            if best_score is None or score > best_score:
                best_score, best_point = score, point
        return best_point

    def _score_house_site(self, point, campfire_pos, biome_grid, ctx):
        px, py = point
        score = 0.0
        biome = biome_grid.get_at(px, py) if biome_grid is not None else BIOME_PLAINS
        if biome == BIOME_DESERT:
            score -= HOUSE_DESERT_PENALTY

        # ---------- Есть ли место сбоку под будущий склад ----------
        half_house_w = HOUSE_DEFAULT_SIZE[0] / 2
        side_w = STORAGE_FIELD_WIDTH + STORAGE_HOUSE_GAP * 2
        left_ok = self._point_clear((px - half_house_w - side_w / 2, py), "storage", biome_grid, ctx)
        right_ok = self._point_clear((px + half_house_w + side_w / 2, py), "storage", biome_grid, ctx)
        if left_ok or right_ok:
            score += HOUSE_STORAGE_ROOM_BONUS

        # ---------- Не слишком далеко и не впритык к костру ----------
        if campfire_pos is not None:
            dist = math.hypot(px - campfire_pos[0], py - campfire_pos[1])
            score -= abs(dist - HOUSE_CAMPFIRE_DISTANCE_IDEAL) * 0.05

        return score

    def _pick_storage_point(self, ctx):
        c = self.c
        house = next((h for h in ctx.houses if c.id in h.owner_ids), None)
        if house is None:
            return None
        half_house_w = house.width / 2
        half_store_w = STORAGE_FIELD_WIDTH / 2
        sides = [1, -1]
        random.shuffle(sides)
        for side_sign in sides:
            px = house.x + side_sign * (half_house_w + STORAGE_HOUSE_GAP + half_store_w)
            point = (px, house.y)
            if self._point_clear(point, "storage", ctx.biome_grid, ctx, skip_house_id=house.id):  # НОВОЕ
                return point
        return None

    def _pick_new_campfire_point(self, ctx, attempts=30):
        c = self.c
        existing_fires = list(ctx.campfires)
        pending_sites = [s for s in ctx.construction_sites if s.build_type == "campfire"]

        for _ in range(attempts):
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(*NEW_CAMPFIRE_DISTANCE_RANGE)
            point = geometry.clamped_point(c.x, c.y, angle, dist)

            far_enough = (
                    all(math.hypot(point[0] - f.x, point[1] - f.y) >= NEW_CAMPFIRE_DISTANCE_RANGE[0]
                        for f in existing_fires)
                    and all(math.hypot(point[0] - s.x, point[1] - s.y) >= NEW_CAMPFIRE_DISTANCE_RANGE[0]
                            for s in pending_sites)
            )
            if not far_enough:
                continue

            if self._point_clear(point, "campfire", ctx.biome_grid, ctx):
                return point

        return None

    def _find_or_create_site(self, build_type, campfire_pos, ctx):
        c = self.c
        for site in ctx.construction_sites:
            if site.build_type != build_type:
                continue
            if math.hypot(c.x - site.x, c.y - site.y) < CONSTRUCTION_SITE_SEARCH_RADIUS:
                return site

        point = self._pick_point(build_type, campfire_pos, ctx.biome_grid, ctx)
        if point is None:
            return None

        site = ConstructionSite(point[0], point[1], build_type, campfire_pos=campfire_pos)
        ctx.construction_sites.append(site)
        c.pending_site_cleanup = site
        return site

    # ---------- Доставка материалов / стройка ----------

    def _deliver(self, site):
        c = self.c
        c.state = STATE_SEEKING
        if math.hypot(c.x - site.x, c.y - site.y) > CONSTRUCTION_APPROACH_DISTANCE:
            c.goal_text = INFO_CREATURE_GOAL_CONSTRUCTION_GO
            c.target = (site.x, site.y)
            return c.target

        wood_to_deposit = min(c.carried_resources["wood"], site.needed("wood"))
        stone_to_deposit = min(c.carried_resources["stone"], site.needed("stone"))
        site.deposited_wood += wood_to_deposit
        site.deposited_stone += stone_to_deposit
        c.carried_resources["wood"] -= wood_to_deposit
        c.carried_resources["stone"] -= stone_to_deposit

        if wood_to_deposit > 0 or stone_to_deposit > 0:
            site.contributor_ids.add(c.id)

        if site.needed("wood") == 0:
            c.carried_resources["wood"] = 0
        if site.needed("stone") == 0:
            c.carried_resources["stone"] = 0

        c.goal_text = INFO_CREATURE_GOAL_CONSTRUCTION_DEPOSIT
        c.target = (c.x, c.y)

        if site.resources_complete():
            site.is_building = True
            site.builder_ids.add(c.id)
            c.construction_phase = "build"

        return c.target

    def _perform_build_phase(self, site, ctx):
        c = self.c
        site.builder_ids.add(c.id)
        site.contributor_ids.add(c.id)
        c.construction_phase = "build"
        c.state = STATE_SEEKING

        if math.hypot(c.x - site.x, c.y - site.y) > CONSTRUCTION_APPROACH_DISTANCE:
            c.goal_text = INFO_CREATURE_GOAL_CONSTRUCTION_GO
            c.target = (site.x, site.y)
            return c.target

        c.goal_text = INFO_CREATURE_GOAL_CONSTRUCTION_BUILD
        c.target = (c.x, c.y)

        alive_ids = {o.id for o in ctx.other_creatures if not o.is_dead}
        alive_ids.add(c.id)
        site.builder_ids &= alive_ids
        if not site.builder_ids:
            site.builder_ids = {c.id}

        is_leader = c.id == min(site.builder_ids)
        if is_leader:
            speed = 1.0 + max(0, len(site.builder_ids) - 1) * BUILD_HELP_SPEED_BONUS_PER_HELPER
            site.build_progress += ctx.dt * speed

        if site.build_progress >= site.build_time:
            self._finish(site, ctx)
            return (c.x, c.y)

        return c.target

    def _finish(self, site, ctx):
        c = self.c
        new_object = None
        if site.build_type == "campfire":
            new_object = Campfire(site.x, site.y)
            ctx.campfires.append(new_object)

        elif site.build_type == "storage":
            new_object = StorageField(site.x, site.y, owner_campfire_pos=site.campfire_pos)
            primary_owner_id = getattr(site, "storage_owner_id", None) or c.id
            new_object.add_owner(primary_owner_id)

            primary_owner = next((o for o in ctx.other_creatures if o.id == primary_owner_id), None)
            partner_id = primary_owner.partner_id if primary_owner is not None else None
            if partner_id is not None and partner_id in site.contributor_ids:
                new_object.add_owner(partner_id)

            new_object.built_by = c.id
            ctx.storage_fields.append(new_object)

            # ---------- Склад сразу становится неотделимой частью дома ----------
            linked_house_id = getattr(site, "linked_house_id", None)
            house = next((h for h in ctx.houses if h.id == linked_house_id), None) if linked_house_id else None
            if house is not None:
                house.attach_storage(new_object)
            else:
                new_object.house_id = None

        elif site.build_type == "graveyard":
            new_object = Graveyard(site.x, site.y)
            ctx.graveyards.append(new_object)

        elif site.build_type == "house":
            cap_range = HOUSE_CAPACITY_RANGE.get(c.temperament, (4, 6))
            new_object = House(site.x, site.y, capacity=random.randint(*cap_range))
            primary_owner_id = getattr(site, "house_owner_id", None) or c.id
            new_object.owner_ids.add(primary_owner_id)
            new_object.resident_ids.add(primary_owner_id)
            c.home_id = new_object.id

            primary_owner = next((o for o in ctx.other_creatures if o.id == primary_owner_id), None)
            partner_id = primary_owner.partner_id if primary_owner is not None else c.partner_id
            if partner_id is not None:
                new_object.owner_ids.add(partner_id)
                if new_object.add_resident(partner_id):
                    partner = next((o for o in ctx.other_creatures if o.id == partner_id), None)
                    if partner is not None:
                        partner.home_id = new_object.id

            # ---------- Ещё не расселённые дети переезжают вместе с семьёй ----------
            for child in ctx.other_creatures:
                if (not child.is_dead and child.home_id is None
                        and child.parent_ids and primary_owner_id in child.parent_ids):
                    if new_object.add_resident(child.id):
                        child.home_id = new_object.id

            # ---------- "Осиротевший" склад из старого мира привязываем к новому дому ----------
            for field in ctx.storage_fields:
                if primary_owner_id in field.owner_ids and getattr(field, "house_id", None) is None:
                    new_object.attach_storage(field)

            ctx.houses.append(new_object)

        if site in ctx.construction_sites:
            ctx.construction_sites.remove(site)

        self._react_to_player_construction_help(site, c, ctx)

        c.goal_text = INFO_CREATURE_GOAL_CONSTRUCTION_DONE
        c.construction_target_id = None
        c.construction_phase = None
        c.pending_construction_cleanup = (site.build_type, new_object)

    def _work_on(self, site, ctx):
        c = self.c
        if site.is_building:
            return self._perform_build_phase(site, ctx)
        if site.resources_complete():
            site.is_building = True
            site.builder_ids.add(c.id)
            c.construction_phase = "build"
            return self._perform_build_phase(site, ctx)

        if c.carried_resources["wood"] > 0 or c.carried_resources["stone"] > 0:
            return self._deliver(site)

        needed_wood = site.needed("wood")
        needed_stone = site.needed("stone")
        res_type = "wood" if needed_wood > 0 else ("stone" if needed_stone > 0 else None)
        if res_type is None:
            return self._deliver(site)

        source = self._find_gather_source(res_type, ctx)
        if source is None and needed_wood > 0 and needed_stone > 0:
            alt_type = "stone" if res_type == "wood" else "wood"
            alt_source = self._find_gather_source(alt_type, ctx)
            if alt_source is not None:
                res_type, source = alt_type, alt_source

        if source is None:
            c.state = STATE_SEEKING
            c.goal_text = (INFO_CREATURE_GOAL_GATHER_WOOD if res_type == "wood"
                           else INFO_CREATURE_GOAL_GATHER_STONE)
            if self.roads is not None:
                route = self.roads.pursue_known_link(res_type, ctx)
                if route:
                    c.target = route
                    return route
            c.target = self.instincts.pursue_search_target()
            return c.target

        needed_amount = needed_wood if res_type == "wood" else needed_stone
        self._start_gathering(res_type, source, needed_amount=needed_amount)
        return self._continue_gathering(ctx)

    # ---------- Восстановление после перезапуска / кооперация ----------

    def _find_orphaned_site(self, ctx, type_filter=None):
        c = self.c
        if c.gender != GENDER_MALE or c.life_stage != LIFE_STAGE_ADULT:
            return None
        if c.panic_active or c.fear_timer > 0 or c.is_sleeping:
            return None
        if not ctx.construction_sites:
            return None

        claimed_ids = {o.construction_target_id for o in ctx.other_creatures
                       if not o.is_dead and o.construction_target_id is not None}

        candidates = [s for s in ctx.construction_sites
                      if s.id not in claimed_ids
                      and (type_filter is None or s.build_type in type_filter)
                      and math.hypot(c.x - s.x, c.y - s.y)
                      < CONSTRUCTION_SITE_SEARCH_RADIUS * ORPHAN_SITE_SEARCH_RADIUS_FACTOR]
        if not candidates:
            return None
        return min(candidates, key=lambda s: math.hypot(c.x - s.x, c.y - s.y))

    def _try_join_help(self, ctx):
        c = self.c
        if c.build_help_check_timer > 0:
            c.build_help_check_timer -= ctx.dt
            return None
        c.build_help_check_timer = random.uniform(*BUILD_HELP_CHECK_INTERVAL)

        own_need = self._determine_need(c.known_campfire, ctx)
        if own_need in ("house", "storage"):
            return None

        sites_by_id = {s.id: s for s in ctx.construction_sites}

        candidates = [
            o for o in ctx.visible_companions
            if o.gender == GENDER_MALE and o.life_stage == LIFE_STAGE_ADULT
               and o.construction_target_id is not None and o.construction_phase in ("deposit", "build")
               and c.social.get_relationship(o) >= BUILD_HELP_MIN_RELATIONSHIP
               and sites_by_id.get(o.construction_target_id) is not None
               and sites_by_id[o.construction_target_id].build_type not in ("house", "storage")
        ]
        if not candidates:
            return None
        if random.random() >= BUILD_HELP_JOIN_CHANCE * c.psyche.helpfulness_modifier():
            return None

        target_worker = c.social.best_companion(candidates)
        c.construction_target_id = target_worker.construction_target_id
        c.construction_phase = "deposit"
        c.social.adjust_mutual_relationship(target_worker, BUILD_HELP_RELATIONSHIP_BONUS)

        c.state = STATE_SEEKING
        c.goal_text = INFO_CREATURE_GOAL_CONSTRUCTION_HELP
        c.target = (target_worker.x, target_worker.y)
        return c.target

    def _react_to_player_construction_help(self, site, finisher, ctx):
        total_units = site.required_wood + site.required_stone + site.build_time
        if total_units <= 0:
            return
        player_units = (site.player_deposited_wood + site.player_deposited_stone
                        + site.player_build_progress)
        if player_units <= 0:
            return
        share = geometry.clamp(player_units / total_units, 0.0, 1.0)

        target = finisher
        owner_attr = getattr(self, "_OWNER_ATTR_BY_TYPE", {}).get(site.build_type)
        if owner_attr is not None:
            owner_id = getattr(site, owner_attr, None)
            if owner_id is not None:
                owner = next((o for o in ctx.other_creatures if o.id == owner_id), None)
                if owner is not None:
                    target = owner

        bonus = PLAYER_CONSTRUCTION_HELP_RELATIONSHIP_MAX * share
        target.player_relationship = geometry.clamp(
            target.player_relationship + bonus, -100.0, 100.0)
        target.psyche.on_player_construction_help(share)
        target.player_reactions.add_memory(
            "construction_help", share=round(share, 2), relationship_after=target.player_relationship)