# [DARK THEME] Обновлено только визуально, логика сохранена.
# ui/legend.py
# Легенда статусов: три цветных кружка с подписями
import flet as ft
from core.constants import COLORS


def create_legend() -> ft.Container:
    """
    Создать строку легенды статусов.
    Три кружка + подписи + пояснение про клик.
    """
    def legend_item(color: str, label: str, description: str) -> ft.Row:
        """Один элемент легенды: кружок + текст"""
        return ft.Row(
            controls=[
                ft.Container(
                    width=12,
                    height=12,
                    bgcolor=color,
                    border_radius=6,
                ),
                ft.Text(
                    label,
                    size=13,
                    weight=ft.FontWeight.W_600,
                    color=COLORS["text"],
                ),
                ft.Text(
                    f"— {description}",
                    size=13,
                    color=COLORS["text_secondary"],
                ),
            ],
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    legend_row = ft.Container(
        content=ft.Row(
            controls=[
                legend_item(COLORS["received"],    "Получено",    "документы поступили"),
                ft.Container(width=20),
                legend_item(COLORS["in_progress"], "В работе",   "находится на рассмотрении"),
                ft.Container(width=20),
                legend_item(COLORS["empty"],       "Не получено", ""),
                ft.Container(expand=True),
                ft.Text(
                    "Клик по статусу — переключить",
                    size=12,
                    italic=True,
                    color=COLORS["text_muted"],
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=4, vertical=8),
    )
    return legend_row