# Промпт агенту: раунд 36 — починка user-установщиков и списка ФИО в настройках

**База:** `main` коммит `11ef639` (после hotfix edition.json).
**Ветка:** `arena/XXXXXXXX-porayonka` (новая).
**Промпт:** `porayonka-app/PROMPT_контроли_доработка36.md`.

## Симптомы после раунда 35

1. **User-установщики (`Порайонка_Пользователь_Setup.exe`, `Порайонка_Пользователь_Web_Setup.exe`) дают админские права.** При установке на ПК пользователя приложение открывается с admin UI (видны «Импорт Excel», «Удалить все», секция пароля в настройках).
2. **В настройках user-версии не виден сотрудник, добавленный в справочник.** Пользователь добавил «Толстолуцкий С.А.» в справочник (через кнопку «Справочники»), он появился в фильтрах, но в настройках (шестерёнка → «Пользователь (ФИО)») его нет.

## Вероятные причины

### 1. `edition.json` рядом с exe невалиден для Python

В `installer/User.iss` / `installer/UserWeb.iss` `CurStepChanged` пишет `edition.json` через `SaveStringToFile(..., False)`. Inno Setup 6 `SaveStringToFile` сохраняет строку в **системной ANSI-кодировке** (на русской Windows — CP1251). Если в JSON есть русское ФИО (`"user_name": "Авакян А.А."`), Python `_read_edition_file(..., encoding='utf-8')` падает с `UnicodeDecodeError` → файл считается невалидным.

Раунд 35 hotfix добавил защиту: `elif main_f.exists(): return _mk(EDITION_ADMIN, ...)` — то есть невалидный `edition.json` рядом с exe превращается в **default admin**. Это и есть причина «user-установщик даёт admin».

**Что сделать:**
- В `core/edition.py::_read_edition_file` добавить fallback-кодировку: сначала `utf-8-sig`, при `UnicodeDecodeError` — `cp1251` (или `locale.getpreferredencoding()`).
- Проверить, что `edition.json` с русским ФИО в CP1251 читается корректно.

### 2. Настройки user используют неполный список людей

В `ui/controls/controls_settings_modal.py` строка 85: `criminalist_names = get_criminalist_names()`. Эта функция возвращает только криминалистов + дефолтных контролёров, но **не** включает `extra_people` (людей, добавленных через «Справочники»).

**Что сделать:**
- Заменить `get_criminalist_names()` на `get_all_people_names(settings)` в `controls_settings_modal.py`.
- Убедиться, что в настройках user-версии видны все люди из справочника (криминалисты + контролёры + доп. ФИО).

## Что нужно сделать

1. **Починить чтение `edition.json`**:
   - `core/edition.py::_read_edition_file` — fallback на CP1251/ANSI при ошибке UTF-8.
   - Добавить тест: `edition.json` с русским ФИО в CP1251 → `load_edition()` возвращает `user` + правильное ФИО.

2. **Починить список ФИО в настройках**:
   - `ui/controls/controls_settings_modal.py` — использовать `get_all_people_names(settings)` вместо `get_criminalist_names()`.
   - Проверить, что `extra_people` отображаются в dropdown «Пользователь (ФИО)».

3. **Пересобрать только user и web установщики** (admin не трогать):
   - `porayonka-app/dist_all/Порайонка_Пользователь/`
   - `porayonka-app/dist_all/Порайонка_Пользователь_Web/`
   - `porayonka-app/installer/output/Порайонка_Пользователь_Setup.exe`
   - `porayonka-app/installer/output/Порайонка_Пользователь_Web_Setup.exe`

4. **Проверки:**
   - `python -m py_compile` всех затронутых файлов.
   - `python -c "import sys; sys.path.insert(0, '.'); from ui.controls.controls_tab import create_controls_tab; print('OK')"`.
   - `python tests/test_controls_smoke.py` — ALL OK.
   - `python tests/test_network_stress.py` — ALL OK.
   - `python tools/audit_excel.py` — 0 significant diffs.
   - Валидация `edition.json` в обоих дистрибутивах: `python -c "import json; print(json.load(open('dist_all/Порайонка_Пользователь/edition.json','r',encoding='utf-8')))"`.

## Ограничения

- Не трогать admin-установщик (`Порайонка_Админ_Setup.exe`) — он работает.
- Flet 0.23.2, без новых зависимостей.
- Все новые `print()` — ASCII (без русских букв).
- UI-текст — русский.
- Не ломать поведение раундов 20–35.

## Куда смотреть

- `porayonka-app/core/edition.py` — `_read_edition_file`, `load_edition`.
- `porayonka-app/ui/controls/controls_settings_modal.py` — список ФИО в настройках.
- `porayonka-app/installer/User.iss` / `UserWeb.iss` — как пишется `edition.json`.
- `porayonka-app/build_all_distributives.bat` — сборка portable exe.
- `porayonka-app/installer/build_installers.bat` — сборка установщиков (требует `C:\porayonka_inno6\iscc.exe`).
