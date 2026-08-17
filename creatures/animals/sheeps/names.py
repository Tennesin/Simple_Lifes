"""Каталог имён овец - отдельный от общего names.py (используется людьми/Кругами)."""

import random

SHEEP_MALE_NAMES = [
    "Барашек", "Пушок", "Кучерявый", "Снежок", "Курчавый",
    "Белогривый", "Пух", "Ватный", "Облачко", "Мохнатый",
]

SHEEP_FEMALE_NAMES = [
    "Пушинка", "Кудряшка", "Снежинка", "Ватка", "Белянка",
    "Овечка", "Мохнатка", "Пуховка", "Кучеряшка", "Облачка",
]

SHEEP_NAME_POOLS = {
    "male": SHEEP_MALE_NAMES,
    "female": SHEEP_FEMALE_NAMES,
}

def random_sheep_name(gender_key):
    pool = SHEEP_NAME_POOLS.get(gender_key) or SHEEP_MALE_NAMES
    return random.choice(pool)