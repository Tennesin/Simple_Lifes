from dataclasses import dataclass, field
from typing import Optional

from game.race_registry import all_races

def _collect_race_collections():
    names = []
    seen = set()
    for descriptor in all_races():
        for name in descriptor.world_collections:
            if name not in seen:
                seen.add(name)
                names.append(name)
    return tuple(names)

class WorldState:

    CORE_COLLECTIONS = (
        "fruits", "spikes", "water_puddles", "bushes", "trees", "stones",
        "campfires", "creatures", "roads", "road_crossings",
        "walls", "fences",
    )

    RACE_COLLECTIONS = _collect_race_collections()
    COLLECTION_NAMES = CORE_COLLECTIONS + RACE_COLLECTIONS

    def __init__(self):
        self.landscape_version = 0
        self.reset()

    def reset(self):
        for name in self.COLLECTION_NAMES:
            setattr(self, name, [])

@dataclass
class WorldFrameContext:
    dt: float = 0.0

    fruits: list = field(default_factory=list)
    spikes: list = field(default_factory=list)
    water_puddles: list = field(default_factory=list)
    bushes: list = field(default_factory=list)
    campfires: list = field(default_factory=list)
    creatures: list = field(default_factory=list)
    roads: list = field(default_factory=list)
    walls: list = field(default_factory=list)
    fences: list = field(default_factory=list)
    trees: list = field(default_factory=list)
    stones: list = field(default_factory=list)
    road_crossings: list = field(default_factory=list)
    wall_bounds: list = field(default_factory=list)
    fence_bounds: list = field(default_factory=list)

    race_collections: dict = field(default_factory=dict)

    creatures_by_id: Optional[dict] = None
    nav_grid_no_fences: object = None
    nav_grid_with_fences: object = None
    nav_grid_no_fences_fallback: object = None
    nav_grid_with_fences_fallback: object = None
    spatial_grids: Optional[dict] = None
    biome_grid: object = None

    def __getattr__(self, name):
        race_collections = object.__getattribute__(self, "race_collections")
        if name in race_collections:
            return race_collections[name]
        raise AttributeError(name)