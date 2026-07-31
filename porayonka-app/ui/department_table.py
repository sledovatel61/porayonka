# ui/department_table.py
# Kanban-доска: три колонки по статусам (Не получено / Запрошено / Получено)
import flet as ft
from typing import List, Callable, Dict
from core.models import Department, Status
from core.constants import COLORS

# ── Конфигурация колонок ─────────────────────────────────────────
_COLUMN_CONFIG: Dict[Status, dict] = {
    Status.EMPTY: {
        "title": "Не получено",
        "header_color": COLORS["empty"],
        "header_bg": COLORS["empty_bg"],
        "col_bg": "#0d1526",
        "stripe_color": COLORS["empty"],
        "card_bg": COLORS["card"],
        "card_hover": COLORS["card_hover"],
        "count_bg": COLORS["empty_bg"],
        "count_color": COLORS["text_secondary"],
    },
    Status.IN_PROGRESS: {
        "title": "Запрошено",
        "header_color": COLORS["in_progress"],
        "header_bg": COLORS["in_progress_bg"],
        "col_bg": "#140f04",
        "stripe_color": COLORS["in_progress"],
        "card_bg": COLORS["card"],
        "card_hover": COLORS["card_hover"],
        "count_bg": COLORS["in_progress_bg"],
        "count_color": COLORS["in_progress_text"],
    },
    Status.RECEIVED: {
        "title": "Получено",
        "header_color": COLORS["received"],
        "header_bg": COLORS["received_bg"],
        "col_bg": "#04130a",
        "stripe_color": COLORS["received"],
        "card_bg": COLORS["card"],
        "card_hover": COLORS["card_hover"],
        "count_bg": COLORS["received_bg"],
        "count_color": COLORS["received_text"],
    },
}

# Порядок колонок слева направо (жизненный цикл)
_COLUMN_ORDER = [Status.EMPTY, Status.IN_PROGRESS, Status.RECEIVED]

# Следующий статус при клике (справа по циклу)
_NEXT_STATUS: Dict[Status, Status] = {
    Status.EMPTY: Status.IN_PROGRESS,
    Status.IN_PROGRESS: Status.RECEIVED,
    Status.RECEIVED: Status.EMPTY,
}


def _next_status_label(dept: Department) -> str:
    """Название статуса, в который перейдёт отдел при клике."""
    next_s = _NEXT_STATUS.get(dept.status, Status.EMPTY)
    return _COLUMN_CONFIG[next_s]["title"]


def _make_card(dept: Department, on_click: Callable, col_cfg: dict) -> ft.Container:
    """Создать карточку отдела для канбан-колонки."""
    # Номер: для ОВД — прочерк, для СО — id
    num_text = "—" if dept.is_ovd else str(dept.id)
    num_color = COLORS["text_muted"] if dept.is_ovd else COLORS["text_light"]
    num_bg = COLORS["btn_reset"] if dept.is_ovd else COLORS["primary_light"]

    name_color = COLORS["text_muted"] if dept.is_ovd else COLORS["text"]

    # Динамический tooltip: куда переедет при клике
    if dept.is_active:
        next_title = _next_status_label(dept)
        tip = f"→ {next_title}"
    else:
        tip = "Отдел отключён"

    card = ft.Container(
        content=ft.Row(
            controls=[
                # Цветная полоса слева
                ft.Container(
                    width=4,
                    border_radius=2,
                    bgcolor=col_cfg["stripe_color"],
                ),
                # Номер
                ft.Container(
                    content=ft.Text(
                        num_text,
                        size=11,
                        color=num_color,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    width=26,
                    height=26,
                    bgcolor=num_bg,
                    border_radius=13,
                    alignment=ft.alignment.center,
                ),
                # Название
                ft.Text(
                    dept.name,
                    size=13,
                    color=name_color,
                    italic=dept.is_ovd,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    no_wrap=True,
                    expand=True,
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        ),
        bgcolor=col_cfg["card_bg"],
        border_radius=8,
        padding=ft.padding.only(left=6, right=12, top=8, bottom=8),
        margin=ft.margin.only(bottom=6),
        opacity=0.45 if not dept.is_active else 1.0,
        ink=True if dept.is_active else False,
        on_click=lambda e: on_click() if dept.is_active else None,
        tooltip=tip,
        animate_opacity=ft.animation.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
    )

    # Hover-эффект для активных
    if dept.is_active:
        normal_bg = col_cfg["card_bg"]
        hover_bg = col_cfg["card_hover"]

        def on_hover(e: ft.ControlEvent, c=card, n=normal_bg, h=hover_bg):
            c.bgcolor = h if e.data == "true" else n
            c.update()

        card.on_hover = on_hover

    return card


def _make_count_badge(count: int, cfg: dict) -> ft.Container:
    """Создать бейдж-счётчик для заголовка колонки."""
    return ft.Container(
        content=ft.Text(
            str(count),
            size=12,
            weight=ft.FontWeight.BOLD,
            color=cfg["count_color"],
        ),
        bgcolor=cfg["count_bg"],
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=8, vertical=2),
        width=28,
        alignment=ft.alignment.center,
    )


def _make_column(
    status: Status,
    departments: List[Department],
    on_status_click: Callable[[Department], None],
) -> ft.Container:
    """Создать одну колонку канбана."""
    cfg = _COLUMN_CONFIG[status]

    # Счётчик — только активные отделы (совпадает с формулой KPI)
    count = len(departments)
    count_badge = _make_count_badge(count, cfg)

    # Заголовок колонки
    header = ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    width=10,
                    height=10,
                    bgcolor=cfg["header_color"],
                    border_radius=5,
                ),
                ft.Text(
                    cfg["title"],
                    size=13,
                    weight=ft.FontWeight.BOLD,
                    color=cfg["header_color"],
                ),
                ft.Container(expand=True),
                count_badge,
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.only(left=12, right=12, top=10, bottom=10),
        border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"])),
    )

    # Карточки
    cards = [
        _make_card(dept, lambda d=dept: on_status_click(d), cfg)
        for dept in departments
    ]

    # Empty state для колонки
    if not cards:
        cards = [
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(ft.icons.INBOX_OUTLINED, size=24, color=COLORS["text_muted"]),
                        ft.Text("Пусто", size=12, color=COLORS["text_muted"]),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                    tight=True,
                ),
                padding=ft.padding.symmetric(vertical=24),
                alignment=ft.alignment.center,
            )
        ]

    cards_column = ft.Column(
        controls=cards,
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    # Колонка целиком
    return ft.Container(
        content=ft.Column(
            controls=[header, cards_column],
            spacing=0,
            expand=True,
        ),
        expand=1,
        bgcolor=cfg["col_bg"],
        border=ft.border.all(1, COLORS["border"]),
        border_radius=10,
        margin=ft.margin.symmetric(horizontal=4),
    )


def create_department_table(
    page: ft.Page,
    departments: List[Department],
    on_status_change: Callable[[Department], None] = None,
) -> ft.Container:
    """
    Создать kanban-доску с тремя колонками по статусам.
    Возвращает контейнер с expand=True.
    """
    # Храним ссылки для rebuild / filter
    page._kanban_departments = departments
    page._kanban_on_status_change = on_status_change

    def handle_status_click(dept: Department):
        if not dept.is_active:
            return
        dept.toggle_status()
        if on_status_change:
            on_status_change(dept)
        # Перерисовать всю доску
        _rebuild_kanban(page)

    page._kanban_handle_click = handle_status_click

    # Распределяем отделы по колонкам
    kanban_row = _build_kanban_row(departments, handle_status_click)

    # Контейнер канбана — expand=True чтобы заполнить высоту
    kanban_container = ft.Container(
        content=kanban_row,
        expand=True,
        padding=ft.padding.symmetric(horizontal=2),
    )

    page.kanban_container = kanban_container
    return kanban_container


def _build_kanban_row(
    departments: List[Department],
    on_status_click: Callable[[Department], None],
    filter_query: str = "",
) -> ft.Row:
    """Построить Row из трёх колонок канбана."""
    q = filter_query.strip().lower()

    columns = []
    for status in _COLUMN_ORDER:
        # Фильтруем отделы данного статуса — только активные (совпадает с KPI)
        col_depts = [
            d for d in departments
            if d.status == status and d.is_active and (not q or q in d.name.lower())
        ]
        columns.append(_make_column(status, col_depts, on_status_click))

    return ft.Row(
        controls=columns,
        spacing=0,
        expand=True,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )


def _rebuild_kanban(page: ft.Page) -> None:
    """Перерисовать канбан-доску на месте."""
    if not hasattr(page, "kanban_container"):
        return
    departments = page._kanban_departments
    handle_click = page._kanban_handle_click

    # Получаем текущий поисковый запрос
    query = ""
    if hasattr(page, "search_field") and page.search_field.value:
        query = page.search_field.value

    kanban_row = _build_kanban_row(departments, handle_click, query)
    page.kanban_container.content = kanban_row
    page.kanban_container.update()


def rebuild_department_table(
    page: ft.Page,
    departments: List[Department],
    on_status_change: Callable[[Department], None] = None,
) -> None:
    """Полная пересборка канбана (после редактирования списка отделов)."""
    page._kanban_departments = departments
    if on_status_change:
        page._kanban_on_status_change = on_status_change
        # Пересоздаём handler с новым on_status_change
        def handle_status_click(dept: Department):
            if not dept.is_active:
                return
            dept.toggle_status()
            if on_status_change:
                on_status_change(dept)
            _rebuild_kanban(page)
        page._kanban_handle_click = handle_status_click
    _rebuild_kanban(page)


def filter_table(page: ft.Page, query: str) -> None:
    """Фильтровать карточки канбана по поисковому запросу."""
    if not hasattr(page, "kanban_container"):
        return
    departments = page._kanban_departments
    handle_click = page._kanban_handle_click

    q = query.strip().lower()

    # Проверяем, есть ли хоть один результат
    if q:
        matches = [d for d in departments if d.is_active and q in d.name.lower()]
        if not matches:
            # Показываем empty-state во всех колонках
            empty_columns = []
            for status in _COLUMN_ORDER:
                cfg = _COLUMN_CONFIG[status]
                header = ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Container(
                                width=10, height=10,
                                bgcolor=cfg["header_color"],
                                border_radius=5,
                            ),
                            ft.Text(
                                cfg["title"],
                                size=13,
                                weight=ft.FontWeight.BOLD,
                                color=cfg["header_color"],
                            ),
                            ft.Container(expand=True),
                            _make_count_badge(0, cfg),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.padding.only(left=12, right=12, top=10, bottom=10),
                    border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"])),
                )
                empty_state = ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.icons.SEARCH_OFF, size=28, color=COLORS["text_muted"]),
                            ft.Text("Ничего не найдено", size=13, color=COLORS["text_secondary"]),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=6,
                        tight=True,
                    ),
                    padding=ft.padding.symmetric(vertical=32),
                    alignment=ft.alignment.center,
                    expand=True,
                )
                col = ft.Container(
                    content=ft.Column(
                        controls=[header, empty_state],
                        spacing=0,
                        expand=True,
                    ),
                    expand=1,
                    bgcolor=cfg["col_bg"],
                    border=ft.border.all(1, COLORS["border"]),
                    border_radius=10,
                    margin=ft.margin.symmetric(horizontal=4),
                )
                empty_columns.append(col)

            kanban_row = ft.Row(
                controls=empty_columns,
                spacing=0,
                expand=True,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
            page.kanban_container.content = kanban_row
            page.kanban_container.update()
            return

    # Обычная фильтрация
    kanban_row = _build_kanban_row(departments, handle_click, query)
    page.kanban_container.content = kanban_row
    page.kanban_container.update()
