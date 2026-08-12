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
)
try:
    from core.zonal_data import save_zonal_collection
except Exception:
    save_zonal_collection = None
from core.models import Department, Status
from core.constants import COLORS

# ── UI-компоненты (первая вкладка) ──────────────────────────────
from ui.header import create_compact_header, update_header_save_date
from ui.stats_bar import create_stats_bar, update_stats_bar
from ui.toolbar import create_toolbar
from ui.legend import create_legend
from ui.department_table import create_department_table, filter_table, rebuild_department_table
from ui.edit_departments_modal import create_edit_departments_modal
from ui.export_modal import create_export_modal
from ui.reset_modal import create_reset_modal
from ui.toast import show_save_toast, show_reset_toast, show_error_toast


# ────────────────────────────────────────────────────────────────
# ГЛАВНАЯ ФУНКЦИЯ
# ────────────────────────────────────────────────────────────────

def main(page: ft.Page) -> None:
    """Точка входа Flet-приложения"""

    # Раунд 20 (задача 4): сериализация ВСЕХ тел обработчиков событий и
    # page.update() одним глобальным RLock — устраняет гонку «пересборка
    # дерева vs diff-движок» (AssertionError __uid, «мертвые фильтры»).
    # Ставим первой строкой: события могут прийти уже во время построения.
    try:
        from ui.update_lock import install_update_serialization
        install_update_serialization(page)
    except Exception:
        pass

    # Раунд 23 (задача 2): редакция дистрибутива (admin/user) — диагностика;
    # автозапуск в Windows (только frozen-сборка; чтобы пользователи не
    # забывали запускать приложение после включения ПК).
    try:
        from core.edition import load_edition
        _ed = load_edition()
        print(f"[MAIN] Redakciya: {_ed.get('role')}"
              + (f" ({_ed.get('user_name')})" if _ed.get('user_name') else ""))
    except Exception:
        pass
    try:
        from core import autostart
        autostart.enable_autostart()  # no-op вне Windows / dev-запуска
    except Exception:
        pass

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

    def _refresh_table_and_stats():
        rebuild_department_table(page, departments, on_status_change)
        update_stats_bar(page, departments)
        update_header_save_date(page)

    def on_edit_departments() -> None:
        dialog = create_edit_departments_modal(
            page=page,
            departments=departments,
            on_save=lambda _: (_refresh_table_and_stats(), save_departments(departments)),
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

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
        for dept in departments:
            dept.status = Status.EMPTY
            dept.updated_at = None
        save_departments(departments)
        _refresh_table_and_stats()
        show_reset_toast(page)

    def on_reset() -> None:
        if hasattr(page, "open_reset_modal"):
            page.open_reset_modal()

    def on_search(query: str) -> None:
        filter_table(page, query)

    # ── Создать компоненты первой вкладки ───────────────────────
    stats_bar = create_stats_bar(page, departments)
    toolbar = create_toolbar(page, on_search, on_save, on_export, on_reset, on_edit_departments)
    legend = create_legend()

    # Подсказка над канбаном
    kanban_hint = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.icons.INFO_OUTLINE, size=14, color=COLORS["text_muted"]),
                ft.Text(
                    "Клик по карточке двигает её вправо по статусам →",
                    size=11,
                    color=COLORS["text_muted"],
                    italic=True,
                ),
            ],
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        ),
        padding=ft.padding.only(left=4, bottom=4),
    )

    print(f"[OK] Departments loaded: {len(departments)}")

    table = create_department_table(page, departments, on_status_change)
    export_modal = create_export_modal(page, departments)
    reset_modal = create_reset_modal(page, on_reset_confirm)

    page.overlay.extend([export_modal, reset_modal])

    # ── Содержимое первой вкладки ────────────────────────────────
    # Канбан-доска должна заполнять оставшееся пространство по вертикали,
    # поэтому внешняя Column БЕЗ scroll — прокрутка внутри колонок канбана.
    tab1_content = ft.Container(
        content=ft.Column(
            controls=[
                stats_bar,
                ft.Container(height=12),
                toolbar,
                ft.Container(height=8),
                legend,
                ft.Container(height=6),
                kanban_hint,
                ft.Container(height=4),
                table,
            ],
            spacing=0,
            expand=True,
        ),
        padding=ft.padding.only(left=20, right=20, top=12, bottom=12),
        expand=True,
    )

    # ── Создать вторую вкладку (Зональные) ──────────────────────
    print("[MAIN] Создаю вкладку Зональные...")
    try:
        from ui.zonal.zonal_tab import create_zonal_tab
        zonal_content_raw = create_zonal_tab(page)

        tab2_content = ft.Container(
            content=zonal_content_raw,
            padding=ft.padding.only(left=20, right=20, top=12, bottom=12),
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

    # ── Создать третью вкладку (Контроли) ───────────────────────
    print("[MAIN] Создаю вкладку Контроли...")
    try:
        from ui.controls.controls_tab import create_controls_tab
        controls_content_raw = create_controls_tab(page)

        tab3_content = ft.Container(
            content=controls_content_raw,
            padding=ft.padding.only(left=20, right=20, top=12, bottom=12),
            expand=True,
        )
        print("[MAIN] [OK] Vkladka Kontroli sozdana")
    except Exception as e:
        import traceback
        print(f"[MAIN] [ERROR] Oshibka sozdaniya vkladki Kontroli: {e}")
        traceback.print_exc()
        tab3_content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(f"Oshibka zagruzki vkladki: {e}", color="#dc2626"),
                ],
            ),
            padding=ft.padding.all(20),
            expand=True,
        )

    # ── Вкладки (custom, без ft.Tabs) ─────────────────────────────
    # Раунд 21 (задача 8): порядок вкладок — «Контроли» (первая и по
    # умолчанию), «Зональные», «Следственные отделы». Контейнеры сохраняют
    # прежние имена (tab1 = отделы, tab2 = зональные, tab3 = контроли),
    # ПОРЯДОК задаётся маппингом в _switch_tab/_mk_tab_btn — логика
    # вкладок (polling, сохранение) не затронута.
    tab1_container = ft.Container(
        content=tab1_content,
        expand=True,
        visible=False,
    )
    tab2_container = ft.Container(
        content=tab2_content,
        expand=True,
        visible=False,
    )
    tab3_container = ft.Container(
        content=tab3_content,
        expand=True,
        visible=True,
    )
    content_area = ft.Stack(
        controls=[tab1_container, tab2_container, tab3_container],
        fit=ft.StackFit.EXPAND,
        expand=True,
    )

    def _restyle_tabs():
        for idx, (btn, ico) in enumerate(
                ((btn_tab1, icon_tab1), (btn_tab2, icon_tab2), (btn_tab3, icon_tab3))):
            selected = (idx == active_tab["value"])
            btn.bgcolor = COLORS["btn_save"] if selected else "transparent"
            for ctl in btn.content.controls:
                if isinstance(ctl, ft.Text):
                    ctl.color = COLORS["text_light"] if selected else COLORS["text_secondary"]
            ico.color = COLORS["text_light"] if selected else COLORS["text_secondary"]
            try:
                btn.update()
            except Exception:
                pass

    def _switch_tab(index: int):
        # Раунд 21 (задача 8): индексы кнопок — НОВЫЙ порядок
        # (0=Контроли, 1=Зональные, 2=Следственные отделы).
        active_tab["value"] = index
        tab3_container.visible = (index == 0)
        tab2_container.visible = (index == 1)
        tab1_container.visible = (index == 2)
        _restyle_tabs()
        try:
            content_area.update()
        except Exception:
            pass

    def _mk_tab_btn(index: int, label: str, icon) -> tuple:
        ico = ft.Icon(icon, size=15, color=COLORS["text_light"] if index == 0 else COLORS["text_secondary"])
        btn = ft.Container(
            content=ft.Row(
                controls=[
                    ico,
                    ft.Text(
                        label,
                        size=12,
                        weight=ft.FontWeight.W_600,
                        color=COLORS["text_light"] if index == 0 else COLORS["text_secondary"],
                        no_wrap=True,
                    ),
                ],
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
            height=32,
            padding=ft.padding.symmetric(horizontal=14),
            border_radius=8,
            alignment=ft.alignment.center,
            bgcolor=COLORS["btn_save"] if index == 0 else "transparent",
            ink=True,
            on_click=lambda e, i=index: _switch_tab(i),
            tooltip=f"Вкладка: {label}",
        )
        return btn, ico

    active_tab = {"value": 0}
    # Раунд 21 (задача 8): «Контроли» — первая и активная по умолчанию
    btn_tab1, icon_tab1 = _mk_tab_btn(0, "Контроли", ft.icons.RULE_FOLDER)
    btn_tab2, icon_tab2 = _mk_tab_btn(1, "Зональные", ft.icons.MAP_OUTLINED)
    btn_tab3, icon_tab3 = _mk_tab_btn(2, "Следственные отделы", ft.icons.ACCOUNT_BALANCE_OUTLINED)

    tab_bar = ft.Container(
        content=ft.Row(
            controls=[btn_tab1, btn_tab2, btn_tab3],
            spacing=4,
            alignment=ft.MainAxisAlignment.START,
            tight=True,
        ),
        height=40,
        padding=ft.padding.all(4),
        bgcolor=COLORS["primary_light"],
        border=ft.border.all(1, COLORS["border"]),
        border_radius=10,
    )

    header = create_compact_header(page, get_last_save_date(), tab_bar)

    # ── Сборка страницы ──────────────────────────────────────────
    page.add(
        ft.Column(
            controls=[
                header,
                content_area,
            ],
            spacing=0,
            expand=True,
        )
    )

    page.update()

    # Раунд 23 (задача 2): значок в системном трее («Открыть»/«Выход») —
    # приложение живёт в трее и всегда на слуху (pystray — опциональная
    # зависимость сборки; без неё — просто работаем без трея).
    try:
        from ui.tray_icon import start_tray
        page._tray_icon = start_tray(page)
    except Exception:
        pass

    # Сохранение при закрытии окна (страховка в дополнение к autosave)
    def _on_window_event(e):
        if e.data == "close":
            # Остановить фоновый polling вкладки «Контроли»
            try:
                if hasattr(page, "_controls_poll_stop"):
                    page._controls_poll_stop["flag"] = True
            except Exception:
                pass
            try:
                save_departments(departments)
                if hasattr(page, "_zonal_collection") and save_zonal_collection is not None:
                    save_zonal_collection(page._zonal_collection)
                update_header_save_date(page)
                print("[MAIN] Data saved on window close")
            except Exception as ex:
                print(f"[MAIN] Save on close error: {ex}")
            finally:
                try:
                    page.window.prevent_close = False
                    page.window.close()
                except Exception:
                    pass

    page.window.prevent_close = True
    try:
        page.window.on_event = _on_window_event
    except Exception:
        # fallback for older API — deprecated path
        page.on_window_event = _on_window_event


# ────────────────────────────────────────────────────────────────
# ТОЧКА ВХОДА
# ────────────────────────────────────────────────────────────────
def _entry():
    """Раунд 24 (задача 2): вход вынесен в функцию, чтобы main_web.py
    (web-обёртка для Win7) мог безопасно переиспользовать его импортом —
    runpy.run_path в frozen-бандле не работает (main.py нет на диске)."""
    # Раунд 23 (задача 3): нативный клиент Flet 0.23.2 (движок Flutter) не
    # поддерживает Windows 7 — он требует Win10+. Для пользовательских
    # Win7-машин — web-режим (открывается в установленном браузере Win7):
    #   python main.py --web [--host 0.0.0.0] [--port 8555]
    # Админские Win10/11-машины — нативный режим по умолчанию.
    import os
    import sys
    if "--web" in sys.argv:
        # Раунд 24 (задача 4): web-режим — без трея (ui/tray_icon.py читает
        # PORAYONKA_WEB и мягко пропускается).
        os.environ["PORAYONKA_WEB"] = "1"
        host, port = "127.0.0.1", 8555
        if "--host" in sys.argv:
            host = sys.argv[sys.argv.index("--host") + 1]
        if "--port" in sys.argv:
            port = int(sys.argv[sys.argv.index("--port") + 1])
        print(f"[MAIN] Web-rezhim: http://{host}:{port}")
        ft.app(target=main, view=ft.AppView.WEB_BROWSER, host=host, port=port)
    else:
        ft.app(target=main)


if __name__ == "__main__":
    _entry()