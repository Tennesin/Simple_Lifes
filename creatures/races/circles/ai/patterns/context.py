from dataclasses import dataclass, field
from typing import Optional

@dataclass
class DecisionContext:
    """Контекст одного тика принятия решений у взрослого/старика.
    Именованные поля с default_factory - никакой позиционной хрупкости:
    добавление нового поля в середину больше не сдвигает остальные."""
    visible_fruits: list = field(default_factory=list)
    visible_spikes: list = field(default_factory=list)
    visible_water: list = field(default_factory=list)
    visible_bushes: list = field(default_factory=list)
    visible_campfires: list = field(default_factory=list)
    visible_companions: list = field(default_factory=list)
    other_creatures: list = field(default_factory=list)
    visible_roads: list = field(default_factory=list)
    all_roads: list = field(default_factory=list)
    storage_fields: list = field(default_factory=list)
    visible_corpses: list = field(default_factory=list)
    graveyards: list = field(default_factory=list)
    houses: list = field(default_factory=list)
    dt: float = 0.0
    other_by_id: Optional[dict] = None
    road_crossings: Optional[list] = None
    visible_child_roads: list = field(default_factory=list)
    all_child_roads: list = field(default_factory=list)
    biome_grid: object = None
    visible_trees: list = field(default_factory=list)
    visible_stones: list = field(default_factory=list)
    all_trees: list = field(default_factory=list)
    all_stones: list = field(default_factory=list)
    campfires: list = field(default_factory=list)
    construction_sites: list = field(default_factory=list)
    all_threats: list = field(default_factory=list)
    all_grass: list = field(default_factory=list)