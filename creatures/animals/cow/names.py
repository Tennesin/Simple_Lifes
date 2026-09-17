"""Каталог имён коров."""

from ...all_needed.animal_names import make_animal_name_pools

COW_MALE_NAMES = [
    "Бурёнок", "Мычун", "Рогач", "Бык", "Тяжеловес",
    "Пятныш", "Крепыш", "Бодун", "Громко", "Толстяк",
]

COW_FEMALE_NAMES = [
    "Бурёнка", "Пеструшка", "Мурка", "Зорька", "Ночка",
    "Ромашка", "Пятнашка", "Милка", "Красотка", "Дочка",
]

COW_NAME_POOLS, random_cow_name = make_animal_name_pools(COW_MALE_NAMES, COW_FEMALE_NAMES)