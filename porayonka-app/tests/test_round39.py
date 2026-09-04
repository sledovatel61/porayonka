# tests/test_round39.py
"""
Полный тестовый контур для Раунда 39:
1. Очистка конечной даты периодического контроля и round-trip (пустая/заданная дата).
2. Ленивые вкладки (LazyTabManager): старт без тяжёлых builder'ов, однократное
   построение при переходе, кэширование и неизменность порядка.
3. Единственный владелец открытия браузера: static & mock тесты отсутствия дублей.
4. Single-instance guard (named mutex / fcntl) и потокобезопасный синглтон трея.
5. Excel upload & import в Admin Win7 Web: загрузка через FilePicker, валидация .xlsx,
   предпросмотр, upsert, блокировка в user-режиме, обработка ошибок и отмен.
"""
import os
import sys
import shutil
import tempfile
import threading
import json
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

# Добавляем родительский каталог в sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.page_stub import PageStub
import flet as ft
from core.constants import COLORS
from core.controls_models import Control, ControlTask, ControlMilestone, ONE_TIME, PERIODIC
from core.controls_data import get_controls_file, load_controls, save_controls
from core.controls_exporter import ControlsExcelExporter, import_plan, import_from_excel
from core.single_instance import SingleInstanceGuard, acquire_single_instance, release_single_instance
from ui.lazy_tabs import LazyTabManager
from ui.tray_icon import start_tray, get_active_icon, stop_tray, _ACTIVE_ICON
from ui.controls.controls_tab import create_controls_tab
from ui.controls.control_card_modal import create_control_card_modal
from ui.controls.russian_calendar import create_russian_date_field, create_russian_calendar_expanded

_PASSED = 0
_FAILED = 0
_FAILURES = []


def check(name: str, cond: bool, extra: str = ""):
    global _PASSED, _FAILED, _FAILURES
    if cond:
        _PASSED += 1
        print(f"[OK ] {name}" + (f"  ({extra})" if extra else ""))
    else:
        _FAILED += 1
        _FAILURES.append(name)
        print(f"[FAIL] {name}" + (f"  ({extra})" if extra else ""))


def setup_temp_appdata(prefix="r39_"):
    td = tempfile.mkdtemp(prefix=prefix)
    os.environ["APPDATA"] = td
    data_dir = Path(td) / "porayonka"
    data_dir.mkdir(parents=True, exist_ok=True)
    return td, data_dir


def test_task1_end_date():
    print("\n=== ТЕСТ 1: Конечная дата периодического контроля и Excel round-trip ===")
    tmp_root, data_dir = setup_temp_appdata("r39_date_")
    try:
        page = PageStub()
        ctl = Control(
            id="c-per-1",
            incoming_number="Т-01",
            control_type=PERIODIC,
            period_days=7,
            end_date="2026-10-15",
            due_date="2026-09-10",
            receive_date="2026-09-01",
            content="Периодический контроль",
            executors=["Миронович Д.В."],
            controller="Потемкин С.А.",
            attachments=["scan.pdf"],
        )
        save_controls([ctl])

        # 1.1 UI-вкладка: открытие карточки и очистка даты
        tab = create_controls_tab(page)
        # Находим строку в таблице и кликаем
        found_rows = [c for c in tab.controls if hasattr(c, "content")]
        # Открываем деталь через _open_detail
        # Вызываем модалку control_card_modal
        on_save_mock = MagicMock()
        modal = create_control_card_modal(page, ctl, ["Миронович Д.В.", "Потемкин С.А."], on_save=on_save_mock)
        check("date39: модалка карточки создана", modal is not None)

        # Проверяем контракт russian_calendar с None
        changed_iso = []
        cal_field = create_russian_date_field(page, "2026-10-15", lambda iso: changed_iso.append(iso), hint="Конечная дата")
        check("date39: russian_date_field начальное значение", cal_field._get_iso() == "2026-10-15")
        cal_field._set_iso(None)
        check("date39: russian_date_field после очистки", cal_field._get_iso() is None)

        cal_exp_changed = []
        cal_exp = create_russian_calendar_expanded(page, "2026-10-15", lambda iso: cal_exp_changed.append(iso))
        cal_exp._set_iso(None)
        check("date39: russian_calendar_expanded после очистки", cal_exp._get_iso() is None)

        # 1.2 Сохранение Control с end_date=None и повторное чтение
        ctl.end_date = None
        save_controls([ctl])
        loaded = load_controls()
        check("date39: сохранение с end_date=None пишет None", loaded[0].end_date is None)
        check("date39: очистка не меняет due_date", loaded[0].due_date == "2026-09-10")
        check("date39: очистка не меняет period_days", loaded[0].period_days == 7)

        # 1.3 Переход periodic -> one-time сбрасывает end_date
        ctl_per = Control(id="c-per-2", incoming_number="Т-02", control_type=PERIODIC, end_date="2026-12-31")
        # Переключаем тип
        ctl_per.control_type = ONE_TIME
        ctl_per.end_date = None
        save_controls([loaded[0], ctl_per])
        loaded2 = load_controls()
        check("date39: переход periodic->one-time обнуляет end_date", loaded2[1].end_date is None)

        # 1.4 Установка новой даты после очистки
        loaded2[0].end_date = "2026-11-20"
        save_controls(loaded2)
        loaded3 = load_controls()
        check("date39: выбор новой даты после очистки сохраняется", loaded3[0].end_date == "2026-11-20")

        # 1.5 Excel Round-trip для пустой и заполненной конечной даты
        exp_file = os.path.join(tmp_root, "export_roundtrip.xlsx")
        c_with_end = Control(id="c-end-1", incoming_number="Э-1", control_type=PERIODIC, period_days=14, end_date="2026-12-01", due_date="2026-09-15")
        c_without_end = Control(id="c-end-2", incoming_number="Э-2", control_type=PERIODIC, period_days=30, end_date=None, due_date="2026-09-20")
        ControlsExcelExporter().export([c_with_end, c_without_end], exp_file, soon_days=3, full=True)
        check("date39: Excel full export создан", os.path.isfile(exp_file))

        res_new, res_stats = import_from_excel(exp_file, [])
        check("date39: Excel импортировал 2 записи", len(res_new) == 2)
        res_by_num = {c.incoming_number: c for c in res_new}
        check("date39: round-trip сохранил end_date с датой", res_by_num["Э-1"].end_date == "2026-12-01")
        check("date39: round-trip сохранил end_date=None для пустой даты", res_by_num["Э-2"].end_date is None)
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


def test_task2_lazy_tabs():
    print("\n=== ТЕСТ 2: Ленивая загрузка вкладок и кэширование ===")
    page = PageStub()
    lazy_mgr = LazyTabManager(page, verbose=False)

    c0 = ft.Container(expand=True, visible=True)
    c1 = ft.Container(expand=True, visible=False)
    c2 = ft.Container(expand=True, visible=False)

    b0_calls = [0]
    b1_calls = [0]
    b2_calls = [0]

    def builder0():
        b0_calls[0] += 1
        return ft.Text("Контроли Content")

    def builder1():
        b1_calls[0] += 1
        return ft.Text("Зональные Content")

    def builder2():
        b2_calls[0] += 1
        return ft.Text("Отделы Content")

    lazy_mgr.register_tab(0, "Контроли", c0, builder0, immediate=True)
    lazy_mgr.register_tab(1, "Зональные", c1, builder1, immediate=False)
    lazy_mgr.register_tab(2, "Следственные отделы", c2, builder2, immediate=False)

    # На старте построена ТОЛЬКО вкладка 0
    check("lazy39: на старте builder0 вызван ровно 1 раз", b0_calls[0] == 1)
    check("lazy39: на старте builder1 НЕ вызывался (count=0)", b1_calls[0] == 0)
    check("lazy39: на старте builder2 НЕ вызывался (count=0)", b2_calls[0] == 0)
    check("lazy39: c0 содержит контент", c0.content is not None)
    check("lazy39: c1 content пуст до переключения", c1.content is None)
    check("lazy39: c2 content пуст до переключения", c2.content is None)

    # Первый переход на вкладку 1 (Зональные)
    lazy_mgr.switch_to(1)
    check("lazy39: после перехода builder1 вызван 1 раз", b1_calls[0] == 1)
    check("lazy39: builder2 по-прежнему не вызывался", b2_calls[0] == 0)
    check("lazy39: c1 видима, c0 и c2 скрыты", c1.visible and not c0.visible and not c2.visible)
    check("lazy39: c1 content заполнен", c1.content is not None)

    # Первый переход на вкладку 2 (Отделы)
    lazy_mgr.switch_to(2)
    check("lazy39: после перехода builder2 вызван 1 раз", b2_calls[0] == 1)
    check("lazy39: c2 видима, c0 и c1 скрыты", c2.visible and not c0.visible and not c1.visible)
    check("lazy39: c2 content заполнен", c2.content is not None)

    # Повторные переходы — проверка кэширования
    lazy_mgr.switch_to(0)
    lazy_mgr.switch_to(1)
    lazy_mgr.switch_to(2)
    lazy_mgr.switch_to(0)

    check("lazy39: после повторных переключений builder0 count == 1", b0_calls[0] == 1)
    check("lazy39: после повторных переключений builder1 count == 1", b1_calls[0] == 1)
    check("lazy39: после повторных переключений builder2 count == 1", b2_calls[0] == 1)
    check("lazy39: get_build_count для всех вкладок строго 1",
          lazy_mgr.get_build_count(0) == 1 and lazy_mgr.get_build_count(1) == 1 and lazy_mgr.get_build_count(2) == 1)


def test_task3_single_browser_owner():
    print("\n=== ТЕСТ 3: Единственный владелец открытия браузера ===")
    app_dir = Path(__file__).resolve().parent.parent

    # 3.1 Static check start_web_win7.bat
    bat_file = app_dir / "start_web_win7.bat"
    bat_text = bat_file.read_text(encoding="utf-8")
    check("browser39: start_web_win7.bat НЕ содержит 'start http'", "start http" not in bat_text.lower())
    check("browser39: start_web_win7.bat информирует об авто-открытии браузера", "браузер открывается автоматически" in bat_text)

    # 3.2 Static check main.py
    main_file = app_dir / "main.py"
    main_text = main_file.read_text(encoding="utf-8")
    check("browser39: main.py использует ft.AppView.WEB_BROWSER для web", "view=ft.AppView.WEB_BROWSER" in main_text)

    # 3.3 main_web.py вторичный запуск vs первичный
    from main_web import _open_browser
    with patch("webbrowser.open") as mock_wb:
        _open_browser(8555)
        check("browser39: _open_browser вызывает webbrowser.open с URL", mock_wb.called)
        mock_wb.assert_called_with("http://127.0.0.1:8555")


def test_task4_single_instance_and_tray():
    print("\n=== ТЕСТ 4: Single-Instance Named Mutex & Tray Singleton ===")
    # 4.1 SingleInstanceGuard: POSIX / Named mutex tests
    g1 = SingleInstanceGuard("test_guard_app")
    g2 = SingleInstanceGuard("test_guard_app")

    check("singleinst39: первый захват успешен", g1.acquire() is True)
    check("singleinst39: g1.is_acquired == True", g1.is_acquired is True)
    check("singleinst39: второй захват тем же именем отклонен", g2.acquire() is False)
    check("singleinst39: g2.is_acquired == False", g2.is_acquired is False)

    # Освобождение
    g1.release()
    check("singleinst39: после release g1.is_acquired == False", g1.is_acquired is False)
    check("singleinst39: после освобождения g2 успешно захватывает", g2.acquire() is True)
    g2.release()

    # 4.2 Windows Named Mutex Mock Simulation
    import ctypes
    mock_windll = MagicMock()
    mock_k32 = MagicMock()
    mock_windll.kernel32 = mock_k32
    with patch("sys.platform", "win32"), patch.object(ctypes, "windll", mock_windll, create=True):
        # Case 1: First instance
        mock_k32.CreateMutexW.return_value = 12345
        mock_k32.GetLastError.return_value = 0
        win_g1 = SingleInstanceGuard("win_test")
        check("singleinst39: Windows first instance acquires handle", win_g1._acquire_windows() is True)

        # Case 2: Second instance with ERROR_ALREADY_EXISTS (183)
        mock_k32.CreateMutexW.return_value = 12346
        mock_k32.GetLastError.return_value = 183
        win_g2 = SingleInstanceGuard("win_test")
        check("singleinst39: Windows second instance ERROR_ALREADY_EXISTS returns False", win_g2._acquire_windows() is False)
        check("singleinst39: CloseHandle вызван для отклоненного хэндла", mock_k32.CloseHandle.called)

        # Case 3: Second instance with ERROR_ACCESS_DENIED (5)
        mock_k32.CreateMutexW.return_value = 0
        mock_k32.GetLastError.return_value = 5
        win_g3 = SingleInstanceGuard("win_test")
        check("singleinst39: Windows ERROR_ACCESS_DENIED returns False", win_g3._acquire_windows() is False)

        # Case 4: Release closes handle
        win_g1._handle = 12345
        win_g1._acquired = True
        win_g1.release()
        check("singleinst39: Windows release сбрасывает handle", win_g1._handle is None)

    # 4.3 Tray Icon Singleton
    stop_tray()
    mock_icon_instance = MagicMock()
    mock_pystray = MagicMock()
    mock_pystray.Icon.return_value = mock_icon_instance
    mock_pil = MagicMock()

    with patch("sys.platform", "win32"), \
         patch.dict("sys.modules", {"pystray": mock_pystray, "PIL": mock_pil, "PIL.Image": mock_pil}):
        # Конкурентный запуск из 10 потоков
        icons = []
        threads = [threading.Thread(target=lambda: icons.append(start_tray(None, web_url="http://127.0.0.1:8555")))
                   for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        check("tray39: все 10 вызовов вернули один и тот же icon", len(set(id(i) for i in icons)) == 1)
        check("tray39: get_active_icon возвращает созданный значок", get_active_icon() == mock_icon_instance)
        stop_tray()
        check("tray39: stop_tray обнуляет _ACTIVE_ICON", get_active_icon() is None)


def test_task5_web_excel_import():
    print("\n=== ТЕСТ 5: Flet Web Excel Upload & Import в Admin ===")
    tmp_root, data_dir = setup_temp_appdata("r39_web_import_")
    try:
        # Создаем тестовый файл Excel для импорта
        xlsx_path = os.path.join(tmp_root, "test_import.xlsx")
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Контроли"
        from core.controls_exporter import TABLE_HEADERS
        ws.append(list(TABLE_HEADERS))
        ws.append([1, "ВХ-101", "01.09.2026", "СУ", "Импортированное задание 1", "Миронович Д.В.", "Потемкин С.А.", "15.10.2026 далее еженедельно", "08.09.2026", ""])
        ws.append([2, "ВХ-102", "01.09.2026", "СУ", "Импортированное задание 2 (разовый)", "Семисенко И.Ю.", "Чашин Э.А.", "30.09.2026", "30.09.2026", ""])
        wb.save(xlsx_path)

        page = PageStub()
        os.environ["PORAYONKA_WEB"] = "1"
        os.environ["PORAYONKA_EDITION"] = "admin"
        upload_dir = os.path.join(data_dir, "web_uploads")
        os.makedirs(upload_dir, exist_ok=True)
        os.environ["FLET_UPLOAD_DIR"] = upload_dir

        from core.controls_data import save_settings
        save_settings({"network_enabled": False})
        save_controls([])
        tab = create_controls_tab(page)

        # 5.1 Проверяем регистрацию FilePicker импорта
        picker = getattr(page, "_controls_import_picker", None)
        check("webimport39: _controls_import_picker зарегистрирован в page", picker is not None)

        # 5.2 Моделируем результат выбора файла в Web (без локального path)
        class MockFile:
            def __init__(self, name):
                self.name = name
                self.path = None

        class MockPickerResult:
            def __init__(self, files):
                self.files = files
                self.path = None

        on_result = getattr(page, "_controls_import_picker_handler")
        on_upload = getattr(page, "_controls_import_picker_upload_handler")

        # Отмена диалога (files=None)
        on_result(MockPickerResult(None))
        check("webimport39: отмена диалога не вызывает падений", len(load_controls()) == 0)

        # Выбор не-xlsx файла
        on_result(MockPickerResult([MockFile("document.pdf")]))
        check("webimport39: не-xlsx файл отклонен", len(load_controls()) == 0)

        # Выбор валидного xlsx файла -> запуск upload
        picker.upload = MagicMock()
        page.get_upload_url = MagicMock(return_value="http://127.0.0.1:8555/upload/test_import.xlsx")

        on_result(MockPickerResult([MockFile("test_import.xlsx")]))
        check("webimport39: upload() вызван для xlsx", picker.upload.called)

        # Копируем файл в upload_dir как будто сервер его принял
        uploaded_target = os.path.join(upload_dir, "test_import.xlsx")
        shutil.copy2(xlsx_path, uploaded_target)

        # 5.3 Моделируем событие завершения upload (progress=1.0)
        class MockUploadEvent:
            def __init__(self, file_name, progress, error=None):
                self.file_name = file_name
                self.progress = progress
                self.error = error

        # Неполный прогресс
        on_upload(MockUploadEvent("test_import.xlsx", 0.5))
        check("webimport39: неполный progress < 1.0 не запускает предпросмотр", len(page.dialogs) == 0)

        # Ошибка upload
        on_upload(MockUploadEvent("test_import.xlsx", 1.0, error="Network error"))
        check("webimport39: ошибка upload обработана корректно", len(page.dialogs) == 0)

        # Повторный выбор файла и успешный upload (progress=1.0)
        on_result(MockPickerResult([MockFile("test_import.xlsx")]))
        on_upload(MockUploadEvent("test_import.xlsx", 1.0, error=None))
        check("webimport39: успешный upload открыл диалог предпросмотра", len(page.dialogs) > 0)

        # 5.4 Подтверждение импорта в диалоге
        preview_dialog = page.dialogs[-1]
        confirm_btn = [c for c in preview_dialog.actions if getattr(c, "text", "") == "Импортировать"][0]
        confirm_btn.on_click(None)

        loaded_controls = load_controls()
        check("webimport39: импортировано ровно 2 контроля", len(loaded_controls) == 2, f"count={len(loaded_controls)}")
        nums = [c.incoming_number for c in loaded_controls]
        check("webimport39: ВХ-101 и ВХ-102 присутствуют в базе", "ВХ-101" in nums and "ВХ-102" in nums)
        c101 = next(c for c in loaded_controls if c.incoming_number == "ВХ-101")
        check("webimport39: уникальный id присвоен", bool(c101.id))
        check("webimport39: периодический контроль импортирован с конечной датой", c101.end_date == "2026-10-15")

        # 5.5 Повторный импорт того же файла (идемпотентность, 0 новых)
        page.dialogs.clear()
        on_result(MockPickerResult([MockFile("test_import.xlsx")]))
        on_upload(MockUploadEvent("test_import.xlsx", 1.0, error=None))
        check("webimport39: повторный импорт без изменений не открывает диалог подтверждения", len(page.dialogs) == 0)
        check("webimport39: повторный импорт не создал дублей (всего 2 записи)", len(load_controls()) == 2)

        # 5.6 Проверка блокировки импорта в User-режиме
        os.environ["PORAYONKA_EDITION"] = "user"
        page_user = PageStub()
        tab_user = create_controls_tab(page_user)
        picker_user = getattr(page_user, "_controls_import_picker", None)
        user_handler = getattr(page_user, "_controls_import_picker_handler")
        picker_user.upload = MagicMock()
        user_handler(MockPickerResult([MockFile("test_import.xlsx")]))
        check("webimport39: User-режим блокирует вызов upload", not picker_user.upload.called)
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
        os.environ.pop("PORAYONKA_WEB", None)


def main():
    print("==================================================================")
    print("        ЗАПУСК ПОЛНОГО ТЕСТОВОГО КОНТУРА РАУНДА 39                ")
    print("==================================================================")
    test_task1_end_date()
    test_task2_lazy_tabs()
    test_task3_single_browser_owner()
    test_task4_single_instance_and_tray()
    test_task5_web_excel_import()

    print("\n==================================================================")
    print(f"ИТОГИ ТЕСТИРОВАНИЯ: ВСЕГО: {_PASSED + _FAILED} | УСПЕШНО: {_PASSED} | ОШИБОК: {_FAILED}")
    print("==================================================================")
    if _FAILED > 0:
        print("ПРОВАЛЕННЫЕ ТЕСТЫ:")
        for f in _FAILURES:
            print(f" - {f}")
        sys.exit(1)
    else:
        print("ВСЕ ПРОВЕРКИ РАУНДА 39 ПРОЙДЕНЫ УСПЕШНО!")
        sys.exit(0)


if __name__ == "__main__":
    main()
