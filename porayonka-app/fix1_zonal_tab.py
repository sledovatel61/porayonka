import re

filepath = r"ui\zonal\zonal_tab.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Исправление: убираем аннотацию типа ReportTemplate из вложенной функции
old = "        def _select_template(t: ReportTemplate):"
new = "        def _select_template(t):"
content = content.replace(old, new)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("OK: fix1 applied")