# PROMPT: Починка user-сборки — она определяется как admin

## Контекст

**Репозиторий:** https://github.com/sledovatel61/porayonka.git, ветка `main`  
**Локальная папка:** `porayonka-app/`  
**Запуск dev:** `python porayonka-app/main.py`

**Проблема:** `Порайонка_Пользователь.exe` (user-сборка) открывается с админским интерфейсом вместо пользовательского. Кнопки «Добавить контроль», «Импорт Excel» и другие admin-функции видны, хотя должны быть скрыты.

## Что уже известно

### Логика определения редакции (`core/edition.py`)

Функция `load_edition()` возвращает редакцию в порядке приоритета:
1. env `PORAYONKA_EDITION` / `PORAYONKA_USER` (только dev/тесты, не frozen)
2. `edition.json` рядом с exe — **абсолютный приоритет** (раунд 34)
3. `edition.json.bak` рядом с exe
4. `%APPDATA%/porayonka/edition.json` — fallback
5. Умолчание — `admin`

### Как работает `apply_edition_to_settings()`

В `ui/controls/controls_tab.py` вызывается после загрузки настроек:
- Для user-редакции: принудительно ставит `network_role="user"`, скрывает admin-кнопки
- Для admin-редакции: `network_role="admin"`, полный UI

### Сборочные файлы

- `build_user.bat` — portable-сборка, создаёт `dist/Порайонка_Пользователь.exe`
- После сборки bat-файл пишет `dist/edition.json` с `{"role": "user"}` через Python в UTF-8
- `Porayonka_User.spec` — PyInstaller spec для user-сборки

### Возможные причины проблемы (из раунда 35)

1. **`_app_dir()` возвращает неправильную папку в frozen onefile**: `Path(sys.executable).resolve().parent` должен возвращать папку exe, но может возвращать `_MEIPASS` или другую папку
2. **`edition.json` не попадает в нужную папку**: bat-файл кладёт его в `dist/`, но при копировании дистрибутива пользователю файл не копируется
3. **`%APPDATA%/porayonka/edition.json` перезаписывает настройки**: при первом запуске user-сборки что-то записывает в appdata admin-редакцию
4. **Кодировка `edition.json`**: несмотря на раунд 36 (fallback cp1251/cp866), файл может читаться неправильно

## Что нужно сделать

### Обязательно

1. **Добавить диагностику** в `load_edition()` и в начало `create_controls_tab`:
   - Путь к `sys.executable`
   - Результат `_app_dir()`
   - Наличие и содержимое `edition.json` рядом с exe
   - Наличие и содержимое `%APPDATA%/porayonka/edition.json`
   - Итоговая роль из `load_edition()`
   - Всё печатать ASCII (без русских букв в print)

2. **Проверить `_app_dir()` в frozen onefile**:
   - Запустить собранный `Порайонка_Пользователь.exe` (или сделать тестовую сборку)
   - Убедиться, что `sys.executable` указывает на правильный exe
   - Убедиться, что `_app_dir()` возвращает папку с `edition.json`

3. **Проверить размещение `edition.json`**:
   - В portable-сборке `edition.json` должен быть РЯДОМ С EXE, в той же папке
   - При копировании дистрибутива пользователю копировать ОБА файла (exe + edition.json)

4. **Проверить приоритет источников**:
   - Если `edition.json` рядом с exe существует и содержит `role: "user"`, он должен победить
   - `%APPDATA%` не должен перезаписывать явную user-редакцию

5. **Если `edition.json` не читается**:
   - Проверить кодировку файла (должен быть UTF-8)
   - Проверить формат JSON (должен быть валидный `{"role": "user"}`)

### Тесты

После исправления:
- Собрать user-версию через `build_user.bat`
- Запустить exe из папки `dist/`
- Проверить, что редакция определяется как `user` (видна диагностика в консоли/логе)
- Проверить, что admin-кнопки скрыты
- Проверить, что user-интерфейс работает корректно

## Ограничения

- Flet строго 0.23.2
- Не ломать admin-сборку (`build_admin.bat`)
- Все print() — только ASCII
- UI-текст — русский
- Не добавлять новые зависимости

## Где смотреть

- `core/edition.py` — определение редакции
- `ui/controls/controls_tab.py` — применение редакции к UI
- `build_user.bat` — сборка user-версии
- `Porayonka_User.spec` — PyInstaller spec

## Выход

Агент работает в отдельной ветке `arena/XXXX-porayonka` от main.
В последнем сообщении — точное имя ветки.

После завершения оркестратор:
1. Подтянет ветку: `git fetch origin <branch> && git worktree add ../porayonka-fix origin/<branch>`
2. Проверит изменения
3. Внесет в main: `git checkout main && git checkout origin/<branch> -- <files>`
4. Закоммитит и запушит