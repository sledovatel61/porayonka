# [DARK THEME] Обновлено только визуально, логика сохранена.
# ui/zonal/summary_panel.py
import flet as ft
from core.zonal_models import ZonalCollection, ReportItemType
from core.zonal_data import get_summary
from core.constants import COLORS, INITIAL_DEPARTMENTS


def create_summary_panel(collection: ZonalCollection) -> ft.Column:
    """
    Создать панель общей сводки.
    Показывает итоги по пунктам + детализацию по активным криминалистам.
    Неактивные исключаются из подсчёта.
    """
    print("[SUMMARY] Создаю сводку")
    print(f"[SUMMARY] Режим по отделам: {collection.template.use_departments_mode}")
    controls      = []
    use_dept_mode = collection.template.use_departments_mode
    
    # Фильтруем только активных криминалистов
    active_criminalists = [c for c in collection.criminalists if c.is_active]
    inactive_count = len(collection.criminalists) - len(active_criminalists)

    header = ft.Container(
        content=ft.Row(
            controls=[
                ft.Text("📈", size=18),
                ft.Text(
                    "Общая сводка",
                    size=15,
                    weight=ft.FontWeight.BOLD,
                    color=COLORS["text_light"],
                ),
                # Бейдж с информацией о неактивных
                ft.Container(
                    content=ft.Text(
                        f"👁 {len(active_criminalists)}",
                        size=12,
                        color=COLORS["text_light"],
                        weight=ft.FontWeight.W_500,
                    ),
                    bgcolor=COLORS["btn_save"],
                    border_radius=8,
                    padding=ft.padding.symmetric(horizontal=8, vertical=3),
                    visible=inactive_count > 0,
                ),
            ],
            spacing=8,
        ),
        gradient=ft.LinearGradient(
            begin=ft.alignment.center_left,
            end=ft.alignment.center_right,
            colors=[COLORS["primary"], COLORS["primary_light"]],
        ),
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        border_radius=ft.border_radius.only(top_left=10, top_right=10),
    )
    controls.append(header)

    if not collection.template.items:
        controls.append(
            ft.Container(
                content=ft.Text(
                    "Добавьте пункты в конструкторе шаблонов",
                    size=13,
                    color=COLORS["text_muted"],
                    italic=True,
                    text_align=ft.TextAlign.CENTER,
                ),
                alignment=ft.alignment.center,
                padding=ft.padding.all(20),
                bgcolor=COLORS["card"],
                border_radius=ft.border_radius.only(bottom_left=10, bottom_right=10),
            )
        )
    else:
        summary_data  = get_summary(collection)
        body_controls = []

        for item_id, data in summary_data.items():
            item       = data["item"]
            total_crim = data["total_criminalists"]

            if item.item_type == ReportItemType.NUMERICAL:
                val_text    = str(data["total_value"])
                unit_str    = f" {item.unit}" if item.unit else ""
                detail_text = f"({data['filled_count']} из {total_crim} заполнили)"
                icon        = "📊"
                value_color = COLORS["stat_blue_text"]
            else:
                val_text    = f"{data['submitted_count']}/{total_crim}"
                pct         = round(data['submitted_count'] / max(total_crim, 1) * 100)
                detail_text = f"({pct}%)"
                unit_str    = ""
                icon        = "✅"
                value_color = COLORS["received_text"] if pct >= 80 else COLORS["in_progress_text"]

            item_header = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Text(icon, size=14),
                        ft.Text(item.name, size=13, weight=ft.FontWeight.W_600,
                                color=COLORS["text"], expand=True),
                        ft.Text(f"{val_text}{unit_str}", size=16,
                                weight=ft.FontWeight.BOLD, color=value_color),
                        ft.Text(detail_text, size=11, color=COLORS["text_secondary"]),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.padding.symmetric(horizontal=16, vertical=10),
                bgcolor=COLORS["primary_light"],
                border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"])),
            )
            body_controls.append(item_header)

            for crim in active_criminalists:  # Только активные
                rd = None
                for sub in collection.submissions:
                    if sub.criminalist_id == crim.id and sub.template_item_id == item.id:
                        rd = sub
                        break

                if use_dept_mode and crim.zone.department_ids:
                    crim_header = ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Text("👤", size=12),
                                ft.Text(crim.full_name, size=12,
                                        weight=ft.FontWeight.W_600, color=COLORS["text"],
                                        expand=True),
                            ],
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=ft.padding.symmetric(horizontal=16, vertical=6),
                        bgcolor=COLORS["card"],
                        border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"])),
                    )
                    body_controls.append(crim_header)

                    dept_map = {d["id"]: d["name"] for d in INITIAL_DEPARTMENTS}
                    if item.item_type == ReportItemType.NUMERICAL:
                        for dept_id in crim.zone.department_ids:
                            dept_name = dept_map.get(dept_id, f"Отдел {dept_id}")
                            dept_val  = rd.department_values.get(dept_id) if rd else None
                            crim_row  = ft.Container(
                                content=ft.Row(
                                    controls=[
                                        ft.Container(width=32),
                                        ft.Text(dept_name, size=11, color=COLORS["text"], expand=True),
                                        ft.Text(
                                            f"{dept_val if dept_val is not None else '—'}"
                                            f"{(' ' + item.unit) if dept_val is not None else ''}",
                                            size=11,
                                            color=COLORS["stat_blue_text"] if dept_val is not None else COLORS["text_muted"],
                                            weight=ft.FontWeight.BOLD if dept_val is not None else ft.FontWeight.NORMAL,
                                        ),
                                    ],
                                    spacing=8,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                padding=ft.padding.symmetric(horizontal=16, vertical=4),
                                bgcolor=COLORS["card"],
                                border=ft.border.only(bottom=ft.BorderSide(1, COLORS["divider"])),
                            )
                            body_controls.append(crim_row)
                    else:
                        for dept_id in crim.zone.department_ids:
                            dept_name    = dept_map.get(dept_id, f"Отдел {dept_id}")
                            is_submitted = rd.department_submitted.get(dept_id, False) if rd else False
                            crim_row     = ft.Container(
                                content=ft.Row(
                                    controls=[
                                        ft.Container(width=32),
                                        ft.Text(dept_name, size=11, color=COLORS["text"], expand=True),
                                        ft.Text(
                                            "✓ Сдано" if is_submitted else "✗ Не сдано",
                                            size=11,
                                            color=COLORS["received_text"] if is_submitted else COLORS["empty"],
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                    ],
                                    spacing=8,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                padding=ft.padding.symmetric(horizontal=16, vertical=4),
                                bgcolor=COLORS["card"],
                                border=ft.border.only(bottom=ft.BorderSide(1, COLORS["divider"])),
                            )
                            body_controls.append(crim_row)
                else:
                    if item.item_type == ReportItemType.NUMERICAL:
                        if rd is not None and rd.value is not None:
                            crim_val   = f"{rd.value}{' ' + item.unit if item.unit else ''}"
                            val_color  = COLORS["stat_blue_text"]
                            val_weight = ft.FontWeight.BOLD
                        else:
                            crim_val   = "—"
                            val_color  = COLORS["text_muted"]
                            val_weight = ft.FontWeight.NORMAL
                    else:
                        if rd is not None and rd.is_submitted:
                            crim_val   = "✓ Сдано"
                            val_color  = COLORS["received_text"]
                            val_weight = ft.FontWeight.BOLD
                        else:
                            crim_val   = "✗ Не сдано"
                            val_color  = COLORS["empty"]
                            val_weight = ft.FontWeight.NORMAL

                    crim_row = ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Container(width=16),
                                ft.Text("👤", size=11),
                                ft.Text(crim.full_name, size=12, color=COLORS["text"], expand=True),
                                ft.Text(crim_val, size=12, color=val_color, weight=val_weight),
                            ],
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=ft.padding.symmetric(horizontal=16, vertical=5),
                        bgcolor=COLORS["card"],
                        border=ft.border.only(bottom=ft.BorderSide(1, COLORS["divider"])),
                    )
                    body_controls.append(crim_row)

            body_controls.append(ft.Container(height=4, bgcolor=COLORS["border"]))

        body = ft.Container(
            content=ft.Column(controls=body_controls, spacing=0),
            bgcolor=COLORS["card"],
            border_radius=ft.border_radius.only(bottom_left=10, bottom_right=10),
        )
        controls.append(body)

    result = ft.Column(
        controls=[
            ft.Container(
                content=ft.Column(controls=controls, spacing=0),
                border=ft.border.all(1, COLORS["border"]),
                border_radius=10,
                shadow=ft.BoxShadow(
                    spread_radius=0,
                    blur_radius=8,
                    color="#00000060",
                    offset=ft.Offset(0, 2),
                ),
            )
        ],
        spacing=0,
    )

    print(f"[SUMMARY] Сводка создана, пунктов: {len(collection.template.items)}")
    return result