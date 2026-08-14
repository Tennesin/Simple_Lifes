"""Универсальные понятия питания."""

from info import INFO_DIET_HERBIVORE, INFO_DIET_CARNIVORE, INFO_DIET_OMNIVORE

DIET_HERBIVORE = "herbivore"
DIET_CARNIVORE = "carnivore"
DIET_OMNIVORE = "omnivore"

FOOD_CATEGORY_PLANT = "plant"
FOOD_CATEGORY_MEAT = "meat"

DIET_ALLOWED_CATEGORIES = {
    DIET_HERBIVORE: (FOOD_CATEGORY_PLANT,),
    DIET_CARNIVORE: (FOOD_CATEGORY_MEAT,),
    DIET_OMNIVORE: (FOOD_CATEGORY_PLANT, FOOD_CATEGORY_MEAT),
}

DIET_DISPLAY_MAP = {
    DIET_HERBIVORE: INFO_DIET_HERBIVORE,
    DIET_CARNIVORE: INFO_DIET_CARNIVORE,
    DIET_OMNIVORE: INFO_DIET_OMNIVORE,
}

def diet_allows_category(diet, category):
    """Допускает ли данная диета данную категорию пищи."""
    return category in DIET_ALLOWED_CATEGORIES.get(diet, ())