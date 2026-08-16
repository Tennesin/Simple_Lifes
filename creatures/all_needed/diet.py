"""Универсальные понятия питания.

ПРИМЕЧАНИЕ: DIET_CARNIVORE / FOOD_CATEGORY_MEAT намеренно убраны отсюда -
в проекте пока нет ни одного ресурса категории "мясо" (труп/туша как объект
поедания) и ни одна раса им не пользуется. Как только появится модель
"труп -> Carcass -> ресурс" (см. docs/HOW_TO_ADD_RACE.md, раздел про
хищников), нужно будет вернуть DIET_CARNIVORE и FOOD_CATEGORY_MEAT и завести
для них реального потребителя, а не мёртвую ветку API."""

from info import INFO_DIET_HERBIVORE, INFO_DIET_OMNIVORE

DIET_HERBIVORE = "herbivore"
DIET_OMNIVORE = "omnivore"

FOOD_CATEGORY_PLANT = "plant"

DIET_ALLOWED_CATEGORIES = {
    DIET_HERBIVORE: (FOOD_CATEGORY_PLANT,),
    DIET_OMNIVORE: (FOOD_CATEGORY_PLANT,),
}

DIET_DISPLAY_MAP = {
    DIET_HERBIVORE: INFO_DIET_HERBIVORE,
    DIET_OMNIVORE: INFO_DIET_OMNIVORE,
}

def diet_allows_category(diet, category):
    """Допускает ли данная диета данную категорию пищи."""
    return category in DIET_ALLOWED_CATEGORIES.get(diet, ())