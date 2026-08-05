# [DARK THEME] Обновлено только визуально, логика сохранена.
# ui/stats_bar.py
# Панель статистики: 4 карточки (Получено, Запрошено, Не получено, Прогресс)
import flet as ft
from typing import List
from core.models import Department, Status
from core.constants import COLORS


def _count_stats(departments: List[Department], active_only: bool = True) -> dict:
    """Посчитать статистику по активным отделам."""
    active = [d for d in departments if d.is_active] if active_only else list(departments)
    received    = sum(1 for d in active if d.status == Status.RECEIVED)
    in_progress = sum(1 for d in active if d.status == Status.IN_PROGRESS)
    empty       = sum(1 for d in active if d.status == Status.EMPTY)
    total       = len(active)
    percent     = round(received / total * 100) if total > 0 else 0
    return dict(received=received, in_progress=in_progress,
                empty=empty, total=total, percent=percent)


def _stat_card(
    icon: str,
    icon_bg: str,
    value_text: ft.Control,
    label: str,
    card_bg: str,
    border_color: str,
    expand: int = 1,
) -> ft.Container:
    """Универсальная карточка статистики."""
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Icon(icon, size=18, color=COLORS["text_light"]),
                    width=40,
                    height=40,
                    bgcolor=icon_bg,
                    border_radius=20,
                    alignment=ft.alignment.center,
                ),
                ft.Column(
                    controls=[
                        value_text,
                        ft.Text(label, size=12, color=COLORS["text_secondary"]),
                    ],
                    spacing=2,
                    tight=True,
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=card_bg,
        border=ft.border.all(1.5, border_color),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=18, vertical=14),
        expand=expand,
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=8,
            color="#40000000",
            offset=ft.Offset(0, 2),
        ),
    )


def create_stats_bar(page: ft.Page, departments: List[Department]) -> ft.Row:
    """
    Создать строку из 4 карточек статистики.
    Сохраняет ссылки в page для обновления.
    """
    stats = _count_stats(departments)

    # ── Карточка 1: Получено
    received_text = ft.Text(
        str(stats["received"]),
        size=28,
        weight=ft.FontWeight.BOLD,
        color=COLORS["received_text"],
    )
    page.stats_received_text = received_text
    card_received = _stat_card(
        icon=ft.icons.CHECK,
        icon_bg=COLORS["received"],
        value_text=received_text,
        label="Получено",
        card_bg=COLORS["stat_received_bg"],
        border_color=COLORS["stat_received_border"],
    )

    # ── Карточка 2: Запрошено
    in_progress_text = ft.Text(
        str(stats["in_progress"]),
        size=28,
        weight=ft.FontWeight.BOLD,
        color=COLORS["in_progress_text"],
    )
    page.stats_in_progress_text = in_progress_text
    card_in_progress = _stat_card(
        icon=ft.icons.REFRESH,
        icon_bg=COLORS["in_progress"],
        value_text=in_progress_text,
        label="Запрошено",
        card_bg=COLORS["stat_progress_bg"],
        border_color=COLORS["stat_progress_border"],
    )

    # ── Карточка 3: Не получено
    empty_text = ft.Text(
        str(stats["empty"]),
        size=28,
        weight=ft.FontWeight.BOLD,
        color=COLORS["text_secondary"],
    )
    page.stats_empty_text = empty_text
    card_empty = _stat_card(
        icon=ft.icons.RADIO_BUTTON_UNCHECKED,
        icon_bg=COLORS["empty"],
        value_text=empty_text,
        label="Не получено",
        card_bg=COLORS["stat_empty_bg"],
        border_color=COLORS["stat_empty_border"],
    )

    # ── Карточка 4: Прогресс
    percent_text = ft.Text(
        f"{stats['percent']}%",
        size=28,
        weight=ft.FontWeight.BOLD,
        color=COLORS["stat_blue_text"],
    )
    page.stats_percent_text = percent_text

    progress_bar = ft.ProgressBar(
        value=stats["percent"] / 100,
        bgcolor=COLORS["primary_light"],
        color=COLORS["btn_save"],
        border_radius=4,
        height=6,
    )
    page.stats_progress_bar = progress_bar

    progress_label = ft.Text(
        f"{stats['received']} из {stats['total']}",
        size=12,
        color=COLORS["text_secondary"],
    )
    page.stats_progress_label = progress_label

    card_progress = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Icon(ft.icons.INSIGHTS, size=16, color=COLORS["text_light"]),
                            width=40,
                            height=40,
                            bgcolor=COLORS["btn_save"],
                            border_radius=20,
                            alignment=ft.alignment.center,
                        ),
                        ft.Column(
                            controls=[
                                percent_text,
                                progress_label,
                            ],
                            spacing=2,
                            tight=True,
                        ),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=4),
                progress_bar,
            ],
            spacing=0,
        ),
        bgcolor=COLORS["stat_blue_bg"],
        border=ft.border.all(1.5, COLORS["stat_blue_border"]),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=18, vertical=14),
        expand=1,
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=8,
            color="#40000000",
            offset=ft.Offset(0, 2),
        ),
    )

    stats_row = ft.Row(
        controls=[card_received, card_in_progress, card_empty, card_progress],
        spacing=14,
        expand=False,
    )
    return stats_row


def update_stats_bar(page: ft.Page, departments: List[Department]) -> None:
    """
    Обновить значения в карточках статистики.
    Вызывать после каждого изменения статуса.
    """
    stats = _count_stats(departments)

    if hasattr(page, "stats_received_text"):
        page.stats_received_text.value = str(stats["received"])
        page.stats_received_text.update()

    if hasattr(page, "stats_in_progress_text"):
        page.stats_in_progress_text.value = str(stats["in_progress"])
        page.stats_in_progress_text.update()

    if hasattr(page, "stats_empty_text"):
        page.stats_empty_text.value = str(stats["empty"])
        page.stats_empty_text.update()

    if hasattr(page, "stats_percent_text"):
        page.stats_percent_text.value = f"{stats['percent']}%"
        page.stats_percent_text.update()

    if hasattr(page, "stats_progress_bar"):
        page.stats_progress_bar.value = stats["percent"] / 100
        page.stats_progress_bar.update()

    if hasattr(page, "stats_progress_label"):
        page.stats_progress_label.value = f"{stats['received']} из {stats['total']}"
        page.stats_progress_label.update()