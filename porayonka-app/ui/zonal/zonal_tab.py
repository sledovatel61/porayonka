# ui/zonal/zonal_tab.py
# Вкладка "Зональные криминалисты" — ФАЗА 2.
# Сетка компактных плашек вместо раскрывающихся карточек.
# [DARK THEME] + ft.icons.* + hint_style (Flet 0.23.2)
import os
import flet as ft
from typing import List, Optional, Callable, Dict
from core.zonal_models import (
    ZonalCollection, ReportTemplate, Criminalist,
    ReportTemplateItem, ReportItemType, ReportData,
    CriminalistZone,
)
from core.zonal_data import (
    load_zonal_collection, save_zonal_collection,
    load_zonal_submissions, save_zonal_submissions,
    clear_zonal_submissions,
    get_initial_criminalists, get_report_data,
    load_zonal_templates, save_zonal_template,
    save_criminalists,
    get_criminalist_fill, get_non_submitters, build_non_submitters_text,
)
from core.constants import COLORS, INITIAL_DEPARTMENTS
from core.zonal_replacement import (
    normalize_zonal_criminalists,
    remove_criminalist_and_clean,
    apply_replacement_selection,
)
from .template_builder import create_template_builder
from .criminalist_tile import (
    create_criminalist_tile,
    create_criminalist_drag_feedback,
    create_criminalist_drag_placeholder,
    rebuild_tile_content,
)
from .form_input_modal import create_form_input_modal
from .add_criminalist_modal import create_add_criminalist_modal
from .criminalists_summary_panel import create_criminalists_summary_panel


def create_zonal_tab(page: ft.Page) -> ft.Column:
    """
    Создать вкладку 'Зональные'.
    Возвращает ft.Column с полным содержимым вкладки.
    """
    print("[ZONAL_TAB] Initializing zonal tab (phase 2: compact tiles)")

    collection = load_zonal_collection()
    if collection is None:
        collection = ZonalCollection(
            template=ReportTemplate(name="Новая форма"),
            criminalists=get_initial_criminalists(),
        )
        print("[ZONAL_TAB] Created new collection")
    else:
        if not collection.criminalists:
            collection.criminalists = get_initial_criminalists()
    normalize_zonal_criminalists(collection.criminalists)

    # Сохраняем ссылку для авто-сохранения при закрытии окна
    page._zonal_collection = collection

    print(f"[ZONAL_TAB] Criminalists: {len(collection.criminalists)}")
    print(f"[ZONAL_TAB] Active: {sum(1 for c in collection.criminalists if c.is_active)}")
    print(f"[ZONAL_TAB] Template items: {len(collection.template.items)}")

    dept_map = {d["id"]: d["name"] for d in INITIAL_DEPARTMENTS}

    # ── Константы раскладки плашек ─────────────────────────────
    # _TILES_PER_ROW пересчитывается динамически из page.width в
    # _calc_tiles_per_row(). Значение по умолчанию 4 — «средний экран».
    _TILE_SPACING = 16
    _TILE_WIDTH = 300        # см. criminalist_tile._TILE_WIDTH
    _TILE_HEIGHT = 380       # см. criminalist_tile._TILE_HEIGHT
    _TILE_RADIUS = 14        # см. criminalist_tile._TILE_RADIUS
    _TAB_HORIZONTAL_PADDING = 40  # main.py: padding=20 слева и справа

    tiles_per_row_ref: Dict = {"value": 4}

    def _calc_tiles_per_row(width: Optional[float]) -> int:
        if width is None or width <= 0:
            return 4
        available = max(0.0, width - _TAB_HORIZONTAL_PADDING)
        # (n * TILE_WIDTH) + ((n - 1) * SPACING) <= available
        # n <= (available + SPACING) / (TILE_WIDTH + SPACING)
        n = int((available + _TILE_SPACING) // (_TILE_WIDTH + _TILE_SPACING))
        return max(3, min(6, n or 3))

    # ── Состояние UI ────────────────────────────────────────────
    tiles: Dict[int, ft.Container] = {}          # id -> плашка
    crim_summary_ref: Dict = {"panel": None, "is_expanded": False}
    template_builder_ref: Dict = {"control": None, "is_expanded": False}
    filter_ref: Dict = {"value": "all"}          # all | pending | inactive
    tiles_column_ref: Dict = {"control": None}

    # ── Колбэки для плашек ──────────────────────────────────────
    callbacks = {
        "on_open_form": lambda c: _on_open_form(c),
        "on_edit": lambda c: _on_edit_criminalist(c),
        "on_toggle_active": lambda c: _on_toggle_active(c),
        "on_delete": lambda c: _on_delete_criminalist(c),
    }

    def autosave():
        try:
            save_zonal_collection(collection)
        except Exception as e:
            print(f"[ZONAL_TAB] Autosave error: {e}")

    def _refresh_crim_summary():
        if crim_summary_ref["panel"] is not None:
            new_panel = create_criminalists_summary_panel(
                collection, crim_summary_ref, _refresh_crim_summary
            )
            crim_summary_ref["panel"].controls = new_panel.controls
            try:
                crim_summary_ref["panel"].update()
            except Exception:
                pass

    def _refresh_summary():
        """Обновить сводку по криминалистам."""
        _refresh_crim_summary()

    def _refresh_tile(crim: Criminalist):
        tile = tiles.get(crim.id)
        if tile is None:
            return
        rebuild_tile_content(tile, crim, collection, dept_map, callbacks)

    def refresh_all_tiles():
        """Обновить все плашки (например, после изменения шаблона)."""
        print("[ZONAL_TAB] Refreshing all tiles...")
        for c in collection.criminalists:
            tile = tiles.get(c.id)
            if tile is None:
                continue
            rebuild_tile_content(tile, c, collection, dept_map, callbacks)
        _refresh_summary()
        _apply_filter()

    # ── Drag-and-drop плашек ────────────────────────────────────
    # В Flet 0.23.2 DragTarget сообщает source только через src_id. Храним
    # текущий id ещё и локально: это даёт безопасный fallback при работе с
    # тестовой page-заглушкой и при завершении drag вне target.
    _DRAG_GROUP = "zonal-criminalist-tile"
    drag_state: Dict = {
        "source_id": None,
        "indicator": None,
        "indicator_target": None,
    }

    def _reset_drag_tile(source_id=None):
        """Вернуть исходной плашке обычные border/opacity после drag."""
        source_id = source_id if source_id is not None else drag_state["source_id"]
        if source_id is None:
            return
        source = next((c for c in collection.criminalists if c.id == source_id), None)
        tile = tiles.get(source_id)
        if source is not None and tile is not None:
            rebuild_tile_content(tile, source, collection, dept_map, callbacks)

    def _hide_insertion_indicator():
        indicator = drag_state["indicator"]
        target = drag_state["indicator_target"]
        drag_state["indicator"] = None
        drag_state["indicator_target"] = None
        if indicator is None:
            return
        indicator.visible = False
        if target is not None:
            try:
                target.update()
            except Exception:
                pass

    def _set_insertion_indicator(indicator, target, insert_after: bool):
        """Показать 3 px линию перед/после плашки назначения."""
        if drag_state["indicator"] is not indicator:
            _hide_insertion_indicator()
            drag_state["indicator"] = indicator
            drag_state["indicator_target"] = target
        indicator.left = None if insert_after else 0
        indicator.right = 0 if insert_after else None
        indicator.visible = True
        try:
            target.update()
        except Exception:
            pass

    def _is_after_target(e) -> bool:
        """Правая половина target означает вставку после него."""
        try:
            return float(e.x) >= (_TILE_WIDTH / 2)
        except (AttributeError, TypeError, ValueError):
            return False

    def _drag_source_id(e=None):
        """Получить Criminalist.id из Draggable.data или локального состояния."""
        try:
            source_control = page.get_control(e.src_id)
            return int(source_control.data)
        except Exception:
            return drag_state["source_id"]

    def _on_drag_start(criminalist: Criminalist):
        def handler(e=None):
            _hide_insertion_indicator()
            previous_source_id = drag_state["source_id"]
            if previous_source_id is not None and previous_source_id != criminalist.id:
                _reset_drag_tile(previous_source_id)
            drag_state["source_id"] = criminalist.id
            # Визуальная обратная связь задаётся отдельными
            # content_when_dragging/content_feedback. Исходную tile здесь
            # не меняем: при отмене drop она сразу возвращается без залипания
            # opacity или border.
        return handler

    def _on_drag_complete(criminalist: Criminalist):
        def handler(e=None):
            _hide_insertion_indicator()
            _reset_drag_tile(criminalist.id)
            if drag_state["source_id"] == criminalist.id:
                drag_state["source_id"] = None
        return handler

    def _move_criminalist(source_id: int, target_id: int, insert_after: bool):
        """Переместить элемент в глобальном порядке collection.criminalists."""
        if source_id is None or source_id == target_id:
            return False
        source = next((c for c in collection.criminalists if c.id == source_id), None)
        target = next((c for c in collection.criminalists if c.id == target_id), None)
        if source is None or target is None:
            return False

        # Индекс назначения ищем после извлечения source: так не возникает
        # off-by-one при переносе вправо в том же ряду.
        collection.criminalists.remove(source)
        target_index = collection.criminalists.index(target)
        collection.criminalists.insert(target_index + (1 if insert_after else 0), source)
        return True

    def _on_drop(target_criminalist: Criminalist):
        def handler(e):
            source_id = _drag_source_id(e)
            insert_after = _is_after_target(e)
            _hide_insertion_indicator()
            _reset_drag_tile(source_id)
            drag_state["source_id"] = None

            if not _move_criminalist(source_id, target_criminalist.id, insert_after):
                return

            # Список сериализуется в текущей последовательности, поэтому это
            # сохраняет единый порядок и при активном фильтре.
            save_criminalists(collection.criminalists)
            autosave()
            _apply_filter()
            print(f"[ZONAL_TAB] Criminalist moved: {source_id} -> "
                  f"{'after' if insert_after else 'before'} {target_criminalist.id}")
        return handler

    def _build_draggable_target(criminalist: Criminalist, tile: ft.Container):
        """Обернуть плашку в Draggable + DragTarget без изменения её размера."""
        indicator = ft.Container(
            width=3,
            height=_TILE_HEIGHT,
            bgcolor=COLORS.get("btn_save", "#3b82f6"),
            border_radius=2,
            visible=False,
            top=0,
        )
        draggable = ft.Draggable(
            group=_DRAG_GROUP,
            data=str(criminalist.id),
            content=tile,
            content_when_dragging=create_criminalist_drag_placeholder(criminalist),
            content_feedback=create_criminalist_drag_feedback(criminalist),
            on_drag_start=_on_drag_start(criminalist),
            on_drag_complete=_on_drag_complete(criminalist),
        )
        stack = ft.Stack(
            controls=[draggable, indicator],
            width=_TILE_WIDTH,
            height=_TILE_HEIGHT,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )
        # DragTarget сам не имеет border_radius. Контейнер фиксированного
        # размера задаёт единый clip для обычной плашки, placeholder и линии
        # вставки, не меняя constraints Row/сетки.
        drag_surface = ft.Container(
            content=stack,
            width=_TILE_WIDTH,
            height=_TILE_HEIGHT,
            border_radius=_TILE_RADIUS,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )
        target_ref: Dict = {"control": None}

        def on_will_accept(e):
            if str(getattr(e, "data", "")).lower() == "true":
                _set_insertion_indicator(indicator, target_ref["control"], False)

        def on_move(e):
            _set_insertion_indicator(
                indicator, target_ref["control"], _is_after_target(e)
            )

        def on_leave(e):
            if drag_state["indicator"] is indicator:
                _hide_insertion_indicator()

        target = ft.DragTarget(
            group=_DRAG_GROUP,
            content=drag_surface,
            on_will_accept=on_will_accept,
            on_move=on_move,
            on_leave=on_leave,
        )
        target_ref["control"] = target
        target.on_accept = _on_drop(criminalist)
        return target

    # ── Раскладка плашек фиксированными рядами ─────────────────
    def _build_tile_rows(visible_criminalists: List[Criminalist]):
        """Разбить видимых криминалистов на ряды по tiles_per_row_ref."""
        n_per_row = max(1, tiles_per_row_ref["value"])
        rows = []
        if not visible_criminalists:
            rows.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.icons.INBOX, size=18,
                                    color=COLORS.get("text_muted", "#64748b")),
                            ft.Text(
                                "Нет криминалистов по выбранному фильтру",
                                size=12,
                                color=COLORS.get("text_secondary", "#94a3b8"),
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        tight=True,
                    ),
                    height=44,
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    bgcolor=COLORS.get("card", "#15202e"),
                    border=ft.border.all(1, COLORS.get("border", "#334155")),
                    border_radius=10,
                )
            )
            return rows
        for i in range(0, len(visible_criminalists), n_per_row):
            chunk = visible_criminalists[i:i + n_per_row]
            row_controls = []
            for c in chunk:
                tile = tiles.get(c.id)
                if tile is None:
                    tile = create_criminalist_tile(c, collection, dept_map, callbacks)
                    tiles[c.id] = tile
                row_controls.append(_build_draggable_target(c, tile))
            rows.append(
                ft.Row(
                    controls=row_controls,
                    spacing=_TILE_SPACING,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    alignment=ft.MainAxisAlignment.CENTER,
                    tight=True,
                )
            )
        return rows

    # ── Фильтрация ─────────────────────────────────────────────
    def _apply_filter():
        """Пересобрать ряды плашек по фильтру (без полной перерисовки таба)."""
        fmode = filter_ref["value"]
        visible = []
        for c in collection.criminalists:
            if fmode == "pending" and get_criminalist_fill(collection, c)["percent"] >= 100:
                continue
            if fmode == "inactive" and c.is_active:
                continue
            visible.append(c)

        tiles_column = tiles_column_ref["control"]
        if tiles_column is not None:
            tiles_column.controls = _build_tile_rows(visible)
            try:
                tiles_column.update()
            except Exception:
                pass

    def _set_filter(value: str):
        filter_ref["value"] = value
        _restyle_filter_buttons()
        _apply_filter()

    # ── Действия с плашками ─────────────────────────────────────
    def _on_toggle_active(crim: Criminalist):
        crim.is_active = not crim.is_active
        save_criminalists(collection.criminalists)
        autosave()
        _refresh_tile(crim)
        _refresh_summary()
        _apply_filter()
        from ui.toast import show_toast
        status = "включен" if crim.is_active else "отключен"
        show_toast(page, f"{crim.full_name} — {status}", icon=ft.icons.VISIBILITY if crim.is_active else ft.icons.CANCEL)

    def _on_open_form(crim: Criminalist):
        dialog = create_form_input_modal(
            page=page,
            criminalist=crim,
            collection=collection,
            dept_map=dept_map,
            on_saved=_on_form_saved,
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def _on_form_saved(crim: Criminalist):
        _refresh_tile(crim)
        _refresh_summary()

    def _on_edit_criminalist(crim: Criminalist):
        def handle_save(full_name: str, note: str, department_ids: list,
                        replacement_ids: list):
            crim.full_name = full_name
            crim.note = note
            crim.zone.department_ids = department_ids
            apply_replacement_selection(
                collection.criminalists, crim.id, list(replacement_ids or [])
            )
            save_criminalists(collection.criminalists)
            autosave()
            _refresh_tile(crim)
            _refresh_summary()
            _apply_filter()
            from ui.toast import show_toast
            show_toast(page, f"Сохранено: {full_name}", icon=ft.icons.EDIT)

        dialog = create_add_criminalist_modal(
            page=page,
            criminalist=crim,
            on_save=handle_save,
            on_delete=lambda c: _on_delete_criminalist(c),
            all_criminalists=collection.criminalists,
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def _on_delete_criminalist(criminalist: Criminalist):
        def confirm_delete(e=None):
            collection.criminalists = remove_criminalist_and_clean(
                collection.criminalists, criminalist.id
            )
            tiles.pop(criminalist.id, None)
            save_criminalists(collection.criminalists)
            autosave()
            _refresh_summary()
            _apply_filter()
            dialog.open = False
            page.update()
            from ui.toast import show_toast
            show_toast(page, f"Удален: {criminalist.full_name}", icon=ft.icons.DELETE)

        def cancel_delete(e=None):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            modal=True,
            bgcolor=COLORS["primary_light"],
            title=ft.Text("Удаление криминалиста", size=16,
                          weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            content=ft.Text(
                f"Вы уверены, что хотите удалить {criminalist.full_name}?\n\n"
                f"Все данные по этому криминалисту будут утеряны.",
                size=13,
                color=COLORS["text"],
            ),
            actions=[
                ft.TextButton("Отмена", on_click=cancel_delete),
                ft.ElevatedButton(
                    "Удалить",
                    bgcolor="#dc2626",
                    color=COLORS["text_light"],
                    on_click=confirm_delete,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def _on_add_criminalist():
        def handle_save(full_name: str, note: str, department_ids: list,
                        replacement_ids: list):
            max_id = max((c.id for c in collection.criminalists), default=0)
            new_id = max_id + 1
            new_criminalist = Criminalist(
                id=new_id,
                full_name=full_name,
                note=note,
                is_active=True,
                zone=CriminalistZone(criminalist_id=new_id, department_ids=department_ids),
                replacement_ids=[],
            )
            collection.criminalists.append(new_criminalist)
            apply_replacement_selection(
                collection.criminalists, new_id, list(replacement_ids or [])
            )
            save_criminalists(collection.criminalists)
            autosave()
            _refresh_summary()
            _apply_filter()
            from ui.toast import show_toast
            show_toast(page, f"Добавлен: {full_name}", icon=ft.icons.ADD)

        dialog = create_add_criminalist_modal(
            page=page,
            criminalist=None,
            on_save=handle_save,
            all_criminalists=collection.criminalists,
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def _on_copy_non_submitters(e=None):
        text = build_non_submitters_text(collection, dept_map)
        try:
            page.set_clipboard(text)
        except Exception as ex:
            print(f"[ZONAL_TAB] Clipboard error: {ex}")
        non = get_non_submitters(collection)
        from ui.toast import show_toast
        show_toast(page, f"Скопирован список не сдавших: {len(non)}", icon=ft.icons.CONTENT_COPY)

    # ── Шаблон / экспорт / сброс ───────────────────────────────
    def on_template_changed():
        autosave()
        refresh_all_tiles()

    def on_template_save(name: str):
        try:
            collection.template.name = name
            save_zonal_template(collection.template)
            autosave()
            from ui.toast import show_toast
            show_toast(page, f"Шаблон '{name}' сохранен", icon=ft.icons.SAVE)
        except Exception as e:
            print(f"[ZONAL_TAB] Template save error: {e}")
            from ui.toast import show_error_toast
            show_error_toast(page, f"Ошибка: {e}")

    def on_template_load():
        _open_template_loader()

    def _load_template_with_warning(t: ReportTemplate):
        has_data = len(collection.submissions) > 0
        if has_data:
            def confirm_load(e=None):
                collection.submissions.clear()
                clear_zonal_submissions()
                collection.template = t
                save_zonal_collection(collection)
                _rebuild_template_builder()
                refresh_all_tiles()
                dialog.open = False
                page.update()
                from ui.toast import show_toast
                show_toast(page, f"Шаблон '{t.name}' загружен (данные сброены)", icon=ft.icons.FOLDER)

            def cancel_load(e=None):
                dialog.open = False
                page.update()

            inactive_count = sum(1 for c in collection.criminalists if not c.is_active)
            inactive_note = f"\n\n({inactive_count} криминалистов отключено)" if inactive_count else ""
            dialog = ft.AlertDialog(
                modal=True,
                bgcolor=COLORS["primary_light"],
                title=ft.Text("Загрузка шаблона", size=16,
                              weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                content=ft.Text(
                    f"Шаблон '{t.name}' загрузит {len(t.items)} пунктов.\n\n"
                    f"Текущие данные будут удалены!{inactive_note}",
                    size=13,
                    color=COLORS["text"],
                ),
                actions=[
                    ft.TextButton("Отмена", on_click=cancel_load),
                    ft.ElevatedButton("Загрузить", bgcolor=COLORS["btn_save"],
                                      color=COLORS["text_light"], on_click=confirm_load),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.overlay.append(dialog)
            dialog.open = True
            page.update()
        else:
            collection.template = t
            autosave()
            _rebuild_template_builder()
            refresh_all_tiles()
            from ui.toast import show_toast
            show_toast(page, f"Шаблон '{t.name}' загружен", icon=ft.icons.FOLDER)

    def _open_template_loader():
        templates = load_zonal_templates()
        if not templates:
            from ui.toast import show_toast
            show_toast(page, "Нет сохраненных шаблонов", icon=ft.icons.FOLDER)
            return

        def _select_template(t):
            _load_template_with_warning(t)

        def _delete_template(t):
            from core.zonal_data import delete_zonal_template
            try:
                delete_zonal_template(t.name)
                dialog.open = False
                page.update()
                from ui.toast import show_toast
                show_toast(page, f"Шаблон '{t.name}' удален", icon=ft.icons.DELETE)
            except Exception as e:
                from ui.toast import show_error_toast
                show_error_toast(page, f"Ошибка удаления: {e}")

        items_list = ft.Column(spacing=8)
        for t in templates:
            template_row = ft.Row(
                controls=[
                    ft.ElevatedButton(
                        text=f"{t.name} ({len(t.items)} пунктов)",
                        icon=ft.icons.FOLDER_OPEN,
                        style=ft.ButtonStyle(
                            bgcolor=COLORS["card"],
                            color=COLORS["text"],
                            shape=ft.RoundedRectangleBorder(radius=8),
                        ),
                        expand=True,
                        on_click=lambda e, t=t: _select_template(t),
                    ),
                    ft.IconButton(
                        icon=ft.icons.DELETE_OUTLINE,
                        icon_color="#ef4444",
                        tooltip="Удалить шаблон",
                        on_click=lambda e, t=t: _delete_template(t),
                    ),
                ],
                spacing=4,
            )
            items_list.controls.append(template_row)

        def _close_dialog(e=None):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            modal=True,
            bgcolor=COLORS["primary_light"],
            title=ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.icons.FOLDER, size=18, color="white"),
                        ft.Text("Выбор шаблона", size=16, weight=ft.FontWeight.BOLD, color="white"),
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
            content=ft.Container(
                content=items_list,
                width=450,
                height=min(len(templates) * 70, 400),
                bgcolor=COLORS["primary_light"],
                padding=ft.padding.all(12),
            ),
            actions=[ft.TextButton("Отмена", on_click=_close_dialog)],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=12),
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def on_template_clear():
        collection.template.items.clear()
        collection.template.name = "Новая форма"
        collection.template.use_departments_mode = False
        # Один пустой пункт по умолчанию — дальше форма расширяется
        # кнопкой "Добавить пункт"
        collection.template.items.append(
            ReportTemplateItem.create(
                name="Новый пункт",
                item_type=ReportItemType.NUMERICAL,
                unit="шт.",
                order=0,
            )
        )
        autosave()
        _rebuild_template_builder()
        refresh_all_tiles()
        from ui.toast import show_toast
        show_toast(page, "Форма очищена", icon=ft.icons.DELETE)

    def on_reset_data():
        has_data = len(collection.submissions) > 0
        if not has_data:
            from ui.toast import show_toast
            show_toast(page, "Данные уже пусты", icon=ft.icons.INFO)
            return

        def confirm_reset(e=None):
            collection.submissions.clear()
            clear_zonal_submissions()
            autosave()
            refresh_all_tiles()
            dialog.open = False
            page.update()
            from ui.toast import show_toast
            show_toast(page, "Данные сброшены, шаблон сохранен", icon=ft.icons.CLEANING_SERVICES)

        def cancel_reset(e=None):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            modal=True,
            bgcolor=COLORS["primary_light"],
            title=ft.Text("Сброс данных", size=16,
                          weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            content=ft.Text(
                f"Очистить все введенные данные ({len(collection.submissions)} записей)?\n\n"
                f"Структура шаблона будет сохранена.",
                size=13,
                color=COLORS["text"],
            ),
            actions=[
                ft.TextButton("Отмена", on_click=cancel_reset),
                ft.ElevatedButton("Сбросить", bgcolor="#f59e0b",
                                  color=COLORS["text_light"], on_click=confirm_reset),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def _on_clear_all_data():
        """
        Кнопка тулбара «Очистить все данные».
        Сбрасывает ТОЛЬКО collection.submissions.
        Шаблон (template), список криминалистов и их is_active сохраняются.
        """
        filled = len(collection.submissions)
        if filled == 0:
            from ui.toast import show_toast
            show_toast(page, "Данные уже пусты", icon=ft.icons.INFO_OUTLINE)
            return

        def confirm(e=None):
            collection.submissions.clear()
            clear_zonal_submissions()
            autosave()
            refresh_all_tiles()
            dialog.open = False
            page.update()
            from ui.toast import show_toast
            show_toast(page, "Все введённые данные очищены",
                       icon=ft.icons.CLEANING_SERVICES)
            print(f"[ZONAL_TAB] Submissions cleared: {filled} records")

        def cancel(e=None):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            modal=True,
            bgcolor=COLORS["primary_light"],
            title=ft.Row(
                controls=[
                    ft.Icon(ft.icons.WARNING_AMBER_ROUNDED, size=20, color="#f59e0b"),
                    ft.Text("Очистить все данные", size=16,
                            weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                ],
                spacing=8,
            ),
            content=ft.Container(
                width=420,
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "Очистить все введённые данные? "
                            "Структура формы и список криминалистов сохранятся.",
                            size=13,
                            color=COLORS["text"],
                        ),
                        ft.Container(height=8),
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Text(f"Будет удалено записей: {filled}",
                                            size=12, color=COLORS["in_progress_text"]),
                                    ft.Text(
                                        f"Сохранится: шаблон «{collection.template.name}» "
                                        f"({len(collection.template.items)} пунктов), "
                                        f"криминалистов: {len(collection.criminalists)}, "
                                        f"их активность.",
                                        size=12, color=COLORS["text_secondary"],
                                    ),
                                ],
                                spacing=4,
                                tight=True,
                            ),
                            bgcolor=COLORS["primary_light"],
                            border=ft.border.all(1, COLORS["border"]),
                            border_radius=8,
                            padding=ft.padding.all(10),
                        ),
                    ],
                    spacing=0,
                    tight=True,
                ),
            ),
            actions=[
                ft.TextButton("Отмена", on_click=cancel),
                ft.ElevatedButton(
                    "Очистить",
                    icon=ft.icons.CLEANING_SERVICES,
                    bgcolor="#f59e0b",
                    color=COLORS["text_light"],
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                    on_click=confirm,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=14),
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def on_departments_mode_changed(use_dept_mode: bool):
        collection.template.use_departments_mode = use_dept_mode
        autosave()
        refresh_all_tiles()

    def on_export_excel():
        """Экспорт через FilePicker — пользователь выбирает место сохранения."""
        from core.zonal_exporter import ZonalExcelExporter
        from ui.toast import show_export_toast, show_error_toast

        def _on_file_picked(e: ft.FilePickerResultEvent):
            if not e.path:
                return
            try:
                ZonalExcelExporter().export(collection, e.path)
                show_export_toast(page, "Зональные Excel")
                page._last_export_path["value"] = e.path
                # Показать кнопку "Открыть отчёт" в тулбаре
                page._open_report_btn.visible = True
                try:
                    page._open_report_btn.update()
                except Exception:
                    page.update()
            except Exception as ex:
                print(f"[ZONAL_TAB] Export error: {ex}")
                show_error_toast(page, f"Ошибка экспорта: {ex}")

        # Создаём FilePicker один раз и добавляем в overlay
        if not hasattr(page, "_zonal_file_picker"):
            picker = ft.FilePicker(on_result=_on_file_picked)
            page.overlay.append(picker)
            page._zonal_file_picker = picker
            page.update()  # ВАЖНО: обновить page после добавления в overlay

        from datetime import datetime as dt
        default_name = f"zonal_{dt.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        page._zonal_file_picker.save_file(
            dialog_title="Сохранить отчёт Excel",
            file_name=default_name,
            allowed_extensions=["xlsx"],
        )

    # ── Фаза 40: печатная PDF-выгрузка зональных ────────────────
    # Отдельный picker/путь/кнопка — не смешиваем с Excel-экспортом.
    pdf_state_ref = {"path": None, "url": None, "web": False}
    page._zonal_pdf_state = pdf_state_ref

    def _web_mode_export():
        return (os.environ.get("PORAYONKA_WEB") == "1"
                or bool(os.environ.get("FLET_ASSETS_DIR")))

    def _open_last_pdf():
        state = page._zonal_pdf_state
        if state.get("web"):
            url = state.get("url")
            if not url:
                from ui.toast import show_error_toast
                show_error_toast(page, "PDF не найден в web-каталоге")
                return
            try:
                page.launch_url(url)
            except Exception as ex:
                print(f"[ZONAL_TAB] Open PDF URL error: {ex}")
                from ui.toast import show_error_toast
                show_error_toast(page, f"Ошибка открытия PDF: {ex}")
            return
        path = state.get("path")
        if not path or not os.path.exists(path):
            from ui.toast import show_error_toast
            show_error_toast(page, "PDF-файл удалён или недоступен")
            return
        import subprocess, sys as _sys_os
        try:
            if _sys_os.platform == "win32":
                os.startfile(path)
            elif _sys_os.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as ex:
            print(f"[ZONAL_TAB] Open PDF error: {ex}")
            from ui.toast import show_error_toast
            show_error_toast(page, f"Ошибка открытия PDF: {ex}")

    def _on_pdf_picked(e):
        if not getattr(e, "path", None):
            return
        try:
            from core.zonal_distribution_exporter import ZonalDistributionPdfExporter
            ZonalDistributionPdfExporter().export(collection, e.path)
        except Exception as ex:
            print(f"[ZONAL_TAB] PDF export error: {ex}")
            from ui.toast import show_error_toast
            show_error_toast(page, f"Ошибка выгрузки PDF: {ex}")
            return
        pdf_state_ref["path"] = e.path
        pdf_state_ref["url"] = None
        pdf_state_ref["web"] = False
        open_pdf_btn.visible = True
        try:
            open_pdf_btn.update()
        except Exception:
            page.update()
        from ui.toast import show_export_toast
        show_export_toast(page, "Зональные PDF")

    def _on_export_pdf(e=None):
        """Выгрузить зональных в PDF (desktop: save_file, web: assets/downloads)."""
        from core.zonal_distribution_exporter import (
            ZonalDistributionPdfExporter,
            pdf_filename,
            write_web_pdf,
        )
        exporter = ZonalDistributionPdfExporter()
        filename = pdf_filename()

        if _web_mode_export():
            try:
                data = exporter.export_bytes(collection)
                final_path, url = write_web_pdf(filename, data)
                pdf_state_ref["path"] = final_path
                pdf_state_ref["url"] = url
                pdf_state_ref["web"] = True
                open_pdf_btn.visible = True
                try:
                    open_pdf_btn.update()
                except Exception:
                    page.update()
                from ui.toast import show_export_toast
                show_export_toast(page, "Зональные PDF")
                try:
                    page.launch_url(url)
                except Exception as ex:
                    print(f"[ZONAL_TAB] PDF web launch error: {ex}")
            except Exception as ex:
                print(f"[ZONAL_TAB] PDF export error: {ex}")
                from ui.toast import show_error_toast
                show_error_toast(page, f"Ошибка выгрузки PDF: {ex}")
            return

        def _pick_pdf():
            if not hasattr(page, "_zonal_pdf_picker"):
                picker = ft.FilePicker(on_result=_on_pdf_picked)
                page.overlay.append(picker)
                page._zonal_pdf_picker = picker
                page.update()  # ВАЖНО: FilePicker монтируется до save_file
            page._zonal_pdf_picker.save_file(
                dialog_title="Сохранить выгрузку зональных PDF",
                file_name=filename,
                allowed_extensions=["pdf"],
            )

        _pick_pdf()

    # Кнопка "Открыть PDF" — отдельная от Excel, появляется после выгрузки
    open_pdf_btn = ft.ElevatedButton(
        text="Открыть PDF",
        icon=ft.icons.PICTURE_AS_PDF,
        bgcolor=COLORS["received"],
        color=COLORS["text_light"],
        height=38,
        visible=False,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.padding.symmetric(horizontal=14),
        ),
        on_click=lambda e: _open_last_pdf(),
        tooltip="Открыть последнюю выгрузку зональных PDF",
    )
    page._zonal_open_pdf_btn = open_pdf_btn

    # Кнопка "Открыть отчёт" — появляется после экспорта
    open_report_btn = ft.ElevatedButton(
        text="Открыть отчёт",
        icon=ft.icons.OPEN_IN_NEW,
        bgcolor=COLORS["received"],
        color=COLORS["text_light"],
        height=38,
        visible=False,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.padding.symmetric(horizontal=14),
        ),
        on_click=lambda e: _open_last_export(),
        tooltip="Открыть последний сохранённый отчёт",
    )
    page._open_report_btn = open_report_btn
    page._last_export_path = {"value": None}

    def _open_last_export():
        import subprocess, sys, os
        path = page._last_export_path.get("value")
        if not path or not os.path.exists(path):
            return
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as ex:
            print(f"[ZONAL_TAB] Open file error: {ex}")

    def _rebuild_template_builder():
        # Template builder теперь в модалке — пересоздаётся при открытии
        pass

    # ── Построение UI ───────────────────────────────────────────
    # Template builder открывается в модалке по кнопке-шестерёнке
    template_builder_ref["control"] = None  # будет создан по требованию

    # ── Модалка настройки сбора данных ───────────────────────────
    def _open_template_settings(e=None):
        """Открыть модалку с конструктором шаблонов."""
        # Адаптивная ширина модалки — под ширину окна приложения
        try:
            _win_w = page.window.width or 1280
        except Exception:
            _win_w = 1280
        dlg_width = max(650, min(900, int(_win_w * 0.45)))

        content_holder = ft.Container(
            width=dlg_width,
            bgcolor=COLORS["card"],
            padding=ft.padding.all(0),
        )

        def _build_builder():
            return create_template_builder(
                page=page,
                collection=collection,
                on_template_changed=on_template_changed,
                on_save=on_template_save,
                on_load=on_template_load,
                on_clear=_on_clear_inside,
                on_reset_data=on_reset_data,
                on_departments_mode_changed=on_departments_mode_changed,
                template_builder_ref=template_builder_ref,
            )

        def _on_clear_inside():
            # Очистить шаблон и сразу пересоздать содержимое
            # открытой модалки (без закрытия/переоткрытия)
            on_template_clear()
            content_holder.content = _build_builder()
            try:
                content_holder.update()
            except Exception:
                page.update()

        content_holder.content = _build_builder()

        def _close_dialog(e=None):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            modal=True,
            bgcolor=COLORS["card"],
            title=ft.Row(
                controls=[
                    ft.Icon(ft.icons.SETTINGS_OUTLINED, size=20, color=COLORS["text"]),
                    ft.Text("Настройка сбора данных", size=16,
                            weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                    ft.Container(expand=True),
                    ft.IconButton(
                        icon=ft.icons.CLOSE,
                        icon_color=COLORS["text_secondary"],
                        icon_size=18,
                        on_click=_close_dialog,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            content=content_holder,
            actions=[],
            shape=ft.RoundedRectangleBorder(radius=12),
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    # Регистрируем в page для доступа из header
    page._open_template_settings = _open_template_settings

    # Инфо-строка о текущем шаблоне
    def _template_info_text():
        name = collection.template.name or "Новая форма"
        n_items = len(collection.template.items)
        dept_mode = "да" if collection.template.use_departments_mode else "нет"
        return f"{name} · {n_items} пунктов · по отделам: {dept_mode}"

    template_info = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.icons.DESCRIPTION_OUTLINED, size=14,
                        color=COLORS["text_muted"]),
                ft.Text(
                    _template_info_text(),
                    size=11,
                    color=COLORS["text_muted"],
                    italic=True,
                ),
            ],
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        ),
        padding=ft.padding.only(left=4, top=2, bottom=2),
    )
    filter_buttons: Dict[str, ft.Container] = {}

    def _filter_count(value: str) -> int:
        if value == "all":
            return len(collection.criminalists)
        if value == "pending":
            return sum(1 for c in collection.criminalists
                       if get_criminalist_fill(collection, c)["percent"] < 100)
        return sum(1 for c in collection.criminalists if not c.is_active)

    def _restyle_filter_buttons():
        """Перекрасить сегменты фильтра под текущее значение."""
        for v, btn in filter_buttons.items():
            selected = (v == filter_ref["value"])
            fg = COLORS["text_light"] if selected else COLORS["text_secondary"]
            btn.bgcolor = COLORS["btn_save"] if selected else "transparent"
            btn.border = ft.border.all(
                1, COLORS["btn_save_hover"] if selected else "transparent")
            row = btn.content
            try:
                row.controls[0].color = fg                      # иконка
                row.controls[1].color = fg                      # подпись
                badge = row.controls[2]                         # счётчик
                badge.bgcolor = ("#22ffffff" if selected else COLORS["card"])
                badge.content.color = fg
                badge.content.value = str(_filter_count(v))
            except Exception:
                pass
            try:
                btn.update()
            except Exception:
                pass

    def _mk_filter_btn(value: str, label: str, icon) -> ft.Container:
        # ВАЖНО (Flet 0.23.2): без `animate` — оно раздувает layout
        # у Container внутри Row (см. AGENTS.md 15.12 / 22).
        selected = (value == filter_ref["value"])
        fg = COLORS["text_light"] if selected else COLORS["text_secondary"]
        badge = ft.Container(
            content=ft.Text(str(_filter_count(value)), size=10,
                            color=fg, weight=ft.FontWeight.W_600, no_wrap=True),
            height=18,
            padding=ft.padding.symmetric(horizontal=6),
            border_radius=9,
            alignment=ft.alignment.center,
            bgcolor="#22ffffff" if selected else COLORS["card"],
        )
        btn = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(icon, size=14, color=fg),
                    ft.Text(label, size=12, weight=ft.FontWeight.W_600, color=fg, no_wrap=True),
                    badge,
                ],
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
            width=None,
            height=32,
            padding=ft.padding.symmetric(horizontal=12),
            border_radius=8,
            border=ft.border.all(1, COLORS["btn_save_hover"] if selected else "transparent"),
            alignment=ft.alignment.center,
            bgcolor=COLORS["btn_save"] if selected else "transparent",
            ink=True,
            on_click=lambda e, v=value: _set_filter(v),
            tooltip=f"Фильтр: {label}",
        )
        filter_buttons[value] = btn
        return btn

    filter_row = ft.Container(
        content=ft.Row(
            controls=[
                _mk_filter_btn("all", "Все", ft.icons.GRID_VIEW),
                _mk_filter_btn("pending", "Не заполнившие", ft.icons.PENDING_ACTIONS),
                _mk_filter_btn("inactive", "Неактивные", ft.icons.PAUSE_CIRCLE_OUTLINE),
            ],
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        ),
        height=40,
        bgcolor=COLORS["primary_light"],
        border=ft.border.all(1, COLORS["border"]),
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=3, vertical=3),
    )

    # ── Кнопки тулбара ──────────────────────────────────────────
    # ВАЖНО (Flet 0.23.2): elevation-словарь и overlay_color внутри
    # ButtonStyle иногда вызывают неопределённое поведение layout — оставляем
    # только простые стили с фиксированной высотой (см. AGENTS.md 22).
    add_btn = ft.ElevatedButton(
        text="Добавить",
        icon=ft.icons.PERSON_ADD_ALT_1,
        bgcolor=COLORS["btn_save"],
        color=COLORS["text_light"],
        height=38,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.padding.symmetric(horizontal=16),
        ),
        tooltip="Добавить нового криминалиста",
        on_click=lambda e: _on_add_criminalist(),
    )

    copy_btn = ft.OutlinedButton(
        text="Копировать не сдавших",
        icon=ft.icons.CONTENT_COPY,
        height=38,
        style=ft.ButtonStyle(
            color=COLORS["btn_save"],
            side=ft.BorderSide(1, COLORS["btn_save"]),
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.padding.symmetric(horizontal=14),
        ),
        on_click=_on_copy_non_submitters,
        tooltip="Скопировать в буфер список ФИО + отделы тех, кто не сдал форму",
    )

    clear_all_btn = ft.OutlinedButton(
        text="Очистить все данные",
        icon=ft.icons.CLEANING_SERVICES,
        height=38,
        style=ft.ButtonStyle(
            color="#f59e0b",
            side=ft.BorderSide(1, "#f59e0b"),
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.padding.symmetric(horizontal=14),
        ),
        on_click=lambda e: _on_clear_all_data(),
        tooltip="Сбросить все введённые значения. Шаблон, список криминалистов и их активность сохранятся",
    )

    export_btn = ft.ElevatedButton(
        text="Экспорт в Excel",
        icon=ft.icons.FILE_DOWNLOAD_OUTLINED,
        bgcolor=COLORS["btn_export"],
        color=COLORS["text_light"],
        height=38,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.padding.symmetric(horizontal=16),
        ),
        on_click=lambda e: on_export_excel(),
        tooltip="Выгрузить сводную таблицу в файл Excel",
    )

    pdf_btn = ft.ElevatedButton(
        text="Выгрузить зональных",
        icon=ft.icons.PICTURE_AS_PDF,
        bgcolor=COLORS["btn_save"],
        color=COLORS["text_light"],
        height=38,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.padding.symmetric(horizontal=16),
        ),
        on_click=lambda e: _on_export_pdf(e),
        tooltip="Создать печатный PDF распределения зон и взаимозаменяемости",
    )

    settings_btn = ft.IconButton(
        icon=ft.icons.SETTINGS_OUTLINED,
        icon_size=20,
        icon_color=COLORS["text_secondary"],
        tooltip="Настройка сбора данных (шаблон, пункты, режим)",
        style=ft.ButtonStyle(
            bgcolor=COLORS["primary_light"],
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.padding.all(8),
        ),
        on_click=_open_template_settings,
    )

    # Тулбар: фиксированная высота, чтобы Container внутри Column(scroll=AUTO)
    # не пытался расти на всю доступную высоту. Внутренние Row —
    # с tight=True и alignment=START, чтобы не растягиваться по горизонтали.
    toolbar = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.icons.FILTER_ALT_OUTLINED, size=16,
                        color=COLORS["text_secondary"]),
                filter_row,
                ft.Container(
                    width=1,
                    height=26,
                    bgcolor=COLORS["border"],
                    margin=ft.margin.symmetric(horizontal=6),
                ),
                add_btn,
                copy_btn,
                clear_all_btn,
                export_btn,
                pdf_btn,
                open_pdf_btn,
                open_report_btn,
                ft.Container(expand=True),
                settings_btn,
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.START,
            tight=True,
            scroll=ft.ScrollMode.HIDDEN,
        ),
        height=60,
        bgcolor=COLORS["card"],
        border=ft.border.all(1, COLORS["border"]),
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
    )

    # Плашки через фиксированные ряды вместо GridView/Row(wrap=True).
    # В Flet 0.23.2 Wrap/GridView внутри прокручиваемой вкладки получают
    # неограниченную ширину и растягивают плашки. Фиксированные ряды по 4 плашки
    # дают конечные constraints и стабильный рендеринг.
    tiles_column = ft.Column(
        spacing=_TILE_SPACING,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )
    tiles_wrapper = ft.Container(
        content=tiles_column,
        alignment=ft.alignment.top_center,
    )
    tiles_column_ref["control"] = tiles_column

    # Первичный расчёт количества плашек в ряду и наполнение
    try:
        tiles_per_row_ref["value"] = _calc_tiles_per_row(page.width)
    except Exception:
        tiles_per_row_ref["value"] = 4
    print(f"[ZONAL_TAB] Initial tiles per row: {tiles_per_row_ref['value']} "
          f"(page width={getattr(page, 'width', None)})")
    tiles_column.controls = _build_tile_rows(collection.criminalists)

    def _on_page_resize(e=None):
        """Пересчитать сетку плашек при изменении ширины окна."""
        try:
            new_val = _calc_tiles_per_row(page.width)
        except Exception:
            return
        if new_val == tiles_per_row_ref["value"]:
            return
        tiles_per_row_ref["value"] = new_val
        print(f"[ZONAL_TAB] Resize: tiles_per_row -> {new_val} (w={page.width})")
        _apply_filter()

    # Не затираем чужие обработчики: сохраняем предыдущий и вызываем оба.
    _prev_resize = getattr(page, "on_resize", None)

    def _combined_resize(e=None):
        _on_page_resize(e)
        if _prev_resize is not None and _prev_resize is not _combined_resize:
            try:
                _prev_resize(e)
            except Exception:
                pass

    try:
        page.on_resize = _combined_resize
    except Exception:
        pass

    # ── Сводка по криминалистам ─────────────────────────────────
    crim_summary_col = create_criminalists_summary_panel(
        collection, crim_summary_ref, _refresh_crim_summary
    )
    crim_summary_ref["panel"] = crim_summary_col

    tab_content = ft.Column(
        controls=[
            template_info,
            ft.Container(height=8),
            crim_summary_col,
            ft.Container(height=14),
            toolbar,
            ft.Container(height=12),
            ft.Container(height=10),
            tiles_wrapper,
            ft.Container(height=40),
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
    )

    print("[ZONAL_TAB] Zonal tab created successfully (phase 2)")
    return tab_content
