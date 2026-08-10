# MANGUST v4 — Полная сводка для разработчика

## 1. Общая информация

**MANGUST v4** — десктопное приложение для автоматизации следственной деятельности (СК РФ). Помогает следователям заполнять формы, вести проекты, конвертировать тексты допросов из 1-го лица в 3-е, а также использовать LLM для умного импорта и краткого изложения показаний.

- **Целевая ОС**: Windows 10/11 (основная), Windows 7 SP1 x86/x64 (legacy-ветка `win7/`)
- **Python**: 3.11.8 (Win10/11), 3.8.10 (Win7)
- **UI-фреймворк**: tkinter + ttkbootstrap (тема `darkly`)
- **Виртуальное окружение**: `venv_new/` (Python 3.11, CUDA-ready); `win7/venv/` + `win7/python38_full/` (Python 3.8 x64, без LLM/CUDA); `win7/venv_x86/` + `win7/python38_full_x86/` (Python 3.8 x86, без LLM/CUDA)
- **Запуск**: `run.bat` (использует `venv_new\Scripts\python.exe`); Win7 — `win7/run.bat`

---

## 2. Технологический стек

| Компонент | Технология | Назначение |
|-----------|-----------|------------|
| UI | tkinter + ttkbootstrap | Главное окно, формы, виджеты |
| Дизайн | Cyber-Neon (кастом) | Тёмная тема с неоновыми акцентами |
| LLM | llama-cpp-python (GGUF) | Qwen2.5-Instruct 3B/14B (CPU/GPU) |
| Данные | JSON-файлы | Проекты, схемы, конфиги |
| Чтение DOC | python-docx, textract, antiword, catdoc, win32com | Извлечение текста из .doc/.docx |
| Чтение PDF | PyMuPDF (fitz), pdfplumber | Извлечение текста из PDF |

### Критические зависимости
- `ttkbootstrap` — тема `darkly`
- `tkcalendar` — календарные виджеты
- `Pillow` — обработка изображений
- `llama-cpp-python` — LLM (CUDA/CPU)
- `python-docx` — чтение .docx
- `PyMuPDF` / `pdfplumber` — чтение PDF
- `textract` — чтение .doc (через antiword)

---

## 3. Структура проекта

```
mangust_v4/
├── main.py                     # Точка входа. CUDA-PATH, зависимости, запуск UI
├── run.bat                     # Запуск через venv_new (Windows)
├── run.ps1                     # Альтернативный запуск (PowerShell)
├── pyproject.toml              # Конфигурация setuptools
├── pytest.ini                  # Конфигурация тестов
├── requirements-llm.txt        # Зависимости для LLM (llama-cpp-python, psutil)
├── fix_structure.py            # Скрипт перестроения структуры УК РФ (вспомогательный)
├── fix_upk_structure.py        # Скрипт перестроения структуры УПК РФ (вспомогательный)
├── config/                     # Все конфигурационные файлы
│   ├── schema_person.json      # Схема формы лица
│   ├── schema_crime.json       # Схема формы преступления
│   ├── lists.json              # Списки для выпадающих полей
│   ├── crime_places.json       # Места преступлений
│   ├── import_keywords.json    # Ключевые слова для умного импорта
│   ├── uk_upk_database.json    # База статей УК РФ (492) / УПК РФ (558)
│   ├── models/                 # GGUF-модели (3B, 14B)
│   └── *.json                  # Прочие конфиги (password, minesweeper_stats и т.д.)
├── src/
│   ├── controllers/
│   │   └── app_controller.py   # ГЛАВНЫЙ КОНТРОЛЛЕР приложения
│   ├── mangust_v4/             # Data Layer (модели, сервисы)
│   │   ├── models/
│   │   │   ├── dataclasses.py  # CrimeCase, Person, Project
│   │   │   ├── migration.py    # Миграция JSON-данных
│   │   │   └── project.py      # Управление проектом
│   │   └── services/
│   │       ├── json_repository.py   # Работа с JSON
│   │       ├── schema_loader.py     # Загрузка схем форм
│   │       └── smart_import_core.py # Ядро умного импорта (LLM)
│   ├── services/
│   │   ├── statute_limitations_service.py  # Сервис расчёта сроков давности УК РФ
│   │   └── statute_repository.py           # Репозиторий справочника УК/УПК РФ
│   └── views/                  # ВСЕ UI-компоненты
│       ├── modern_widgets.py   # Дизайн-система (цвета, шрифты, кнопки, PlaceholderEntry, PlaceholderText)
│       ├── cyber_calendar.py   # Единый календарь Cyber-Neon (CyberDatePicker, CyberCalendarPopup)
│       ├── constructor.py      # Конструктор схем форм
│       ├── crime_form.py       # Форма преступления
│       ├── person_form.py      # Форма лица
│       ├── person_editor_dialog.py # Редактор лиц (модальное окно)
│       ├── preview_view.py     # Предпросмотр документа
│       ├── dialogs.py          # Диалоги (горячие клавиши и т.д.)
│       ├── smart_import_dialog.py  # Умный импорт (LLM)
│       ├── first_to_third_converter.py  # КОНВЕРТЕР 1→3 лицо
│       ├── day_calculator.py   # Калькулятор сроков (старый)
│       ├── statute_calculator.py   # Калькулятор сроков давности УК РФ (новый)
│       ├── statute_reference_view.py  # Справочник УК/УПК РФ
│       ├── minesweeper.py      # Сапёр (мини-игра)
│       ├── solitaire.py        # Пасьянс
│       ├── rest_games.py       # Прочие мини-игры
│       ├── test_pil.py         # Тестовый виджет
│       └── apply_readonly_fix.py
├── tests/
│   ├── test_migration.py
│   └── golden_files/           # Эталонные файлы для тестов
├── tools/
│   ├── innosetup/              # Inno Setup 6 (Win10/11)
│   └── nsis/                   # NSIS 3 (Win7)
├── win7/                       # Legacy-сборка для Windows 7 SP1 x86/x64
│   ├── python38_full/          # Полный Python 3.8.10 x64 с tkinter/tcl/tk
│   ├── python38_full_x86/      # Полный Python 3.8.10 x86 с tkinter/tcl/tk
│   ├── venv_x86/               # Виртуальное окружение x86 для сборки
│   ├── venv/                   # Виртуальное окружение Win7
│   ├── src/                    # Симлинк/копия исходников (см. BUILD_INSTALLERS.md)
│   ├── dist/MANGUST_v4_Win7/   # Собранное портативное приложение Win7 x64
│   ├── dist/MANGUST_v4_Win7_x86/ # Собранное портативное приложение Win7 x86
│   ├── build/MANGUST_v4_Win7/  # Build-артефакты PyInstaller x64
│   ├── build/MANGUST_v4_Win7_x86/ # Build-артефакты PyInstaller x86
│   ├── MANGUST_v4_Win7.spec    # PyInstaller spec для Win7 x64
│   ├── MANGUST_v4_Win7_x86.spec # PyInstaller spec для Win7 x86
│   ├── rthooks/                # runtime hooks PyInstaller
│   ├── main.py, run.bat, run.ps1, requirements-win7.txt
│   └── pytest.ini, README.md
├── Для обучения/               # Обучающие материалы + тестовые тексты
│   ├── ВУД/                    # Образцы ВУД
│   ├── Допросы/                # Образцы допросов
│   ├── Обвинительные/          # Образцы обвинительных заключений
│   └── Конвертер/              # Тестовые файлы для конвертера (ReGex, ИИ, .doc, .txt)
└── Эталонные файлы/            # Эталонные JSON для сравнения
```

---

## 4. Цветовая палитра (Cyber-Neon)

**Источник истины**: `src/views/modern_widgets.py`

```python
BG_APP_DARK     = "#0d1117"   # Фон всего приложения
BG_PANEL        = "#161b22"   # Фон панелей
BG_PANEL_LIGHT  = "#1c2333"   # Светлые панели
BG_CARD         = "#1e2a3a"   # Карточки
BG_INPUT        = "#0d1117"   # Поля ввода
BG_PREVIEW      = "#1a1f2e"   # Чуть светлее BG_PANEL для предпросмотра

CYAN_NEON       = "#06b6d4"   # Основной акцент (кнопки, рамки)
CYAN_DARK       = "#0891b2"   # Акцент при наведении
GREEN_NEON      = "#10b981"   # Успех, готовность
RED_NEON        = "#ef4444"   # Ошибки, опасность
GOLD_NEON       = "#fbbf24"   # Предупреждения, заметки
PURPLE_NEON     = "#8b5cf6"   # Вторичный акцент

TEXT_PRIMARY    = "#e2e8f0"   # Основной текст
TEXT_SECONDARY  = "#94a3b8"   # Вторичный текст
TEXT_MUTED      = "#64748b"   # Приглушённый текст
TEXT_WHITE      = "#ffffff"   # Белый текст

BORDER_DEFAULT  = "#2a3f60"   # Стандартная рамка
BORDER_CYAN     = "#0891b2"   # Рамка при акценте
BORDER_HOVER    = "#3a5f82"   # Рамка при наведении
```

---

## 5. Вкладки приложения (порядок в notebook)

1. **👤 Лица** (`person_form.py`) — список и управление лицами
2. **⚖️ Происшествие** (`crime_form.py`) — форма ввода данных о преступлении
3. **🔄 1→3 лицо** (`first_to_third_converter.py`) — конвертер текста допросов
4. **👁️ Предпросмотр** (`preview_view.py`) — предпросмотр документа
5. **🛠️ Конструктор** (`constructor.py`) — конструктор схем форм
6. **🧮 Калькулятор** (`day_calculator.py`) — расчёт сроков (старый)
7. **⏳ Сроки давности** (`statute_calculator.py`) — калькулятор сроков давности УК РФ (новый)
8. **📖 Справочник УК/УПК** (`statute_reference_view.py`) — справочник статей УК РФ и УПК РФ
9. **🎮 Игры** — Сапёр, Пасьянс и т.д.

---

## 6. Что уже реализовано (история изменений v4)

### Placeholder во всех полях ввода
- ✅ `PlaceholderEntry` (`modern_widgets.py`) — Entry с подсказкой `---введите текст---`, выровненной по центру. Реализован через **внутреннюю переменную** `_internal_var` (`tk.StringVar`), которая всегда привязана к Entry. Внешняя `textvariable` синхронизируется через trace (`_on_internal_var_write` / `_on_ext_var_write`). Placeholder **не попадает во внешнюю переменную**.
  - ⚠️ **Исправлен критический баг**: старая реализация переключала `configure(textvariable="")` / `configure(textvariable=self._var)` в рантайме. В Tcl/Tk `configure -textvariable ""` привязывает к глобальной tcl-переменной с именем `""`, а не отключает привязку. Это приводило к тому, что первый ввод после placeholder уходил в неверную переменную (текст был тусклым, не сохранялся, пропадал при Alt-Tab).
  - ✅ **Фикс**: `textvariable` Entry никогда не переключается — всегда `_internal_var`. Убран `update_idletasks()`. Конфликт с `configure_wrapper` из `_install_entry_error_pulse` устранён.
- ✅ `PlaceholderText` (`modern_widgets.py`) — Text с placeholder-подсказкой.
- ✅ Вкладка **Происшествие** (`crime_form.py`) — все однострочные поля (`_make_entry`) и многострочные поля (`TextSection`, фабула, выписка протокола ОМП, сведения о фигуранте) имеют placeholder.
- ✅ Модальное окно редактирования лица (`person_editor_dialog.py`) — placeholder в полях **Место рождения**, **СНИЛС**, **ИНН**.
- ❌ **TODO**: добавить placeholder в остальные модальные окна (AddressDialog, DecisionDialog, QualificationDialog, DocumentDialog, TransportDialog, IdentifierDialog и др.).
- ❌ **TODO**: в модальном окне лица автозаполняемые поля (Фамилия, Имя, Отчество, Дата рождения, Дата смерти, Возраст от/до, Год рождения от/до) — **без placeholder** (как требовал заказчик).

### Конвертер 1→3 лицо (`first_to_third_converter.py`)
- ✅ Два режима: **Логический** (RegEx, быстрый) и **ИИ** (LLM, точный)
- ✅ Полная таблица замен `_REPLACEMENTS` — 400+ паттернов (местоимения, глаголы наст./буд./прош. вр.)
- ✅ Продуктивные паттерны для нестандартных глаголов (`-ую → -ует`, `-аю → -ает`, `-юсь → -ется`)
- ✅ Защита цитат в кавычках от замены
- ✅ Извлечение текста показаний из .doc/.docx/.pdf/.txt с фильтрацией служебных блоков
- ✅ Обработка .doc через antiword → catdoc → win32com → LibreOffice
- ✅ Chunked LLM-обработка (части ~12000 символов) с few-shot примерами
- ✅ Post-processing LLM: `желаю→желает`, `состою→состоит`, `прохожу→проходит`, `имею→имеет`, `могу→может`, `мной→им/ей`
- ✅ **Подсветка результата** в основном окне: 🟡 жёлтый — заменённые формы, 🔴 красный — ошибки/проверьте
- ✅ Легенда цветов размещена в панели действий справа, под окном результата, без пустого пространства
- ✅ Ручное редактирование с подсветкой (`warn`/`error` теги через Python `re.finditer`)
- ✅ Блокировка ИИ-режима для лёгких моделей (3B/1.5B) — диалог с контактами и ссылкой Max

### Умный Импорт (`smart_import_dialog.py`, `smart_import_core.py`)
- ✅ LLM-анализ текста протокола/объяснения и автоматическое заполнение форм
- ✅ Мерж импортированных данных (не затирает ручной ввод)
- ✅ Динамическая активация чекбоксов по тексту метки
- ✅ Ключевые слова из `config/import_keywords.json`

### RegEx-first рефакторинг — Phase 1 (2026-07-16)
- ✅ Архитектура **Candidate → Resolver → Validator → Confidence** в `smart_import_core.py`.
- ✅ Сохранение структуры DOCX: последовательный обход XML body, `TextNode` с индексами таблиц/ячеек, дедупликация merged cells.
- ✅ Секционирование v6: scoring заголовков, повторные секции, якоря вынесены в `config/smart_import_sections.json`.
- ✅ Candidate-layer для номера дела и дат с ролевой классификацией (`case_initiation_date`, `document_date`, `birth_date`, `crime_date`).
- ✅ Sentence-scoped keyword rules v6: границы слов, `negative_patterns`, `relation_verbs`, `allowed_articles`, scope `fabula/episode/body/document`.
- ✅ Provenance metadata: результат всегда содержит `_field_meta` и `_warnings`.
- ✅ Обратная совместимость: v5 парсеры и legacy-формат `import_keywords.json` продолжают работать.
- ✅ ~~TODO Phase 2~~ — **выполнено 2026-07-20** (см. ниже «Phase 2 — Candidate-based extraction»).

### RegEx keyword hardening — Phase 1.5 (2026-07-16)
- ✅ Улучшены keyword-правила в `config/import_keywords.json`: medical/evidence scopes для `method`/`injuries`, morphology fallback, bounded neighbor-sentence context для `tools`.
- ✅ Добавлен `stem_phrase` mode и лёгкий morphology fallback (`_keyword_stem`, `_keyword_relation_matches`) для relation context.
- ✅ Guarded rules для `tools` (нож/транспорт/запись) без возврата к document-wide substring.
- ✅ Новые regression tests: `tests/test_keyword_phase15.py` (11 шт.).
- ✅ **Root cause ложной регрессии**: первоначальное сравнение показало «все поля пустые», потому что `tools/generate_phase15_results.py` сохранял сырой выход `process_file` без обёртки `{"crime_case": ...}`. `tools/compare_phase15.py` ожидал project-формат. После конвертации через `tools/generate_phase15_project_format.py` метрики на 9 обвинительных заключениях:
  - True Positives: 43 → 44
  - False Positives: 48 → 15
  - False Negatives: 15 → 14

### RegEx keyword recall — Phase 1.6 (2026-07-16)
- ✅ Целевой тюнинг keyword-правил для закрытия recall-пробелов в `method`, `tools`, `injuries`, `stolen`.
- ✅ Добавлена новая категория `stolen` в `config/import_keywords.json` с theft relation verbs, article guard (ст. 158–164) и negative contexts.
- ✅ Добавлены article-guarded правила для сексуальных механизмов (ст. 132/134) → `method` «Иной установленный способ...».
- ✅ Добавлены правила для «Части тела ... как средство физического воздействия» и активной видеозаписи (`осуществлял видеозапись`, `производил съёмку`).
- ✅ Усилены правила для `injuries` (`половые органы`, `промежность`, `влагалище`) с medical/evidence scope и negative contexts.
- ✅ Новые regression tests: `tests/test_keyword_phase16.py` (10 шт.).
- ✅ Метрики на 9 обвинительных заключениях после Phase 1.6:
  - True Positives: 44 → **50**
  - False Positives: 15 → **13**
  - False Negatives: 14 → **8**
  - `injuries`: 7/9 → **9/9**
  - `method`: 4/8 → **6/8**
  - `tools`: 4/8 → **6/8**
  - `stolen`: 3/4 → **3/4** (без лишних FP)
- ⚠️ **Валидация временно отключена** (`ValidationController.ENABLED = False`) для удобства тестирования умного импорта.

### Phase 2 — Candidate-based extraction лиц/адресов/квалификаций/crime_place (2026-07-20) ✅
**Источник**: арена-агент по промпту `PROMPT_PHASE2.md` (репо `sledovatel61/mangust`, ветка `arena/019f740d-mangust`, коммит `c368e49`). Код перенесён в основное дерево и независимо проверен.

**Что добавлено в `smart_import_core.py` (+1944 строки):**
- `_apply_person_candidate_layer` — извлечение лиц по позитивным якорям (`_PERSON_ANCHOR_RE`, `_HEADER_FIO_RE`, **без `re.IGNORECASE`**), зональная верификация (a0/evidence/protocol/pre), same-birth merge, relative-skip («на иждевении», «состав семьи», «семейное положение»), `_normalize_person_fio` через pymorphy3 (падежи `Чекомасовой Марией` → `Чекомасова Мария`), лимит **8** + флаг `PERSONS_OVERFLOW`.
- `_apply_address_candidate_layer` — 4 источника кандидатов (S1–S4), скорер контекста со штрафами (evproc/сговор/residence/institution/work/venue), коллапсы «один дом»/typo/by_city_house, динамический порог ≥0.95→≥0.80, канон топонимов, лимит **4** + флаг `ADDR_OVERFLOW`.
- Qualifications layer — `_QUAL_CONCLUSION_RE` (ленивый хвост до «УК РФ/РСФСР»), `_parse_qual_article_list`, исключение «по совокупности», мерж с baseline (не перезапись).
- Crime place resolver — `_apply_crime_place_resolver`, метки `_CP_LBL_*` дословно из `config/crime_places.json`, cottage только с indoor-контекстом.
- Интеграция в `_process_with_regex` (слои после основных парсеров); работает для accusation/initiation/interrogation/termination.

**Метрики корпуса (10 обвинительных, `tools/compare_phase2.py`, текущий-vs-эталон TP/FP/FN):**
- Persons: Русских/Пугачёва/Курсевич/Железненко/Асатуллаев/Поташук **2/0/0** (было до 1/3/1); Евтушенко 3/1/0 (Морозов найден); Сулейманов 3/1/0.
- Addresses: Русских/Пугачёва/Курсевич/Асатуллаев/Поташук **1/0/0**; Евтушенко 4/0/2 (cap 4 из 6); Сулейманов 2/1/1.
- Qualifications: Евтушенко **2/0/0** (ст. 166+326), Поташук **1/0/0** (УК РСФСР); остальные без потерь.
- Crime place: ложные срабатывания indoor/building/outdoor убраны почти везде (напр. Русских indoor FP 2→0, building 3→0).
- Checkbox-агрегаты Phase 1.6 без регрессий: **TP=50, FP=13, FN=8**.
- pytest: **98 passed**, `py_compile` 3.11 и 3.8 — OK.

**Инструменты и артефакты:**
- `tools/compare_phase2.py` — корпусный гейт Phase 2 (persons/addresses/quals/crime_place, TP/FP/FN vs база/эталон, санити-лимиты 8 лиц/4 адреса, `resolve_doc` допускает `.doc` и `.docx`).
- `tests/test_smart_import_phase2.py` — 21 regression-тест.
- `PHASE2_REPORT.md` (корень) — полный отчёт агента с методами и метриками.
- Известные ограничения: Сулейманов qual 1 из 3 (мультиэпизодность не решена); Евтушенко адреса усечены лимитом 4 из 6; Железненко адрес в display-форме «д. 23, кв. 65» vs эталон «23, кв. 65».

**Уроки (обязательны для будущих фаз):**
- ❌ `re.IGNORECASE` + `[А-ЯЁ]` в паттернах ФИО → матчит любые тройки слов (взрыв 29–662 ложных лиц на документ). Проверено первой неудачной попыткой.
- Стоп-листы «не-фамилий» не масштабируются — только позитивные якоря.
- Любой resolver обязан иметь верхний лимит сущностей.
- Приёмка только по корпусу (`compare_phase2.py`), юнит-тесты на игрушечных текстах недостаточны.

**Фикс мержа в приложении (2026-07-20):** `_on_import_result` (`app_controller.py`) дедуплицировал списки decisions/addresses/qualifications единым ключом `type+date`. У адресов и квалификаций поля `date` нет (`None == None`), поэтому все однотипные записи схлопывались в одну — в приложении сохранялся 1 адрес из 4 и 1 квалификация из 2 (Евтушенко, Сулейманов). Заменено на `_import_entity_dedup_key()` со специфичными ключами: addresses — нормализованный текст адреса + type; qualifications — article+part+point+episode; decisions — type+date (как раньше). Regression-тесты: `tests/test_import_merge_dedup.py` (8 шт.).

### Phase 3 — qualifications episode, канон/recall адресов, crime_place контекст (2026-07-22) ✅
**Источник**: арена-агент по промпту `PROMPT_PHASE3.md` (ветка `arena/019f740d-mangust`, коммит `aed5b38` — тот же чат, что сделал Phase 2). Перенесено в основное дерево и независимо проверено. Два конкурирующих варианта отклонены: у одного CP-фикс вышел случайно (косвенно через окна адресов), у другого — **`is_eval_doc`**: детект оценочного корпуса по фамилиям в имени файла/тексте и иное поведение на нём (гейминг гейта, недопустимо).

**Что добавлено в `smart_import_core.py` (+92 строки):**
- **Гигиена `episode` у квалификаций (§4.1)**: `episode` теперь порядковый номер выводного тезиса обвинения (`"1"`, `"2"`, `"3"`…), выставляется ТОЛЬКО при нескольких тезисах; у одиночной квалификации поле не добавляется. Verbose-хвосты («совершил преступление, предусмотренное…», лидирующая запятая) убраны. Сулейманов: 3 записи с `episode` 1/2/3.
- **Канон дома «д. N» (§4.2)**: голое число после улицы → «д. N» ТОЛЬКО для квартирных адресов (Железненко: «ул. Свободы, 23, кв. 65» → «…д. 23, кв. 65», TP 0→1). Уличные сцены без квартиры, литеры («10 «Б»») и дроби не трогаются.
- **Recall адресов (§4.3)**: `PHASE2_MAX_ADDRESSES` 4 → **6** (обоснование: 6 эталонных сцен Евтушенко подряд идут выше шумовых по score; FP=0 на корпусе). Синхронно `MAX_ADDRESSES=6` в `tools/compare_phase2.py`. Евтушенко: **6/6 адресов** (TP=6 FP=0).
- **Типография города**: display-форма «г.Азов»/«г. Азов» сохраняется как в тексте документа (`city_glued`) — эталоны копируют исходную типографию.
- **Crime place (§4.5)**: контекстный выбор residential-метки. Маркеры частного дома («частный (жилой) дом», «частный сектор», «коттедж», «дачный/сельский дом») или «домовладение» + внутренний контекст → «Частный коттедж, сельский, дачный дом» (Асатуллаев TP=1). «Жилой многоквартирный дом» авто-эмиссией НЕ выставляется (в корпусе каждое «многоквартирн…» имеет эталон building=∅ → авто-эмиссия гарантировала бы FP).

**Метрики (гейт `tools/compare_phase2.py`, текущий-vs-эталон):**
- Евтушенко ADDR 4→**6/6** (TP=6 FP=0); Железненко ADDR TP 0→**1**; Асатуллаев CP-building → «Частный коттедж…» (TP=1); Сулейманов quals — 3 записи episode 1/2/3; Сулейманов ADDR 2/1/1 — опечатка эталона «ПроселочкаЯ» (извлечённая форма «Просёлочная» по тексту документа правильная, расхождение задокументировано).
- Persons по-прежнему 2/0/0 на эталонных; checkbox-агрегаты без регрессий (TP=50, FP=13, FN=8).
- pytest: **129 passed**, `py_compile` 3.11 и 3.8 — OK.
- Артефакты: `tests/test_smart_import_phase3.py` (21 тест), `PHASE3_REPORT.md` (корень), обновлённый `tests/test_smart_import_phase2.py` (cap-тест 4→6).

### Удаление ИИ из интерфейса (2026-07-20) ✅
LLM отключена в публичной сборке (невозможно адаптировать под все машины). **Код LLM сохранён** (пайплайн `smart_import_core.py`, `_convert_llm` конвертера, `_detect_pc_power`, `_detect_import_mode`, `_test_llm` и др.), но из UI убран полностью:
- `smart_import_dialog.py`: `import_mode` зафиксирован в `"LIGHT"`; удалены панель выбора режима (CyberOptionMenu ИИ/Логический), бейдж режима, статус LLM, кнопка «Проверить LLM»; title без суффикса режима; текст «Анализ текста с помощью ИИ…» → «Анализ текста документа…». `_update_mode_ui` имеет guard по `hasattr("_mode_badge")`.
- `first_to_third_converter.py`: `initial_mode` всегда `"regex"` (без `_detect_pc_power`); удалены бейдж «🧠 ИИ», радио-кнопка «ИИ», статус-лейбл LLM. Остался один радио «⚡ Логический».
- `app_controller.py`: `self.import_mode = "LIGHT"` вместо `self._detect_import_mode()`.
- **Возврат ИИ в UI**: вернуть панель режима в `SmartImportDialog._build_header`, радио/статус в `FirstToThirdConverter._build_controls`, восстановить авто-детект режима в обоих местах.

### Подсветка заполненных секций — «Место совершения» и «Количество фигурантов» (2026-07-20) ✅
- ✅ **«Место совершения» (родительская секция) не подсвечивалась** при отмеченных чекбоксах в подсекциях. Причина: `_is_widget_non_empty` (`crime_form.py`) понимал `tk.Text`, `Entry`, `ttk.Combobox`, `CyberOptionMenu`, `tk/ttk.Checkbutton`, но **не кастомный canvas-виджет `ModernCheckbutton`** — обход тела родительской секции (`_walk_has_content`) находил «пусто» и `set_has_content(False)` даже снимал подсветку. Фикс: `_is_widget_non_empty` теперь распознаёт `ModernCheckbutton` через `widget._is_checked()`.
- ✅ **«Количество фигурантов» не подсвечивалось при выборе в выпадающем списке**. Причина: `CyberOptionMenu` не испускает `<<ComboboxSelected>>` (AGENTS.md §11: callback идёт через `command` → `_emit`), поэтому `_bind_section_events` на выбор не срабатывал. Фикс: в `_build_perpetrators_count` добавлен `trace_add("write", ...)` на переменную → `_check_section_content("perpetrators_count_section")`; в `_after_set_data_update_highlights` добавлена явная обработка пары var `perpetrators_count` → секция `perpetrators_count_section` (общий цикл `_vars` ищет секцию по имени var и её не находил).
- ✅ Тесты: `tests/test_section_highlight.py` (4 шт.) — ModernCheckbutton, вложенный обход, CyberOptionMenu, строка с комбобоксом.

### Подложка чекбокса — глубокий синий вместо серой (2026-07-22) ✅
- ✅ `ModernCheckbutton._draw_box()` (`modern_widgets.py`): fill неотмеченного чекбокса (состояния normal/hover/disabled) изменён с `self._parent_bg` на **`BG_INPUT`** (`#0d1117`) — чекбокс теперь выглядит как текстовое поле (глубокий синий), а не серое пятно панели. Отмеченное состояние без изменений (заливка `CYAN_NEON`), рамка `BORDER_DEFAULT` → `CYAN_NEON` при hover/отметке. Анимации не затронуты (интерполяции fill нет — bounce меняет только размер).

### Система безопасности: пароль приложения + PBKDF2 (2026-07-23) ✅
**Источник**: аудит безопасности (агент на арене, отчёт `LLM/Безопасность/Работа агента.md`). Концепция агента принята, но его diff содержал синтаксические ошибки (`json.dump` с двумя аргументами, мёртвый код после `return`) — реализовано чисто с нуля.

- ✅ **`src/services/security_manager.py`** (новый): PBKDF2-HMAC-SHA256, 600 000 итераций (OWASP 2023), `secrets.compare_digest`. Опциональный пароль приложения (`config/app_password.json`, формат `{hash, salt, iterations}`). Автоблокировка через `root.after` (весь код в UI-потоке, без `threading.Timer`): таймаут 10 мин, `bind_all("<KeyPress>"/"<Button>")` для отслеживания активности. Только stdlib.
- ✅ **`src/views/app_password_dialog.py`** (новый): 3 диалога Cyber-Neon — `AppLoginDialog` (вход при запуске, 5 попыток → выход), `AppUnlockDialog` (разблокировка, нельзя закрыть/Escape), `PasswordSettingsDialog` (установка/смена/удаление).
- ✅ **`main.py`**: проверка пароля ДО создания основного UI; отмена/исчерпание попыток → `window.destroy()` + выход. Без пароля — запуск как раньше.
- ✅ **`app_controller.py`**: `security` в конструкторе (`security=None` → создаётся внутри), `_security.attach(root)` после `_build_shell`, кнопка `🔒 Пароль` в сайдбаре (`password_command`), методы `_on_inactivity_lock`/`_show_unlock_dialog`/`_open_password_settings`.
- ✅ **`modern_widgets.py`** (`CyberSidebar`): параметр `password_command`, кнопка `🔒 Пароль` (GOLD_NEON) над «О программе».
- ✅ **`constructor.py`** (`PasswordManager`): переведён с plain-text на PBKDF2 (те же хелперы из `security_manager`), прозрачная миграция legacy `{"password": "..."}` при первом чтении.
- ✅ **`config/password.json` в обеих сборках содержит только хеш** — plaintext `12345678` нигде в дистрибутиве нет (дефолт остался `12345678`, просто хранится хешем).
- ✅ JSON проектов **не шифруется** (осознанно): формат согласован с веб-формой централизованного учёта, шифрование сломало бы выгрузку.
- ✅ Тесты: `tests/test_security.py` (23 шт.) — хеширование, CRUD пароля, миграция legacy, fallback в LOCALAPPDATA, lock/unlock.

### Overlay конфигов — фикс Permission denied в Program Files (2026-07-23) ✅
**Проблема**: при установке в `C:\Program Files` каталог `_internal/config` read-only для обычного пользователя. Конструктор падал с `[Errno 13] Permission denied` при сохранении схем/справочников; та же проблема у `ui_settings.json`, `password.json`, статистики сапёра, истории импорта/расчётов, training_logs.

**Решение**: `src/services/config_store.py` (новый) — пользовательские копии конфигов в `%LOCALAPPDATA%/MANGUST_v4/config`:
- **`readable_path(bundled_dir, filename)`**: пользовательская копия, если существует, иначе bundled. Консистентность «прочитал то, что записал» + данные переживают переустановку.
- **`writable_path(bundled_dir, filename)`**: если overlay-копия уже есть → в неё; иначе bundled, если он writable (dev-режим, portable); иначе overlay (каталог создаётся).
- **`writable_dir(bundled_dir, subdir)`**: то же для подкаталогов (training_logs).
- Проверка writable — реальным probe-файлом (на Windows `os.access`/`chmod` на каталог ненадёжен).

**Обновлённые точки чтения/записи** (все идут через config_store):
- `schema_loader.py::load_json` — чтение через `readable_path` (покрывает ВСЕ конфиги приложения).
- `constructor.py` — `_resolve_overlay_paths()` + `_schema_read_files`/`_schema_write_files`/`_lists_*`/`_ui_*`; `_load_all_from_disk`, `_save_all`, `_save_ui_settings`, автосоздание справочника, `PasswordManager` (`_read_file`/`_write_file`).
- `app_controller.py` — сохранение `ui_settings.json`.
- `minesweeper.py` — `_stats_read_path`/`_stats_write_path` для `minesweeper_stats.json`.
- `smart_import_dialog.py` — `processing_history.json`.
- `statute_calculator.py` — `statute_history.json`.
- `smart_import_core.py` — `save_training_log` через `writable_dir`.
- `security_manager.py` — `_candidate_paths`/`_write_path` через config_store; legacy-файл `%LOCALAPPDATA%/MANGUST_v4/app_password.json` (из первой сборки 2026-07-23) по-прежнему находится при чтении.

**Важно**: `config/app_password.json` НЕ создаётся в репозитории — только на ПК пользователя при установке пароля. Тесты: `tests/test_config_store.py` (14 шт.) + E2E-симуляция read-only bundled (SchemaLoader/PasswordManager/SecurityManager пишут в overlay, читают оттуда же, данные переживают «переустановку»). pytest **165 passed** (3.11) / **86 passed** (3.8).

**⚠️ Побочный эффект overlay (2026-08-06)**: пользовательская overlay-копия конфига **маскирует обновления bundled-конфига** в новых сборках (overlay-first чтение). Если в новой версии меняется содержимое `lists.json`/схем по умолчанию, машины, где пользователь уже редактировал конфиги через Конструктор, продолжат видеть СВОЮ копию. Для точечных обновлений (как person_status ниже) overlay-файл патчится скриптом; для крупных — нужна миграция overlay. Тесты изолированы от реального overlay автouse-фикстурой в `tests/conftest.py` (`LOCALAPPDATA` → tmp).

### Коды person_status приведены к веб-форме: 1/2/3 → 2/3/4 (2026-08-06) ✅
**Контекст**: веб-разработчик подтвердил реальные value поля «Статус лица» веб-формы скрином: `2=фигурант (исполнитель, соучастник)`, `3=жертва`, `4=свидетель`. Наши коды были 1/2/3 (позиции, присвоенные при извлечении). **Система кодов**: веб-разработчик просил «наименование раздела и числовой код позиции» — мы передаём позиции/коды опций, его бэкенд маппит их на внутренние value веб-формы (у которой, напр., `investigation_unit` = 2600018).

- ✅ `config/lists.json` + `win7/config/lists.json`: `person_status_values` → web_value **2/3/4** (label'ы не изменились).
- ✅ `migration.py::_normalize_coded_field`: новая ветка **remap по label** — если сохранённый `{код: label}` не совпадает с актуальным справочником, но label в нём есть, подставляется актуальный код. Старые проекты с кодами 1/2/3 не теряют статус (без этой ветки они молча обнулялись бы).
- ✅ Overlay на машинах тестировщиков: `%LOCALAPPDATA%/MANGUST_v4/config/lists.json` пропатчен тем же remap (пользовательские дополнения справочников сохранены).
- ✅ Тесты: `tests/test_person_status_codes.py` (5 шт.) — коды справочника, pass-through новых, remap старых 1/2/3→2/3/4, legacy-строка, roundtrip.
- ✅ Структура JSON от разработчика: «УД → статус лица → лицо → адреса, цифровые следы и т.д.» — соответствует нашей (`crime_case` + `persons[]` с `person_status` и вложенными списками), изменений не требует.

### Рестайлинг фона секций — финальная схема «как в Лицах» (2026-07-22) ✅
**История**: сначала тела секций были сделаны `BG_INPUT`, а поля — карточками `BG_PANEL_LIGHT`. По ревью заказчика это дало смесь «где-то серый, где-то чёрный». **Финальная схема = эталон вкладки «Лица»**:
- **Тело секций/карточек**: `BG_PANEL` (`#161b22`, тёмно-синий, НЕ чёрный).
- **Поля внутри** (комбобоксы, entries, date-picker, списки Решения/Квалификации/Адреса/Файлы, текстовые поля, Фабула): `BG_INPUT`/`BG_APP_DARK` (`#0d1117`, глубокий синий).
- **Квадрат чекбокса**: `BG_INPUT` (см. предыдущий блок).
- **Хедеры секций**: `BG_PANEL_LIGHT` + cyan-glow рамка (стала видна после `autostyle=False`).
- Текстовые секции (Фабула, выписка ОМП и др.): как раньше — тело `BG_PANEL`, текст `BG_PANEL`, зелёный акцент.

**Ключевая находка (важно для всех будущих UI-правок)**: видимый «серый» в приложении — это **не `BG_PANEL`**, а `#222222` — ttkbootstrap через `Bootstyle.override_tk_widget_constructor` принудительно перезаписывает `bg` **всех** `tk.Frame`/`tk.Label` (и `tk.Entry`) без `autostyle=False`. Любая смена цвета в коде невидима без `autostyle=False` (проверено рендер-замерами пикселей). Кастомные ttk-стили (`Modern.TEntry` и др.) регистрируются только через **`StyleEngine()`** (singleton, `_configure_all()`) — вызывается при старте приложения; без него style lookup возвращает пустую строку и виджеты падают в дефолт темы.

**Что осталось от рестайлинга (улучшения)**:
- `ModernCollapsibleSection` (`modern_widgets.py`): параметр **`body_bg`** (default `BG_PANEL`) и **`autostyle=False` во всех внутренних частях** (frame, glow_outer/glow_mid/inner, accent_bar, chevron, title, action-кнопки, separator, body) — задуманные cyan-glow рамка и светлый хедер `BG_PANEL_LIGHT` теперь реально видны во всём приложении (это и есть «шикарные секции» во вкладке Лица).
- `ModernCheckbutton`: `autostyle=False` у frame/`_box_bg`/label + fill квадрата `BG_INPUT`.
- `CyberDatePicker`: внутренние row/entry/label следуют за переданным `bg` (default `BG_INPUT` — обратная совместимость), `autostyle=False` у `tk.Entry`.
- `PlaceholderEntry`: больше не сбрасывает стиль принудительно на `Modern.TEntry` — `self._filled_style`/`self._placeholder_style`; зарегистрированы резервные стили `ModernCard.TEntry`/`PlaceholderCard.TEntry` (сейчас не используются, оставлены на будущее).
- Все фреймы/`_make_label` в `crime_form.py` — `autostyle=False` (иначе цвета невидимы).
- Проверка: рендер-замеры (тело `#161b22`, поля `#0d1117`, хедер `#1c2333`), pytest **129 passed**.

### Формат хранения чекбоксов — словарь `{web_value: label}` (только выбранные в JSON)
- ✅ **Финальный формат по требованию веб-разработчика**: ключ — цифровой `web_value` (строка), значение — текстовый `label` опции. Невыбранные элементы не попадают в JSON.
- ✅ Внутреннее представление (`CrimeCase`, `Person`): checkbox-поля и `crime_place` хранятся как словарь `{web_value: label}` (только выбранные).
- ✅ При сохранении (`to_dict()`) в JSON остаются только выбранные значения: `"status": {"2": "Фигурант достоверно установлен"}`, `"crime_place": {"indoor": {"3971": "Внутреннее жилое помещение"}}`.
- ✅ `crime_form.py` / `person_editor_dialog.py` / `dynamic_form.py`: `get_data()` возвращает `Dict[str, str]`; `set_data()` принимает текущий формат `{web_value: label}`. Сохранена обратная совместимость:
  - старые позиционные массивы `[0, 1, 0, ...]`;
  - старые именованные словари `{"Название чекбокса": 0/1}`;
  - старый список `web_value`;
  - старый словарь `{web_value: 0/1}`.
- ✅ `migration.py`: `_normalize_checkbox()` и `_normalize_crime_place_array()` конвертируют все старые форматы в `Dict[str, str] {web_value: label}` при загрузке проекта, включая частичные index-массивы и списки текстовых меток (например, `crime_region`).
- ✅ `dataclasses.py`: поля `checkbox_group` в `CrimeCase` и `Person`, а также `crime_place` в `CrimeCase`, имеют тип `Dict[str, str]` / `Dict[str, Dict[str, str]]`.
- ✅ `preview_view.py`: `_selected_labels()` и `_render_crime_place()` работают с форматом `{web_value: label}` (с поддержкой legacy-форматов).
- ✅ `app_controller.py`: `_apply_checkbox_matches()` активирует чекбоксы по текстовым меткам; `_convert_smart_import_result()` преобразует LLM-результаты в словарь `{web_value: label}`. Добавлены `_normalize_person_data()` / `_normalize_persons_data()` для нормализации checkbox-полей лица.
- ✅ `json_repository.py`: валидация считает пустой список `[]` и пустой словарь `{}` незаполненным полем.
- ✅ **Конструктор (`constructor.py`)** управляет структурой схемы (`options` с `id`, `label`, `index`, `web_value`), но не форматом данных проекта.
- ✅ Дубликаты `web_value` внутри одного поля запрещены; при обнаружении (например, `tools`) значение уточняется по исходному файлу веб-формы.
- ✅ Синхронизация `config/import_keywords.json`: label ключевых слов приведены в соответствие с `label` опций схемы (кавычки, формулировки), чтобы умный импорт находил чекбоксы по exact match.
- ✅ `crime_region`: переведён из `combobox` + custom `region_checkboxes` в полноценный `checkbox_group` с 123 опциями (регионы РФ и зарубежные государства) из `извлечение.txt`. `CrimeCase.crime_region` теперь `Dict[str, str]` `{web_value: label}`.

### Формат хранения выпадающих списков — словарь `{web_value: label}`
- ✅ **Поля с единственным выбором**: `investigation_region`, `investigation_unit`, `crime_time` теперь хранятся как `Dict[str, str]` `{web_value: label}` вместо простой строки.
- ✅ Справочники `investigation_regions`, `investigation_units`, `crime_time_values` в `config/lists.json` переведены в объектный формат `{ "web_value": "1", "label": "..." }`.
- ✅ `crime_form.py`: `_resolve_list_entries()` возвращает пары `{web_value, label}`; `_make_combobox()` для кодированных полей сохраняет маппинг `label→code`/`code→label`; `get_data()` возвращает `{web_value: label}` (или `{}` при пустом выборе); `set_data()` понимает новый словарь и legacy-строку.
- ✅ `migration.py`: `_normalize_coded_field()` конвертирует старые текстовые значения и legacy-словари в `{web_value: label}`.
- ✅ `dataclasses.py`: поля `investigation_region`, `investigation_unit`, `crime_time` имеют тип `Dict[str, str]`.
- ✅ `preview_view.py`: рендерит текстовую часть словаря через `_coded_label()`.
- ✅ `app_controller.py`: `_convert_smart_import_result()` переводит label-значения из LLM в `{web_value: label}`.
- ✅ `json_repository.py` / `project.py`: `Project.from_dict()` получает `lists_catalog` для миграции кодированных полей.

### Калькулятор сроков давности УК РФ (`statute_calculator.py`)
- ✅ Новая вкладка «Сроки давности УК РФ»
- ✅ Поисковый выбор статьи УК РФ (`SearchableCombobox`) + кнопка **✕** для мгновенной очистки выбранной статьи
- ✅ **Глобальный выбор основания приостановления** (вместо per-row combobox): `ModernCombobox` со значениями:
  - "Производство по делу не приостанавливалось"
  - "п. 1 ч. 1 ст. 208 УПК РФ (приостановлено в связи с неустановлением лица)"
  - "п. 2 ч. 1 ст. 208 УПК РФ (приостановлено в связи с розыском)"
- ✅ **Per-row чекбокс** в каждом периоде приостановления (`ModernCheckbutton`). Если галочка снята — период игнорируется.
- ✅ **`global_basis` в сервисе**: если ни один период не отмечен, но глобальное основание выбрано (п.1 или п.2), `StatuteLimitationsService.calculate(..., global_basis="208_1"/"208_2")` применяет основание без конкретных дат.
- ✅ **Post-1997 розыск** (`event_date >= 1997-01-01`, п.2): статус `suspended_manhunt` (или `suspended_manhunt_high` для высшей меры) — срок не истекает, `final_end_date = None`, таймлайн показывает **∞ / розыск**.
- ✅ **Pre-1997 розыск** (`event_date < 1997-01-01`): единый 15-летний предел по **ст. 48 УК РСФСР** для ВСЕХ pre-1997 преступлений (разделение по `RSFSR_CUTOFF_DATE` убрано). Если с даты совершения прошло > 15 лет → `expired`, иначе `suspended_manhunt`.
- ✅ **Fixed-point расчёт** срока с учётом периодов розыска (ст. 208 УПК РФ).
- ✅ История расчётов
- ✅ Копирование и сохранение результатов

### Справочник УК/УПК РФ (`statute_reference_view.py`, `statute_repository.py`)
- ✅ Новая вкладка «Справочник УК/УПК РФ»
- ✅ База данных `config/uk_upk_database.json` (492 статьи УК РФ + **558 статей УПК РФ**)
- ✅ **УК РФ** — точная иерархия: Общая часть / Особенная часть → Раздел (I–XII) → Глава (1–34) → Статья
- ✅ **УПК РФ** — точная иерархия: Часть (первая–шестая) → Раздел (I–XIX) → Глава (1–57) → Статья
- ✅ Диапазоны статей встроены в названия разделов и глав (например, `Глава 1. ... (ст. 1-5)`)
- ✅ Treeview tooltips при наведении на узлы (показывает полный текст обрезанных строк)
- ✅ **Поисковый выбор статьи** (`SearchableCombobox`) — выпадающий список с фильтрацией по номеру, названию и ключевым словам
- ✅ При активном поиске левое окно показывает **плоский список статей** (без иерархии разделов/глав) с подсветкой совпадений (`search_match`)
- ✅ При пустом поиске — классическая иерархия: часть → раздел → глава → статья
- ✅ Фильтр: Все / УК РФ / УПК РФ
- ✅ Просмотр текста статьи с разбивкой по частям, inline-бейджами категорий, санкциям и примечаниям
- ✅ Копирование номера статьи и текста в буфер обмена
- ✅ Сортировка результатов: УК РФ first, затем УПК РФ, по номеру статьи
- ✅ Контекстное меню (Копировать / Выделить всё) в правой панели
- ✅ Правильная работа выделения текста (`tag_raise("sel")`) поверх цветных фонов (например, note_box)
- ✅ Fallback для одночастных статей: при `parts=["ч.1"]` текст выводится целиком без разбивки по `^\d+\. ` и **без заголовка «Часть 1»**, чтобы не вводить пользователя в заблуждение (исправлено для ст. 138.1, 171.4 и др.)
- ✅ Заголовок статьи внутри `tk.Text` выделен тегом `article_title` (жирный, белый) и отделён пустой строкой от основного текста; дублирующий `Label` с названием над текстом удалён, чтобы не занимать место
- ✅ Абзацный отступ первой строки ~1.25 см (`lmargin1=35 pt`) для `part_body` и `sanction`; продолжение строк без отступа (`lmargin2=0`)
- ✅ Inline-бейдж тяжести теперь располагается на одной строке с заголовком «Часть N» (`align="center"`), убирая лишний вертикальный зазор
- ✅ Уменьшен внутренний отступ `tk.Text` (`pady=4` вместо `12`), текст прижат ближе к верхнему краю окна просмотра
- ✅ Размер шрифта правой панели увеличен до 11 pt

### Гендерный выбор
- ✅ **Убрано автоопределение пола** — выбор обязателен (Мужской/Женский)
- ✅ Блокировка конвертации без выбранного пола
- ✅ Сброс пола при очистке полей

### Дизайн и UI
- ✅ Cyber-Neon тёмная тема (`modern_widgets.py`)
- ✅ ModernButton (Neon Edge), GlowFrame, ModernScrollbar
- ✅ Hover-эффекты, анимации, неоновые рамки
- ✅ Обработка окна загрузки со спиннером и таймером
- ✅ Кликабельная ссылка Max (мессенджер) + кнопка копирования контактов

### ModernCollapsibleSection — анимация раскрытия убрана (`modern_widgets.py`)
- ❌ **Canvas-based expand/collapse animation удалена** — из-за фундаментального конфликта `winfo_reqheight` embedded frame и `bbox("all")` внешнего scroll-canvas анимация вызывала растягивание scrollregion, обрезку заголовков и лаги.
- ✅ Возвращён мгновенный `pack`/`pack_forget` (как в старой версии). `_body_canvas`, `_body_window`, `_animate_body`, `_finalize_expand`, `_finalize_collapse` — удалены.
- ✅ `section.body` снова является прямым потомком `ModernCollapsibleSection` (`tk.Frame(self, ...)`), а не вложен во внутренний canvas.

### Рамка карточки лица — фикс `ttkbootstrap autostyle` (`person_form.py`)
- ⚠️ **Проблема**: `ttkbootstrap` через `update_frame_style()` принудительно сбрасывает `highlightthickness=0` у всех `tk.Frame` без `autostyle=False`, делая рамку карточки невидимой.
- ✅ **Фикс**: `outer` frame теперь имеет `bg=BORDER_DEFAULT` + `autostyle=False`, внутри него `inner` frame с `bg=BG_PANEL` и `padx=1, pady=1`. За счёт этого образуется ровная 1-пиксельная рамка цвета `BORDER_DEFAULT`.
- ✅ Все виджеты внутри карточки (`shadow`, `card_header`, `content`, `btn_frame`, `tk.Label` и т.д.) получили `autostyle=False`.

### Важно: ttkbootstrap `autostyle` и кастомные фоны
- ⚠️ **Критический баг Windows/tkk**: `ttkbootstrap` через `Bootstyle.override_tk_widget_constructor` принудительно меняет `bg` у `tk.Frame`, `tk.Label`, `tk.Text` на цвет темы (`BG_PANEL`).
- ✅ **Фикс**: ко **всем** `tk.Frame`, `tk.Label`, `tk.Text`, которым нужен кастомный `bg=BG_INPUT` (или другой), **обязательно** передавать `autostyle=False`.
- ✅ Это исправлено во всём `statute_reference_view.py` (~20 виджетов) и других модулях.

### ModernButton — Neon Edge redesign (`modern_widgets.py`)
- ✅ **Концепция Neon Edge**: тёмное тело кнопки (`BG_PANEL`) + неоновая акцентная полоска снизу (2px rest → 3px hover/active).
- ✅ **Убрано**: canvas-based ripple-анимация, яркая заливка всей кнопки, emoji в текстах.
- ✅ **Добавлено**: strip flash (белый 80ms) при клике, плавная анимация возврата к REST через `interpolate_color`.
- ✅ **Hover без мигания**: `_pointer_inside_self()` через `winfo_containing()` — надёжная проверка при переходе между дочерними виджетами.
- ✅ **Поддержка фокуса**: `FocusIn`/`FocusOut` для Tab-навигации.
- ✅ **API сохранён**: `configure(text=...)`, `set_text(...)`, `get_text()`, `configure(command=...)`, `configure(state=...)`, `width`.
- ✅ **Убраны emoji** из всех вызовов `ModernButton` по проекту (Загрузить, Сохранить, Новый, Умный импорт, Добавить, Удалить, Редактировать, Обновить и др.).

### Важно: стиль `Modern.TCombobox` и `ModernCombobox`
- ⚠️ **Критический баг Windows/tkk**: стиль `Modern.TCombobox` с `selectbackground=BG_INPUT` и сложным `map` (с `lightcolor`/`darkcolor`/`background`) ломает отрисовку стрелки выпадающего списка при пустом значении в `readonly`-режиме.
- ✅ **Фикс**: стиль `Modern.TCombobox` и класс `ModernCombobox` возвращены к рабочей версии (`selectbackground=BG_CARD`, `selectforeground=CYAN_NEON`, упрощённый `map`, без `_force_dark_bg`/`_on_selected`).

### Контактная информация (источник истины)
```
Гайнутдинов Станислав Игоревич
E-mail: gainutdinov@61.sledcom.ru
Max: https://max.ru/u/f9LHodD0cOKPf_YmNa6x3gO281-u9uSgyvfairSziqaSykAigRch_WIbMjc
```
Находится в `app_controller.py::_show_about()` и дублируется в диалогах конвертера/суммаризатора.

### Кодированные выпадающие списки во всех диалогах (2026-06-29)
- ✅ Все поля с выбором из справочника (combobox) теперь сериализуются в JSON как `{web_value: label}` — включая ранее «голые» строковые константы.
- ✅ В `config/lists.json` добавлены справочники:
  - `decision_types` — виды решений по уголовному делу;
  - `address_types_person` — типы адресов для формы лица (подмножество `address_types`).
  - `address_types` уже содержал полный набор типов адресов для формы преступления.
- ✅ `src/views/dialogs.py`:
  - `DECISION_TYPES`, `ADDRESS_TYPES_CRIME`, `ADDRESS_TYPES_PERSON` переведены в объектный формат `{web_value, label}`;
  - `DecisionDialog` и `AddressDialog` принимают `lists_catalog` и используют справочники из `config/lists.json`;
  - `BaseEntityDialog._normalize_combo_entries` корректно работает как с объектами, так и со строками.
- ✅ `src/mangust_v4/models/migration.py`:
  - Добавлен `_normalize_entity_list` — кодирует поле `type` в `decisions`, `addresses`, `documents`, `transport`, `identifiers` в `{web_value: label}` при загрузке старых файлов.
- ✅ `src/controllers/app_controller.py`:
  - `_convert_smart_import_result` конвертирует текстовые `type` вложенных сущностей (decisions/addresses/persons) в `{web_value: label}`.
- ✅ `src/views/preview_view.py` — предпросмотр уже использует `_coded_label()` для отображения текстовой части кодированного словаря.
- ✅ `src/views/constructor.py` — в редактор справочников добавлены отображаемые названия для `decision_types` и `address_types_person`.
- ✅ Тесты: добавлены `tests/test_coded_combobox_fields.py` и обновлены фикстуры в `tests/conftest.py`; прогон `pytest -q` — **41/41 passed**.

### Обязательная валидация и UX подсветки ошибок (2026-07-13)
- ✅ Вынесен `ValidationController` (`src/controllers/validation_controller.py`) — единый источник обязательных полей для Конструктора и валидации.
- ✅ Обязательные поля происшествия: `case_number`, `case_date`, `reg_number`, `investigation_region`, `investigation_unit`, `is_serial`, `crime_date_from/to`, checkbox-группы (`status`, `crime_type`, `motive`, `method`, `tools`), модальные списки (`decisions`, `qualifications`, `addresses`).
- ✅ Обязательные поля лица: идентификаторы (`identifiers`) и любые `required_if_form_filled`-секции из `schema_person.json`.
- ✅ `CrimeFormView` подсвечивает пустые обязательные поля (`entry`, `combobox`, `date`, `text`, модальные списки, checkbox-секции). Подсветка снимается при вводе/выборе.
- ✅ `PersonFormView` подсвечивает красным рамку карточек лиц с незаполненными обязательными полями.
- ✅ `ModernCollapsibleSection.set_validation_error()` делает ошибку заметной: красный заголовок, красная стрелка, красная акцентная полоса, красная внешняя рамка 2 px.
- ✅ `ValidationErrorDialog` (`src/views/modern_widgets.py`) — группировка ошибок по «Происшествие» / «Лицо N» с цветными заголовками; прокрутка работает и за ползунком, и колёсиком мыши (рекурсивный бинд на все дочерние виджеты).
- ✅ `PersonEditorDialog` не даёт сохранить лицо без идентификаторов.
- ✅ Тесты: `tests/test_validation_controller.py`.

### Отображение кодированных значений в UI без служебного кода (2026-07-13)
- ✅ Формат хранения в JSON остался `{web_value: label}`, но пользователь видит только `label`.
- ✅ `src/views/dynamic_form.py`: `StructuredListWidget._display_value()` извлекает `label` из `{web_value: label}`. `_make_label()` использует его для всех модальных списков: `decisions`, `qualifications`, `addresses`, `documents`, `transport`, `identifiers`.
- ✅ `src/views/person_form.py`: `PersonFormView._display_value()` убирает служебный код при отображении статусов, личности, местонахождения, физического состояния, пола.
- ✅ Тесты: `tests/test_display_labels.py`.

---

## 7. Активные проблемы и TODO

### Критические
- [x] **Windows + llama-cpp — CUDA/GPU** (исправлено):
  - VC_redist уже установлен (v14.50).
  - `llama-cpp-python` понижена до **0.2.90** — единственной версии с pre-built CUDA wheel для Windows (cu121). Версии 0.3.x имеют wheels только для Linux.
  - `os.add_dll_directory` + `PATH` для LM Studio backend добавлены в `main.py` и `smart_import_core.py`.
  - `CUDA_PATH` специально **не** выставляется, т.к. `llama_cpp/_ctypes_extensions.py` ожидает подпапки `bin/` и `lib/`, а в LM Studio backend DLL лежат в корне.
  - Для собранной portable-сборки и установщика Win10/11 CUDA runtime (`cudart64_12.dll`, `cublas64_12.dll`, `cublasLt64_12.dll`) копируется в `dist/MANGUST_v4/_internal` из `installer/cuda_runtime/` через `MANGUST_v4.spec`; в установщике — тот же компонент, кладущий DLL в `{app}\_internal`.
  - Проверено: `llama_supports_gpu_offload() -> True` на RTX 3070.

### Placeholder (в процессе)
- ✅ **Критический баг PlaceholderEntry исправлен** (тусклый текст после удаления, пропадание при Alt-Tab). См. раздел 6.
- [ ] Добавить `PlaceholderEntry` / `PlaceholderText` в остальные модальные окна:
  - `AddressDialog`, `DecisionDialog`, `QualificationDialog`
  - `DocumentDialog`, `TransportDialog`, `IdentifierDialog`
- [ ] Проверить, что placeholder не мешает `get_data()` / `set_data()` в диалогах

### UI / Отрисовка (исправлено ✅)
- [x] **Наложение вкладок при уменьшенном окне**: после перехода на системный chrome + `WS_EX_COMPOSITED` старая вкладка оставалась видимой поверх новой до разворачивания окна. Исправлено принудительной перерисовкой окна в `HiddenNotebook.select` (`_send_setredraw` + `InvalidateRect` + `UpdateWindow`).
- [x] **Прокрутка колесом в DayCalculatorView**: колесо мыши не работало в центральной колонке. Исправлено паттерном Enter/Leave + `bind_all`/`unbind_all` с проверкой координат курсора.
- [x] **Растягивание области предпросмотра фото в редакторе лица после удаления**: `Label` превью получал `width=150, height=150` при загрузке фото, а при удалении размеры не сбрасывались, из-за чего секция «Фотографии лица» раздувалась. Исправлено в `person_editor_dialog.py`: превью обернуто в фиксированный `Frame` 150×150 px с `pack_propagate(False)`; `Label` внутри центрируется через `place`, а `_update_photo_preview` больше не меняет `width/height` Label.

### Конвертер (улучшения)
- [ ] Дообучение/улучшение RegEx на основе разницы ИИ vs RegEx (собрано 4 файла: Юркевич, Толмачев, ЦВЫК, Маринина)
- [ ] Добавить больше post-processing для LLM (остатки "мной" в некоторых контекстах)

### Smart Import — Stage 1 MVP (завершён ✅)
**Результаты:**
- **Точность RegEx-first v3**: Грабёж 64.7%, Убийство 76.5%, **среднее 70.6%** (цель 70–80% достигнута)
- **Скорость**: 0.01–0.02с на документ (CPU, без LLM)
- **Все улучшения интегрированы** в `src/mangust_v4/services/smart_import_core.py`

**Ключевые исправления (интегрированы):**
- `case_number`: фильтр IMEI (15 цифр, начинающихся с 35/86/99)
- `case_date`: fallback на дату преступления, если шапка пустая; фильтр "суд"/"привлекался"/"назначением наказания"
- `crime_date_from/to`: ±150 символов контекст, фильтр "показания"/"приказ"/"постановление"; ограничение фабулы границами секций
- `qualifications`: поиск **только в фабуле** (исключает дубли из показаний/заключений); фильтр судимостей (±200 символов)
- `crime_type`: детерминированный маппинг по статье УК → массив индексов
- `reg_year`: приоритет `case_date` → `crime_date_to` → `case_number` (последние 4 цифры)
- `perpetrators_count`: приоритет фабулы (маркеры ФИГУРАНТ/СОУЧАСТНИК + "неустановленное лицо") → блок "ОБВИНЯЕТСЯ:"
- `crime_time`: преобразование точного времени в категорию суток ("с 22 до 06 часов" и т.п.)
- `omp_protocol` / `sme_conclusion`: добавлены в `_parse_accusation_v5`

**Ограничения (зависят от входных данных):**
- Тестовые .txt имеют повреждённую шапку (пустые поля `____`) → `case_date` и `investigation_unit` невозможно извлечь
- `omp_protocol` / `sme_conclusion` не валидируются, т.к. тестовые документы — фрагменты
- `qualifications` для многоэпизодных грабежей: фабула содержит 1 упоминание статьи, эталон ожидает N записей (по числу эпизодов)

### Smart Import — Stage 1.5 (завершён ✅)
**Цель:** довести RegEx-first до 75–80% на реальных .docx документах.

**Результаты на реальных .docx (финальные):**
| Документ | Точность | Примечание |
|----------|----------|------------|
| Русских А.В. (убийство, ст.105) | **14/14 (100%)** | Все поля совпадают (с учётом устаревших эталонов) |
| Пугачёва М.Н. (убийство, ст.105) | **12/14 (85%)** | investigation_unit эталон устарел (Октябрьский→Первомайский); sme_conclusion — разные экспертизы |
| Сулейманов Р.Е. (грабёж, ст.161) | **10/14 (71%)** | case_date и investigation_unit в эталоне устарели; addresses — 219/2 vs 225/2 (эталон неполный) |
| **Среднее** | **85.3%** | Цель 75–80% достигнута |

**Ключевые улучшения (интегрированы):**
- `app_controller.py` — **исправлен баг мержа**: `_on_import_result` не мержил `crime_region` и `crime_type` (списковые поля вне `decisions`/`addresses`/`qualifications`). Добавлен отдельный блок мержа checkbox-групп.
- `_articles_to_checkboxes`: добавлен маппинг **ст. 134** (сексуальные преступления).
- `_extract_victims_v5`: добавлен **fallback из фабулы** — если в секции "Данные о потерпевших" нет данных, ищем ФИО + дата рождения после маркеров "с", "в отношении", "нанес", "убил", "ранил" в фабуле. Исключаем обвиняемого.
- `_extract_addresses_v5`:
  - Улучшен `_normalize_address`: убирает префиксы "Место совершения преступления", "место жительства", `\xa0` (неразрывный пробел).
  - Добавлен fallback: поиск `место совершения преступления` по **всему тексту** (не только первые 5000 символов), извлечение адреса паттерном `г. ... ул. ... д. ...`.
  - Фильтрация: исключение адресов с ключевыми словами "проживает", "жительства", "регистрации".
  - Лимит возвращаемых адресов увеличен до 3 (было безлимитно → 11 адресов).
- `_extract_omp_protocol`:
  - Теперь возвращает **все протоколы** из документа (объединённые через `\n`), а не только первый.
  - Если кандидат начинается с "от ДД.ММ.ГГГГ" — добавляется префикс "Протокол осмотра места происшествия".
- `_extract_stolen_items_extended`: добавлена нормализация винительного падежа → именительный (`сумку` → `сумка`, `кольцо` не меняется).
- `test_real_docs_v4.py`: улучшенная логика сравнения:
  - Fuzzy-match для `addresses` (префикс/суффикс).
  - Частичное совпадение для длинных строк (`omp_protocol`, `sme_conclusion`) с нормализацией `\n ` → `\n`.
  - Пустой эталон + непустой факт = `[PART]` (эталон устарел).

**Известные ограничения:**
- Тестовые эталоны частично устарели (case_date Сулейманова — возбуждение vs утверждение; investigation_unit — старые районы).
- `addresses` Сулейманова: факт извлекает `219/2`, эталон содержит `225/2, 22, 11` — возможно, эталон неполный.
- `sme_conclusion` Пугачёвой: эталон `№ 4193-Э` (экспертиза трупа), факт `№ 2439` — разные экспертизы в документе.

**Временные файлы:** `test_real_docs_v4.py` (тест на реальных .docx). **Временные файлы удалены** после завершения работы.

### Smart Import — Исправление извлечения жертв (2025-06-04) ✅
**Проблема:** В документе "Русских А.В." (убийство, ст.105) вместо прямой жертвы **Васильев А.С.** извлекались родственники **Кочеткова Н.А.**, **Склярова С.В.**, **Павлова Н.С.** из секции "Данные о потерпевших" (моральный вред).

**Причины:**
1. Фабула fallback (`fab_vic_pat`) требовал **двойной пробел** после предлога "с" из-за лишнего `\s+` в regex.
2. `_normalize_name_case` не нормализовал косвенные падежи (`Васильевым` → `Васильев`).
3. `victim_pat` (основной паттерн для dedicated-секции) использовал `.*?` **без `re.DOTALL`**, поэтому не пересекал разрывы строк между датой рождения и адресом.
4. Фильтр `моральный вред` проверял только `residence`, а не полный контекст найденного совпадения.
5. Приоритет: `victims[:3]` обрезал фабульную жертву, потому что она добавлялась **после** dedicated-жертв.

**Исправления в `smart_import_core.py`:**
- `fab_vic_pat`: убран лишний `\s+`, добавлен `re.DOTALL` к `victim_pat`.
- `_normalize_name_case`: добавлена простая нормализация падежей (`-ым→`, `-ой→-а`, `-евым→-ев` и т.д.).
- `_extract_victims_v5`: реструктурирован на `victims_dedicated` + `victims_fabula`.
- Контекстный фильтр `моральный вред`: теперь проверяет `src[m.start()-50 : m.end()+800]` с `re.search(r'моральный\s*вред', ctx)`.
- Фильтр без даты рождения: требует, чтобы отчество оканчивалось типично (`-ович`, `-евич`, `-овна`, `-оглы`, `-кызы` и т.д.).
- **Приоритет**: если `victims_fabula` не пустой — возвращаются **только** фабульные жертвы (прямые), иначе — dedicated.
- Результат: "Русских" → 1 жертва (Васильев А.С.), "Пугачёва" → 1 жертва (Вардиашвили Д.К.), "Сулейманов" → 1 жертва (Сайфушева Л.И.).

### Smart Import — Уведомление после импорта (2025-06-04) ✅
**Задача:** После применения умного импорта показывать модальное окно с процентом заполнения формы и предупреждением о необходимости сверки.

**Реализовано:**
- `show_smart_import_notification()` в `src/views/modern_widgets.py` — Cyber-Neon диалог:
  - Неоновая линия сверху (`CYAN_NEON`), тёмный фон (`BG_APP_DARK`).
  - Крупный процент заполнения цветом: зелёный (≥70%), жёлтый (≥40%), красный (<40%).
  - Текст: "Форма заполнена (X из Y ключевых полей)" + статистика (лица, чекбоксы).
  - **Пульсирующий блок предупреждения** (`PulsingWarningBlock`): фон плавно пульсирует между `GOLD_DARK` (`#b45309`) и `GOLD_NEON` (`#fbbf24`) с периодом 1200 мс. Весь блок полностью закрашен ярким золотым, текст тёмный (`BG_APP_DARK`) для контраста.
  - Кнопка "Закрыть" (`ModernButton`, variant="primary"), закрытие по `Enter` / `Escape`.
- `_calculate_fill_percent()` в `app_controller.py` — расчёт по 21 ключевому полю формы преступления.
- Вызов уведомления в `_on_import_result()` после завершения мержа и обновления UI.

### Smart Import — Stage 2 (завершён ✅)
**Цель:** интеграция LLM как fallback для полей, где RegEx вернул пусто или конфликт.

**Архитектура (реализовано):**
1. **`process_file` — RegEx-first (всегда):**
   - Сначала запускается `_process_with_regex` (как в `LIGHT`).
   - Результат помечается `_engine="regex"`, `_llm_used=False`.
2. **LLM fallback (только для пустых/проблемных полей):**
   - `_get_llm_fallback_fields(regex_result, doc_type)` проверяет: `addresses`, `omp_protocol`, `sme_conclusion`, `qualifications`, `investigation_unit`, `case_date`, `crime_date_from/to`, `traces_research`, `stolen_items_extended`, `_persons`.
   - Если список непустой — запускается `LLMPipeline.run()` на весь документ (сохранены существующие prompt'ы и валидация).
   - `_merge_llm_fallback()` внедряет LLM-данные **только** в пустые/неполные поля RegEx. Уже заполненные поля не затираются.
   - Результат помечается `_engine="regex+ai"`, `_llm_used=True`.
3. **Оптимизации:**
   - Для текстовых полей (`omp_protocol`, `sme_conclusion` и др.) берётся более длинный вариант (LLM > RegEx + 20%).
   - Для `_persons` и `addresses` — union по уникальности (дедупликация по ФИО/адресу).
   - Для `qualifications` — дедупликация по ключу `article|part|point|episode`.
   - Если все поля заполнены RegEx — LLM не вызывается вообще (экономия времени).

**Файлы:**
- `src/mangust_v4/services/smart_import_core.py` — `_get_llm_fallback_fields`, `_merge_llm_fallback`, `_qual_key`.
- `main.py` + `smart_import_core.py` — фикс CUDA-путей (`add_dll_directory` + `PATH`, без `CUDA_PATH`).

### Smart Import — Stage 1.5+ (RegEx-first hardening, 2025-06-04)
**Цель:** устранить регрессии и повысить точность извлечения на сложных документах (Железненко ст.105, Касацкий ст.132, Апонасенко ст.111) без деградации на уже проверенных (Русских, Пугачёва, Сулейманов).

**Критические фиксы `smart_import_core.py`:**
- **`_extract_sme_conclusion` / `_extract_traces_research`**: заменён greedy `([\s\S]*?)` на lookahead-терминатор `(?=\n\s*(?:\(т\.\s*\d+|\(том №|Заключение\s+эксперта\s+№|Протокол|Показания|Кроме\s+того|\Z))`. Ранее regex «перепрыгивал» через несколько заключений и возвращал кровяную экспертизу вместо СМЭ. Убран capturing group (fix `IndexError: no such group` в `_extract_traces_research`).
- **`_extract_perpetrators_count`**: приоритет блока `ОБВИНЯЕТСЯ:` (ограничен до фабульных маркеров) над фабульным подсчётом ФИО. Добавлена фильтрация служебных лиц (`следователь`, `эксперт`, `переводчик`, `адвокат`, `защитник`, `понятой`) при подсчёте по фабуле.
- **`_extract_victims_v5`**: добавлен dash-паттерн `– Фамилия Имя Отчество` и `проживающий` regex. Фильтр `моральный вред` в dedicated-секции ослаблен — проверяется контекст ±50/+800 символов вокруг совпадения, а не только поле `residence`.
- **Checkbox fallbacks для LIGHT-режима**: `_parse_accusation_v5` автоматически генерирует `_checkbox_matches` для `status`, `motive`, `tools`, `injuries`, `crime_place_*` когда LLM недоступен. Мотив «Бытовой» определяется по ключевым словам (`конфликт`, `неприязненных отношений` в `import_keywords.json`). Мотив «Сексуальный» — по статьям 131–135.
- **Injuries scope guard**: fallback injuries (шея, туловище и т.д.) заполняются только для violent-статей (105–108, 111, 112, 115, 118, 119) или если в фабуле есть «убийств»/«смерт».
- **Дедупликация**: `_build_qualifications` дедуплицирует по ключу `article:part:point`. `_articles_to_checkboxes` использует `dict.fromkeys()` для уникальности лейблов.
- **Runtime fixes**: исправлены `NameError: name 'articles' is not defined` и `UnboundLocalError: cannot access local variable '_primary_art'` в `_parse_accusation_v5` — переменные вынесены в правильный scope.

**Фиксы в других модулях:**
- **`app_controller.py`**: мерж импортированных checkbox-полей расширен — добавлены `status` и `crime_place_*` (`indoor`/`building`/`outdoor`).
- **`crime_form.py`**: поля с кастомным `bg` получили `autostyle=False` (предотвращает перезапись ttkbootstrap).
- **`config/import_keywords.json`**: добавлены триггеры `конфликт`, `неприязненных отношений` → мотив «Бытовой».

**Результаты верификации:**
| Документ | Статья | Статус |
|----------|--------|--------|
| Железненко | ст.105 | ✅ СМЭ №106, трасологическое №74, 2 лица, мотив «Бытовой» |
| Касацкий | ст.132 | ✅ мотив «Сексуальный», тип «Насильственное действие сексуального характера (ст. 132 УК РФ)» |
| Апонасенко | ст.111 | ✅ мотив «Бытовой», тип «Причинение тяжкого вреда здоровью (ст. 111 УК РФ)» |
| Русских | ст.105 | ✅ без регрессий |
| Пугачёва | ст.105 | ✅ без регрессий |
| Сулейманов | ст.161 | ✅ без регрессий |

**Решённые runtime-баги:**
- `IndexError: no such group` — `_extract_traces_research` использовал capturing group внутри `finditer`, а потом обращался к `m.group(1)`. Fix: `m.group(0)`.
- `NameError: name 'articles' is not defined` — в `_parse_accusation_v5` осталась ссылка на старое имя переменной после рефакторинга. Fix: переименовано в `articles_meta`.
- `UnboundLocalError: cannot access local variable '_primary_art'` — `_primary_art` использовалась в блоке fallback до инициализации. Fix: вынесена в начало функции.

### Smart Import — Улучшение парсинга прекращений (2026-06-04) ✅
**Цель:** научить RegEx-first парсер корректно извлекать данные из постановлений о прекращении УД (`termination`).

**Тестовые документы:**
| Документ | Статья | Эталонные persons | Результат |
|----------|--------|-------------------|-----------|
| Плиш 2016687357 | ст.105 ч.1 | Плиш Г.В. (фигурант), Кошелев В.Ю. (жертва) | ✅ Совпадает |
| Лебедь 2016527092 | ст.109 ч.2 | Лебедь А.И. (жертва) | ✅ Совпадает |
| 117 Абу-Самак | ст.110 ч.2 п.в | Погорелова З.Н., Абу-Самак Ф.М. (жертвы) | ✅ Основные persons найдены (±лишние родственники) |

**Ключевые фиксы `smart_import_core.py`:**
- `_normalize_text`: очистка `\r` (разрывала word-boundary проверки).
- `_extract_sections_v5`: добавлены якоря `ustanovil`/`postanovil` для корректного разбиения прекращений; `FABULA_STARTS` теперь ищет ближайший к началу якорь (исправляет захват середины документа).
- `_parse_termination_v5`: полноценный парсер — теперь извлекает fabula, crime_date, investigation_region/unit, status, qualifications, addresses, victims, checkboxes.
- `_extract_victims_v5`:
  - `fab_vic_pat3` — поддержка инициалов (`В.Ю.`) без `IndexError`.
  - `text_vic_pat` / `text_vic_pat2` — поиск жертв по всему тексту (не только фабула).
  - `hyphen_pat` / `hyphen_initials` — поддержка двойных фамилий (`Абу-Самак Ф.М.`).
- `_filter_persons_by_age`: добавлен `reference_year` — возраст вычисляется относительно года дела, а не текущего (критично для детей-жертв).
- `_filter_related_persons`: исключает родственников (дети с "дочь"/"сын" в контексте), даже если они формально названы "потерпевшими".
- `_deduplicate_persons`: дедупликация с учётом двойных фамилий (сохраняет более полный вариант `Абу-Самак` vs `Самак`).
- `_articles_to_checkboxes`: добавлен маппинг ст.110 → `crime_type="Самоубийство"` (label синхронизирован со схемой и `web_value=4`).
- `_parse_termination_v5` (дети): accused с возрастом < 12 автоматически переклассифицируется в "жертва".

**Регрессии:**
- Обвинительные документы (Русских, Пугачёва, Сулейманов) — без регрессий.

### Smart Import — Termination docs: инициалы, ложные жертвы, адреса (2026-06-05) ✅
**Цель:** второй проход по прекращениям — раскрытие инициалов, фильтрация ложных жертв, улучшение адресов.

**Новые документы:** Аветисьянц, Владыкин, Рябов.

**Изменения `smart_import_core.py`:**
- **`_expand_initials(person, full_text)`**: ищет в полном тексте полное ФИО, соответствующее инициалам (фамилия + первая буква имени/отчества), и заменяет инициалы на полные имя/отчество. Использует `pymorphy3.MorphAnalyzer` для лемматизации фамилии (обрезает падежные окончания при поиске).
- **`_normalize_name_case(name)`**: добавлены суффиксы творительного падежа (`-ием→-ий`, `-еем→-ей`, `-аем→-ай`, `-ой→-а`, `-ым→` и др.) + интеграция `pymorphy3` для автоматической нормализации. Исправляет `Геннадием` → `Геннадий`, `Кошелевым` → `Кошелев`.
- **`_filter_false_victims(persons, text)`**: трёхуровневая фильтрация:
  1. **Deceased relatives**: исключает persons, у которых в контексте (±150 символов) есть death-words (`умерла`, `скончалась`) БЕЗ victim-markers (`погиб`, `убит`, `насильственной смерти`).
  2. **Children (< 12)**: исключает детей с маркерами `дочь`, `сын`, `детей` в контексте.
  3. **Parents of other victims**: исключает родителей, если в контексте есть `мать`/`отец`/`родитель` и person упоминается раньше слова `дочь`/`сын`. Защищено victim-markers: если в ЛЮБОМ контексте найден `убита`/`признана потерпевшей`/`насильственной смерти` — person остаётся.
- **`_extract_addresses_v5(text)`**:
  - Обратный порядок адресов: `в квартире № X дома № Y по ул. ... в городе ...`.
  - Улицы с цифрами: `40-летия Победы` теперь ловятся.
  - `_normalize_address` переводит обратный порядок в стандартный и чистит пунктуацию.
  - Поиск ведётся и в `fabula`, и в полном `text` (fallback).
- **`_extract_sections_v5` (фабула прекращений)**:
  - Добавлены стоп-слова: `\nДОПРОШЕННЫЙ`, `\nСВИДЕТЕЛЬ`, `\nДопрошенный`, `\nСвидетельница`.
  - Убраны слишком ранние: `\nПРОТОКОЛ`, `\nРАПОРТ` (резали фабулу в описательной части).
  - Жёсткий лимит: если после стоп-слов фабула всё ещё > 6000 символов — обрезается по последнему предложению.
- **`_get_llm_fallback_fields`**: для `doc_type == "termination"` возвращает пустой список — LLM fallback НЕ используется. FULL-режим для прекращений работает как LIGHT (только RegEx).
- **Исправлен `NameError: _fp_words`** в `_extract_victims_v5`: переменная вынесена из внутреннего блока `if fabula:` в начало метода.

**Зависимость:** `pymorphy3` + `pymorphy3-dicts-ru` (замена `pymorphy2`, которая сломана на Python 3.11 из-за удалённого `inspect.getargspec`).

### Smart Import — Улучшение импорта протоколов допроса (2026-06-16) ✅
**Цель:** повысить точность RegEx-first импорта протоколов допроса (подозреваемый/обвиняемый) по эталонам Хошафян, Ромашевский, Погорелов, Финогенова.

**Ключевые изменения `smart_import_core.py`:**
- **`_extract_person_from_table_v5`**: переписан парсер таблицы личных данных. Теперь физические строки таблицы группируются в логические строки по номеру поля (`1.`, `2.` и т.д.), а многострочные названия полей и значения склеиваются корректно. Исправлены обрезанные адреса (`Ростовская|`, `и (или) регистрации`), место рождения (`Ростовской`) и занятие.
- **`_normalize_surname_case`**: новый метод нормализации фамилии с учётом пола по отчеству. Женские формы (`-ова`, `-ева`, `-ина`) сохраняются (Финогенова), мужские приводятся к именительному падежу.
- **`_extract_document_date`**: улучшено извлечение даты документа из шапки протокола — поддерживаются даты с разнесёнными по ячейкам числом, месяцем и годом (`17 ноября 2021`), с кавычками и без.
- **`_parse_interrogation_v5`**: для допросов теперь извлекаются статьи УК РФ из текста, формируются `qualifications`, `crime_type`, `motive`, `status`, `method`, `tools`, а также именованные `social_status`/`crime_status` лица на основе занятия и типа преступления.
- **`_articles_to_checkboxes`**: добавлен маппинг ст. 291.1 → `Посредничество во взяточничестве` + мотив `Корыстный`; для ст. 105 мотив по умолчанию `Бытовой`.

**Результаты на эталонах (LIGHT/RegEx):**
- ФИО, дата рождения, место рождения, адрес/регистрация, гражданство, занятие — извлекаются корректно.
- `social_status` и `crime_status` лица заполняются именованными словарями.
- `crime_type`, `motive`, `status`, `case_date` совпадают с эталоном (за исключением отсутствующих в документе полей).
- Остались расхождения только по полям, отсутствующим в самом протоколе допроса: `investigation_region/unit`, дата/время/регион преступления, национальность, травмы (требуют внешнего дела/СМЭ).

**Результаты на новых документах (LIGHT / FULL=LIGHT):**
| Документ | Статья | Статус |
|----------|--------|--------|
| Хошафян | ст.105 ч.3 п.в,д | ✅ persons, адрес, соц./крим. статус, crime_type, motive, status |
| Ромашевский | ст.105 | ✅ persons, адрес, статусы, crime_type, motive, method, tools |
| Погорелов | ст.105 | ✅ persons, адрес, статусы, crime_type, motive, method, tools |
| Финогенова | ст.291.1 | ✅ persons, адрес, статусы, crime_type, motive, status |

**Регрессии:** обвинительные/ВУД/прекращения не затронуты (изменения специфичны для `doc_type == "interrogation"` и `_extract_person_from_table_v5`).

**Замечание:** LLM-файлы (`ИИ.json`) не перегенерированы, т.к. в текущем окружении `llama-cpp-python` не загружается (`llama.dll` отсутствует). Код `_merge_llm_fallback` и `_extract_person_from_table_v5` получил те же исправления, что и RegEx-путь.

**Результаты верификации прекращений (LIGHT / FULL=LIGHT):**
| Документ | Фабула | Persons | Адреса | Примечание |
|----------|--------|---------|--------|------------|
| Аветисьянц | 2799 | 2 | 1 | Обвиняемый + жертва (Т.И.) ✅ |
| Владыкин | 5962 | 1 | 2 | Обрезана до 6000 символов |
| Рябов | 904 | 1 | 0 | Короткая фабула |

**Регрессии на обвинительных (обнаружены, не критичны):**
- Русских: `Козлова Е.В.` (возможно, родственница) добавляется как лишняя жертва.
- Пугачёва: `Жирнова Наталья` (вероятно, супруга потерпевшего) добавляется как лишняя жертва.
- Сулейманов: `Баранова И.М.` не извлекается (не находится `_extract_victims_v5`).

**Решение:** `_filter_false_victims` не ловит ложных жертв без явных маркеров родства в контексте. Доработка — в следующей итерации, если потребуется.

### Прокрутка колесом мыши в DayCalculatorView (исправлено ✅)
**Проблема:** После рефактора центральная колонка «Калькулятора дней» перестала прокручиваться колесом мыши. Вручную за скроллбар листалось, а колесо не работало.

**Причина:** Бинды `<MouseWheel>` на `DayCalculatorView`/`Canvas` не срабатывали, потому что `Frame`/`Canvas` не получают фокус по умолчанию, а событие колеса в Windows направляется виджету под курсором.

**Фикс в `src/views/day_calculator.py` (`_build_center_column`):**
- Используется стандартный для проекта паттерн Enter/Leave + `bind_all` / `unbind_all`:
  - `canvas.bind("<Enter>", ...)` — активирует `bind_all("<MouseWheel>", _on_mousewheel)`.
  - `canvas.bind("<Leave>", ...)` — отключает `bind_all("<MouseWheel>")`.
- Обработчик проверяет:
  - `container.winfo_ismapped()` — не скроллить, если вкладка скрыта.
  - Координаты курсора относительно `container` — прокрутка только над центральной колонкой.
- Направление: `canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")`.

### Custom Chrome / Window chrome (финальное решение ✅)
**Задача:** получить плавные анимации maximize/restore/resize, кастомный Cyber-Neon title bar и стабильную работу модальных окон, исключив фатальные ошибки GIL.

**История проблемы:**
- Ранние версии использовали `Win32CustomChrome` — WndProc subclassing через `SetWindowLongPtrW(GWLP_WNDPROC)` с удалением `WS_CAPTION`.
- Это приводило к `Fatal Python error: PyEval_RestoreThread`, когда Windows modal sizing loop (drag titlebar, Aero Snap, maximize/restore) реентерила Python-callback.
- Многочисленные попытки флагов `_in_transition`, `PostMessage`, временного снятия subclass'а и пр. снижали, но не устраняли риск полностью, особенно на разных версиях Windows/ttkbootstrap.

**Финальное решение (Windows 10/11):**
- **Системный chrome оставлен**: `WS_CAPTION` не удаляется. Вместо этого окно выглядит как современное тёмное приложение за счёт DWM.
- **DWM immersive dark mode** (`modern_widgets.py::_set_immersive_dark`):
  - `DWMWA_USE_IMMERSIVE_DARK_MODE = 20` (Windows 11) / `19` (Windows 10 fallback).
  - `DWMWA_CAPTION_COLOR` и `DWMWA_TEXT_COLOR` — тёмный фон заголовка + белый текст.
- **Внутренний CyberTitleBar** (`CyberTitleBar`, `TitlebarControl`):
  - Визуально закрывает системный titlebar в client-area.
  - Поддерживает drag окна, кастомные кнопки (− □ ×), иконку и заголовок.
  - Все `tk.Frame`/`tk.Label` в header'е и диалогах с кастомным `bg` обязательно имеют `autostyle=False`.
- **WindowTransitionStabilizer** (`modern_widgets.py`):
  - Отслеживает `<Configure>` корневого окна и состояние `normal ↔ zoomed`.
  - На 200 мс выключает `WM_SETREDRAW` в начале перехода и включает обратно по таймеру.
  - Пропускает переходы, когда зажата ЛКМ (drag titlebar), чтобы окно не «залипало».
  - Safety net: `<FocusIn>` / `<Map>` принудительно восстанавливают redraw.
- **Двойная буферизация** (`apply_custom_chrome`):
  - Добавляет `WS_CLIPCHILDREN` | `WS_CLIPSIBLINGS` в GWL_STYLE.
  - Добавляет `WS_EX_COMPOSITED` в GWL_EXSTYLE.
  - Цель — уменьшить мерцание и артефакты при ручном resize и maximize/restore.
- **Maximize/restore в главном окне** (`app_controller.py::_toggle_maximize`):
  - Используется `ShowWindow(hwnd, 3)` / `ShowWindow(hwnd, 9)`.
  - Никаких локальных обёрток `WM_SETREDRAW` — стабилизация централизована в `WindowTransitionStabilizer`.
- **Win32CustomChrome** (`modern_widgets.py`):
  - Оставлен как **no-op shell** с контекстным менеджером `suspended_for()` для обратной совместимости.
  - Весь WndProc subclassing и удаление `WS_CAPTION` удалены.
- **Модальное окно «Калькулятор срока следствия»** (`investigation_dialog.py`):
  - Использует **стандартный системный chrome** (`resizable(True, True)`), без subclassing HWND.
  - Внутри — визуальный `CyberTitleBar` и кастомные кнопки управления.
  - Эталон плавности maximize/restore/resize.

**HiddenNotebook / переключение вкладок (`modern_widgets.py`):**
- `HiddenNotebook` — кастомный `tk.Frame`, который показывает одну вкладку за раз через `pack()` / `pack_forget()`.
- После перехода на системный chrome + `WS_EX_COMPOSITED` + `WindowTransitionStabilizer` обнаружилась регрессия: при уменьшенном окне старая вкладка (например, «Происшествие») оставалась видимой поверх новой («Лица») до разворачивания окна.
- **Причина**: `WindowTransitionStabilizer` отключает `WM_SETREDRAW` на 200 мс при maximize/restore; при обычном resize / переключении вкладок redraw может оставаться отключённым, а `WS_EX_COMPOSITED` сохраняет старое содержимое буфера.
- **Фикс** в `HiddenNotebook.select`:
  - После `pack_forget()` старой вкладки и `pack()` новой вызывается `update_idletasks()`.
  - Новой вкладке даётся `lift()`, чтобы гарантированно быть поверх.
  - Принудительно включается `WM_SETREDRAW` (`_send_setredraw(hwnd, True)`), затем `InvalidateRect(hwnd, None, True)` + `UpdateWindow(hwnd)` — полная синхронная перерисовка окна.

**Известные ограничения:**
- `WindowTransitionStabilizer.on_configure()` сравнивает `str(event.widget) != str(self.root)` — важно сравнивать строки путей, а не объекты (widget path vs объект даёт ложное совпадение).

**Файлы:**
- `src/views/modern_widgets.py` — `apply_custom_chrome`, `WindowTransitionStabilizer`, `CyberTitleBar`, `Win32CustomChrome` (no-op), `HiddenNotebook`.
- `src/controllers/app_controller.py` — `_toggle_maximize`, `_sync_maximize_btn`, вызов `apply_custom_chrome`.
- `src/views/investigation_dialog.py` — модальное окно на системном chrome.

### Удаление дублей заголовков в модальных окнах (выполнено ✅)
**Проблема:** Во всех модальных окнах (кроме "Калькулятор срока следствия") title bar (`CyberTitleBar`) дублировался внутренним заголовком в body окна.

**Убрано:**
- `BaseEntityDialog._build_header` — удалён весь метод и вызов. Диалоги: Решение, Квалификация, Адрес, Документ, Транспорт, Идентификатор.
- `PersonEditorDialog._build_ui` — удалён `title_bar` frame с текстом `Лицо N - редактирование`.
- `PasswordDialog` (`constructor.py`) — удалён внутренний header. Иконка `🔒` перенесена в `title` → `CyberTitleBar` отображает `🔒 Доступ к Конструктору`.
- `PasswordDialog` (`dialogs.py`) — аналогично, `🔒` в title bar.
- `SmartImportDialog._build_header` — удалены дубли `📥 Умный импорт данных` + подзаголовок. Mode-панель (FULL/HYBRID/LIGHT) оставлена.
- `minesweeper.py CustomDialog` — удалён внутренний `⚙ Своя игра`. Иконка `⚙` перенесена в title bar.

### Единый стиль выпадающих списков в модальных окнах ✅
**Проблема:** В модальных окнах использовались `ModernCombobox` / `ttk.Combobox`, выпадающий список которых отображался старым серым системным стилем.

**Решение:** Все выпадающие списки в модальных окнах переведены на `CyberOptionMenu` (`modern_widgets.py`) — тот же виджет, что на вкладке «Происшествие».

**Файлы:**
- `src/views/person_editor_dialog.py` — статус, личность, местонахождение, физическое состояние, пол, расовый тип, национальность.
- `src/views/dialogs.py` (`BaseEntityDialog` и наследники) — `DecisionDialog`, `AddressDialog`, `DocumentDialog`, `TransportDialog`, `IdentifierDialog`.
- `src/views/smart_import_dialog.py` — переключатель режима «ИИ / Логический».

**Убрано:** устаревшие костыли стилизации `ttk.Combobox` dropdown (`_apply_combobox_styles`, `_finalize_combobox`, `_restyle_all_comboboxes`).

### CyberDatePicker — растяжение поля даты ✅
**Проблема:** Поля даты в секции «Дата и время совершения» (`crime_form.py`) отображались узким прямоугольником и не занимали доступную ширину колонки.

**Решение:** `CyberDatePicker` (`cyber_calendar.py`) теперь корректно растягивается:
- Внутренний `row` пакуется с `fill="x", expand=True`.
- Внутренний `Entry` пакуется с `fill="x", expand=True`.

### Preview / Предпросмотр (`preview_view.py`)
**Цель:** сделать правую панель предпросмотра удобной для быстрого копирования данных в сторонние веб-формы.

**Crime preview (происшествие):**
- ✅ Реорганизован в плоские header-блоки в порядке следования формы: Основные данные → Регион и орган расследования → Решения → Квалификация → Адреса → Вид происшествия → Дата и время совершения → Место совершения → Обстоятельства.
- ✅ Checkbox-группы (`status`, `crime_type`, `motive`, `method`, `tools` и др.) рендерятся как bullet-списки с подписью секции.
- ✅ Адреса: тип адреса выводится как обычная метка, убраны скобки `[ ]` и затемнённый цвет.
- ✅ Квалификация: `ст. {art}` выводится обычным текстом (`value`), убран золотой `qual`-тег.
- ✅ Базовый шрифт предпросмотра увеличен до `Segoe UI 12`.

**Person preview (лицо):**
- ✅ Верхние статус-поля (`Статус`, `Личность`, `Местонахождение`, `Физическое состояние`) — по одной строке каждое.
- ✅ Заголовок `Установочные данные лица:` + полная ФИО с датой рождения (био), затем отдельные поля (Фамилия, Имя, Отчество, Дата рождения, Пол и т.д.).
- ✅ Явные заголовки для списков в фиксированном порядке: **Адреса → Документы → Транспорт → Идентификаторы**.
- ✅ Checkbox-группы (`Социальный статус`, `Криминальный статус`, `Особые приметы`) перенесены в самый низ.
- ✅ Визуальные отступы между крупными блоками (после био, после прочих полей, между Адресами/Документами/Транспортом/Идентификаторами и перед чекбокс-группами).

**Smart-copy / копирование:**
- ✅ `value_copy` — специальный тег, при рендере заменяется на `_insert_copyable()`: текст подсвечивается при наведении и копируется одним кликом (или `Ctrl+C`).
- ✅ Копируемые поля: текстовые поля, даты, поля ввода (`text`/`entry`/`date`), адреса, серия/номер/дата выдачи/кем выдан документов, **а также Марка / Модель / Госномер транспорта**.
- ✅ `combobox` и `checkbox_group` значения намеренно **не** копируются одним кликом — пользователь должен перебирать их вручную в целевой веб-форме.
- ✅ Исправлено контекстное меню «Копировать» в `tk.Text` с `state="disabled"`: вместо `event_generate("<<Copy>>")` используется прямой вызов `_copy_selection_impl()`.
- ✅ `_set_text()` сбрасывает stale-выделение (`tag_remove("sel", "1.0", "end")`) при обновлении preview.
- ✅ Smart-copy hover очищает чужое ручное выделение, даже если виджет disabled.
- ✅ **Позиция прокрутки сохраняется при перестроении (2026-07-20):** раньше `_set_text()` заканчивался `see("1.0")` — при любом изменении данных в форме слева предпросмотр прыгал в начало. Теперь перед перестроением запоминается первая видимая строка (`index("@0,0")`) и восстанавливается через `yview(f"{line}.0")`; если контент стал короче позиции — кламп к `end_line`, если пользователь был в начале — остаётся в начале. Работает и для `value_copy` сегментов. Тесты: `tests/test_preview_scroll.py` (4 шт.).

**Исправление обрезания текста после сохранения лица (Windows + WS_EX_COMPOSITED):**
- ✅ **Проблема:** при сохранении/редактировании лица текст в правой панели PreviewView обрезался в обычном окне; разворачивание окна или переключение вкладок исправляло отображение.
- ✅ **Причина:** `_sync_and_refresh()` вызывал `preview.rebuild_person_tabs()` на каждое сохранение, уничтожая и создавая `tk.Text` заново. На Windows с включённым `WS_EX_COMPOSITED` нативный paint/display cache не инвалидировался, и `tk.Text` рисовал строки по старой более узкой ширине, хотя `winfo_width()` показывал 598–615 px.
- ✅ **Решение:**
  - `AppController._sync_and_refresh()` больше не вызывает `preview.rebuild_person_tabs()` вручную; вкладки пересоздаются только в `PreviewView.update_preview()`, когда реально меняется количество лиц.
  - Preview обновляется сразу (`_refresh_preview()`), без 300 мс debounce.
  - В `PreviewView` добавлен `_force_native_repaint()`: после `update_preview()` вызывается Win32 `InvalidateRect` + `UpdateWindow` для HWND видимых `tk.Text` и корневого окна, принудительно обновляя composited backbuffer.
  - Для защиты от подвисания на старте repaint пропускается, пока корневое окно не `winfo_viewable()`.

### История работы с LLM (Claude, GPT, Qwen)
**Этап 1 — Первоначальная разработка smart_import_core.py:**
- **Claude/GPT** — архитектура гибридного парсера (RegEx + Natasha + LLM fallback).
- **Claude** — реализация `_parse_accusation_v5`, структура extractors, маппинг статей УК на чекбоксы.
- **GPT** — улучшение `_extract_investigation_unit`, fuzzy-match к справочнику, `_normalize_unit_case`.

**Этап 2 — Улучшение RegEx-first (Stage 1.5):**
- **Qwen 2.5 3B (GPU)** — генерация тестовых эталонов и LLM fallback в умном импорте. Результаты использовались как baseline для сравнения с RegEx.
- **Claude** — анализ diff между ИИ и RegEx (4 файла: Юркевич, Толмачев, ЦВЫК, Маринина). Выявлены паттерны для `_REPLACEMENTS` (конвертер 1→3).
- **GPT** — идея нормализации фамилий для `perpetrators_count` (отбрасывание падежных окончаний `-а`, `-у`, `-ым`).

**Этап 3 — Багфикс и доводка (текущий чат):**
- **Kimi** — исправление `_on_import_result` (мерж `crime_region`/`crime_type`), улучшение `_extract_addresses_v5`, `_extract_victims_v5`, `_extract_omp_protocol`, `_normalize_address`.
- **Kimi** — создание `test_real_docs_v4.py`, fuzzy-match логики сравнения.

**Ключевые инсайты от LLM:**
- Claude предложил `fixed-point` расчёт для калькулятора сроков давности (учёт периодов розыска).
- GPT предложил `global_basis` (глобальный combobox основания приостановления) в `statute_calculator.py`.
- Qwen сгенерировал структуру `uk_upk_database.json` (558 статей УПК РФ) по запросу "создай JSON УПК РФ".

### Проблемы, с которыми столкнулись (и решения)
1. **ttkbootstrap `autostyle` перезаписывает `bg`** у `tk.Frame`/`tk.Label`/`tk.Text` → решение: `autostyle=False` везде, где кастомный `bg`.
2. **`ttk.Panedwindow` sash 1px** — невозможно захватить мышкой → решение: `tk.PanedWindow(sashwidth=8)`.
3. **`ModernCollapsibleSection` canvas-анимация** — конфликт `winfo_reqheight` и `bbox("all")` → решение: удалить анимацию, мгновенный `pack`/`pack_forget`.
4. **`PlaceholderEntry` configure(textvariable)** — в Tcl/Tk `configure -textvariable ""` привязывает к глобальной переменной `""`, ломая ввод → решение: внутренняя `_internal_var` + trace, никакого переключения `textvariable`.
5. **`smart_import_core.py` разорванные строки в regex** — при редактировании через `StrReplaceFile` строки с `
` разрывались на две физические строки → решение: всегда проверять `python -m py_compile` после правки regex.
6. **`_normalize_address` и ` `** — docx содержит неразрывные пробелы, которые не схлопываются `replace("  ", " ")` → решение: явная замена ` ` → `" "`.
7. **`(?i)` + `[А-ЯЁ]`** в regex ловит строчные буквы → решение: убрать `(?i)` из агрессивных cleanup-регулярок или использовать `[А-ЯЁа-яё]`.
8. **Greedy regex в `_extract_sme_conclusion`** — `([\s\S]*?)` перепрыгивал через границы заключений, возвращая кровяную экспертизу вместо СМЭ. → решение: lookahead-терминатор `(?=\n\s*(?:\(том №|Заключение эксперта №|Протокол|...))`.
9. **Capturing group в `_extract_traces_research`** — `re.finditer` с capturing group вызывал `IndexError: no such group` при обращении к `m.group(1)`. → решение: использовать `m.group(0)`.
10. **Scope переменных `_primary_art` и `articles` в `_parse_accusation_v5`** — после рефакторинга остались обращения к переменным до их инициализации или со старыми именами. → решение: вынести `_primary_art` в начало функции, переименовать `articles` → `articles_meta`.
11. **WndProc subclassing → fatal GIL fault** — `Win32CustomChrome` через `SetWindowLongPtrW(GWLP_WNDPROC)` с удалением `WS_CAPTION` вызывал `Fatal Python error: PyEval_RestoreThread`, когда Windows modal sizing loop (drag titlebar, Aero Snap, maximize/restore, filedialog) реентерила Python-callback. `tk_getOpenFile` также deadlock'ил на `SendMessage(WM_ACTIVATE)` к subclassed owner. → решение: полный отказ от WndProc subclassing. Системный chrome оставлен, используется DWM immersive dark mode + `DWMWA_CAPTION_COLOR`/`DWMWA_TEXT_COLOR` для тёмного titlebar. `Win32CustomChrome` сохранён как no-op shell с `suspended_for()` для обратной совместимости.
12. **Maximize/restore артефакты главного окна** — после перехода на системный chrome оставался кратковременный артефакт перерисовки при maximize/restore. → решение: `WindowTransitionStabilizer` отключает `WM_SETREDRAW` на 200 мс при переходе `normal ↔ zoomed`, игнорируя drag ЛКМ; `WS_EX_COMPOSITED` + `WS_CLIPCHILDREN`/`WS_CLIPSIBLINGS` для двойной буферизации. Небольшой остаточный артефакт остаётся и считается допустимым.
13. **Обрезание текста в PreviewView после сохранения лица** — `_sync_and_refresh()` пересоздавал `tk.Text` вкладок предпросмотра при каждом сохранении, а на Windows с `WS_EX_COMPOSITED` composited backbuffer не инвалидировался, поэтому строки отображались по старой узкой ширине. → решение: не пересоздавать вкладки без необходимости; явный Win32 `InvalidateRect` + `UpdateWindow` для виджетов preview и корневого окна; пропускать repaint, пока окно не видимо.

### Общие
- [ ] Унификация диалога "ИИ недоступен" (сейчас дублируется в 2 местах)
- [ ] Улучшение `_extract_interrogation_text` для экзотических форм протоколов
- [ ] Тестирование LLM-режима (FULL/HYBRID) после стабилизации RegEx-first

### Установщики / оформление (завершено, 2026-07-10)
- [x] Принять решение по формату верхнего баннера Inno Setup: выбран квадратный `wizard_small_164.png` 164×164.
- [x] Подготовить PNG-версии ассетов v2 с точными целевыми размерами.
- [x] Очистить тексты v2 от служебных markdown-заголовков и применить правки автора/аудитории.
- [x] Интегрировать финальные ассеты v2 в `installer_assets/win10_11/` и `installer_assets/win7/`.
- [x] Обновить `setup.iss` / `setup.nsi` под новые имена/размеры файлов.
- [x] Пересобрать `dist_installer/MANGUST_v4_Win10_11_Setup.exe` и `dist_installer/MANGUST_v4_Win7_Setup.exe`.
- [ ] Визуально проверить страницы приветствия, лицензии, компонентов и завершения в обоих установщиках.

### PanedWindow / Предпросмотр (`app_controller.py`)
- ✅ **ttk.Panedwindow → tk.PanedWindow**: `ttk.Panedwindow` имел sash шириной 1px, который было нереально захватить мышкой. Заменён на `tk.PanedWindow(..., sashwidth=8, sashrelief="flat", bg=BG_APP_DARK, bd=0)`.
- ✅ **Распределение по умолчанию из `config/ui_settings.json`**: ключ `preview_split_ratio` (доля левой панели), по умолчанию `0.72`. Значение редактируется в Конструкторе на вкладке **«Настройки ширины предпросмотра»**.
- ✅ **Приоритет ручного sash**: если пользователь двигал sash мышкой, позиция сохраняется в `_main_sash_pos`, флаг `_sash_moved_manually = True`, и при пересборке UI восстанавливается именно она.
- ✅ **Применение нового ratio**: когда в Конструкторе нажимается «Сохранить настройки ширины предпросмотра», в `ui_settings.json` устанавливается `preview_split_ratio_changed = True`. При следующем «Применить и перезагрузить формы» `AppController._apply_schema_changes()` видит флаг, сбрасывает `_sash_moved_manually` и `_main_sash_pos`, очищает флаг из файла и применяет новое `preview_split_ratio`.
- ✅ **Возврат предпросмотра**: при переключении с вкладок без предпросмотра (Калькулятор, Конструктор, Справочник) обратно на форму, `self._main_paned.add(self._right_panel, width=400, stretch="always")` восстанавливает ширину.

### Калькулятор сроков давности (выполнено)
- ✅ Глобальный combobox + per-row чекбоксы
- ✅ `global_basis` в сервисе
- ✅ Post-1997 / pre-1997 логика розыска
- ✅ Кнопка очистки статьи
- ✅ `CyberDatePicker` / `CyberCalendarPopup` (`cyber_calendar.py`) — единый кастомный виджет выбора даты (стиль Cyber-Neon) во всех вкладках: `crime_form.py`, `statute_calculator.py`, `investigation_dialog.py`. Фокус возвращается на поле ввода автоматически.
- ✅ Компактный layout полей даты в `statute_calculator.py` — без растягивания на всю ширину (`pack(anchor="w")`).
- ✅ `<Return>` в полях даты триггерит `_on_calculate()`.

---

## 8. Ключевые файлы для редактирования

| Файл | Строк | Назначение | Частота изменений |
|------|-------|-----------|-------------------|
| `src/views/first_to_third_converter.py` | ~2700 | Конвертер 1→3 лицо | **ВЫСОКАЯ** |
| `src/controllers/app_controller.py` | ~2520 | Главный контроллер + custom chrome header | Средняя |
| `src/views/modern_widgets.py` | ~5560 | Дизайн-система: PlaceholderEntry/PlaceholderText, custom chrome helpers (WindowTransitionStabilizer, CyberTitleBar, TitlebarControl, HeaderSeparator, no-op Win32CustomChrome), ValidationErrorDialog | **ВЫСОКАЯ** |
| `src/views/crime_form.py` | ~3440 | Форма преступления | Низкая |
| `src/views/person_editor_dialog.py` | ~830 | Редактор лиц (модальное окно) | Средняя |
| `src/views/statute_calculator.py` | ~1500 | Калькулятор сроков давности УК РФ | Средняя |
| `src/views/statute_reference_view.py` | ~1080 | Справочник УК/УПК РФ | Средняя |
| `src/services/statute_repository.py` | ~220 | Репозиторий справочника УК/УПК | Низкая |
| `src/services/security_manager.py` | ~340 | PBKDF2-пароль приложения + автоблокировка | Низкая |
| `src/services/config_store.py` | ~130 | Overlay конфигов (LOCALAPPDATA при read-only Program Files) | Низкая |
| `src/views/app_password_dialog.py` | ~500 | Диалоги пароля: вход, разблокировка, настройка | Низкая |
| `src/views/smart_import_dialog.py` | ~800 | Умный импорт | Средняя |
| `src/views/dialogs.py` | ~1160 | Диалоги (Address, Decision, Document, Password и т.д.) | Средняя |
| `src/views/dynamic_form.py` | ~860 | Модальные списки (`StructuredListWidget`, `MediaListWidget`) и `CollapsibleSection` | Средняя |
| `src/views/person_form.py` | ~680 | Форма лица (список карточек) | Низкая |
| `config/schema_crime.json` | — | Схема преступления | Редкая |
| `config/schema_person.json` | — | Схема лица | Редкая |
| `config/uk_upk_database.json` | — | База статей УК/УПК РФ | Редкая |
| `fix_structure.py` | — | Перестроение структуры УК РФ (вспомогательный) | Редкая |
| `fix_upk_structure.py` | — | Перестроение структуры УПК РФ (вспомогательный) | Редкая |

---

## 9. Инструкции по запуску

```batch
:: 1. Перейти в папку проекта
cd "mangust_v4"

:: 2. Запустить через venv_new (ОБЯЗАТЕЛЬНО через run.bat, не через Git Bash!)
run.bat

:: 3. Для разработки — установка зависимостей в venv_new:
venv_new\Scripts\python.exe -m pip install -r requirements-llm.txt
```

### Важно про LLM
- Модели кладутся в `config/models/`
- Основная модель (3B, ~2 GB): `qwen2.5-3b-instruct-q5_k_m.gguf`
- Расширенная модель (14B, ~8 GB): `Qwen2.5-14B-Instruct-Q4_K_M.gguf`
- ИИ-режим доступен при наличии модели 3B+
- CUDA: LM Studio backend path прописан в `main.py` (`_lmstudio_cuda`)

---

## 10. Тестирование и обучающие материалы

- **Тестовые тексты конвертера**: `Для обучения/Конвертер/`
- **Эталонные JSON**: `Эталонные файлы/`
- **Golden files**: `tests/golden_files/`

### Автотесты
- `tests/test_migration.py` — миграция JSON-проектов между версиями.
- `tests/test_constructor.py` — CRUD Конструктора:
  - Редактор справочников: добавление / переименование / удаление значений `lists.json` + перезагрузка через `SchemaLoader`.
  - Редактор опций чекбоксов: добавление / обновление / удаление опций в схеме.
  - Добавление поля типа `combobox` в схему, сохранение и перезагрузка.
  - Автосоздание `list_key` и справочника для поля `combobox` без ручного ввода ключа.
  - Сохранение `preview_split_ratio` через вкладку «Настройки ширины предпросмотра».
- `tests/test_checkbox_web_value.py` — формат хранения checkbox-полей (`web_value`), миграция старых форматов, roundtrip JSON.
- `tests/test_person_editor_dialog.py` — UI-диалог редактирования лица (превью фото, чекбоксы).
- `tests/test_validation_controller.py` — валидация обязательных полей происшествия и лиц.
- `tests/test_display_labels.py` — отображение `label` вместо служебного кода `{web_value: label}` в UI.

Запуск:
```batch
venv_new\Scripts\python.exe -m pytest tests/ -v
```

### Результаты сравнения 7B vs RegEx (4 файла)
| Файл | Пол | ИИ лучше? | Остатки ИИ |
|------|-----|-----------|------------|
| Юркевич | муж. | Да (исправил согласование) | "мной", "наша", "нас" |
| Толмачев | муж. | Значительно (исправил опечатки) | "мной" |
| ЦВЫК | жен. | Категорически (8+ ошибок RegEx) | Нет |
| Маринина | жен. | Категорически (все опечатки) | "проходит" вместо "просит" |

---

## 11. Соглашения по коду

- **Язык**: весь UI на русском, код на английском
- **Типизация**: `from __future__ import annotations` + type hints
- **Логирование**: `logging.getLogger(__name__)`
- **Цвета**: импортировать из `modern_widgets.py`, не хардкодить
- **tk.Text readonly**: `state="disabled"`, для редактирования временно `state="normal"`
- **РегEx**: в `_REPLACEMENTS` порядок важен — сначала составные выражения, потом простые
- **LLM prompt**: few-shot примеры для конкретного пола, temperature=0.3, top_p=0.9
- **PlaceholderEntry**: при пустом поле внешняя `textvariable` остаётся `""` (placeholder не попадает в неё). Entry всегда привязана к внутренней `_internal_var`. **Никогда** не переключать `configure(textvariable=...)` в рантайме — это ломает привязку в Tcl/Tk. Синхронизация с внешней переменной только через trace.
- **ModernCombobox**: не добавлять `_force_dark_bg`, `after_idle`/`after(100)` перерисовку — это ломает стрелку dropdown на Windows. Финализировать через `after(60, ...)` или сразу после `grid()`.
- **CyberOptionMenu**: использовать в модальных окнах вместо `ttk.Combobox` / `ModernCombobox` для единого визуального стиля с основной формой. API: `variable`, `values`, `command`. Не поддерживает `state="readonly"` и `<<ComboboxSelected>>` — callback передаётся через `command`, а текущее значение читается из привязанной `StringVar`.
- **CyberDatePicker**: внутренний `row` и `Entry` должны паковаться с `fill="x", expand=True`, чтобы поле растягивалось по ширине колонки.
- **ttkbootstrap autostyle**: `tk.Frame(..., bg=BG_INPUT)` без `autostyle=False` будет перезаписан в `BG_PANEL`. **Всегда** передавать `autostyle=False` при кастомном `bg`/`fg` у `tk.Frame`, `tk.Label`, `tk.Text`.
- **Text selection**: `tag_raise("sel")` необходим, если другие теги (например, `note_box`) имеют `background`, иначе выделение будет невидимым.
- **Combobox mouse wheel**: глобально отключена прокрутка `<MouseWheel>` / `<Button-4>` / `<Button-5>` для класса `TCombobox` (`bind_class` в `app_controller.py`). Значение выбирается только из выпадающего списка; колесо над Combobox не прокручивает страницу и не меняет выбор.
- **Canvas mouse wheel (scrollable области)**: стандартный паттерн — `canvas.bind("<Enter>", lambda _: canvas.bind_all("<MouseWheel>", handler))` / `canvas.bind("<Leave>", lambda _: canvas.unbind_all("<MouseWheel>"))`. Это совместимо с несколькими scrollable-областями в одном окне и не требует глобального `bind_all` постоянно.
- **HiddenNotebook tab switching**: после `pack_forget()` / `pack()` обязательно вызвать `update_idletasks()`, `lift()` для новой вкладки и принудительную перерисовку окна (`_send_setredraw(hwnd, True)` + `InvalidateRect` + `UpdateWindow`), иначе при системном chrome + `WS_EX_COMPOSITED` старая вкладка может «просвечивать» поверх новой.
- **Выбор игры (вкладка «Отдых»)**: реализовано кнопками-переключателями (`tk.Radiobutton` с `indicatoron=False`) вместо `Combobox`, как переключатель режима в конвертере (`Режим:`).
- **CyberDatePicker focus**: всплывающий `CyberCalendarPopup` автоматически возвращает фокус в `owner` (внутренний `Entry`) после выбора даты или при закрытии. Дополнительный `focus_target` не требуется.
- **PanedWindow split ratio**: ширина левой панели по умолчанию задаётся `config/ui_settings.json` → `preview_split_ratio`. Ручное положение sash запоминается в `_main_sash_pos` с флагом `_sash_moved_manually`. Чтобы новое ratio применилось после изменения в Конструкторе, используется флаг `preview_split_ratio_changed=True` в `ui_settings.json`; `AppController._apply_schema_changes()` потребляет флаг, сбрасывает ручное положение и применяет ratio.
- **Preview spacing**: в `preview_view.py` отступы между крупными секциями добавляются через `("\n", "")` только при непустом блоке. Порядок секций лица: статус-блок → `Установочные данные лица` → Адреса → Документы → Транспорт → Идентификаторы → checkbox-группы.
- **Статус `suspended_manhunt` (post-1997)**: `final_end_date` явно `None`, `remaining_days = None`. UI (таймлайн) должен отображать **∞ / розыск** и не пытаться рассчитать ratio для `final_end_date_str`.
- **Pre-1997 розыск**: для ВСЕХ преступлений до 01.01.1997 с п.2 ст. 208 УПК РФ проверяется 15-летний предел по ст. 48 УК РСФСР (`elapsed_days > 15*365`). `RSFSR_CUTOFF_DATE` не используется для разделения логики expired/suspended.
- **Checkbox group data format**: в JSON `Dict[str, int]` `{label: 1}` — только выбранные, НЕ `List[int]`. Ключ — точный `label` из схемы (`option.get("label")`), значение — `1`. `crime_place` хранится как `Dict[str, Dict[str, int]]` — `{категория: {label: 1}}`. Внутри программы нули тоже допустимы (`{label: 0/1}`), но при сохранении фильтруются. Старые сохранённые проекты автоматически мигрируются при загрузке.
- **UK RF structure exact mapping**:
  - Общая часть: Разделы I–VI, Главы 1–15.2 (ст. 1-104.5)
  - Особенная часть: Разделы VII–XII, Главы 16–34 (ст. 105-361)
- **UPK RF structure exact mapping**:
  - Часть первая (ст. 1-139): Разделы I–VI, Главы 1–18
  - Часть вторая (ст. 140-226.9): Разделы VII–VIII, Главы 19–32.1
  - Часть третья (ст. 227-419): Разделы IX–XV, Главы 33–49
  - Часть четвертая (ст. 420-452): Разделы XVI–XVII, Главы 50–52
  - Часть пятая (ст. 453-473.7): Раздел XVIII, Главы 53–55.1
  - Часть шестая (ст. 474-476): Раздел XIX, Главы 56–57

---

*Последнее обновление: 2026-07-13 (переименование вкладки «Настройки ширины предпросмотра»; флаг `preview_split_ratio_changed` для применения нового split-ratio после «Применить и перезагрузить формы»; CyberOptionMenu в модальных окнах; растяжение CyberDatePicker; восстановление PanedWindow split; автосоздание справочника для combobox-полей; обязательная валидация с UX-подсветкой ошибок; отображение `label` вместо `{web_value: label}` в UI)*

---

## 12. Временный приказ № 90 (СУ СК России по Ростовской области)

> ⚠️ Этот приказ добавлен **временно** для локальной апробации в СУ СК России по Ростовской области. Перед глобальным релизом его необходимо удалить.

### Файл
`mangust_v4\Приказ\Приказ № 90 от 28.10.2025 Мангуст СУ СК РФ по РО.pdf`

### UI
Вкладка **Инструкции** (`src/controllers/app_controller.py`, метод `_build_instruction_tab`). Второй приказ добавлен через повторно используемый вложенный класс `_OrderDownloadPanel`:

```python
self._order90_panel = self._OrderDownloadPanel(
    self,
    frame,
    title="Приказ СУ СК России по Ростовской области от 28.10.2025 № 90",
    subtitle='«О централизованном криминалистическом учете преступлений в СУ СК России по Ростовской области»',
    source=self.app_root / "Приказ" / "Приказ № 90 от 28.10.2025 Мангуст СУ СК РФ по РО.pdf",
    default_name="Приказ № 90 от 28.10.2025 Мангуст СУ СК РФ по РО.pdf",
)
```

### Порядок удаления перед релизом
1. Удалить PDF-файл из папки:
   `mangust_v4\Приказ\Приказ № 90 от 28.10.2025 Мангуст СУ СК РФ по РО.pdf`
2. В `src/controllers/app_controller.py` в методе `_build_instruction_tab` удалить (или закомментировать) блок `self._order90_panel = self._OrderDownloadPanel(...)` — строки с `title`, `subtitle`, `source`, `default_name` для приказа № 90.
3. Если после удаления остаётся только приказ № 96, вложенный класс `_OrderDownloadPanel` можно оставить — он используется для единственной панели № 96.
4. Проверить: `python -m py_compile src/controllers/app_controller.py` и запустить приложение — на вкладке «Инструкции» должен остаться только приказ СК России № 96.

**Примечание для следующего чата:**
- В `ModernCollapsibleSection` (`modern_widgets.py`) **анимация expand/collapse полностью удалена**. Используется мгновенный `pack`/`pack_forget`. Не пытаться восстановить `_body_canvas` / `_animate_body` — подход Claude/GPT не работает из-за фундаментального конфликта `winfo_reqheight` и `bbox("all")`.
- В `person_form.py` карточки лиц используют **двухслойную рамку** (`outer` bg=BORDER_DEFAULT + `inner` bg=BG_PANEL с `padx=1, pady=1`) вместо `highlightthickness`. Все виджеты внутри карточки имеют `autostyle=False`.
- В `app_controller.py` PanedWindow — это **`tk.PanedWindow`** (не `ttk.Panedwindow`), с `sashwidth=8` для удобного захвата и начальной шириной предпросмотра `width=400`.
- `PreviewView` (`preview_view.py`) — обычный `tk.Frame`, без `pack_propagate(False)` / фиксированной ширины. В `_render_entity` (превью лица) используется фиксированный порядок списков: `addresses` → `documents` → `transport` → `identifiers` с явными заголовками, отступами между блоками и copyable-полями для транспорта (`plate`, `brand`, `model`). Checkbox-группы рендерятся в самом низу через `_bullet_list`.
- `PlaceholderEntry` (`modern_widgets.py`) — переписан с нуля: внутренняя `_internal_var` + trace-синхронизация, никакого `configure(textvariable=...)` в рантайме.
- **PanedWindow split ratio**: ширина левой панели по умолчанию берётся из `config/ui_settings.json` → `preview_split_ratio`. Ручное положение sash приоритетно, пока не изменено в Конструкторе: при сохранении на вкладке «Настройки ширины предпросмотра» в файле появляется `preview_split_ratio_changed=True`; `AppController._apply_schema_changes()` потребляет флаг, сбрасывает `_sash_moved_manually`/`_main_sash_pos` и применяет новое ratio.
- **Termination docs (`_parse_termination_v5`)**: FULL-режим работает как LIGHT (LLM fallback отключён через `_get_llm_fallback_fields`). Фабула обрезается стоп-словами (`\nДОПРОШЕННЫЙ`, `\nСВИДЕТЕЛЬ`) + жёсткий лимит 6000 символов. `_filter_false_victims` фильтрует deceased relatives, children < 12 и parents, но защищён victim-markers (`убита`, `насильственной смерти`).
- **Custom chrome / titlebar** (`modern_widgets.py`, `app_controller.py`, `investigation_dialog.py`): используется системный chrome с DWM immersive dark mode; `WS_CAPTION` **не удаляется**. Внутри окна — визуальный `CyberTitleBar`. `WindowTransitionStabilizer` отключает `WM_SETREDRAW` на 200 мс при maximize/restore. `Win32CustomChrome` оставлен как no-op shell с `suspended_for()` для обратной совместимости; WndProc subclassing удалён. Модальное окно «Калькулятор срока следствия» (`investigation_dialog.py`) — стандартный resizable системный chrome, без subclassing HWND.
- **Модальные окна**: внутренние дублирующие заголовки (`_build_header` в `BaseEntityDialog`, `title_bar` в `PersonEditorDialog`, `header` в `PasswordDialog`/`SmartImportDialog`/`minesweeper.py`) удалены. Иконки (`🔒`, `📥`, `⚙`) перенесены в `CyberTitleBar` (title bar). `BaseEntityDialog` и `PasswordDialog` больше не создают внутренний header frame.
- **`TitlebarControl`** — Canvas-based кнопки управления окном (− □ ×) со скруглённым hover-bg. **`HeaderSeparator`** — двухслойный разделитель header/body (faint cyan + shadow).
- **`main.py`** — Unicode-символы `✓`/`✗` заменены на `OK`/`FAIL` для совместимости с `cp1251` консолью Windows.
- **`pymorphy3`** используется в `_normalize_name_case` и `_expand_initials` (замена `pymorphy2`).
- **`DayCalculatorView`** (`src/views/day_calculator.py`): прокрутка центральной колонки колесом мыши реализована через паттерн `Enter/Leave + bind_all/unbind_all`. Никаких постоянных глобальных биндов `<MouseWheel>`.
- **`HiddenNotebook.select`** (`src/views/modern_widgets.py`): при переключении вкладок после `pack_forget()`/`pack()` вызывается `update_idletasks()`, `lift()` новой вкладки и принудительная Win32-перерисовка окна (`_send_setredraw` + `InvalidateRect` + `UpdateWindow`). Это обязательно, т.к. системный chrome + `WS_EX_COMPOSITED` + `WindowTransitionStabilizer` без этой меры оставляют старую вкладку видимой поверх новой при уменьшенном окне.
- **Выпадающие списки в модальных окнах**: заменены на `CyberOptionMenu` (`modern_widgets.py`). Не возвращать `ttk.Combobox` / `ModernCombobox` в `PersonEditorDialog`, `BaseEntityDialog` и `SmartImportDialog`.
- **PanedWindow split restoration** (`app_controller.py`): после пересборки UI (например, из Конструктора) флаг `_split_restored` должен сбрасываться, иначе `_restore_main_split` не отработает и предпросмотр займёт неправильную долю экрана. `_main_sash_pos` не сбрасывать. Начальное соотношение (до ручного движения sash) берётся из `config/ui_settings.json` (`preview_split_ratio`), по умолчанию 0.72. Ручное положение sash запоминается через `_sash_moved_manually` и имеет приоритет; если пользователь изменит ratio в Конструкторе и нажмёт «Сохранить настройки ширины предпросмотра», в `ui_settings.json` устанавливается флаг `preview_split_ratio_changed=True`, а при «Применить и перезагрузить формы» AppController сбрасывает `_sash_moved_manually`, удаляет флаг и применяет новое ratio.
- **Конструктор (`constructor.py`)**:
  - Поле типа `combobox` автоматически получает `list_key = {field_name}_values` при сохранении, если ключ не введён вручную. Справочник сразу создаётся в `lists.json`, а label поля отображается в «Редакторе Справочников». При загрузке с диска `LISTS_LABELS` синхронизируется с combobox-полями схем.
  - Вкладка **Настройки ширины предпросмотра** позволяет задать `preview_split_ratio` (доля левой панели по умолчанию, 50–90%). Значение сохраняется в `config/ui_settings.json` вместе с флагом `preview_split_ratio_changed=True`; при «Применить и перезагрузить формы» флаг сбрасывается и новое ratio применяется даже если ранее sash двигали вручную.
- **`CyberDatePicker`** (`src/views/cyber_calendar.py`): поле даты растягивается по ширине контейнера — внутренний `row` и `Entry` пакуются с `fill="x", expand=True`.
- **`CrimeFormView` / `PersonFormView`**: корневые `tk.Frame` получили `autostyle=False`, чтобы `ttkbootstrap` не перезаписывал их фон при переключении/ресайзе.


---

## 13. Оптимизации производительности / отрисовки (2026-06-16)

После анализа Claude и GPT внедрены точечные оптимизации для устранения лагов PanedWindow, медленного раскрытия секций, рывков maximize/restore и артефактов в Сапёре.

### 13.1 Общий подход
- В `src/views/modern_widgets.py` добавлены:
  - `_Debouncer` — простой debounce через `widget.after()`.
  - `_mark_toplevel_resizing(toplevel, duration_ms)` — глобальный флаг `_mangust_in_resize`, который выставляется на время drag sash / WM_SIZE. Тяжёлые виджеты проверяют его и откладывают перерисовку.

### 13.2 Лаг ползунка PanedWindow (`src/controllers/app_controller.py`)
- `center_paned` создан с `opaqueresize=False` — теперь размеры pane пересчитываются по отпусканию sash, а не на каждый пиксель.
- Добавлены бинды `<ButtonPress-1>` / `<ButtonRelease-1>` на sash: во время drag выставляется `_mangust_in_resize = True`.
- `_restore_main_split` вызывается один раз (`after_idle`), а не три. Добавлен флаг `_split_restored`, предотвращающий повторные вызовы `sashpos()`.
- **FIX (2026-06-26)**: `_build_ui()` сбрасывает `_split_restored = False` и `_split_restore_attempts = 0`, но **не сбрасывает** `_main_sash_pos`. Это позволяет корректно восстановить положение sash после "Применить и перезагрузить формы" в Конструкторе, вместо того чтобы оставлять PanedWindow в дефолтном/случайном распределении.

### 13.3 Медленное раскрытие секций с чекбоксами (`src/views/modern_widgets.py`, `src/views/crime_form.py`)
- В `ModernCheckbutton.__init__` убран `bind("<Configure>", ...)`. Чекбокс фиксированного размера 16×16; лавина Configure при раскрытии секции с 80+ чекбоксами больше не триггерит `canvas.delete("all")` для каждого.
- В `ModernCollapsibleSection._expand` добавлены `update_idletasks()` до и после `pack(body)`, чтобы Tk обработал layout одним пакетом.
- **Lazy builder:** `ModernCollapsibleSection` получила `set_lazy_builder()` / `ensure_built()`. Тяжёлый контент (чекбоксы) создаётся только при первом раскрытии; до этого секция хранит пустой `body`. Сборка выполняется с заморозкой перерисовки окна (`WM_SETREDRAW`), чтобы избежать лавины перерисовок.
- В `crime_form.py` ленивость применена к `_build_checkbox_accordion` и `_build_crime_region`: виджеты не создаются при старте приложения, а только при первом expand или при `set_data()` с ненулевыми сохранёнными значениями.

### 13.4 Рывки maximize/restore (`src/views/modern_widgets.py`, `src/controllers/app_controller.py`)
- Отказ от WndProc subclassing и удаления `WS_CAPTION` — устраняет реентерабельный GIL-fault `PyEval_RestoreThread`.
- Используется системный chrome + DWM immersive dark mode + `DWMWA_CAPTION_COLOR`/`DWMWA_TEXT_COLOR` для тёмного titlebar.
- `WindowTransitionStabilizer` на 200 мс отключает `WM_SETREDRAW` при переходах `normal ↔ zoomed` (maximize/restore), исключая перерисовку виджетов во время DWM-анимации.
- Переходы во время drag titlebar (ЛКМ зажата) игнорируются, чтобы окно не «залипало» mid-drag.
- `WS_EX_COMPOSITED` + `WS_CLIPCHILDREN`/`WS_CLIPSIBLINGS` включены для двойной буферизации.
- `_toggle_maximize` в `app_controller.py` использует только `ShowWindow(hwnd, 3/9)`; локальные `WM_SETREDRAW` убраны.

### 13.5 CrimeForm canvas (`src/views/crime_form.py`)
- `_on_canvas_configure` переведён на debounce: ширина canvas-window меняется через `after(40ms)` в обычном режиме и `after(120ms)` во время `_mangust_in_resize`. Это снижает нагрузку при drag sash.

### 13.6 Сапёр — артефакты при смене сложности (`src/views/minesweeper.py`)
- `BGCanvas` получил методы `suspend()` / `resume()` и debounce в `_on_configure`:
  - Rebuild фона откладывается на 150–250 мс после последнего Configure.
  - `_tick` пропускает кадры, пока `_suspended` или `_rebuild_pending`.
- Во время активного resize `BGCanvas._schedule_rebuild` больше не перекрашивает canvas в solid-цвет — это вызывало чёрные прямоугольники на HUD.
- `MinesweeperGame.new_game()` приостанавливает `BGCanvas` на время перестройки поля и возобновляет через `after_idle(...suspend(False))`.
- **Явный z-order:** после создания `_bg_cv` и `_center` вызываются `self._center.lift()` и `self._bg_cv.lower(self._center)`, чтобы HUD всегда был поверх фона.
- **Пост-обработка HUD:** добавлен `_post_new_game()`, вызываемый через `after_idle` после `_draw_field`. Он повторно поднимает z-order и перерисовывает LED (`_upd_mines_led`, `_upd_timer_led`), чтобы исключить обрезание индикаторов при смене сложности.
- `PillButton` больше не привязан к `<Configure>` (кнопка фиксированного размера).
- `_auto_cell_size()` больше не вызывает `update_idletasks()`.

### 13.7 Переключение вкладок HiddenNotebook (`src/views/modern_widgets.py`)
- `HiddenNotebook.select` после `pack_forget()`/`pack()` делает:
  - `update_idletasks()` для старой и новой вкладки;
  - `lift()` новой вкладки;
  - `_send_setredraw(hwnd, True)` + `InvalidateRect(hwnd, None, True)` + `UpdateWindow(hwnd)` для принудительной синхронной перерисовки всего окна.
- Это устраняет артефакт, при котором при уменьшенном окне содержимое предыдущей вкладки оставалось видимым поверх новой из-за `WS_EX_COMPOSITED` / `WindowTransitionStabilizer`.

### 13.8 Что осталось без изменений (намеренно)
- Анимации фона в Сапёре сохранены, но приостанавливаются на время перестройки/resize.

## 14. CrimeForm — артефакты скролла и динамический `WS_EX_COMPOSITED` (2026-06-24)

### Проблема
Во вкладке **Происшествие** (`CrimeForm`) при скролле большой canvas-формы возникали артефакты: старые фрагменты интерфейса «просвечивали» поверх новых, скролл был рваным. Источник — флаг `WS_EX_COMPOSITED` в кастомном Win32-хроме (`modern_widgets.py`).

### Диагностика
- `MANGUST_DISABLE_COMPOSITED=1` — полное отключение `WS_EX_COMPOSITED` устраняет артефакты скролла, но ломает chrome/отрисовку окна (WindowTransitionStabilizer, переключение вкладок).
- `MANGUST_STANDARD_CHROME=1` — стандартный chrome Windows устраняет проблему полностью, но отменяет кастомный тёмный заголовок и DWM-настройки.
- Попытки виртуализации (`virtual scroll`, `aggressive virtualization`), аккордеона и `place`-скролла не помогли или портят UX/теряют данные.
- WebView-прототип (`tkwebview2`) не заработал из-за несовместимости API:
  ```text
  TypeError: WebView2.__init__() missing 2 required positional arguments: 'width' and 'height'
  AttributeError: 'EdgeChrome' object has no attribute 'web_view'
  ```
  Откатан к canvas-режиму.

### Финальное решение — динамическое отключение composited
Реализован режим `MANGUST_DYNAMIC_COMPOSITED=1` (по умолчанию включён в `main.py`):
- `WS_EX_COMPOSITED` **включён** в обычном состоянии — chrome стабилен, ресайз/максимизация плавные.
- При любом скролле формы (`<MouseWheel>`, drag scrollbar, кнопки scrollbar) composited **временно отключается** у главного окна.
- После последнего события скролла composited **возвращается** с debounce (`MANGUST_COMPOSITED_REENABLE_DELAY_MS`, по умолчанию 900 мс).

### Код
- `main.py`:
  - `os.environ.setdefault("MANGUST_DYNAMIC_COMPOSITED", "1")` — включает динамический режим по умолчанию для dev-запуска и PyInstaller/установленного приложения.
- `src/views/modern_widgets.py`:
  - `_set_window_composited(hwnd, enabled, *, flush=False)` — переключение `GWL_EXSTYLE` через `SetWindowLongW` + `SetWindowPos` + `InvalidateRect`/`UpdateWindow`.
  - `disable_composited_temporarily(window, delay_ms=...)` / `restore_composited_later(window)` — debounce-обёртки.
- `src/views/crime_form.py`:
  - `_disable_composited_for_scroll()` — вызывается из `_on_scrollbar_yview()`, `_apply_mousewheel_units()` и других точек скролла.
- `run.bat` (дублирует настройку для совместимости со старыми ярлыками):
  ```bat
  set MANGUST_DYNAMIC_COMPOSITED=1
  ```

### Env-флаги для тестирования
| Переменная | Значение | Эффект |
|------------|----------|--------|
| `MANGUST_DYNAMIC_COMPOSITED` | `1` | Динамический режим (по умолчанию) |
| `MANGUST_COMPOSITED_REENABLE_DELAY_MS` | `1500` | Увеличить задержку возврата composited |
| `MANGUST_DISABLE_COMPOSITED` | `1` | Полное отключение (диагностика, ломает chrome) |
| `MANGUST_STANDARD_CHROME` | `1` | Стандартный Windows chrome (без кастомного заголовка) |
| `MANGUST_CRIME_WEBVIEW` | `1` | Нерабочий прототип WebView (не использовать) |

### Ограничения
- При **очень быстром** скролле (резкий drag scrollbar / интенсивное колесо) микро-артефакты остаются. Это фундаментальное ограничение Windows DWM + большого числа child-HWND в tkinter. В рамках tkinter кардинальных решений нет.
- WebView fallback потребовал бы доработки под текущую версию `tkwebview2` / WebView2 runtime.

### Чистка проекта
Удалены бэкап-папки и тестовые/временные файлы, оставшиеся от отладки:
- `backup_attempt7/`, `backup_attempt8v1/`, `backup_attempt8v1_2/`
- `backup_before_vfinal/`, `backup_before_webview/`, `backup_before_итог/`
- Артефакты type-hint: `4`, `None`, `Optional[str]`, `Optional[tk.Widget]`, `bool`, `str`
- `main.py.backup_20260622_105453`
- Debug/временные `.txt` и `.py` в корне проекта


## 15. Windows 7 Legacy Build (2026-07-10)

### Цель
Создать отдельную, **упрощённую** версию MANGUST v4, способную работать на **Windows 7 SP1 x86/x64**.
Основная линейка остаётся на Python 3.11 + Windows 10/11; Win7-версия — это форк в папке `win7/`.

### Почему отдельная папка
- Python 3.11 не поддерживает Windows 7.
- LLM/CUDA-зависимости невозможно собрать под Windows 7.
- Часть Win32 API (DWM immersive dark mode, GetDpiForWindow и др.) отсутствует в Windows 7.
- Проще поддерживать два изолированных артефакта, чем пытаться совместить всё в одной кодовой базе.

### Что уже сделано
1. Создана папка `win7/`.
2. Скопированы/синхронизированы:
   - `src/` — исходный код приложения;
   - `config/` — JSON-схемы и справочники **без** `config/models/` (GGUF-модели не нужны);
   - `tests/` — тесты;
   - `assets/` — иконки;
   - `main.py`, `run.bat`, `run.ps1` — точки входа;
   - `pyproject.toml`, `pytest.ini`, `README.md`;
   - `requirements-win7.txt` — зафиксированные зависимости для Python 3.8 / Windows 7.
   - `MANGUST_v4_Win7.spec` — PyInstaller spec для Win7.

### Что сделано (2026-07-10)

Адаптация выполнена агентом на AI Arena. Полный отчёт: `win7/ADAPTATION_REPORT.md`.

1. **Python 3.8.10** — приведены type hints (`X | Y` → `Optional`/`Union`, `list[str]` → `List[str]`), убран BOM.
2. **LLM/CUDA отключены** — `smart_import_core.py` работает только в Regex-режиме (LIGHT), UI «ИИ» скрыт.
3. **Win32 UI адаптирован** — DWM-атрибуты и DPI-aware API в `try/except`, на Windows 7 автоматически `MANGUST_STANDARD_CHROME=1`.
4. **Точки входа обновлены** — `run.bat` / `run.ps1` используют `venv\Scripts\python.exe`, `main.py` без pip auto-install и CUDA-path.
5. **Зависимости зафиксированы** — `requirements-win7.txt` без LLM/CUDA/WebView2/torch.
6. **Data-layer тесты проходят** — миграция, checkbox/web_value, coded combobox.
7. **Восстановлены недостающие модули** — калькуляторы, справочник УК/УПК, игры, `assets/empty.ico`, недостающие config-файлы.
8. **Сборка PyInstaller Win7 стабилизирована**:
   - Для x64 используется **полный Python 3.8.10** с `tkinter` (`win7/python38_full/`).
   - Для x86 используется **полный Python 3.8.10 x86** с `tkinter` (`win7/python38_full_x86/`), вместо embeddable-версии.
   - `win7/MANGUST_v4_Win7.spec` и `win7/MANGUST_v4_Win7_x86.spec` копируют `src/` как data-файлы (`datas += [(os.path.abspath('src'), 'src')]`), что позволяет fallback-импортам `mangust_v4.*` → `src.*` → bare modules работать в собранном EXE.
   - В `hiddenimports` добавлены `ttkbootstrap`, `jaraco.text`, `jaraco.context`, `jaraco.functools`, `platformdirs`.
   - Для pywin32 используется `collect_all('win32com')` + `collect_all('win32')` и явное копирование `pythoncom38.dll`/`pywintypes38.dll` из `pywin32_system32`.
   - В обоих spec установлен `upx=False` и явно добавлены CRT DLL (`vcruntime140.dll`, `vcruntime140_1.dll`, `msvcp140.dll` и др.) из соответствующего `python38_full*`.
   - Runtime hook `win7/rthooks/pyi_rth_win7_prereq.py` выдаёт предупреждение, если на Windows 7 отсутствует `AddDllDirectory`.
   - При сборке задаются `PYTHONUTF8=1` и `PYTHONIOENCODING=utf-8`, иначе PyInstaller падает на парсинге `.spec` в путях с кириллицей.
9. **Фикс `_socket` на Windows 7 SP1** (2026-07-14):
   - **Корневая причина:** Python 3.8 использует `LoadLibraryExW` с флагами `LOAD_LIBRARY_SEARCH_*`, которые требуют обновления **KB3063858** (или KB2533623) на Windows 7 SP1. Без него `_socket.pyd`, `_ssl.pyd`, `_ctypes.pyd` и др. не загружаются.
   - **Решение:** универсальный установщик `installer_assets/win7/setup.nsi` автоматически проверяет наличие `AddDllDirectory` и, при необходимости, устанавливает `KB3063858` + Visual C++ 2015-2022 Redistributable, после чего предлагает перезагрузку.
   - Файлы prerequisites скачиваются в `installer_assets/win7/prerequisites/`:
     - `KB3063858/Windows6.1-KB3063858-x86.msu`
     - `KB3063858/Windows6.1-KB3063858-x64.msu`
     - `vcredist/VC_redist.x86.exe`
     - `vcredist/VC_redist.x64.exe`
10. **Smoke-test Win7 EXE проходит** — приложение стартует, загружает схемы, отрисовывает главное окно.

### Что требует ручной проверки на Windows 7
- ✅ GUI-запуск собранного `MANGUST_v4_Win7.exe` и запуск через `venv` — проверены на доступной Windows-машине.
- ✅ Умный импорт и конвертер 1→3 лица в Regex-режиме — работают.
- ✅ `pytest tests -q` внутри `venv` — проходит.
- ⏳ Создание лица, заполнение происшествия, сохранение/загрузка JSON — требуется полный пользовательский сценарий на Windows 7 SP1 x86/x64.

### Артефакты в папке `win7/`
```
win7/
├── main.py                       # адаптированная точка входа
├── run.bat                       # запуск через venv
├── run.ps1                       # запуск через venv (PowerShell)
├── pyproject.toml                # Python >=3.8
├── pytest.ini
├── requirements-win7.txt         # зафиксированные зависимости
├── README.md
├── AGENTS.md                     # локальная сводка для агента
├── MANGUST_v4_Win7.spec          # PyInstaller spec x64
├── MANGUST_v4_Win7_x86.spec      # PyInstaller spec x86
├── rthooks/                      # runtime hooks PyInstaller
│   └── pyi_rth_win7_prereq.py    # вторичная проверка KB3063858
├── python38_full/                # полный Python 3.8.10 x64 с tkinter/tcl/tk
├── python38_full_x86/            # полный Python 3.8.10 x86 с tkinter/tcl/tk
├── venv_x86/                     # виртуальное окружение x86
├── venv/                         # виртуальное окружение Win7
├── build/MANGUST_v4_Win7/        # build-артефакты PyInstaller x64
├── build/MANGUST_v4_Win7_x86/    # build-артефакты PyInstaller x86
├── dist/MANGUST_v4_Win7/         # собранное портативное приложение x64
├── dist/MANGUST_v4_Win7_x86/     # собранное портативное приложение x86
├── assets/
├── config/                       # без models/
├── src/                          # адаптированный код
└── tests/                        # адаптированные тесты
```

### Ограничения Win7-версии
- **Без LLM**: умный импорт только на Regex, или вкладка скрыта.
- **Без CUDA**: все вычисления на CPU.
- **Без WebView2**: если понадобится web-просмотр — только внешний браузер.
- **Упрощённый chrome**: нативный заголовок окна Windows 7.

### Как пользоваться
1. На машине с Windows 7 установить Python 3.8.10.
2. Перейти в `win7/`.
3. Создать venv: `python -m venv venv` (или `py -3.8 -m venv venv`).
4. Установить зависимости: `venv\Scripts\pip install -r requirements-win7.txt`.
5. Запустить: `run.bat`.

### Проблемы и решения при сборке Win7 (2026-07-14)

#### 1. Поддержка `.doc` через Word COM (pywin32)
- Добавлен `pywin32==306` в `win7/requirements-win7.txt`.
- В `win7/MANGUST_v4_Win7.spec` и `win7/MANGUST_v4_Win7_x86.spec` добавлено:
  - `collect_all('win32com')` и `collect_all('win32')` для включения Python-модулей pywin32;
  - ручное копирование `pythoncom38.dll`/`pywintypes38.dll` из `pywin32_system32` в сборку.
- pywin32 DLL в собранном приложении находятся в `_internal/pywin32_system32`, `win32com` и `win32` — в `_internal/win32com` / `_internal/win32`.
- **Важно:** чтение `.doc` работает только при наличии Microsoft Word или LibreOffice Writer на целевой машине. Без Office `.doc` не открывается; `.docx`, `.pdf`, `.txt` работают без Office.

#### 2. Две архитектуры: x64 и x86
- `win7/dist/MANGUST_v4_Win7` — 64-битная сборка (Python 3.8.10 x64, `python38_full/`).
- `win7/dist/MANGUST_v4_Win7_x86` — 32-битная сборка (Python 3.8.10 x86, `python38_full_x86/`).
- Универсальный установщик `installer_assets/win7/setup.nsi` выбирает архитектуру по `${RunningX64}` и копирует соответствующий `dist/`.

#### 3. PyInstaller loader: `os.add_dll_directory` падает на Windows 7 без KB2533623
- **Ошибка:** `OSError: [WinError 127] Не найдена указанная процедура: '...\_internal\pywin32_system32'`.
- **Причина:** PyInstaller loader `pyimod04_pywin32.py` вызывает `os.add_dll_directory`, который на Win7 требует системный API `AddDllDirectory` (KB2533623). На чистой Win7 x86/x64 этого API нет.
- **Решение:** пропатчен `venv/Lib/site-packages/PyInstaller/loader/pyimod04_pywin32.py` и `venv_x86/Lib/site-packages/PyInstaller/loader/pyimod04_pywin32.py`:
  ```python
  try:
      os.add_dll_directory(pywin32_system32_path)
  except OSError:
      pass
  ```
  При ошибке загрузчик продолжает работу; DLL всё равно добавляются в `PATH` ниже по коду.

#### 4. Ошибка `ImportError: DLL load failed while importing _socket` на Win7 32-bit
- **Ошибка:** приложение падает на старте в runtime hook `pyi_rth_multiprocessing.py` → `import socket` → `ImportError: DLL load failed while importing _socket: Параметр задан неверно`.
- **Контекст:** возникает при запуске `MANGUST_v4_Win7_x86.exe` на Windows 7 SP1 x86 без обновления **KB3063858** (или KB2533623). Python 3.8 использует `LoadLibraryExW` с флагами `LOAD_LIBRARY_SEARCH_*`, которые требуют API `AddDllDirectory`, появившегося после установки этого обновления.
- **Решение:**
  1. Установщик `installer_assets/win7/setup.nsi` перед копированием приложения вызывает `HasAddDllDirectory` и, если API отсутствует, тихо устанавливает `KB3063858` (`wusa.exe ... /quiet /norestart`) и VC++ Redistributable.
  2. Если установка потребовала перезагрузки, в финишном диалоге предлагается перезагрузить ПК.
  3. `win7/main.py` при старте на Windows 7 проверяет `AddDllDirectory` и показывает предупреждение, если обновление всё ещё отсутствует (вторичная защита).
  4. В оба spec добавлен `upx=False` и явные CRT DLL, чтобы исключить конфликты упаковки и отсутствующего VCRuntime.
- **Статус:** исправлено на уровне установщика + runtime guard. Пользователь подтвердил успешный запуск собранного приложения Win7 Legacy x86/x64. Финальная проверка на чистой Win7 SP1 с установкой KB3063858 остаётся желательной, но критическая ошибка устранена.

#### 5. Кодировка установщика NSIS
- `setup.nsi` сохранён в UTF-8.
- Сборка установщика обязательно с флагом `-INPUTCHARSET UTF8`:
  ```bash
  makensis.exe -INPUTCHARSET UTF8 setup.nsi
  ```
- Без флага русский текст в мастере установки превращается в кракозябры.

#### 6. Прокрутка / composited на Win10/11 при запуске Win7-сборки
- В `win7/main.py` добавлено `os.environ.setdefault("MANGUST_DYNAMIC_COMPOSITED", "1")` для всех Windows.
- На Windows 7 остаётся `MANGUST_STANDARD_CHROME=1` + `MANGUST_DISABLE_COMPOSITED=1`.
- На Win10/11 при запуске Win7-установщика теперь активируется динамический режим отключения `WS_EX_COMPOSITED` при скролле, что устраняет «наезжание» секций.

#### 7. NSIS падает на тестовых `.egg` из `setuptools` / `pkg_resources`
- **Ошибка:** `makensis` не может открыть файлы с путями > 260 символов, которые тянет `collect_all('pkg_resources')` / `collect_all('setuptools')` (`pkg_resources/tests/data/*.egg`, `setuptools/tests/...`).
- **Решение:** в `win7/MANGUST_v4_Win7.spec` и `win7/MANGUST_v4_Win7_x86.spec` после всех `collect_all()` добавлена фильтрация `datas`:
  ```python
  _filtered_datas = []
  for _src, _dst in datas:
      _dst_norm = str(_dst).replace('\\', '/')
      _src_norm = str(_src).replace('\\', '/')
      if '/tests/' in _dst_norm or '/tests/' in _src_norm or '.egg' in _src_norm:
          continue
      _filtered_datas.append((_src, _dst))
  datas = _filtered_datas
  ```
- **Результат:** из сборки исключены `pkg_resources/tests/`, `setuptools/tests/`, `setuptools/_distutils/tests/`, `setuptools/_vendor/importlib_resources/tests/` и все `.egg`-файлы; установщик собирается без ошибок длинных путей.


## 16. Установщики Windows (2026-07-13)

### Релиз 2026-07-23 — финальный кастомный установщик Win10/11 (принят пользователем) ✅
- ✅ **`dist_installer/MANGUST_v4_Win10_11_Setup.exe`** (588 МБ) — принят («Годится, оставлям»). Основа: вариант агента `arena/019f8dee-mangust` (направление B) + точечные фиксы.
- **Состав страниц:**
  - **Welcome**: тёмный мокап; текст — локальная форма криминалистического учёта преступлений для последующего внесения в централизованный учёт «Мангуст — ИС СК России» (**приказ СК России от 18.07.2025 № 96**). Дубль подзаголовка убран (`WelcomePage.Description` не задаётся), список возможностей с welcome убран.
  - **Прогресс**: золотой бегунок **внизу** панели + %, список возможностей приложения **по центру**; элементы родированы на `WizardForm.ProgressGauge.Parent` (КЛЮЧЕВОЕ: формовые контролы InnerNotebook перекрывает).
  - **Внутренние страницы**: нейтральный хедер navy + золотая линия-разделитель под хедером (позиция от низа `PageDescriptionLabel`), без баннера поверх стандартного хедера (он обрезал заголовки).
  - **Finish**: боковая панель с гербом.
- **Критические уроки Inno Setup (оплачено ~7 итераций):**
  - Оверлей на стандартной странице — ТОЛЬКО репарентингом на панель страницы (`<Control>.Parent` её штатного контрола). `BringToFront` на уровне `WizardForm` бесполезен против поверхности InnerNotebook.
  - Стандартный хедер (`PageNameLabel`/`PageDescriptionLabel`) НЕЛЬЗЯ перекрывать баннером и увеличивать `Font.Size` (16pt обрезает текст сверху — метка фиксированной высоты).
  - `TColor` = BGR (`$00BBGGRR`): `$001B0D2A` — это бордовый, navy — `$002A1B0D`.
  - `TBitmapImage.Color` и `TNewStaticText.Transparent` НЕ публикуются (компиляция падает). Золотая линия — bitmap `divider_gold.bmp`.
  - `#13#10` нельзя ставить в начало строки скрипта — препроцессор Inno принимает за директиву (переносы только в конце строк: `...' + #13#10 +`).
  - BMP только 24-bit; `WizardResizable` устарела; `InnerPage` без `.Surface`.
  - Геометрия оверлеев — только в `CurPageChanged` (при показе страницы), не в `InitializeWizard`.
- Итоговый скрипт и разбор: репо `installer_work/inno/` (`setup.iss`, `INNO_FINAL.md`, `PROMPT_INNO*.md` — история попыток).

### Релиз 2026-07-22 — кастомный дизайн, без LLM/CUDA (текущий)
- ✅ **Оба установщика пересобраны с нуля** с фирменным дизайном (тёмно-синий + золото + циан-неон, официальная эмблема СК России):
  - `dist_installer/MANGUST_v4_Win10_11_Setup.exe` — **588 МБ** (было ~2.8 ГБ; компоненты `llm_model` и `cuda_runtime` удалены — приложение работает в Regex-режиме).
  - `dist_installer/MANGUST_v4_Win7_Setup.exe` — **~135 МБ** (x64/x86 авто-выбор, prerequisites KB3063858 + VC++ redist, `-INPUTCHARSET UTF8`).
- ✅ **Графика — комплект Агента 4** (`LLM/для установщика/для арены_картинки/extract_4/MANGUST_v4/`): панель 164×314, квадрат 164×164, `app_icon.ico` (7 размеров 16–256), иконки 48×48 24-bit BMP, `install_bg.bmp` 816×401 24-bit (фон кастомной welcome-страницы). Скопирована в `installer_assets/win10_11/images/` и `win7/images/`.
- ✅ **Скрипты — на базе кода Агента 2** (`LLM/для установщика/22.07.2026/Агент № 2.md`) с правками:
  - Кастомная страница приветствия сделана правильно: `CreateCustomPage(wpWelcome)` + `ShouldSkipPage` пропускает стандартную, фон `TBitmapImage` **родирован в `WelcomePage.Surface`** (`alClient` + `Stretch`), лейблы с `Transparent := True` поверх, DPI-скейлинг `ScaleX/ScaleY`.
  - **TColor — формат BGR** (`$00BBGGRR`), не RGB! Подзаголовок `$00CFC1B4` (#B4C1CF), золото издателя `$0027A2C9` (#C9A227). Устаревшая директива `WizardResizable` убрана (игнорируется Inno 6.7).
  - Лицензия обновлена: «дистрибутив НЕ содержит нейросетевых моделей».
  - Новый подзаголовок везде: **«Локальная система централизованного криминалистического учета преступлений СК России»**; старый («Автоматизация следственной деятельности») запрещён.
- ✅ **Приложение пересобрано** (PyInstaller): `dist/MANGUST_v4` (Win10/11) — включает Phase 2/3, фикс мержа импорта, удаление ИИ из UI, скролл preview, подсветку секций, эталонную схему фонов.
- ✅ **win7/src синхронизирован с основным src** через `tools/convert_to_py38.py` (конвертер PEP 604/585 → 3.8); все файлы компилируются `python38`. Пересобраны `win7/dist/MANGUST_v4_Win7` (x64) и `win7/dist/MANGUST_v4_Win7_x86`.
  - ⚠️ Известный баг конвертера: слипание строки `-> None:` со следующей (встречено в `preview_view.py::_render_files` — исправлено вручную). После каждой конвертации прогонять `py_compile` по всему `win7/src`.
- ⚠️ **Мусор в `src/views/`**: бэкап-папки `Для проверки/`, `Новый агент/`, `Последняя версия/`, `Рабочая версия/` и `*.txt`-бэкапы (`modern_widgets.py.txt` и др.) — `datas` PyInstaller копирует весь `src` в сборку. Безвредно, но раздувает дистрибутив; вычистить при следующей сборке.

### Статус на 2026-07-13 (архив)
- ✅ **Windows 10/11**: приложение запущено пользователем, LLM-режим и RegEx-режим работают корректно. Установщик `dist_installer/MANGUST_v4_Win10_11_Setup.exe` (~2.8 ГБ) пересобран через Inno Setup 6 с включённым pywin32 для чтения `.doc`.
- ✅ **Windows 7 Legacy**: собраны портативные `win7/dist/MANGUST_v4_Win7/MANGUST_v4_Win7.exe` (x64) и `win7/dist/MANGUST_v4_Win7_x86/MANGUST_v4_Win7_x86.exe` (x86) на полном Python 3.8.10. Проблема `ImportError: DLL load failed while importing _socket` решается автоматической установкой **KB3063858** через NSIS-установщик.
- ✅ **Установщик Win7**: пересобран `dist_installer/MANGUST_v4_Win7_Setup.exe` (~134 МБ) через NSIS 3 с автовыбором x64/x86, включёнными prerequisites (KB3063858 + VC++ redist), кодировкой UTF8 (`-INPUTCHARSET UTF8`) и исключением тестовых `.egg`/`tests/` данных setuptools/pkg_resources.

### Структура установщиков

**Win10/11 (Inno Setup)**
- `installer_assets/win10_11/setup.iss` — скрипт установщика.
- Графика:
  - `WizardImageFile=images\wizard_image.png` — боковая иллюстрация 164×314 (новый стиль v2).
  - `WizardSmallImageFile=images\wizard_small_164.png` — квадратный логотип 164×164 в правом верхнем углу (новый стиль v2).
  - `SetupIconFile=images\app_icon.ico` — многоразмерная иконка v2 (16, 32, 48, 64, 128, 256 px).
- Компоненты:
  - **MANGUST v4 — основное приложение** (обязательно)
  - **LLM-модель Qwen 2.5 3B** (~2.3 ГБ, опционально)
  - **CUDA runtime** (~740 МБ, опционально; cudart64_12.dll, cublas64_12.dll, cublasLt64_12.dll)
- Исходные файлы:
  - приложение — `dist/MANGUST_v4/`
  - модель — `config/models/qwen2.5-3b-instruct-q5_k_m.gguf`
  - CUDA — `installer/cuda_runtime/`
- **pywin32 для чтения `.doc`:**
  - `MANGUST_v4.spec` не использует `collect_all('win32')`/`collect_all('win32com')` — эти вызовы ломают порядок загрузки модулей;
  - pywin32 (`win32com`, `pythoncom`, `pywintypes`) автоматически собирается стандартными хуками PyInstaller;
  - DLL `pythoncom311.dll`/`pywintypes311.dll` также копируются хуками в `_internal/pywin32_system32`.
  - Без pywin32 в сборке на Windows 10 умный импорт падает с ошибкой «Модуль pywin32 не установлен» при попытке прочитать `.doc` через Word COM.

**Win7 (NSIS)**
- `installer_assets/win7/setup.nsi` — скрипт установщика.
- `win7/MANGUST_v4_Win7.spec` — PyInstaller spec для x64.
- `win7/MANGUST_v4_Win7_x86.spec` — PyInstaller spec для x86.
- `win7/rthooks/pyi_rth_win7_prereq.py` — runtime hook; предупреждает, если на Windows 7 отсутствует `AddDllDirectory`.
- В обоих spec:
  - `datas` включает `config/`, `assets/`, `..\Приказ`, а также `src/` (`datas += [(os.path.abspath('src'), 'src')]`);
  - `hiddenimports` включает `ttkbootstrap`, `jaraco.text`, `jaraco.context`, `jaraco.functools`, `platformdirs`, `win32com`, `win32com.client`, `pythoncom`, `pywintypes`;
  - используется `collect_data_files('ttkbootstrap')` и `collect_all('ttkbootstrap')`;
  - используется `collect_all('win32com')` и `collect_all('win32')` для включения модулей pywin32;
  - принудительно копируются `pythoncom38.dll`/`pywintypes38.dll` из `pywin32_system32`;
  - `upx=False` в `EXE` и `COLLECT`;
  - явно добавлены CRT DLL из `python38_full*` (`vcruntime140.dll`, `vcruntime140_1.dll`, `msvcp140.dll` и др.).
- **Патч PyInstaller loader:** `venv/Lib/site-packages/PyInstaller/loader/pyimod04_pywin32.py` и `venv_x86/...` обёртывают `os.add_dll_directory` в `try/except OSError`, чтобы приложение запускалось на Windows 7 без KB2533623.
- **Prerequisites:** установщик включает и при необходимости устанавливает:
  - `KB3063858` (`Windows6.1-KB3063858-x86.msu` / `Windows6.1-KB3063858-x64.msu`) — обязательно для Python 3.8 на Windows 7 SP1;
  - Visual C++ 2015-2022 Redistributable (`VC_redist.x86.exe` / `VC_redist.x64.exe`).
  - Файлы хранятся в `installer_assets/win7/prerequisites/` и копируются в `$PLUGINSDIR\prereq` во время установки.
- Графика:
  - `MUI_WELCOMEFINISHPAGE_BITMAP=images\wizard_image.bmp` — 164×314 24-bit BMP (новый стиль v2).
  - `MUI_HEADERIMAGE_BITMAP=images\wizard_banner.bmp` — 150×57 24-bit BMP (`nsis_header.bmp` из v2).
  - `MUI_ICON=images\app_icon.ico` — многоразмерная иконка v2.
- Компоненты: x64 или x86 версия приложения (`win7/dist/MANGUST_v4_Win7/` или `win7/dist/MANGUST_v4_Win7_x86/`) выбирается автоматически по разрядности ОС.
- Сборка:
  ```bat
  cd win7
  set PYTHONUTF8=1
  set PYTHONIOENCODING=utf-8
  .\venv\Scripts\pyinstaller.exe --noconfirm MANGUST_v4_Win7.spec
  .\venv_x86\Scripts\pyinstaller.exe --noconfirm MANGUST_v4_Win7_x86.spec
  cd ..\installer_assets\win7
  ..\..\tools\nsis\Bin\makensis.exe -INPUTCHARSET UTF8 setup.nsi
  ```
- **Важно:** без `-INPUTCHARSET UTF8` `makensis` интерпретирует `setup.nsi` и `texts\02_license.txt` как ANSI, и весь русский текст на страницах приветствия/лицензии/завершения превращается в кракозябры. License-файл должен быть UTF-8 (желательно с BOM).

### Скрипты подготовки и сборки
- `prepare_installer_assets.py` — собирает финальные ассеты из комплекта v2 (`LLM/для установщика/обновленный вариант 2/installer_assets/`): масштабирует PNG до целевых размеров, копирует готовые BMP, конвертирует `.md` → `.txt`, валидирует размеры и иконки.
- `clean_installer_texts.py` — очищает тексты v2 от служебных markdown-заголовков, добавляет должность автору-разработчику и исправляет целевую аудиторию.
- `prepare_cuda_runtime.py` — скачивает и извлекает CUDA runtime DLL.
- `MANGUST_v4.spec` — PyInstaller spec для Win10/11.
- `BUILD_INSTALLERS.md` — полная инструкция по сборке.

### Важные ограничения
- **7B-модель (`qwen2.5-7b-instruct-q4_k_m.gguf`) не включается** в установщик и не используется программой.
- **3B-модель** — опциональный компонент только в Win10/11-установщике.
- **Win7-установщик** — без LLM/CUDA, только Regex-импорт.
- **CUDA runtime** в Win10/11-установщике кладётся в `{app}\_internal` (рядом с остальными runtime-DLL приложения), а не в отдельную папку. Это позволяет `llama-cpp-python` загружать `cudart64_12.dll` / `cublas64_12.dll` / `cublasLt64_12.dll` через `PATH`/`AddDllDirectory` без дополнительного кода в `main.py`. Компонент остаётся опциональным: если он не выбран при установке, LLM не загрузится на машинах без системного CUDA runtime.

### Что требует проверки
- ✅ Запуск приложения Win10/11 и работа LLM/RegEx — **проверено пользователем**.
- ✅ Запуск portable-сборки Win10/11 после добавления pywin32 — **проверен на сборочной машине**, приложение стартует и отрисовывает главное окно.
- ✅ Запуск приложения Win7 Legacy x64 — **проверен на Win10/11**, приложение стартует и отрисовывает главное окно.
- ✅ Установка и запуск Win7 Legacy **x86/x64 проверены пользователем** — приложение работает, все модули стартуют корректно.
- ⚠️ **Известный недочёт:** на Win7 есть небольшие проблемы с отображением значков/иконок; функциональность не затронута, правки отложены.
- ⏳ Установка/удаление через установщик на Windows 10/11 x64 (ярлыки, Uninstall).
- ⏳ Установка `KB3063858` и запуск приложения на чистой Windows 7 SP1 x86/x64 — требуется проверка на физической/виртуальной машине.
- ⏳ Работа RegEx-импорта и конвертера 1→3 лица в установленной Win7-сборке.
- ⏳ Работа LLM-модели при выборе компонентов «LLM-модель» + «CUDA runtime» на машине с NVIDIA (проверено в исходниках, требуется проверка в установленной сборке).

### Артефакты
- `dist_installer/MANGUST_v4_Win10_11_Setup.exe` — установщик для Windows 10/11.
- `dist_installer/MANGUST_v4_Win7_Setup.exe` — установщик для Windows 7 SP1.
- `dist/MANGUST_v4/` — собранное основное приложение Win10/11.
- `win7/dist/MANGUST_v4_Win7/` — собранное приложение Win7 x64.
- `win7/dist/MANGUST_v4_Win7_x86/` — собранное приложение Win7 x86.

---

## 17. Оформление установщика — обновление ассетов v2 (завершено, 2026-07-10)

### Что сделано
- ✅ Принят **квадратный** логотип `wizard_small_164.png` (164×164) для `WizardSmallImageFile` Inno Setup — современный вид, рекомендация агента v2.
- ✅ Подготовлены финальные ассеты в `installer_assets/`:
  - PNG: `wizard_image.png` 164×314, `finish_image.png` 164×314, `welcome_logo.png` 150×150, `install_background.png` 493×314, иконки разделов 64×64, `wizard_small_164.png` 164×164.
  - BMP: `wizard_image.bmp` 164×314, `finish_image.bmp` 164×314, `wizard_small_164.bmp` 164×164.
  - NSIS: `wizard_banner.bmp` 150×57 (скопирован из `nsis_header.bmp` v2).
  - Иконка: `app_icon.ico` с размерами 16, 32, 48, 64, 128, 256 px.
- ✅ Тексты очищены от служебных markdown-заголовков (`# Страница X — ...`, `## Заголовок`, `## Подзаголовок`, `## Основной текст`, `## Преамбула`, `## Контакты`) и приведены к финальному виду:
  - добавлена должность автора-разработчика;
  - целевая аудитория: «следователи следственных отделов, следователи-криминалисты, помощники следователей СУ СК РФ по Ростовской области».
- ✅ Обновлены скрипты:
  - `prepare_installer_assets.py` — теперь берёт картинки и тексты из `LLM/для установщика/обновленный вариант 2/installer_assets/`, масштабирует PNG, копирует BMP, конвертирует `.md` → `.txt`, валидирует размеры.
  - `clean_installer_texts.py` — переключён на обработку текстов v2.
  - `installer_assets/win10_11/setup.iss` — `WizardSmallImageFile` теперь указывает на `wizard_small_164.png`.
  - `installer_assets/win7/setup.nsi` — `MUI_HEADERIMAGE_BITMAP` использует готовый `wizard_banner.bmp` 150×57.
- ✅ Пересобраны установщики:
  - `dist_installer/MANGUST_v4_Win10_11_Setup.exe` — 2.8 ГБ (Inno Setup 6).
  - `dist_installer/MANGUST_v4_Win7_Setup.exe` — ~128 МБ (NSIS 3, включает prerequisites KB3063858 + VC++ redist и x64/x86 сборки).

### Источники ассетов
- `LLM/для установщика/обновленный вариант 2/installer_assets/` — исходный комплект v2 (картинки + тексты).

### Файлы
- `installer_assets/win10_11/setup.iss` — скрипт Inno Setup.
- `installer_assets/win7/setup.nsi` — скрипт NSIS.
- `prepare_installer_assets.py` — подготовка финальных ассетов.
- `clean_installer_texts.py` — очистка текстов и правки автора/аудитории.
- `dist_installer/MANGUST_v4_Win10_11_Setup.exe` — установщик для Windows 10/11 x64.
- `dist_installer/MANGUST_v4_Win7_Setup.exe` — установщик для Windows 7 SP1 x86/x64 (автовыбор разрядности).

### Кастомизация мастера установки Win10/11 через `[Code]`
- ✅ Добавлены UI-ассеты в установщик через `dontcopy` + `ExtractTemporaryFile`:
  - `license_icon.bmp` — иконка для страницы лицензии;
  - `components_icon.bmp` — иконка для страницы выбора компонентов;
  - `folder_icon.bmp` — иконка для страницы выбора папки и страницы задач.
- ⚠️ PNG-версии иконок вызывали runtime-ошибку `Bitmap image is not valid` при запуске установщика. Причина: Inno Setup 6.7.1 некорректно загружал эти PNG в `TBitmapImage` (возможно, из-за особенностей цветового профиля/метаданных). **Исправление:** иконки сконвертированы в 24-bit BMP и загружаются как `.bmp`.
- ✅ В секции `[Code]` скрипта `installer_assets/win10_11/setup.iss` реализована динамическая подстановка иконок:
  - иконки создаются как `TBitmapImage` с `Parent := WizardForm`;
  - каждой иконке вызывается `BringToFront`, чтобы она отображалась поверх страницы;
  - в обработчике `CurPageChanged` показывается только иконка текущей страницы;
  - иконки позиционируются в правой части окна ниже логотипа (`WizardForm.ClientWidth - 60, Top = 120`), чтобы не перекрываться `wizard_small_164.png`.
- ⚠️ Попытка установить тёмный фон формы и страниц (`WizardForm.Color`, `WizardForm.InnerNotebook.Color`, `TWizardPage.Surface.Color`) привела к ошибкам компиляции — эти свойства недоступны в публичном API Inno Setup 6.7.1. В качестве безопасного компромисса оставлены иконки на стандартном светлом фоне modern-стиля.
- ✅ PNG-иконки вызывали runtime-ошибку `Bitmap image is not valid`; переключены на 24-bit BMP (`license_icon.bmp`, `components_icon.bmp`, `folder_icon.bmp`).
- ✅ Исправлена ошибка запуска приложения после установки: `AttributeError: module 'pytz' has no attribute 'UnknownTimeZoneError'`. Причина — `babel`/`tkcalendar` требуют `pytz`, но он не был включён в PyInstaller-сборку. Исправление: установлен `pytz` в `venv_new` и добавлен `collect_all('pytz')` в `MANGUST_v4.spec`.
- ✅ Исправлена критическая ошибка `Failed to start embedded python interpreter!` / `ModuleNotFoundError: No module named 'src'`. Причина: PyInstaller 6.x не корректно собирал namespace-пакет `src` из корня проекта. Исправление:
  - добавлены `__init__.py` в `src/`, `src/controllers/`, `src/services/`;
  - в `MANGUST_v4.spec` добавлено явное копирование `src` как data-файлов: `datas += [(os.path.abspath('src'), 'src')]`;
  - установлен `pathex=[os.path.abspath('.')]` и список `hiddenimports` для ключевых модулей `src`.
- ✅ Исправлена ошибка загрузки LLM в собранном приложении: `llama-cpp-python не установлен`. Причина: PyInstaller 6.x не включал подмодуль `numpy._core._exceptions` (и ряд других модулей numpy 2.x), из-за чего `llama_cpp` не мог импортировать `numpy` и падал с `ImportError`. Исправление: в `MANGUST_v4.spec` добавлен `collect_all('numpy')` для полной сборки numpy.
- ✅ Исправлена ошибка `GGUF не найдена: ...\_internal\config\models\qwen2.5-3b-instruct-q5_k_m.gguf`. Причина: установщик Inno Setup копирует JSON-конфиги в `_internal/config` (вместе с приложением), а GGUF-модель — в `config/models` рядом с exe. `SmartImportProcessor` искал модель только в `config_dir/models`, где `config_dir` = `_internal/config`. Исправление: `SmartImportProcessor` теперь ищет GGUF в двух местах: `_internal/config/models` (fallback) и `config/models` рядом с exe (основной путь установщика). `AppController._resolve_config_dir()` оставлен на `_internal/config` для JSON-конфигов.
- ✅ Пересобраны приложение (`dist/MANGUST_v4/`) и установщик (`dist_installer/MANGUST_v4_Win10_11_Setup.exe`).

### Что требует проверки
- Визуальная проверка страниц приветствия, лицензии, выбора компонентов, выбора папки, задач и завершения в Win10/11-установщике.
- Корректность отображения квадратного логотипа `wizard_small_164.png` в Inno Setup.
- Корректность отображения иконок `license_icon.png`, `components_icon.png`, `folder_icon.png` в правом верхнем углу соответствующих страниц.
- Корректность отображения боковой иллюстрации `wizard_image.bmp` и верхнего баннера `wizard_banner.bmp` в NSIS (Win7).
- Установка и запуск приложения после установки.
