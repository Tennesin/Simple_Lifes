"""Каталог имён овец - отдельный от общего names.py (используется людьми/Кругами)."""

from ...all_needed import animal_names

SHEEP_MALE_NAMES = [
    "Барашек", "Пушок", "Кучерявый", "Снежок", "Курчавый",
    "Белогривый", "Пух", "Ватный", "Облачко", "Мохнатый",
]

SHEEP_FEMALE_NAMES = [
    "Пушинка", "Кудряшка", "Снежинка", "Ватка", "Белянка",
    "Овечка", "Мохнатка", "Пуховка", "Кучеряшка", "Облачка",
]

SHEEP_NAME_POOLS, random_sheep_name = animal_names.make_animal_name_pools(SHEEP_MALE_NAMES, SHEEP_FEMALE_NAMES)