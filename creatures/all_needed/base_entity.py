import math
import settings
from . import geometry

class BaseEntity:
    """Общий базовый класс для любой позиционируемой игровой сущности."""
    def distance_to(self, obj) -> float:
        return math.hypot(self.x - obj.x, self.y - obj.y)

    def flee_point(self, from_pos, distance):
        return geometry.flee_point(self.x, self.y, from_pos, distance)


class LivingEntity(BaseEntity):
    """Общий контракт живого существа"""
    race_name: str = None

    def get_race_name(self) -> str:
        if self.race_name is None:
            raise NotImplementedError(
                f"{type(self).__name__} должен определить атрибут класса race_name")
        return self.race_name

    def decide(self, ctx):
        raise NotImplementedError

    def update_needs(self, dt, other_creatures=None, biome_grid=None):
        raise NotImplementedError

    def interact(self, *args, **kwargs):
        raise NotImplementedError

    def effective_vision_radius(self):
        return settings.DEFAULT_VISION_RADIUS

    def on_landmark_removed(self, landmark_type, landmark_id, position):
        pass

    def on_road_deleted(self, road_obj_type, road):
        pass

    def on_road_progress_shift(self, obj_type, road, inserted_index):
        pass

    def can_verify_child_road_safety(self):
        return False

    def begin_name_edit(self):
        return self.name if getattr(self, "name", None) else ""

    def commit_name_edit(self, new_name):
        self.name = new_name

    def on_grab_start(self, world):
        pass

    def on_grab_release(self, game):
        return False

    def draw(self, screen, screen_pos, show_status_rings=True):
        raise NotImplementedError

    def save(self, base_path):
        raise NotImplementedError