"""Универсальный формат текстового наполнения игровой инструкции."""

from dataclasses import dataclass, field
from typing import Callable, Optional, Tuple, Union

# =========================================================================
# Семантические цвета - переиспользуем уже принятые в проекте оттенки,
# чтобы инструкция не жила своей отдельной палитрой поверх основной игры.
# =========================================================================

INSTRUCTION_COLOR_DEFAULT = (225, 225, 225)         # ~ WORLD_SCREEN_TEXT
INSTRUCTION_COLOR_MALE = (200, 30, 30)              # = CREATURE_COLOR_MALE
INSTRUCTION_COLOR_FEMALE = (230, 100, 180)          # = CREATURE_COLOR_FEMALE
INSTRUCTION_COLOR_WARNING = (230, 90, 90)           # ~ WORLD_SCREEN_ERROR_COLOR
INSTRUCTION_COLOR_GOOD = (90, 230, 120)             # тон "полезной" дороги (Road.draw)
INSTRUCTION_COLOR_NEUTRAL_ACCENT = (200, 200, 120)  # числовой акцент (возраст, время)
INSTRUCTION_COLOR_HINT = (140, 140, 140)            # приглушённый текст-подсказка

# =========================================================================
# Блоки содержимого - минимальный набор, достаточный чтобы избежать
# монолита обычного текста: заголовок / абзац / пункт с иконкой / врезка.
# =========================================================================

@dataclass(frozen=True)
class InstructionHeader:
    """Подзаголовок внутри раздела (например 'Стадии жизни')."""
    text: str

@dataclass(frozen=True)
class InstructionParagraph:
    """Обычный абзац. color=None -> берётся цвет по умолчанию при отрисовке."""
    text: str
    color: Optional[Tuple[int, int, int]] = None

@dataclass(frozen=True)
class InstructionBullet:
    """Пункт списка. icon - строковый ключ варианта иконки."""
    text: str
    color: Optional[Tuple[int, int, int]] = None
    icon: Optional[str] = None

@dataclass(frozen=True)
class InstructionCallout:
    """Акцентная врезка (предупреждение / 'это не баг' / важное замечание)."""
    text: str
    color: Tuple[int, int, int] = INSTRUCTION_COLOR_WARNING


InstructionBlock = Union[InstructionHeader, InstructionParagraph, InstructionBullet, InstructionCallout]

# =========================================================================
# Запись списка (одна раса / одно животное) - сворачиваемая карточка.
# =========================================================================

@dataclass(frozen=True)
class InstructionEntry:
    key: str                                            # race_name / animal_name
    title: str                                           # "Круг", "Корова"
    sections: Tuple[InstructionBlock, ...] = field(default_factory=tuple)
    preview_icon: Optional[str] = None                   # вариант иконки для строки-заголовка
    icon_factory: Optional[Callable[[str], object]] = None

# =========================================================================
# Категория верхнего уровня ("Основы", "Расы", "Животные", "Полезное").
# =========================================================================

@dataclass(frozen=True)
class InstructionCategory:
    key: str
    label: str
    sections: Tuple[InstructionBlock, ...] = field(default_factory=tuple)
    entries: Tuple[InstructionEntry, ...] = field(default_factory=tuple)

    @property
    def is_list(self):
        return bool(self.entries)

# =========================================================================
# Перенос текста по словам - используется отрисовщиком блоков (game/widgets.py).
# =========================================================================

def wrap_instruction_text(font, text, max_width):
    words = text.split(' ')
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines if lines else [""]

def truncate_text(font, text, max_width):
    """Обрезает text до ширины max_width пикселей, добавляя многоточие,
    если он не влезает целиком."""
    if not text or font.size(text)[0] <= max_width:
        return text
    while text and font.size(text + "…")[0] > max_width:
        text = text[:-1]
    return (text + "…") if text else "…"


def draw_wrapped_text(screen, font, text, x, y, max_width, color, line_height=22):
    """Переносит text по словам под max_width и рисует построчно, начиная с (x, y)."""
    for line in wrap_instruction_text(font, text, max_width):
        line_surf = font.render(line, True, color)
        screen.blit(line_surf, (x, y))
        y += line_height
    return y