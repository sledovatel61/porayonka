# ui/reset_modal.py
# Модальное окно подтверждения сброса всех статусов
# [DARK THEME] Обновлено визуально
import flet as ft
from core.constants import COLORS

def create_reset_modal(
    page: ft.Page,
    on_confirm_reset: callable,
) -> ft.AlertDialog:
    """
    Создать модальное диалоговое окно подтверждения сброса.
    """
    def close_dialog(e=None):
        dialog.open = False
        page.update()

    def confirm_reset(e=None):
        dialog.open = False
        page.update()
        on_confirm_reset()

    dialog = ft.AlertDialog(
        modal=True,
        bgcolor=COLORS["primary_light"],  # ТЁМНЫЙ ФОН
        title=ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text("⚠️", size=22),
                    ft.Text(
                        "Сброс данных",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color="white",
                        expand=True,
                    ),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            gradient=ft.LinearGradient(
                begin=ft.alignment.center_left,
                end=ft.alignment.center_right,
                colors=["#dc2626", "#b91c1c"],
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=14),
            border_radius=ft.border_radius.only(top_left=12, top_right=12),
            margin=ft.margin.only(top=-12, left=-24, right=-24),
        ),
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(height=8),
                    ft.Container(
                        content=ft.Text("🔄", size=48),
                        alignment=ft.alignment.center,
                    ),
                    ft.Container(height=12),
                    ft.Text(
                        "Все статусы будут сброшены до начального состояния.",
                        size=14,
                        color=COLORS["text"],  # Светлый текст
                        text_align=ft.TextAlign.CENTER,
                        weight=ft.FontWeight.W_500,
                    ),
                    ft.Container(height=6),
                    ft.Container(
                        content=ft.Text(
                            "Это действие нельзя отменить.",
                            size=13,
                            color="#f87171",  # Светло-красный
                            weight=ft.FontWeight.BOLD,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        alignment=ft.alignment.center,
                    ),
                    ft.Container(height=12),
                    ft.Container(
                        content=ft.Text(
                            "Вы уверены, что хотите продолжить?",
                            size=13,
                            color=COLORS["text_secondary"],  # Серый текст
                            text_align=ft.TextAlign.CENTER,
                            italic=True,
                        ),
                        alignment=ft.alignment.center,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=0,
            ),
            width=380,
            padding=ft.padding.all(20),
        ),
        actions=[
            ft.TextButton(
                text="Отмена",
                style=ft.ButtonStyle(
                    color=COLORS["text_secondary"],
                    bgcolor=COLORS["empty_bg"],
                    shape=ft.RoundedRectangleBorder(radius=8),
                    padding=ft.padding.symmetric(horizontal=24, vertical=12),
                ),
                expand=True,
                on_click=close_dialog,
            ),
            ft.ElevatedButton(
                text="Сбросить",
                icon=ft.Icons.DELETE_SWEEP_OUTLINED,
                bgcolor="#dc2626",
                color="white",
                elevation=2,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=8),
                    padding=ft.padding.symmetric(horizontal=24, vertical=12),
                ),
                expand=True,
                on_click=confirm_reset,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        shape=ft.RoundedRectangleBorder(radius=12),
    )

    def open_dialog():
        dialog.open = True
        page.update()

    # Сохранить функцию открытия в page
    page.open_reset_modal = open_dialog
    return dialog