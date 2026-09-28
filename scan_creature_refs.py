"""
scan_creature_refs.py - статический сканер обращений к существу (Creature)
и проверка существования атрибутов. Кладётся в корень проекта.

РЕЖИМЫ:
  python scan_creature_refs.py                      # поля активного этапа из scan_plan.py
  python scan_creature_refs.py --stages 13 14       # поля указанных этапов
  python scan_creature_refs.py --fields is_sleeping home_id   # точечный поиск
  python scan_creature_refs.py --all                # инвентаризация всех полей
  python scan_creature_refs.py --check              # несуществующие атрибуты (getattr/hasattr тоже)
  python scan_creature_refs.py --state-audit        # оценка state-блоков, кандидаты на слияние

УРОВНИ УВЕРЕННОСТИ в отчётах:
  C - база точно существо (c / creature / self.c / self внутри Creature)
  A - база выведена как существо (цикл по other_creatures, lookup_creature(...) и т.п.)
  H - имя похоже на существо (other, partner, ward...), вывод не подтвердил
  U - неизвестно (только с --include-unknown)

Ограничение: это эвристика, а не type-checker. Алиасы через словари и
параметры без аннотаций ловятся только на уровне H. --check не заменяет
пробный запуск игры.
"""

import argparse
import ast
import os
import sys
from collections import defaultdict, namedtuple

try:
    from scan_plan import ACTIVE_STAGE, NEVER_MIGRATE, PLAN_STAGES
except ImportError:
    PLAN_STAGES, NEVER_MIGRATE, ACTIVE_STAGE = {}, set(), None

# =========================================================================
# Настройки
# =========================================================================

DEFAULT_OUT_DIR = r"d:\Akmal\Personal\AI developed Mini-games\Simple Lifes\temporary\1_scan_results"
IGNORED_DIR_NAMES = {"__pycache__", ".git", ".idea", "err", "temporary"}
IGNORED_FILES = {"text_maker.py", "scan_creature_refs.py", "scan_plan.py"}
ALLOWED_TOP_DIRS = {"creatures", "game", "ui"}        # при --roots . (корень проекта)
ANIMALS_PATH_PART = "creatures/animals"               # пропускается без --with-animals

CREATURE_CLASS_NAME = "Creature"
SCAN_SELF_CLASSES = {"Creature"}                      # self.xxx внутри них = поле существа
STATE_BASE_CLASS = "StateBlock"
STATE_BLOCKS_SOFT_LIMIT = 14                          # см. README, раздел про state
PLUMBING_FILES = ("creature.py", "creature_lifecycle.py")   # регистрация/персистентность - не считается использованием
MERGE_JACCARD = 0.6

SURE_NAMES = {"c", "creature"}
HINT_NAMES = {
    "other", "o", "partner", "mother", "father", "parent", "child", "ward", "guardian",
    "corpse", "carrier", "target_corpse", "mourner", "deceased", "intruder", "playmate",
    "thief", "needy", "recipient", "feeder", "heir", "male", "female", "candidate",
    "companion", "nearest_companion", "target_companion", "owner", "sibling", "son",
    "daughter", "target",
}
COLLECTION_NAMES = {
    "other_creatures", "visible_companions", "race_creatures", "creatures", "visible_corpses",
    "companions", "living_creatures", "nearby_creatures", "residents", "sons", "daughters",
    "corpses_to_remove", "ready_for_interact",
}
BY_ID_NAMES = {"creatures_by_id", "other_by_id"}
CREATURE_ATTRS = {"selected_creature", "grabbed_creature"}
CREATURE_RETURNING_FUNCS = {
    "lookup_creature", "best_companion", "find_needy_friend", "_find_visible_parent",
    "_find_elder_guardian", "_find_partner", "find_creature_at", "_living_creature_at",
    "_resolve_committed_target", "_pick_new_target",
}
PASSTHROUGH_FUNCS = {"list", "sorted", "tuple", "set", "reversed", "filter_same_race", "filter", "iter"}
DYNAMIC_ATTR_FUNCS = {"getattr", "hasattr", "setattr", "delattr"}

Record = namedtuple("Record", "tier field path kind rel lineno ctx text base")

# =========================================================================
# Загрузка и разбор файлов (каждый файл парсится один раз)
# =========================================================================

def rel(path):
    return os.path.relpath(path).replace(os.sep, "/")

def add_parents(tree):
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node

class SourceFile:
    def __init__(self, path):
        self.path = path
        self.rel = rel(path)
        self.lines = []
        self.tree = None
        self.error = None
        try:
            with open(path, "r", encoding="utf-8") as f:
                source = f.read()
            self.lines = source.splitlines()
            self.tree = ast.parse(source, filename=path)
            add_parents(self.tree)
        except (OSError, UnicodeDecodeError, SyntaxError) as error:
            self.error = str(error)

    def line(self, number):
        return self.lines[number - 1].strip() if 0 < number <= len(self.lines) else ""

def iter_python_files(roots, with_animals):
    seen = set()
    for root in roots:
        is_project_root = os.path.normpath(root) == "."
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in IGNORED_DIR_NAMES]
            if is_project_root and os.path.normpath(dirpath) == ".":
                dirnames[:] = [d for d in dirnames if d in ALLOWED_TOP_DIRS]
            if not with_animals and ANIMALS_PATH_PART in rel(dirpath):
                dirnames[:] = []
                continue
            for name in filenames:
                if not name.endswith(".py") or name in IGNORED_FILES:
                    continue
                path = os.path.join(dirpath, name)
                key = os.path.abspath(path)
                if key not in seen:
                    seen.add(key)
                    yield path

def load_sources(roots, with_animals):
    sources, broken = [], []
    for path in iter_python_files(roots, with_animals):
        src = SourceFile(path)
        (sources if src.tree is not None else broken).append(src)
    return sources, broken

# =========================================================================
# Модель классов проекта (для --check и --state-audit)
# =========================================================================

def base_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return "?"

def call_class_name(value):
    """ClassName(...) или ClassName.rolled(...) -> 'ClassName', иначе None."""
    if not isinstance(value, ast.Call):
        return None
    func = value.func
    if isinstance(func, ast.Name):
        name = func.id
    elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        name = func.value.id
    else:
        return None
    return name if name[:1].isupper() else None

class ClassInfo:
    def __init__(self, node, src):
        self.name = node.name
        self.rel = src.rel
        self.bases = [base_name(b) for b in node.bases]
        self.attrs = set()
        self.attr_types = {}
        self.fields = []            # поля dataclass по порядку
        self._collect(node)

    def _collect(self, node):
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                self.attrs.add(item.target.id)
                self.fields.append(item.target.id)
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        self.attrs.add(target.id)
            elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.attrs.add(item.name)
                for sub in ast.walk(item):
                    targets = []
                    if isinstance(sub, ast.Assign):
                        targets = sub.targets
                    elif isinstance(sub, (ast.AnnAssign, ast.AugAssign)):
                        targets = [sub.target]
                    for target in targets:
                        for t in (target.elts if isinstance(target, ast.Tuple) else [target]):
                            if (isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name)
                                    and t.value.id == "self"):
                                self.attrs.add(t.attr)
                                type_name = call_class_name(getattr(sub, "value", None))
                                if type_name and t.attr not in self.attr_types:
                                    self.attr_types[t.attr] = type_name

class ProjectIndex:
    def __init__(self, sources):
        self.by_name = defaultdict(list)
        self._cache = {}
        for src in sources:
            for node in ast.walk(src.tree):
                if isinstance(node, ast.ClassDef):
                    self.by_name[node.name].append(ClassInfo(node, src))

    def get(self, name):
        """Класс по имени; None, если неизвестен или имя неоднозначно."""
        infos = self.by_name.get(name)
        return infos[0] if infos and len(infos) == 1 else None

    def resolve(self, info):
        """(атрибуты, типы атрибутов, closed). closed=False - среди предков есть
        неизвестный класс, проверку по такому классу не делаем."""
        key = id(info)
        if key in self._cache:
            return self._cache[key]
        self._cache[key] = (set(info.attrs), dict(info.attr_types), False)   # защита от циклов
        attrs, types, closed = set(info.attrs), dict(info.attr_types), True
        for base in info.bases:
            if base == "object":
                continue
            parent = self.get(base)
            if parent is None:
                closed = False
                continue
            p_attrs, p_types, p_closed = self.resolve(parent)
            attrs |= p_attrs
            for k, v in p_types.items():
                types.setdefault(k, v)
            closed = closed and p_closed
        self._cache[key] = (attrs, types, closed)
        return self._cache[key]

    def inherits(self, info, target, _depth=0):
        if _depth > 20:
            return False
        for b in info.bases:
            if b == target:
                return True
            parent = self.get(b)
            if parent is not None and self.inherits(parent, target, _depth + 1):
                return True
        return False

    def class_of_attr(self, owner, attr):
        if owner is None:
            return None
        _attrs, types, _closed = self.resolve(owner)
        type_name = types.get(attr)
        return self.get(type_name) if type_name else None

# =========================================================================
# Вывод алиасов: какие локальные имена - существа ("C") или списки существ ("L")
# =========================================================================

def terminal_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None

def comp_kind(node, env, self_c):
    local = dict(env)
    for gen in node.generators:
        if isinstance(gen.target, ast.Name) and expr_kind(gen.iter, local, self_c) == "L":
            local[gen.target.id] = "C"
    return "L" if expr_kind(node.elt, local, self_c) == "C" else None

def expr_kind(node, env, self_c):
    """'C' - выражение это существо, 'L' - коллекция существ, None - неизвестно."""
    if isinstance(node, ast.Name):
        if node.id == "self":
            return "C" if self_c else None
        if node.id in env:
            return env[node.id]
        if node.id in SURE_NAMES:
            return "C"
        if node.id in COLLECTION_NAMES:
            return "L"
        return None
    if isinstance(node, ast.Attribute):
        if (isinstance(node.value, ast.Name) and node.value.id == "self"
                and node.attr in ("c", "creature")):
            return "C"
        if node.attr in COLLECTION_NAMES:
            return "L"
        if node.attr in CREATURE_ATTRS:
            return "C"
        return None
    if isinstance(node, ast.Call):
        name = terminal_name(node.func)
        if name in CREATURE_RETURNING_FUNCS:
            return "C"
        if (name == "get" and isinstance(node.func, ast.Attribute)
                and terminal_name(node.func.value) in BY_ID_NAMES):
            return "C"
        if name == "next" and node.args and isinstance(node.args[0], (ast.GeneratorExp, ast.ListComp)):
            return "C" if comp_kind(node.args[0], env, self_c) == "L" else None
        if name in ("min", "max") and node.args:
            return "C" if expr_kind(node.args[0], env, self_c) == "L" else None
        if name in PASSTHROUGH_FUNCS:
            return "L" if any(expr_kind(a, env, self_c) == "L" for a in node.args) else None
        return None
    if isinstance(node, (ast.ListComp, ast.GeneratorExp, ast.SetComp)):
        return comp_kind(node, env, self_c)
    if isinstance(node, ast.IfExp):
        return expr_kind(node.body, env, self_c) or expr_kind(node.orelse, env, self_c)
    if isinstance(node, ast.BoolOp):
        for value in node.values:
            kind = expr_kind(value, env, self_c)
            if kind:
                return kind
        return None
    if isinstance(node, ast.Subscript):
        if terminal_name(node.value) in BY_ID_NAMES:
            return "C"
        return "C" if expr_kind(node.value, env, self_c) == "L" else None
    return None

def annotated_as_creature(annotation):
    if isinstance(annotation, ast.Name):
        return annotation.id == CREATURE_CLASS_NAME
    if isinstance(annotation, ast.Attribute):
        return annotation.attr == CREATURE_CLASS_NAME
    if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
        return annotation.value.strip() == CREATURE_CLASS_NAME
    return False

def infer_env(fn, self_c):
    env = {}
    for node in ast.walk(fn):
        if isinstance(node, ast.arguments):
            for arg in node.posonlyargs + node.args + node.kwonlyargs:
                if arg.annotation is not None and annotated_as_creature(arg.annotation):
                    env[arg.arg] = "C"
    for _ in range(6):
        changed = False
        for node in ast.walk(fn):
            new = []
            if isinstance(node, ast.Assign):
                kind = expr_kind(node.value, env, self_c)
                if kind:
                    new = [(t.id, kind) for t in node.targets if isinstance(t, ast.Name)]
            elif isinstance(node, ast.AnnAssign) and node.value is not None and isinstance(node.target, ast.Name):
                kind = expr_kind(node.value, env, self_c)
                if kind:
                    new = [(node.target.id, kind)]
            elif isinstance(node, ast.NamedExpr) and isinstance(node.target, ast.Name):
                kind = expr_kind(node.value, env, self_c)
                if kind:
                    new = [(node.target.id, kind)]
            elif isinstance(node, (ast.For, ast.comprehension)):
                if isinstance(node.target, ast.Name) and expr_kind(node.iter, env, self_c) == "L":
                    new = [(node.target.id, "C")]
            for name, kind in new:
                if env.get(name) != kind:
                    env[name] = kind
                    changed = True
        if not changed:
            break
    return env

# =========================================================================
# Контекст, области видимости, разбор цепочек
# =========================================================================

def enclosing_class_name(node):
    cur = getattr(node, "parent", None)
    while cur is not None:
        if isinstance(cur, ast.ClassDef):
            return cur.name
        cur = getattr(cur, "parent", None)
    return None

def scope_of(node):
    """Внешняя функция/метод, в которой лежит узел (или None для модуля/тела класса)."""
    outer = None
    cur = getattr(node, "parent", None)
    while cur is not None:
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
            outer = cur
        cur = getattr(cur, "parent", None)
    return outer

def get_scope(fn, cache):
    key = id(fn) if fn is not None else 0
    if key not in cache:
        if fn is None:
            cache[key] = ({}, False)
        else:
            self_c = enclosing_class_name(fn) in SCAN_SELF_CLASSES
            cache[key] = (infer_env(fn, self_c), self_c)
    return cache[key]

def context_label(node):
    classes, funcs = [], []
    cur = getattr(node, "parent", None)
    while cur is not None:
        if isinstance(cur, ast.ClassDef):
            classes.append(cur.name)
        elif isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs.append(cur.name)
        cur = getattr(cur, "parent", None)
    func = funcs[-1] if funcs else None
    cls = classes[0] if classes else None
    if cls and func:
        return f"{cls} -> {func}"
    return func or cls or "(модуль)"

def split_chain(node):
    segs, cur = [], node
    while isinstance(cur, ast.Attribute):
        segs.append(cur.attr)
        cur = cur.value
    segs.reverse()
    return cur, segs

def safe_unparse(node):
    try:
        return ast.unparse(node)
    except Exception:
        return "?"

def base_tier(base, env, self_c):
    if isinstance(base, ast.Name):
        if base.id == "self":
            return "C" if self_c else "U"
        if base.id in SURE_NAMES:
            return "C"
    if expr_kind(base, env, self_c) == "C":
        return "A"
    if isinstance(base, ast.Name) and base.id in HINT_NAMES:
        return "H"
    return "U"

def resolve_base(node, env, self_c):
    """(уровень, сегменты цепочки, текст базы) для Name/Attribute-цепочки."""
    base, segs = split_chain(node)
    if isinstance(base, ast.Name) and base.id == "self" and segs and segs[0] in ("c", "creature"):
        return "C", segs[1:], "self." + segs[0]
    return base_tier(base, env, self_c), segs, safe_unparse(base)

def classify(node):
    parent = getattr(node, "parent", None)
    if isinstance(parent, ast.Call) and parent.func is node:
        return "CALL"
    if isinstance(parent, ast.AugAssign) and parent.target is node:
        return "RW"
    if isinstance(node.ctx, ast.Store):
        return "W"
    if isinstance(node.ctx, ast.Del):
        return "DEL"
    return "R"

# =========================================================================
# Сбор обращений (режимы поиска и state-audit)
# =========================================================================

def collect_records(src):
    records, scopes = [], {}
    for node in ast.walk(src.tree):
        if isinstance(node, ast.Attribute):
            parent = getattr(node, "parent", None)
            if isinstance(parent, ast.Attribute) and parent.value is node:
                continue                                    # берём только внешнюю часть цепочки
            env, self_c = get_scope(scope_of(node), scopes)
            tier, segs, base_text = resolve_base(node, env, self_c)
            if not segs:
                continue
            records.append(Record(tier, segs[0], ".".join(segs), classify(node), src.rel,
                                  node.lineno, context_label(node), src.line(node.lineno), base_text))
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
              and node.func.id in DYNAMIC_ATTR_FUNCS and len(node.args) >= 2
              and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str)):
            env, self_c = get_scope(scope_of(node), scopes)
            tier, segs, base_text = resolve_base(node.args[0], env, self_c) \
                if isinstance(node.args[0], (ast.Name, ast.Attribute)) \
                else (base_tier(node.args[0], env, self_c), [], safe_unparse(node.args[0]))
            segs = segs + [node.args[1].value]
            records.append(Record(tier, segs[0], ".".join(segs), f"DYN:{node.func.id}", src.rel,
                                  node.lineno, context_label(node), src.line(node.lineno), base_text))
    return records

def fmt(r):
    return f"[{r.rel}] {r.lineno} [{r.kind}/{r.tier}] {r.ctx} | {r.base}.{r.path}: {r.text}"

# =========================================================================
# Режим поиска (--fields / --stages / --all)
# =========================================================================

def write_field_report(out, records, groups, tiers):
    by_field = defaultdict(list)
    for r in records:
        if r.tier in tiers:
            by_field[r.field].append(r)
    for title, fields in groups:
        out.write(f"########## {title} ##########\n\n")
        names = fields if fields is not None else sorted(by_field, key=lambda f: (-len(by_field[f]), f))
        for field in names:
            entries = sorted(by_field.get(field, []), key=lambda r: (r.rel, r.lineno))
            mark = "  [NEVER_MIGRATE]" if field in NEVER_MIGRATE else ""
            out.write(f"=== {field}  ({len(entries)} обращений){mark} ===\n")
            if not entries:
                out.write("  (обращений не найдено - уже мигрировано или опечатка в плане)\n")
                if fields is not None:
                    print(f"[внимание] '{field}': обращений не найдено", file=sys.stderr)
            for r in entries:
                out.write(fmt(r) + "\n")
            out.write("\n")

# =========================================================================
# Режим --check: обращения к несуществующим атрибутам
# =========================================================================

def static_class(node, env, self_c, index, creature_info):
    if expr_kind(node, env, self_c) == "C":
        return creature_info
    if isinstance(node, ast.Attribute):
        return index.class_of_attr(static_class(node.value, env, self_c, index, creature_info), node.attr)
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "getattr"
            and len(node.args) >= 2 and isinstance(node.args[1], ast.Constant)
            and isinstance(node.args[1].value, str)):
        return index.class_of_attr(static_class(node.args[0], env, self_c, index, creature_info),
                                   node.args[1].value)
    return None

def build_moved_hints(index, creature_info):
    """поле -> ['housing.at_home', ...]: подсказка "возможно, поле переехало"."""
    hints = defaultdict(list)
    _attrs, types, _closed = index.resolve(creature_info)
    for attr, type_name in types.items():
        block = index.get(type_name)
        if block is not None:
            for field in block.fields:
                hints[field].append(f"{attr}.{field}")
    return hints

def run_check(sources, index, out):
    creature_info = index.get(CREATURE_CLASS_NAME)
    if creature_info is None:
        out.write(f"Класс {CREATURE_CLASS_NAME} не найден в просканированных файлах.\n")
        return 1
    hints = build_moved_hints(index, creature_info)
    problems = []

    def check_attr(src, node, owner, name, dynamic):
        attrs, _types, closed = index.resolve(owner)
        if not closed or name in attrs or name.startswith("__"):
            return
        hint = f"  (возможно: c.{', c.'.join(hints[name])})" if name in hints else ""
        how = ("getattr/hasattr вернёт default ТИХО, без ошибки" if dynamic
               else "AttributeError при выполнении этой ветки")
        problems.append((src.rel, node.lineno, context_label(node),
                         f"{owner.name} не имеет атрибута '{name}' - {how}{hint}", src.line(node.lineno)))

    for src in sources:
        scopes = {}
        for node in ast.walk(src.tree):
            if isinstance(node, ast.Attribute):
                env, self_c = get_scope(scope_of(node), scopes)
                owner = static_class(node.value, env, self_c, index, creature_info)
                if owner is not None:
                    check_attr(src, node, owner, node.attr, dynamic=False)
            elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                  and node.func.id in DYNAMIC_ATTR_FUNCS and len(node.args) >= 2
                  and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str)):
                env, self_c = get_scope(scope_of(node), scopes)
                owner = static_class(node.args[0], env, self_c, index, creature_info)
                if owner is not None:
                    check_attr(src, node, owner, node.args[1].value, dynamic=True)

    problems.sort()
    out.write(f"Найдено проблем: {len(problems)}\n\n")
    for rel_path, lineno, ctx, message, text in problems:
        out.write(f"[{rel_path}] {lineno} {ctx}\n    {message}\n    > {text}\n\n")
    return len(problems)

# =========================================================================
# Режим --state-audit
# =========================================================================

def run_state_audit(records, index, out):
    creature_info = index.get(CREATURE_CLASS_NAME)
    if creature_info is None:
        out.write(f"Класс {CREATURE_CLASS_NAME} не найден.\n")
        return
    _attrs, types, _closed = index.resolve(creature_info)
    blocks = {}
    for attr, type_name in types.items():
        info = index.get(type_name)
        if info is not None and index.inherits(info, STATE_BASE_CLASS):
            blocks[attr] = info

    users = {attr: {"files": set(), "classes": set()} for attr in blocks}
    for r in records:
        if r.tier in ("C", "A", "H") and r.field in blocks and not r.rel.endswith(PLUMBING_FILES):
            users[r.field]["files"].add(r.rel)
            users[r.field]["classes"].add(r.ctx.split(" -> ")[0])

    out.write(f"State-блоков: {len(blocks)} (мягкий лимит {STATE_BLOCKS_SOFT_LIMIT})\n")
    if len(blocks) > STATE_BLOCKS_SOFT_LIMIT:
        out.write("!!! ЛИМИТ ПРЕВЫШЕН - новые блоки только с явного разрешения автора проекта.\n")
    out.write("(файлы creature.py / creature_lifecycle.py не учитываются: это регистрация и сохранение)\n\n")

    out.write("--- Блоки ---\n")
    for attr, info in sorted(blocks.items()):
        persisted = "to_persisted_dict" in index.resolve(info)[0]
        small = "  <- МЕЛКИЙ (<=3 полей)" if len(info.fields) <= 3 else ""
        out.write(f"c.{attr:<16} {info.name:<22} полей: {len(info.fields):<3} "
                  f"персист: {'да' if persisted else 'нет':<4} "
                  f"файлов: {len(users[attr]['files']):<3} классов: {len(users[attr]['classes'])}{small}\n")

    out.write("\n--- Кандидаты на слияние (пересечение круга пользователей >= "
              f"{MERGE_JACCARD:.0%}) ---\n")
    names, found = sorted(blocks), False
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            fa, fb = users[a]["files"], users[b]["files"]
            if not fa or not fb:
                continue
            score = len(fa & fb) / len(fa | fb)
            if score >= MERGE_JACCARD:
                found = True
                out.write(f"c.{a} + c.{b}: {score:.0%} общих файлов "
                          f"({', '.join(sorted(fa & fb))})\n")
    if not found:
        out.write("(нет)\n")

# =========================================================================
# main
# =========================================================================

def resolve_out_path(out_arg, default_name):
    path = out_arg if out_arg and os.path.isabs(out_arg) else os.path.join(DEFAULT_OUT_DIR, out_arg or default_name)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    return path

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--roots", nargs="+", default=["."],
                        help="что сканировать (по умолчанию весь проект: creatures/game/ui + корневые файлы)")
    parser.add_argument("--with-animals", action="store_true", help="включить creatures/animals")
    parser.add_argument("--include-unknown", action="store_true", help="показать и уровень U (много шума)")
    parser.add_argument("--fields", nargs="+", help="точечный поиск указанных полей")
    parser.add_argument("--stages", nargs="+", type=int, help="этапы из scan_plan.py")
    parser.add_argument("--all", action="store_true", help="инвентаризация всех полей")
    parser.add_argument("--check", action="store_true", help="поиск обращений к несуществующим атрибутам")
    parser.add_argument("--state-audit", action="store_true", help="оценка state-блоков")
    parser.add_argument("--out", default=None, help="имя/путь файла отчёта")
    args = parser.parse_args()

    sources, broken = load_sources(args.roots, args.with_animals)
    for src in broken:
        print(f"[ПРОПУЩЕН] {src.rel}: {src.error}", file=sys.stderr)
    index = ProjectIndex(sources)
    tiers = {"C", "A", "H"} | ({"U"} if args.include_unknown else set())

    if args.check:
        mode, default_name = "check", "creature_refs_check.txt"
    elif args.state_audit:
        mode, default_name = "audit", "state_audit.txt"
    elif args.fields:
        mode, default_name = "fields", "creature_refs_search.txt"
    elif args.all:
        mode, default_name = "all", "creature_refs_full.txt"
    else:
        stages = args.stages or ([ACTIVE_STAGE] if ACTIVE_STAGE is not None else [])
        if not stages or not PLAN_STAGES:
            parser.error("нет этапов: заполни scan_plan.py или используй --fields/--check/--state-audit")
        mode = "stages"
        default_name = "creature_refs_stage" + "_".join(map(str, sorted(set(stages)))) + ".txt"

    out_path = resolve_out_path(args.out, default_name)
    exit_code = 0
    with open(out_path, "w", encoding="utf-8") as out:
        out.write(f"Файлов разобрано: {len(sources)}; пропущено из-за ошибок: {len(broken)}\n")
        for src in broken:
            out.write(f"  ПРОПУЩЕН {src.rel}: {src.error}\n")
        out.write("Уровни: C - точно существо, A - выведено, H - похоже по имени, U - неизвестно\n")
        out.write("=" * 78 + "\n\n")

        if mode == "check":
            exit_code = 1 if run_check(sources, index, out) else 0
        elif mode == "audit":
            records = [r for src in sources for r in collect_records(src)]
            run_state_audit(records, index, out)
        else:
            records = [r for src in sources for r in collect_records(src)]
            if mode == "fields":
                groups = [("Поля: " + ", ".join(args.fields), args.fields)]
            elif mode == "all":
                groups = [("Все поля", None)]
            else:
                groups = [(f"ЭТАП {s} ({len(PLAN_STAGES.get(s, ()))} полей)", list(PLAN_STAGES.get(s, ())))
                          for s in sorted(set(stages))]
            write_field_report(out, records, groups, tiers)

    print(f"Готово: {out_path}")
    sys.exit(exit_code)

if __name__ == "__main__":
    main()