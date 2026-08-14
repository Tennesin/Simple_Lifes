import shutil

from settings import *
from ..ci_settings import *
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

        corpses_to_remove = self._process_corpses(ctx.dt, race_creatures, genealogy)
        ready_for_interact = self._process_living_creatures(ctx, race_creatures, genealogy)

        self._run_interactions(ctx.dt, ready_for_interact)
        self._cleanup_removed_corpses(corpses_to_remove)

    # =====================================================================
    # Домен: отбор существ этой расы из общего списка мира
    # =====================================================================

    def _race_creatures(self):
        return [c for c in self.game.world.creatures
                if getattr(c, "race_name", None) == self.race_name]

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
                # ---------- Носильщик ищется среди своей же расы: труп Круга
                # физически переносит только другой Круг. ----------
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

        for creature in race_creatures:
            if creature.is_dead:
                continue

            genealogy.register_creature(creature)
            genealogy.update_name(creature.id, creature.name)
            if creature.partner_id is not None:
                genealogy.register_pair(creature.id, creature.partner_id)

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

            if (game.biome_manager.grid is not None
                    and game.biome_manager.grid.get_at(creature.x, creature.y) == BIOME_SEA):
                creature.die("утонул в море")
                if game.player.grabbed_creature is creature:
                    game.player.grabbed_creature = None
                continue

            birth_request = creature.family.update(ctx.dt, world.creatures, ctx.creatures_by_id)
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

            creature.pathfinder.move_towards(target, ctx.dt, biome_grid=game.biome_manager.grid)
            ready_for_interact.append(creature)

        return ready_for_interact

    # =====================================================================
    # Домен: взаимодействия существ с миром (еда/вода/шипы/костёр/разговоры и т.д.)
    # =====================================================================

    def _run_interactions(self, dt, ready_for_interact):
        world = self.game.world
        ready_for_interact.sort(key=_storage_priority)
        for creature in ready_for_interact:
            creature.interactions.process(world.fruits, world.spikes, world.water_puddles,
                                          world.bushes, world.campfires, world.creatures,
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