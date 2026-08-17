import shutil
import random
import math

from settings import *
from ..ci_settings import *
from ..ci_info import INFO_CREATURE_GOAL_HOUSE_EVICTED
from ..life_cycle import apply_grief_for_death
from .input_events import cleanup_area_for_new_graveyard, cleanup_area_for_new_construction

def tick_circle_world(game, dt):
    for gy in game.world.graveyards:
        gy.update(dt)

    panel = game.ui.graveyard_panel
    if (panel.details_record is not None
            and panel.details_record.get("time_since_burial", 0.0) > GRAVEYARD_DATA_RETENTION):
        panel.details_record = None

def _storage_priority(creature):
    if creature.life_stage == LIFE_STAGE_CHILD:
        return 0
    if creature.life_stage == LIFE_STAGE_OLD:
        return 1
    if creature.gender == GENDER_FEMALE:
        return 2
    return 3

class CircleTickProcessor:
    """Единственная точка входа - process(ctx). Всё остальное - детали."""

    race_name = "circle"

    def __init__(self, game):
        self.game = game

    def process(self, ctx):
        genealogy = self.game.object_manager.spawn_managers["circle"].genealogy
        race_creatures = self._race_creatures()

        ctx.campfire_occupancy = self._compute_campfire_occupancy(ctx.campfires, race_creatures)

        self._reconcile_storage_ownership(ctx)
        self._reconcile_house_ownership(ctx)
        corpses_to_remove = self._process_corpses(ctx.dt, race_creatures, genealogy)
        ready_for_interact = self._process_living_creatures(ctx, race_creatures, genealogy)
        self._process_grief(race_creatures)

        self._run_interactions(ctx, ready_for_interact)
        self._cleanup_removed_corpses(corpses_to_remove)

    # =====================================================================
    # Домен: отбор существ этой расы из общего списка мира
    # =====================================================================

    def _race_creatures(self):
        return [c for c in self.game.world.creatures
                if getattr(c, "race_name", None) == self.race_name]

    # =====================================================================
    # Домен: занятость костров - сколько существ считают его "домом"
    # =====================================================================

    def _compute_campfire_occupancy(self, campfires, race_creatures):
        occupancy = {fire.id: 0 for fire in campfires}
        for creature in race_creatures:
            if creature.is_dead or creature.known_campfire is None:
                continue
            kx, ky = creature.known_campfire
            for fire in campfires:
                if math.hypot(kx - fire.x, ky - fire.y) < 5:
                    occupancy[fire.id] = occupancy.get(fire.id, 0) + 1
                    break
        return occupancy

    # =====================================================================
    # Домен: наследование прав на семейный склад при смерти владельца
    # =====================================================================

    def _reconcile_house_ownership(self, ctx):
        world = self.game.world
        if not world.houses:
            return
        creatures_by_id = ctx.creatures_by_id or {c.id: c for c in world.creatures}

        for house in world.houses:
            dead_residents = [rid for rid in house.resident_ids
                              if creatures_by_id.get(rid) is None or creatures_by_id[rid].is_dead]
            for rid in dead_residents:
                house.remove_resident(rid)

            if not house.owner_ids:
                continue
            dead_owners = [oid for oid in house.owner_ids
                           if creatures_by_id.get(oid) is None or creatures_by_id[oid].is_dead]
            for owner_id in dead_owners:
                self._transfer_house_owner(house, owner_id, world)

    def _transfer_house_owner(self, house, owner_id, world):
        house.owner_ids.discard(owner_id)
        house.remove_resident(owner_id)

        heir_id = None
        partner = next((c for c in world.creatures if not c.is_dead and c.partner_id == owner_id), None)
        if partner is not None and partner.id in house.resident_ids:
            heir_id = partner.id
        else:
            sons = [c for c in world.creatures
                    if not c.is_dead and c.parent_ids and owner_id in c.parent_ids
                    and c.gender == GENDER_MALE and c.id in house.resident_ids]
            if sons:
                heir_id = min(sons, key=lambda s: s.age).id  # самый младший сын
            else:
                unmarried_daughters = [c for c in world.creatures
                                       if not c.is_dead and c.parent_ids and owner_id in c.parent_ids
                                       and c.gender == GENDER_FEMALE and c.partner_id is None
                                       and c.id in house.resident_ids]
                if unmarried_daughters:
                    heir_id = random.choice(unmarried_daughters).id
                else:
                    any_children = [c for c in world.creatures
                                    if not c.is_dead and c.parent_ids and owner_id in c.parent_ids
                                    and c.id in house.resident_ids]
                    if any_children:
                        heir_id = random.choice(any_children).id

        if heir_id is not None:
            house.owner_ids.add(heir_id)
            for field in world.storage_fields:
                if getattr(field, "house_id", None) == house.id and owner_id in field.owner_ids:
                    field.owner_ids.discard(owner_id)
                    field.add_owner(heir_id)

    def _reconcile_storage_ownership(self, ctx):
        world = self.game.world
        if not world.storage_fields:
            return
        creatures_by_id = ctx.creatures_by_id or {c.id: c for c in world.creatures}

        for field in world.storage_fields:
            if not field.owner_ids:
                continue
            dead_owners = [oid for oid in field.owner_ids
                          if creatures_by_id.get(oid) is None or creatures_by_id[oid].is_dead]
            for owner_id in dead_owners:
                self._transfer_storage_owner(field, owner_id, world)

    def _transfer_storage_owner(self, field, owner_id, world):
        field.owner_ids.discard(owner_id)
        partner = next((c for c in world.creatures if not c.is_dead and c.partner_id == owner_id), None)

        heir_id = None
        if partner is not None:
            heir_id = partner.id
        else:
            children = [c for c in world.creatures
                       if not c.is_dead and c.parent_ids and owner_id in c.parent_ids]
            daughters = [c for c in children if c.gender == GENDER_FEMALE]
            sons = [c for c in children if c.gender == GENDER_MALE]
            if daughters:
                heir_id = random.choice(daughters).id
            elif sons:
                heir_id = random.choice(sons).id

        # ---------- Наследника нет - склад необратимо становится общественным достоянием ----------
        if heir_id is not None:
            field.add_owner(heir_id)

    # =====================================================================
    # Домен: обработка мёртвых существ (переноска трупа/захоронение/истечение таймера)
    # =====================================================================

    def _process_corpses(self, dt, race_creatures, genealogy):
        game = self.game
        world = game.world
        corpses_to_remove = []

        for creature in race_creatures:
            if not creature.is_dead:
                continue

            genealogy.mark_dead(creature.id, creature)
            if creature.being_carried_by is not None:
                carrier = next((cc for cc in race_creatures if cc.id == creature.being_carried_by), None)
                valid_carry = (carrier is not None and not carrier.is_dead
                               and carrier.burial_target_id == creature.id)
                if not valid_carry:
                    creature.being_carried_by = None
                    creature.burial_claimant_id = None
                else:
                    creature.x, creature.y = carrier.x, carrier.y
                    target_graveyard = next(
                        (g for g in world.graveyards if g.id == carrier.graveyard_target_id), None)
                    if (target_graveyard is not None and
                            target_graveyard.distance_to_point(creature.x, creature.y) < GRAVEYARD_BURIAL_DISTANCE):
                        target_graveyard.bury(creature)
                        carrier.burial_target_id = None
                        carrier.graveyard_target_id = None
                        carrier.is_dragging_corpse = False
                        corpses_to_remove.append(creature)
                    continue

            if creature.tick_corpse(dt):
                corpses_to_remove.append(creature)

        return corpses_to_remove

    # =====================================================================
    # Домен: обработка живых существ - нужды, взросление, роды, решение и движение
    # =====================================================================

    def _process_living_creatures(self, ctx, race_creatures, genealogy):
        game = self.game
        world = game.world
        ready_for_interact = []
        wall_polylines, _fence_polylines = game.welded_landscape_polylines()

        for creature in race_creatures:
            if creature.is_dead:
                continue

            genealogy.register_creature(creature)
            genealogy.update_name(creature.id, creature.name)
            if creature.partner_id is not None:
                genealogy.register_pair(creature.id, creature.partner_id)

            creature.at_home = creature.is_in_own_house(world.houses)
            creature.update_needs(ctx.dt, world.creatures, biome_grid=game.biome_manager.grid)
            if creature.is_dead:
                if game.player.grabbed_creature is creature:
                    game.player.grabbed_creature = None
                continue

            creature.aging.update(ctx.dt)
            if creature.is_dead:
                if game.player.grabbed_creature is creature:
                    game.player.grabbed_creature = None
                continue

            # ---------- Выселение сына по истечении отсрочки ----------
            if creature.home_eviction_timer > 0:
                creature.home_eviction_timer -= ctx.dt
                if creature.home_eviction_timer <= 0 and creature.home_id is not None:
                    house = next((h for h in world.houses if h.id == creature.home_id), None)
                    if house is not None:
                        house.remove_resident(creature.id)
                    creature.home_id = None
                    creature.home_eviction_timer = 0.0
                    creature.goal_text = INFO_CREATURE_GOAL_HOUSE_EVICTED

            if (game.biome_manager.grid is not None
                    and game.biome_manager.grid.get_at(creature.x, creature.y) == BIOME_SEA):
                creature.die("утонул в море")
                if game.player.grabbed_creature is creature:
                    game.player.grabbed_creature = None
                continue

            birth_request = creature.family.update(
                ctx.dt, race_creatures, ctx.creatures_by_id, world.storage_fields, world.houses)
            if birth_request is not None:
                game.object_manager.spawn_managers[self.race_name].create_child_creature(creature, birth_request)

            if creature.is_grabbed:
                ready_for_interact.append(creature)
                continue

            target = creature.decide(ctx)

            if creature.pending_construction_cleanup is not None:
                build_type, new_object = creature.pending_construction_cleanup
                creature.pending_construction_cleanup = None
                if new_object is not None:
                    if build_type == "graveyard":
                        cleanup_area_for_new_graveyard(game, new_object)
                    elif build_type in ("campfire", "storage"):
                        cleanup_area_for_new_construction(game, new_object, new_object.radius + 10)

            creature.pathfinder.move_towards(
                target, ctx.dt, biome_grid=game.biome_manager.grid,
                wall_polylines=wall_polylines)
            ready_for_interact.append(creature)

        return ready_for_interact

    # =====================================================================
    # Домен: скорбь - разовая рассылка удара по психике сородичам умершего
    # =====================================================================

    def _process_grief(self, race_creatures):
        for creature in race_creatures:
            if creature.is_dead and creature._pending_grief:
                creature._pending_grief = False
                apply_grief_for_death(creature, race_creatures)

    # =====================================================================
    # Домен: взаимодействия существ с миром (еда/вода/шипы/костёр/разговоры и т.д.)
    # =====================================================================

    def _run_interactions(self, ctx, ready_for_interact):
        world = self.game.world
        grids = ctx.spatial_grids
        dt = ctx.dt
        ready_for_interact.sort(key=_storage_priority)

        for creature in ready_for_interact:
            if grids is not None:
                nearby_fruits = grids["fruits"].query_nearby(creature.x, creature.y, EAT_DISTANCE + 10)
                nearby_spikes = grids["spikes"].query_nearby(creature.x, creature.y, EAT_DISTANCE + 10)
                nearby_water = grids["water"].query_nearby(creature.x, creature.y, EAT_DISTANCE + 40)
                nearby_bushes = grids["bushes"].query_nearby(creature.x, creature.y,
                                                             TERRITORY_BUSH_CLAIM_RADIUS + 20)
                nearby_campfires = grids["campfires"].query_nearby(creature.x, creature.y, CAMPFIRE_RADIUS)
                nearby_creatures = grids["creatures"].query_nearby(
                    creature.x, creature.y, max(TALK_DISTANCE, JEALOUSY_CHECK_DISTANCE))
            else:
                nearby_fruits, nearby_spikes = world.fruits, world.spikes
                nearby_water, nearby_bushes = world.water_puddles, world.bushes
                nearby_campfires, nearby_creatures = world.campfires, world.creatures

            creature.interact(nearby_fruits, nearby_spikes, nearby_water,
                              nearby_bushes, nearby_campfires, nearby_creatures,
                              world.storage_fields, dt, walls=world.walls,
                              biome_grid=self.game.biome_manager.grid)

    # =====================================================================
    # Домен: окончательное удаление истёкших трупов из мира
    # =====================================================================

    def _cleanup_removed_corpses(self, corpses_to_remove):
        game = self.game
        world = game.world
        if not corpses_to_remove:
            return

        for corpse in corpses_to_remove:
            for bush in world.bushes:
                if getattr(bush, "claimed_by", None) == corpse.id:
                    bush.claimed_by = None
            for water in world.water_puddles:
                if getattr(water, "claimed_by", None) == corpse.id:
                    water.claimed_by = None

        if game.selected_creature in corpses_to_remove:
            game.selected_creature = None
            game.editing_name = False
            game.name_edit_buffer = ""

        if game.world_path:
            for corpse in corpses_to_remove:
                folder_path = os.path.join(game.world_path, "creatures", corpse.id)
                shutil.rmtree(folder_path, ignore_errors=True)

        world.creatures = [c for c in world.creatures if c not in corpses_to_remove]