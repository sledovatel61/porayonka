# [DARK THEME] Обновлено только визуально, логика сохранена.
# assets/styles.py
# Глобальные стили и тема приложения
import flet as ft
from core.constants import COLORS


def get_app_theme() -> ft.Theme:
    """
    Вернуть объект темы Flet для тёмного режима.
    Задаёт шрифты, цвета акцента, стили кнопок.
    """
    return ft.Theme(
        color_scheme_seed=COLORS["btn_save"],
        color_scheme=ft.ColorScheme(
            primary=COLORS["btn_save"],
            secondary=COLORS["btn_export"],
            background=COLORS["bg"],
            surface=COLORS["card"],
            on_primary=COLORS["text_light"],
            on_secondary=COLORS["text_light"],
        ),
        font_family="Segoe UI",
        visual_density=ft.ThemeVisualDensity.COMFORTABLE,
        use_material3=True,
    )


def get_scrollbar_theme() -> ft.ScrollbarTheme:
    """Тема полосы прокрутки"""
    return ft.ScrollbarTheme(
        thickness=6,
        radius=3,
        thumb_color={
            ft.ControlState.DEFAULT:  COLORS["border"],
            ft.ControlState.HOVERED:  COLORS["text_muted"],
            ft.ControlState.DRAGGED:  COLORS["btn_save"],
        },
    )