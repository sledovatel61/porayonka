# ui/zonal/zonal_tab.py
# Вкладка "Зональные криминалисты" — ФАЗА 2.
# Сетка квадратных плашек вместо раскрывающихся карточек.
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
    print("[ZONAL_TAB] Inicializaciya vkladki Zonalnye (faza 2: setka plashek)")

    collection = load_zonal_collection()
    if collection is None:
        collection = ZonalCollection(
            template=ReportTemplate(name="Novaya forma"),
            criminalists=get_initial_criminalists(),
        )
        print("[ZONAL_TAB] Sozdana novaya kollekciya")
    else:
        if not collection.criminalists:
            collection.criminalists = get_initial_criminalists()
    print(f"[ZONAL_TAB] Kriminalistov: {len(collection.criminalists)}")
    print(f"[ZONAL_TAB] Aktivnyh: {sum(1 for c in collection.criminalists if c.is_active)}")
    print(f"[ZONAL_TAB] Punktov shablena: {len(collection.template.items)}")

    dept_map = {d["id"]: d["name"] for d in INITIAL_DEPARTMENTS}

    # ── Состояние UI ────────────────────────────────────────────
    tiles: Dict[int, ft.Container] = {}          # id -> плашка
    summary_ref: Dict = {"panel": None}
    template_builder_ref: Dict = {"control": None}
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
            print(f"[ZONAL_TAB] Oshibka avtosohraneniya: {e}")

    def _refresh_summary():
        if summary_ref["panel"] is not None:
            new_summary = create_summary_panel(collection)
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
        print("[ZONAL_TAB] Obnovlyayu vse plashki...")
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

        new_controls = []
        for c in visible:
            tile = tiles.get(c.id)
            if tile is None:
                tile = create_criminalist_tile(c, collection, dept_map, callbacks)
                tiles[c.id] = tile
            new_controls.append(tile)

        rr = responsive_row_ref["control"]
        if rr is not None:
            rr.controls = new_controls
            try:
                rr.update()
            except Exception:
                pass
        # Обновим счётчик видимых
        try:
            visible_count_text.value = f"Pokazano: {len(visible)} iz {len(collection.criminalists)}"
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
        status = "vklyuchen" if crim.is_active else "otklyuchen"
        show_toast(page, f"{crim.full_name} — {status}", icon="👁" if crim.is_active else "🚫")

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
            show_toast(page, f"Sohraneno: {full_name}", icon="✏️")

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
            show_toast(page, f"Udalen: {criminalist.full_name}", icon="🗑️")

        def cancel_delete(e=None):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Udalenie kriminalista", size=16,
                          weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            content=ft.Text(
                f"Vy uvereny, chto hotite udalit {criminalist.full_name}?\n\n"
                f"Vse dannye po etomu kriminalistu budut poteryany.",
                size=13,
                color=COLORS["text"],
            ),
            actions=[
                ft.TextButton("Otmena", on_click=cancel_delete),
                ft.ElevatedButton(
                    "Udalit",
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
            show_toast(page, f"Dobavlen: {full_name}", icon="➕")

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
            print(f"[ZONAL_TAB] Oshibka clipboard: {ex}")
        non = get_non_submitters(collection)
        from ui.toast import show_toast
        show_toast(page, f"Skopirovan spisok ne sdavshih: {len(non)}", icon="📋")

    # ── Шаблон / экспорт / сброс (как в фазе 1) ────────────────
    def on_template_changed():
        autosave()
        refresh_all_tiles()

    def on_template_save(name: str):
        try:
            collection.template.name = name
            save_zonal_template(collection.template)
            autosave()
            from ui.toast import show_toast
            show_toast(page, f"Shablon '{name}' sohranen", icon="💾")
        except Exception as e:
            print(f"[ZONAL_TAB] Oshibka sohraneniya shablena: {e}")
            from ui.toast import show_error_toast
            show_error_toast(page, f"Oshibka: {e}")

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
                show_toast(page, f"Shablon '{t.name}' zagruzhen (dannye sbroseny)", icon="📂")

            def cancel_load(e=None):
                dialog.open = False
                page.update()

            inactive_count = sum(1 for c in collection.criminalists if not c.is_active)
            inactive_note = f"\n\n({inactive_count} kriminalistov otklyucheno)" if inactive_count else ""
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Zagruzka shablena", size=16,
                              weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                content=ft.Text(
                    f"Shablon '{t.name}' zagruzit {len(t.items)} punktov.\n\n"
                    f"Tekuschie dannye budut udaleny!{inactive_note}",
                    size=13,
                    color=COLORS["text"],
                ),
                actions=[
                    ft.TextButton("Otmena", on_click=cancel_load),
                    ft.ElevatedButton("Zagruzit", bgcolor=COLORS["btn_save"],
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
            show_toast(page, f"Shablon '{t.name}' zagruzhen", icon="📂")

    def _open_template_loader():
        templates = load_zonal_templates()
        if not templates:
            from ui.toast import show_toast
            show_toast(page, "Net sohranennyh shablenov", icon="📂")
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
                show_toast(page, f"Shablon '{t.name}' udalen", icon="🗑️")
            except Exception as e:
                from ui.toast import show_error_toast
                show_error_toast(page, f"Oshibka udaleniya: {e}")

        items_list = ft.Column(spacing=8)
        for t in templates:
            template_row = ft.Row(
                controls=[
                    ft.ElevatedButton(
                        text=f"📋 {t.name} ({len(t.items)} punktov)",
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
                        tooltip="Udalit shablon",
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
                        ft.Text("📂 ", size=18),
                        ft.Text("Vybor shablena", size=16, weight=ft.FontWeight.BOLD, color="white"),
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
            actions=[ft.TextButton("Otmena", on_click=_close_dialog)],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def on_template_clear():
        collection.template.items.clear()
        collection.template.name = "Novaya forma"
        collection.template.use_departments_mode = False
        autosave()
        _rebuild_template_builder()
        refresh_all_tiles()
        from ui.toast import show_toast
        show_toast(page, "Forma ochischena", icon="🗑️")

    def on_reset_data():
        has_data = len(collection.submissions) > 0
        if not has_data:
            from ui.toast import show_toast
            show_toast(page, "Dannye uzhe pusty", icon="ℹ️")
            return

        def confirm_reset(e=None):
            collection.submissions.clear()
            clear_zonal_submissions()
            autosave()
            refresh_all_tiles()
            dialog.open = False
            page.update()
            from ui.toast import show_toast
            show_toast(page, "Dannye sbroseny, shablon sohranen", icon="🧹")

        def cancel_reset(e=None):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Sbros dannyh", size=16,
                          weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            content=ft.Text(
                f"Ochistit vse vvedennye dannye ({len(collection.submissions)} zapisey)?\n\n"
                f"Struktura shablena budet sohranena.",
                size=13,
                color=COLORS["text"],
            ),
            actions=[
                ft.TextButton("Otmena", on_click=cancel_reset),
                ft.ElevatedButton("Sbrosit", bgcolor="#f59e0b",
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
            show_export_toast(page, "Zonalnye Excel")
        except Exception as e:
            print(f"[ZONAL_TAB] Oshibka eksporta: {e}")
            from ui.toast import show_error_toast
            show_error_toast(page, f"Oshibka eksporta: {e}")

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
    )
    template_builder_wrapper = ft.Column(controls=[template_builder], spacing=0)
    template_builder_ref["control"] = template_builder_wrapper

    # Поиск
    search_field = ft.TextField(
        value="",
        hint_text="Poisk po FIO...",
        prefix_icon=ft.icons.SEARCH,
        border_radius=8,
        border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"],
        color=COLORS["text"],
        hint_style=ft.TextStyle(color=COLORS["text_muted"]),
        height=40,
        text_size=13,
        expand=True,
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
            _mk_filter_btn("all", "Vse"),
            _mk_filter_btn("pending", "Ne zapolnivshie"),
            _mk_filter_btn("inactive", "Neaktivnye"),
        ],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # Кнопка добавления
    add_btn = ft.ElevatedButton(
        text="Dobavit",
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

    # Кнопка копирования списка не сдавших (заглушка под Telegram/Messenger MAX)
    copy_btn = ft.OutlinedButton(
        text="Kopirovat ne sdavshih",
        icon=ft.icons.CONTENT_COPY,
        height=40,
        style=ft.ButtonStyle(
            color=COLORS["btn_save"],
            side=ft.BorderSide(1, COLORS["btn_save"]),
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=14),
        ),
        on_click=_on_copy_non_submitters,
        tooltip="Skopirovat v bufer spisok FIO + otdely teh, kto ne sdal formu",
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
        f"Pokazano: {len(collection.criminalists)} iz {len(collection.criminalists)}",
        size=12,
        color=COLORS["text_secondary"],
    )

    # Сетка плашек
    responsive_row = ft.ResponsiveRow(
        columns=12,
        spacing=12,
        run_spacing=12,
        controls=[],
    )
    responsive_row_ref["control"] = responsive_row

    # Первичное наполнение сетки
    for crim in collection.criminalists:
        tile = create_criminalist_tile(crim, collection, dept_map, callbacks)
        tiles[crim.id] = tile
        responsive_row.controls.append(tile)

    summary_col = create_summary_panel(collection)
    summary_ref["panel"] = summary_col

    export_btn = ft.ElevatedButton(
        text="Eksport v Excel",
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
            responsive_row,
            ft.Container(height=16),
            ft.Row(controls=[export_btn], alignment=ft.MainAxisAlignment.END),
            ft.Container(height=20),
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    print("[ZONAL_TAB] Vkladka sozdana uspeshno (faza 2)")
    return tab_content
