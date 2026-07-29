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
from .criminalists_summary_panel import create_criminalists_summary_panel


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

    # ── Константы раскладки плашек ─────────────────────────────
    # _TILES_PER_ROW пересчитывается динамически из page.width в
    # _calc_tiles_per_row(). Значение по умолчанию 4 — «средний экран».
    _TILE_SPACING = 12
    _TILE_WIDTH = 280        # см. criminalist_tile._TILE_WIDTH
    _TAB_HORIZONTAL_PADDING = 40  # main.py: padding=20 слева и справа

    tiles_per_row_ref: Dict = {"value": 4}

    def _calc_tiles_per_row(width: Optional[float]) -> int:
        if width is None or width <= 0:
            return 4
        available = max(0.0, width - _TAB_HORIZONTAL_PADDING)
        # (n * TILE_WIDTH) + ((n - 1) * SPACING) <= available
        # n <= (available + SPACING) / (TILE_WIDTH + SPACING)
        n = int((available + _TILE_SPACING) // (_TILE_WIDTH + _TILE_SPACING))
        return max(2, min(5, n or 2))

    # ── Состояние UI ────────────────────────────────────────────
    tiles: Dict[int, ft.Container] = {}          # id -> плашка
    summary_ref: Dict = {"panel": None, "is_expanded": False}
    crim_summary_ref: Dict = {"panel": None, "is_expanded": False}
    template_builder_ref: Dict = {"control": None, "is_expanded": False}
    filter_ref: Dict = {"value": "all"}          # all | pending | inactive
    tiles_column_ref: Dict = {"control": None}
    counters_ref: Dict = {"control": None}

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

    def _refresh_general_summary():
        if summary_ref["panel"] is not None:
            new_summary = create_summary_panel(collection, summary_ref, _refresh_general_summary)
            summary_ref["panel"].controls = new_summary.controls
            try:
                summary_ref["panel"].update()
            except Exception:
                pass

    def _refresh_crim_summary():
        if crim_summary_ref["panel"] is not None:
            new_panel = create_criminalists_summary_panel(
                collection, crim_summary_ref, _refresh_crim_summary
            )
            crim_summary_ref["panel"].controls = new_panel.controls
            try:
                crim_summary_ref["panel"].update()
            except Exception:
                pass

    def _refresh_counters():
        """Обновить чипы-счётчики над сеткой плашек."""
        box = counters_ref["control"]
        if box is None:
            return
        try:
            box.content = _build_counters_row()
            box.update()
        except Exception:
            pass

    def _refresh_summary():
        """Обновить обе сводки и счётчики."""
        _refresh_general_summary()
        _refresh_crim_summary()
        _refresh_counters()

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

    # ── Раскладка плашек фиксированными рядами ─────────────────
    def _build_tile_rows(visible_criminalists: List[Criminalist]):
        """Разбить видимых криминалистов на ряды по tiles_per_row_ref."""
        n_per_row = max(1, tiles_per_row_ref["value"])
        rows = []
        if not visible_criminalists:
            rows.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.icons.INBOX, size=18,
                                    color=COLORS.get("text_muted", "#64748b")),
                            ft.Text(
                                "Нет криминалистов по выбранному фильтру",
                                size=12,
                                color=COLORS.get("text_secondary", "#94a3b8"),
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        tight=True,
                    ),
                    height=44,
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    bgcolor=COLORS.get("card", "#15202e"),
                    border=ft.border.all(1, COLORS.get("border", "#334155")),
                    border_radius=10,
                )
            )
            return rows
        for i in range(0, len(visible_criminalists), n_per_row):
            chunk = visible_criminalists[i:i + n_per_row]
            row_controls = []
            for c in chunk:
                tile = tiles.get(c.id)
                if tile is None:
                    tile = create_criminalist_tile(c, collection, dept_map, callbacks)
                    tiles[c.id] = tile
                row_controls.append(tile)
            rows.append(
                ft.Row(
                    controls=row_controls,
                    spacing=_TILE_SPACING,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    alignment=ft.MainAxisAlignment.START,
                    tight=True,
                )
            )
        return rows

    # ── Фильтрация ─────────────────────────────────────────────
    def _apply_filter():
        """Пересобрать ряды плашек по фильтру (без полной перерисовки таба)."""
        fmode = filter_ref["value"]
        visible = []
        for c in collection.criminalists:
            if fmode == "pending" and get_criminalist_fill(collection, c)["percent"] >= 100:
                continue
            if fmode == "inactive" and c.is_active:
                continue
            visible.append(c)

        tiles_column = tiles_column_ref["control"]
        if tiles_column is not None:
            tiles_column.controls = _build_tile_rows(visible)
            try:
                tiles_column.update()
            except Exception:
                pass
        # Обновим счётчики
        _refresh_counters()

    def _set_filter(value: str):
        filter_ref["value"] = value
        _restyle_filter_buttons()
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

    def _on_clear_all_data():
        """
        Кнопка тулбара «Очистить все данные».
        Сбрасывает ТОЛЬКО collection.submissions.
        Шаблон (template), список криминалистов и их is_active сохраняются.
        """
        filled = len(collection.submissions)
        if filled == 0:
            from ui.toast import show_toast
            show_toast(page, "Данные уже пусты", icon=ft.icons.INFO_OUTLINE)
            return

        def confirm(e=None):
            collection.submissions.clear()
            clear_zonal_submissions()
            autosave()
            refresh_all_tiles()
            dialog.open = False
            page.update()
            from ui.toast import show_toast
            show_toast(page, "Все введённые данные очищены",
                       icon=ft.icons.CLEANING_SERVICES)
            print(f"[ZONAL_TAB] Submissions cleared: {filled} records")

        def cancel(e=None):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Icon(ft.icons.WARNING_AMBER_ROUNDED, size=20, color="#f59e0b"),
                    ft.Text("Очистить все данные", size=16,
                            weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                ],
                spacing=8,
            ),
            content=ft.Container(
                width=420,
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "Очистить все введённые данные? "
                            "Структура формы и список криминалистов сохранятся.",
                            size=13,
                            color=COLORS["text"],
                        ),
                        ft.Container(height=8),
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Text(f"Будет удалено записей: {filled}",
                                            size=12, color=COLORS["in_progress_text"]),
                                    ft.Text(
                                        f"Сохранится: шаблон «{collection.template.name}» "
                                        f"({len(collection.template.items)} пунктов), "
                                        f"криминалистов: {len(collection.criminalists)}, "
                                        f"их активность.",
                                        size=12, color=COLORS["text_secondary"],
                                    ),
                                ],
                                spacing=4,
                                tight=True,
                            ),
                            bgcolor=COLORS["primary_light"],
                            border=ft.border.all(1, COLORS["border"]),
                            border_radius=8,
                            padding=ft.padding.all(10),
                        ),
                    ],
                    spacing=0,
                    tight=True,
                ),
            ),
            actions=[
                ft.TextButton("Отмена", on_click=cancel),
                ft.ElevatedButton(
                    "Очистить",
                    icon=ft.icons.CLEANING_SERVICES,
                    bgcolor="#f59e0b",
                    color=COLORS["text_light"],
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                    on_click=confirm,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=14),
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

    # ── Кнопки фильтра (сегментированный переключатель) ─────────
    filter_buttons: Dict[str, ft.Container] = {}

    def _filter_count(value: str) -> int:
        if value == "all":
            return len(collection.criminalists)
        if value == "pending":
            return sum(1 for c in collection.criminalists
                       if get_criminalist_fill(collection, c)["percent"] < 100)
        return sum(1 for c in collection.criminalists if not c.is_active)

    def _restyle_filter_buttons():
        """Перекрасить сегменты фильтра под текущее значение."""
        for v, btn in filter_buttons.items():
            selected = (v == filter_ref["value"])
            fg = COLORS["text_light"] if selected else COLORS["text_secondary"]
            btn.bgcolor = COLORS["btn_save"] if selected else "transparent"
            btn.border = ft.border.all(
                1, COLORS["btn_save_hover"] if selected else "transparent")
            row = btn.content
            try:
                row.controls[0].color = fg                      # иконка
                row.controls[1].color = fg                      # подпись
                badge = row.controls[2]                         # счётчик
                badge.bgcolor = ("#ffffff22" if selected else COLORS["card"])
                badge.content.color = fg
                badge.content.value = str(_filter_count(v))
            except Exception:
                pass
            try:
                btn.update()
            except Exception:
                pass

    def _mk_filter_btn(value: str, label: str, icon) -> ft.Container:
        # ВАЖНО (Flet 0.23.2): без `animate` — оно раздувает layout
        # у Container внутри Row (см. AGENTS.md 15.12 / 22).
        selected = (value == filter_ref["value"])
        fg = COLORS["text_light"] if selected else COLORS["text_secondary"]
        badge = ft.Container(
            content=ft.Text(str(_filter_count(value)), size=10,
                            color=fg, weight=ft.FontWeight.W_600, no_wrap=True),
            height=18,
            padding=ft.padding.symmetric(horizontal=6),
            border_radius=9,
            alignment=ft.alignment.center,
            bgcolor="#ffffff22" if selected else COLORS["card"],
        )
        btn = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(icon, size=14, color=fg),
                    ft.Text(label, size=12, weight=ft.FontWeight.W_600, color=fg, no_wrap=True),
                    badge,
                ],
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
            width=None,
            height=32,
            padding=ft.padding.symmetric(horizontal=12),
            border_radius=8,
            border=ft.border.all(1, COLORS["btn_save_hover"] if selected else "transparent"),
            alignment=ft.alignment.center,
            bgcolor=COLORS["btn_save"] if selected else "transparent",
            ink=True,
            on_click=lambda e, v=value: _set_filter(v),
            tooltip=f"Фильтр: {label}",
        )
        filter_buttons[value] = btn
        return btn

    filter_row = ft.Container(
        content=ft.Row(
            controls=[
                _mk_filter_btn("all", "Все", ft.icons.GRID_VIEW),
                _mk_filter_btn("pending", "Не заполнившие", ft.icons.PENDING_ACTIONS),
                _mk_filter_btn("inactive", "Неактивные", ft.icons.PAUSE_CIRCLE_OUTLINE),
            ],
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        ),
        height=40,
        bgcolor=COLORS["primary_light"],
        border=ft.border.all(1, COLORS["border"]),
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=3, vertical=3),
    )

    # ── Кнопки тулбара ──────────────────────────────────────────
    # ВАЖНО (Flet 0.23.2): elevation-словарь и overlay_color внутри
    # ButtonStyle иногда вызывают неопределённое поведение layout — оставляем
    # только простые стили с фиксированной высотой (см. AGENTS.md 22).
    add_btn = ft.ElevatedButton(
        text="Добавить",
        icon=ft.icons.PERSON_ADD_ALT_1,
        bgcolor=COLORS["btn_save"],
        color=COLORS["text_light"],
        height=38,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.padding.symmetric(horizontal=16),
        ),
        tooltip="Добавить нового криминалиста",
        on_click=lambda e: _on_add_criminalist(),
    )

    copy_btn = ft.OutlinedButton(
        text="Копировать не сдавших",
        icon=ft.icons.CONTENT_COPY,
        height=38,
        style=ft.ButtonStyle(
            color=COLORS["btn_save"],
            side=ft.BorderSide(1, COLORS["btn_save"]),
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.padding.symmetric(horizontal=14),
        ),
        on_click=_on_copy_non_submitters,
        tooltip="Скопировать в буфер список ФИО + отделы тех, кто не сдал форму",
    )

    clear_all_btn = ft.OutlinedButton(
        text="Очистить все данные",
        icon=ft.icons.CLEANING_SERVICES,
        height=38,
        style=ft.ButtonStyle(
            color="#f59e0b",
            side=ft.BorderSide(1, "#f59e0b"),
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.padding.symmetric(horizontal=14),
        ),
        on_click=lambda e: _on_clear_all_data(),
        tooltip="Сбросить все введённые значения. Шаблон, список криминалистов и их активность сохранятся",
    )

    export_btn = ft.ElevatedButton(
        text="Экспорт в Excel",
        icon=ft.icons.FILE_DOWNLOAD_OUTLINED,
        bgcolor=COLORS["btn_export"],
        color=COLORS["text_light"],
        height=38,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.padding.symmetric(horizontal=16),
        ),
        on_click=lambda e: on_export_excel(),
        tooltip="Выгрузить сводную таблицу в файл Excel",
    )

    # Тулбар: фиксированная высота, чтобы Container внутри Column(scroll=AUTO)
    # не пытался расти на всю доступную высоту. Внутренние Row —
    # с tight=True и alignment=START, чтобы не растягиваться по горизонтали.
    toolbar = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.icons.FILTER_ALT_OUTLINED, size=16,
                        color=COLORS["text_secondary"]),
                filter_row,
                ft.Container(
                    width=1,
                    height=26,
                    bgcolor=COLORS["border"],
                    margin=ft.margin.symmetric(horizontal=6),
                ),
                add_btn,
                copy_btn,
                clear_all_btn,
                export_btn,
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.START,
            tight=True,
            scroll=ft.ScrollMode.HIDDEN,
        ),
        height=60,
        bgcolor=COLORS["card"],
        border=ft.border.all(1, COLORS["border"]),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
    )

    # ── Строка счётчиков над сеткой плашек ──────────────────────
    def _counter_chip(icon, text: str, color: str) -> ft.Container:
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(icon, size=13, color=color),
                    ft.Text(text, size=11, color=COLORS["text_secondary"]),
                ],
                spacing=5,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=COLORS["primary_light"],
            border=ft.border.all(1, COLORS["border"]),
            border_radius=20,
            padding=ft.padding.symmetric(horizontal=10, vertical=4),
        )

    def _build_counters_row() -> ft.Row:
        total = len(collection.criminalists)
        active = sum(1 for c in collection.criminalists if c.is_active)
        done = sum(1 for c in collection.criminalists
                   if c.is_active and get_criminalist_fill(collection, c)["percent"] >= 100)
        pending = active - done
        return ft.Row(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.icons.BADGE_OUTLINED, size=16, color=COLORS["btn_save"]),
                        ft.Text("Криминалисты", size=13, weight=ft.FontWeight.BOLD,
                                color=COLORS["text"]),
                    ],
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    tight=True,
                ),
                _counter_chip(ft.icons.GROUPS, f"Всего: {total}", COLORS["text_secondary"]),
                _counter_chip(ft.icons.PERSON_OUTLINE, f"Активных: {active}",
                              COLORS["received_text"]),
                _counter_chip(ft.icons.TASK_ALT, f"Сдали: {done}", COLORS["stat_blue_text"]),
                _counter_chip(ft.icons.PENDING_ACTIONS, f"Осталось: {pending}",
                              COLORS["in_progress_text"]),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.START,
            tight=True,
        )

    # counters_box: фиксированная высота — иначе Container внутри
    # прокручиваемой Column в Flet 0.23.2 занимает всё оставшееся
    # пространство, отталкивая плашки за экран.
    counters_box = ft.Container(
        content=_build_counters_row(),
        height=40,
        padding=ft.padding.symmetric(horizontal=4, vertical=2),
        alignment=ft.alignment.center_left,
    )
    counters_ref["control"] = counters_box

    # Плашки через фиксированные ряды вместо GridView/Row(wrap=True).
    # В Flet 0.23.2 Wrap/GridView внутри прокручиваемой вкладки получают
    # неограниченную ширину и растягивают плашки. Фиксированные ряды по 4 плашки
    # дают конечные constraints и стабильный рендеринг.
    tiles_column = ft.Column(
        spacing=_TILE_SPACING,
        horizontal_alignment=ft.CrossAxisAlignment.START,
    )
    tiles_wrapper = ft.Container(
        content=tiles_column,
        alignment=ft.alignment.top_left,
    )
    tiles_column_ref["control"] = tiles_column

    # Первичный расчёт количества плашек в ряду и наполнение
    try:
        tiles_per_row_ref["value"] = _calc_tiles_per_row(page.width)
    except Exception:
        tiles_per_row_ref["value"] = 4
    print(f"[ZONAL_TAB] Initial tiles per row: {tiles_per_row_ref['value']} "
          f"(page width={getattr(page, 'width', None)})")
    tiles_column.controls = _build_tile_rows(collection.criminalists)

    def _on_page_resize(e=None):
        """Пересчитать сетку плашек при изменении ширины окна."""
        try:
            new_val = _calc_tiles_per_row(page.width)
        except Exception:
            return
        if new_val == tiles_per_row_ref["value"]:
            return
        tiles_per_row_ref["value"] = new_val
        print(f"[ZONAL_TAB] Resize: tiles_per_row -> {new_val} (w={page.width})")
        _apply_filter()

    # Не затираем чужие обработчики: сохраняем предыдущий и вызываем оба.
    _prev_resize = getattr(page, "on_resize", None)

    def _combined_resize(e=None):
        _on_page_resize(e)
        if _prev_resize is not None and _prev_resize is not _combined_resize:
            try:
                _prev_resize(e)
            except Exception:
                pass

    try:
        page.on_resize = _combined_resize
    except Exception:
        pass

    # ── Сводки ──────────────────────────────────────────────────
    summary_col = create_summary_panel(collection, summary_ref, _refresh_general_summary)
    summary_ref["panel"] = summary_col

    crim_summary_col = create_criminalists_summary_panel(
        collection, crim_summary_ref, _refresh_crim_summary
    )
    crim_summary_ref["panel"] = crim_summary_col

    tab_content = ft.Column(
        controls=[
            template_builder_wrapper,
            ft.Container(height=12),
            summary_col,
            ft.Container(height=10),
            crim_summary_col,
            ft.Container(height=14),
            toolbar,
            ft.Container(height=12),
            counters_box,
            ft.Container(height=10),
            tiles_wrapper,
            ft.Container(height=40),
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
    )

    print("[ZONAL_TAB] Zonal tab created successfully (phase 2)")
    return tab_content
