# fix_flet.py
import re
import os

# Файлы, где могли остаться несовместимые параметры
TARGET_FILES = [
    "ui/zonal/template_builder.py",
    "ui/zonal/criminalist_card.py",
    "ui/zonal/add_criminalist_modal.py",
    "ui/zonal/zone_manager.py",
    "ui/toolbar.py"
]

def fix_file(filepath):
    if not os.path.exists(filepath):
        print(f"[WARN] {filepath} не найден, пропускаем.")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Заменяем hint_text_color="..." на hint_style=ft.TextStyle(color="...")
    pattern_hint = r'hint_text_color\s*=\s*["\']([^"\']+)["\']'
    replacement_hint = r'hint_style=ft.TextStyle(color="\1")'
    new_content = re.sub(pattern_hint, replacement_hint, content)

    # 2. На всякий случай исправляем cursor_color, если тоже вызовет ошибку в старых версиях
    # (обычно работает, но на всякий случай оставим как есть)

    if new_content != content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"[OK] Исправлено: {filepath}")
    else:
        print(f"[SKIP] {filepath} уже в порядке")

if __name__ == "__main__":
    print("[SCAN] Поиск и исправление несовместимых параметров Flet...")
    for f in TARGET_FILES:
        fix_file(f)
    print("[DONE] Готово! Запусти main.py снова.")