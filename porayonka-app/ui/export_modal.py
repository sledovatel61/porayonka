# [DARK THEME] Обновлено только визуально, логика сохранена.
# ui/export_modal.py
import flet as ft
import os
import traceback
from pathlib import Path
from datetime import datetime
from typing import List
from core.models import Department, Status
from core.constants import COLORS
from core.exporter import ExcelExporter, HTMLExporter


def _get_downloads_path() -> str:
    """Получить путь к папке Загрузок пользователя"""
    print("[EXPORT] Определяю папку загрузок...")
    home = Path.home()
    downloads = home / "Downloads"
    if downloads.exists():
        print(f"[EXPORT] Папка загрузок (Windows): {downloads}")
        return str(downloads)
    downloads = home / "Загрузки"
    if downloads.exists():
        print(f"[EXPORT] Папка загрузок (Linux): {downloads}")
        return str(downloads)
    print(f"[EXPORT] Fallback папка: {home}")
    return str(home)


def create_export_modal(
    page: ft.Page,
    departments: List[Department],
) -> ft.AlertDialog:
    """
    Создать модальное окно экспорта.
    КРИТИЧНО: departments передаётся по ссылке — всегда актуален.
    """
    print("[EXPORT_MODAL] Создаю модальное окно экспорта...")

    excel_badge = ft.Container(
        content=ft.Text("Скачан ✓", size=11, color=COLORS["text_light"],
                        weight=ft.FontWeight.W_600),
        bgcolor=COLORS["received"],
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
        visible=False,
    )
    html_badge = ft.Container(
        content=ft.Text("Скачан ✓", size=11, color=COLORS["text_light"],
                        weight=ft.FontWeight.W_600),
        bgcolor=COLORS["received"],
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
        visible=False,
    )

    def get_stats() -> dict:
        received    = sum(1 for d in departments if d.status == Status.RECEIVED)
        in_progress = sum(1 for d in departments if d.status == Status.IN_PROGRESS)
        empty       = sum(1 for d in departments if d.status == Status.EMPTY)
        print(f"[EXPORT_MODAL] Статистика: получено={received}, в работе={in_progress}, пусто={empty}")
        return dict(received=received, in_progress=in_progress, empty=empty)

    stats = get_stats()

    stat_received_text    = ft.Text(str(stats["received"]),    size=22, weight=ft.FontWeight.BOLD, color=COLORS["received_text"])
    stat_in_progress_text = ft.Text(str(stats["in_progress"]), size=22, weight=ft.FontWeight.BOLD, color=COLORS["in_progress_text"])
    stat_empty_text       = ft.Text(str(stats["empty"]),       size=22, weight=ft.FontWeight.BOLD, color=COLORS["text_secondary"])

    def _make_stat_col(value_text: ft.Text, label: str, label_color: str) -> ft.Column:
        return ft.Column(
            controls=[
                value_text,
                ft.Text(label, size=11, color=label_color),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=2,
        )

    summary_block = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Сводка по экспорту", size=12, weight=ft.FontWeight.W_600,
                        color=COLORS["text"]),
                ft.Container(height=8),
                ft.Row(
                    controls=[
                        _make_stat_col(stat_received_text,    "Получено",    COLORS["received_text"]),
                        ft.VerticalDivider(width=1, color=COLORS["border"]),
                        _make_stat_col(stat_in_progress_text, "В работе",    COLORS["in_progress_text"]),
                        ft.VerticalDivider(width=1, color=COLORS["border"]),
                        _make_stat_col(stat_empty_text,       "Не получено", COLORS["text_secondary"]),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                ),
            ],
        ),
        bgcolor=COLORS["primary_light"],
        border=ft.border.all(1, COLORS["border"]),
        border_radius=10,
        padding=ft.padding.all(14),
    )

    def _make_export_card(
        icon: str,
        title: str,
        description: str,
        badge: ft.Container,
        on_click_handler,
        bg_color: str = COLORS["card"],
        border_color: str = COLORS["border"],
    ) -> ft.Container:
        card = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text(icon, size=28),
                    ft.Column(
                        controls=[
                            ft.Text(title, size=14, weight=ft.FontWeight.BOLD,
                                    color=COLORS["text"]),
                            ft.Text(description, size=11, color=COLORS["text_secondary"]),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    badge,
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=bg_color,
            border=ft.border.all(1.5, border_color),
            border_radius=10,
            padding=ft.padding.all(14),
            on_click=on_click_handler,
            animate=ft.animation.Animation(150, ft.AnimationCurve.EASE_IN_OUT),
        )
        _orig_bg = bg_color

        def on_hover(e: ft.ControlEvent):
            card.bgcolor = COLORS["card_hover"] if e.data == "true" else _orig_bg
            card.update()

        card.on_hover = on_hover
        return card

    def do_export_excel(e):
        print("[EXPORT] ▶ Нажата кнопка Excel")
        print(f"[EXPORT] Количество отделов: {len(departments)}")
        try:
            try:
                import openpyxl
                print(f"[EXPORT] openpyxl версия: {openpyxl.__version__}")
            except ImportError:
                raise ImportError("openpyxl не установлен. Выполните: pip install openpyxl")
            downloads = _get_downloads_path()
            filename  = f"porayonka_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            filepath  = os.path.join(downloads, filename)
            print(f"[EXPORT] Сохраняю Excel в: {filepath}")
            ExcelExporter().export(departments, filepath)
            print(f"[EXPORT] ✓ Excel успешно сохранён: {filepath}")
            if os.path.exists(filepath):
                size = os.path.getsize(filepath)
                print(f"[EXPORT] Размер файла: {size} байт")
            else:
                print("[EXPORT] ⚠ Файл не найден после сохранения!")
            excel_badge.visible = True
            excel_badge.update()
            from ui.toast import show_export_toast
            show_export_toast(page, "Excel")
        except Exception as ex:
            print(f"[EXPORT] ✕ Ошибка Excel: {ex}")
            traceback.print_exc()
            from ui.toast import show_error_toast
            show_error_toast(page, f"Ошибка экспорта Excel: {ex}")

    def do_export_html(e):
        print("[EXPORT] ▶ Нажата кнопка HTML")
        print(f"[EXPORT] Количество отделов: {len(departments)}")
        try:
            downloads = _get_downloads_path()
            filename  = f"porayonka_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            filepath  = os.path.join(downloads, filename)
            print(f"[EXPORT] Сохраняю HTML в: {filepath}")
            HTMLExporter().export(departments, filepath)
            print(f"[EXPORT] ✓ HTML успешно сохранён: {filepath}")
            if os.path.exists(filepath):
                size = os.path.getsize(filepath)
                print(f"[EXPORT] Размер файла: {size} байт")
            else:
                print("[EXPORT] ⚠ Файл не найден после сохранения!")
            html_badge.visible = True
            html_badge.update()
            try:
                import webbrowser
                file_url = f"file:///{filepath.replace(os.sep, '/')}"
                print(f"[EXPORT] Открываю браузер: {file_url}")
                webbrowser.open(file_url)
            except Exception as browser_ex:
                print(f"[EXPORT] ⚠ Не удалось открыть браузер: {browser_ex}")
            from ui.toast import show_export_toast
            show_export_toast(page, "HTML")
        except Exception as ex:
            print(f"[EXPORT] ✕ Ошибка HTML: {ex}")
            traceback.print_exc()
            from ui.toast import show_error_toast
            show_error_toast(page, f"Ошибка экспорта HTML: {ex}")

    card_excel = _make_export_card(
        icon="📊",
        title="CSV / Excel",
        description="Открывается в Microsoft Excel, LibreOffice Calc и Google Таблицах",
        badge=excel_badge,
        on_click_handler=do_export_excel,
    )
    card_html = _make_export_card(
        icon="🖨️",
        title="HTML (печать)",
        description="Красиво оформленная таблица. Откройте в браузере и нажмите Ctrl+P",
        badge=html_badge,
        on_click_handler=do_export_html,
    )

    def close_dialog(e=None):
        print("[EXPORT_MODAL] Закрываю диалог")
        dialog.open = False
        page.update()

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text("📤", size=20),
                    ft.Text(
                        "Экспорт данных",
                        size=17,
                        weight=ft.FontWeight.BOLD,
                        color=COLORS["text_light"],
                        expand=True,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CLOSE,
                        icon_color=COLORS["text_light"],
                        icon_size=18,
                        on_click=close_dialog,
                        style=ft.ButtonStyle(padding=ft.padding.all(4)),
                    ),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            gradient=ft.LinearGradient(
                begin=ft.alignment.center_left,
                end=ft.alignment.center_right,
                colors=[COLORS["primary"], COLORS["primary_light"]],
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            border_radius=ft.border_radius.only(top_left=12, top_right=12),
            margin=ft.margin.only(top=-12, left=-24, right=-24),
        ),
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(height=6),
                    card_excel,
                    ft.Container(height=8),
                    card_html,
                    ft.Container(height=12),
                    summary_block,
                    ft.Container(height=4),
                ],
                spacing=0,
                tight=True,
            ),
            width=440,
            padding=ft.padding.symmetric(horizontal=0, vertical=0),
        ),
        actions=[
            ft.TextButton(
                text="Закрыть",
                style=ft.ButtonStyle(
                    color=COLORS["text_secondary"],
                    bgcolor=COLORS["btn_reset"],
                    shape=ft.RoundedRectangleBorder(radius=8),
                    padding=ft.padding.symmetric(horizontal=24, vertical=12),
                ),
                expand=True,
                on_click=close_dialog,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.CENTER,
        shape=ft.RoundedRectangleBorder(radius=12),
    )

    def open_dialog(update_deps: bool = True):
        """Открыть диалог с актуальной статистикой"""
        print("[EXPORT_MODAL] Открываю диалог...")
        if update_deps:
            st = get_stats()
            stat_received_text.value    = str(st["received"])
            stat_in_progress_text.value = str(st["in_progress"])
            stat_empty_text.value       = str(st["empty"])
        excel_badge.visible = False
        html_badge.visible  = False
        dialog.open = True
        page.update()
        print("[EXPORT_MODAL] Диалог открыт")

    page.open_export_modal = open_dialog
    print("[EXPORT_MODAL] Модальное окно создано, page.open_export_modal установлен")
    return dialog