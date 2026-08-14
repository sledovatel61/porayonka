# ui/controls/controls_settings_modal.py
# Настройки вкладки «Контроли»: порог «скоро», сетевой режим, пользователь,
# пароль администратора.
# Раунд 28 (задача 6): управление справочниками (люди/инициаторы) УБРАНО —
# оно живёт в отдельной модалке «Справочники» из тулбара; значения
# custom_initiators/extra_people здесь лишь прокидываются при сохранении.
import flet as ft
from typing import Callable

from core.constants import COLORS
from core.controls_data import (
    DEFAULT_SETTINGS, DEFAULT_NETWORK_PATH, get_criminalist_names,
)
from core.controls_models import short_name


def _default_net_path29() -> str:
    """Раунд 29 (задача 4): дефолтный сетевой путь (UNC), если поле пути
    оставлено пустым — чтобы не вводить вручную на каждом ПК."""
    return DEFAULT_NETWORK_PATH


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
    # Раунд 31 (задача 4): у user-редакции звук уведомлений ОБЯЗАТЕЛЕН —
    # переключатель скрывается, вместо него read-only строка «включён».
    # (Заполняется позже, когда известна редакция — _is_user_edition29.)
    sound_user_ro = ft.Container(
        content=ft.Row(controls=[
            ft.Icon(ft.icons.NOTIFICATIONS_ACTIVE, size=16,
                    color=COLORS["text_secondary"]),
            ft.Text("Звук уведомлений включён", size=12, color=COLORS["text"],
                    weight=ft.FontWeight.W_600),
        ], spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        visible=False,
    )

    net_switch = ft.Switch(
        value=bool(settings.get("network_enabled")),
        active_color=COLORS["received"], label="Сетевой режим",
    )
    # Раунд 35 (задача 1.2): у user-редакции сеть read-only (иконка замка +
    # текст «включён») — пользователь не может отключить синхронизацию.
    net_switch_ro = ft.Container(
        content=ft.Row(controls=[
            ft.Icon(ft.icons.LOCK_OUTLINE, size=16,
                    color=COLORS["text_secondary"]),
            ft.Text("Сетевой режим включён", size=12, color=COLORS["text"],
                    weight=ft.FontWeight.W_600),
        ], spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        visible=False,
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
    # Раунд 29 (задача 10): user-редакция с ФИО, зафиксированным установщиком
    # (edition.json рядом с exe), не должна позволять смену пользователя из
    # настроек — раньше выбор «другого» сохранялся в настройки, но при
    # следующем запуске apply_edition_to_settings возвращал зафиксированное
    # ФИО, и пользователь видел несостоявшуюся смену («остался Семисенко»).
    from core.edition import load_edition as _load_edition29  # noqa: E402
    try:
        _edition29 = _load_edition29() or {}
    except Exception:
        _edition29 = {}
    _fixed_user29 = ""
    try:
        if (_edition29.get("role") == "user"
                and (_edition29.get("user_name") or "").strip()):
            _fixed_user29 = (_edition29.get("user_name") or "").strip()
    except Exception:
        _fixed_user29 = ""
    _is_user_edition29 = (_edition29.get("role") == "user")
    user_dd = ft.Dropdown(
        label="Пользователь (ФИО)",
        value=(_fixed_user29 or current_user)
        if (_fixed_user29 or current_user) in criminalist_names else None,
        options=[ft.dropdown.Option(n, short_name(n)) for n in criminalist_names],
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"], width=340,
        disabled=bool(_fixed_user29),
    )
    # Раунд 29 (задача 10): подсказка под dropdown'ом пользователя.
    user_hint = ft.Text(
        ("Пользователь задан при установке. Для смены переустановите "
         "приложение или обратитесь к администратору."
         if _fixed_user29 else
         ("Выберите себя из списка — к ФИО привязываются «свои» контроли "
          "и напоминания о сроках." if _is_user_edition29 else
          "Пользователь (ФИО) — для роли «Пользователь»: свои контроли и "
          "напоминания о сроках.")),
        size=10, color=COLORS["text_muted"],
    )
    if _fixed_user29:
        # Зафиксированное ФИО обязано быть ВИДНО даже если справочник
        # переименовали/почистили — добавляем опцией.
        try:
            if _fixed_user29 not in criminalist_names:
                user_dd.options.append(
                    ft.dropdown.Option(_fixed_user29, short_name(_fixed_user29)))
                user_dd.value = _fixed_user29
        except Exception:
            pass
    # Раунд 30 (задача 4): зафиксированное установщиком ФИО показываем
    # read-only ВИДОМ (иконка замка + светлый текст) вместо disabled Dropdown:
    # клиент Flet 0.23.2 рисует выбранное значение disabled-Dropdown цветом
    # светлой темы (почти чёрный на тёмном фоне — «Не видно кто пользователь,
    # текст черный.png»), а text_style/color на disabled-состояние не влияют.
    user_dd_ro = None
    if _fixed_user29:
        user_dd_ro = ft.Container(
            content=ft.Row(controls=[
                ft.Icon(ft.icons.LOCK_OUTLINE, size=16,
                        color=COLORS["text_secondary"]),
                ft.Text(_fixed_user29, size=13, color=COLORS["text"],
                        weight=ft.FontWeight.W_600, expand=True, no_wrap=True,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        tooltip=_fixed_user29),
            ], spacing=8, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=COLORS["card"], border=ft.border.all(1, COLORS["border"]),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=12, vertical=12),
            width=340,
        )
    # Раунд 29 (задача 10, смежно): роль в user-редакции тоже редактируется
    # только редакцией — не даём уйти в «Администратор» и сохранить мусор
    # (apply_edition_to_settings всё равно вернул бы «user» при запуске).
    # Раунд 31 (задача 4): у user-редакции звук уведомлений нельзя выключить —
    # переключатель заменяется read-only строкой «включён».
    if _is_user_edition29:
        try:
            role_dd.value = "user"
            role_dd.disabled = True
        except Exception:
            pass
        sound_check.visible = False
        sound_user_ro.visible = True
        # Раунд 35: сеть у user — read-only (переключатель скрыт)
        net_switch.visible = False
        net_switch_ro.visible = True
    path_field = ft.TextField(
        value=settings.get("network_shared_path", ""),
        label="Путь к общей папке/файлу (например \\\\SERVER\\share\\porayonka\\controls.json)",
        label_style=ft.TextStyle(color=COLORS["text_secondary"]),
        border_radius=8, border_color=COLORS["border"],
        focused_border_color=COLORS["btn_save"],
        bgcolor=COLORS["card"], color=COLORS["text"],
        hint_style=ft.TextStyle(color=COLORS["text_muted"]),
        width=556,
        # Раунд 29 (задача 4): дефолтный UNC-путь уже подставлен при загрузке
        # настроек (load_settings); здесь — напоминание в placeholder.
        hint_text="Оставьте как есть: \\\\192.168.0.60\\общая\\Гайнутдинов\\Porayonka workspace",
    )
    hint_text = ft.Text(
        "Синхронизация: общий JSON + обновление раз в ~20 сек. "
        "Перед перезаписью — резервная копия. Вложения — в общей папке. "
        "При пустом пути подставляется сетевой путь по умолчанию.",
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
        # Раунд 29: ключи из текущих настроек сохраняем ВСЕ (мапа выше
        # перекрывает редактируемые) — раньше терялись col_widths/refs_* /
        # person_roles / alarm_log и пр. не-редактируемые здесь ключи.
        merged.update(settings or {})
        merged.update({
            "soon_days": soon,
            # Раунд 35: у user-редакции сеть принудительно включена
            "network_enabled": (True if _is_user_edition29
                                else bool(net_switch.value)),
            "network_role": role_dd.value or "admin",
            # Раунд 29 (задача 10): фиксированное установщиком ФИО не подменяем
            # выбором из отключённого dropdown (оно всё равно вернулось бы
            # при запуске — см. apply_edition_to_settings).
            "network_user": (_fixed_user29 or (user_dd.value or "")),
            # Раунд 29 (задача 4): пустой путь -> сетевой путь по умолчанию.
            "network_shared_path": (path_field.value or "").strip()
            or _default_net_path29(),
            # Раунд 31 (задача 4): у user-редакции звук принудительно включён
            "notify_sound": (True if _is_user_edition29
                             else bool(sound_check.value)),
        })
        on_apply(merged)
        dialog.open = False
        page.update()

    _sections = [
        ft.Container(
            content=ft.Column(controls=[
                ft.Text("Уведомления", size=12, weight=ft.FontWeight.BOLD,
                        color=COLORS["text"]),
                soon_field,
                # Раунд 31 (задача 4): user-редакция — read-only «включён»
                # вместо переключателя звука
                (sound_user_ro if _is_user_edition29 else sound_check),
            ], spacing=6, tight=True),
            bgcolor=COLORS["card"], border=ft.border.all(1, COLORS["border"]),
            border_radius=10, padding=ft.padding.all(10),
        ),
        ft.Container(
            content=ft.Column(controls=[
                ft.Text("Сетевой режим (локальная сеть)", size=12,
                        weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                # Раунд 35: user — read-only «включён» вместо переключателя
                (net_switch_ro if _is_user_edition29 else net_switch),
                role_dd,
                (user_dd_ro if user_dd_ro is not None else user_dd),
                user_hint,
                path_field,
                hint_text,
            ], spacing=8, tight=True),
            bgcolor=COLORS["card"], border=ft.border.all(1, COLORS["border"]),
            border_radius=10, padding=ft.padding.all(10),
        ),
    ]
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
            content=ft.Column(controls=_sections, spacing=10,
                              scroll=ft.ScrollMode.AUTO),
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
