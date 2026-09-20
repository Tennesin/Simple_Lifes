"""Каталог имён волков."""

from ...all_needed import animal_names

WOLF_MALE_NAMES = [
    "Серый", "Клык", "Хмурый", "Лютый", "Тень",
    "Быстрый", "Одинокий", "Вожак", "Хищник", "Ветер",
]

WOLF_FEMALE_NAMES = [
    "Серая", "Тихая", "Лютая", "Стрела", "Тень",
    "Быстрая", "Одинокая", "Хищница", "Метель", "Ночь",
]

WOLF_NAME_POOLS, random_wolf_name = animal_names.make_animal_name_pools(WOLF_MALE_NAMES, WOLF_FEMALE_NAMES)