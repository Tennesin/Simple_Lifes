from settings import BIOME_BRUSH_DEFAULT_RADIUS, LANDSCAPE_MIN_POINT_DIST
from game.race_registry import all_road_networks

class Player:

    TOOL_PET = "pet"
    TOOL_HIT = "hit"
    TOOL_GRAB = "grab"
    TOOL_ROAD = "road"
    TOOL_WALL = "wall"
    TOOL_FENCE = "fence"
    TOOL_BIOME_PLAINS = "biome_plains"
    TOOL_BIOME_DESERT = "biome_desert"
    TOOL_BIOME_RIVER = "biome_river"
    TOOL_BIOME_SEA = "biome_sea"

    DOUBLE_CLICK_TIME = 0.35
    DOUBLE_CLICK_DIST = 10

    def __init__(self):
        self.tool = None

        self.grabbed_creature = None
        self.grabbed_object = None
        self.grabbed_object_valid = True
        self.last_click_time = 0.0
        self.last_click_pos = (0, 0)
        self.last_click_target = None

        for spec in all_road_networks():
            setattr(self, f"drawing_{spec.obj_type}", None)
        self.road_min_point_dist = 18
        self.landscape_min_point_dist = LANDSCAPE_MIN_POINT_DIST

        self.drawing_landscape = None
        self.landscape_type = None
        self.brush_radius = BIOME_BRUSH_DEFAULT_RADIUS
        self.brush_adjust_start_y = None
        self.brush_adjust_start_radius = None

    def reset_tool(self):
        self.tool = None