# AGENTS.md — Порайонка v2.0 DARK final

## 1. Актуальный статус

Порайонка — Python/Flet-приложение для учёта контролей, следственных отделов и зональных криминалистов СК РФ по Ростовской области. Рабочий код находится в `porayonka-app/`; React-прототип в `src/` отдельный и с Python-версией не синхронизирован.

Три вкладки: **Контроли** (основной список, пункты, архив, вложения, Excel, сеть, уведомления), **Зональные криминалисты** (шаблоны, сборы, сводки, Excel), **Следственные отделы** (29 отделов, статусы, статистика, экспорт).

Исторические раунды из старой версии AGENTS.md удалены намеренно. Ниже оставлены только актуальные инварианты, правила разработки и подробная инструкция сборки.

## 2. Стек и обязательные правила

- Python 3.10+; **Flet строго 0.23.2**, не повышать.
- `openpyxl==3.1.5`; PyInstaller.
- `pystray` и `Pillow` опциональны для трея/сборки.
- UI-тексты на русском; `print()` и диагностика только ASCII (CP1251-safe).
- Использовать `ft.icons.*`, не emoji и не `ft.Icons.*`.
- Цвета Flet с альфой — только `#AARRGGBB` (альфа первая), не CSS `#RRGGBBAA`. Для динамической альфы использовать `with_alpha()` из `ui/controls/glass_theme.py`.
- У скруглённого контейнера рамка только равномерная (`ft.border.all`), не разнотолщинный `border.only`.

### Flet 0.23.2: layout и обновления

- Внутри `Column(scroll=ft.ScrollMode.AUTO)` не использовать вертикальный `expand=True`; допустимы горизонтальные flex-спейсеры в ограниченном Row.
- Не использовать `wrap=True` в Row внутри прокручиваемых вкладок.
- Не использовать `animate*`, `gradient`, `shadow` и тяжёлый Python-hover на мелких элементах scroll-column.
- Не сочетать `scroll=HIDDEN + tight=True + expand=True` в одном Row.
- Для bounded-списка: ограниченный внешний контейнер и внутренний `Column(scroll=ft.ScrollMode.ALWAYS, expand=True)`.
- Не подписывать списки на `on_scroll`: на Windows Flet 0.23.2 возможны `KeyError: sd/dir`.
- Обновления немонтированных контролов — только через `_safe_update()`.
- Для событий/фонового polling использовать общий lock из `ui/update_lock.py`; нельзя параллельно менять дерево Flet и вызывать `page.update()` из разных потоков.
- FilePicker сначала добавить в `page.overlay`, вызвать `page.update()`, затем `pick_files()`/`save_file()`.
- Не использовать вложенные AlertDialog для выбора людей: карточка контроля — overlay/master-detail, выбор людей — inline.

## 3. Структура и хранение данных

```text
porayonka-app/
  main.py, main_web.py, requirements.txt
  core/                         # модели, данные, экспорт, edition, сеть
  ui/                           # общие компоненты, zonal/, controls/
  tests/test_controls_smoke.py
  tests/test_network_stress.py
  assets/                       # icon.png, pig.mp3, win7 DLL
```

Основные модули: `core/controls_models.py`, `controls_data.py`, `controls_exporter.py`, `controls_notify.py`, `control_locks.py`, `edition.py`; `ui/controls/controls_tab.py`; `ui/update_lock.py`; `ui/tray_icon.py`; `ui/sound_alert.py`.

Данные Python-версии: `%APPDATA%\porayonka\departments.json`, `zonal_collection.json`, `zonal_criminalists.json`, `templates\`, `controls.json`, `controls_settings.json`, `edition.json`, `controls_attachments\<control_id>\`, `error.log`.

Сетевой источник контролей — общий `controls.json`, путь по умолчанию:

```text
\\192.168.0.60\общая\Гайнутдинов\Porayonka workspace
```

В сетевом режиме локальный кэш объединяется с общим файлом по `id`, более свежий `updated_at` побеждает. Новые и изменённые записи должны подтягиваться при запуске и polling. Union-merge может сохранить локальную запись, удалённую из общего файла, если удаление не помечено отдельно — эту семантику не менять без отдельной задачи и теста.

## 4. Редакции admin/user

`core/edition.py` определяет `admin` или `user`.

- Frozen: встроенный `edition.json` имеет приоритет; рядом с exe также должны быть `edition.json` и `edition.json.bak`.
- Dev: `PORAYONKA_EDITION=admin|user`, `PORAYONKA_USER_NAME`.
- Admin — полный интерфейс. User — read-only: кнопки добавления, импорта, удаления, справочников и редактирования контролей физически не добавляются в дерево.
- User-сеть включена принудительно и показывает свои контроли/пункты по `network_user`.
- User без ФИО, зафиксированного установщиком, при первом запуске показывает «Кто вы?».
- Явный edition-файл не должен наследовать чужие `network_role`/`network_user` из appdata.
- Трей: закрытие окна скрывает его и оставляет polling; «Выход» останавливает polling, трей и процесс. Web-режим не ломать.

## 5. Функциональные инварианты

### Контроли

- Excel H: конечная дата разового контроля или `дата далее периодичность` для периодического. Excel I: `due_date`.
- User-экспорт и admin-экспорт с конкретным фильтром исполнителя используют `user_effective_due_date`; подсветка срока только для `OVERDUE`/`TODAY`, не для `SOON`.
- Импортированный `Control` обязан сразу иметь уникальный `id`; вложения используют тот же id и не дублируются при повторном FilePicker event.
- Исполнение пункта синхронизирует общий срок с ближайшим неисполненным пунктом.
- Полный справочник используется фильтрами; роли ограничивают выбор в карточке, но не отправляют существующие записи в «Прочие».

### Зональные и отделы

Не ломать фиксированный рабочий layout карточек криминалистов, клики, активность, фильтры, шаблоны, сводки, очистку, копирование не сдавших и Excel. Для отделов сохранять 29 отделов, три статуса, поиск, статистику, сброс, экспорт и порядок списка.

## 6. Запуск и обязательная проверка

Из `porayonka-app`:

```bat
python -m pip install -r requirements.txt
python main.py
```

После любых правок вкладки «Контроли», сети, Excel, edition, вложений или сборки:

```bat
python -m py_compile main.py main_web.py core\edition.py core\controls_data.py core\controls_models.py core\controls_notify.py core\controls_exporter.py ui\controls\controls_tab.py ui\controls\controls_settings_modal.py ui\controls\control_card_modal.py ui\controls\russian_calendar.py ui\controls\glass_theme.py
python -c "import sys; sys.path.insert(0, '.'); from ui.controls.controls_tab import create_controls_tab; print('OK')"
python tests\test_controls_smoke.py
python tests\test_network_stress.py
```

Stress-тест после изменений синхронизации запускать минимум три раза. Один `import main` недостаточен: вкладка «Контроли» импортируется лениво. Дополнительно выполнить живую проверку `python main.py`.

## 7. Сборка portable-дистрибутивов — подробная инструкция

Скрипты запускаются из `porayonka-app`, сами переходят в свой каталог. Перед сборкой закрыть exe и очистить заблокированные старые каталоги.

### 7.1 Полная сборка всех редакций (рекомендуется)

```bat
cd /d "C:\Users\User\Documents\Исходная программа\porayonka-app v2 DARK final\porayonka-app"
build_all_distributives.bat
```

Скрипт проверяет Python, ставит `requirements.txt`, `pystray`, `pillow`, `pyinstaller`, создаёт `assets\icon.ico`, получает Win7 DLL-стаб релиза 0.3.1, проверяет SHA256, собирает четыре spec и проверяет результаты. При отсутствии/неверной DLL Win7-сборка останавливается.

Результат:

```text
dist_all\Порайонка_Админ\              exe + edition.json + edition.json.bak
dist_all\Порайонка_Пользователь\       exe + edition.json + edition.json.bak
dist_all\Порайонка_Пользователь_Web\   exe + edition.json + .bak + start_web_win7.bat + DLL
dist_all\Порайонка_Админ_Web\          exe + edition.json + .bak + start_web_win7.bat + DLL
```

Desktop использовать на Win10/11. На Win7 использовать web-папку нужной редакции и `start_web_win7.bat`; нативный Flet-клиент Win7 не поддерживает. Переносить нужно всю папку, не только exe.

### 7.2 Отдельная admin desktop-сборка

```bat
cd /d "...\porayonka-app"
build_admin.bat
```

Использует `Porayonka_Admin.spec`, результат `dist\Порайонка_Админ.exe`, рядом UTF-8 `edition.json` с `{"role":"admin"}` и `.bak`.

### 7.3 Отдельная user desktop-сборка

```bat
cd /d "...\porayonka-app"
build_user.bat
```

Скрипт спрашивает ФИО. Enter оставляет его пустым, и приложение спросит «Кто вы?». Использует `Porayonka_User.spec`, создаёт UTF-8 `edition.json` с ролью user, ФИО (если задано) и `.bak`. Не заменять Python-запись JSON на `echo`: русское ФИО ломается в OEM/ANSI кодировке cmd.

### 7.4 Web-сборки для Windows 7

```bat
cd /d "...\porayonka-app"
build_user_web_win7.bat
build_admin_web_win7.bat
```

Используют `Porayonka_User_Web.spec` и `Porayonka_Admin_Web.spec`. Spec обязаны включать Flet static dirs `flet/web`, `flet/fastapi` и hidden imports `flet.web`, `flet.fastapi`, `uvicorn`, `fastapi`, `starlette`, иначе сервер отвечает HTTP 500. `main_web.py` ставит `PORAYONKA_WEB=1` и запускает `main._entry()` с `--web --host 0.0.0.0 --port 8555`.

Запуск:

```bat
start_web_win7.bat
```

По умолчанию: `http://127.0.0.1:8555`. Не удалять `_ensure_console_streams()`: при `console=False` stdout/stderr frozen exe могут быть `None`, а uvicorn использует их.

### 7.5 Spec, edition и очистка

- Актуальные spec: `Porayonka_Admin.spec`, `Porayonka_User.spec`, `Porayonka_Admin_Web.spec`, `Porayonka_User_Web.spec`.
- В spec должны быть `core;core`, `ui;ui`, `assets;assets`, актуальные hidden imports Flet и `build_edition\edition.json`.
- Перед PyInstaller создаётся `build_edition\edition.json`; после сборки временная папка удаляется.
- Admin: `{"role":"admin"}`; user: `{"role":"user"}` плюс `user_name`.
- `edition.json`/`.bak` писать только Python в UTF-8.
- Не смешивать `dist`, `dist_all`, `build` и редакции. При подозрении на старый артефакт использовать `--clean` и удалить соответствующий build/output.
- После сборки проверить имя exe, роль/ФИО JSON, `.bak`, Win7 DLL и web assets.

### 7.6 Inno Setup

После portable-сборки:

```bat
cd /d "...\porayonka-app\installer"
build_installers.bat
```

Поиск `iscc.exe`: `C:\porayonka_inno6\iscc.exe`, затем `C:\Program Files (x86)\Inno Setup 6\iscc.exe`, `C:\Program Files\Inno Setup 6\iscc.exe`, затем PATH. Собираются `Admin.iss`, `User.iss`, `UserWeb.iss`, `AdminWeb.iss`; результат в `installer\output\`.

Инварианты установщиков: автозапуск без дублей Tasks; запуск только на финальной странице; Admin без пароля установщика; user может пропустить ФИО; русское ФИО записывается через `SaveStringToUTF8File`; `edition.json` и `.bak` остаются рядом с exe.

### 7.7 Быстрый цикл после мелкой правки

```bat
cd /d "...\porayonka-app"
python -m py_compile main.py main_web.py core\edition.py core\controls_data.py ui\controls\controls_tab.py
python tests\test_controls_smoke.py
python tests\test_network_stress.py
build_all_distributives.bat
```

После сборки проверить: admin открывается сразу и не наследует user; user без кнопок редактирования получает сетевые контроли; web открывает браузер; Win7 DLL лежит рядом с web exe.

## 8. Запрещённые регрессии

Не повышать Flet, не возвращать старый `flet pack` как основной путь, не удалять embedded/sidecar edition, не переносить только exe, не возвращать `page.overlay.append(picker)` без `page.update()`, `on_scroll` у списков, вложенные модалки, параллельные Flet updates или массовый `git checkout` незакоммиченных файлов.

## 9. Старт нового чата

```bat
git status --short
git log -3 --oneline
cd porayonka-app
python tests\test_controls_smoke.py
```

В рабочем дереве могут быть незакоммиченные изменения сборочных файлов, кода синхронизации и тестов — сначала определить их назначение, не откатывать массово. Для проверки user после замены admin: сверить точный UNC-путь, доступ к общему `controls.json` под user, новые/изменённые записи, архивирование/удаление после перезапуска и отсутствие admin-функций.

## 10. Раунд 38 — новые инварианты (дедуп, backup, скан-гард, «Скачать» → «Открыть», Win7 web)

- **Дедупликация** (`core/controls_dedup.py`): business-key = NFKC + casefold входящего номера (все тире/разделители → `-`); пустой номер НЕ объединяет записи. Каноник: с вложениями → больше заполненных полей → свежее обновление. Вложения склеиваются по полному ПУТИ с побайтовым сравнением: одинаковые копии не плодятся, разные одноимённые файлы получают суффикс `_1`/`_2`. user-редакция никогда не пишет в сетевой `controls.json` (только читает); admin при старте лечит shared, перед лечением делает migration-backup.
- **Резервные копии** (`core/backup.py`): не чаще раза в сутки, при старте и в долгой работе; копируются все JSON + `controls_attachments`; tmp → атомарный rename; `manifest.json` (дата, версия схемы, состав, SHA256); частичный сбой не засчитывает день; retention ~30 копий; lock-файл от гонок; shared-backup только admin в `workspace/backups/YYYY-MM-DD` (offline не ломает локальный backup); restore документирован и покрыт тестом.
- **Скан задания обязателен** для НОВЫХ карточек (PDF или изображение): без него «Сохранить» блокируется подсказкой «Прикрепите скан задания (PDF или изображение)». Исторические контролы редактируются без скана (пилюля «Без скана», у `done` не показывается); Excel-импорт сканом не блокируется.
- **Вложение видно сразу**: перед навешиванием нового обработчика FilePicker старый ОТПИСЫВАЕТСЯ через `unsubscribe` — присваивание `on_result` в Flet 0.23.2 накапливает handlers, и событие уезжало в замыкание уже закрытой карточки. Регресс-чек «ровно 1 handler» живёт в smoke.
- **«Скачать» → «Открыть»**: `FilePicker.save_file` → побайтовая атомарная запись (tmp+rename) → toast → кнопка меняется на «Открыть»; Cancel ничего не меняет; файл удалён внешне — снова «Скачать»; web-режим отдаёт файл через `FLET_ASSETS_DIR/downloads` (browser download).
- **Excel upsert** (`import_plan` в `core/controls_exporter.py`): preview «новые/обновляемые/без изменений/конфликты/ошибки», конфликты молча не перетираются, перед применением — backup; существующие id, вложения и richer-поля не теряются; видимые колонки листа накладываются поверх скрытого full-листа.
- **Win7 web-профиль**: `requirements-win7-web.txt` (flet/flet-core/flet-runtime 0.23.2, fastapi 0.115.4, starlette 0.41.3, pydantic 1.10.26, uvicorn 0.32.0 — всё запинено); сборка только в чистом `.venv-win7-web`, жёсткий стоп при `pydantic_core`/pydantic 2.x; `upx=False` в web-spec; манифест собирает `tools/make_web_manifest.py`; `api-ms-win-core-path-l1-1-0.dll` кладётся рядом с web exe, desktop-ступени не меняются.
- **Обязательный контур** дополнен `tests/test_round38.py`; стресс-сценарии 11 и 14 перед «Сохранить» прикрепляют PDF (скан-гард), сценарий 13 проверяет «вложение видно сразу».
