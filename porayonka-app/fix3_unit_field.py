filepath = r"ui\zonal\template_builder.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

old = '''    # Поле единицы измерения
        unit_field = ft.TextField(
            value=item.unit,
            hint_text="ед.",
            border_radius=6,
            border_color=COLORS["border"],
            focused_border_color=COLORS["btn_save"],
            bgcolor="white",
            height=38,
            text_size=13,
            width=60,
            visible=(item.item_type == ReportItemType.NUMERICAL),
            on_change=lambda e, i=item: _on_item_unit_change(e, i),
        )'''

new = '''    # Поле единицы измерения
        unit_field = ft.TextField(
            value=item.unit,
            hint_text="ед.",
            border_radius=6,
            border_color=COLORS["border"],
            focused_border_color=COLORS["btn_save"],
            bgcolor="white",
            height=38,
            text_size=13,
            width=70,
            content_padding=ft.padding.symmetric(horizontal=8, vertical=8),
            visible=(item.item_type == ReportItemType.NUMERICAL),
            on_change=lambda e, i=item: _on_item_unit_change(e, i),
        )'''

content = content.replace(old, new)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("OK: fix3 applied")