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
                bgcolor="#15ffffff",
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
            color="#60000000",
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

# ────────────────────────────────────────────────────────────────
# КОМПАКТНАЯ ШАПКА (редизайн v4)
# Без иконки и названия приложения (они дублируют заголовок окна).
# Слева — переключатель вкладок, справа — дата последнего сохранения.
# ────────────────────────────────────────────────────────────────

def create_compact_header(
    page: ft.Page,
    last_save: Optional[datetime],
    tabs_control: ft.Control,
    form_settings_visible: bool = False,
) -> ft.Container:
    """
    Компактная шапка приложения (высота ~48 px вместо ~130 px).
    Слева — переключатель вкладок, справа — кнопки + дата последнего сохранения.
    Раунд 26 (задача 6): «Настройка формы» относится только к вкладке
    «Зональные» — начальная видимость передаётся параметром, дальше ею
    управляет _switch_tab через page._btn_form_settings.
    """
    save_text = ft.Text(
        value=(last_save.strftime("%d.%m.%Y, %H:%M:%S")
               if last_save is not None else "Ещё не сохранено"),
        size=11,
        color=COLORS["text_secondary"],
        weight=ft.FontWeight.W_500,
        no_wrap=True,
    )
    page.save_date_text = save_text

    # ── Модалка «О программе» ──────────────────────────────────────
    def _open_about(e=None):
        def _close(e=None):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            modal=True,
            bgcolor=COLORS["primary_light"],
            title=ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.icons.INFO_OUTLINE, size=20, color="white"),
                        ft.Text("О программе", size=16,
                                weight=ft.FontWeight.BOLD, color="white"),
                    ],
                    spacing=8,
                ),
                padding=ft.padding.symmetric(horizontal=16, vertical=12),
                gradient=ft.LinearGradient(
                    begin=ft.alignment.center_left,
                    end=ft.alignment.center_right,
                    colors=[COLORS["primary"], COLORS["primary_light"]],
                ),
                border_radius=ft.border_radius.only(top_left=12, top_right=12),
            ),
            # Раунд 28 (задача 5): текст обрезался при 1280x720 — ограничиваем
            # высоту и даём внутренний скролл (просто Column(scroll=AUTO) внутри
            # фиксированной высоты — легально по AGENTS §15.11).
            # Раунд 33 (задача 1.3): больше места + внутренний скролл —
            # текст больше не обрезается справа (скрин «Не помещается текст
            # в о программе.png»). Помещается на 1280x720.
            content=ft.Container(
                width=720,
                height=520,
                content=ft.Column(
                    scroll=ft.ScrollMode.AUTO,
                    controls=[
                        ft.Text("Порайонка v2.0 DARK final", size=20,
                                weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                        ft.Container(height=8),
                        ft.Text(
                            "Разработчик: Старший следователь-криминалист "
                            "отдела криминалистики СУ СК России по Ростовской области "
                            "Гайнутдинов Станислав Игоревич",
                            size=13,
                            color=COLORS["text_secondary"],
                        ),
                        ft.Container(height=12),
                        ft.Text("Возможности приложения:", size=14,
                                weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                        ft.Container(height=6),
                        ft.Row(controls=[
                            ft.Icon(ft.icons.CHECK, size=14, color=COLORS["received"]),
                            ft.Text("Три вкладки: «Следственные отделы», "
                                    "«Зональные криминалисты», «Контроли»",
                                    size=12, color=COLORS["text_secondary"],
                                    expand=True),
                        ], spacing=6, tight=True),
                        ft.Row(controls=[
                            ft.Icon(ft.icons.CHECK, size=14, color=COLORS["received"]),
                            ft.Text("Контроли: сроки, пункты, исполнители, "
                                    "вложения, архив, импорт/экспорт Excel",
                                    size=12, color=COLORS["text_secondary"],
                                    expand=True),
                        ], spacing=6, tight=True),
                        ft.Row(controls=[
                            ft.Icon(ft.icons.CHECK, size=14, color=COLORS["received"]),
                            ft.Text("Две редакции: администраторская (полная, "
                                    "с паролем) и пользовательская (просмотр)",
                                    size=12, color=COLORS["text_secondary"],
                                    expand=True),
                        ], spacing=6, tight=True),
                        ft.Row(controls=[
                            ft.Icon(ft.icons.CHECK, size=14, color=COLORS["received"]),
                            ft.Text("Сетевая синхронизация контролей через "
                                    "общую папку",
                                    size=12, color=COLORS["text_secondary"],
                                    expand=True),
                        ], spacing=6, tight=True),
                        ft.Row(controls=[
                            ft.Icon(ft.icons.CHECK, size=14, color=COLORS["received"]),
                            ft.Text("Напоминания о сроках контроля: "
                                    "у пользователей каждые 2 часа, "
                                    "у администраторов — раз в день",
                                    size=12, color=COLORS["text_secondary"],
                                    expand=True),
                        ], spacing=6, tight=True),
                        ft.Row(controls=[
                            ft.Icon(ft.icons.CHECK, size=14, color=COLORS["received"]),
                            ft.Text("Системный трей и автозапуск; web-режим "
                                    "для Windows 7 (работа в браузере)",
                                    size=12, color=COLORS["text_secondary"],
                                    expand=True),
                        ], spacing=6, tight=True),
                        ft.Row(controls=[
                            ft.Icon(ft.icons.CHECK, size=14, color=COLORS["received"]),
                            ft.Text("Экспорт сводки в Excel для руководства",
                                    size=12, color=COLORS["text_secondary"],
                                    expand=True),
                        ], spacing=6, tight=True),
                        ft.Container(height=12),
                        ft.Text(
                            "Приложение создано для автоматизации учёта "
                            "и контроля работы следственных отделов и зональных "
                            "криминалистов Следственного комитета Российской "
                            "Федерации по Ростовской области.",
                            size=12,
                            color=COLORS["text_muted"],
                            italic=True,
                        ),
                    ],
                    spacing=0,
                    tight=True,
                ),
                padding=ft.padding.all(20),
            ),
            actions=[
                ft.ElevatedButton(
                    "Закрыть",
                    bgcolor=COLORS["btn_save"],
                    color="white",
                    on_click=_close,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    page._open_about = _open_about

    # ── Кнопка «Настройка формы» (только вкладка Зональные) ───────
    # Раунд 26 (задача 6): кнопка относится только к «Зональным» — видимость
    # задаётся параметром и переключается из main._switch_tab через
    # page._btn_form_settings.
    btn_settings = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.icons.SETTINGS_OUTLINED, size=14,
                        color=COLORS["text_secondary"]),
                ft.Text("Настройка формы", size=11,
                        color=COLORS["text_secondary"],
                        weight=ft.FontWeight.W_500, no_wrap=True),
            ],
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        ),
        height=28,
        padding=ft.padding.symmetric(horizontal=10),
        border_radius=8,
        border=ft.border.all(1, COLORS["border"]),
        alignment=ft.alignment.center,
        ink=True,
        visible=form_settings_visible,
        on_click=lambda e: (page._open_template_settings()
                            if hasattr(page, "_open_template_settings") else None),
        tooltip="Настройка шаблона сбора данных (вкладка «Зональные»)",
    )
    try:
        page._btn_form_settings = btn_settings
    except Exception:
        pass

    # ── Кнопка «О программе» ──────────────────────────────────────
    btn_about = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.icons.INFO_OUTLINE, size=14,
                        color=COLORS["text_secondary"]),
                ft.Text("О программе", size=11,
                        color=COLORS["text_secondary"],
                        weight=ft.FontWeight.W_500, no_wrap=True),
            ],
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        ),
        height=28,
        padding=ft.padding.symmetric(horizontal=10),
        border_radius=8,
        border=ft.border.all(1, COLORS["border"]),
        alignment=ft.alignment.center,
        ink=True,
        on_click=_open_about,
        tooltip="Информация о приложении и разработчике",
    )

    right_block = ft.Row(
        controls=[
            btn_settings,
            btn_about,
            ft.Container(width=1, height=20, bgcolor=COLORS["border"]),
            ft.Icon(ft.icons.SCHEDULE, size=13, color=COLORS["text_muted"]),
            ft.Text("Сохранено:", size=11, color=COLORS["text_muted"], no_wrap=True),
            save_text,
        ],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        tight=True,
    )

    return ft.Container(
        content=ft.Row(
            controls=[tabs_control, right_block],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        height=52,
        padding=ft.padding.symmetric(horizontal=16, vertical=6),
        gradient=ft.LinearGradient(
            begin=ft.alignment.center_left,
            end=ft.alignment.center_right,
            colors=[COLORS["primary"], COLORS["primary_dark"]],
        ),
        border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"])),
    )
