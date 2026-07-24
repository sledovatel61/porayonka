# main.py
# ════════════════════════════════════════════════════════════════
# ПОРАЙОНКА v2.0
# Трекер статусов следственных отделов СК РФ (Ростовская область)
# + Вкладка "Зональные" для зональных криминалистов
# ════════════════════════════════════════════════════════════════
import flet as ft
from datetime import datetime
from typing import List

# ── Ядро ────────────────────────────────────────────────────────
from core.data import (
    load_departments,
    save_departments,
    get_last_save_date,
    reset_departments,
)
from core.models import Department, Status
from core.constants import COLORS

# ── UI-компоненты (первая вкладка) ──────────────────────────────
from ui.header import create_header, update_header_save_date
from ui.stats_bar import create_stats_bar, update_stats_bar
from ui.toolbar import create_toolbar
from ui.legend import create_legend
from ui.department_table import create_department_table, filter_table
from ui.export_modal import create_export_modal
from ui.reset_modal import create_reset_modal
from ui.toast import show_save_toast, show_reset_toast, show_error_toast


# ────────────────────────────────────────────────────────────────
# ГЛАВНАЯ ФУНКЦИЯ
# ────────────────────────────────────────────────────────────────

def main(page: ft.Page) -> None:
    """Точка входа Flet-приложения"""

    # ── Настройки окна ──────────────────────────────────────────
    page.title = "Порайонка — СК РФ Ростовская область"
    page.window.width = 1280
    page.window.height = 860
    page.window.min_width = 900
    page.window.min_height = 650
    page.window.center()
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.spacing = 0
    page.bgcolor = COLORS["bg"]

    # Применить тему
    try:
        from assets.styles import get_app_theme
        page.theme = get_app_theme()
    except Exception:
        pass

    # ── Загрузить данные ─────────────────────────────────────────
    departments: List[Department] = load_departments()

    # ── Колбэки первой вкладки ───────────────────────────────────
    def on_status_change(dept: Department) -> None:
        try:
            save_departments(departments)
            update_header_save_date(page)
            update_stats_bar(page, departments)
        except Exception as ex:
            show_error_toast(page, f"Ошибка сохранения: {ex}")

    def on_save() -> None:
        try:
            save_departments(departments)
            update_header_save_date(page)
            show_save_toast(page)
        except Exception as ex:
            show_error_toast(page, f"Ошибка сохранения: {ex}")

    def on_export() -> None:
        if hasattr(page, "open_export_modal"):
            page.open_export_modal()

    def on_reset_confirm() -> None:
        nonlocal departments
        reset_departments()
        for dept in departments:
            dept.status = Status.EMPTY
            dept.updated_at = None
        if hasattr(page, "status_cells"):
            from ui.status_cell import update_status_cell
            for dept in departments:
                cell = page.status_cells.get(dept.id)
                if cell:
                    update_status_cell(cell, dept)
        update_stats_bar(page, departments)
        update_header_save_date(page)
        show_reset_toast(page)

    def on_reset() -> None:
        if hasattr(page, "open_reset_modal"):
            page.open_reset_modal()

    def on_search(query: str) -> None:
        filter_table(page, query)

    # ── Создать компоненты первой вкладки ───────────────────────
    header = create_header(page, get_last_save_date())
    stats_bar = create_stats_bar(page, departments)
    toolbar = create_toolbar(page, on_search, on_save, on_export, on_reset)
    legend = create_legend()

    print(f"[OK] Departments loaded: {len(departments)}")

    table = create_department_table(page, departments, on_status_change)
    export_modal = create_export_modal(page, departments)
    reset_modal = create_reset_modal(page, on_reset_confirm)

    page.overlay.extend([export_modal, reset_modal])

    # ── Содержимое первой вкладки ────────────────────────────────
    tab1_content = ft.Container(
        content=ft.Column(
            controls=[
                stats_bar,
                ft.Container(height=16),
                toolbar,
                ft.Container(height=10),
                legend,
                ft.Container(height=14),
                table,
                ft.Container(height=20),
            ],
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=ft.padding.all(20),
        expand=True,
    )

    # ── Создать вторую вкладку (Зональные) ──────────────────────
    print("[MAIN] Создаю вкладку Зональные...")
    try:
        from ui.zonal.zonal_tab import create_zonal_tab
        zonal_content_raw = create_zonal_tab(page)

        tab2_content = ft.Container(
            content=zonal_content_raw,
            padding=ft.padding.all(20),
            expand=True,
        )
        print("[MAIN] [OK] Vkladka Zonalnye sozdana")
    except Exception as e:
        import traceback
        print(f"[MAIN] [ERROR] Oshibka sozdaniya vkladki Zonalnye: {e}")
        traceback.print_exc()
        tab2_content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(f"Oshibka zagruzki vkladki: {e}", color="#dc2626"),
                ],
            ),
            padding=ft.padding.all(20),
            expand=True,
        )

    # ── Вкладки (custom, без ft.Tabs) ─────────────────────────────
    tab1_container = ft.Container(
        content=tab1_content,
        expand=True,
        visible=True,
    )
    tab2_container = ft.Container(
        content=tab2_content,
        expand=True,
        visible=False,
    )
    content_area = ft.Stack(
        controls=[tab1_container, tab2_container],
        expand=True,
    )

    def _switch_tab(index: int):
        tab1_container.visible = (index == 0)
        tab2_container.visible = (index == 1)
        btn_tab1.style.bgcolor = COLORS["btn_save"] if index == 0 else COLORS["primary_light"]
        btn_tab2.style.bgcolor = COLORS["btn_save"] if index == 1 else COLORS["primary_light"]
        try:
            content_area.update()
            btn_tab1.update()
            btn_tab2.update()
        except Exception:
            pass

    btn_tab1 = ft.ElevatedButton(
        text="Следственные отделы",
        color=COLORS["text"],
        bgcolor=COLORS["btn_save"],
        height=40,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=16),
        ),
        on_click=lambda e: _switch_tab(0),
    )
    btn_tab2 = ft.ElevatedButton(
        text="Зональные",
        color=COLORS["text"],
        bgcolor=COLORS["primary_light"],
        height=40,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=16),
        ),
        on_click=lambda e: _switch_tab(1),
    )
    tab_bar = ft.Container(
        content=ft.Row(
            controls=[btn_tab1, btn_tab2],
            spacing=12,
            alignment=ft.MainAxisAlignment.START,
        ),
        padding=ft.padding.symmetric(horizontal=20, vertical=8),
        bgcolor=COLORS["primary"],
    )

    # ── Сборка страницы ──────────────────────────────────────────
    page.add(
        ft.Column(
            controls=[
                header,
                tab_bar,
                content_area,
            ],
            spacing=0,
            expand=True,
        )
    )

    page.update()


# ────────────────────────────────────────────────────────────────
# ТОЧКА ВХОДА
# ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ft.app(target=main)