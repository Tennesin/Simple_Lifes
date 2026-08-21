"""Универсальные понятия питания.

Категории пищи:
- FOOD_CATEGORY_PLANT - растительная пища (фрукты у Круга, трава у животных)
- FOOD_CATEGORY_RAW_MEAT - сырое мясо (ресурс Meat, objects.py)
- FOOD_CATEGORY_COOKED_MEAT - жареное мясо. ЗАГЛУШКА: соответствующего игрового
  ресурса пока нет. Категория заведена заранее, чтобы диета DIET_OMNIVORE уже
  сейчас была официально верной (всеядные едят фрукты + жареное мясо, но НЕ
  сырое). Мёртвой веткой это не станет: пока ни у одной расы/животного нет
  фактического ресурса с этой категорией в food_category_map, события такого
  поедания просто не наступят.

Типы диеты:
- DIET_HERBIVORE - только растительная пища (трава - у травоядных животных)
- DIET_CARNIVORE - только сырое мясо (волк)
- DIET_OMNIVORE - растительная пища + жареное мясо (Круг). Именно поэтому
  Круг ест фрукты, но не ест сырое мясо: сырое мясо не входит в разрешённые
  категории всеядных."""

from info import INFO_DIET_HERBIVORE, INFO_DIET_CARNIVORE, INFO_DIET_OMNIVORE

DIET_HERBIVORE = "herbivore"
DIET_CARNIVORE = "carnivore"
DIET_OMNIVORE = "omnivore"

FOOD_CATEGORY_PLANT = "plant"
FOOD_CATEGORY_RAW_MEAT = "raw_meat"
FOOD_CATEGORY_COOKED_MEAT = "cooked_meat"

DIET_ALLOWED_CATEGORIES = {
    DIET_HERBIVORE: (FOOD_CATEGORY_PLANT,),
    DIET_CARNIVORE: (FOOD_CATEGORY_RAW_MEAT,),
    DIET_OMNIVORE: (FOOD_CATEGORY_PLANT, FOOD_CATEGORY_COOKED_MEAT),
}

DIET_DISPLAY_MAP = {
    DIET_HERBIVORE: INFO_DIET_HERBIVORE,
    DIET_CARNIVORE: INFO_DIET_CARNIVORE,
    DIET_OMNIVORE: INFO_DIET_OMNIVORE,
}

def diet_allows_category(diet, category):
    """Допускает ли данная диета данную категорию пищи."""
    return category in DIET_ALLOWED_CATEGORIES.get(diet, ())