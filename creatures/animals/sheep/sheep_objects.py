"""Шерсть, выпадающая с овцы после смерти или стрижки."""

from ...all_needed import animal_drop
from . import sheep_settings


class Wool(animal_drop.AnimalDropResource):
    """Практического применения пока нет."""

    type_name = "Шерсть"
    drop_collection_attr = "wools"
    default_lifetime = sheep_settings.WOOL_LIFETIME
    color = sheep_settings.WOOL_COLOR
    color_border = sheep_settings.WOOL_COLOR_BORDER
    size = sheep_settings.WOOL_SIZE
    shape = "square"

    def has_wool(self):
        return self.has_resource()