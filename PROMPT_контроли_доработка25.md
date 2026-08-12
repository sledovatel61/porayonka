# Промпт: Вкладка «Контроли» — Раунд 25 (починка smoke-тестов под Windows)

**Репозиторий:** https://github.com/sledovatel61/porayonka.git (ветка `main`)  
**Приложение:** `porayonka-app/main.py`  
**Запуск:** `cd porayonka-app && python main.py`  
**Flet:** строго `0.23.2`  
**База:** твоя ветка `arena/019fec02-porayonka` коммит `5086e8b` (раунд 24) + актуальный `main` (`bb23bb8`).

---

## Контекст

Раунд 24 (дистрибутивы admin/user + web Win7 + реальный звук) выполнен, но **smoke-тесты падают на Windows**, поэтому код не может быть влит в `main`.

Основная причина — тесты писались в Linux-сандбоксе и ожидают «вне Windows» поведение, а также в тестовых строках снова появились Unicode-символы, которые Windows-консоль (cp1251) не может напечатать.

---

## Что падает на Windows

```text
FAILED: sound23: play_alarm_sound вне Windows — no-op False (не падает)
FAILED: os23: автозапуск вне Windows — supported=False, включение не падает
```

- `sound23`: `play_alarm_sound(True)` на Windows возвращает `True` (платформа win32), а тест ожидает `False`.
- `os23`: `autostart.is_supported()` на Windows возвращает `True`, а тест ожидает `False`.

Также в `tests/test_controls_smoke.py` много `check("... — ...")` с em-dash `—` и `→` / `×`. При запуске без `PYTHONIOENCODING=utf-8` падает:

```text
UnicodeEncodeError: 'charmap' codec can't encode character '\xd7' ...
```

---

## Задачи раунда 25

### 1. Сделать smoke-тесты платформенно-независимыми

- Для проверок «вне Windows» используй **мокинг**, а не реальную платформу:
  - `sound_alert.sys.platform` / `autostart.sys.platform` — подменить на `"linux"` (или `"darwin"`) в контексте теста;
  - `sys.frozen` — подменить на `False` / `True` по необходимости;
  - можно использовать `unittest.mock.patch.object(sys, 'platform', 'linux')` или временное присвоение с `try/finally`.
- Тесты должны проходить **и на Windows, и на Linux** без переменных окружения.

### 2. Вернуть ASCII в печатаемые строки тестов

- Во всех `check("...")` и `print(...)` убрать символы, не входящие в cp1251:
  - `—` → `-`
  - `→` → `->`
  - `×` → `x`
- Комментарии и docstring можно оставить с Unicode — они не печатаются.
- Проверь: `grep -nP "[^\x00-\x7F]" tests/test_controls_smoke.py` не должен находить строки с `check(` / `print(`.

### 3. Проверить, что в коде нет регрессий

- `controls_tab.py`, `main.py`, `main_web.py`, `core/*.py`, `ui/*.py` должны компилироваться и импортироваться.
- Функционал раундов 20–24 не ломать.

---

## Обязательная проверка (на Windows-машине)

```bash
cd porayonka-app
python -m py_compile ui/controls/controls_tab.py ui/controls/russian_calendar.py \
  ui/controls/glass_theme.py ui/controls/control_card_modal.py \
  ui/controls/controls_settings_modal.py main.py main_web.py ui/update_lock.py \
  core/controls_models.py core/controls_data.py core/controls_exporter.py \
  core/edition.py core/autostart.py ui/tray_icon.py ui/sound_alert.py
python -c "import sys; sys.path.insert(0, '.'); from ui.controls.controls_tab import create_controls_tab; print('OK')"
python tests/test_controls_smoke.py   # ALL OK обязателен, без PYTHONIOENCODING
```

**Важно:** тесты должны проходить при стандартной Windows-консоли (cp1251), без `chcp 65001` и без `PYTHONIOENCODING=utf-8`.

---

## Процесс

1. Забрать актуальный `main` (`bb23bb8`) и свою ветку `arena/019fec02-porayonka` (`5086e8b`).
2. Исправить тесты по пунктам 1–2.
3. Прогнать проверки на Windows (или максимально близко — Linux с `LC_ALL=C` не поможет, нужен именно Windows cp1251; если нет Windows, сделай мокинг и убери Unicode).
4. Обновить `AGENTS.md` §64 (результаты раунда 25).
5. Запушить в `arena/019fec02-porayonka` и сообщить коммит.

Не добавляй новых фич, только починка тестов и ASCII.
