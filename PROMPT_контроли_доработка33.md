# Раунд 33 — hotfix: admin-версия (серый экран после пароля), трей в нативных exe, "О программе", чистка appdata-наследия

**Дата:** 2026-08-14  
**База:** `main`, коммит `010a757ce9b9d6491182b61d728494e7d9ec8256`  
**Скрины:** `porayonka-app v2 DARK final/LLM/14.08.2026/`:
- `Вдмин запрашивает пароль.png` — диалог входа админа, окно работает;
- `ввел пароль админа.png` — после ввода пароля окно приложения полностью серое, UI не отрисовывается;
- `Запустил админ версию, загрузился пользователь Миронович.png` — после удаления `edition.json` и `edition.json.bak` из папки exe запускается пользовательский режим с сетью "пользователь" и данными Мироновича;
- `Не помещается текст в о программе.png` — диалог "О программе", текст справа обрезается и выходит за границы панели.

## 1. Баги, найденные при живом тесте portable exe на Windows

### 1.1 Admin-версия: после ввода пароля — серый экран, приложение мёртвое

**Сценарий:**
1. Запуск `Порайонка_Админ.exe` (в папке лежит `edition.json {"role":"admin"}`).
2. Появляется диалог "Вход: администраторская редакция".
3. Ввод пароля → "Войти".
4. Окно приложения остаётся **серым/пустым**, вкладки не появляются, окно не реагирует.

**Диагностика пользователя:**
- Если удалить `edition.json` и `edition.json.bak` из папки с exe, приложение запускается (уже без диалога пароля), но в **пользовательском режиме** от имени Мироновича.
- Это говорит о том, что в `%APPDATA%/porayonka/controls_settings.json` сохранились `network_role="user"` и `network_user="Миронович Д.В."` от предыдущего запуска пользовательской версии, и даже при `role="admin"` в `edition.json` приложение падает/схлопывается на конфликте или диалог парода не отпускает UI-поток.

**Что нужно сделать:**
1. Гарантированно закрыть/удалить диалог пароля **до** вызова `_main_impl()`. В раунде 32 делалось `page.close(dlg)` + `dlg.open=False` + удаление из `_Page__offstage.controls` + `page.update()`. Возможно, в frozen-сборке `console=False` очередь update не сбрасывается или диалог остаётся в overlay. Попробовать комбинации:
   - `page.close(dlg)` → `page.update()` → `_main_impl()`;
   - `dlg.open = False` → `page.update()` → `_main_impl()`;
   - явное `page.overlay.remove(dlg)` / `page._Page__offstage.controls.remove(dlg)` → `page.update()` → `_main_impl()`;
   - отложенный вызов `_main_impl()` через `page.run_thread` или таймер.
2. При **явной admin-редакции** (`edition.json` рядом с exe содержит `"role":"admin"`) приложение должно **игнорировать** сохранённые `network_role`/`network_user` в `controls_settings.json` и всегда стартовать как admin с полным UI. Т.е. `apply_edition_to_settings()` для admin должен принудительно сбрасывать `network_role="admin"` и `network_user=""` (или оставлять пустым), независимо от appdata.
3. Проверить, что в `_main_impl()` нет запрещённых layout-паттернов, вызывающих схлопывание: `Column(scroll=AUTO, expand=True)`, `wrap=True`, `animate`, `gradient`/`shadow` на мелких контейнерах. После диалога пароля корневой layout должен быть таким же рабочим, как и без диалога.
4. Добавить **файловое логирование необработанных исключений** для frozen-сборок: `console=False`, поэтому падения невидны. Перехват `sys.excepthook` + запись в `%APPDATA%/porayonka/error.log` (с ротацией, max 500 КБ). Это критично для диагностики серого экрана.

### 1.2 Трей в нативных admin/user exe: "Открыть" не восстанавливает окно

**Сценарий:**
- Закрываешь окно админской или пользовательской версии крестиком — приложение сворачивается в трей.
- Клик по значку "Открыть" — окно **не появляется**.
- В web-версии (`Порайонка_Пользователь_Web.exe`) трей работает корректно.

**Что нужно сделать:**
1. В `ui/tray_icon.py` функция `_show` должна восстанавливать окно в обычных exe:
   - `page.window.visible = True`
   - `page.window.minimized = False`
   - `page.window.to_front()`
   - `page.update()`
   - при необходимости `page.window.maximized = False` или `page.window.focus()`.
2. Добавить отладочный `print` (ASCII) в `_show` и в `_on_window_event` в `main.py`, чтобы в логе было видно, вызывается ли обработчик.
3. Проверить, что в `main.py` для нативных exe при `on_window_event == "close"` вызывается сворачивание (`page.window.visible = False`) только если `page._tray_icon` существует, иначе — обычный выход.
4. Возможно, для frozen exe нужно инициализировать `page.window.on_event` после `page.window` и до запуска трея.

### 1.3 Диалог "О программе" — текст не помещается

**Симптом:** текст справа обрезается, видны хвосты строк за границей панели.

**Что нужно сделать:**
1. Увеличить ширину и/или высоту диалога.
2. Внутренний контент обернуть в `Column(scroll=AUTO)` с ограниченной высотой.
3. Убедиться, что текст переносится корректно (wrap). Внутри `Column(scroll=AUTO)` нельзя `expand=True`, но `Text` с `max_lines` и переносом допустим.
4. Сделать так, чтобы диалог помещался на экране 1280×720 и выше.

### 1.4 User-версия не спрашивает ФИО, потому что appdata помнит старого пользователя

**Симптом:** при запуске `Порайонка_Пользователь.exe` диалог "Кто вы?" не появляется, сразу открывается режим Мироновича.

**Что нужно сделать:**
1. При user-редакции:
   - если `edition.json` рядом с exe содержит `user_name` — использовать его, не спрашивать;
   - если `user_name` нет — **всегда** показывать диалог "Кто вы?", независимо от `network_user` в `controls_settings.json`.
2. Явная user-редакция с пустым `user_name` должна сбрасывать сохранённый `network_user` в appdata, чтобы не было наследия от admin или другого user.
3. Admin-редакция должна сбрасывать `network_user` и `network_role` в appdata (уже частично делалось в раунде 32, но видимо не полностью работает в frozen).

## 2. Обязательные действия

### 2.1 Логирование ошибок в файл

Добавить в `main.py` (или отдельный модуль `core/crash_log.py`):
```python
import sys, traceback, os
from datetime import datetime

def _install_crash_hook():
    def _hook(exc_type, exc_value, tb):
        log_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "porayonka")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "error.log")
        if os.path.exists(log_path) and os.path.getsize(log_path) > 500_000:
            os.remove(log_path)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] {exc_type.__name__}: {exc_value}\n")
            traceback.print_tb(tb, file=f)
            f.write("\n")
        sys.__excepthook__(exc_type, exc_value, tb)
    sys.excepthook = _hook
```
Вызвать `_install_crash_hook()` первой строкой в `main.py`/`main_web.py`.

### 2.2 Проверка и доработка `apply_edition_to_settings`

В `core/edition.py` и `ui/controls/controls_tab.py`:
- Admin-редакция: `network_role = "admin"`, `network_user = ""`.
- User-редакция: `network_role = "user"`; если `user_name` задан в edition.json — `network_user = user_name`, иначе `network_user = ""` (диалог "Кто вы?").
- Сохранять настройки сразу после применения edition.
- Эти действия должны выполняться **до** построения таблицы.

### 2.3 Починка диалога пароля

В `ui/admin_gate.py`:
- Добавить флаг `_closed`.
- После успешной проверки пароля выполнить строго:
  ```python
  _closed = True
  page.close(dlg)
  dlg.open = False
  try:
      page._Page__offstage.controls.remove(dlg)
  except Exception:
      pass
  page.update()
  on_ok()
  ```
- Если диалог всё равно остаётся — попробовать обернуть `on_ok()` в `page.run_thread(lambda _: on_ok(), None)` с задержкой.

### 2.4 Трей в нативных exe

В `ui/tray_icon.py`:
- `_show` обязательно делает `page.window.minimized = False`.
- Добавить `page.window.visible = True`.
- Добавить `page.window.to_front()`.
- Добавить `page.update()`.
- В frozen-сборке возможно нужно `page.window.focus()` или `page.window.maximized = False`.

В `main.py`:
- `_on_window_event` при `"close"`: если `page._tray_icon` есть — `page.window.visible = False`, иначе — выход.
- Убедиться, что `page.window.on_event = _on_window_event` назначается раньше `start_tray`.

### 2.5 "О программе"

В `ui/header.py` или где диалог "О программе":
- Увеличить размер контейнера диалога (например, `width=720, height=520`).
- Внутри `Column(scroll=AUTO)` с фиксированной высотой.
- `Text` с `max_lines=None` или `max_lines=10` и переносом.

## 3. Что сохранить

- Весь текущий функционал вкладки "Контроли" (фильтры, карточка, Excel, сеть, архив, вложения, алармы, справочники).
- Flet 0.23.2, без новых зависимостей.
- Layout-ограничения AGENTS.md.
- ASCII print, русский UI, цвета AARRGGBB.

## 4. Что не трогать

- Вкладки "Следственные отделы" и "Зональные криминалисты".
- Сетевой режим, синхронизация, Excel round-trip.
- Звук, web-режим (кроме трея, если он там работает — не сломать).

## 5. Проверка

```bash
cd porayonka-app
python -m py_compile main.py main_web.py ui/admin_gate.py ui/tray_icon.py \
    core/edition.py ui/controls/controls_tab.py ui/controls/controls_settings_modal.py \
    core/crash_log.py
python -c "import sys; sys.path.insert(0, '.'); from ui.controls.controls_tab import create_controls_tab; print('OK')"
python tests/test_controls_smoke.py   # ALL OK
python tests/test_network_stress.py   # ALL OK
```

**Живая проверка (обязательна):**
1. Собрать `Порайонка_Админ.exe` и `Порайонка_Пользователь.exe`.
2. Сначала запустить user-версию, выбрать ФИО "Миронович Д.В.", закрыть.
3. Затем запустить admin-версию — должен запросить пароль (если установлен), принять его, открыться в admin-режиме, без наследия user.
4. Проверить трей: закрыть окно крестиком → значок в трее → "Открыть" → окно восстанавливается.
5. Открыть "О программе" — текст полностью виден, есть скролл при необходимости.
6. Если admin падает/серый экран — проверить `%APPDATA%/porayonka/error.log` и приложить его к ответу.

## 6. Результат

- diff для внедрения в `main`;
- обновлённый `AGENTS.md` §75 с результатами;
- три собранных/проверенных portable exe (или готовый код + инструкция для оркестратора).
