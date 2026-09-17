"""Миникарта — core-пайплайн слоёв + расовые слои через insert_after
(по образцу WorldRenderer._build_render_pipeline)."""

import math
import pygame

from settings import *
from game.race_registry import all_minimap_layers
from game.animal_registry import all_animals


def _mm_draw_roads(panel, screen, game, to_minimap, scale, display):
    if display["minimap_show_roads"]:
        for road in game.world.roads:
            if road.rating == "useful" and len(road.points) >= 2:
                pts = [to_minimap(px, py) for px, py in road.points]
                pygame.draw.lines(screen, (255, 255, 255), False, pts, 1)

def _mm_draw_landscape(panel, screen, game, to_minimap, scale, display):
    for wall in game.world.walls:
        if len(wall.points) >= 2:
            pts = [to_minimap(px, py) for px, py in wall.points]
            pygame.draw.lines(screen, WALL_COLOR, False, pts, 2)
    for fence in game.world.fences:
        if len(fence.points) >= 2:
            pts = [to_minimap(px, py) for px, py in fence.points]
            pygame.draw.lines(screen, FENCE_COLOR, False, pts, 1)

def _mm_draw_water(panel, screen, game, to_minimap, scale, display):
    if display["minimap_show_water"]:
        for water in game.world.water_puddles:
            pos = to_minimap(water.x, water.y)
            pygame.draw.circle(screen, (60, 140, 220), (int(pos[0]), int(pos[1])), 2)

def _mm_draw_bushes(panel, screen, game, to_minimap, scale, display):
    if display["minimap_show_bushes"]:
        for bush in game.world.bushes:
            pos = to_minimap(bush.x, bush.y)
            pygame.draw.circle(screen, BUSH_COLOR, (int(pos[0]), int(pos[1])), 2)

def _mm_draw_trees(panel, screen, game, to_minimap, scale, display):
    if display["minimap_show_trees"]:
        for tree in game.world.trees:
            pos = to_minimap(tree.x, tree.y)
            pygame.draw.circle(screen, TREE_COLOR_LEAVES, (int(pos[0]), int(pos[1])), 2)

def _mm_draw_stones(panel, screen, game, to_minimap, scale, display):
    if display["minimap_show_stones"]:
        for stone in game.world.stones:
            pos = to_minimap(stone.x, stone.y)
            pygame.draw.circle(screen, STONE_COLOR, (int(pos[0]), int(pos[1])), 2)

def _mm_draw_fruits(panel, screen, game, to_minimap, scale, display):
    if display["minimap_show_fruits"]:
        for fruit in game.world.fruits:
            if fruit.active:
                pos = to_minimap(fruit.x, fruit.y)
                pygame.draw.circle(screen, FRUIT_COLOR, (int(pos[0]), int(pos[1])), 2)

def _mm_draw_spikes(panel, screen, game, to_minimap, scale, display):
    if display["minimap_show_spikes"]:
        for spike in game.world.spikes:
            pos = to_minimap(spike.x, spike.y)
            pygame.draw.circle(screen, (255, 165, 0), (int(pos[0]), int(pos[1])), 2)

def _mm_draw_creatures(panel, screen, game, to_minimap, scale, display):
    for creature in game.world.creatures:
        pos = to_minimap(creature.x, creature.y)
        color = creature.draw_minimap_color() if hasattr(creature, "draw_minimap_color") else (200, 30, 30)
        pygame.draw.circle(screen, color, (int(pos[0]), int(pos[1])), 2)

def _default_animal_minimap_marker(screen, pos):
    pygame.draw.circle(screen, (225, 205, 90), (int(pos[0]), int(pos[1])), 2)

def _mm_draw_animals(panel, screen, game, to_minimap, scale, display):
    for descriptor in all_animals():
        checkbox_key = f"minimap_show_animal_{descriptor.animal_name}"
        if not display.get(checkbox_key, True):
            continue
        draw_marker = descriptor.minimap_marker_fn or _default_animal_minimap_marker
        for animal in getattr(game.world, descriptor.world_collection):
            pos = to_minimap(animal.x, animal.y)
            draw_marker(screen, pos)

_CORE_MINIMAP_LAYERS = (
    ("roads", _mm_draw_roads),
    ("landscape", _mm_draw_landscape),
    ("water", _mm_draw_water),
    ("bushes", _mm_draw_bushes),
    ("trees", _mm_draw_trees),
    ("stones", _mm_draw_stones),
    ("fruits", _mm_draw_fruits),
    ("spikes", _mm_draw_spikes),
    ("creatures", _mm_draw_creatures),
    ("animals", _mm_draw_animals),
)

class MinimapPanel:

    def __init__(self, game, font):
        self.game = game
        self.font = font
        self.rect = pygame.Rect(0, 0, MINIMAP_MAX_WIDTH, MINIMAP_MAX_HEIGHT)
        self._biome_layer = None
        self._biome_layer_key = None
        self._pipeline = self._build_pipeline()
        self._dos_overlay_surface = None
        self._dos_cut_surface = None
        self._dos_surfaces_size = None
        self.rebuild_layout(WINDOW_WIDTH, WINDOW_HEIGHT)

    @staticmethod
    def _build_pipeline():
        race_layers_by_anchor = {}
        for layer in all_minimap_layers():
            race_layers_by_anchor.setdefault(layer.insert_after, []).append(layer)

        pipeline = []
        for key, fn in _CORE_MINIMAP_LAYERS:
            pipeline.append(fn)
            for layer in race_layers_by_anchor.get(key, []):
                pipeline.append(layer.draw_fn)
        return pipeline

    def rebuild_layout(self, window_w, window_h):
        world_w = self.game.camera.world_w
        world_h = self.game.camera.world_h
        ratio = world_w / world_h

        if ratio >= 1:
            mm_w = MINIMAP_MAX_WIDTH
            mm_h = int(mm_w / ratio)
            if mm_h < MINIMAP_MIN_HEIGHT:
                mm_h = MINIMAP_MIN_HEIGHT
                mm_w = int(mm_h * ratio)
        else:
            mm_h = MINIMAP_MAX_HEIGHT
            mm_w = int(mm_h * ratio)
            if mm_w < MINIMAP_MIN_WIDTH:
                mm_w = MINIMAP_MIN_WIDTH
                mm_h = int(mm_w / ratio)

        mm_w = min(mm_w, MINIMAP_MAX_WIDTH)
        mm_h = min(mm_h, MINIMAP_MAX_HEIGHT)

        self.rect = pygame.Rect(
            MINIMAP_MARGIN, window_h - mm_h - MINIMAP_MARGIN,
            mm_w, mm_h
        )

    def _draw_biomes(self, screen, rect):
        game = self.game
        grid = game.biome_manager.grid
        if grid is None:
            return

        cache_key = (id(grid), game.world.landscape_version, rect.width, rect.height)
        if self._biome_layer is None or self._biome_layer_key != cache_key:
            self._biome_layer = self._build_biome_layer(grid, rect.width, rect.height)
            self._biome_layer_key = cache_key

        screen.blit(self._biome_layer, rect.topleft)

    def _build_biome_layer(self, grid, width, height):
        layer = pygame.Surface((width, height))
        scale_x = width / self.game.camera.world_w
        scale_y = height / self.game.camera.world_h
        cell_w = max(1, int(math.ceil(grid.cell_size * scale_x)))
        cell_h = max(1, int(math.ceil(grid.cell_size * scale_y)))

        for row in range(grid.rows):
            py = int(row * grid.cell_size * scale_y)
            for col in range(grid.cols):
                biome = grid.cells[row * grid.cols + col]
                color = MINIMAP_BIOME_COLOR.get(biome, MINIMAP_BIOME_COLOR[BIOME_PLAINS])
                px = int(col * grid.cell_size * scale_x)
                pygame.draw.rect(layer, color, (px, py, cell_w, cell_h))
        return layer

    def draw(self, screen):
        game = self.game
        display = game.display_settings
        rect = self.rect
        pygame.draw.rect(screen, MINIMAP_BG_COLOR, rect)

        self._draw_biomes(screen, rect)

        scale_x = rect.width / game.camera.world_w
        scale_y = rect.height / game.camera.world_h

        def to_minimap(wx, wy):
            return (rect.x + wx * scale_x, rect.y + wy * scale_y)

        for draw_fn in self._pipeline:
            draw_fn(self, screen, game, to_minimap, (scale_x, scale_y), display)

        favorite = self._find_favorite_entity(game.favorite_id)
        self._draw_dos_overlay(screen, rect, (scale_x, scale_y), favorite)
        if favorite is not None:
            self._draw_favorite_marker(screen, to_minimap, favorite)

        cam = game.camera
        view_x = rect.x + cam.x * scale_x
        view_y = rect.y + cam.y * scale_y
        view_w = max(2, cam.camera.width * scale_x)
        view_h = max(2, cam.camera.height * scale_y)
        view_rect = pygame.Rect(int(view_x), int(view_y), int(view_w), int(view_h))
        pygame.draw.rect(screen, MINIMAP_VIEWPORT_COLOR, view_rect, 2)

        pygame.draw.rect(screen, MINIMAP_BORDER_COLOR, rect, 2)

        hint_txt = self.font.render("Tab", True, (170, 170, 170))
        screen.blit(hint_txt, (rect.right - hint_txt.get_width() - 4, rect.y - 20))

    def _find_favorite_entity(self, favorite_id):
        if favorite_id is None:
            return None
        game = self.game
        for c in game.world.creatures:
            if c.id == favorite_id and not c.is_dead:
                return c
        for descriptor in all_animals():
            for animal in getattr(game.world, descriptor.world_collection):
                if animal.id == favorite_id:
                    return animal
        return None

    def _get_dos_surfaces(self, size):
        if self._dos_surfaces_size != size:
            self._dos_overlay_surface = pygame.Surface(size, pygame.SRCALPHA)
            self._dos_cut_surface = pygame.Surface(size, pygame.SRCALPHA)
            self._dos_surfaces_size = size
        return self._dos_overlay_surface, self._dos_cut_surface

    def _draw_dos_overlay(self, screen, rect, scale, favorite):
        game = self.game
        scale_x, scale_y = scale

        overlay, cut = self._get_dos_surfaces(rect.size)
        overlay.fill((0, 0, 0, MINIMAP_SIMULATION_AREA_ALPHA))
        cut.fill((0, 0, 0, 0))

        units = game.display_settings.get("simulation_area_units", SIMULATION_AREA_DEFAULT_UNITS)
        units = max(SIMULATION_AREA_MIN_UNITS, min(SIMULATION_AREA_MAX_UNITS, units))
        margin = units * SIMULATION_AREA_PX_PER_UNIT
        cam = game.camera

        sim_x = (cam.x - margin) * scale_x
        sim_y = (cam.y - margin) * scale_y
        sim_w = (cam.camera.width + margin * 2) * scale_x
        sim_h = (cam.camera.height + margin * 2) * scale_y
        pygame.draw.rect(cut, (255, 255, 255, 255),
                         pygame.Rect(int(sim_x), int(sim_y), int(sim_w), int(sim_h)))

        if favorite is not None:
            vision = (favorite.effective_vision_radius()
                      if hasattr(favorite, "effective_vision_radius") else DEFAULT_VISION_RADIUS)
            local_x = favorite.x * scale_x
            local_y = favorite.y * scale_y
            radius_px = vision * scale_x
            pygame.draw.circle(cut, (255, 255, 255, 255), (int(local_x), int(local_y)), int(radius_px))

        overlay.blit(cut, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
        screen.blit(overlay, rect.topleft)

    def _draw_favorite_marker(self, screen, to_minimap, favorite):
        from game.widgets import star_points
        fx, fy = to_minimap(favorite.x, favorite.y)
        size = MINIMAP_FAVORITE_STAR_SIZE
        points = star_points(fx, fy, size, size * 0.45)
        pygame.draw.polygon(screen, FAVORITE_STAR_COLOR, points)
        pygame.draw.polygon(screen, FAVORITE_STAR_BORDER, points, 1)