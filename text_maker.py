import ast
import os

def analyze_python_file(filepath: str) -> tuple[int, list[str]]:
    """Возвращает количество строк и список имён всех классов в Python-файле."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        loc = len(content.splitlines())

        tree = ast.parse(content, filename=filepath)
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

        return loc, classes
    except Exception:
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                return sum(1 for _ in f), []
        except Exception:
            return 0, []

def collect_statistics(main_dir: str, ignored_files: set, allowed_subdirs: set) -> tuple[int, int, int]:
    """
    Собирает суммарную статистику по проекту:
    - total_loc: суммарное количество строк во всех .py файлах
    - total_classes: суммарное количество классов
    - total_dirs: количество внутренних папок (всех, кроме корневой)
    """
    total_loc = 0
    total_classes = 0
    total_dirs = 0

    for root, dirs, files in os.walk(main_dir):
        # На верхнем уровне оставляем только разрешённые подпапки
        if root == main_dir:
            dirs[:] = [d for d in dirs if d in allowed_subdirs]

        # Каждая оставшаяся в dirs папка будет посещена и должна быть посчитана
        total_dirs += len(dirs)

        for file in files:
            if root == main_dir and file in ignored_files:
                continue
            if file.endswith(".py"):
                loc, classes = analyze_python_file(os.path.join(root, file))
                total_loc += loc
                total_classes += len(classes)

    return total_loc, total_classes, total_dirs

def main():
    main_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = os.path.basename(__file__)

    ignored_files = {script_name, "scan_creature_refs.py"}
    base_target_dir = r"d:\Akmal\Personal\AI developed Mini-games\Simple Lifes\temporary"
    os.makedirs(base_target_dir, exist_ok=True)

    allowed_subdirs = {"creatures", "game", "ui"}

    # --- 1. Копирование .py → .txt ---
    for root, dirs, files in os.walk(main_dir):
        if root == main_dir:
            dirs[:] = [d for d in dirs if d in allowed_subdirs]

        rel_path = os.path.relpath(root, main_dir)
        target_subdir = base_target_dir if rel_path == "." else os.path.join(base_target_dir, rel_path)

        for file in files:
            if root == main_dir and file in ignored_files:
                continue
            if file.endswith(".py"):
                source_path = os.path.join(root, file)
                target_filename = os.path.splitext(file)[0] + ".txt"
                target_path = os.path.join(target_subdir, target_filename)
                os.makedirs(target_subdir, exist_ok=True)

                with open(source_path, "r", encoding="utf-8") as f_in:
                    content = f_in.read()
                with open(target_path, "w", encoding="utf-8") as f_out:
                    f_out.write(content)

                print(f"Создан/перезаписан: {target_path}")

    # --- 2. Рекурсивное формирование файла-скелета ---
    def build_tree(
        dir_path: str,
        prefix: str = "",
        is_last: bool = True,
        is_root: bool = False,
        show_lines: bool = False,
    ) -> list[str]:
        """Рекурсивно строит псевдографическое дерево.
        При show_lines=True рядом с названиями файлов указывается количество строк и список классов.
        """
        lines = []
        name = os.path.basename(dir_path) or dir_path

        if is_root:
            lines.append(f"{name}/")
        else:
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{name}/")

        subdirs = []
        py_files = []
        try:
            for entry in os.listdir(dir_path):
                full = os.path.join(dir_path, entry)
                if os.path.isdir(full) and (dir_path != main_dir or entry in allowed_subdirs):
                    subdirs.append(entry)
                elif os.path.isfile(full) and entry.endswith(".py"):
                    if dir_path == main_dir and entry in ignored_files:
                        continue
                    py_files.append(entry)
        except PermissionError:
            pass

        subdirs.sort()
        py_files.sort()

        child_prefix = "" if is_root else prefix + ("    " if is_last else "│   ")

        items = subdirs + py_files
        for i, item in enumerate(items):
            is_item_last = i == len(items) - 1

            if item in subdirs:
                sub_path = os.path.join(dir_path, item)
                lines.extend(build_tree(sub_path, child_prefix, is_item_last, is_root=False, show_lines=show_lines))
            else:
                file_connector = "└── " if is_item_last else "├── "
                if show_lines:
                    file_path = os.path.join(dir_path, item)
                    loc, classes = analyze_python_file(file_path)
                    classes_str = f" | Классы: {', '.join(classes)}" if classes else ""
                    lines.append(f"{child_prefix}{file_connector}{item} [{loc} стр.{classes_str}]")
                else:
                    lines.append(f"{child_prefix}{file_connector}{item}")

        return lines

    # --- 3. Генерация и сохранение файлов-скелетов ---

    # Обычный СКЕЛЕТ (без изменений)
    skeleton_lines = build_tree(main_dir, is_root=True, show_lines=False)
    skeleton_path = os.path.join(base_target_dir, "СКЕЛЕТ.txt")
    with open(skeleton_path, "w", encoding="utf-8") as skel:
        skel.write("\n".join(skeleton_lines) + "\n")
    print(f"Файл-скелет создан: {skeleton_path}")

    # СКЕЛЕТ_ПРОДВИНУТЫЙ с суммарной статистикой в начале
    total_loc, total_classes, total_dirs = collect_statistics(main_dir, ignored_files, allowed_subdirs)

    stats_header = [
        "СУММАРНЫЕ ДАННЫЕ:",
        f"Всего строк: {total_loc}",
        f"Всего классов: {total_classes}",
        f"Внутренних папок: {total_dirs}",
        ""  # пустая строка-разделитель
    ]

    skeleton_lines_detailed = stats_header + build_tree(main_dir, is_root=True, show_lines=True)
    skeleton_detailed_path = os.path.join(base_target_dir, "СКЕЛЕТ_ПРОДВИНУТЫЙ.txt")
    with open(skeleton_detailed_path, "w", encoding="utf-8") as skel:
        skel.write("\n".join(skeleton_lines_detailed) + "\n")
    print(f"Подробный файл-скелет создан: {skeleton_detailed_path}")

if __name__ == "__main__":
    main()