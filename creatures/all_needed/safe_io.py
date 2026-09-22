"""Безопасная запись файлов: сначала во временный файл, затем атомарная подмена."""

import json
import os

def write_json_atomic(path, data, indent=None, ensure_ascii=False):
    """Обрыв записи оставляет старый файл нетронутым, а не половину нового."""
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise