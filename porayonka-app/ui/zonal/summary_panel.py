# ui/zonal/summary_panel.py
# Компактная панель общей сводки (Фаза 2).
# Считает только активных криминалистов.
# [DARK THEME] + ft.icons.* (Flet 0.23.2)
import flet as ft
from typing import Callable, Optional, Dict
from core.zonal_data import get_fill_summary
from core.constants import COLORS


def _stat(icon, label: str, value: str, value_color: str) -> ft.Container:
    """Один блок статистики: иконка + значение + подпись."""
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(icon, size=16, color=COLORS["text_secondary"]),
                        ft.Text(value, size=20, weight=ft.FontWeight.BOLD, color=value_color),
                    ],
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Text(label, size=11, color=COLORS["text_secondary"]),
            ],
            spacing=2,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        ),
        padding=ft.padding.symmetric(horizontal=14, vertical=8),
        bgcolor=COLORS["card"],
        border=ft.border.all(1, COLORS["border"]),
        border_radius=10,
    )


def create_summary_panel(
    collection,
    summary_ref: Optional[Dict] = None,
    on_toggle: Optional[Callable] = None,
) -> ft.Column:
    """
    Создать панель общей сводки.
    Возвращает ft.Column (контракт обновления controls в zonal_tab).
    Учитываются ТОЛЬКО активные криминалисты.
    """
    is_expanded = False
    if summary_ref is not None:
        is_expanded = summary_ref.get("is_expanded", False)

    print(f"[SUMMARY] Creating summary panel: expanded={is_expanded}")
    s = get_fill_summary(collection)
    overall = s["overall_percent"]
    active = s["active"]
    inactive = s["inactive"]
    submitted = s["items_submitted"]

    if overall >= 100:
        bar_color = COLORS["received"]
    elif overall > 0:
        bar_color = COLORS["in_progress"]
    else:
        bar_color = COLORS["empty"]

    # Бейдж активности (с учётом отключённых)
    badge_text = f"Активные: {active}"
    if inactive > 0:
        badge_text += f"  (откл.: {inactive})"

    def _toggle(e):
        if summary_ref is not None:
            summary_ref["is_expanded"] = not summary_ref.get("is_expanded", False)
        if on_toggle is not None:
            on_toggle()

    if not is_expanded:
        # ── СВЁРНУТЫЙ ВИД: одна компактная строка ──
        progress_bar = ft.ProgressBar(
            value=overall / 100.0,
            height=8,
            color=bar_color,
            bgcolor=COLORS["border"],
            border_radius=4,
            width=150,
        )

        collapsed_row = ft.Row(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.icons.INSIGHTS, size=18, color="white"),
                        ft.Text("Сводка", size=13, weight=ft.FontWeight.BOLD, color="white"),
                    ],
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.VerticalDivider(width=1, color=COLORS["border"]),
                ft.Row(
                    controls=[
                        ft.Icon(ft.icons.GROUPS, size=14, color=COLORS["received_text"]),
                        ft.Text(f"Активно: {active}", size=12, color=COLORS["text"],
                                weight=ft.FontWeight.W_500),
                    ],
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    controls=[
                        ft.Icon(ft.icons.CHECK_CIRCLE, size=14, color=COLORS["stat_blue_text"]),
                        ft.Text(f"Сдано: {submitted}", size=12, color=COLORS["text"],
                                weight=ft.FontWeight.W_500),
                    ],
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    controls=[
                        ft.Text(f"Прогресс: {overall}%", size=12, color=COLORS["text"],
                                weight=ft.FontWeight.W_500),
                        progress_bar,
                    ],
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(expand=True),
                ft.Icon(
                    ft.icons.KEYBOARD_ARROW_DOWN,
                    size=18,
                    color="white",
                ),
            ],
            spacing=16,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        card = ft.Container(
            content=collapsed_row,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            gradient=ft.LinearGradient(
                begin=ft.alignment.center_left,
                end=ft.alignment.center_right,
                colors=[COLORS["primary"], COLORS["primary_light"]],
            ),
            border=ft.border.all(1, COLORS["border"]),
            border_radius=10,
            ink=True,
            on_click=_toggle,
            tooltip="Нажмите, чтобы развернуть общую сводку",
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=6,
                color="#40000000",
                offset=ft.Offset(0, 1),
            ),
        )

        print(f"[SUMMARY] Summary collapsed: active={active}, submitted={submitted}, overall={overall}%")
        return ft.Column(controls=[card], spacing=0)

    # ── РАЗВЁРНУТЫЙ ВИД: полная панель со статистикой ──
    progress_area = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("Общий прогресс", size=12, color=COLORS["text_secondary"]),
                        ft.Text(f"{overall}%", size=14, weight=ft.FontWeight.BOLD,
                                color=COLORS["text"]),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.ProgressBar(
                    value=overall / 100.0,
                    height=10,
                    color=bar_color,
                    bgcolor=COLORS["border"],
                    border_radius=5,
                ),
            ],
            spacing=6,
        ),
        padding=ft.padding.symmetric(horizontal=14, vertical=8),
        bgcolor=COLORS["card"],
        border=ft.border.all(1, COLORS["border"]),
        border_radius=10,
    )

    header = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.icons.INSIGHTS, size=18, color="white"),
                ft.Text("Общая сводка", size=14, weight=ft.FontWeight.BOLD, color="white"),
                ft.Container(expand=True),
                ft.Container(
                    content=ft.Text(badge_text, size=11, color="white"),
                    bgcolor=COLORS["btn_save"],
                    border_radius=8,
                    padding=ft.padding.symmetric(horizontal=8, vertical=3),
                ),
                ft.Icon(ft.icons.KEYBOARD_ARROW_UP, size=18, color="white"),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        gradient=ft.LinearGradient(
            begin=ft.alignment.center_left,
            end=ft.alignment.center_right,
            colors=[COLORS["primary"], COLORS["primary_light"]],
        ),
        padding=ft.padding.symmetric(horizontal=14, vertical=8),
        border_radius=ft.border_radius.only(top_left=10, top_right=10),
        ink=True,
        on_click=_toggle,
        tooltip="Нажмите, чтобы свернуть общую сводку",
    )

    body = ft.Container(
        content=ft.ResponsiveRow(
            columns=12,
            spacing=10,
            run_spacing=10,
            controls=[
                ft.Container(col={"sm": 6, "md": 3, "lg": 3}, content=_stat(
                    ft.icons.GROUPS, "Активных криминалистов", str(active), COLORS["received_text"])),
                ft.Container(col={"sm": 6, "md": 3, "lg": 3}, content=_stat(
                    ft.icons.CHECK_CIRCLE, "Сдано пунктов", str(submitted), COLORS["stat_blue_text"])),
                ft.Container(col={"sm": 12, "md": 6, "lg": 6}, content=progress_area),
            ],
        ),
        padding=ft.padding.all(10),
        bgcolor=COLORS["card"],
        border=ft.border.all(1, COLORS["border"]),
        border_radius=ft.border_radius.only(bottom_left=10, bottom_right=10),
    )

    card = ft.Container(
        content=ft.Column(controls=[header, body], spacing=0),
        border=ft.border.all(1, COLORS["border"]),
        border_radius=10,
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=8,
            color="#60000000",
            offset=ft.Offset(0, 2),
        ),
    )

    print(f"[SUMMARY] Summary expanded: active={active}, submitted={submitted}, overall={overall}%")
    return ft.Column(controls=[card], spacing=0)
