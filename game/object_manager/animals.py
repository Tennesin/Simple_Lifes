"""Гибель животного: либо с выпадением ресурсов (убили/умерло), либо тихо (исчезло вне ДОС)."""

from game.animal_registry import all_animals
from creatures.all_needed.weak_owner import WeakEntityMixin

class AnimalService:

    def __init__(self, game):
        self.game = game

    def remove_with_drops(self, animal):
        """Гибель животного: вместо трупа выпадает набор ресурсов из animal.get_drops()."""
        return self._remove(animal, spawn_drops=True)

    def remove_silently(self, animal):
        """Исчезновение замороженного вне ДОС животного: без дропа и без следов."""
        return self._remove(animal, spawn_drops=False)

    # ---------------------------------------------------------------------

    @staticmethod
    def _descriptor_for(animal):
        return next((d for d in all_animals() if isinstance(animal, d.animal_cls)), None)

    def _remove(self, animal, spawn_drops):
        game = self.game
        descriptor = self._descriptor_for(animal)
        if descriptor is None:
            return False
        collection = getattr(game.world, descriptor.world_collection)
        if animal not in collection:
            return False

        collection.remove(animal)
        if spawn_drops:
            self._spawn_drops(animal)

        if game.selected_object is animal:
            game.selected_object = None
        if game.player.grabbed_object is animal:
            game.player.grabbed_object = None
        if game.favorite_id == animal.id:
            game.favorite_id = None
        self._release_ai(animal)
        return True

    def _spawn_drops(self, animal):
        game = self.game
        get_drops = getattr(animal, "get_drops", None)
        if get_drops is None:
            return
        for drop in get_drops():
            attr = getattr(drop, "drop_collection_attr", None)
            if attr is None or not hasattr(game.world, attr):
                continue
            getattr(game.world, attr).append(drop)
            game.simulation.register_dropped_object(attr, drop)

    @staticmethod
    def _release_ai(animal):
        """Обнуляет ссылку ИИ на животное. ИИ ищем по типу (WeakEntityMixin), а не по именам
        атрибутов - новому виду животного не придётся дописывать имя сюда."""
        for name, value in list(vars(animal).items()):
            if isinstance(value, WeakEntityMixin):
                value.entity = None
                setattr(animal, name, None)