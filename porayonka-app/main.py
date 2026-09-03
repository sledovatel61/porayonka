# main.py
# ════════════════════════════════════════════════════════════════
# ПОРАЙОНКА v2.0
# Трекер статусов следственных отделов СК РФ (Ростовская область)
# + Вкладка "Зональные" для зональных криминалистов
# ════════════════════════════════════════════════════════════════
import flet as ft
from datetime import datetime
from typing import List

# Раунд 33 (задача 1.1): файловый лог необработанных исключений —
# в frozen-сборках console=False падения не видны, пишем в
# %APPDATA%/porayonka/error.log. ДО всех остальных импортов/вызовов.
try:
    from core.crash_log import install_crash_hook
    install_crash_hook()
except Exception:
    pass

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
    """Точка входа Flet-приложения (обёртка-ворота).

    Раунд 34: ввод пароля администратора ОТКЛЮЧЁН ПОЛНОСТЬЮ — живой тест
    раунда 33 показал, что диалог не пускал в admin-приложение. Admin-
    редакция открывается сразу. Код ворот сохранён в ui/admin_gate.py
    (не удалять) для возможного будущего возврата.
    Поток: main() -> _main_impl(page); применение редакции к настройкам
    (admin сбрасывает user-наследие) — внутри create_controls_tab.
    """
    try:
        from ui.update_lock import install_update_serialization
        install_update_serialization(page)   # идемпотентно (см. раунд 20)
    except Exception:
        pass
    # Раунд 34: пароль admin отключён — сразу строим UI.
    #
    # Было (раунды 26-33):
    #   try:
    #       from ui.admin_gate import show_admin_password_gate
    #       show_admin_password_gate(page, on_ok=lambda: _main_impl(page))
    #   except Exception as ex:
    #       # Ворота сломались — не блокируем запуск навсегда (fail-open).
    #       print(f"[MAIN] auth gate error: {ex}")
    #       _main_impl(page)
    _main_impl(page)


def _main_impl(page: ft.Page) -> None:
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
        # Раунд 26 (задача 6): «Настройка формы» видна только на «Зональных»
        try:
            _bfs = getattr(page, "_btn_form_settings", None)
            if _bfs is not None:
                _bfs.visible = (index == 1)
                _bfs.update()
        except Exception:
            pass
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

    # Раунд 26 (задача 6): «Настройка формы» видна, только если активная
    # вкладка — «Зональные» (по умолчанию активны «Контроли» → скрыта).
    header = create_compact_header(page, get_last_save_date(), tab_bar,
                                   form_settings_visible=(active_tab["value"] == 1))

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

    # Раунд 33 (задача 1.2/2.4): обработчик закрытия окна назначается ДО
    # старта трея — в frozen-сборке иначе окно «теряет» сворачивание в трей.
    def _on_window_event(e):
        if e.data == "close":
            print("[MAIN] window close event")
            # Сохраняем данные всегда (страховка в дополнение к autosave)
            try:
                save_departments(departments)
                if hasattr(page, "_zonal_collection") and save_zonal_collection is not None:
                    save_zonal_collection(page._zonal_collection)
                update_header_save_date(page)
                print("[MAIN] Data saved on window close")
            except Exception as ex:
                print(f"[MAIN] Save on close error: {ex}")
            # Раунд 32 (задача 2): если есть трей — закрытие крестиком
            # СВОРАЧИВАЕТ приложение в трей (процесс живёт, polling
            # продолжает работать, «Открыть» в трее восстанавливает окно).
            # Без трея — обычный выход.
            _tray32 = getattr(page, "_tray_icon", None)
            if _tray32 is not None:
                try:
                    page.window.visible = False
                    page.update()
                    print("[MAIN] window hidden to tray")
                except Exception:
                    pass
            else:
                try:
                    if hasattr(page, "_controls_poll_stop"):
                        page._controls_poll_stop["flag"] = True
                except Exception:
                    pass
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

    # Раунд 23 (задача 2): значок в системном трее («Открыть»/«Выход») —
    # приложение живёт в трее и всегда на слуху (pystray — опциональная
    # зависимость сборки; без неё — просто работаем без трея).
    # Раунд 26 (задача 2): в web-режиме трей стартует один раз в _entry()
    # с URL сервера (main() вызывается на КАЖДУЮ браузерную сессию —
    # второй значок не нужен); здесь сессии только получают ссылку на иконку
    # для balloon-уведомлений по срокам.
    try:
        import os as _os26
        if _os26.environ.get("PORAYONKA_WEB"):
            from ui.tray_icon import get_active_icon
            page._tray_icon = get_active_icon()
        else:
            from ui.tray_icon import start_tray
            page._tray_icon = start_tray(page)
    except Exception:
        pass


# ────────────────────────────────────────────────────────────────
# ТОЧКА ВХОДА
# ────────────────────────────────────────────────────────────────
def _ensure_console_streams() -> bool:
    """Раунд 26 (задача 1): PyInstaller onefile с console=False ставит
    sys.stdout/sys.stderr = None — uvicorn (web-сервер Flet) при старте
    вызывает sys.stdout.isatty() и падает:
      AttributeError: 'NoneType' object has no attribute 'isatty' и
      ValueError: Unable to configure formatter 'default'.
    Подменяем потоки на devnull ДО запуска flet/uvicorn. Вызывается из
    web-ветки _entry() и из main_web.py. Возвращает True, если была подмена."""
    import os
    import sys
    fixed = False
    for _nm in ("stdout", "stderr"):
        if getattr(sys, _nm, None) is None:
            try:
                setattr(sys, _nm,
                        open(os.devnull, "w", encoding="utf-8", errors="replace"))
                fixed = True
            except Exception:
                pass
    return fixed


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
        os.environ["PORAYONKA_WEB"] = "1"
        # Раунд 38 (задачи 3.3/7): в web-режиме FLET_ASSETS_DIR ведёт в
        # пользовательский каталог %APPDATA%\porayonka\web_assets — туда
        # копируются статические файлы бандла (иконка/звук), а кнопка
        # «Скачать» вложения кладёт копии для отдачи браузеру
        # (/assets/downloads/). Делается ДО ft.app — сервер читает env при
        # запуске. Desktop-режим не затрагивается.
        try:
            import shutil as _sh38w
            _appdata38 = os.environ.get("APPDATA") or os.path.expanduser("~")
            _wa38 = os.path.join(_appdata38, "porayonka", "web_assets")
            os.makedirs(_wa38, exist_ok=True)
            _src38 = None
            if getattr(sys, "frozen", False):
                _src38 = os.path.join(getattr(sys, "_MEIPASS", ""), "assets")
            else:
                _src38 = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "assets")
            if _src38 and os.path.isdir(_src38):
                for _nm38 in os.listdir(_src38):
                    _sp38 = os.path.join(_src38, _nm38)
                    if os.path.isfile(_sp38):
                        try:
                            _sh38w.copy2(_sp38, os.path.join(_wa38, _nm38))
                        except OSError:
                            pass
            # свежая сессия — чистим каталог скачанных копий
            _dl38 = os.path.join(_wa38, "downloads")
            if os.path.isdir(_dl38):
                _sh38w.rmtree(_dl38, ignore_errors=True)
            os.makedirs(_dl38, exist_ok=True)
            os.environ["FLET_ASSETS_DIR"] = _wa38
        except Exception:
            pass
        # Раунд 26 (задача 1): у frozen console=False нет stdout/stderr —
        # чиним ДО старта uvicorn (внутри ft.app).
        _ensure_console_streams()
        host, port = "127.0.0.1", 8555
        if "--host" in sys.argv:
            host = sys.argv[sys.argv.index("--host") + 1]
        if "--port" in sys.argv:
            port = int(sys.argv[sys.argv.index("--port") + 1])
        # Раунд 26 (задача 2): трей ДО старта сервера ОДИН РАЗ НА ПРОЦЕСС,
        # с URL для «Открыть»/клика по значку (браузер может быть закрыт;
        # процесс живёт, пока жив трей и uvicorn).
        try:
            from ui.tray_icon import start_tray
            _web_url = (f"http://127.0.0.1:{port}"
                        if host in ("0.0.0.0", "") else f"http://{host}:{port}")
            start_tray(None, web_url=_web_url)
        except Exception:
            pass
        print(f"[MAIN] Web-rezhim: http://{host}:{port}")
        ft.app(target=main, view=ft.AppView.WEB_BROWSER, host=host, port=port)
    else:
        ft.app(target=main)


if __name__ == "__main__":
    _entry()