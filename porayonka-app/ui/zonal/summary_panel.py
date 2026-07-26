# ui/zonal/summary_panel.py
# Панель общей сводки (редизайн, фаза 3).
#
# Две формы подачи:
#   create_summary_line(collection)  — однострочная сводка для основного экрана
#                                      (активных / сдано / общий прогресс).
#   create_summary_panel(collection) — подробная сводка, показывается
#                                      в раскрывающемся блоке «Подробная сводка».
#
# LAYOUT: без expand=True в вертикальном направлении, без ResponsiveRow.
# Всё построено на Row с фиксированными размерами — панель живёт внутри
# прокручиваемой колонки вкладки (Flet 0.23.2).
# [DARK THEME] + ft.icons.* (Flet 0.23.2)
import flet as ft
from core.zonal_data import get_fill_summary
from core.constants import COLORS


def _bar_color(percent: int) -> str:
    if percent >= 100:
        return COLORS["received"]
    if percent > 0:
        return COLORS["in_progress"]
    return COLORS["empty"]


def _chip(icon, text: str, color: str, tooltip: str = None) -> ft.Container:
    """Компактный чип «иконка + текст» для однострочной сводки."""
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(icon, size=15, color=color),
                ft.Text(text, size=12, weight=ft.FontWeight.W_600, color=color),
            ],
            spacing=6,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(horizontal=10, vertical=5),
        bgcolor=COLORS["empty_bg"],
        border=ft.border.all(1, COLORS["border"]),
        border_radius=8,
        tooltip=tooltip,
    )


def create_summary_line(collection) -> ft.Row:
    """
    Однострочная сводка для основного экрана вкладки:
    активных / сдано пунктов / общий прогресс.
    Возвращает ft.Row (контракт обновления controls в zonal_tab).
    """
    s = get_fill_summary(collection)
    overall = s["overall_percent"]
    active = s["active"]
    inactive = s["inactive"]
    submitted = s["items_submitted"]

    active_text = f"Активных: {active}"
    if inactive:
        active_text += f" (откл. {inactive})"

    controls = [
        _chip(ft.icons.GROUPS, active_text, COLORS["received_text"],
              tooltip="Криминалистов, участвующих в сборе данных"),
        _chip(ft.icons.CHECK_CIRCLE, f"Сдано пунктов: {submitted}", COLORS["stat_blue_text"],
              tooltip="Всего заполненных пунктов по активным криминалистам"),
        ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.icons.INSIGHTS, size=15, color=COLORS["text_secondary"]),
                    ft.Text("Общий прогресс:", size=12, color=COLORS["text_secondary"]),
                    ft.ProgressBar(
                        value=overall / 100.0,
                        width=140,
                        height=8,
                        color=_bar_color(overall),
                        bgcolor=COLORS["border"],
                        border_radius=4,
                    ),
                    ft.Text(f"{overall}%", size=12, weight=ft.FontWeight.BOLD,
                            color=COLORS["text"]),
                ],
                spacing=8,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(horizontal=10, vertical=5),
            bgcolor=COLORS["empty_bg"],
            border=ft.border.all(1, COLORS["border"]),
            border_radius=8,
        ),
    ]

    return ft.Row(
        controls=controls,
        spacing=10,
        wrap=True,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _detail_row(label: str, value: str, value_color: str) -> ft.Row:
    """Строка подробной сводки: подпись слева, значение справа."""
    return ft.Row(
        controls=[
            ft.Text(label, size=12, color=COLORS["text_secondary"], width=260,
                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            ft.Text(value, size=13, weight=ft.FontWeight.BOLD, color=value_color),
        ],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def create_summary_panel(collection) -> ft.Column:
    """
    Подробная сводка (для раскрывающегося блока «Подробная сводка»).
    Возвращает ft.Column (контракт обновления controls в zonal_tab).
    Учитываются ТОЛЬКО активные криминалисты.
    """
    s = get_fill_summary(collection)
    overall = s["overall_percent"]
    active = s["active"]
    inactive = s["inactive"]
    submitted = s["items_submitted"]
    total = s["total_criminalists"]
    template_items = len(collection.template.items)

    # Разбивка по состоянию заполнения (только активные)
    from core.zonal_data import get_criminalist_fill
    done = 0
    partial = 0
    empty = 0
    for c in collection.criminalists:
        if not c.is_active:
            continue
        pct = get_criminalist_fill(collection, c)["percent"]
        if pct >= 100:
            done += 1
        elif pct > 0:
            partial += 1
        else:
            empty += 1

    rows = [
        _detail_row("Всего криминалистов в списке", str(total), COLORS["text"]),
        _detail_row("Участвуют в сборе", str(active), COLORS["received_text"]),
        _detail_row("Отключены от сбора", str(inactive), COLORS["text_muted"]),
        ft.Divider(height=12, color=COLORS["border"]),
        _detail_row("Пунктов в текущей форме", str(template_items), COLORS["text"]),
        _detail_row("Сдано пунктов (всего)", str(submitted), COLORS["stat_blue_text"]),
        ft.Divider(height=12, color=COLORS["border"]),
        _detail_row("Заполнили форму полностью", str(done), COLORS["received_text"]),
        _detail_row("Заполнили частично", str(partial), COLORS["in_progress_text"]),
        _detail_row("Не приступали", str(empty), COLORS["text_muted"]),
        ft.Divider(height=12, color=COLORS["border"]),
        ft.Row(
            controls=[
                ft.Text("Общий прогресс", size=12, color=COLORS["text_secondary"], width=260),
                ft.ProgressBar(
                    value=overall / 100.0,
                    width=200,
                    height=10,
                    color=_bar_color(overall),
                    bgcolor=COLORS["border"],
                    border_radius=5,
                ),
                ft.Text(f"{overall}%", size=13, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    ]

    body = ft.Container(
        content=ft.Column(controls=rows, spacing=6, tight=True),
        padding=ft.padding.all(14),
        bgcolor=COLORS["card"],
        border=ft.border.all(1, COLORS["border"]),
        border_radius=10,
    )

    return ft.Column(controls=[body], spacing=0, tight=True)
