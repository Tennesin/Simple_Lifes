"""Универсальная фабрика пулов имён для животных - одна структура
(male_list, female_list, name_pools, random_name), меняются только слова."""

import random

def make_animal_name_pools(male_names, female_names):
    """Возвращает (pools_dict, random_name_fn)."""
    pools = {"male": male_names, "female": female_names}

    def random_animal_name(gender_key):
        pool = pools.get(gender_key) or male_names
        return random.choice(pool)

    return pools, random_animal_name