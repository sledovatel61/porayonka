# ui/zonal/zonal_tab.py
# Вкладка "Зональные криминалисты" — ФАЗА 2.
# Сетка компактных плашек вместо раскрывающихся карточек.
# [DARK THEME] + ft.icons.* + hint_style (Flet 0.23.2)
import flet as ft
from typing import List, Optional, Callable, Dict
from core.zonal_models import (
    ZonalCollection, ReportTemplate, Criminalist,
    ReportTemplateItem, ReportItemType, ReportData,
    CriminalistZone,
)
from core.zonal_data import (
    load_zonal_collection, save_zonal_collection,
    load_zonal_submissions, save_zonal_submissions,
    clear_zonal_submissions,
    get_initial_criminalists, get_report_data,
    load_zonal_templates, save_zonal_template,
    save_criminalists,
    get_criminalist_fill, get_non_submitters, build_non_submitters_text,
)
from core.constants import COLORS, INITIAL_DEPARTMENTS
from .template_builder import create_template_builder
from .criminalist_tile import create_criminalist_tile, rebuild_tile_content
from .form_input_modal import create_form_input_modal
from .add_criminalist_modal import create_add_criminalist_modal
from .summary_panel import create_summary_panel


def create_zonal_tab(page: ft.Page) -> ft.Column:
    """
    Создать вкладку 'Зональные'.
    Возвращает ft.Column с полным содержимым вкладки.
    """
    print("[ZONAL_TAB] Initializing zonal tab (phase 2: compact tiles)")

    collection = load_zonal_collection()
    if collection is None:
        collection = ZonalCollection(
            template=ReportTemplate(name="Новая форма"),
            criminalists=get_initial_criminalists(),
        )
        print("[ZONAL_TAB] Created new collection")
    else:
        if not collection.criminalists:
            collection.criminalists = get_initial_criminalists()
    print(f"[ZONAL_TAB] Criminalists: {len(collection.criminalists)}")
    print(f"[ZONAL_TAB] Active: {sum(1 for c in collection.criminalists if c.is_active)}")
    print(f"[ZONAL_TAB] Template items: {len(collection.template.items)}")

    dept_map = {d["id"]: d["name"] for d in INITIAL_DEPARTMENTS}

    # ── Состояние UI ────────────────────────────────────────────
    tiles: Dict[int, ft.Container] = {}          # id -> плашка
    summary_ref: Dict = {"panel": None, "is_expanded": False}
    template_builder_ref: Dict = {"control": None, "is_expanded": False}
    search_ref: Dict = {"value": ""}
    filter_ref: Dict = {"value": "all"}          # all | pending | inactive
    responsive_row_ref: Dict = {"control": None}

    # ── Колбэки для плашек ──────────────────────────────────────
    callbacks = {
        "on_open_form": lambda c: _on_open_form(c),
        "on_edit": lambda c: _on_edit_criminalist(c),
        "on_toggle_active": lambda c: _on_toggle_active(c),
        "on_delete": lambda c: _on_delete_criminalist(c),
    }

    def autosave():
        try:
            save_zonal_collection(collection)
        except Exception as e:
            print(f"[ZONAL_TAB] Autosave error: {e}")

    def _refresh_summary():
        if summary_ref["panel"] is not None:
            new_summary = create_summary_panel(collection, summary_ref, _refresh_summary)
            summary_ref["panel"].controls = new_summary.controls
            try:
                summary_ref["panel"].update()
            except Exception:
                pass

    def _refresh_tile(crim: Criminalist):
        tile = tiles.get(crim.id)
        if tile is None:
            return
        rebuild_tile_content(tile, crim, collection, dept_map, callbacks)

    def refresh_all_tiles():
        """Обновить все плашки (например, после изменения шаблона)."""
        print("[ZONAL_TAB] Refreshing all tiles...")
        for c in collection.criminalists:
            tile = tiles.get(c.id)
            if tile is None:
                continue
            rebuild_tile_content(tile, c, collection, dept_map, callbacks)
        _refresh_summary()
        _apply_filter()

    # ── Фильтрация / поиск ─────────────────────────────────────
    def _apply_filter():
        """Пересобрать сетку плашек по поиску и фильтру (без полной перерисовки таба)."""
        query = search_ref["value"].strip().lower()
        fmode = filter_ref["value"]
        visible = []
        for c in collection.criminalists:
            if query and query not in c.full_name.lower():
                continue
            if fmode == "pending" and get_criminalist_fill(collection, c)["percent"] >= 100:
                continue
            if fmode == "inactive" and c.is_active:
                continue
            visible.append(c)

        tiles_wrap = responsive_row_ref["control"]
        if tiles_wrap is not None:
            new_controls = []
            for c in visible:
                tile = tiles.get(c.id)
                if tile is None:
                    tile = create_criminalist_tile(c, collection, dept_map, callbacks)
                    tiles[c.id] = tile
                new_controls.append(tile)
            tiles_wrap.controls = new_controls
            try:
                tiles_wrap.update()
            except Exception:
                pass
        # Обновим счётчик видимых
        try:
            visible_count_text.value = f"Показано: {len(visible)} из {len(collection.criminalists)}"
            visible_count_text.update()
        except Exception:
            pass

    def _set_filter(value: str):
        filter_ref["value"] = value
        for v, btn in filter_buttons.items():
            selected = (v == value)
            btn.bgcolor = COLORS["btn_save"] if selected else COLORS["empty_bg"]
            btn.color = "white" if selected else COLORS["text_secondary"]
            try:
                btn.update()
            except Exception:
                pass
        _apply_filter()

    # ── Действия с плашками ─────────────────────────────────────
    def _on_toggle_active(crim: Criminalist):
        crim.is_active = not crim.is_active
        save_criminalists(collection.criminalists)
        autosave()
        _refresh_tile(crim)
        _refresh_summary()
        _apply_filter()
        from ui.toast import show_toast
        status = "включен" if crim.is_active else "отключен"
        show_toast(page, f"{crim.full_name} — {status}", icon=ft.icons.VISIBILITY if crim.is_active else ft.icons.CANCEL)

    def _on_open_form(crim: Criminalist):
        dialog = create_form_input_modal(
            page=page,
            criminalist=crim,
            collection=collection,
            dept_map=dept_map,
            on_saved=_on_form_saved,
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def _on_form_saved(crim: Criminalist):
        _refresh_tile(crim)
        _refresh_summary()

    def _on_edit_criminalist(crim: Criminalist):
        def handle_save(full_name: str, note: str, department_ids: list):
            crim.full_name = full_name
            crim.note = note
            crim.zone.department_ids = department_ids
            save_criminalists(collection.criminalists)
            autosave()
            _refresh_tile(crim)
            _refresh_summary()
            _apply_filter()
            from ui.toast import show_toast
            show_toast(page, f"Сохранено: {full_name}", icon=ft.icons.EDIT)

        dialog = create_add_criminalist_modal(
            page=page,
            criminalist=crim,
            on_save=handle_save,
            on_delete=lambda c: _on_delete_criminalist(c),
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def _on_delete_criminalist(criminalist: Criminalist):
        def confirm_delete(e=None):
            collection.criminalists = [c for c in collection.criminalists if c.id != criminalist.id]
            tiles.pop(criminalist.id, None)
            save_criminalists(collection.criminalists)
            autosave()
            _refresh_summary()
            _apply_filter()
            dialog.open = False
            page.update()
            from ui.toast import show_toast
            show_toast(page, f"Удален: {criminalist.full_name}", icon=ft.icons.DELETE)

        def cancel_delete(e=None):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Удаление криминалиста", size=16,
                          weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            content=ft.Text(
                f"Вы уверены, что хотите удалить {criminalist.full_name}?\n\n"
                f"Все данные по этому криминалисту будут утеряны.",
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

    def _on_add_criminalist():
        def handle_save(full_name: str, note: str, department_ids: list):
            max_id = max((c.id for c in collection.criminalists), default=0)
            new_id = max_id + 1
            new_criminalist = Criminalist(
                id=new_id,
                full_name=full_name,
                note=note,
                is_active=True,
                zone=CriminalistZone(criminalist_id=new_id, department_ids=department_ids),
            )
            collection.criminalists.append(new_criminalist)
            save_criminalists(collection.criminalists)
            autosave()
            _refresh_summary()
            _apply_filter()
            from ui.toast import show_toast
            show_toast(page, f"Добавлен: {full_name}", icon=ft.icons.ADD)

        dialog = create_add_criminalist_modal(
            page=page,
            criminalist=None,
            on_save=handle_save,
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def _on_copy_non_submitters(e=None):
        text = build_non_submitters_text(collection, dept_map)
        try:
            page.set_clipboard(text)
        except Exception as ex:
            print(f"[ZONAL_TAB] Clipboard error: {ex}")
        non = get_non_submitters(collection)
        from ui.toast import show_toast
        show_toast(page, f"Скопирован список не сдавших: {len(non)}", icon=ft.icons.CONTENT_COPY)

    # ── Шаблон / экспорт / сброс ───────────────────────────────
    def on_template_changed():
        autosave()
        refresh_all_tiles()

    def on_template_save(name: str):
        try:
            collection.template.name = name
            save_zonal_template(collection.template)
            autosave()
            from ui.toast import show_toast
            show_toast(page, f"Шаблон '{name}' сохранен", icon=ft.icons.SAVE)
        except Exception as e:
            print(f"[ZONAL_TAB] Template save error: {e}")
            from ui.toast import show_error_toast
            show_error_toast(page, f"Ошибка: {e}")

    def on_template_load():
        _open_template_loader()

    def _load_template_with_warning(t: ReportTemplate):
        has_data = len(collection.submissions) > 0
        if has_data:
            def confirm_load(e=None):
                collection.submissions.clear()
                clear_zonal_submissions()
                collection.template = t
                save_zonal_collection(collection)
                _rebuild_template_builder()
                refresh_all_tiles()
                dialog.open = False
                page.update()
                from ui.toast import show_toast
                show_toast(page, f"Шаблон '{t.name}' загружен (данные сброены)", icon=ft.icons.FOLDER)

            def cancel_load(e=None):
                dialog.open = False
                page.update()

            inactive_count = sum(1 for c in collection.criminalists if not c.is_active)
            inactive_note = f"\n\n({inactive_count} криминалистов отключено)" if inactive_count else ""
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Загрузка шаблона", size=16,
                              weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                content=ft.Text(
                    f"Шаблон '{t.name}' загрузит {len(t.items)} пунктов.\n\n"
                    f"Текущие данные будут удалены!{inactive_note}",
                    size=13,
                    color=COLORS["text"],
                ),
                actions=[
                    ft.TextButton("Отмена", on_click=cancel_load),
                    ft.ElevatedButton("Загрузить", bgcolor=COLORS["btn_save"],
                                      color=COLORS["text_light"], on_click=confirm_load),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.overlay.append(dialog)
            dialog.open = True
            page.update()
        else:
            collection.template = t
            autosave()
            _rebuild_template_builder()
            refresh_all_tiles()
            from ui.toast import show_toast
            show_toast(page, f"Шаблон '{t.name}' загружен", icon=ft.icons.FOLDER)

    def _open_template_loader():
        templates = load_zonal_templates()
        if not templates:
            from ui.toast import show_toast
            show_toast(page, "Нет сохраненных шаблонов", icon=ft.icons.FOLDER)
            return

        def _select_template(t):
            _load_template_with_warning(t)

        def _delete_template(t):
            from core.zonal_data import delete_zonal_template
            try:
                delete_zonal_template(t.name)
                dialog.open = False
                page.update()
                from ui.toast import show_toast
                show_toast(page, f"Шаблон '{t.name}' удален", icon=ft.icons.DELETE)
            except Exception as e:
                from ui.toast import show_error_toast
                show_error_toast(page, f"Ошибка удаления: {e}")

        items_list = ft.Column(spacing=8)
        for t in templates:
            template_row = ft.Row(
                controls=[
                    ft.ElevatedButton(
                        text=f"{t.name} ({len(t.items)} пунктов)",
                        icon=ft.icons.FOLDER_OPEN,
                        style=ft.ButtonStyle(
                            bgcolor=COLORS["card"],
                            color=COLORS["text"],
                            shape=ft.RoundedRectangleBorder(radius=8),
                        ),
                        expand=True,
                        on_click=lambda e, t=t: _select_template(t),
                    ),
                    ft.IconButton(
                        icon=ft.icons.DELETE_OUTLINE,
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
            bgcolor=COLORS["primary_light"],
            title=ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.icons.FOLDER, size=18, color="white"),
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
            actions=[ft.TextButton("Отмена", on_click=_close_dialog)],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def on_template_clear():
        collection.template.items.clear()
        collection.template.name = "Новая форма"
        collection.template.use_departments_mode = False
        autosave()
        _rebuild_template_builder()
        refresh_all_tiles()
        from ui.toast import show_toast
        show_toast(page, "Форма очищена", icon=ft.icons.DELETE)

    def on_reset_data():
        has_data = len(collection.submissions) > 0
        if not has_data:
            from ui.toast import show_toast
            show_toast(page, "Данные уже пусты", icon=ft.icons.INFO)
            return

        def confirm_reset(e=None):
            collection.submissions.clear()
            clear_zonal_submissions()
            autosave()
            refresh_all_tiles()
            dialog.open = False
            page.update()
            from ui.toast import show_toast
            show_toast(page, "Данные сброшены, шаблон сохранен", icon=ft.icons.CLEANING_SERVICES)

        def cancel_reset(e=None):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Сброс данных", size=16,
                          weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            content=ft.Text(
                f"Очистить все введенные данные ({len(collection.submissions)} записей)?\n\n"
                f"Структура шаблона будет сохранена.",
                size=13,
                color=COLORS["text"],
            ),
            actions=[
                ft.TextButton("Отмена", on_click=cancel_reset),
                ft.ElevatedButton("Сбросить", bgcolor="#f59e0b",
                                  color=COLORS["text_light"], on_click=confirm_reset),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def on_departments_mode_changed(use_dept_mode: bool):
        collection.template.use_departments_mode = use_dept_mode
        autosave()
        refresh_all_tiles()

    def on_export_excel():
        import os
        from pathlib import Path
        from datetime import datetime
        from core.zonal_exporter import ZonalExcelExporter
        try:
            home = Path.home()
            downloads = home / "Downloads"
            if not downloads.exists():
                downloads = home
            filename = f"zonal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            filepath = str(downloads / filename)
            ZonalExcelExporter().export(collection, filepath)
            from ui.toast import show_export_toast
            show_export_toast(page, "Зональные Excel")
        except Exception as e:
            print(f"[ZONAL_TAB] Export error: {e}")
            from ui.toast import show_error_toast
            show_error_toast(page, f"Ошибка экспорта: {e}")

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
            on_reset_data=on_reset_data,
            on_departments_mode_changed=on_departments_mode_changed,
            template_builder_ref=template_builder_ref,
        )
        template_builder_ref["control"].controls = [new_builder]
        try:
            template_builder_ref["control"].update()
        except Exception:
            pass

    # ── Построение UI ───────────────────────────────────────────
    template_builder = create_template_builder(
        page=page,
        collection=collection,
        on_template_changed=on_template_changed,
        on_save=on_template_save,
        on_load=on_template_load,
        on_clear=on_template_clear,
        on_reset_data=on_reset_data,
        on_departments_mode_changed=on_departments_mode_changed,
        template_builder_ref=template_builder_ref,
    )
    template_builder_wrapper = ft.Column(controls=[template_builder], spacing=0)
    template_builder_ref["control"] = template_builder_wrapper

    # Поиск
    search_field = ft.TextField(
        value="",
        hint_text="Поиск по ФИО...",
        prefix_icon=ft.icons.SEARCH,
        border_radius=8,
        border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"],
        color=COLORS["text"],
        hint_style=ft.TextStyle(color=COLORS["text_muted"]),
        height=40,
        width=320,
        text_size=13,
        on_change=lambda e: (_set_search(e.control.value),),
    )

    def _set_search(value: str):
        search_ref["value"] = value
        _apply_filter()

    # Кнопки фильтра
    filter_buttons: Dict[str, ft.OutlinedButton] = {}

    def _mk_filter_btn(value: str, label: str) -> ft.OutlinedButton:
        selected = (value == filter_ref["value"])
        btn = ft.OutlinedButton(
            text=label,
            style=ft.ButtonStyle(
                color="white" if selected else COLORS["text_secondary"],
                bgcolor=COLORS["btn_save"] if selected else COLORS["empty_bg"],
                side=ft.BorderSide(1, COLORS["border"]),
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
            ),
            on_click=lambda e, v=value: _set_filter(v),
        )
        filter_buttons[value] = btn
        return btn

    filter_row = ft.Row(
        controls=[
            _mk_filter_btn("all", "Все"),
            _mk_filter_btn("pending", "Не заполнившие"),
            _mk_filter_btn("inactive", "Неактивные"),
        ],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # Кнопка добавления
    add_btn = ft.ElevatedButton(
        text="Добавить",
        icon=ft.icons.ADD,
        bgcolor=COLORS["btn_save"],
        color=COLORS["text_light"],
        height=40,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=14),
        ),
        on_click=lambda e: _on_add_criminalist(),
    )

    # Кнопка копирования списка не сдавших
    copy_btn = ft.OutlinedButton(
        text="Копировать не сдавших",
        icon=ft.icons.CONTENT_COPY,
        height=40,
        style=ft.ButtonStyle(
            color=COLORS["btn_save"],
            side=ft.BorderSide(1, COLORS["btn_save"]),
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=14),
        ),
        on_click=_on_copy_non_submitters,
        tooltip="Скопировать в буфер список ФИО + отделы тех, кто не сдал форму",
    )

    toolbar = ft.Row(
        controls=[
            search_field,
            filter_row,
            add_btn,
            copy_btn,
        ],
        spacing=10,
        wrap=True,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    visible_count_text = ft.Text(
        f"Показано: {len(collection.criminalists)} из {len(collection.criminalists)}",
        size=12,
        color=COLORS["text_secondary"],
    )

    # Плашки через обычный переносимый Row вместо GridView.
    # В Flet 0.23.2 GridView внутри прокручиваемой вкладки стабильно создавал ячейки,
    # но на Windows не отрисовывал вложенный content плашек. Row(wrap=True) не
    # виртуализирует элементы, зато даёт обычные конечные constraints и сохраняет
    # компактную раскладку с переносом строк.
    tiles_wrap = ft.Row(
        spacing=12,
        run_spacing=12,
        wrap=True,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )
    responsive_row_ref["control"] = tiles_wrap

    # Первичное наполнение плашек
    for crim in collection.criminalists:
        tile = create_criminalist_tile(crim, collection, dept_map, callbacks)
        tiles[crim.id] = tile
        tiles_wrap.controls.append(tile)

    summary_col = create_summary_panel(collection, summary_ref, _refresh_summary)
    summary_ref["panel"] = summary_col

    export_btn = ft.ElevatedButton(
        text="Экспорт в Excel",
        icon=ft.icons.DOWNLOAD,
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
            summary_col,
            ft.Container(height=12),
            toolbar,
            ft.Container(height=6),
            visible_count_text,
            ft.Container(height=10),
            tiles_wrap,
            ft.Container(height=16),
            ft.Row(controls=[export_btn], alignment=ft.MainAxisAlignment.END),
            ft.Container(height=20),
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
    )

    print("[ZONAL_TAB] Zonal tab created successfully (phase 2)")
    return tab_content
