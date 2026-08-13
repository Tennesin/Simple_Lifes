import os

def main():
    main_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = os.path.basename(__file__)

    # Целевая папка для копий
    base_target_dir = r"d:\Akmal\Personal\AI developed Mini-games\Simple Lifes\temporary"
    os.makedirs(base_target_dir, exist_ok=True)

    # Разрешённые подпапки в корне проекта
    allowed_subdirs = {"creatures", "game"}

    # --- Копирование .py → .txt ---
    for root, dirs, files in os.walk(main_dir):
        if root == main_dir:
            dirs[:] = [d for d in dirs if d in allowed_subdirs]

        rel_path = os.path.relpath(root, main_dir)
        target_subdir = base_target_dir if rel_path == "." else os.path.join(base_target_dir, rel_path)

        for file in files:
            if root == main_dir and file == script_name:
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

    # --- Формирование файла-скелета в виде дерева ---
    def build_tree(dir_path, prefix='', is_last=True, is_root=False):
        """Рекурсивно строит псевдографическое дерево папок и .py файлов."""
        lines = []
        name = os.path.basename(dir_path) or dir_path

        # Заголовок текущей папки
        if is_root:
            lines.append(f"{name}/")
        else:
            connector = '└── ' if is_last else '├── '
            lines.append(f"{prefix}{connector}{name}/")

        # Собираем содержимое: подпапки и .py файлы
        subdirs = []
        py_files = []
        try:
            for entry in os.listdir(dir_path):
                full = os.path.join(dir_path, entry)
                if os.path.isdir(full) and (dir_path != main_dir or entry in allowed_subdirs):
                    subdirs.append(entry)
                elif os.path.isfile(full) and entry.endswith('.py'):
                    if dir_path == main_dir and entry == script_name:
                        continue
                    py_files.append(entry)
        except PermissionError:
            pass

        subdirs.sort()
        py_files.sort()

        # Префикс для дочерних элементов
        if is_root:
            child_prefix = ''
        else:
            child_prefix = prefix + ('    ' if is_last else '│   ')

        # Выводим сначала папки, затем файлы
        items = subdirs + py_files
        for i, item in enumerate(items):
            is_item_last = (i == len(items) - 1)
            if item in subdirs:
                sub_path = os.path.join(dir_path, item)
                lines.extend(build_tree(sub_path, child_prefix, is_item_last, is_root=False))
            else:
                file_connector = '└── ' if is_item_last else '├── '
                lines.append(f"{child_prefix}{file_connector}{item}")

        return lines

    skeleton_lines = build_tree(main_dir, is_root=True)
    skeleton_path = os.path.join(base_target_dir, "СКЕЛЕТ.txt")
    with open(skeleton_path, 'w', encoding='utf-8') as skel:
        skel.write('\n'.join(skeleton_lines) + '\n')
    print(f"Файл-скелет создан: {skeleton_path}")

if __name__ == "__main__":
    main()