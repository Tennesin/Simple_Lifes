import pygame
import random
from settings import *
from info import *
import settings
from game.race_registry import all_races
from game.animal_registry import all_animals, all_animal_drop_collections
from creatures.all_needed import geometry

# =========================================================================
# Ядро конвейера отрисовки мира: (ключ_слоя, функция_отрисовки).
# =========================================================================

def _draw_roads(renderer, screen, game, camera, in_view):
    for road in game.world.roads:
        road.draw(screen, camera)
    if game.player.drawing_road is not None:
        game.player.drawing_road.draw(screen, camera)

def _draw_road_crossings(renderer, screen, game, camera, in_view):
    for crossing in game.world.road_crossings:
        if in_view(crossing.x, crossing.y):
            pos = camera.apply_pos((crossing.x, crossing.y))
            crossing.draw(screen, pos)

def _draw_landscape(renderer, screen, game, camera, in_view):
    for wall in game.world.walls:
        wall.draw(screen, camera)
    for fence in game.world.fences:
        fence.draw(screen, camera)
    if game.player.drawing_landscape is not None:
        mouse_x, mouse_y = pygame.mouse.get_pos()
        cursor_world = None
        if mouse_y > UI_HEIGHT:
            cursor_world = camera.world_from_screen(mouse_x, mouse_y)
        game.player.drawing_landscape.draw(screen, camera, extra_point=cursor_world)

def _draw_water(renderer, screen, game, camera, in_view):
    for water in game.world.water_puddles:
        if in_view(water.x, water.y):
            pos = camera.apply_pos((water.x, water.y))
            water.draw(screen, pos)

def _draw_bushes(renderer, screen, game, camera, in_view):
    for bush in game.world.bushes:
        if in_view(bush.x, bush.y):
            pos = camera.apply_pos((bush.x, bush.y))
            bush.draw(screen, pos)

def _draw_trees(renderer, screen, game, camera, in_view):
    for tree in game.world.trees:
        if in_view(tree.x, tree.y):
            pos = camera.apply_pos((tree.x, tree.y))
            tree.draw(screen, pos)

def _draw_stones(renderer, screen, game, camera, in_view):
    for stone in game.world.stones:
        if in_view(stone.x, stone.y):
            pos = camera.apply_pos((stone.x, stone.y))
            stone.draw(screen, pos)

def _draw_fruits(renderer, screen, game, camera, in_view):
    for fruit in game.world.fruits:
        if fruit.active and in_view(fruit.x, fruit.y):
            pos = camera.apply_pos((fruit.x, fruit.y))
            fruit.draw(screen, pos)

def _draw_spikes(renderer, screen, game, camera, in_view):
    for spike in game.world.spikes:
        if in_view(spike.x, spike.y):
            pos = camera.apply_pos((spike.x, spike.y))
            spike.draw(screen, pos)

def _draw_creatures(renderer, screen, game, camera, in_view):
    show_status_rings = game.display_settings["show_status_rings"]
    show_creature_names = game.display_settings["show_creature_names"]
    houses = game.world.houses
    for creature in game.world.creatures:
        if (not creature.is_dead and hasattr(creature, "is_in_own_house")
                and creature.is_in_own_house(houses)):
            continue
        if in_view(creature.x, creature.y):
            pos = camera.apply_pos((creature.x, creature.y))
            creature.draw(screen, pos, show_status_rings=show_status_rings)
            creature_name = getattr(creature, "name", None)
            if show_creature_names and creature_name and not creature.is_dead:
                renderer.draw_creature_name(screen, creature_name, pos)

def _draw_grass(renderer, screen, game, camera, in_view):
    for patch in game.world.grass:
        if in_view(patch.x, patch.y):
            pos = camera.apply_pos((patch.x, patch.y))
            patch.draw(screen, pos)

def _draw_meat(renderer, screen, game, camera, in_view):
    for meat in game.world.meats:
        if in_view(meat.x, meat.y):
            pos = camera.apply_pos((meat.x, meat.y))
            meat.draw(screen, pos)

def _draw_animals(renderer, screen, game, camera, in_view):
    for descriptor in all_animals():
        for animal in getattr(game.world, descriptor.world_collection):
            if in_view(animal.x, animal.y):
                pos = camera.apply_pos((animal.x, animal.y))
                animal.draw(screen, pos)

def _draw_animal_drops(renderer, screen, game, camera, in_view):
    for attr in all_animal_drop_collections():
        for drop in getattr(game.world, attr):
            if in_view(drop.x, drop.y):
                pos = camera.apply_pos((drop.x, drop.y))
                drop.draw(screen, pos)

CORE_RENDER_LAYERS = (
    ("roads", _draw_roads),
    ("road_crossings", _draw_road_crossings),
    ("landscape", _draw_landscape),
    ("grass", _draw_grass),
    ("water_puddles", _draw_water),
    ("bushes", _draw_bushes),
    ("trees", _draw_trees),
    ("stones", _draw_stones),
    ("fruits", _draw_fruits),
    ("meat", _draw_meat),
    ("animal_drops", _draw_animal_drops),
    ("spikes", _draw_spikes),
    ("creatures", _draw_creatures),
    ("animals", _draw_animals),
)

class Camera:
    def __init__(self, world_w, world_h, viewport_w=None, viewport_h=None):
        viewport_w = viewport_w if viewport_w is not None else settings.WINDOW_WIDTH
        viewport_h = viewport_h if viewport_h is not None else settings.WINDOW_HEIGHT - UI_HEIGHT
        viewport_w = min(viewport_w, world_w)
        viewport_h = min(viewport_h, world_h)
        self.camera = pygame.Rect(0, 0, viewport_w, viewport_h)
        self.world_w = world_w
        self.world_h = world_h

    @property
    def x(self):
        return self.camera.x

    @property
    def y(self):
        return self.camera.y

    @x.setter
    def x(self, val):
        self.camera.x = val

    @y.setter
    def y(self, val):
        self.camera.y = val

    def apply_pos(self, world_pos):
        screen_x = world_pos[0] - self.camera.x
        screen_y = world_pos[1] - self.camera.y + UI_HEIGHT
        return (screen_x, screen_y)

    def world_from_screen(self, screen_x, screen_y):
        wx = screen_x + self.camera.x
        wy = screen_y - UI_HEIGHT + self.camera.y
        return (wx, wy)

    def move(self, dx, dy):
        self.camera.x += dx
        self.camera.y += dy
        max_x = max(0, self.world_w - self.camera.width)
        max_y = max(0, self.world_h - self.camera.height)
        self.camera.x = max(0, min(self.camera.x, max_x))
        self.camera.y = max(0, min(self.camera.y, max_y))

    def reset(self):
        self.camera.x = 0
        self.camera.y = 0

    def center_on(self, wx, wy):
        self.camera.x = wx - self.camera.width / 2
        self.camera.y = wy - self.camera.height / 2
        max_x = max(0, self.world_w - self.camera.width)
        max_y = max(0, self.world_h - self.camera.height)
        self.camera.x = max(0, min(self.camera.x, max_x))
        self.camera.y = max(0, min(self.camera.y, max_y))

class BiomeTextureCache:

    def __init__(self):
        self._cache = {}  # (biome_type, checker_flag, variant, size) -> Surface

    def get_tile(self, biome_type, checker_flag, variant, base_color, size):
        key = (biome_type, checker_flag, variant, size)
        surf = self._cache.get(key)
        if surf is None:
            surf = self._generate_tile(base_color, biome_type, checker_flag, variant, size)
            self._cache[key] = surf
        return surf

    def _generate_tile(self, base_color, biome_type, checker_flag, variant, size):
        surf = pygame.Surface((size, size))
        surf.fill(base_color)

        seed_val = (BIOME_CODE.get(biome_type, 0) * 1000003) ^ (checker_flag * 7919) ^ (variant * 104729)
        rng = random.Random(seed_val & 0xffffffff)

        detail_count = rng.randint(*BIOME_TEXTURE_DETAIL_COUNT)
        for _ in range(detail_count):
            shade = rng.randint(*BIOME_TEXTURE_SHADE_RANGE)
            color = tuple(max(0, min(255, c + shade)) for c in base_color)
            w = rng.randint(4, max(5, size // 3))
            h = rng.randint(4, max(5, size // 3))
            x = rng.randint(0, size - w)
            y = rng.randint(0, size - h)
            pygame.draw.rect(surf, color, (x, y, w, h))
        return surf

class WorldRenderer:
    def __init__(self, game):
        self.game = game
        self.font = pygame.font.SysFont(FONT_NAME, FONT_SIZE_ONSCREEN)
        self.name_font = pygame.font.SysFont(FONT_NAME, FONT_SIZE_NAME)
        self.biome_tiles = BiomeTextureCache()
        self._render_pipeline = self._build_render_pipeline()

    @staticmethod
    def _build_render_pipeline():
        race_layers_by_anchor = {}
        for descriptor in all_races():
            for layer in descriptor.render_layers:
                race_layers_by_anchor.setdefault(layer.insert_after, []).append(layer)

        pipeline = []
        for key, fn in CORE_RENDER_LAYERS:
            pipeline.append(fn)
            for layer in race_layers_by_anchor.get(key, []):
                pipeline.append(layer.draw_fn)
        return pipeline

    def draw(self, screen):
        game = self.game
        screen.fill((0, 0, 0))

        if not game.world_loaded:
            self.draw_empty_state(screen)
            return

        self.draw_grid(screen)

        cam = game.camera
        margin = 60
        view_left = cam.x - margin
        view_right = cam.x + cam.camera.width + margin
        view_top = cam.y - margin
        view_bottom = cam.y + cam.camera.height + margin

        def in_view(ox, oy):
            return view_left <= ox <= view_right and view_top <= oy <= view_bottom

        for draw_fn in self._render_pipeline:
            draw_fn(self, screen, game, cam, in_view)

        if game.player.grabbed_object is not None:
            obj = game.player.grabbed_object
            if hasattr(obj, 'x') and hasattr(obj, 'y'):
                pos = game.camera.apply_pos((obj.x, obj.y))
                pygame.draw.circle(screen, (255, 255, 255), (int(pos[0]), int(pos[1])), 16, 2)

        if game.selected_creature and not game.selected_creature.is_dead:
            self.draw_vision_circle(screen, game.selected_creature)

        if game.paused:
            self.draw_pause_overlay(screen)

    def draw_creature_name(self, screen, name, pos):
        sx, sy = pos
        name_surf = self.name_font.render(name, True, (255, 255, 255))
        text_rect = name_surf.get_rect(center=(int(sx), int(sy) - 22))
        bg_rect = text_rect.inflate(8, 4)
        bg = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(bg, (0, 0, 0, 130), bg.get_rect(), border_radius=4)
        screen.blit(bg, bg_rect.topleft)
        screen.blit(name_surf, text_rect.topleft)

    def draw_grid(self, screen):
        game = self.game
        cam = game.camera
        screen_w, screen_h = screen.get_width(), screen.get_height()

        biome_grid = game.biome_manager.grid
        # ---------- Визуальную сетку рисуем ровно тем же размером клетки, что и реальный биом ----------
        cell_size = biome_grid.cell_size if biome_grid is not None else BIOME_CELL_SIZE

        start_x = max(0, cam.x // cell_size)
        start_y = max(0, cam.y // cell_size)
        end_x = min(cam.world_w // cell_size, (cam.x + screen_w) // cell_size + 1)
        end_y = min(cam.world_h // cell_size, (cam.y + (screen_h - UI_HEIGHT)) // cell_size + 1)

        for i in range(int(start_x), int(end_x) + 1):
            for j in range(int(start_y), int(end_y) + 1):
                wx = i * cell_size + cell_size / 2
                wy = j * cell_size + cell_size / 2
                biome = biome_grid.get_at(wx, wy) if biome_grid is not None else BIOME_PLAINS
                checker_flag = (i + j) % 2

                if biome == BIOME_PLAINS:
                    base_color = COLOR_LIGHT if checker_flag == 0 else COLOR_DARK
                else:
                    base_color = BIOME_BASE_COLOR[biome]

                variant = (i * 7919 + j * 104729) % BIOME_TEXTURE_VARIANTS
                tile = self.biome_tiles.get_tile(biome, checker_flag, variant, base_color, int(cell_size))

                rect = (
                    i * cell_size - cam.x,
                    j * cell_size - cam.y + UI_HEIGHT,
                    cell_size, cell_size
                )
                screen.blit(tile, rect)

    def draw_vision_circle(self, screen, creature):
        game = self.game
        pos = game.camera.apply_pos((creature.x, creature.y))
        vision_radius = creature.effective_vision_radius()

        welded_walls, welded_fences = game.welded_landscape_polylines()
        blocking_polylines = list(welded_walls)
        if not creature.can_jump_fences():
            blocking_polylines += welded_fences

        polygon_world = geometry.visibility_polygon(creature.x, creature.y, vision_radius, blocking_polylines)
        polygon_screen = [game.camera.apply_pos(p) for p in polygon_world]

        self._draw_vision_shadow(screen, pos, vision_radius, polygon_screen)

        if len(polygon_screen) >= 2:
            pygame.draw.lines(screen, VISION_CIRCLE_COLOR, True, polygon_screen, 2)

    def _draw_vision_shadow(self, screen, pos, radius, polygon_screen):
        diameter = int(radius * 2) + 4
        if diameter <= 0:
            return
        origin_x = pos[0] - radius - 2
        origin_y = pos[1] - radius - 2

        shade = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
        pygame.draw.circle(shade, (0, 0, 0, VISION_SHADOW_ALPHA),
                           (diameter // 2, diameter // 2), int(radius))

        if len(polygon_screen) >= 3:
            mask = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
            local_poly = [(px - origin_x, py - origin_y) for px, py in polygon_screen]
            pygame.draw.polygon(mask, (255, 255, 255, 255), local_poly)
            shade.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)

        screen.blit(shade, (origin_x, origin_y))

    def draw_empty_state(self, screen):
        txt = self.font.render(INFO_EMPTY_STATE_HINT, True, TEXT_COLOR)
        screen.blit(txt, (screen.get_width() // 2 - txt.get_width() // 2, screen.get_height() // 2))

    def draw_pause_overlay(self, screen):
        txt = self.font.render(INFO_PAUSE_OVERLAY, True, (255, 220, 60))
        screen.blit(txt, (screen.get_width() // 2 - txt.get_width() // 2, UI_HEIGHT + 10))