"""Шкура, выпадающая с волка после смерти."""

from ...all_needed.animal_drop import AnimalDropResource
from .wolf_settings import HIDE_LIFETIME, HIDE_COLOR, HIDE_COLOR_BORDER, HIDE_SIZE

class Hide(AnimalDropResource):
    type_name = "Шкура"
    drop_collection_attr = "hides"
    default_lifetime = HIDE_LIFETIME
    color = HIDE_COLOR
    color_border = HIDE_COLOR_BORDER
    size = HIDE_SIZE
    shape = "diamond"

    def has_hide(self):
        return self.has_resource()