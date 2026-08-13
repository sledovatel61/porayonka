# ПРОМПТ АГЕНТУ-АУДИТОРУ: РАУНД 31 — исправления после живой приёмки раунда 30

**Репозиторий:** `https://github.com/sledovatel61/porayonka.git` (ветка `main`)  
**Приложение:** `porayonka-app/main.py`  
**Запуск:** `python porayonka-app/main.py`  
**Flet:** строго `0.23.2`  
**Роль:** аудитор + исполнитель. Работай в своей arena-ветке, запушь, оркестратор внедрит в `main`.

## Контекст

После внедрения раунда 30 в `main` пользователь проверил три редакции из исходников (`set PORAYONKA_EDITION=admin/user` и web). Найдены баги. Нужно исправить их, сохранив весь существующий функционал (особенно сеть, locks, вложения, экспорт, авторизацию, read-only user).  
Перед правками **обязательно** прочитать `AGENTS.md` разделы **37**, **72**, **71** (раунд 29) и **70** (раунд 28). Там описаны ограничения Flet 0.23.2, цвета AARRGGBB, `_safe_update`, `ui_lock`, `update_lock`, network merge, locks, offline-вложения и т.д.

**Скрины:** `design/screenshots/13.08.2026/` (новые файлы уже в `main`):
- `Экспорт контролей у пользователя1.png` — обрезание ячеек в Excel.
- `Экспорт контролей у пользователя2.png` — список контролей у пользователя: контроль `Иссоп-216-1017-26/дсп` показан в «Просрочено 3», хотя просрочен пункт `п.6 — Семисенко И.Ю., Чащин Э.А. — 16.02.2026`, а пункт пользователя `п.2 — Миронович Д.В. — 01.05.2026` ещё не просрочен.
- `Отключить у пользователей возможность убирать звук уведомлений.png` — в настройках user-редакции есть переключатель звука.
- (Старые скрины раунда 30 остаются для истории.)

## Задачи раунда 31

### 1. Пароль админа в dev-режиме из исходников

**Симптом:** `set PORAYONKA_EDITION=admin` + `python main.py` сразу запрашивает пароль. Ввод `1` не принимается, повторные вводы бесполезны. После `move "%APPDATA%\porayonka\edition.json" …` пароль пропал.

**Причина:** в `core/edition.py::load_edition` переменные окружения задают `role=admin`, но `password_hash` продолжает подтягиваться из `%APPDATA%\porayonka\edition.json` (оставшегося от предыдущих тестов). `check_admin_password` сначала сверяет hash, а plain-пароль из `PORAYONKA_ADMIN_PASSWORD` не используется, если hash взят из файла.

**Что нужно:**
- Если `PORAYONKA_EDITION` (env) явно задаёт роль, она должна **полностью** переопределять редакцию для dev-запуска: `password_hash` и `password` из env имеют приоритет; если в env их нет — оставить пустыми, даже если в appdata/файлах рядом с exe есть hash.
- Сохранить backward compatibility: в сборках (frozen) `edition.json` рядом с exe должен по-прежнему побеждать env, если явно задан рядом с программой (т.е. установщик определяет дистрибутив). Но в dev-режиме env должна быть верховной.
- Простой вариант: приоритет env в `load_edition` — если env задана, не читать `password_hash`/`password` из файлов, только `role`/`user_name` из env (user_name может быть пустым). Для роли admin без env-пароля вход без пароля (как раньше в dev).
- Тест: smoke-тест §75/§86 `auth30` — дополнить сценарий: dev-запуск `PORAYONKA_EDITION=admin` с appdata-файлом, содержащим чужой `password_hash`, не должен требовать пароль; `PORAYONKA_ADMIN_PASSWORD=1` должен требовать пароль `1`.

**Файлы:** `core/edition.py`, `ui/admin_gate.py`, `tests/test_controls_smoke.py`.

### 2. Сетевой путь по умолчанию у user-редакции

**Симптом:** в user-настройках (и, вероятно, admin) отображается старый локальный путь, а не `\\192.168.0.60\общая\Гайнутдинов\Porayonka workspace`.

**Причина:** `DEFAULT_NETWORK_PATH` в `core/controls_data.py` применяется только при пустом `network_shared_path`. У пользователя в `controls_settings.json` сохранён старый локальный путь (например, `C:\…`), поэтому default не подхватывается.

**Что нужно:**
- В `load_settings()` добавить миграцию: если существующий `network_shared_path` **пустой** или **не начинается с `\\`** (не UNC-путь), заменить его на `DEFAULT_NETWORK_PATH` и сохранить настройки.
- Исключение: если пользователь явно ввёл другой UNC-путь — не трогать.
- Старые локальные пути типа `C:\…` или пустая строка — перезаписывать на default.
- Обновить smoke-тест: секция сетевых настроек проверяет, что `C:\local_path` мигрирует в `DEFAULT_NETWORK_PATH`, а `\\server\share` остаётся.

**Файлы:** `core/controls_data.py`, `tests/test_controls_smoke.py`.

### 3. Системный трей (frozen/сборка)

**Симптом:** пользователь говорит, что «админская версия падала в трей, а в пользовательской значка нет». Проверялось из `python main.py` — в dev-режиме трей по дизайну раунда 24 отключён (`sys.frozen` guard). Но для проверки дистрибутивов и удобства отладки трей должен быть стабильным.

**Что нужно:**
- Разрешить трей и в **dev-режиме**, если установлены `pystray`/`pillow` (guarded import), но не падать, если их нет. Убрать или смягчить `sys.frozen` guard: `if sys.platform != "win32": return None`; дальше — guarded import pystray/pillow; при ошибке — `print` и `None`. Это позволит пользователю `pip install pystray pillow` и тестировать трей без сборки exe.
- Убедиться, что в web-режиме трей открывает браузер (`web_url`), а в нативном — показывает окно (`page.window.to_front()`).
- Убедиться, что повторный вызов `start_tray` (например, при перезапуске `main()` в web) не пытается создать второй значок, а возвращает существующий (`_ACTIVE_ICON` singleton уже есть).
- Добавить тест (smoke): `start_tray` в dev-режиме с `pystray` установленным возвращает иконку; без pystray — `None`; повторный вызов возвращает тот же объект; web-режим — `web_url` в меню.

**Файлы:** `ui/tray_icon.py`, `main.py`, `tests/test_controls_smoke.py`.

### 4. Убрать у пользователей возможность отключать звук уведомлений

**Симптом:** в настройках user-редакции есть переключатель «Звук уведомлений».

**Что нужно:**
- В `ui/controls/controls_settings_modal.py` для `user`-редакции скрыть контрол `notify_sound` (чекбокс/переключатель). Вместо него показать read-only строку: «Звук уведомлений включён» (светлым текстом).
- Форсировать `settings["notify_sound"] = True` при сохранении настроек user-редакции.
- Для admin-редакции оставить возможность выключать звук (или тоже убрать? Пока только user — по требованию пользователя).
- Обновить smoke-тест §84/§85: в user-редакции в настройках нет чекбокса звука, значение `notify_sound` всегда True.

**Файлы:** `ui/controls/controls_settings_modal.py`, `tests/test_controls_smoke.py`.

### 5. Персонализация просрочек/сроков по пользователю (САМОЕ ВАЖНОЕ)

**Симптом:** user `Миронович Д.В.` видит в «Просрочено» контроль `Иссоп-216-1017-26/дсп`, потому что просрочен пункт `п.6 — Семисенко И.Ю., Чащин Э.А. — 16.02.2026`. Но этот пункт не назначен на Мироновича. У Мироновича в этом контроле пункт `п.2 — 01.05.2026`, который ещё не просрочен. Пользователь требует: «контроли по пунктам должны распределяться по пользователям в плане просрочек, а не показывать чужие».

**Что нужно:**
- Добавить в `core/controls_models.py`:
  - `user_effective_due_date(control: Control, user_name: str) -> Optional[date]` — минимальная дата среди **неисполненных** задач (`ControlTask`), где `user_name` есть в `assignees`. Если таких задач нет, fallback на общий `effective_due_date(control)` **только если** `user_name` присутствует в `executors` контроля или является `controller`. Иначе `None`.
  - `user_deadline_status(control: Control, user_name: str, soon_days: int = 3) -> str` — статус по `user_effective_due_date`. Если `None` → `IN_PROGRESS` (или `NONE`, но для фильтрации лучше статус, не попадающий в alarm/просрочку). Важно: если у пользователя нет активных задач в контроле, он не должен видеть этот контроль в просрочках/сегодня/скоро.
- Переписать `core/controls_notify.py::collect_alarm_controls(controls, soon_days, user_name=None)`:
  - Если `user_name` задан, фильтровать и сортировать по `user_deadline_status(..., user_name)` (OVERDUE/TODAY/SOON). Возвращать только контроли, у которых user-статус — alarm.
  - Если `user_name` не задан (admin), оставить текущее поведение по общему контролю.
- В `ui/controls/controls_tab.py`:
  - Счётчики «Просрочено / Сегодня / Скоро / В работе / Исполнено» в шапке (и фильтры по статусу) должны использовать **user-статус**, когда задан `network_user` (особенно в user-редакции). Для admin (network_user пустой) — общий статус.
  - Сортировка списка в user-режиме по `user_effective_due_date`.
  - Колонка «Срок исполн.» в таблице показывает `user_effective_due_date` для текущего `network_user` (с tooltip, показывающим общий срок контроля, если они отличаются).
  - `_check_my_notifications` использовать `user_deadline_status` и `collect_alarm_controls(..., user_name)`.
  - Убедиться, что `my_status_map` строится по user-статусу.
- В `core/controls_exporter.py`:
  - Экспорт admin-отчёта оставить общим статусом (как сейчас). Но убедиться, что жёлтая подсветка — только `OVERDUE` и `TODAY`; `SOON` не подсвечивать жёлтым (пользователь: «желтым должны подсвечиваться только контроли, которые либо просрочены, либо срок сегодня»). Опционально: `SOON` — без заливки, `OVERDUE` — красный/жёлтый, `TODAY` — жёлтый.
  - Убрать обрезание ячеек: для колонок «Содержание» (5) и «Исполнители» (6) включить `wrap_text=True` и увеличить ширину/высоту строки. Для «Содержание» уже wrap, но ширина маленькая; для «Исполнителей» добавить wrap. Рассмотреть автоподбор высоты строки по контенту (`content_lines` для исполнителей тоже).
- Тесты:
  - Новый smoke-раздел: контроль с двумя пунктами, один просрочен (чужой), один непросрочен (свой). User-фильтр «Просрочено» показывает 0, «Сегодня» 0, «Скоро» по своему пункту, «Все» 1. Admin-фильтр «Просрочено» показывает 1.
  - `collect_alarm_controls` с user_name возвращает только свой пункт.
  - Экспорт: ячейки «Содержание» и «Исполнители» имеют `wrap_text=True`; SOON не жёлтый.

**Файлы:** `core/controls_models.py`, `core/controls_notify.py`, `ui/controls/controls_tab.py`, `core/controls_exporter.py`, `tests/test_controls_smoke.py`, `tests/test_network_stress.py`.

### 6. Мелкие регрессии

- **Время:** убедиться, что ложное предупреждение о расхождении времени (раунд 30, задача 5) не появляется при корректном времени. Если вдруг появится — смягчить до не-модального toast.
- **Сетевые тесты:** не ломать `tests/test_network_stress.py` (85/104 проверок). После изменений в `collect_alarm_controls` и `controls_models` обновить тесты, если меняются сигнатуры.
- **Контракты:** не менять публичные сигнатуры без необходимости. `effective_due_date` и `deadline_status` оставить как есть (для admin/общих случаев). Добавить новые функции с `user_`-префиксом.

## Технические ограничения (проверено болью)

- Flet строго 0.23.2, без новых зависимостей (кроме опциональных pystray/pillow).
- Внутри `Column(scroll=AUTO)` — без `expand=True` (кроме горизонтальных спейсеров в Row), без `wrap=True`, без `animate*`, без `gradient`/`shadow` на мелких контейнерах.
- Цвета 8-digit — только `#AARRGGBB`.
- `print()` — ASCII, UI-текст — русский, `ft.icons.*`.
- Все `.update()` через `_safe_update()` (кроме горячих hover, там `_safe_update` молча).
- `ui_lock()`/`update_lock` (раунд 20) не трогать.
- Не ломать раунды 20–30: locks, network merge, offline-вложения, edition, read-only user, автозапуск, web.

## Проверка после правок (обязательно)

```bash
cd porayonka-app
python -m py_compile main.py main_web.py ui/admin_gate.py \
    ui/controls/controls_tab.py ui/controls/controls_settings_modal.py \
    ui/controls/control_card_modal.py ui/tray_icon.py \
    core/controls_data.py core/controls_models.py core/controls_notify.py \
    core/controls_exporter.py core/edition.py
python -c "import sys; sys.path.insert(0, '.'); from ui.controls.controls_tab import create_controls_tab; print('OK')"
python tests/test_controls_smoke.py    # ALL OK
python tests/test_network_stress.py     # ALL OK (104 проверки, 3 прогона)
```

## Результат

- Ветка `arena/XXXXXXXX-porayonka` с коммитом.
- Diff и описание фиксов для каждой задачи (причина + решение).
- Все smoke/stress-тесты зелёные.
- Оркестратор внедрит в `main` точечным `git checkout`.
