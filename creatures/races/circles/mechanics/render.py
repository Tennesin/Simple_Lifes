"""Слои отрисовки, специфичные для расы 'Круг'."""

from ..ci_settings import (
    CHILD_ROAD_COLOR_SAFE, CHILD_ROAD_COLOR_DANGEROUS, CHILD_ROAD_COLOR_PENDING,
    STORAGE_FIELD_COLOR_BORDER, GRAVEYARD_COLOR_FILL, GRAVEYARD_COLOR_BORDER,
)

def draw_child_roads(renderer, screen, game, camera, in_view):
    for croad in game.world.child_roads:
        croad.draw(screen, camera)
    if game.player.drawing_child_road is not None:
        game.player.drawing_child_road.draw(screen, camera)
    for crossing in game.world.child_road_crossings:
        if in_view(crossing.x, crossing.y):
            pos = camera.apply_pos((crossing.x, crossing.y))
            crossing.draw(screen, pos)

def draw_storage_fields(renderer, screen, game, camera, in_view):
    for field in game.world.storage_fields:
        if in_view(field.x, field.y):
            pos = camera.apply_pos((field.x, field.y))
            field.draw(screen, pos)

def draw_construction_sites(renderer, screen, game, camera, in_view):
    for site in game.world.construction_sites:
        if in_view(site.x, site.y):
            pos = camera.apply_pos((site.x, site.y))
            site.draw(screen, pos)

def draw_graveyards(renderer, screen, game, camera, in_view):
    for gy in game.world.graveyards:
        if in_view(gy.x, gy.y):
            pos = camera.apply_pos((gy.x, gy.y))
            gy.draw(screen, pos)

def draw_houses(renderer, screen, game, camera, in_view):
    for house in game.world.houses:
        if in_view(house.x, house.y):
            pos = camera.apply_pos((house.x, house.y))
            house.draw(screen, pos)

# =========================================================================
# Слои миникарты, специфичные для расы 'Круг'.
# =========================================================================

def draw_minimap_child_roads(panel, screen, game, to_minimap, scale, display):
    import pygame
    if not display["minimap_show_roads"]:
        return
    for croad in game.world.child_roads:
        if len(croad.points) < 2:
            continue
        if croad.rating == "safe":
            color = CHILD_ROAD_COLOR_SAFE
        elif croad.rating == "dangerous":
            color = CHILD_ROAD_COLOR_DANGEROUS
        else:
            color = CHILD_ROAD_COLOR_PENDING
        pts = [to_minimap(px, py) for px, py in croad.points]
        pygame.draw.lines(screen, color, False, pts, 1)

def draw_minimap_constructions(panel, screen, game, to_minimap, scale, display):
    import pygame
    if not display.get("minimap_show_constructions", True):
        return
    scale_x, scale_y = scale

    for field in game.world.storage_fields:
        pos = to_minimap(field.x, field.y)
        size = max(4, int(field.radius * 2 * scale_x))
        field_rect = pygame.Rect(0, 0, size, size)
        field_rect.center = (int(pos[0]), int(pos[1]))
        pygame.draw.rect(screen, STORAGE_FIELD_COLOR_BORDER, field_rect, 1)

    for gy in game.world.graveyards:
        pos = to_minimap(gy.x, gy.y)
        gy_w = max(4, int(gy.width * scale_x))
        gy_h = max(3, int(gy.height * scale_y))
        gy_rect = pygame.Rect(0, 0, gy_w, gy_h)
        gy_rect.center = (int(pos[0]), int(pos[1]))
        pygame.draw.rect(screen, GRAVEYARD_COLOR_FILL, gy_rect)
        pygame.draw.rect(screen, GRAVEYARD_COLOR_BORDER, gy_rect, 1)