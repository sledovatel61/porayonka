# [DARK THEME] Обновлено только визуально, логика сохранена.
# ui/zonal/zonal_tab.py
import flet as ft
from typing import List, Optional, Callable
from core.zonal_models import (
    ZonalCollection, ReportTemplate, Criminalist,
    ReportTemplateItem, ReportItemType, ReportData,
)
from core.zonal_data import (
    load_zonal_collection, save_zonal_collection,
    get_initial_criminalists, get_report_data,
    load_zonal_templates, save_zonal_template,
    save_criminalists,
)
from core.zonal_constants import get_initial_criminalists
from core.constants import COLORS, INITIAL_DEPARTMENTS
from .template_builder import create_template_builder
from .criminalist_card import create_criminalist_card
from .summary_panel import create_summary_panel


def create_zonal_tab(page: ft.Page) -> ft.Column:
    """
    Создать вкладку 'Зональные'.
    Возвращает ft.Column с полным содержимым вкладки.
    """
    print("[ZONAL_TAB] Инициализация вкладки Зональные")

    collection = load_zonal_collection()
    if collection is None:
        collection = ZonalCollection(
            template=ReportTemplate(name="Новая форма"),
            criminalists=get_initial_criminalists(),
        )
        print("[ZONAL_TAB] Создана новая коллекция")
    else:
        if not collection.criminalists:
            collection.criminalists = get_initial_criminalists()
    print(f"[ZONAL_TAB] Криминалистов: {len(collection.criminalists)}")
    print(f"[ZONAL_TAB] Пунктов шаблона: {len(collection.template.items)}")

    criminalist_cards: dict  = {}
    summary_ref: dict        = {"panel": None}
    template_builder_ref: dict = {"control": None}
    cards_column_ref: dict   = {"control": None}

    dept_map = {d["id"]: d["name"] for d in INITIAL_DEPARTMENTS}

    def autosave():
        try:
            save_zonal_collection(collection)
        except Exception as e:
            print(f"[ZONAL_TAB] Ошибка автосохранения: {e}")

    def refresh_all_cards():
        print("[ZONAL_TAB] Обновляю все карточки...")
        for crim_id, card_col in criminalist_cards.items():
            crim = next((c for c in collection.criminalists if c.id == crim_id), None)
            if crim is None:
                continue
            new_card = create_criminalist_card(
                page=page,
                criminalist=crim,
                collection=collection,
                on_data_change=_on_data_change,
                on_zone_edit=_on_zone_edit,
                on_delete_criminalist=_on_delete_criminalist,
                dept_map=dept_map,
            )
            card_col.controls = new_card.controls
            card_col.update()
        _refresh_summary()

    def _on_data_change():
        autosave()
        _refresh_summary()

    def _on_zone_edit(criminalist: Criminalist):
        _open_zone_editor(criminalist)

    def _refresh_summary():
        if summary_ref["panel"] is not None:
            new_summary = create_summary_panel(collection)
            summary_ref["panel"].controls = new_summary.controls
            try:
                summary_ref["panel"].update()
            except Exception:
                pass

    def _rebuild_template_builder():
        if template_builder_ref["control"] is None:
            return
        new_builder = create_template_builder(
            page=page,
            collection=collection,
            on_template_changed=on_template_changed,
            on_save=on_template_save,
            on_load=on_template_load,
            on_clear=on_template_clear,
            on_departments_mode_changed=on_departments_mode_changed,
        )
        template_builder_ref["control"].controls = [new_builder]
        try:
            template_builder_ref["control"].update()
        except Exception:
            pass

    def _open_zone_editor(crim: Criminalist):
        from .zone_manager import create_zone_manager_dialog
        dialog = create_zone_manager_dialog(
            page=page,
            criminalist=crim,
            dept_map=dept_map,
            on_save=lambda: _on_zone_saved(crim),
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def _on_zone_saved(crim: Criminalist):
        save_criminalists(collection.criminalists)
        autosave()
        card_col = criminalist_cards.get(crim.id)
        if card_col:
            new_card = create_criminalist_card(
                page=page,
                criminalist=crim,
                collection=collection,
                on_data_change=_on_data_change,
                on_zone_edit=_on_zone_edit,
                on_delete_criminalist=_on_delete_criminalist,
                dept_map=dept_map,
            )
            card_col.controls = new_card.controls
            card_col.update()
        from ui.toast import show_save_toast
        show_save_toast(page)

    def _on_add_criminalist():
        """Открыть диалог добавления криминалиста"""
        from .add_criminalist_modal import create_add_criminalist_modal

        def handle_save(full_name: str, note: str, department_ids: list):
            max_id = max((c.id for c in collection.criminalists), default=0)
            new_id = max_id + 1
            from core.zonal_models import Criminalist, CriminalistZone
            new_criminalist = Criminalist(
                id=new_id,
                full_name=full_name,
                note=note,
                zone=CriminalistZone(
                    criminalist_id=new_id,
                    department_ids=department_ids,
                ),
            )
            collection.criminalists.append(new_criminalist)
            save_criminalists(collection.criminalists)
            autosave()
            _refresh_cards_list()
            from ui.toast import show_toast
            show_toast(page, f"Добавлен: {full_name}", icon="➕")

        dialog = create_add_criminalist_modal(
            page=page,
            criminalist=None,
            on_save=handle_save,
            existing_ids=None,
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def _on_delete_criminalist(criminalist: Criminalist):
        """Удалить криминалиста"""
        def confirm_delete(e=None):
            collection.criminalists = [c for c in collection.criminalists if c.id != criminalist.id]
            save_criminalists(collection.criminalists)
            autosave()
            _refresh_cards_list()
            dialog.open = False
            page.update()
            from ui.toast import show_toast
            show_toast(page, f"Удалён: {criminalist.full_name}", icon="🗑️")

        def cancel_delete(e=None):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("⚠️ Удаление криминалиста", size=16,
                          weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            content=ft.Text(
                f"Вы уверены, что хотите удалить {criminalist.full_name}?\n\n"
                f"Все данные по этому криминалисту будут потеряны.",
                size=13,
                color=COLORS["text"],
            ),
            actions=[
                ft.TextButton("Отмена", on_click=cancel_delete),
                ft.ElevatedButton(
                    "Удалить",
                    bgcolor="#dc2626",
                    color=COLORS["text_light"],
                    on_click=confirm_delete,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def _refresh_cards_list():
        """Полностью пересобрать список карточек"""
        print("[ZONAL_TAB] Пересобираю список карточек...")
        criminalist_cards.clear()
        new_cards = []
        for crim in collection.criminalists:
            card_col = create_criminalist_card(
                page=page,
                criminalist=crim,
                collection=collection,
                on_data_change=_on_data_change,
                on_zone_edit=_on_zone_edit,
                on_delete_criminalist=_on_delete_criminalist,
                dept_map=dept_map,
            )
            criminalist_cards[crim.id] = card_col
            new_cards.append(card_col)
        if cards_column_ref["control"]:
            cards_column_ref["control"].controls = new_cards
            cards_column_ref["control"].update()
        _refresh_summary()

    def on_template_changed():
        autosave()
        refresh_all_cards()

    def on_template_save(name: str):
        try:
            collection.template.name = name
            save_zonal_template(collection.template)
            autosave()
            from ui.toast import show_toast
            show_toast(page, f"Шаблон '{name}' сохранён", icon="💾")
        except Exception as e:
            print(f"[ZONAL_TAB] Ошибка сохранения шаблона: {e}")
            from ui.toast import show_error_toast
            show_error_toast(page, f"Ошибка: {e}")

    def on_template_load():
        _open_template_loader()

    def _open_template_loader():
        templates = load_zonal_templates()
        if not templates:
            from ui.toast import show_toast
            show_toast(page, "Нет сохранённых шаблонов", icon="📂")
            return

        def _select_template(t):
            collection.template = t
            autosave()
            _rebuild_template_builder()
            refresh_all_cards()
            dialog.open = False
            page.update()
            from ui.toast import show_toast
            show_toast(page, f"Шаблон '{t.name}' загружен", icon="📂")

        def _delete_template(t):
            from core.zonal_data import delete_zonal_template
            try:
                delete_zonal_template(t.name)
                dialog.open = False
                page.update()
                from ui.toast import show_toast
                show_toast(page, f"Шаблон '{t.name}' удалён", icon="🗑️")
            except Exception as e:
                from ui.toast import show_error_toast
                show_error_toast(page, f"Ошибка удаления: {e}")

        items_list = ft.Column(spacing=8)
        for t in templates:
            # Контейнер для каждой кнопки с шаблоном
            template_row = ft.Row(
                controls=[
                    ft.ElevatedButton(
                        text=f"📋 {t.name} ({len(t.items)} пунктов)",
                        style=ft.ButtonStyle(
                            bgcolor=COLORS["card"],
                            color=COLORS["text"],
                            shape=ft.RoundedRectangleBorder(radius=8),
                        ),
                        expand=True,
                        on_click=lambda e, t=t: _select_template(t),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_color="#ef4444",
                        tooltip="Удалить шаблон",
                        on_click=lambda e, t=t: _delete_template(t),
                    ),
                ],
                spacing=4,
            )
            items_list.controls.append(template_row)

        def _close_dialog(e=None):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            modal=True,
            bgcolor=COLORS["primary_light"],  # ← Тёмный фон
            title=ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Text("📂 ", size=18),
                        ft.Text("Выбор шаблона", size=16, weight=ft.FontWeight.BOLD, color="white"),
                    ],
                    spacing=8,
                ),
                padding=ft.padding.symmetric(horizontal=16, vertical=12),
                gradient=ft.LinearGradient(
                    begin=ft.alignment.center_left,
                    end=ft.alignment.center_right,
                    colors=[COLORS["primary"], COLORS["primary_light"]],
                ),
                border_radius=ft.border_radius.only(top_left=12, top_right=12),
            ),
            content=ft.Container(
                content=items_list,
                width=450,
                height=min(len(templates) * 70, 400),
                bgcolor=COLORS["primary_light"],
                padding=ft.padding.all(12),
            ),
            actions=[
                ft.TextButton("Отмена", on_click=_close_dialog),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def on_template_clear():
        """Очистить все пункты шаблона, название и режим"""
        collection.template.items.clear()
        collection.template.name = "Новая форма"
        collection.template.use_departments_mode = False
        autosave()
        _rebuild_template_builder()
        refresh_all_cards()
        from ui.toast import show_toast
        show_toast(page, "Форма очищена", icon="🗑️")

    def on_departments_mode_changed(use_dept_mode: bool):
        collection.template.use_departments_mode = use_dept_mode
        autosave()
        refresh_all_cards()

    def on_export_excel():
        import os
        from pathlib import Path
        from datetime import datetime
        from core.zonal_exporter import ZonalExcelExporter
        try:
            home      = Path.home()
            downloads = home / "Downloads"
            if not downloads.exists():
                downloads = home
            filename = f"zonal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            filepath = str(downloads / filename)
            ZonalExcelExporter().export(collection, filepath)
            from ui.toast import show_export_toast
            show_export_toast(page, "Зональные Excel")
        except Exception as e:
            print(f"[ZONAL_TAB] Ошибка экспорта: {e}")
            from ui.toast import show_error_toast
            show_error_toast(page, f"Ошибка экспорта: {e}")

    # ── Построение UI ────────────────────────────────────────
    template_builder = create_template_builder(
        page=page,
        collection=collection,
        on_template_changed=on_template_changed,
        on_save=on_template_save,
        on_load=on_template_load,
        on_clear=on_template_clear,
        on_departments_mode_changed=on_departments_mode_changed,
    )

    template_builder_wrapper = ft.Column(
        controls=[template_builder],
        spacing=0,
    )
    template_builder_ref["control"] = template_builder_wrapper

    add_criminalist_btn = ft.ElevatedButton(
        text="➕ Добавить криминалиста",
        bgcolor=COLORS["btn_save"],
        color=COLORS["text_light"],
        height=40,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=16),
        ),
        on_click=lambda e: _on_add_criminalist(),
    )

    header_row = ft.Row(
        controls=[
            ft.Text(
                "👥 Зональные криминалисты",
                size=16,
                weight=ft.FontWeight.BOLD,
                color=COLORS["text"],
            ),
            ft.Container(expand=True),
            add_criminalist_btn,
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    cards_column = ft.Column(spacing=12)
    for crim in collection.criminalists:
        card_col = create_criminalist_card(
            page=page,
            criminalist=crim,
            collection=collection,
            on_data_change=_on_data_change,
            on_zone_edit=_on_zone_edit,
            on_delete_criminalist=_on_delete_criminalist,
            dept_map=dept_map,
        )
        criminalist_cards[crim.id] = card_col
        cards_column.controls.append(card_col)

    cards_column_ref["control"] = cards_column

    summary_col = create_summary_panel(collection)
    summary_ref["panel"] = summary_col

    export_btn = ft.ElevatedButton(
        text="📊 Экспорт в Excel",
        bgcolor=COLORS["btn_export"],
        color=COLORS["text_light"],
        height=44,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.padding.symmetric(horizontal=20),
        ),
        on_click=lambda e: on_export_excel(),
    )

    tab_content = ft.Column(
        controls=[
            template_builder_wrapper,
            ft.Container(height=16),
            header_row,
            ft.Container(height=8),
            cards_column,
            ft.Container(height=16),
            summary_col,
            ft.Container(height=8),
            ft.Row(controls=[export_btn], alignment=ft.MainAxisAlignment.END),
            ft.Container(height=20),
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    print("[ZONAL_TAB] Вкладка создана успешно")
    return tab_content