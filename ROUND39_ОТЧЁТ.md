# Раунд 39 — отчёт исполнителя

Ветка: `arena/01a06c6a-porayonka`
Remote: `https://github.com/sledovatel61/porayonka.git`
Baseline: `f460fd8` (`Add files via upload`, = `origin/main`)
Промпт оркестратора: `PROMPT_новому_агенту_восстановление_Round39.md`
(взят из ветки `round39-recovery-prompt`, коммит `5f2f6ce` — ветка и SHA
подтверждены `git ls-remote`).

## 0. Проверка исходного состояния

Заявления оркестратора о состоянии репозитория **подтвердились**:

| Заявление | Проверка | Результат |
|---|---|---|
| `core/single_instance.py` отсутствует | `test -e` | MISSING |
| `ui/lazy_tabs.py` отсутствует | `test -e` | MISSING |
| `tests/test_round39.py` отсутствует | `test -e` | MISSING |
| `ROUND39.patch` отсутствует | `test -e` | MISSING |
| `round39-files.zip` отсутствует | `test -e` | MISSING |
| Коммиты `e577fef` / `ef6f8ab` недоступны | `git log` | в истории только `f460fd8` |
| Ветка `round39-recovery-prompt` @ `5f2f6ce` существует | `git ls-remote origin` | `5f2f6ce898206192346a4a48d4e97612e3f24b14  refs/heads/round39-recovery-prompt` |

Baseline до правок был зелёным: `py_compile` OK, импорт `create_controls_tab`
OK, `test_controls_smoke` / `test_network_stress` (123 проверки) /
`test_round38` — все `ALL OK`, exit 0.

## 1. Конечная дата периодического контроля

**Первопричина.** У поля конечной даты (`end_box` в
`ui/controls/controls_tab.py`) не было команды очистки: ни крестика в поле,
ни «Очистить» в глобальном календаре (`_open_global_cal` имел только
«Сегодня» и «Закрыть»). Выставленную дату нельзя было снять — только
перезаписать.

**Исправление.**
- В `end_box` добавлен `end_clear_btn` (иконка CLEAR, tooltip
  «Очистить конечную дату (сделать «не указана»)»), виден только когда дата
  задана и не в user-редакции. Паттерн — тот же, что уже проверен в
  `create_russian_date_field` (внутренний IconButton перехватывает клик
  раньше `on_click` контейнера).
- В **единственный** глобальный календарь добавлена кнопка «Очистить»,
  видимая только когда поле открыто с `can_clear=True`. Второй независимый
  календарь **не создавался** — используется существующий контракт
  `setter(Optional[str])`.
- `_set_end(None)` → `detail_state["end_date"] = None`, поле показывает «—»,
  крестик скрывается.
- `_on_type_change`: переход `periodic -> one-time` обнуляет скрытое
  значение `end_date`. Отслеживается **предыдущий** тип (`_type_prev`), а не
  наличие даты — иначе обнуление срабатывало бы на любом `on_change` и
  стирало «срок разового контроля» из колонки H Excel (регресс раунда 22).

**Проверено тестами** (`r39-1.0a` … `r39-1.12c`): round-trip модели
(очистка → сохранение → `end_date is None` → повторное открытие не
возвращает дату → выбор новой даты → сохранение), неизменность
`due_date`/`period_days`/`tasks`/`milestones`, отсутствие «Очистить» у
`due`, раунд 22 сохранён, Excel round-trip для пустой и заданной даты.

## 2. Ленивые вкладки

**Первопричина.** `main.py` вызывал `create_zonal_tab(page)` и
`create_controls_tab(page)` на старте, до `page.add()` — пользователь видел
только «Контроли», но платил за построение всех трёх деревьев.

**Исправление.** Новый модуль `ui/lazy_tabs.py` — `LazyTabHost`
(build-on-first-use + кэш экземпляра, построение под общим UI-lock из
`ui/update_lock.py`). В `main.py` бывший inline-код вкладки отделов вынесен
в `_build_departments_tab()` **без изменений**; «Зональные» и «Контроли»
используют те же `create_zonal_tab()` / `create_controls_tab()`. Порядок
вкладок и активная по умолчанию (index 0 = «Контроли») не изменились.
Диагностика build/reuse — отключаемая (`PORAYONKA_LAZY_TAB_DIAG=1`),
ASCII-safe.

**Проверено тестами** (`r39-2.1a` … `r39-2.8g`), в том числе на **реальном**
`main._main_impl`:

```
СТАРТ:            {'zonal': 0, 'controls': 1, 'departments': 0}
первый переход:   {'zonal': 1, 'controls': 1, 'departments': 0}
7 переходов туда-сюда: {'zonal': 1, 'controls': 1, 'departments': 1}
```

Плюс: 12 конкурентных `get()` → builder вызван 1 раз, все потоки получили
один экземпляр.

## 3. Один владелец открытия браузера

**Первопричина.** На запуске через bat срабатывали два открывателя:
`ft.app(view=AppView.WEB_BROWSER)` и `start http://127.0.0.1:8555` в
`start_web_win7.bat`.

**Владелец — FLET** (`BROWSER_OWNER = "flet:AppView.WEB_BROWSER"` в
`main.py`, обоснование в комментарии). `start_web_win7.bat` теперь только
запускает сервер, ждёт HTTP-доступности и **печатает адрес**. Заодно bat
перебирает порты 8555..8564 (раньше ждал жёстко 8555 и ошибочно сообщал
«сервер не ответил», когда `main_web.py` уезжал на свободный порт).

`main_web.py::_open_browser()` оставлен: он вызывается **только** в ветках
повторного запуска, где процесс завершается `sys.exit(0)`, не доходя до
`ft.app()` — то есть Flet в таком процессе браузер не открывает физически.
Это зафиксировано AST-тестом (`r39-3.3b`: orphan-веток 0).

## 4. Tray и single-instance

**Первопричины.**
1. Проверка `if _ACTIVE_ICON is not None` в `start_tray()` была **без
   блокировки**. Flet 0.23.2 исполняет обработчики событий в
   `ThreadPoolExecutor`, а в web-режиме `main()` вызывается на каждую
   браузерную сессию → два параллельных входа создавали два `pystray.Icon`.
2. Single-instance guard'а не было вообще.

**Исправление.**
- `ui/tray_icon.py`: double-checked locking (`_TRAY_LOCK`) — проверка и до,
  и после lock; весь участок «проверка → import → иконка → `run_detached` →
  публикация `_ACTIVE_ICON`» неделим. Добавлен `stop_tray(icon=None,
  release_guard=False)`; `icon.stop()` теперь вызывается **ровно один раз**
  (раньше `_quit` звал `stop()` и сам, и через реестр).
- Новый модуль `core/single_instance.py`: Windows named mutex
  `Local\Porayonka_<edition>` через `CreateMutexW`. Семантика:
  `acquired` / `already_exists` (**не** fail-open) / `fail_open` — только
  когда API невозможно вызвать. Чужой handle закрывается, чтобы второй
  процесс не становился держателем. Есть `focus_existing()` (передача
  управления первому экземпляру) и идемпотентный `release()` + `atexit`.
- `main.py::_entry()` desktop-ветка занимает guard **до** `ft.app`, при
  занятом mutex — `focus_existing()` и `return`; освобождение в `finally` и
  в «Выходе» из трея.

**Проверено тестами** (`r39-4.1a` … `r39-4.11c`) с моками pystray/ctypes:
10 конкурентных `start_tray()` → 1 `pystray.Icon`, 1 `run_detached`, все
потоки получили один объект; `ERROR_ALREADY_EXISTS` → `(False,
"already_exists")` и `status() == "already_exists"` (не fail-open);
недоступный API → fail-open.

## 5. Excel-импорт в Admin Win7 Web

**Две первопричины** (обе подтверждены живым запуском).

1. `_on_import_picked` брал только `e.path` / `e.files[0].path`. В браузере
   `FilePickerResultEvent.files[*].path == None` → код уходил в
   `if not path: return`. Файл надо **загружать**: `picker.upload([
   FilePickerUploadFile(name, page.get_upload_url(name, expires))])` и ждать
   `on_upload` с `progress == 1.0` и `error is None`.
2. Сервер не регистрировал эндпоинт загрузки:
   `flet/fastapi/app.py` создаёт `PUT /upload` только при заданном
   `upload_dir` (из `FLET_UPLOAD_DIR`), а подпись запроса
   (`flet_runtime/uploads.py:get_upload_signature`) требует
   `FLET_SECRET_KEY`. Не было ни того, ни другого.

**Живое доказательство** (Linux, Flet 0.23.2, реальный uvicorn):

| Сценарий | `PUT /upload` |
|---|---|
| Без `FLET_UPLOAD_DIR` (контрольный опыт) | **405 Method Not Allowed** |
| С `FLET_UPLOAD_DIR`, без `FLET_SECRET_KEY` | 500, `Specify secret_key parameter or set FLET_SECRET_KEY...` |
| После исправления (`main.py --web`, порт 8599) | **200**, файл лёг в `web_uploads/probe39.xlsx`, 89068 байт = размеру исходника, читается openpyxl |

`GET /` → **HTTP 200**.

**Исправление.**
- `main.py::_entry()` web-ветка задаёт `FLET_UPLOAD_DIR`
  (`%APPDATA%\porayonka\web_uploads`) и `FLET_SECRET_KEY`
  (`%APPDATA%\porayonka\upload_secret.key`, `secrets.token_hex(32)`,
  стабилен между перезапусками) — оба **до** `ft.app`.
- `controls_tab.py`: `_on_import_picked` обрабатывает `path`,
  `files[*].path`, отмену (нет ни того ни другого → toast «Импорт отменён»)
  и web-форму (нужен upload). Цепочка колбэков
  `on_result → picker.upload() → on_upload → _preview_import`, **без
  блокирующего ожидания** — тело обработчика исполняется под общим UI-lock,
  ожидание внутри `on_result` было бы дедлоком.
- Импорт стартует только после проверки, что физический `.xlsx` существует
  (`os.path.isfile`) и имеет расширение `.xlsx`. Фиктивные пути запрещены.
- `on_upload` подписывается **ровно один раз**: старая подписка снимается
  через `EventHandler.unsubscribe` (та же первопричина накопления
  обработчиков, что чинил раунд 38 для `on_result`).
- Все отказы → русский toast + ASCII-safe запись в
  `%APPDATA%\porayonka\error.log`.
- Preview/upsert/backup, категории, уникальные id, rich-поля и вложения не
  тронуты — используется прежний `_preview_import`. Desktop-путь (`e.path`)
  не изменился; user-редакция импорта не получает.

**Проверено тестами** (`r39-5.0a` … `r39-5.11g`): пустая модель → выбор xlsx
→ upload → `progress 0.42` (импорт не запускается) → `progress 1.0` → preview
(«Новые: 2», «Конфликты: 0») → «Импортировать» → 2 записи в модели и в
таблице; отмена; ошибка upload; «файл не доехал»; не-xlsx; повторный импорт
(`on_upload` по-прежнему 1 подписка); desktop-импорт без upload.

## Обязательный тестовый контур

Выполнено из `porayonka-app`, полный вывод сохранён в
`porayonka-app/ROUND39_проверки.log` (нормализован в UTF-8; 10 мусорных
байтов из предсуществующего вывода `test_controls_smoke` заменены на U+FFFD).

| Команда | Код возврата | Итог |
|---|---|---|
| `python -m py_compile main.py main_web.py core/edition.py core/controls_data.py core/controls_models.py core/controls_notify.py core/controls_exporter.py ui/controls/controls_tab.py ui/controls/controls_settings_modal.py ui/controls/control_card_modal.py ui/controls/russian_calendar.py ui/controls/glass_theme.py ui/zonal/zonal_tab.py` | 0 | OK |
| `python -c "...from ui.controls.controls_tab import create_controls_tab..."` | 0 | OK |
| `python tests/test_controls_smoke.py` | 0 | ALL OK |
| `python tests/test_network_stress.py` (×3) | 0 / 0 / 0 | ALL OK (123 проверки каждый) |
| `python tests/test_round38.py` | 0 | ALL OK |
| `python tests/test_round39.py` | 0 | ALL OK (153 проверки) |

Суммарно в логе: **1555 строк `[OK ]`, 0 строк `[FAIL`**.

Живой web-запуск: `python main.py --web --host 0.0.0.0 --port 8599` →
порт слушает, `GET /` = 200, `PUT /upload` = 200 с реальным файлом.

## Что НЕ проверено и почему

- **Физический Windows 7.** Здесь нет Win7: named mutex, `pystray`,
  `FindWindowW`, `start_web_win7.bat` и поведение нативного клиента Flet
  проверены только моками/статикой. Ручной Win7-прогон не выполнялся и за
  него не выдаётся.
- **Portable-сборки и Inno Setup.** PyInstaller/ISCC в этом окружении нет;
  `.spec` и `.iss` не менялись и не пересобирались.
- **Реальный браузерный upload.** `main(page)` в web-режиме вызывается
  только при подключении браузерного клиента; здесь браузера нет. Поэтому
  проверен весь путь **кроме** самого клика в диалоге: подпись URL той же
  функцией, что и `page.get_upload_url()`, реальный `PUT` и появление файла
  в том каталоге, где его ищет `_uploaded_path()`.
- **Desktop-трей вживую** (Linux-хост) — только мок pystray.

## Изменённые файлы

Мои изменения:

```
porayonka-app/main.py                       (M)  +ленивые вкладки, guard, FLET_UPLOAD_DIR/SECRET_KEY, BROWSER_OWNER
porayonka-app/start_web_win7.bat            (M)  убран `start http://`, перебор портов 8555..8564
porayonka-app/ui/controls/controls_tab.py   (M)  очистка конечной даты, web-upload импорта
porayonka-app/ui/tray_icon.py               (M)  double-checked locking, stop_tray, release guard
porayonka-app/core/single_instance.py       (A)  named mutex guard
porayonka-app/ui/lazy_tabs.py               (A)  LazyTabHost
porayonka-app/tests/test_round39.py         (A)  153 проверки
porayonka-app/ROUND39_проверки.log          (A)  полный вывод обязательного контура
ROUND39_ОТЧЁТ.md                            (A)  этот файл
```

Чужие незакоммиченные изменения (`build_all_distributives.bat`,
`installer/*.iss`, `installer/build_installers.bat`, `.venv-win7-web/`),
которые упоминал оркестратор, **в этом checkout отсутствуют** — дерево до
моих правок было чистым (`git status --short` пуст). Ничего не откатывалось
и не форматировалось.

Файл `PROMPT_новому_агенту_восстановление_Round39.md` — **не моё
изменение**: он взят из ветки оркестратора `round39-recovery-prompt`
(`5f2f6ce`) и закоммичен отдельным коммитом, чтобы коммит с кодом содержал
только мои правки.

## Оставшиеся риски

1. `end_clear_btn` внутри кликабельного `Container` опирается на то, что
   Flutter отдаёт клик внутреннему IconButton. Паттерн уже работает в
   `create_russian_date_field`, но на живом Win7-клиенте это стоит
   проверить глазами.
2. `Local\`-mutex per-session: в разных RDP-сессиях одного пользователя
   экземпляр может быть свой. Для Win7-машин (одна консольная сессия) это не
   проблема.
3. `FLET_SECRET_KEY` хранится в `%APPDATA%` в открытом виде. Он защищает
   только подпись локального upload-запроса к localhost-серверу, но если
   сервер поднят на `0.0.0.0` в недоверенной сети — это надо учитывать.
4. `_build_departments_tab()` при первом переходе вызывает
   `page.overlay.extend([export_modal, reset_modal])`. До первого перехода
   на «Следственные отделы» этих модалок в overlay нет — они и не доступны,
   но если будущая правка обратится к ним раньше, получит отсутствующий
   контрол.
