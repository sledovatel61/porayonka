# [DARK THEME] Обновлено только визуально, логика сохранена.
# ui/toast.py
import flet as ft
from core.constants import COLORS


def show_toast(
    page: ft.Page,
    message: str = "Данные сохранены",
    icon: str = ft.icons.CHECK_CIRCLE,
    duration_ms: int = 2500,
    is_error: bool = False,
) -> None:
    """
    Показать всплывающее уведомление (SnackBar) внизу экрана.
    :param page: объект страницы Flet
    :param message: текст уведомления
    :param icon: иконка перед текстом
    :param duration_ms: длительность показа в мс
    :param is_error: True → красный фон, False → тёмный фон
    """
    bg_color   = "#dc2626" if is_error else COLORS["toast_bg"]
    icon_color = "#f87171" if is_error else COLORS["received"]

    snack = ft.SnackBar(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Text(
                        icon,
                        size=16,
                        color=icon_color,
                        weight=ft.FontWeight.BOLD,
                    ),
                    width=28,
                    height=28,
                    bgcolor=f"{icon_color}25",
                    border_radius=14,
                    alignment=ft.alignment.center,
                ),
                ft.Text(
                    message,
                    size=14,
                    color=COLORS["text_light"],
                    weight=ft.FontWeight.W_500,
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=bg_color,
        duration=duration_ms,
        show_close_icon=False,
        behavior=ft.SnackBarBehavior.FLOATING,
        shape=ft.RoundedRectangleBorder(radius=10),
        margin=ft.margin.only(right=20, bottom=20, left=20),
        elevation=8,
    )
    page.snack_bar      = snack
    page.snack_bar.open = True
    page.update()


def show_save_toast(page: ft.Page) -> None:
    """Быстрый вызов уведомления о сохранении"""
    show_toast(page, "Данные сохранены", icon=ft.icons.CHECK_CIRCLE)


def show_reset_toast(page: ft.Page) -> None:
    """Уведомление о сбросе"""
    show_toast(page, "Все статусы сброшены", icon=ft.icons.REFRESH)


def show_export_toast(page: ft.Page, format_name: str) -> None:
    """Уведомление об экспорте"""
    show_toast(page, f"Файл {format_name} скачан", icon=ft.icons.FOLDER)


def show_error_toast(page: ft.Page, message: str) -> None:
    """Уведомление об ошибке"""
    show_toast(page, message, icon=ft.icons.CLOSE, is_error=True)