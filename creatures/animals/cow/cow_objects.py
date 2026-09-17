"""Ресурсы, выпадающие с коровы после процедуры или смерти."""

from ...all_needed.animal_drop import AnimalDropResource
from .cow_settings import LEATHER_LIFETIME, LEATHER_COLOR, LEATHER_COLOR_BORDER, LEATHER_SIZE

class Leather(AnimalDropResource):
    """Кожа коровы."""

    type_name = "Кожа"
    drop_collection_attr = "leathers"
    default_lifetime = LEATHER_LIFETIME
    color = LEATHER_COLOR
    color_border = LEATHER_COLOR_BORDER
    size = LEATHER_SIZE
    shape = "diamond"

    def has_leather(self):
        return self.has_resource()