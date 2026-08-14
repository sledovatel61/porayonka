# РАУНД 34 — убрать пароль admin, починить detection admin/user exe, диалог «Кто вы?»

**Дата:** 2026-08-14.  
**База:** `main`, коммит `0099a35` (раунд 33 влит).  
**Ветка агента:** новая `arena/XXXXXXXX-porayonka` от `main`.  
**Скрины/логи:** `design/screenshots/14.08.2026/` (пользователь обновил).

## 1. Что сломано после раунда 33 (живой тест трёх exe)

1. **Пароль admin не пускает.**  
   `Порайонка_Админ.exe` сразу запрашивает пароль, ввод не принимается, «Выход» не работает, приложение не открывается. Пользователь требует **убрать пароль из admin-версии полностью** в этом раунде (переработаем позже, если понадобится).

2. **Admin exe загружается как user «Миронович».**  
   После удаления `%APPDATA%\porayonka\edition.json` и `.bak` запуск admin exe открывает user-режим с уже выбранным пользователем «Миронович Д.В.».  
   Возможные причины:
   - `core/edition.py` для frozen onefile PyInstaller не находит `edition.json` рядом с реальным exe (может смотреть во временную папку `_MEI` или в appdata);
   - `controls_settings.json` остался с `network_role="user"` / `network_user="Миронович Д.В."`, и admin-редакция не принудительно сбрасывает его;
   - `_self_heal_edition_files` восстанавливает/копирует appdata-файл в папку exe.

3. **User/web не спрашивают «Кто вы?».**  
   `Порайонка_Пользователь.exe` и `Порайонка_Пользователь_Web.exe` при первом запуске (без вшитого ФИО) не показывают диалог выбора ФИО, а сразу открываются с наследованным `network_user` («Миронович»).

4. **Трей в нативных exe работает.**  
   После закрытия окна «Открыть» в трее восстанавливает приложение — это оставляем.

5. **«О программе» починено.**  
   Текст помещается — оставляем.

## 2. Цели раунда 34

1. **Убрать ввод пароля из admin-версии.**  
   `main.py` не должен вызывать `show_admin_password_gate` ни при каком режиме. Admin-редакция открывает UI сразу.

2. **Починить определение admin/user для frozen onefile-сборок PyInstaller.**  
   - `core/edition.py`: `_app_dir()` в frozen-режиме должен возвращать папку **реального exe-файла**, а не временной `_MEI`.
   - `edition_file_candidates()` должен отдавать абсолютный приоритет `edition.json` рядом с реальным exe; appdata-файлы — только fallback.
   - Ограничить `_self_heal_edition_files`: никогда не копировать edition.json **из appdata в папку exe**; разрешить только восстановление `edition.json` из `edition.json.bak` в той же папке, и только если основного файла там нет.
   - Привязка роли к exe должна быть неизменной: `Порайонка_Админ.exe` всегда admin, `Порайонка_Пользователь.exe`/`_Web.exe` всегда user, независимо от того, что лежит в `%APPDATA%`.

3. **Admin-редакция всегда сбрасывает user-наследие.**  
   При открытии вкладки «Контроли» для explicit admin (из edition.json рядом с exe или env) принудительно: `network_role = "admin"`, `network_user = ""`, сохранить настройки. Appdata `network_role/user` не должен иметь приоритета.

4. **User-редакция всегда спрашивает «Кто вы?» при отсутствии вшитого ФИО.**  
   - Если `edition.user_name` не задан (пустая строка), игнорировать `network_user` из `controls_settings.json`.
   - Показать диалог «Кто вы?» до построения таблицы.
   - После выбора сохранить `network_user` в настройки и не спрашивать повторно, пока `edition.user_name` пуст.

5. **Диагностика.**  
   Добавить ASCII `print()` в `load_edition()` / `_app_dir()`:
   - путь к `sys.executable` и `sys._MEIPASS` (если есть) в frozen;
   - выбранная папка `_app_dir()`;
   - источник edition (env / app_dir / appdata / default);
   - итоговая роль и user_name.
   Это нужно для отладки на реальных ПК.

## 3. Технические ограничения

- Flet строго 0.23.2, без новых зависимостей.
- `print()` — только ASCII; UI-текст — русский.
- Внутри `Column(scroll=AUTO)` — без `expand=True` (кроме горизонтальных спейсеров в Row), без `wrap=True`, без `animate*`, без `gradient`/`shadow` на мелких контейнерах.
- Цвета 8-digit — только `#AARRGGBB`.
- Не ломать раунды 20–33: сеть, архив, вложения, Excel, трей, lock-файлы, офлайн-вложения, портретные сроки, user-уведомления.
- Тесты `tests/test_controls_smoke.py` должны остаться cp1251-безопасными (без `—`, `→`, `×` в `print`/`check`).
- Код `ui/admin_gate.py` и `core/crash_log.py` не удалять — пароль временно отключается только в `main.py`.

## 4. Где смотреть

- `porayonka-app/core/edition.py` — определение `_app_dir()`, `load_edition()`, `apply_edition_to_settings()`, `_self_heal_edition_files()`.
- `porayonka-app/main.py` — вызов `show_admin_password_gate`, `_main_impl()`, `_maybe_ask_identity()`.
- `porayonka-app/ui/controls/controls_tab.py` — `create_controls_tab()`, `_maybe_ask_identity()`, `_first_table_init()`.
- `porayonka-app/Porayonka_Admin.spec`, `Porayonka_User.spec`, `Porayonka_User_Web.spec` — проверить, что `edition.json` добавлен как data рядом с exe.
- `porayonka-app/build_admin.bat`, `build_user.bat`, `build_user_web_win7.bat` — проверить генерацию `edition.json`.

## 5. Что нужно сделать

1. В `main.py` закомментировать/убрать вызов `show_admin_password_gate`.  
   Поток выполнения: `main()` → `apply_edition_to_settings(...)` → `_main_impl(page)`.  
   Возможно оставить старую ветку пароля в комментарии «отключено раунд 34».

2. В `core/edition.py`:
   - `_app_dir()`: если `hasattr(sys, "frozen")`/`sys.frozen` — вернуть `Path(sys.executable).parent.resolve()`.  
     НЕ `Path(sys._MEIPASS).parent` и не `Path(sys.argv[0]).parent`.
   - `load_edition()`: кандидаты в порядке приоритета:
     1. env `PORAYONKA_EDITION` (role), `PORAYONKA_USER` (user_name), `PORAYONKA_ADMIN_PASSWORD*` — только для dev/тестов;
     2. `app_dir/edition.json`;
     3. `app_dir/edition.json.bak`;
     4. `appdata/edition.json`;
     5. default admin.
     Если `app_dir/edition.json` существует — читать только его (не мержить с appdata).
   - `_self_heal_edition_files`: в frozen-режиме НЕ пытаться копировать `edition.json` из appdata в app_dir. Только: если в app_dir нет edition.json, но есть edition.json.bak — скопировать .bak в edition.json. Если и .bak нет — оставить как есть.
   - `apply_edition_to_settings`: при `role == "admin"` всегда сбрасывать `network_role="admin"`, `network_user=""` и сохранять настройки. При `role == "user"` сбрасывать `network_role="user"`; `network_user` сбрасывать, только если `edition.user_name` пуст (чтобы вшитое ФИО работало).

3. В `ui/controls/controls_tab.py`:
   - `_maybe_ask_identity()` должен показывать диалог, если `edition.role == "user"` И (`edition.user_name == ""` ИЛИ `force_ask == True`).
   - До выбора ФИО таблица не строится (`_first_table_init()` откладывается в `on_done` диалога).
   - После выбора: `network_user = selected`, сохранить настройки, затем строить таблицу.
   - Если `edition.user_name` непустое — использовать его как `network_user`, диалог не показывать.

4. Обновить `tests/test_controls_smoke.py`:
   - Убрать/адаптировать проверки, которые ожидают диалог пароля (auth32/auth33).
   - Добавить `edition34`: frozen onefile app_dir из `sys.executable`; appdata не перебивает app_dir; admin сбрасывает user; user без user_name сбрасывает network_user и показывает диалог.
   - Добавить `id34`: user-редакция без вшитого ФИО всегда показывает «Кто вы?».

5. Обновить `AGENTS.md` раздел 76 после завершения.

## 6. Проверка

Обязательные проверки после правок:

```bash
cd porayonka-app
python -m py_compile main.py main_web.py ui/admin_gate.py \
    ui/controls/controls_tab.py ui/controls/controls_settings_modal.py \
    core/edition.py core/controls_data.py core/controls_models.py \
    core/controls_notify.py core/controls_exporter.py core/crash_log.py   # OK
python -c "import sys; sys.path.insert(0, '.'); \
    from ui.controls.controls_tab import create_controls_tab; print('OK')"  # OK
python tests/test_controls_smoke.py    # ALL OK
python tests/test_network_stress.py    # ALL OK (3 прогона)
```

Живая проверка (пользователь выполнит после сборки):
1. Собрать `Порайонка_Админ.exe` → запускается сразу без пароля, UI admin, не «Миронович».
2. Собрать `Порайонка_Пользователь.exe` → на машине, где раньше был «Миронович», спрашивает «Кто вы?»; после выбора работает как user.
3. Собрать `Порайонка_Пользователь_Web.exe` → аналогично, диалог «Кто вы?» при первом запуске.
4. Трей в нативных exe по-прежнему восстанавливает окно.

## 7. Что не трогать

- Не удалять `ui/admin_gate.py` / `core/crash_log.py` — они понадобятся для возможной будущей реализации пароля.
- Не менять layout вкладок 1–2 и функционал вкладки «Контроли» (кроме точечных изменений для роли/диалога).
- Не повышать Flet, не добавлять новые зависимости.
- Не коммитить `dist_all/`, `build/`, `build.log`, `*.exe` в git.
