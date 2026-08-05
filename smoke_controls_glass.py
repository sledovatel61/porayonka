# Headless smoke для редизайна «Контроли» (Glass Dark).
# Запуск: /tmp/poray-venv/bin/python smoke_controls_glass.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "porayonka-app"))

import flet as ft

# Переменные окружения: не ходить в реальный %APPDATA%
os.environ.setdefault("APPDATA", "/tmp/poray_smoke_appdata")
os.makedirs("/tmp/poray_smoke_appdata/porayonka", exist_ok=True)


class FakeWindow:
    width = 1280
    height = 860
    def __init__(self):
        self._events = {}
    def on_event(self, *a, **k):
        pass


class FakePage:
    def __init__(self, width=1440):
        self.width = width
        self.height = 900
        self.window = FakeWindow()
        self.overlay = []
        self.snack_bar = None
        self._controls_poll_stop = None
        self.on_resize = None
        self.opened = []
        self.closed = []
        self._uid = 0

    def update(self):
        pass

    def open(self, ctrl):
        self.opened.append(ctrl)

    def close(self, ctrl):
        self.closed.append(ctrl)


def walk(ctrl):
    """Обойти дерево контролов (по атрибуту controls у контейнеров)."""
    yield ctrl
    for attr in ("controls", "content"):
        try:
            v = getattr(ctrl, attr)
        except Exception:
            continue
        if isinstance(v, (list, tuple)):
            for c in v:
                yield from walk(c)
        elif v is not None and isinstance(v, ft.Control):
            yield from walk(v)


def find(ctrl, cls):
    return [c for c in walk(ctrl) if isinstance(c, cls)]


def main():
    page = FakePage(1440)
    from ui.controls.controls_tab import create_controls_tab
    tab = create_controls_tab(page)
    print("[1] tab built OK")

    # структура: корневая колонка со Stack
    stacks = find(tab, ft.Stack)
    assert stacks, "no Stack in tab"
    assert len(stacks[0].controls) == 2, "Stack must hold main + detail overlay"
    main_ct, overlay_ct = stacks[0].controls
    assert overlay_ct.visible is False

    # фон вкладки
    assert main_ct.bgcolor == "#0a1024", f"tab bg wrong: {main_ct.bgcolor}"

    # шапка таблицы построена (Bug C fix)
    header_rows = find(main_ct, ft.Container)
    # найдём header_row по высоте 34 и фону шапки
    headers = [c for c in header_rows if c.height == 34 and c.bgcolor == "#0d1830"]
    assert headers, "header row not found"
    hr = headers[0]
    assert isinstance(hr.content, ft.Row) and len(hr.content.controls) >= 12, "header cells missing"

    # чипы-счётчики: 6 чипов + сегмент режима
    chips = [c for c in find(main_ct, ft.Container)
             if c.height == 30 and c.border_radius == 15]
    assert len(chips) == 6, f"expected 6 status chips, got {len(chips)}"

    # нет DatePicker в overlay (БАГ F): только FilePicker'ы
    dps = [c for c in page.overlay if isinstance(c, ft.DatePicker)]
    assert not dps, "DatePicker still mounted in overlay!"
    fps = [c for c in page.overlay if isinstance(c, ft.FilePicker)]
    print(f"[2] overlay clean: {len(fps)} FilePickers, 0 DatePickers")

    # ── Русский календарь ──────────────────────────────────────
    from ui.controls.russian_calendar import create_russian_date_field
    picked = {"v": None}
    page2 = FakePage(1280)
    df = create_russian_date_field(page2, None, lambda iso: picked.update(v=iso), hint="Дата", width=150)
    assert df._field is not None

    # открыть панель (фокус поля)
    df._field.on_focus(None)
    panel = df.controls[1]
    assert panel.visible is True, "calendar panel did not open"

    # проверить заголовок месяца и листание
    from datetime import date as d
    month_label = find(df, ft.Text)
    def label_text():
        for t in find(df, ft.Text):
            if t.size == 13 and t.weight == ft.FontWeight.BOLD:
                return t.value
        return None
    cur = label_text()
    expected = ("Январь" if d.today().month == 1 else None)
    assert cur and str(d.today().year) in cur, f"month label wrong: {cur}"

    # листаем вперёд → месяц изменился
    chevrons = [c for c in find(df, ft.IconButton) if c.icon in (ft.icons.CHEVRON_RIGHT, ft.icons.CHEVRON_LEFT)]
    right = [c for c in chevrons if c.icon == ft.icons.CHEVRON_RIGHT][0]
    right.on_click(None)
    after = label_text()
    assert after != cur, "month did not flip"

    # клик по дню = мгновенный выбор
    grid_containers = [c for c in find(df, ft.Container) if c.width == 34 and c.height == 32]
    day_cells = [c for c in grid_containers if c.on_click is not None]
    assert day_cells, "no day cells"
    day_cells[0].on_click(None)
    assert picked["v"] is not None, "on_change not called on day click"
    assert panel.visible is False, "panel not closed after pick"
    assert df._field.value != "", "field text not updated after pick"
    print(f"[3] russian calendar: open→flip→pick→close OK ({picked['v']})")

    # «Сегодня» и «Очистить»
    def _btn_text(b):
        if b.text:
            return b.text
        c = getattr(b, "content", None)
        return getattr(c, "value", "") if c is not None else ""
    btns = find(df, ft.TextButton)
    labels = {_btn_text(b): b for b in btns}
    assert "Сегодня" in labels and "Очистить" in labels, list(labels.keys())
    df._field.on_focus(None)
    labels["Сегодня"].on_click(None)
    assert picked["v"] == d.today().isoformat()
    df._field.on_focus(None)
    labels["Очистить"].on_click(None)
    assert picked["v"] is None and df._field.value == ""

    # ── Карточка (резервный путь) ──────────────────────────────
    from ui.controls.control_card_modal import create_control_card_modal
    from core.controls_models import Control
    ctl = Control(id="t1", incoming_number="Иссоп-216-1017-26/дсп", content="Тест")
    saved = []
    dlg = create_control_card_modal(page2, ctl, ["Семисенко Иван Юрьевич", "Чашин Эдгар Анатольевич"],
                                    on_save=lambda c: saved.append(c), settings={})
    assert dlg is not None and isinstance(dlg, ft.AlertDialog)
    assert dlg.bgcolor == "#16213d"
    # в modal нет DatePicker в overlay
    dps2 = [c for c in page2.overlay if isinstance(c, ft.DatePicker)]
    assert not dps2, "DatePicker in card modal overlay"
    print("[4] card modal built OK (no DatePicker)")

    # ── Настройки ───────────────────────────────────────────────
    from ui.controls.controls_settings_modal import create_controls_settings_modal
    sdlg = create_controls_settings_modal(page2, {}, lambda s: None)
    assert isinstance(sdlg, ft.AlertDialog) and sdlg.bgcolor == "#16213d"
    print("[5] settings modal built OK")

    # ── Экспорт/импорт-контракты на месте ───────────────────────
    from core.controls_exporter import ControlsExcelExporter, import_from_excel
    assert hasattr(ControlsExcelExporter(), "export")
    assert callable(import_from_excel)
    print("[6] export/import contracts OK")

    print("\nALL SMOKE CHECKS PASSED")


if __name__ == "__main__":
    main()
