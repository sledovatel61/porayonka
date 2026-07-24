# ui/zonal/zonal_tab.py
# Vkladka "Zonalnye kriminalisty" - novyy UI s setkoy ploshek
# [DARK THEME] Polnaya pererabotka UI
import flet as ft
from typing import List, Optional, Callable
from core.zonal_models import (
    ZonalCollection, ReportTemplate, Criminalist,
    ReportTemplateItem, ReportItemType, ReportData,
)
from core.zonal_data import (
    load_zonal_collection, save_zonal_collection,
    clear_zonal_submissions,
    get_initial_criminalists, get_report_data,
    load_zonal_templates, save_zonal_template,
    save_criminalists,
)
from core.constants import COLORS, INITIAL_DEPARTMENTS


def create_zonal_tab(page: ft.Page) -> ft.Column:
    """
    Sozdat vkladku 'Zonalnye' s novym UI.
    Setka ploshek vmesto dlinnyh raskryvayuschihsya kartochek.
    """
    print("[ZONAL_TAB] Inicializaciya vkladki Zonalnye")

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
    print(f"[ZONAL_TAB] Punktov shablona: {len(collection.template.items)}")

    # Resfy
    tiles_grid_ref: dict = {"control": None}
    tiles_container_ref: dict = {"control": None}
    summary_ref: dict = {"panel": None}
    search_field_ref: dict = {"field": None}
    
    # Sostoyanie filtrov
    show_inactive_ref: dict = {"value": False}
    search_query_ref: dict = {"value": ""}

    dept_map = {d["id"]: d["name"] for d in INITIAL_DEPARTMENTS}

    def autosave():
        try:
            save_zonal_collection(collection)
        except Exception as e:
            print(f"[ZONAL_TAB] Oshibka avtosohraneniya: {e}")

    def _refresh_tiles():
        """Obnovit setku ploshek"""
        print("[ZONAL_TAB] Obnovlyayu setku ploshek...")
        
        if tiles_container_ref["control"] is None:
            return
        
        # Filtraciya
        filtered = _get_filtered_criminalists()
        
        # Sozdayem novuyu setku
        from .criminalist_tile import create_tiles_grid
        
        new_grid = create_tiles_grid(
            page=page,
            collection=collection,
            on_click=_on_tile_click,
            on_toggle_active=_on_toggle_active,
            on_edit=_on_edit_criminalist,
            dept_map=dept_map,
            show_inactive=show_inactive_ref["value"],
        )
        
        tiles_container_ref["control"].content = new_grid
        tiles_grid_ref["control"] = new_grid
        try:
            tiles_container_ref["control"].update()
        except Exception:
            pass
        
        _refresh_summary()

    def _get_filtered_criminalists() -> List[Criminalist]:
        """Poluchit otfiltrovannyh kriminalistov"""
        query = search_query_ref["value"].lower().strip()
        
        result = []
        for c in collection.criminalists:
            # Filt po aktivnosti
            if not c.is_active and not show_inactive_ref["value"]:
                continue
            
            # Filt po poisky
            if query and query not in c.full_name.lower():
                continue
            
            result.append(c)
        
        return result

    def _refresh_summary():
        """Obnovit svodky"""
        if summary_ref["panel"] is not None:
            from .compact_summary import create_compact_summary
            new_summary = create_compact_summary(collection)
            summary_ref["panel"].content = new_summary.content
            try:
                summary_ref["panel"].update()
            except Exception:
                pass

    def _on_tile_click(criminalist: Criminalist):
        """Otkryt formu zapolneniya dlya kriminalista"""
        from .fill_form_modal import create_fill_form_modal
        
        def on_form_save():
            autosave()
            _refresh_tiles()
        
        dialog = create_fill_form_modal(
            page=page,
            criminalist=criminalist,
            collection=collection,
            on_save=on_form_save,
            dept_map=dept_map,
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def _on_toggle_active(criminalist: Criminalist):
        """Pereклюchit status aktivnosti"""
        criminalist.is_active = not criminalist.is_active
        save_criminalists(collection.criminalists)
        autosave()
        
        # Obnovlyaem chasty
        _update_inactive_filter()
        _refresh_tiles()
        
        status = "aktiven" if criminalist.is_active else "otklyuchen"
        from ui.toast import show_toast
        show_toast(page, f"{criminalist.full_name} - {status}")

    def _on_edit_criminalist(criminalist: Criminalist):
        """Otkryt modalnoe okno redaktirovaniya"""
        from .edit_criminalist_modal import create_edit_criminalist_modal
        
        def on_save(full_name: str, note: str, is_active: bool, department_ids: list):
            criminalist.full_name = full_name
            criminalist.note = note
            criminalist.is_active = is_active
            criminalist.zone.department_ids = department_ids
            save_criminalists(collection.criminalists)
            autosave()
            _update_inactive_filter()
            _refresh_tiles()
            from ui.toast import show_save_toast
            show_save_toast(page)
        
        def on_delete():
            _on_delete_criminalist(criminalist)
        
        dialog = create_edit_criminalist_modal(
            page=page,
            criminalist=criminalist,
            on_save=on_save,
            on_delete=on_delete,
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def _on_delete_criminalist(criminalist: Criminalist):
        """Udalit kriminalista"""
        def confirm_delete(e=None):
            collection.criminalists = [c for c in collection.criminalists if c.id != criminalist.id]
            save_criminalists(collection.criminalists)
            autosave()
            _update_inactive_filter()
            _refresh_tiles()
            from ui.toast import show_toast
            show_toast(page, f"Udalen: {criminalist.full_name}")
        
        def cancel_delete(e=None):
            dialog.open = False
            page.update()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("!!! Udalenie kriminalista", size=16,
                          weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            content=ft.Text(
                f"Uvereny, chto hochete udalit {criminalist.full_name}?\n\n"
                f"Vse dannye budut poteryany.",
                size=13,
                color=COLORS["text"],
            ),
            actions=[
                ft.TextButton("Otmenit", on_click=cancel_delete),
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
        """Otkryt dialog dobavleniya kriminalista"""
        from .edit_criminalist_modal import create_edit_criminalist_modal
        
        def on_save(full_name: str, note: str, is_active: bool, department_ids: list):
            max_id = max((c.id for c in collection.criminalists), default=0)
            new_id = max_id + 1
            from core.zonal_models import Criminalist, CriminalistZone
            new_criminalist = Criminalist(
                id=new_id,
                full_name=full_name,
                note=note,
                is_active=is_active,
                zone=CriminalistZone(
                    criminalist_id=new_id,
                    department_ids=department_ids,
                ),
            )
            collection.criminalists.append(new_criminalist)
            save_criminalists(collection.criminalists)
            autosave()
            _update_inactive_filter()
            _refresh_tiles()
            from ui.toast import show_toast
            show_toast(page, f"Dobavlen: {full_name}")
        
        def on_delete():
            pass  # Neispolzuetsya pri dobavlenii
        
        dialog = create_edit_criminalist_modal(
            page=page,
            criminalist=None,
            on_save=on_save,
            on_delete=on_delete,
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def _on_show_inactive_changed(e):
        """Pereклюchit pokaz neaktivnyh"""
        show_inactive_ref["value"] = e.control.value
        _refresh_tiles()

    def _on_search_change(e):
        """Poisk po FIO"""
        search_query_ref["value"] = e.control.value or ""
        _refresh_tiles()
        
        # Pokazat/skrty kknopku ochistki
        clear_btn.visible = len(search_query_ref["value"]) > 0
        try:
            clear_btn.update()
        except Exception:
            pass

    def _on_search_clear(e):
        """Ochistit poisk"""
        if search_field_ref["field"]:
            search_field_ref["field"].value = ""
            search_field_ref["field"].update()
        search_query_ref["value"] = ""
        clear_btn.visible = False
        _refresh_tiles()

    def _on_copy_not_submitted():
        """Skopirovat spisok ne sdavshih v bufer obmena"""
        from .utils import get_not_submitted_list
        
        text = get_not_submitted_list(collection, dept_map)
        
        try:
            page.set_clipboard(text)
            from ui.toast import show_toast
            show_toast(page, "Spisok skopirovan v bufer")
        except Exception as e:
            print(f"[ZONAL_TAB] Ne udalos kopirovat: {e}")
            from ui.toast import show_error_toast
            show_error_toast(page, "Oshibka kopirovaniya")

    def _update_inactive_filter():
        """Obnovit vidimost filtra neaktivnyh"""
        inactive_count = sum(1 for c in collection.criminalists if not c.is_active)
        if inactive_checkbox:
            inactive_checkbox.label = f"Pokazyvat otklyuchennyh ({inactive_count})" if inactive_count else "Pokazyvat otklyuchennyh"
            inactive_checkbox.visible = inactive_count > 0
            try:
                inactive_checkbox.update()
            except Exception:
                pass

    def _on_template_clear():
        """Ochistit vse punkty shapona"""
        collection.template.items.clear()
        collection.template.name = "Novaya forma"
        collection.template.use_departments_mode = False
        autosave()
        _refresh_tiles()
        from ui.toast import show_toast
        show_toast(page, "Forma ochischena")

    def _on_reset_data():
        """Sbrosit vse dannye, sohraniv shaplon"""
        has_data = len(collection.submissions) > 0
        
        if not has_data:
            from ui.toast import show_toast
            show_toast(page, "Dannye uzhe pusty")
            return
        
        def confirm_reset(e=None):
            collection.submissions.clear()
            clear_zonal_submissions()
            autosave()
            _refresh_tiles()
            dialog.open = False
            page.update()
            from ui.toast import show_toast
            show_toast(page, "Dannye sbroшенy, shaplon sohranen")
        
        def cancel_reset(e=None):
            dialog.open = False
            page.update()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("--- Sbros dannyh ---", size=16,
                          weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            content=ft.Text(
                f"Ochistit vse vvedennye dannye ({len(collection.submissions)} zapisey)?\n\n"
                f"Struktura shapona budet sohranena.",
                size=13,
                color=COLORS["text"],
            ),
            actions=[
                ft.TextButton("Otmenit", on_click=cancel_reset),
                ft.ElevatedButton(
                    "Sbrosit",
                    bgcolor="#f59e0b",
                    color=COLORS["text_light"],
                    on_click=confirm_reset,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def _on_export_excel():
        """Eksport v Excel"""
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

    # ── Postroenie UI ────────────────────────────────────────
    
    # Zagolovok sekcii
    section_header = ft.Container(
        content=ft.Row(
            controls=[
                ft.Text("[=] ZONALNYE KRIMINALISTY", size=18, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            ],
        ),
        padding=ft.padding.only(bottom=8),
    )
    
    # Panel upravleniya (Compact)
    inactive_count = sum(1 for c in collection.criminalists if not c.is_active)
    
    inactive_checkbox = ft.Checkbox(
        label=f"Pokazyvat otklyuchennyh ({inactive_count})" if inactive_count else "Pokazyvat otklyuchennyh",
        value=False,
        active_color=COLORS["btn_save"],
        label_style=ft.TextStyle(size=12, color=COLORS["text_secondary"]),
        on_change=_on_show_inactive_changed,
        visible=inactive_count > 0,
    )
    
    # Poysk
    search_field = ft.TextField(
        hint_text="Poisk po FIO...",
        prefix_icon=ft.icons.SEARCH,
        border_radius=8,
        border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"],
        color=COLORS["text"],
        hint_style=ft.TextStyle(color=COLORS["text_muted"]),
        height=38,
        text_size=13,
        width=200,
        on_change=_on_search_change,
    )
    search_field_ref["field"] = search_field
    
    clear_btn = ft.IconButton(
        icon=ft.icons.CLOSE,
        icon_size=18,
        icon_color=COLORS["text_secondary"],
        tooltip="Ochistit poisk",
        visible=False,
        on_click=_on_search_clear,
        style=ft.ButtonStyle(padding=ft.padding.all(4)),
    )
    
    # Knopki
    add_btn = ft.ElevatedButton(
        text="[+] Dobavit",
        bgcolor=COLORS["btn_save"],
        color="white",
        height=38,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=14),
        ),
        on_click=lambda e: _on_add_criminalist(),
    )
    
    export_btn = ft.ElevatedButton(
        text="[XLS] Export",
        bgcolor=COLORS["btn_export"],
        color="white",
        height=38,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=14),
        ),
        on_click=lambda e: _on_export_excel(),
    )
    
    copy_btn = ft.OutlinedButton(
        text="[Copy] Ne sdali",
        height=38,
        style=ft.ButtonStyle(
            color=COLORS["btn_save"],
            side=ft.BorderSide(1, COLORS["btn_save"]),
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=14),
        ),
        on_click=lambda e: _on_copy_not_submitted(),
    )
    
    clear_data_btn = ft.OutlinedButton(
        text="[---] Sbros",
        height=38,
        style=ft.ButtonStyle(
            color="#f59e0b",
            side=ft.BorderSide(1, "#f59e0b"),
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=14),
        ),
        on_click=lambda e: _on_reset_data(),
    )
    
    # Panel upravleniya
    control_panel = ft.Container(
        content=ft.Row(
            controls=[
                ft.Row(
                    controls=[search_field, clear_btn],
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(expand=True),
                inactive_checkbox,
                ft.Container(width=8),
                add_btn,
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
        bgcolor=COLORS["card"],
        border=ft.border.all(1, COLORS["border"]),
        border_radius=10,
    )
    
    # Svodka
    from .compact_summary import create_compact_summary
    summary_container = ft.Container(
        content=create_compact_summary(collection),
        padding=ft.padding.only(bottom=12),
    )
    summary_ref["panel"] = summary_container
    
    # Setka ploshek
    from .criminalist_tile import create_tiles_grid
    
    initial_tiles = []
    for c in collection.criminalists:
        if c.is_active or show_inactive_ref["value"]:
            initial_tiles.append(c)
    
    initial_grid = create_tiles_grid(
        page=page,
        collection=collection,
        on_click=_on_tile_click,
        on_toggle_active=_on_toggle_active,
        on_edit=_on_edit_criminalist,
        dept_map=dept_map,
        show_inactive=show_inactive_ref["value"],
    )
    
    tiles_container = ft.Container(
        content=initial_grid,
        padding=ft.padding.only(bottom=16),
    )
    tiles_container_ref["control"] = tiles_container
    tiles_grid_ref["control"] = initial_grid
    
    # Knopki nizu
    bottom_buttons = ft.Row(
        controls=[
            copy_btn,
            clear_data_btn,
            ft.Container(expand=True),
            export_btn,
        ],
        spacing=10,
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )
    
    # --- Vlozhenie v konstruktor shapona (dlya sohraneniya funkcionala) ---
    # Etot blok dolzhen byt, no mozhet byt skryt ili umenshen
    template_section = _create_mini_template_builder()

    # Vsya vkladka
    tab_content = ft.Column(
        controls=[
            section_header,
            template_section,
            ft.Container(height=12),
            summary_container,
            ft.Container(height=8),
            control_panel,
            ft.Container(height=12),
            tiles_container,
            ft.Container(height=8),
            bottom_buttons,
            ft.Container(height=20),
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    print("[ZONAL_TAB] Vkladka sozdana uspeshno")
    return tab_content


def _create_mini_template_builder() -> ft.Container:
    """
    Sozdat minimalnyy konstruktor shapona (sjato).
    Dlya sovmestimi s suschestvuyuschim funkcionalom.
    """
    # Eto minimalnyy placeholder - polnyy konstruktor mozhet byt v separate file
    return ft.Container(
        content=ft.Container(
            content=ft.Text(
                "Shaplon: ispolzuyte polnyy konstruktor v张开 Konstruktor vkladke",
                size=11,
                color=COLORS["text_muted"],
                italic=True,
            ),
            padding=ft.padding.all(8),
        ),
        bgcolor=COLORS["primary_light"],
        border=ft.border.all(1, COLORS["border"]),
        border_radius=8,
    )
