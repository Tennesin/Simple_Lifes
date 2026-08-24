import math
import random

from objects import Fruit, Tree, Stone, Grass
from settings import *
import settings
from creatures.all_needed import navigation
from creatures.all_needed.navigation import SpatialGrid
from game.world_context import WorldState, WorldFrameContext
from game.race_registry import all_races
from game.animal_registry import all_animals, all_animal_drop_collections

class Simulation:
    STATIC_GRID_REBUILD_INTERVAL = 6

    def __init__(self, game):
        self.game = game
        self._nav_cache = navigation.NavGridCache()
        self._fruit_grid = SpatialGrid(cell_size=200)
        self._spike_grid = SpatialGrid(cell_size=200)
        self._water_grid = SpatialGrid(cell_size=200)
        self._bush_grid = SpatialGrid(cell_size=200)
        self._campfire_grid = SpatialGrid(cell_size=300)
        self._creature_grid = SpatialGrid(cell_size=250)
        self._corpse_grid = SpatialGrid(cell_size=250)
        self._tree_spawn_timer = random.uniform(*NATURAL_TREE_SPAWN_INTERVAL)
        self._bush_spawn_timer = random.uniform(*NATURAL_BUSH_SPAWN_INTERVAL)
        self._stone_spawn_timer = random.uniform(*NATURAL_STONE_SPAWN_INTERVAL)
        self._grass_spawn_timer = random.uniform(*NATURAL_GRASS_SPAWN_INTERVAL)
        self._tree_grid = SpatialGrid(cell_size=200)
        self._stone_grid = SpatialGrid(cell_size=200)
        self._static_grid_frame = 0

        self._tick_processors = [
            descriptor.tick_processor_cls(game) for descriptor in all_races()
        ]

    # =====================================================================
    # Точка входа
    # =====================================================================

    def update(self, dt):
        game = self.game
        if not game.world_loaded or game.paused:
            return
        if game.create_world_screen is not None or game.load_world_screen is not None:
            return
        if game.settings_screen is not None:
            return

        self._handle_natural_growth(dt)
        self._update_bushes(dt)
        self._tick_race_world_objects(dt)

        simulation_bounds = self._compute_simulation_bounds(game)
        active_ids = self._compute_active_ids(game, simulation_bounds)

        self._tick_animals(dt, active_ids)
        self._tick_transient_drop_decay(dt)

        ctx = self._prepare_frame_context(dt, simulation_bounds=simulation_bounds, active_ids=active_ids)

        for processor in self._tick_processors:
            processor.process(ctx)
        self._cleanup_transient_objects()

    # =====================================================================
    # Домен: подготовка контекста кадра - теперь единый WorldFrameContext
    # =====================================================================

    def _prepare_frame_context(self, dt, simulation_bounds=None, active_ids=None):
        game = self.game
        world = game.world

        creatures_by_id = {c.id: c for c in world.creatures}

        nav_grid_no_fences = self._nav_cache.get(
            settings.WORLD_WIDTH, settings.WORLD_HEIGHT, NAV_GRID_CELL_SIZE,
            world.walls, world.fences, world.spikes, False,
            NAV_OBSTACLE_INFLATE, SPIKE_NAV_BLOCK_RADIUS,
            biome_grid=game.biome_manager.grid, version=world.landscape_version)
        nav_grid_with_fences = self._nav_cache.get(
            settings.WORLD_WIDTH, settings.WORLD_HEIGHT, NAV_GRID_CELL_SIZE,
            world.walls, world.fences, world.spikes, True,
            NAV_OBSTACLE_INFLATE, SPIKE_NAV_BLOCK_RADIUS,
            biome_grid=game.biome_manager.grid, version=world.landscape_version)

        nav_grid_no_fences_fallback = self._nav_cache.get_fallback(
            settings.WORLD_WIDTH, settings.WORLD_HEIGHT, NAV_GRID_CELL_SIZE,
            world.walls, world.fences, world.spikes, False,
            SPIKE_NAV_BLOCK_RADIUS,
            biome_grid=game.biome_manager.grid, version=world.landscape_version)
        nav_grid_with_fences_fallback = self._nav_cache.get_fallback(
            settings.WORLD_WIDTH, settings.WORLD_HEIGHT, NAV_GRID_CELL_SIZE,
            world.walls, world.fences, world.spikes, True,
            SPIKE_NAV_BLOCK_RADIUS,
            biome_grid=game.biome_manager.grid, version=world.landscape_version)

        self._static_grid_frame += 1
        rebuild_static = (
                self._static_grid_frame % self.STATIC_GRID_REBUILD_INTERVAL == 0
                or not self._fruit_grid.buckets  # первый кадр после запуска/загрузки мира
        )

        if rebuild_static:
            self._fruit_grid.build(f for f in world.fruits if f.active)
            self._spike_grid.build(world.spikes)
            self._water_grid.build(w for w in world.water_puddles if w.has_water())
            self._bush_grid.build(world.bushes)
            self._campfire_grid.build(world.campfires)
            self._tree_grid.build(t for t in world.trees if t.has_wood())
            self._stone_grid.build(s for s in world.stones if s.has_stone())

        self._creature_grid.build(
            c for c in world.creatures if not c.is_dead and not getattr(c, "at_home", False))
        self._corpse_grid.build(c for c in world.creatures if c.is_dead)

        spatial_grids = {
            "fruits": self._fruit_grid, "spikes": self._spike_grid,
            "water": self._water_grid, "bushes": self._bush_grid,
            "campfires": self._campfire_grid, "creatures": self._creature_grid,
            "corpses": self._corpse_grid,
            "trees": self._tree_grid, "stones": self._stone_grid,
        }

        race_collections = {
            name: getattr(world, name, []) for name in WorldState.RACE_COLLECTIONS
        }
        animal_collections = {
            descriptor.world_collection: getattr(world, descriptor.world_collection, [])
            for descriptor in all_animals()
        }

        wall_bounds = [(w, *w.get_bounding_circle()) for w in world.walls if w.points]
        fence_bounds = [(f, *f.get_bounding_circle()) for f in world.fences if f.points]

        if simulation_bounds is None:
            simulation_bounds = self._compute_simulation_bounds(game)
        if active_ids is None:
            active_ids = self._compute_active_ids(game, simulation_bounds)

        return WorldFrameContext(
            dt=dt,
            fruits=world.fruits, spikes=world.spikes, water_puddles=world.water_puddles,
            bushes=world.bushes, creatures=world.creatures, roads=world.roads,
            walls=world.walls, fences=world.fences, trees=world.trees, stones=world.stones,
            road_crossings=world.road_crossings, grass=world.grass, wall_bounds=wall_bounds,
            fence_bounds=fence_bounds, race_collections=race_collections,
            animal_collections=animal_collections, creatures_by_id=creatures_by_id,
            nav_grid_no_fences=nav_grid_no_fences, nav_grid_with_fences=nav_grid_with_fences,
            nav_grid_no_fences_fallback=nav_grid_no_fences_fallback,
            nav_grid_with_fences_fallback=nav_grid_with_fences_fallback,
            spatial_grids=spatial_grids, biome_grid=game.biome_manager.grid,
            simulation_bounds=simulation_bounds, active_ids=active_ids,
        )

    # =====================================================================
    # Домен: Область Симуляции (ДОС) - границы вокруг камеры + набор id,
    # которые в неё попадают. Само использование (заморозка/упрощение)
    # реализуется в тик-обработчиках рас и животных - здесь только подготовка.
    # =====================================================================

    def _compute_simulation_bounds(self, game):
        units = game.display_settings.get("simulation_area_units", SIMULATION_AREA_DEFAULT_UNITS)
        units = max(SIMULATION_AREA_MIN_UNITS, min(SIMULATION_AREA_MAX_UNITS, units))
        margin = units * SIMULATION_AREA_PX_PER_UNIT
        cam = game.camera
        return (
            cam.x - margin, cam.y - margin,
            cam.x + cam.camera.width + margin, cam.y + cam.camera.height + margin,
        )

    def _compute_active_ids(self, game, bounds):
        min_x, min_y, max_x, max_y = bounds
        world = game.world

        def _in_bounds(obj):
            return min_x <= obj.x <= max_x and min_y <= obj.y <= max_y

        active_ids = {c.id for c in world.creatures if _in_bounds(c)}
        for descriptor in all_animals():
            active_ids.update(
                a.id for a in getattr(world, descriptor.world_collection) if _in_bounds(a)
            )

        favorite_id = getattr(game, "favorite_creature_id", None)
        if favorite_id is None:
            return active_ids

        favorite = next((c for c in world.creatures if c.id == favorite_id and not c.is_dead), None)
        if favorite is None:
            return active_ids

        active_ids.add(favorite.id)
        vision = (favorite.effective_vision_radius()
                  if hasattr(favorite, "effective_vision_radius") else DEFAULT_VISION_RADIUS)

        # ---------- НОВОЕ: прямой перебор вместо self._creature_grid ----------
        for other in world.creatures:
            if other.id == favorite.id or other.is_dead:
                continue
            if math.hypot(other.x - favorite.x, other.y - favorite.y) <= vision:
                active_ids.add(other.id)
        for descriptor in all_animals():
            for animal in getattr(world, descriptor.world_collection):
                if math.hypot(animal.x - favorite.x, animal.y - favorite.y) <= vision:
                    active_ids.add(animal.id)

        return active_ids

    # =====================================================================
    # Домен: естественный рост деревьев/кустов/камней (таймеры мира)
    # =====================================================================

    def _handle_natural_growth(self, dt):
        game = self.game

        self._tree_spawn_timer -= dt
        if self._tree_spawn_timer <= 0:
            self._tree_spawn_timer = random.uniform(*NATURAL_TREE_SPAWN_INTERVAL)
            if random.random() < NATURAL_TREE_SPAWN_CHANCE:
                game.object_manager.try_natural_tree_growth()

        self._bush_spawn_timer -= dt
        if self._bush_spawn_timer <= 0:
            self._bush_spawn_timer = random.uniform(*NATURAL_BUSH_SPAWN_INTERVAL)
            if random.random() < NATURAL_BUSH_SPAWN_CHANCE:
                game.object_manager.try_natural_bush_growth()

        self._stone_spawn_timer -= dt
        if self._stone_spawn_timer <= 0:
            self._stone_spawn_timer = random.uniform(*NATURAL_STONE_SPAWN_INTERVAL)
            if random.random() < NATURAL_STONE_SPAWN_CHANCE:
                game.object_manager.try_natural_stone_growth()

        self._grass_spawn_timer -= dt
        if self._grass_spawn_timer <= 0:
            self._grass_spawn_timer = random.uniform(*NATURAL_GRASS_SPAWN_INTERVAL)
            if random.random() < NATURAL_GRASS_SPAWN_CHANCE:
                game.object_manager.try_natural_grass_growth()

    # =====================================================================
    # Домен: тик кустов и неживых объектов
    # =====================================================================

    def _update_bushes(self, dt):
        game = self.game
        for bush in game.world.bushes:
            if bush.update(dt):
                game.object_manager.try_spawn_fruit_near_bush(bush)

    def _tick_race_world_objects(self, dt):
        game = self.game
        for descriptor in all_races():
            if descriptor.world_tick_fn is not None:
                descriptor.world_tick_fn(game, dt)

    def _tick_animals(self, dt, active_ids):
        nav_grid, nav_grid_fallback = self._prepare_animal_nav_grid()
        for descriptor in all_animals():
            if descriptor.tick_fn is not None:
                descriptor.tick_fn(self.game, dt, nav_grid, nav_grid_fallback, active_ids=active_ids)

    def _prepare_animal_nav_grid(self):
        game = self.game
        nav_grid = self._nav_cache.get(
            settings.WORLD_WIDTH, settings.WORLD_HEIGHT, NAV_GRID_CELL_SIZE,
            game.world.walls, game.world.fences, game.world.spikes,
            True, NAV_OBSTACLE_INFLATE, SPIKE_NAV_BLOCK_RADIUS,
            biome_grid=game.biome_manager.grid, version=game.world.landscape_version)
        # ---------- НОВОЕ: запасная сетка с минимальным отступом ----------
        nav_grid_fallback = self._nav_cache.get_fallback(
            settings.WORLD_WIDTH, settings.WORLD_HEIGHT, NAV_GRID_CELL_SIZE,
            game.world.walls, game.world.fences, game.world.spikes,
            True, SPIKE_NAV_BLOCK_RADIUS,
            biome_grid=game.biome_manager.grid, version=game.world.landscape_version)
        return nav_grid, nav_grid_fallback

    def _tick_transient_drop_decay(self, dt):
        game = self.game
        world = game.world
        for attr in ("meats",) + all_animal_drop_collections():
            collection = getattr(world, attr)
            if not collection:
                continue
            expired = [obj for obj in collection if obj.tick(dt)]
            if not expired:
                continue
            setattr(world, attr, [obj for obj in collection if obj not in expired])
            if game.selected_object in expired:
                game.selected_object = None
            if game.player.grabbed_object in expired:
                game.player.grabbed_object = None

    # =====================================================================
    # Домен: очистка "недолговечных" объектов - съеденные фрукты,
    # осиротевшие ссылки на них у игрока, устаревший выбор стройплощадки
    # =====================================================================

    def _cleanup_transient_objects(self):
        game = self.game
        world = game.world

        if (game.player.grabbed_object is not None
                and isinstance(game.player.grabbed_object, Fruit)
                and not game.player.grabbed_object.active):
            game.player.grabbed_object = None

        world.fruits = [f for f in world.fruits if f.active]
        if game.selected_object is not None and isinstance(game.selected_object,
                                                           Fruit) and not game.selected_object.active:
            game.selected_object = None

        self._cleanup_exhausted_resource(world, "trees", Tree, lambda t: t.has_wood())
        self._cleanup_exhausted_resource(world, "stones", Stone, lambda s: s.has_stone())
        self._cleanup_exhausted_resource(world, "grass", Grass, lambda g: g.has_food())
        self._cleanup_exhausted_water(world)

        if (game.selected_object is not None
                and hasattr(game.selected_object, "build_type")
                and game.selected_object not in world.construction_sites):
            game.selected_object = None

        if (game.player.grabbed_object is not None
                and hasattr(game.player.grabbed_object, "build_type")
                and game.player.grabbed_object not in world.construction_sites):
            game.player.grabbed_object = None

    def _cleanup_exhausted_resource(self, world, attr, cls, alive_check):
        game = self.game
        collection = getattr(world, attr)
        alive = [obj for obj in collection if alive_check(obj)]
        if len(alive) == len(collection):
            return
        removed = [obj for obj in collection if obj not in alive]
        setattr(world, attr, alive)

        if game.selected_object in removed:
            game.selected_object = None
        if game.player.grabbed_object in removed:
            game.player.grabbed_object = None

    def _cleanup_exhausted_water(self, world):
        game = self.game
        alive = [w for w in world.water_puddles if w.has_water()]
        if len(alive) == len(world.water_puddles):
            return
        removed = [w for w in world.water_puddles if w not in alive]
        world.water_puddles = alive

        for water in removed:
            if water.claimed_by is not None:
                owner = next((c for c in world.creatures if c.id == water.claimed_by), None)
                if owner is not None and hasattr(owner, "territory"):
                    owner.territory.claims_count["water"] = max(
                        0, owner.territory.claims_count.get("water", 0) - 1)
            game.object_manager.unlink_road_endpoints("water", water.id)
            for creature in world.creatures:
                creature.on_landmark_removed("water", water.id, (water.x, water.y))

        if game.selected_object in removed:
            game.selected_object = None
        if game.player.grabbed_object in removed:
            game.player.grabbed_object = None

    # =====================================================================
    # Служебное
    # =====================================================================

    def invalidate_nav_cache(self):
        self._nav_cache.invalidate()