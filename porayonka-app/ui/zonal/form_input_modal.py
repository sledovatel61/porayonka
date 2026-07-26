# ui/zonal/form_input_modal.py
# Модальное окно ввода сданных данных по форме для криминалиста.
# Открывается кликом по плашке. Фаза 2.
# [DARK THEME] + ft.icons.* + hint_style (Flet 0.23.2)
import flet as ft
from core.zonal_data import get_report_data, save_zonal_collection
from core.constants import COLORS
from .form_fields import build_item_block, build_comment_block


def create_form_input_modal(
    page: ft.Page,
    criminalist,
    collection,
    dept_map: dict,
    on_saved: callable,
) -> ft.AlertDialog:
    """
    Создать модальное окно заполнения формы для криминалиста.
    on_saved(criminalist) вызывается после сохранения (для обновления плашки).
    """
    print(f"[FORM_MODAL] Opening form for criminalist id={criminalist.id}")

    items_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

    def _autosave():
        try:
            save_zonal_collection(collection)
        except Exception as e:
            print(f"[FORM_MODAL] Autosave error: {e}")

    def _rebuild_items():
        items_list.controls.clear()
        if not collection.template.items:
            items_list.controls.append(
                ft.Container(
                    content=ft.Text(
                        "Нет пунктов шаблона. Добавьте пункты в конструкторе.",
                        size=13,
                        color=COLORS["text_muted"],
                        italic=True,
                    ),
                    padding=ft.padding.all(12),
                )
            )
        else:
            for item in sorted(collection.template.items, key=lambda x: x.order):
                rd = get_report_data(collection, criminalist.id, item.id)
                items_list.controls.append(
                    build_item_block(item, rd, criminalist, collection, _autosave, dept_map)
                )
        # Комментарий (общий)
        items_list.controls.append(build_comment_block(collection, criminalist, _autosave))
        try:
            items_list.update()
        except Exception:
            pass

    _rebuild_items()

    def _close(e=None):
        dialog.open = False
        page.update()

    def _save(e=None):
        _autosave()
        dialog.open = False
        page.update()
        if on_saved:
            on_saved(criminalist)
        from ui.toast import show_save_toast
        show_save_toast(page)

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ft.icons.EDIT_DOCUMENT, size=20, color="white"),
                    ft.Text(
                        f"Форма: {criminalist.full_name}",
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color="white",
                        expand=True,
                    ),
                    ft.IconButton(
                        icon=ft.icons.CLOSE,
                        icon_color="white",
                        icon_size=18,
                        on_click=_close,
                        style=ft.ButtonStyle(padding=ft.padding.all(4)),
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            gradient=ft.LinearGradient(
                begin=ft.alignment.center_left,
                end=ft.alignment.center_right,
                colors=[COLORS["primary"], COLORS["primary_light"]],
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            border_radius=ft.border_radius.only(top_left=12, top_right=12),
            margin=ft.margin.only(top=-12, left=-24, right=-24),
        ),
        bgcolor=COLORS["primary_light"],
        content=ft.Container(
            content=items_list,
            width=560,
            height=520,
        ),
        actions=[
            ft.TextButton(
                "Отмена",
                style=ft.ButtonStyle(
                    color=COLORS["text_secondary"],
                    bgcolor=COLORS["empty_bg"],
                    shape=ft.RoundedRectangleBorder(radius=8),
                    padding=ft.padding.symmetric(horizontal=20, vertical=10),
                ),
                expand=True,
                on_click=_close,
            ),
            ft.ElevatedButton(
                "Сохранить",
                icon=ft.icons.SAVE,
                bgcolor=COLORS["btn_save"],
                color="white",
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=8),
                    padding=ft.padding.symmetric(horizontal=20, vertical=10),
                ),
                expand=True,
                on_click=_save,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        shape=ft.RoundedRectangleBorder(radius=12),
    )

    print(f"[FORM_MODAL] Dialog created for criminalist id={criminalist.id}")
    return dialog
