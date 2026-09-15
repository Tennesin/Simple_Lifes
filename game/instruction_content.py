"""Содержимое Инструкции, не зависящее от creatures/: 'Основы' и 'Полезное',
плюс сборка полного набора категорий (включая расы и животных - строго
через реестры)."""

import pygame

from settings import (
    FRUIT_COLOR, FRUIT_COLOR_BORDER, BUSH_COLOR, BUSH_COLOR_BORDER,
    TREE_COLOR_LEAVES, TREE_COLOR_LEAVES_BORDER, STONE_COLOR, STONE_COLOR_BORDER,
    GRASS_COLOR, GRASS_COLOR_DARK, MEAT_COLOR, MEAT_COLOR_BORDER,
    COLOR_LIGHT, COLOR_DARK, BIOME_BASE_COLOR, BIOME_DESERT, BIOME_RIVER, BIOME_SEA,
)
from creatures.all_needed.instruction_icons import IconCache
from creatures.all_needed.instruction import (
    InstructionHeader, InstructionParagraph, InstructionBullet, InstructionCallout,
    InstructionCategory, INSTRUCTION_COLOR_GOOD, INSTRUCTION_COLOR_WARNING,
    INSTRUCTION_COLOR_HINT, INSTRUCTION_COLOR_NEUTRAL_ACCENT,
)
from game.race_registry import all_race_instruction_entries, all_player_tools, all_road_networks
from game.animal_registry import all_animal_instruction_entries

# =========================================================================
# Простые core-иконки: объект = форма + заливка + обводка
# =========================================================================

_SHAPE_CIRCLE, _SHAPE_ELLIPSE, _SHAPE_SQUARE, _SHAPE_BLADE, _SHAPE_CROSS = (
    "circle", "ellipse", "square", "blade", "cross")

_CORE_ICON_SPECS = {
    "fruit": (_SHAPE_CIRCLE, FRUIT_COLOR, FRUIT_COLOR_BORDER),
    "bush": (_SHAPE_CIRCLE, BUSH_COLOR, BUSH_COLOR_BORDER),
    "tree": (_SHAPE_CIRCLE, TREE_COLOR_LEAVES, TREE_COLOR_LEAVES_BORDER),
    "stone": (_SHAPE_CIRCLE, STONE_COLOR, STONE_COLOR_BORDER),
    "water": (_SHAPE_ELLIPSE, (60, 140, 220), (30, 90, 170)),
    "meat": (_SHAPE_ELLIPSE, MEAT_COLOR, MEAT_COLOR_BORDER),
    "grass": (_SHAPE_BLADE, GRASS_COLOR, GRASS_COLOR_DARK),
    "spike": (_SHAPE_CROSS, (255, 165, 0), (0, 0, 0)),
    "biome_plains": (_SHAPE_SQUARE, COLOR_LIGHT, COLOR_DARK),
    "biome_desert": (_SHAPE_SQUARE, BIOME_BASE_COLOR[BIOME_DESERT], (150, 120, 60)),
    "biome_river": (_SHAPE_SQUARE, BIOME_BASE_COLOR[BIOME_RIVER], (40, 100, 170)),
    "biome_sea": (_SHAPE_SQUARE, BIOME_BASE_COLOR[BIOME_SEA], (10, 35, 100)),
}

_CORE_ICON_CACHE = IconCache()


def _build_core_icon(variant_key, size):
    spec = _CORE_ICON_SPECS.get(variant_key)
    if spec is None:
        return None
    shape, fill, border = spec

    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    center = (size // 2, size // 2)
    radius = max(2, size // 2 - 2)

    if shape == _SHAPE_CIRCLE:
        pygame.draw.circle(surf, fill, center, radius)
        pygame.draw.circle(surf, border, center, radius, 2)
    elif shape == _SHAPE_ELLIPSE:
        rect = pygame.Rect(2, size // 4, size - 4, size // 2)
        pygame.draw.ellipse(surf, fill, rect)
        pygame.draw.ellipse(surf, border, rect, 2)
    elif shape == _SHAPE_SQUARE:
        rect = pygame.Rect(2, 2, size - 4, size - 4)
        pygame.draw.rect(surf, fill, rect)
        pygame.draw.rect(surf, border, rect, 1)
    elif shape == _SHAPE_BLADE:
        base_y = size - 3
        for i, offset in enumerate((-5, 0, 5)):
            color = fill if i % 2 == 0 else border
            tip = (center[0] + offset, 3)
            pygame.draw.polygon(surf, color, [
                (center[0] + offset - 3, base_y), (center[0] + offset + 3, base_y), tip])
    elif shape == _SHAPE_CROSS:
        pygame.draw.circle(surf, fill, center, radius)
        pygame.draw.line(surf, border, (center[0] - 5, center[1]), (center[0] + 5, center[1]), 2)
        pygame.draw.line(surf, border, (center[0], center[1] - 5), (center[0], center[1] + 5), 2)

    return surf


def core_instruction_icon(variant_key, size=20):
    if variant_key not in _CORE_ICON_SPECS:
        return None
    return _CORE_ICON_CACHE.get((variant_key, size), lambda: _build_core_icon(variant_key, size))


# =========================================================================
# Категория "Основы"
# =========================================================================

CORE_INSTRUCTION_SECTIONS = (
    InstructionParagraph(
        "Simple_Lifes - симулятор жизни, а не стратегия. Вы не отдаёте приказов: существа "
        "сами решают, куда идти, что есть, с кем дружить и что строить. Ваша роль - роль "
        "обстоятельств: вы создаёте мир, меняете ландшафт, подкидываете ресурсы, рисуете "
        "дороги и наблюдаете, что из этого выйдет."),

    InstructionHeader("Мир"),
    InstructionBullet("Мир создаётся один раз: задаются имя, размер, сид и соотношение биомов. "
                      "Один и тот же сид всегда даёт одну и ту же карту."),
    InstructionBullet("Мир сохраняется отдельной папкой и переживает выход из игры. "
                      "Автосохранение включено по умолчанию."),
    InstructionBullet("Мини-карта показывает биомы, объекты и текущую область обзора."),

    InstructionHeader("Биомы"),
    InstructionBullet("Равнина - основная земля. Только здесь растут деревья, кусты и трава.",
                      icon="biome_plains"),
    InstructionBullet("Пустыня - проходима, но жажда и силы тратятся быстрее, а тревожность "
                      "растёт. Трава на песке не живёт.", icon="biome_desert"),
    InstructionBullet("Река - проходима вплавь вдвое медленнее, зато из неё можно пить прямо "
                      "на ходу.", icon="biome_river"),
    InstructionBullet("Море - смертельно для всех. В море нельзя войти по своей воле: "
                      "маршруты строятся в обход.", icon="biome_sea"),
    InstructionCallout(
        "Кисть биомов перерисовывает мир на лету. Залив местность морем или рекой, вы "
        "уничтожите всё, что там стояло, - включая дома, склады и кладбища."),

    InstructionHeader("Природные объекты"),
    InstructionBullet("Куст - периодически рождает рядом с собой фрукты.", icon="bush"),
    InstructionBullet("Фрукт - основная еда разумных рас.", icon="fruit"),
    InstructionBullet("Водоём - ограниченный запас воды; исчерпав заряды, он пересыхает "
                      "и исчезает.", icon="water"),
    InstructionBullet("Дерево - источник древесины для построек.", icon="tree"),
    InstructionBullet("Камень - источник камня для построек.", icon="stone"),
    InstructionBullet("Трава - еда травоядных животных. Выеденная поляна уменьшается "
                      "на глазах.", icon="grass"),
    InstructionBullet("Мясо - выпадает из погибших животных, со временем портится.", icon="meat"),
    InstructionBullet("Шипы - ранят любого, кто подойдёт вплотную, и отбрасывают его прочь.",
                      icon="spike", color=INSTRUCTION_COLOR_WARNING),
    InstructionParagraph(
        "Деревья, кусты, камни и трава со временем вырастают заново сами, но не бесконечно: "
        "у каждого вида есть предел численности.", color=INSTRUCTION_COLOR_HINT),

    InstructionHeader("Ландшафт игрока"),
    InstructionBullet("Стена - непроходима и полностью перекрывает обзор. Существа её "
                      "обходят и не видят сквозь неё."),
    InstructionBullet("Забор - ниже стены: взрослые здоровые существа через него перепрыгивают, "
                      "а дети, старики и беременные - нет."),

    InstructionHeader("Дороги и перекрёстки"),
    InstructionParagraph(
        "Дорогу можно нарисовать зажатой ЛКМ. Пересекаясь, дороги автоматически образуют "
        "перекрёсток, на котором существо может свернуть - либо из любопытства, либо потому "
        "что знает: по той ветке лежит нужный ему ресурс. Концы дороги, упирающиеся в "
        "заметный объект (воду, куст, дерево, костёр), запоминаются как маршрут к нему."),

    InstructionHeader("Как существа находят путь"),
    InstructionParagraph(
        "Если до цели есть прямая видимость, существо идёт напрямую. Если путь перекрыт - "
        "строится обходной маршрут по невидимой сетке проходимости, учитывающей стены, "
        "заборы, шипы и море. В вопросах выживания (еда, вода, бегство) поиск пути "
        "работает старательнее обычного.", color=INSTRUCTION_COLOR_HINT),

    InstructionHeader("Область симуляции"),
    InstructionParagraph(
        "Полноценно живут только существа рядом с камерой - остальные замирают, чтобы игра "
        "не тормозила на больших картах. Размер этой области настраивается. Замороженное "
        "животное, которого игрок никогда не трогал, со временем исчезает."),
    InstructionParagraph(
        "Избранное существо (звезда) - исключение: оно и всё в радиусе его зрения "
        "продолжают жить полноценно, где бы ни находилась камера.",
        color=INSTRUCTION_COLOR_GOOD),
)


# =========================================================================
# Категория "Полезное"
# =========================================================================

_USEFUL_STATIC_SECTIONS = (
    InstructionHeader("Управление камерой и выделением"),
    InstructionBullet("ПКМ (зажать и вести) - перемещение камеры."),
    InstructionBullet("ЛКМ по мини-карте - мгновенно перенести камеру в эту точку."),
    InstructionBullet("ЛКМ по существу или объекту - выбрать его и открыть панель сведений."),
    InstructionBullet("Двойной ЛКМ по объекту - взять его в руку и перенести. Повторный ЛКМ - "
                      "отпустить. Красное кольцо означает, что сюда класть нельзя."),
    InstructionBullet("Ctrl + ЛКМ по объекту - удалить его."),
    InstructionBullet("Delete - удалить выбранный объект."),

    InstructionHeader("Горячие клавиши"),
    InstructionBullet("Пробел - пауза."),
    InstructionBullet("Tab - показать/скрыть мини-карту."),
    InstructionBullet("Escape - шаг назад: отпустить предмет, отменить рисование, выйти из "
                      "инструмента, снять выделение, закрыть меню."),
    InstructionBullet("Стрелки вверх/вниз - прокрутка в этой Инструкции (если не работает "
                      "колёсико). Ползунок справа тоже можно тянуть мышью.",
                      color=INSTRUCTION_COLOR_HINT),

    InstructionHeader("Скрытые возможности"),
    InstructionBullet("Shift + движение мыши с выбранным биомом - плавно менять радиус кисти, "
                      "не рисуя.", color=INSTRUCTION_COLOR_NEUTRAL_ACCENT),
    InstructionBullet("Z + ЛКМ по выбранной стройплощадке - ускорить стройку: вы сами "
                      "подвозите материалы и ведёте работы. Чем больше ваша доля в постройке, "
                      "тем сильнее вырастет отношение хозяина к вам.",
                      color=INSTRUCTION_COLOR_NEUTRAL_ACCENT),
    InstructionBullet("ЛКМ по полоске показателя в панели существа - изменить его на 10%: "
                      "клик по левой половине уменьшает, по правой увеличивает. Существо "
                      "запомнит и хорошее, и плохое.", color=INSTRUCTION_COLOR_NEUTRAL_ACCENT),
    InstructionBullet("ЛКМ по полю имени - дать существу имя. Названное существо считает себя "
                      "особенным и относится к вам заметно теплее.", color=INSTRUCTION_COLOR_GOOD),
    InstructionBullet("Звезда в углу панели - сделать существо избранным."),
    InstructionBullet("Кнопка-стрелка у края панели - свернуть правую панель, чтобы она не "
                      "закрывала обзор."),
    InstructionBullet("Кнопка 'Геном' - древо родословной. Его можно таскать мышью; "
                      "крестик рядом с узлом означает, что этот предок уже мёртв."),

    InstructionHeader("Настройки"),
    InstructionBullet("Отображение - что показывать на мини-карте, имена существ, цветные "
                      "кольца состояния."),
    InstructionBullet("Техническое - автосохранение и размер области симуляции. Уменьшайте "
                      "область, если игра тормозит на большой карте."),
    InstructionParagraph(
        "Настройки сохраняются между запусками игры и не привязаны к конкретному миру.",
        color=INSTRUCTION_COLOR_HINT),
)


def _build_tool_hint_sections():
    """Подсказки инструментов не дублируются вручную, а берутся из тех же
    констант, что показывает сама игра - рассинхронизация невозможна."""
    blocks = [InstructionHeader("Инструменты игрока")]
    for spec in all_player_tools():
        blocks.append(InstructionBullet(f"{spec.label} - {spec.hint}"))
    for spec in all_road_networks():
        if spec.menu_label and spec.menu_hint:
            blocks.append(InstructionBullet(f"{spec.menu_label} - {spec.menu_hint}"))
    return tuple(blocks) if len(blocks) > 1 else ()


# =========================================================================
# Сборка всех категорий - единственная точка, из которой панель берёт данные
# =========================================================================

def build_instruction_categories():
    return (
        InstructionCategory(key="core", label="Основы",
                            sections=CORE_INSTRUCTION_SECTIONS),
        InstructionCategory(key="races", label="Расы",
                            entries=all_race_instruction_entries()),
        InstructionCategory(key="animals", label="Животные",
                            entries=all_animal_instruction_entries()),
        InstructionCategory(key="useful", label="Полезное",
                            sections=_USEFUL_STATIC_SECTIONS + _build_tool_hint_sections()),
    )