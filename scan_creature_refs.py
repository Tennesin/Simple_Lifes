"""
scan_creature_refs.py - утилита для поиска всех обращений к атрибутам
существа (c.xxx, self.c.xxx, creature.xxx, а также self.xxx внутри самого
класса Creature) по проекту.

Кладётся в корень проекта. Не требует внешних зависимостей.

РЕЖИМ 1 - обращения по этапам плана рефакторинга (без аргументов или --stages):
    python scan_creature_refs.py
    python scan_creature_refs.py --stages 4
    -> creature_refs_stageN.txt: обращения только к полям, перечисленным
       в PLAN_STAGES ниже, сгруппированные по этапу и по имени поля, плюс
       отдельный блок строковых совпадений (setattr/getattr/реестры) и
       sanity-check по полям без единой записи (W).

РЕЖИМ 2 - точечный поиск произвольных полей (в обход PLAN_STAGES):
    python scan_creature_refs.py --fields puberty_active is_pregnant home_id
    -> creature_refs_search.txt: обращения к указанным полям в простом
       построчном формате "[файл] номер_строки [R/W/CALL] поле: строка_кода".

Настройки (--root, --targets, --self-classes, --out) см. в argparse ниже.

=========================================================================
Три доработки поверх исходной версии сканера
=========================================================================

1. self.xxx внутри самого Creature (и любых других классов из
   --self-classes) теперь тоже считается обращением к полю существа -
   раньше "self" не входил в --targets намеренно (self.xxx означает поле
   совсем другого объекта почти везде в проекте), но внутри самого класса
   Creature self.hp/self.die()/self.burial и т.п. - это и есть искомые
   обращения, и они молча пропускались.

2. STAGE_EXTRA_TARGETS - список алиасов переменных-существ ("corpse",
   "carrier", "mother", "father", ...), характерных для конкретных этапов.
   Пополняется вручную по ходу расследования: нашёл новый alias - впиши
   сюда, чтобы при повторном прогоне того же этапа он попал в отчёт
   автоматически, а не терялся до следующей ручной вычитки кода.

3. scan_string_literals - отдельный проход по строковым литералам,
   совпадающим с именем поля. Ловит setattr/getattr по имени и элементы
   реестровых кортежей вроде _CREATURE_SIMPLE_FIELDS/_CREATURE_TUPLE_FIELDS
   в mechanics/creature_lifecycle.py, которые обычный обход по
   ast.Attribute не видит в принципе, поскольку это просто строки.
"""

import argparse
import ast
import os
import sys

DEFAULT_ROOT = "creatures/races/circles"
DEFAULT_OUT_DIR = r"d:\Akmal\Personal\AI developed Mini-games\Simple Lifes\temporary\1_scan_results"
DEFAULT_TARGETS = ("c", "self.c", "creature", "self.creature")
IGNORED_DIR_NAMES = {"__pycache__", ".git", ".idea"}

# ---------- Доработка 1: self.xxx внутри этих классов тоже считается полем существа ----------
SELF_SCAN_CLASSES = {"Creature"}

# =========================================================================
# Реестр полей по этапам плана миграции Creature (см. пошаговый план).
# Обновлять здесь по мере перехода к следующим этапам - остальной код
# трогать не нужно. Этап без полей просто не даёт совпадений и не появляется в отчёте.
# =========================================================================

PLAN_STAGES = {
    0: (
        # Шаг 0 - подготовка state/, StateBlock. Полей нет. РЕАЛИЗОВАНО.
    ),
    1: (
        # Шаг 1 - домен "Пубертат" (PubertyState). РЕАЛИЗОВАНО.
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
        # Шаг 2 - домен "Труп/кладбище" (BurialState). РЕАЛИЗОВАНО.
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
    3: (
        # Шаг 3 - домен "Территория" (внутри уже существующего
        # CreatureTerritory в life_cycle.py). РЕАЛИЗОВАНО.
        "territory_pursuit_target_id",
        "territory_pursuit_obj",
        "territory_pursuit_last_pos",
        "territory_pursuit_commit_timer",
    ),
    4: (
        # Шаг 4 - домен "Детские дороги": следование (ChildRoadPlayState,
        # владелец - child_ai.py:_ChildRoadPlayMixin) + физическая проверка
        # взрослым (RoadVerifyState, владелец - patterns/roads.py:ChildRoadVerification).
        # Один общий скан, но на выходе - ДВА отдельных StateBlock.

        # --- следование (игра) ---
        "following_child_road",
        "child_road_progress",
        "child_road_direction",
        "child_road_entry_reached",
        "child_road_play_cooldown",
        "child_road_play_counts",
        "child_road_disinterest",

        # --- проверка безопасности взрослым ---
        "child_road_verify_target_id",
        "child_road_verify_progress",
        "child_road_verify_direction",
        "child_road_verify_entry_reached",
        "child_road_verify_found_danger",
        "child_road_verify_check_timer",
    ),
    5: (
        # Шаг 5 - Стройка/добыча ресурсов + Кормление (сознательно вместе -
        # делать после появления реестра типов зданий, см. план).
        "carry_capacity",
        "carried_resources",
        "gather_target_id",
        "gather_type",
        "gather_progress",
        "gather_needed_amount",
        "construction_target_id",
        "construction_phase",
        "pending_construction_cleanup",
        "pending_site_cleanup",
        "construction_check_timer",
        "build_help_check_timer",
        "carried_fruit",
        "carried_water",
        "feed_target_id",
        "parent_feed_check_timer",
        "urgent_child_id",
        "urgent_child_timer",
    ),
    6: (
        # Шаг 6 - Семейный склад запасов ("Склад/дом" - снабжение).
        "storage_supply_check_timer",
        "storage_supply_mode",
    ),
    7: (
        # Шаг 7 - Жильё.
        "home_id",
        "home_eviction_timer",
        "at_home",
    ),
    8: (
        # Шаг 8 - Семья/размножение.
        "partner_id",
        "is_pregnant",
        "pregnancy_timer",
        "parent_ids",
        "reuniting_with_partner",
        "reunite_commit_timer",
        "partner_reunite_cooldown",
    ),
    9: (
        # Шаг 9 - Опека стариков над чужими детьми.
        "elder_ward_id",
        "elder_ward_check_timer",
    ),
    10: (
        # Шаг 10 - Дороги игрока (не детские; следование по нарисованной дороге).
        "known_roads",
        "known_road_links",
        "following_road",
        "following_road_active",
        "road_progress",
        "road_direction",
        "road_entry_reached",
        "road_follow_check_timer",
    ),
    11: (
        # Шаг 11 - Ориентиры (костёр/сон/точка комфорта).
        "comfort_point",
        "known_campfire",
        "known_campfire_id",
        "sleep_spot",
        "sleep_spot_campfire",
        "landmark_register_timer",
    ),
    12: (
        # Шаг 12 - Навигация / ИИ-троттлинг.
        "target",
        "decision_timer",
        "ai_dt_debt",
        "ai_last_goal",
        "ai_plan_valid",
        "speed_factor",
        "stuck_check_timer",
        "position_at_last_check",
        "stuck_level",
        "stuck_last_nav_index",
        "nav_path",
        "nav_path_index",
        "nav_goal",
        "nav_recalc_timer",
        "nav_search_failed",
    ),
    13: (
        # Шаг 13 - Флаги поиска ресурсов + сон + неуязвимость/заморозка.
        "seeking_food",
        "seeking_water",
        "seeking_sanity",
        "seeking_sleep",
        "wake_threshold",
        "is_sleeping",
        "sleep_forced",
        "freeze_timer",
        "spike_invuln_timer",
    ),
    14: (
        # Шаг 14 - Память об игроке/объектах + точные цели поиска еды/воды.
        "player_memory",
        "knowledge",
        "food_memory_target",
        "water_memory_target",
    ),
    15: (
        # Шаг 15 - Реакции игрок<->существо.
        "player_relationship",
        "calm_timer",
        "fear_timer",
        "player_fear_timer",
        "fear_source",
        "favorite_bonus_applied",
        "is_grabbed",
        "grab_before_state",
    ),
    16: (
        # Шаг 16 - Возраст / стадия жизни (без puberty - тот уже отдельно).
        "age",
        "life_stage",
    ),
    17: (
        # Шаг 17 - Поведение ребёнка (испуг, догонялки).
        "child_distress_timer",
        "play_target_id",
        "play_role",
        "play_timer",
        "play_cooldown",
    ),
    18: (
        # Шаг 18 - Социальное (отношения, запросы компании, эмпатия).
        "relationships",
        "social_request_timer",
        "social_request_point",
        "share_info_timer",
        "_helping_target_id",
        "helping_commit_timer",
    ),
    19: (
        # Шаг 19 - Характер / скорость / любопытство.
        "temperament",
        "base_speed_multiplier",
        "curiosity",
        "curiosity_active",
        "curiosity_rolled",
        "curiosity_interested",
    ),
    20: (
        # Шаг 20 - Смерть.
        "is_dead",
        "death_timer",
        "death_cause",
        "_pending_grief",
    ),
    21: (
        # Шаг 21 - Текущее состояние / отображаемая цель.
        "state",
        "goal_text",
        "panic_active",
        "is_talking",
    ),
    22: (
        # Шаг 22 (ПОСЛЕДНИЙ, самый рискованный) - Витальность.
        "hp",
        "hunger",
        "thirst",
        "consciousness",
        "sanity_decay_timer",
        "energy",
    ),
    # Идентичность (id, gender, name, player_named, x, y, radius) сознательно
    # НЕ вынесена отдельным этапом: это не поведенческое состояние, а
    # перманентные идентификаторы/геометрия - план не предполагает её миграцию.
}
ACTIVE_STAGE = 10

# ---------- Доработка 2: алиасы переменных-существ, характерные для конкретных этапов ----------
# Пополняется по ходу расследования: нашёл новый alias руками - впиши сюда,
# чтобы при повторном прогоне того же этапа он попал в отчёт автоматически.
STAGE_EXTRA_TARGETS = {
    2: ("corpse", "carrier", "target_corpse"),
    4: ("road",),
    7: ("mother", "father", "child", "female", "male", "parent", "guardian"),
    8: ("mother", "father", "child", "partner", "other", "target", "o", "mourner", "deceased"),
    9: ("ward", "guardian"),
    17: ("playmate",),
}

NEVER_MIGRATE = {
    # Категория A — контракт creatures/all_needed/
    "nav_path", "nav_path_index", "nav_goal", "nav_recalc_timer", "nav_search_failed",
    "speed_factor", "spike_invuln_timer",
    # Категория B — контракт LivingEntity/CreatureBase
    "is_dead", "hp", "hunger", "thirst", "energy",
    # Категория C — общая шина ИИ, не домен
    "target", "decision_timer", "state", "goal_text", "panic_active",
    # Категория D — идентичность/диспетчерский ключ
    "age", "life_stage", "temperament",
    # Категория E — мягче, но рекомендую держать с витальностью
    "consciousness", "sanity_decay_timer",
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
    'c.hp' как чтение поля от 'c.distance_to(x)' как вызов метода, а также
    чтобы найти ближайший охватывающий класс для self.xxx (доработка 1)."""
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node
    return tree


def enclosing_class_name(node):
    """Имя ближайшего охватывающего класса (через .parent) или None.
    node - сам узел ast.Attribute (self.xxx), не node.value."""
    current = getattr(node, "parent", None)
    while current is not None:
        if isinstance(current, ast.ClassDef):
            return current.name
        current = getattr(current, "parent", None)
    return None


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


def scan_file(path, targets, self_classes=frozenset()):
    """Возвращает список кортежей (field, kind, lineno, line_text, tag).
    tag - "target" (обычное совпадение c/self.c/creature/...) или
    "self" (доработка 1: self.xxx внутри класса из self_classes)."""
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
        is_self_field = (
            isinstance(node.value, ast.Name) and node.value.id == "self"
            and enclosing_class_name(node) in self_classes
        )
        if base not in targets and not is_self_field:
            continue

        field = node.attr
        kind = classify(node)
        lineno = node.lineno
        line_text = lines[lineno - 1].strip() if 0 < lineno <= len(lines) else ""
        tag = "self" if (is_self_field and base not in targets) else "target"
        results.append((field, kind, lineno, line_text, tag))

    return results


def scan_string_literals(path, field_set):
    """Доработка 3: строковые литералы, совпадающие с именем поля - ловит
    setattr/getattr по имени, ключи словарей save()/to_dict(), элементы
    реестровых кортежей вроде _CREATURE_SIMPLE_FIELDS/_CREATURE_TUPLE_FIELDS,
    которые обычный AST-обход по ast.Attribute не видит в принципе."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=path)
    except (OSError, UnicodeDecodeError, SyntaxError):
        return []

    lines = source.splitlines()
    results = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in field_set:
            lineno = node.lineno
            text = lines[lineno - 1].strip() if 0 < lineno <= len(lines) else ""
            results.append((node.value, "STR", lineno, text))
    return results


def rel(path, root):
    return os.path.relpath(path, root).replace(os.sep, "/")


def run_full_inventory(root, targets, self_classes, out_path):
    """Полная инвентаризация: группировка по имени поля (все поля без
    фильтра по PLAN_STAGES - используется только при явном --all)."""
    by_field = {}  # field -> list[(file, kind, lineno, text, tag)]

    for path in sorted(iter_python_files(root)):
        for field, kind, lineno, text, tag in scan_file(path, targets, self_classes):
            by_field.setdefault(field, []).append((path, kind, lineno, text, tag))

    with open(out_path, "w", encoding="utf-8") as out:
        out.write(f"Инвентаризация обращений {sorted(targets)} (+ self.xxx в {sorted(self_classes)}) в '{root}'\n")
        out.write(f"Всего уникальных полей/методов: {len(by_field)}\n")
        out.write("=" * 78 + "\n\n")

        for field in sorted(by_field, key=lambda f: (-len(by_field[f]), f)):
            entries = by_field[field]
            out.write(f"=== {field}  ({len(entries)} обращений) ===\n")
            for path, kind, lineno, text, tag in sorted(entries, key=lambda e: (e[0], e[2])):
                short = rel(path, ".")
                tag_suffix = "/self" if tag == "self" else ""
                out.write(f"[{short}] {lineno} [{kind}{tag_suffix}]: {text}\n")
            out.write("\n")

    print(f"Готово: {out_path} ({sum(len(v) for v in by_field.values())} обращений, "
          f"{len(by_field)} уникальных полей)")


def run_targeted_search(root, targets, self_classes, fields, out_path):
    """Точечный поиск конкретных полей - формат построчного отчёта."""
    fields = set(fields)
    total = 0

    with open(out_path, "w", encoding="utf-8") as out:
        out.write(f"Поиск полей {sorted(fields)} среди {sorted(targets)} "
                  f"(+ self.xxx в {sorted(self_classes)}) в '{root}'\n")
        out.write("=" * 78 + "\n\n")

        for path in sorted(iter_python_files(root)):
            matches = [m for m in scan_file(path, targets, self_classes) if m[0] in fields]
            if not matches:
                continue
            short = rel(path, ".")
            for field, kind, lineno, text, tag in sorted(matches, key=lambda e: e[2]):
                tag_suffix = "/self" if tag == "self" else ""
                out.write(f"[{short}] {lineno} [{kind}{tag_suffix}] {field}: {text}\n")
                total += 1

    print(f"Готово: {out_path} ({total} совпадений)")

def resolve_out_path(out_arg, default_name):
    """Если --out не задан - кладём файл в DEFAULT_OUT_DIR с именем по умолчанию.
    Если --out задан и это абсолютный путь - используем как есть.
    Если --out задан относительным - тоже кладём в DEFAULT_OUT_DIR."""
    if out_arg:
        path = out_arg if os.path.isabs(out_arg) else os.path.join(DEFAULT_OUT_DIR, out_arg)
    else:
        path = os.path.join(DEFAULT_OUT_DIR, default_name)

    out_dir = os.path.dirname(path) or "."
    os.makedirs(out_dir, exist_ok=True)
    return path

def run_staged_inventory(root, targets, self_classes, stage_numbers, out_path):
    """Обращения только к полям из PLAN_STAGES, сгруппированные по этапу, а
    внутри этапа - по имени поля. Дополнительно, для каждого этапа:
    - применяются его STAGE_EXTRA_TARGETS (доработка 2);
    - отдельным блоком идут строковые совпадения (доработка 3);
    - выводится sanity-check по полям без единой записи (W)."""
    total_matches = 0

    with open(out_path, "w", encoding="utf-8") as out:
        out.write(f"Обращения к полям из PLAN_STAGES, этапы {stage_numbers}, в '{root}'\n")
        out.write(f"Базовые targets: {sorted(targets)}; self.xxx учитывается в классах: {sorted(self_classes)}\n")
        out.write("=" * 78 + "\n\n")

        for stage in stage_numbers:
            fields = PLAN_STAGES.get(stage)
            if fields is None:
                print(f"[предупреждение] этап {stage} не описан в PLAN_STAGES - пропущен", file=sys.stderr)
                continue
            if not fields:
                # Этап объявлен, но полей ещё нет (например, шаг 0 - инфраструктура)
                continue

            # ---------- Доработка 2: алиасы, специфичные именно для этого этапа ----------
            stage_targets = set(targets) | set(STAGE_EXTRA_TARGETS.get(stage, ()))
            field_set = set(fields)
            by_field = {}  # field -> list[(file, kind, lineno, text, tag)]

            for path in sorted(iter_python_files(root)):
                for field, kind, lineno, text, tag in scan_file(path, stage_targets, self_classes):
                    if field in field_set:
                        by_field.setdefault(field, []).append((path, kind, lineno, text, tag))

            stage_total = sum(len(v) for v in by_field.values())
            total_matches += stage_total

            extra_note = f", доп. алиасы: {sorted(STAGE_EXTRA_TARGETS[stage])}" if stage in STAGE_EXTRA_TARGETS else ""
            out.write(f"########## ЭТАП {stage} ({len(fields)} полей в плане, "
                      f"{stage_total} обращений{extra_note}) ##########\n\n")

            # Поля этапа перечисляем в порядке PLAN_STAGES, а не по алфавиту -
            # так проще сверяться со списком полей будущего StateBlock.
            for field in fields:
                entries = by_field.get(field, [])
                out.write(f"=== {field}  ({len(entries)} обращений) ===\n")
                if not entries:
                    out.write("  (обращений не найдено)\n")
                for path, kind, lineno, text, tag in sorted(entries, key=lambda e: (e[0], e[2])):
                    short = rel(path, ".")
                    tag_suffix = "/self" if tag == "self" else ""
                    out.write(f"[{short}] {lineno} [{kind}{tag_suffix}]: {text}\n")
                out.write("\n")

            # ---------- Доработка 3: строковые совпадения (setattr/getattr/реестры) ----------
            out.write("--- Строковые совпадения (setattr/getattr/реестры) ---\n")
            str_total = 0
            for path in sorted(iter_python_files(root)):
                for value, kind, lineno, text in scan_string_literals(path, field_set):
                    short = rel(path, ".")
                    out.write(f"[{short}] {lineno} [{kind}] {value}: {text}\n")
                    str_total += 1
            if str_total == 0:
                out.write("  (совпадений не найдено)\n")
            out.write("\n")

            # ---------- Sanity-check: поле встречается, но ни разу не как запись (W) ----------
            for field in fields:
                entries = by_field.get(field, [])
                kinds = {k for _p, k, _l, _t, _tag in entries}
                if kinds and "W" not in kinds:
                    print(f"[внимание] этап {stage}, '{field}': нет ни одной записи (W) в '{root}' - "
                          f"проверь вручную, не пишется ли поле динамически/вне root "
                          f"(см. также блок 'Строковые совпадения' в отчёте)", file=sys.stderr)

            out.write("\n")

    print(f"Готово: {out_path} ({total_matches} обращений по этапам {stage_numbers})")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=DEFAULT_ROOT,
                        help=f"Папка для сканирования (по умолчанию: {DEFAULT_ROOT})")
    parser.add_argument("--targets", nargs="+", default=list(DEFAULT_TARGETS),
                        help=f"Какие 'базовые' имена считать существом (по умолчанию: {DEFAULT_TARGETS})")
    parser.add_argument("--self-classes", nargs="+", default=sorted(SELF_SCAN_CLASSES),
                        help="Классы, внутри которых self.xxx тоже считается полем существа "
                             f"(по умолчанию: {sorted(SELF_SCAN_CLASSES)}). Пустой список ('--self-classes') "
                             "отключает эту проверку.")
    parser.add_argument("--fields", nargs="+", default=None,
                        help="Точечный поиск только этих полей (игнорирует PLAN_STAGES)")
    parser.add_argument("--stages", nargs="+", type=int, default=[ACTIVE_STAGE],
                        help=f"Какие этапы плана включить в отчёт "
                             f"(по умолчанию: [{ACTIVE_STAGE}] - см. ACTIVE_STAGE в начале файла)")
    parser.add_argument("--all", action="store_true",
                        help="Полная инвентаризация ВСЕХ полей без фильтра по PLAN_STAGES "
                             "(даёт большой файл - использовать только осознанно)")
    parser.add_argument("--out", default=None,
                        help=f"Имя/путь выходного файла. Относительный путь или имя без пути "
                             f"кладётся в {DEFAULT_OUT_DIR} (по умолчанию имя подбирается по режиму).")
    args = parser.parse_args()

    targets = set(args.targets)
    self_classes = set(args.self_classes)

    # ---------- Доработка 2: при точечном запросе одного этапа сразу подмешиваем его алиасы ----------
    if not args.fields and not args.all and len(set(args.stages)) == 1:
        targets |= set(STAGE_EXTRA_TARGETS.get(args.stages[0], ()))

    if args.fields:
        out_path = resolve_out_path(args.out, "creature_refs_search.txt")
        run_targeted_search(args.root, targets, self_classes, args.fields, out_path)
    elif args.all:
        out_path = resolve_out_path(args.out, "creature_refs_full.txt")
        run_full_inventory(args.root, targets, self_classes, out_path)
    else:
        default_name = f"creature_refs_stage{'_'.join(map(str, sorted(set(args.stages))))}.txt"
        out_path = resolve_out_path(args.out, default_name)
        run_staged_inventory(args.root, targets, self_classes, sorted(set(args.stages)), out_path)

if __name__ == "__main__":
    main()