# ui/controls/controls_settings_modal.py
# Настройки вкладки «Контроли»: порог «скоро», сетевой режим и синхронизация.
import flet as ft
from typing import Callable, Dict

from core.constants import COLORS
from core.controls_data import DEFAULT_SETTINGS, get_criminalist_names


def create_controls_settings_modal(
    page: ft.Page,
    settings: dict,
    on_apply: Callable[[dict], None],
) -> ft.AlertDialog:
    """Модалка настроек. on_apply(merged_settings) вызывается при сохранении."""
    soon_field = ft.TextField(
        value=str(settings.get("soon_days", 3)),
        label="Считать срок «скорым» за (дней)",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        keyboard_type=ft.KeyboardType.NUMBER, width=220,
    )

    net_switch = ft.Switch(
        value=bool(settings.get("network_enabled")),
        active_color=COLORS["received"], label="Сетевой режим",
    )
    role_dd = ft.Dropdown(
        label="Роль",
        value=settings.get("network_role", "admin"),
        options=[
            ft.dropdown.Option("admin", "Администратор (ведёт контроли)"),
            ft.dropdown.Option("user", "Пользователь (видит свои задания)"),
        ],
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"], width=320,
    )
    user_field = ft.TextField(
        value=settings.get("network_user", ""),
        label="Имя пользователя / компьютера (по-фамильно)",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        hint_style=ft.TextStyle(color=COLORS["text_muted"]),
        expand=True,
    )
    path_field = ft.TextField(
        value=settings.get("network_shared_path", ""),
        label="Путь к общей папке/файлу (например \\\\SERVER\\share\\porayonka\\controls.json)",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        hint_style=ft.TextStyle(color=COLORS["text_muted"]),
        expand=True,
    )
    hint_text = ft.Text(
        "Синхронизация: общий JSON-файл + автоматическое обновление раз в ~20 сек. "
        "Перед перезаписью создаётся резервная копия.",
        size=10, color=COLORS["text_muted"],
    )

    def _close(e=None):
        dialog.open = False
        page.update()

    def _save(e=None):
        try:
            soon = max(1, int(soon_field.value or "3"))
        except ValueError:
            soon = 3
        merged = dict(DEFAULT_SETTINGS)
        merged.update({
            "soon_days": soon,
            "network_enabled": bool(net_switch.value),
            "network_role": role_dd.value or "admin",
            "network_user": (user_field.value or "").strip(),
            "network_shared_path": (path_field.value or "").strip(),
        })
        on_apply(merged)
        dialog.open = False
        page.update()

    dialog = ft.AlertDialog(
        modal=True,
        bgcolor=COLORS["primary_light"],
        title=ft.Row(controls=[
            ft.Icon(ft.icons.SETTINGS_OUTLINED, size=20, color=COLORS["text"]),
            ft.Text("Настройки контролей", size=16, weight=ft.FontWeight.BOLD,
                    color=COLORS["text"]),
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        content=ft.Container(
            width=560,
            content=ft.Column(controls=[
                ft.Container(
                    content=ft.Column(controls=[
                        ft.Text("Уведомления", size=12, weight=ft.FontWeight.BOLD,
                                color=COLORS["text"]),
                        soon_field,
                    ], spacing=6, tight=True),
                    bgcolor=COLORS["card"], border=ft.border.all(1, COLORS["border"]),
                    border_radius=10, padding=ft.padding.all(10),
                ),
                ft.Container(
                    content=ft.Column(controls=[
                        ft.Text("Сетевой режим (локальная сеть)", size=12,
                                weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                        net_switch,
                        role_dd,
                        user_field,
                        path_field,
                        hint_text,
                    ], spacing=8, tight=True),
                    bgcolor=COLORS["card"], border=ft.border.all(1, COLORS["border"]),
                    border_radius=10, padding=ft.padding.all(10),
                ),
            ], spacing=10, tight=True),
        ),
        actions=[
            ft.TextButton("Отмена", on_click=_close),
            ft.ElevatedButton("Сохранить", icon=ft.icons.SAVE, bgcolor=COLORS["btn_save"],
                              color=COLORS["text_light"], on_click=_save,
                              style=ft.ButtonStyle(
                                  shape=ft.RoundedRectangleBorder(radius=8),
                                  padding=ft.padding.symmetric(horizontal=20, vertical=8))),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        shape=ft.RoundedRectangleBorder(radius=12),
    )
    return dialog
