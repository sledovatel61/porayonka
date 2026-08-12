# Промпт: Вкладка «Контроли» — Раунд 24 (сборка дистрибутивов admin/user + web Win7 + реальный звук)

**Репозиторий:** https://github.com/sledovatel61/porayonka.git (ветка `main`)  
**Приложение:** `porayonka-app/main.py`  
**Запуск:** `cd porayonka-app && python main.py`  
**Flet:** строго `0.23.2`  
**База:** `main` после раунда 23 (коммит `2781c7c` + скрины; код раунда 23 пока НЕ влит, он в `arena/019fec02-porayonka` коммит `c147ecc`).

---

## Текущее состояние

Агент раунда 23 реализовал в ветке `arena/019fec02-porayonka`:

- редакцию `edition.json` (`core/edition.py`), read-only user-режим;
- трей (`ui/tray_icon.py`), автозапуск (`core/autostart.py`);
- алармы сроков со звуком `assets/pig.wav` (синтезированный);
- web-режим `--web` для Win7;
- мгновенные вложения и крупные бейджи.

**Проблема:** это код, а не готовые дистрибутивы. Сборочных скриптов/spec для admin/user/web нет; старые `build_exe.bat` / `build_win7.bat` / `Porayonka_Win7.spec` не актуальны. Звук свиньи — синтезированный, а реальный `Звук свиньи.mp3` лежит в `porayonka-app/assets/pig.mp3` (уже в `main`).

---

## Задачи раунда 24

### 1. Два дистрибутива (admin + user)

Создать актуальные PyInstaller spec и build-скрипты:

- `Porayonka_Admin.spec` / `build_admin.bat`:
  - собирает exe с именем `Порайонка_Админ.exe`;
  - в сборку включается `edition.json` с `{"role": "admin"}` рядом с exe (или в `APPDATA`, но лучше рядом — чтобы не переопределялось);
  - используется Flet 0.23.2, openpyxl, все модули вкладок;
  - иконка из `assets/icon.png` (если есть) или стандартная.

- `Porayonka_User.spec` / `build_user.bat`:
  - собирает exe с именем `Порайонка_Пользователь.exe`;
  - `edition.json` с `{"role": "user"}`;
  - read-only режим, уведомления каждые 2 часа, автозапуск, трей.

- Оба скрипта должны:
  - устанавливать зависимости из `requirements.txt` + `pystray pillow`;
  - очищать `build/` и `dist/` перед сборкой;
  - копировать `assets/` (включая `pig.mp3` и `pig.wav`) внутрь сборки;
  - выводить понятный итог: путь к exe.

### 2. Web-версия для Win7

- `build_user_web_win7.bat`:
  - собирает web-бандл приложения (Flet 0.23.2 поддерживает `flet build web` или можно использовать `pyinstaller --onefile` с web-ресурсами? — выбрать рабочий вариант);
  - выдаёт папку `dist/web/` со статикой (index.html, js, wasm);
  - создаёт `start_web_win7.bat`, который запускает `python main.py --web --host 0.0.0.0 --port 8555` и открывает браузер по умолчанию (подходит для Win7 с Chrome/Firefox);
  - user-редакция фиксируется в web-режиме (например, через `edition.json` в папке web или через переменную окружения `PORAYONKA_EDITION=user`).

- Если `flet build web` недоступен/не работает на Win7 — сделать альтернативу: `build_user_web_win7.bat` собирает exe, который запускает `main.py --web` (то есть сервер + автооткрытие браузера), а статика лежит рядом. Главное — чтобы на Win7 пользователь мог запустить один файл и работать через браузер.

### 3. Реальный звук свиньи (MP3)

- В `main` уже есть `porayonka-app/assets/pig.mp3` (реальный файл).
- Нужно заменить синтезированный `assets/pig.wav` на реальный:
  - Вариант A (предпочтительно): использовать `pig.mp3` напрямую через Windows MCI (`ctypes.windll.winmm.mciSendStringW`) — это stdlib, играет MP3 на Win7+.
  - Вариант B: при сборке конвертировать `pig.mp3` → `pig.wav` (если ffmpeg доступен), но в исходниках хранить `pig.mp3` как источник.
- Обновить `ui/sound_alert.py` (или где играет звук) так, чтобы:
  - если рядом/`APPDATA` есть `pig.wav` — играть его (обратная совместимость);
  - иначе играть `pig.mp3` через MCI (fallback);
  - при ошибке — молча или print ASCII.

### 4. Автозапуск и трей

- Убедиться, что `autostart.enable_autostart()` и `start_tray()` вызываются только в frozen-сборке и только на Windows.
- В web-режиме трей не нужен (но не должен мешать).
- Для user-редакции автозапуск обязателен; для admin — тоже, но можно не обязательно.

### 5. Проверка и тесты

- Обновить `requirements.txt` (добавить `pystray pillow` как опциональные, но в build-скриптах устанавливать).
- Smoke-тесты должны остаться зелёными (612+ проверок).
- Добавить smoke-проверку, что сборочные файлы существуют и `edition.json` корректно подхватывается (можно headless).

---

## Технические ограничения

- Flet строго 0.23.2.
- Не добавлять новых runtime-зависимостей (pystray/pillow — только для сборки, опционально).
- Цвета 8-hex — только `#AARRGGBB`; `print()` — ASCII; UI-текст — русский; `ft.icons.*`.
- Не ломать вкладки «Следственные отделы», «Зональные», «Контроли» и их контракты.
- Не возвращать `page.overlay.append` без `page.update()`, `scroll=HIDDEN + tight + expand` в Row, `expand=True` внутри `Column(scroll=AUTO)`.

---

## Материалы

- Промпт: `PROMPT_контроли_доработка24.md`.
- Реальный звук: `porayonka-app/assets/pig.mp3`.
- Код раунда 23: ветка `arena/019fec02-porayonka` коммит `c147ecc` (можно взять за основу, но не обязательно мержить целиком — главное, чтобы итог в `main` был цельным).
- Скрины вложений: `design/screenshots/12.08.2026/`.

---

## Проверка

```bash
cd porayonka-app
python -m py_compile ui/controls/controls_tab.py ui/controls/russian_calendar.py \
  ui/controls/glass_theme.py ui/controls/control_card_modal.py \
  ui/controls/controls_settings_modal.py main.py ui/update_lock.py \
  core/controls_models.py core/controls_data.py core/controls_exporter.py \
  core/edition.py core/autostart.py ui/tray_icon.py ui/sound_alert.py
python -c "import sys; sys.path.insert(0, '.'); from ui.controls.controls_tab import create_controls_tab; print('OK')"
python tests/test_controls_smoke.py   # ALL OK обязателен
# Проверить наличие сборочных файлов:
ls Porayonka_Admin.spec Porayonka_User.spec Porayonka_User_Web.spec build_admin.bat build_user.bat build_user_web_win7.bat
```

После проверки обновить `AGENTS.md` §63 (результаты раунда 24), запушить в `arena/XXXX-porayonka` и сообщить имя ветки.
