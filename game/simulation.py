import random

from objects import Fruit
from settings import *
import settings
from creatures.all_needed import navigation
from creatures.all_needed.navigation import SpatialGrid
from game.world_context import WorldFrameContext
from game.race_registry import all_races

class Simulation:

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
        self._tree_grid = SpatialGrid(cell_size=200)
        self._stone_grid = SpatialGrid(cell_size=200)

        # ---------- Один тик-процессор на каждую зарегистрированную расу
        # (game/race_registry.py, шаги A.3/A.4). Раньше здесь был
        # единственный self._circle_tick = CircleTickProcessor(game),
        # жёстко завязанный на Circle - теперь состав процессоров
        # целиком определяется реестром рас. ----------
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

        ctx = self._prepare_frame_context(dt)

        for processor in self._tick_processors:
            processor.process(ctx)
        self._cleanup_transient_objects()

    # =====================================================================
    # Домен: подготовка контекста кадра - теперь единый WorldFrameContext
    # =====================================================================

    def _prepare_frame_context(self, dt):
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

        self._fruit_grid.build(f for f in world.fruits if f.active)
        self._spike_grid.build(world.spikes)
        self._water_grid.build(world.water_puddles)
        self._bush_grid.build(world.bushes)
        self._campfire_grid.build(world.campfires)
        self._creature_grid.build(c for c in world.creatures if not c.is_dead)
        self._corpse_grid.build(c for c in world.creatures if c.is_dead)
        self._tree_grid.build(t for t in world.trees if t.has_wood())
        self._stone_grid.build(s for s in world.stones if s.has_stone())

        spatial_grids = {
            "fruits": self._fruit_grid, "spikes": self._spike_grid,
            "water": self._water_grid, "bushes": self._bush_grid,
            "campfires": self._campfire_grid, "creatures": self._creature_grid,
            "corpses": self._corpse_grid,
            "trees": self._tree_grid, "stones": self._stone_grid,
        }

        return WorldFrameContext(
            dt=dt,
            fruits=world.fruits, spikes=world.spikes, water_puddles=world.water_puddles,
            bushes=world.bushes, campfires=world.campfires, creatures=world.creatures,
            roads=world.roads, storage_fields=world.storage_fields, graveyards=world.graveyards,
            child_roads=world.child_roads, construction_sites=world.construction_sites,
            walls=world.walls, fences=world.fences, trees=world.trees, stones=world.stones,
            road_crossings=world.road_crossings,
            creatures_by_id=creatures_by_id,
            nav_grid_no_fences=nav_grid_no_fences, nav_grid_with_fences=nav_grid_with_fences,
            spatial_grids=spatial_grids, biome_grid=game.biome_manager.grid,
        )

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

        if (game.selected_object is not None
                and hasattr(game.selected_object, "build_type")
                and game.selected_object not in world.construction_sites):
            game.selected_object = None

        if (game.player.grabbed_object is not None
                and hasattr(game.player.grabbed_object, "build_type")
                and game.player.grabbed_object not in world.construction_sites):
            game.player.grabbed_object = None

    # =====================================================================
    # Служебное
    # =====================================================================

    def invalidate_nav_cache(self):
        self._nav_cache.invalidate()