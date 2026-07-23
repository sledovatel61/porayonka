filepath = r"ui\zonal\zonal_tab.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

old = '''    def on_template_clear():
        """Очистить все пункты шаблона"""
        collection.template.items.clear()
        autosave()
        refresh_all_cards()
        from ui.toast import show_toast
        show_toast(page, "Форма очищена", icon=" ")'''

new = '''    def on_template_clear():
        """Очистить все пункты шаблона и сбросить название"""
        collection.template.items.clear()
        collection.template.name = "Новая форма"
        collection.template.use_departments_mode = False
        autosave()
        # Пересоздать template_builder с нуля
        _rebuild_template_builder()
        refresh_all_cards()
        from ui.toast import show_toast
        show_toast(page, "Форма очищена", icon="🗑")'''

content = content.replace(old, new)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("OK: fix2 applied")