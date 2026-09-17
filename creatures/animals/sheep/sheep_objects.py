"""Шерсть, выпадающая с овцы после смерти или стрижки."""

from ...all_needed.animal_drop import AnimalDropResource
from .sheep_settings import WOOL_LIFETIME, WOOL_COLOR, WOOL_COLOR_BORDER, WOOL_SIZE

class Wool(AnimalDropResource):
    """Практического применения пока нет."""

    type_name = "Шерсть"
    drop_collection_attr = "wools"
    default_lifetime = WOOL_LIFETIME
    color = WOOL_COLOR
    color_border = WOOL_COLOR_BORDER
    size = WOOL_SIZE
    shape = "square"

    def has_wool(self):
        return self.has_resource()