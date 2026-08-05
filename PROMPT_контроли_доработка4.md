# Промпт новому агенту: починить вкладку «Контроли» (карточка не открывается) + доводка

РЕПОЗИТОРИЙ: https://github.com/sledovatel61/porayonka.git
БАЗА: ветка `arena/019fcc5f-porayonka`, HEAD `71f9a57` (там последняя работа по редизайну Glass Dark — НЕ начинай с main, там 80% готово).
ПРИЛОЖЕНИЕ: `porayonka-app/main.py`. Flet строго 0.23.2. Windows.
ОБЯЗАТЕЛЬНО прочитай `AGENTS.md` — разделы 15.11 (layout-запреты), 28–31 (архитектура вкладки), 32 (hex `#AARRGGBB`).

## 0. Текущее состояние

Вкладка «Контроли» (Glass Dark редизайн) почти готова: таблица-плашки, фильтры, русский календарь, resize колонок. Но при живом запуске:

1. **КРИТИЧНО: карточка контроля не открывается.** Клик по строке/карандашу/«Добавить контроль» → экран затемняется (dim работает), сама карточка НЕ появляется. В консоли НЕТ traceback от `_open_detail` — ошибка либо проглочена, либо карточка строится с нулевой/битой геометрией.
2. **Консоль забита** `AssertionError: Control must be added to the page first.` — десятки вызовов `.update()` при инициализации до монтирования контролов (`_rebuild_table`, `_rebuild_header`, `_restyle_counters`, `_refresh_filter_options`, `_update_sync_ui`, `_rebuild_filter_cal`, `_rebuild_global_cal`, `_rebuild_list`, `_rebuild_task_cards`, `_rebuild_milestones`, `_rebuild_attach` и др.).

Файлы: `porayonka-app/ui/controls/controls_tab.py` (~2300 строк), `glass_theme.py`, `russian_calendar.py`, `control_card_modal.py`, `controls_settings_modal.py`.

## 1. Задача 1 — найти и починить открытие карточки

Где смотреть: `_open_detail` (controls_tab.py ~стр. 1290), построение колонок (~стр. 1660), `detail_overlay` / `detail_overlay_container`, место, где `visible` переключается и вызывается `update()`.

Вероятные причины (проверь все):
- Исключение в построении карточки, пойманное молча (найди оставшиеся `except: pass` / `except Exception: pass` на этом пути — все должны быть `traceback.print_exc()`).
- Схлопывание: `Column(scroll=AUTO)` + `tight` + `expand` комбинации (AGENTS §15.11) — карточка высотой 0.
- `update()` контрола, не добавленного в page (см. задачу 2) в момент открытия — после починки логирования станет видно.

Требование: карточка открывается по клику на строку, по карандашу, через «Добавить контроль»; двухколоночный layout виден целиком; закрытие/сохранение работают; скролл без пустого хвоста.

## 2. Задача 2 — убрать шум «Control must be added to the page first»

Сделай хелпер `_safe_update(control)`: вызывает `control.update()` только если контрол смонтирован (`control.page is not None`), иначе пропускает. Примени ко ВСЕМ `.update()` в файле, обёрнутым в try/except. После этого при инициализации консоль должна быть чистой, а реальные ошибки — видны (traceback).

## 3. Задача 3 — сверка с мокапом и остаточные UX-пункты

Эталон: `design/mockups_portable/photo/01_glass_dark.png`. После починки карточки проверь и доведи, если не сделано:
- Иерархия яркости: фон `#0a1024` < панели `#141e33` < плашки `#1e2a44` (серый оттенок, плашки явно отделяются от фона).
- Hover плашки `#28324e`, мгновенный.
- Колонка «Действия»: карандаш `#4f8cff` + корзина `#ff5c6e`.
- Фильтры «Исполнители»/«Контролёры» — options из реальных данных (distinct), фильтрация работает.
- «С:»/«По:» — shared-календарь поверх, фильтрует; крестик очистки внутри поля.
- Длинные исполнители — перенос на 2 строки, плашка тянется по высоте.
- Исполненные — внизу списка.
- Resize колонок drag'ом за границу заголовка, сохранение в `controls_settings.json`.

## 4. Ограничения (обязательно)

- Hex с альфой — только `#AARRGGBB` (AGENTS §32); динамика `f"#22{color[1:]}"`.
- `Column(scroll=AUTO)`: без `expand` (кроме горизонтальных спейсеров в Row), `wrap`, `animate`, `shadow`, `gradient`; рамки равномерной толщины.
- Без вложенных `AlertDialog`; диалоги подтверждений — `page.open()/page.close()`.
- Не ломать: данные, Excel импорт/экспорт, сетевой режим, архив, роли, вкладки 1–2, контракты функций.
- `ft.icons.*`, ASCII `print()`, русский UI.
- НЕ переписывай всё с нуля — только точечные исправления. Ветка уже содержит рабочую базу.

## 5. Проверка (строго)

`import main` НЕДОСТАТОЧЕН: `main.py` импортирует вкладку лениво — синтаксические ошибки вкладки он не ловит. Обязательно:
```bash
cd porayonka-app
python -m py_compile ui/controls/controls_tab.py ui/controls/russian_calendar.py ui/controls/glass_theme.py ui/controls/control_card_modal.py ui/controls/controls_settings_modal.py main.py
python -c "import sys; sys.path.insert(0, '.'); from ui.controls.controls_tab import create_controls_tab; print('OK')"
```
Плюс headless-smoke с page-заглушкой: вкладка строится, `_open_detail` создаёт карточку с контентом (левая и правая колонки непустые).

Когда закончишь — коммить только в отдельную ветку от базы (не в main; если сессия закреплена на ветке — используй её), и в последнем сообщении напиши мне точное имя этой ветки.
