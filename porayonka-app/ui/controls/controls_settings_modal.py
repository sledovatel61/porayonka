# ui/controls/controls_settings_modal.py
# Настройки вкладки «Контроли»: порог «скоро», сетевой режим,
# пользователь, пользовательские инициаторы.
import flet as ft
from typing import Callable

from core.constants import COLORS
from core.controls_data import DEFAULT_SETTINGS, get_criminalist_names
from core.controls_models import short_name


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
    sound_check = ft.Checkbox(
        label="Звук уведомлений",
        value=bool(settings.get("notify_sound", True)),
        active_color=COLORS["received"],
        label_style=ft.TextStyle(size=12, color=COLORS["text"]),
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
        bgcolor=COLORS["card"], color=COLORS["text"], width=340,
    )

    criminalist_names = get_criminalist_names()
    current_user = settings.get("network_user", "") or ""
    user_dd = ft.Dropdown(
        label="Пользователь (ФИО)",
        value=current_user if current_user in criminalist_names else None,
        options=[ft.dropdown.Option(n, short_name(n)) for n in criminalist_names],
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"], width=340,
    )
    path_field = ft.TextField(
        value=settings.get("network_shared_path", ""),
        label="Путь к общей папке/файлу (например \\\\SERVER\\share\\porayonka\\controls.json)",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        hint_style=ft.TextStyle(color=COLORS["text_muted"]),
        width=556,
    )
    hint_text = ft.Text(
        "Синхронизация: общий JSON + обновление раз в ~20 сек. "
        "Перед перезаписью — резервная копия. Вложения — в общей папке.",
        size=10, color=COLORS["text_muted"],
    )

    # ── Пользовательские инициаторы ─────────────────────────────
    init_list = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, height=90)
    init_field = ft.TextField(
        label="Новый инициатор",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        hint_style=ft.TextStyle(color=COLORS["text_muted"]),
        expand=True, height=36,
    )

    def _rebuild_init_list():
        init_list.controls.clear()
        cur = list(settings.get("custom_initiators", []) or [])
        if not cur:
            init_list.controls.append(ft.Text("Нет пользовательских инициаторов",
                                              size=11, color=COLORS["text_muted"]))
        for name in cur:
            init_list.controls.append(
                ft.Container(
                    content=ft.Row(controls=[
                        ft.Icon(ft.icons.ACCOUNT_CIRCLE_OUTLINED, size=14,
                                color=COLORS["text_secondary"]),

                        ft.Text(name, size=12, color=COLORS["text"], expand=True,
                                no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS,
                                tooltip=name),
                        ft.IconButton(icon=ft.icons.CLOSE, icon_size=14,
                                      icon_color="#f87171", tooltip="Удалить",
                                      on_click=lambda e, n=name: _remove_init(n)),
                    ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                       alignment=ft.MainAxisAlignment.START, tight=True),
                    bgcolor=COLORS["card"], border=ft.border.all(1, COLORS["border"]),
                    border_radius=6, padding=ft.padding.symmetric(horizontal=6, vertical=2),
                )
            )
        try:
            init_list.update()
        except Exception:
            pass

    def _add_init(e=None):
        name = init_field.value.strip()
        if not name:
            return
        cur = list(settings.get("custom_initiators", []) or [])
        if name not in cur:
            cur.append(name)
        settings["custom_initiators"] = cur
        init_field.value = ""
        try:
            init_field.update()
        except Exception:
            pass
        _rebuild_init_list()

    def _remove_init(name):
        cur = list(settings.get("custom_initiators", []) or [])
        if name in cur:
            cur.remove(name)
        settings["custom_initiators"] = cur
        _rebuild_init_list()

    _rebuild_init_list()

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
            "network_user": user_dd.value or "",
            "network_shared_path": (path_field.value or "").strip(),
            "custom_initiators": list(settings.get("custom_initiators", []) or []),
            "notify_sound": bool(sound_check.value),
            "notify_log": settings.get("notify_log") or {},
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
            width=600,
            height=460,
            content=ft.Column(controls=[
                ft.Container(
                    content=ft.Column(controls=[
                        ft.Text("Уведомления", size=12, weight=ft.FontWeight.BOLD,
                                color=COLORS["text"]),
                        soon_field,
                        sound_check,
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
                        user_dd,
                        path_field,
                        hint_text,
                    ], spacing=8, tight=True),
                    bgcolor=COLORS["card"], border=ft.border.all(1, COLORS["border"]),
                    border_radius=10, padding=ft.padding.all(10),
                ),
                ft.Container(
                    content=ft.Column(controls=[
                        ft.Text("Инициаторы (пользовательские)", size=12,
                                weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                        ft.Row(controls=[init_field,
                                          ft.ElevatedButton("Добавить",
                                                            bgcolor=COLORS["btn_save"],
                                                            color=COLORS["text_light"],
                                                            height=36,
                                                            on_click=_add_init)],
                               spacing=6, tight=True,
                               vertical_alignment=ft.CrossAxisAlignment.CENTER,
                               alignment=ft.MainAxisAlignment.START),
                        init_list,
                    ], spacing=8, tight=True),
                    bgcolor=COLORS["card"], border=ft.border.all(1, COLORS["border"]),
                    border_radius=10, padding=ft.padding.all(10),
                ),
            ], spacing=10, scroll=ft.ScrollMode.AUTO),
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
