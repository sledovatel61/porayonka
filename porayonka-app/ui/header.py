# [DARK THEME] Обновлено только визуально, логика сохранена.
# ui/header.py
# Шапка приложения: логотип, заголовок, дата последнего сохранения
import flet as ft
from datetime import datetime
from typing import Optional
from core.constants import COLORS, APP_TITLE, APP_SUBTITLE


def create_header(page: ft.Page, last_save: Optional[datetime]) -> ft.Container:
    """
    Создать шапку приложения.
    :param page: объект страницы Flet
    :param last_save: дата/время последнего сохранения (None если нет)
    :return: контейнер с шапкой
    """
    def format_save_date(dt: Optional[datetime]) -> str:
        if dt is None:
            return "Ещё не сохранено"
        return dt.strftime("%d.%m.%Y, %H:%M:%S")

    save_text = ft.Text(
        value=format_save_date(last_save),
        size=13,
        color=COLORS["text_secondary"],
        weight=ft.FontWeight.W_500,
    )

    page.save_date_text = save_text

    left_block = ft.Row(
        controls=[
            ft.Container(
                content=ft.Text("🏛", size=28),
                width=52,
                height=52,
                bgcolor="#ffffff15",
                border_radius=12,
                alignment=ft.alignment.center,
            ),
            ft.Column(
                controls=[
                    ft.Text(
                        APP_TITLE,
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        color=COLORS["text_light"],
                    ),
                    ft.Text(
                        APP_SUBTITLE,
                        size=12,
                        color=COLORS["text_secondary"],
                    ),
                ],
                spacing=2,
            ),
        ],
        spacing=14,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    right_block = ft.Column(
        controls=[
            ft.Text(
                "Последнее сохранение",
                size=11,
                color=COLORS["text_muted"],
            ),
            save_text,
        ],
        spacing=3,
        horizontal_alignment=ft.CrossAxisAlignment.END,
    )

    header = ft.Container(
        content=ft.Row(
            controls=[left_block, right_block],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=24, vertical=16),
        gradient=ft.LinearGradient(
            begin=ft.alignment.center_left,
            end=ft.alignment.center_right,
            colors=[COLORS["primary"], COLORS["primary_dark"]],
        ),
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=16,
            color="#00000060",
            offset=ft.Offset(0, 4),
        ),
    )
    return header


def update_header_save_date(page: ft.Page, dt: Optional[datetime] = None) -> None:
    """
    Обновить дату сохранения в шапке.
    Вызывается после каждого сохранения.
    """
    if not hasattr(page, "save_date_text"):
        return
    now = dt or datetime.now()
    page.save_date_text.value = now.strftime("%d.%m.%Y, %H:%M:%S")
    page.save_date_text.update()