"""Каталог имён коров."""

import random

COW_MALE_NAMES = [
    "Бурёнок", "Мычун", "Рогач", "Бык", "Тяжеловес",
    "Пятныш", "Крепыш", "Бодун", "Громко", "Толстяк",
]

COW_FEMALE_NAMES = [
    "Бурёнка", "Пеструшка", "Мурка", "Зорька", "Ночка",
    "Ромашка", "Пятнашка", "Милка", "Красотка", "Дочка",
]

COW_NAME_POOLS = {
    "male": COW_MALE_NAMES,
    "female": COW_FEMALE_NAMES,
}

def random_cow_name(gender_key):
    pool = COW_NAME_POOLS.get(gender_key) or COW_MALE_NAMES
    return random.choice(pool)