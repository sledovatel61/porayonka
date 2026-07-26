# ui/zonal/collapsible.py
# Сворачиваемая секция для вкладки "Зональные" (редизайн, фаза 3).
#
# Зачем: конструктор шаблона и подробная сводка занимали почти весь экран.
# Теперь они лежат в сворачиваемых секциях (по умолчанию свёрнуты) и
# раскрываются кликом по заголовку.
#
# LAYOUT (Flet 0.23.2): секция — это обычный ft.Column без expand и без scroll.
# Сворачивание сделано через visible=False у тела секции: скрытый контрол
# не участвует в раскладке, поэтому свёрнутая секция занимает только высоту
# своего заголовка.
import flet as ft
from core.constants import COLORS


def create_collapsible_section(
    title: str,
    icon,
    body: ft.Control,
    expanded: bool = False,
    subtitle: str = None,
) -> ft.Column:
    """
    Создать сворачиваемую секцию.

    :param title: заголовок секции (русский текст)
    :param icon: иконка ft.icons.*
    :param body: содержимое секции (любой контрол)
    :param expanded: раскрыта ли секция изначально (по умолчанию — свёрнута)
    :param subtitle: необязательная краткая подпись справа от заголовка
    :return: ft.Column с заголовком и телом
    """
    body_container = ft.Container(
        content=body,
        visible=expanded,
        padding=ft.padding.only(top=10),
    )

    chevron = ft.Icon(
        ft.icons.EXPAND_MORE if expanded else ft.icons.CHEVRON_RIGHT,
        size=20,
        color="white",
    )

    state = {"expanded": expanded}

    def _toggle(e=None):
        state["expanded"] = not state["expanded"]
        body_container.visible = state["expanded"]
        chevron.name = ft.icons.EXPAND_MORE if state["expanded"] else ft.icons.CHEVRON_RIGHT
        try:
            body_container.update()
            chevron.update()
        except Exception:
            pass

    header_controls = [
        chevron,
        ft.Icon(icon, size=18, color="white"),
        ft.Text(title, size=14, weight=ft.FontWeight.BOLD, color="white"),
    ]
    if subtitle:
        header_controls.append(
            ft.Text(subtitle, size=11, color=COLORS["text_secondary"])
        )

    header = ft.Container(
        content=ft.Row(
            controls=header_controls,
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        gradient=ft.LinearGradient(
            begin=ft.alignment.center_left,
            end=ft.alignment.center_right,
            colors=[COLORS["primary"], COLORS["primary_light"]],
        ),
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
        border_radius=10,
        ink=True,
        on_click=_toggle,
        tooltip="Нажмите, чтобы свернуть или развернуть",
    )

    return ft.Column(controls=[header, body_container], spacing=0, tight=True)
