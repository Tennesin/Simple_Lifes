"""Ресурсы, выпадающие с коровы после процедуры или смерти."""

from ...all_needed import animal_drop
from . import cow_settings


class Leather(animal_drop.AnimalDropResource):
    """Кожа коровы."""

    type_name = "Кожа"
    drop_collection_attr = "leathers"
    default_lifetime = cow_settings.LEATHER_LIFETIME
    color = cow_settings.LEATHER_COLOR
    color_border = cow_settings.LEATHER_COLOR_BORDER
    size = cow_settings.LEATHER_SIZE
    shape = "diamond"

    def has_leather(self):
        return self.has_resource()