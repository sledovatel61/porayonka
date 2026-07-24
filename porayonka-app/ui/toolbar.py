# ui/toolbar.py
# Панель управления: поле поиска + кнопки (Сохранить, Экспорт, Сброс)
# ИСПРАВЛЕНО: заменен hint_text_color на hint_style
import flet as ft
from core.constants import COLORS

def create_toolbar(
    page: ft.Page,
    on_search: callable,
    on_save: callable,
    on_export: callable,
    on_reset: callable,
) -> ft.Container:
    """
    Создать панель управления.
    """
    # ── Поле поиска ──────────────────────────────────────────
    search_field = ft.TextField(
        hint_text=" Поиск по отделам...",
        prefix_icon=ft.icons.SEARCH,
        border_radius=10,
        border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        # [FIX] Используем hint_style вместо hint_text_color
        hint_style=ft.TextStyle(color=COLORS["text_muted"]),
        # [DARK] Темный фон поля ввода
        bgcolor=COLORS["card"],
        # [DARK] Цвет вводимого текста
        color=COLORS["text"],
        height=44,
        text_size=14,
        cursor_color=COLORS["btn_save"],
        content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
        expand=True,
    )
    page.search_field = search_field

    def on_search_change(e: ft.ControlEvent):
        query = search_field.value or ""
        # Показать/скрыть кнопку очистки
        clear_btn.visible = len(query) > 0
        clear_btn.update()
        on_search(query)

    def on_clear_click(e: ft.ControlEvent):
        search_field.value = ""
        search_field.update()
        clear_btn.visible = False
        clear_btn.update()
        on_search("")

    search_field.on_change = on_search_change

    # Кнопка очистки поиска
    clear_btn = ft.IconButton(
        icon=ft.icons.CLOSE,
        icon_size=18,
        icon_color=COLORS["text_secondary"],
        tooltip="Очистить поиск",
        visible=False,
        on_click=on_clear_click,
        style=ft.ButtonStyle(
            padding=ft.padding.all(6),
        ),
    )

    search_row = ft.Row(
        controls=[search_field, clear_btn],
        spacing=4,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        expand=True,
    )

    # ── Кнопка «Сохранить» ───────────────────────────────────
    btn_save = ft.ElevatedButton(
        text="Сохранить",
        icon=ft.icons.SAVE_OUTLINED,
        bgcolor=COLORS["btn_save"],
        color="white",
        elevation=2,
        height=44,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.padding.symmetric(horizontal=18),
        ),
        on_click=lambda e: on_save(),
        tooltip="Сохранить данные вручную",
    )

    # ── Кнопка «Экспорт» ─────────────────────────────────────
    btn_export = ft.ElevatedButton(
        text="Экспорт",
        icon=ft.icons.UPLOAD_FILE_OUTLINED,
        bgcolor=COLORS["btn_export"],
        color="white",
        elevation=2,
        height=44,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.padding.symmetric(horizontal=18),
        ),
        on_click=lambda e: on_export(),
        tooltip="Экспорт в Excel или HTML",
    )

    # ── Кнопка «Сброс» (маленькая, только иконка) ────────────
    btn_reset = ft.IconButton(
        icon=ft.icons.RESTART_ALT_OUTLINED,
        icon_color=COLORS["text_secondary"],
        icon_size=22,
        tooltip="Сбросить все статусы",
        on_click=lambda e: on_reset(),
        style=ft.ButtonStyle(
            bgcolor=COLORS["btn_reset"],
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.padding.all(10),
        ),
    )

    # ── Сборка тулбара ────────────────────────────────────────
    toolbar = ft.Container(
        content=ft.Row(
            controls=[
                search_row,
                ft.Container(width=12),
                btn_save,
                ft.Container(width=8),
                btn_export,
                ft.Container(width=8),
                btn_reset,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
        ),
        padding=ft.padding.symmetric(horizontal=2, vertical=0),
    )

    return toolbar