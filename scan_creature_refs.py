"""
scan_creature_refs.py - утилита для поиска всех обращений к атрибутам
существа (c.xxx, self.c.xxx, creature.xxx) по проекту.

Кладётся в корень проекта. Не требует внешних зависимостей.

РЕЖИМ 1 - обращения по этапам плана рефакторинга (без аргументов или --stages):
    python scan_creature_refs.py
    python scan_creature_refs.py --stages 1
    -> creature_refs_stages.txt: обращения только к полям, перечисленным
       в PLAN_STAGES ниже, сгруппированные по этапу и по имени поля.
       Список полей в PLAN_STAGES нужно обновлять по мере продвижения плана -
       остальные поля (ещё не запланированные к переносу) в отчёт не попадают,
       чтобы файл не разрастался на весь проект сразу.

РЕЖИМ 2 - точечный поиск произвольных полей (в обход PLAN_STAGES):
    python scan_creature_refs.py --fields puberty_active is_pregnant home_id
    -> creature_refs_search.txt: обращения к указанным полям в простом
       построчном формате "[файл] номер_строки [R/W/CALL] поле: строка_кода".

Настройки (--root, --targets, --out) см. в argparse ниже.
"""

import argparse
import ast
import os
import sys

DEFAULT_ROOT = "creatures/races/circles"
DEFAULT_TARGETS = ("c", "self.c", "creature", "self.creature")
IGNORED_DIR_NAMES = {"__pycache__", ".git", ".idea"}

# =========================================================================
# Реестр полей по этапам плана миграции Creature (см. пошаговый план).
# Обновлять здесь по мере перехода к следующим этапам - остальной код
# трогать не нужно. Этап без полей (например, 0 - подготовка инфраструктуры)
# просто не даёт совпадений и не появляется в отчёте.
# =========================================================================

PLAN_STAGES = {
    0: (
        # Шаг 0 - подготовка state/, StateBlock и т.п.
        # Полей Creature ещё не касается - список пуст намеренно.
    ),
    1: (
        # Шаг 1 - домен "Пубертат" (PubertyState)
        "puberty_trigger_age",
        "puberty_done",
        "puberty_active",
        "puberty_timer",
        "_puberty_speed_bonus",
        "_puberty_orig_curiosity",
        "puberty_courtship_cooldown",
        "puberty_courtship_target_id",
        "puberty_courtship_timer",
        "puberty_courtship_deadline",
        "puberty_courtship_fail_streak",
        "puberty_courtship_avoid",
    ),
    2: (
        # Шаг 2 - домен "Труп/кладбище" (BurialState)
        "being_carried_by",
        "burial_claimant_id",
        "burial_target_id",
        "graveyard_target_id",
        "is_dragging_corpse",
        "known_graveyard",
        "known_graveyard_id",
        "graveyard_alert_pos",
        "graveyard_alert_timer",
    ),
}


def base_expr(node):
    """Возвращает строковый 'путь' выражения слева от точки: для `c` -> 'c',
    для `self.c` -> 'self.c', для чего-то незнакомого (вызов функции,
    индексация и т.п.) -> None."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = base_expr(node.value)
        if base is None:
            return None
        return f"{base}.{node.attr}"
    return None


def add_parents(tree):
    """Простановка .parent у каждого узла - нужно, чтобы отличить
    'c.hp' как чтение поля от 'c.distance_to(x)' как вызов метода."""
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node
    return tree


def classify(node):
    """R - чтение, W - запись (включая del), CALL - вызов метода
    (c.method(...)) - для таких пометка R/W менее осмысленна."""
    parent = getattr(node, "parent", None)
    if isinstance(parent, ast.Call) and parent.func is node:
        return "CALL"
    if isinstance(node.ctx, ast.Store):
        return "W"
    if isinstance(node.ctx, ast.Del):
        return "DEL"
    return "R"


def iter_python_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIR_NAMES]
        for name in filenames:
            if name.endswith(".py"):
                yield os.path.join(dirpath, name)


def scan_file(path, targets):
    """Возвращает список кортежей (field, kind, lineno, line_text)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError) as e:
        print(f"[пропущен] {path}: {e}", file=sys.stderr)
        return []

    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as e:
        print(f"[ошибка синтаксиса] {path}: {e}", file=sys.stderr)
        return []

    add_parents(tree)
    lines = source.splitlines()
    results = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute):
            continue
        base = base_expr(node.value)
        if base not in targets:
            continue
        field = node.attr
        kind = classify(node)
        lineno = node.lineno
        line_text = lines[lineno - 1].strip() if 0 < lineno <= len(lines) else ""
        results.append((field, kind, lineno, line_text))

    return results


def rel(path, root):
    return os.path.relpath(path, root).replace(os.sep, "/")


def run_full_inventory(root, targets, out_path):
    """Полная инвентаризация: группировка по имени поля (все поля без
    фильтра по PLAN_STAGES - используется только при явном --all)."""
    by_field = {}  # field -> list[(file, kind, lineno, text)]

    for path in sorted(iter_python_files(root)):
        for field, kind, lineno, text in scan_file(path, targets):
            by_field.setdefault(field, []).append((path, kind, lineno, text))

    with open(out_path, "w", encoding="utf-8") as out:
        out.write(f"Инвентаризация обращений {sorted(targets)} в '{root}'\n")
        out.write(f"Всего уникальных полей/методов: {len(by_field)}\n")
        out.write("=" * 78 + "\n\n")

        for field in sorted(by_field, key=lambda f: (-len(by_field[f]), f)):
            entries = by_field[field]
            out.write(f"=== {field}  ({len(entries)} обращений) ===\n")
            for path, kind, lineno, text in sorted(entries, key=lambda e: (e[0], e[2])):
                short = rel(path, ".")
                out.write(f"[{short}] {lineno} [{kind}]: {text}\n")
            out.write("\n")

    print(f"Готово: {out_path} ({sum(len(v) for v in by_field.values())} обращений, "
          f"{len(by_field)} уникальных полей)")


def run_targeted_search(root, targets, fields, out_path):
    """Точечный поиск конкретных полей - формат построчного отчёта."""
    fields = set(fields)
    total = 0

    with open(out_path, "w", encoding="utf-8") as out:
        out.write(f"Поиск полей {sorted(fields)} среди {sorted(targets)} в '{root}'\n")
        out.write("=" * 78 + "\n\n")

        for path in sorted(iter_python_files(root)):
            matches = [m for m in scan_file(path, targets) if m[0] in fields]
            if not matches:
                continue
            short = rel(path, ".")
            for field, kind, lineno, text in sorted(matches, key=lambda e: e[2]):
                out.write(f"[{short}] {lineno} [{kind}] {field}: {text}\n")
                total += 1

    print(f"Готово: {out_path} ({total} совпадений)")


def run_staged_inventory(root, targets, stage_numbers, out_path):
    """Обращения только к полям из PLAN_STAGES, сгруппированные по этапу,
    а внутри этапа - по имени поля. Этапы без полей (пока пустые в
    PLAN_STAGES) пропускаются без записи пустой секции."""
    total_matches = 0

    with open(out_path, "w", encoding="utf-8") as out:
        out.write(f"Обращения к полям из PLAN_STAGES, этапы {stage_numbers}, в '{root}'\n")
        out.write("=" * 78 + "\n\n")

        for stage in stage_numbers:
            fields = PLAN_STAGES.get(stage)
            if fields is None:
                print(f"[предупреждение] этап {stage} не описан в PLAN_STAGES - пропущен", file=sys.stderr)
                continue
            if not fields:
                # Этап объявлен, но полей ещё нет (например, шаг 0 - инфраструктура)
                continue

            field_set = set(fields)
            by_field = {}  # field -> list[(file, kind, lineno, text)]

            for path in sorted(iter_python_files(root)):
                for field, kind, lineno, text in scan_file(path, targets):
                    if field in field_set:
                        by_field.setdefault(field, []).append((path, kind, lineno, text))

            stage_total = sum(len(v) for v in by_field.values())
            total_matches += stage_total

            out.write(f"########## ЭТАП {stage} ({len(fields)} полей в плане, {stage_total} обращений) ##########\n\n")

            # Поля этапа перечисляем в порядке PLAN_STAGES, а не по алфавиту -
            # так проще сверяться со списком полей будущего StateBlock.
            for field in fields:
                entries = by_field.get(field, [])
                out.write(f"=== {field}  ({len(entries)} обращений) ===\n")
                if not entries:
                    out.write("  (обращений не найдено)\n")
                for path, kind, lineno, text in sorted(entries, key=lambda e: (e[0], e[2])):
                    short = rel(path, ".")
                    out.write(f"[{short}] {lineno} [{kind}]: {text}\n")
                out.write("\n")

            out.write("\n")

    print(f"Готово: {out_path} ({total_matches} обращений по этапам {stage_numbers})")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=DEFAULT_ROOT,
                        help=f"Папка для сканирования (по умолчанию: {DEFAULT_ROOT})")
    parser.add_argument("--targets", nargs="+", default=list(DEFAULT_TARGETS),
                        help=f"Какие 'базовые' имена считать существом (по умолчанию: {DEFAULT_TARGETS})")
    parser.add_argument("--fields", nargs="+", default=None,
                        help="Точечный поиск только этих полей (игнорирует PLAN_STAGES)")
    parser.add_argument("--stages", nargs="+", type=int, default=sorted(PLAN_STAGES.keys()),
                        help=f"Какие этапы плана включить в отчёт (по умолчанию все описанные: "
                             f"{sorted(PLAN_STAGES.keys())})")
    parser.add_argument("--all", action="store_true",
                        help="Полная инвентаризация ВСЕХ полей без фильтра по PLAN_STAGES "
                             "(даёт большой файл - использовать только осознанно)")
    parser.add_argument("--out", default=None,
                        help="Имя выходного файла (по умолчанию подбирается по режиму)")
    args = parser.parse_args()

    targets = set(args.targets)

    if args.fields:
        out_path = args.out or "creature_refs_search.txt"
        run_targeted_search(args.root, targets, args.fields, out_path)
    elif args.all:
        out_path = args.out or "creature_refs_full.txt"
        run_full_inventory(args.root, targets, out_path)
    else:
        out_path = args.out or "creature_refs_stages.txt"
        run_staged_inventory(args.root, targets, sorted(set(args.stages)), out_path)

if __name__ == "__main__":
    main()