"""Каталог имён волков."""

import random

WOLF_MALE_NAMES = [
    "Серый", "Клык", "Хмурый", "Лютый", "Тень",
    "Быстрый", "Одинокий", "Вожак", "Хищник", "Ветер",
]

WOLF_FEMALE_NAMES = [
    "Серая", "Тихая", "Лютая", "Стрела", "Тень",
    "Быстрая", "Одинокая", "Хищница", "Метель", "Ночь",
]

WOLF_NAME_POOLS = {
    "male": WOLF_MALE_NAMES,
    "female": WOLF_FEMALE_NAMES,
}

def random_wolf_name(gender_key):
    pool = WOLF_NAME_POOLS.get(gender_key) or WOLF_MALE_NAMES
    return random.choice(pool)