"""Шкура, выпадающая с волка после смерти."""

from ...all_needed import animal_drop
from . import wolf_settings

class Hide(animal_drop.AnimalDropResource):
    type_name = "Шкура"
    drop_collection_attr = "hides"
    default_lifetime = wolf_settings.HIDE_LIFETIME
    color = wolf_settings.HIDE_COLOR
    color_border = wolf_settings.HIDE_COLOR_BORDER
    size = wolf_settings.HIDE_SIZE
    shape = "diamond"

    def has_hide(self):
        return self.has_resource()