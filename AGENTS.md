# AGENTS.md — Порайонка v2.0 DARK final

## 1. Общее описание проекта

**Порайонка** — десктопное приложение для учёта статусов следственных отделов Следственного комитета РФ по Ростовской области.

Проект содержит **две реализации**:

1. **Основная (Python + Flet)** — полноценное десктопное приложение в папке `porayonka-app/`.
   - Две вкладки: «Следственные отделы» и «Зональные криминалисты».
   - Тёмная тема (DARK final).
   - Сохранение данных в `%APPDATA%\porayonka\`.
   - Экспорт в Excel и HTML.
   - Сборка в `.exe` через PyInstaller / Flet pack.

2. **Веб-прототип (React + Vite + Tailwind)** — упрощённая версия в корне `src/`.
   - Только вкладка «Следственные отделы» (29 отделов).
   - Хранение в `localStorage`.
   - Экспорт в CSV и HTML.
   - Сборка в один `index.html` через `vite-plugin-singlefile`.

> Важно: `porayonka-app/README.md` написан для версии 1.0 (светлая тема, одна вкладка) и не отражает текущее состояние v2.0. Используйте **этот файл** как источник правды.

---

## 2. Технологический стек

### Python-приложение (основное)

| Компонент | Версия / Библиотека |
|-----------|---------------------|
| Язык | Python 3.10+ |
| GUI | Flet 0.23.2 |
| Excel | openpyxl 3.1.5 |
| Сборка | PyInstaller / `flet pack` |
| Тема | Material 3, тёмная палитра `core/constants.py` |

### Веб-прототип (React)

| Компонент | Версия / Библиотека |
|-----------|---------------------|
| Framework | React 19.2.3 |
| Bundler | Vite 7.2.4 |
| Styling | Tailwind CSS 4.1.17 |
| Single-file | `vite-plugin-singlefile` 2.3.0 |
| TypeScript | 5.9.3 |

---

## 3. Структура репозитория

```
.
├── index.html              # Точка входа React-версии
├── package.json            # Зависимости React-версии
├── vite.config.ts          # Vite + Tailwind + singlefile
├── tsconfig.json           # TS настройки
├── src/                    # React-версия
│   ├── App.tsx             # Главный компонент (29 отделов + статусы + экспорт)
│   ├── main.tsx            # Точка входа React
│   ├── index.css           # Tailwind CSS
│   └── utils/cn.ts         # clsx + tailwind-merge утилита
├── Porayonka_Win7.spec     # PyInstaller spec для Win7 (корень, не используется напрямую)
└── porayonka-app/          # Основное Python + Flet приложение
    ├── main.py             # Точка входа Flet
    ├── requirements.txt    # flet==0.23.2, openpyxl==3.1.5
    ├── README.md           # УСТАРЕВШИЙ README v1.0 (не доверять)
    ├── build_exe.bat       # Сборка .exe через flet pack (v1.0, устаревший путь)
    ├── build_win7.bat      # Сборка Win7 через PyInstaller + flet 0.21.2
    ├── fix_flet.py         # Автофикс hint_text_color → hint_style
    ├── fix1_zonal_tab.py   # Убрать аннотацию ReportTemplate во вложенной функции
    ├── fix2_clear.py       # Очистка формы: сброс названия, режима, пересоздание builder
    ├── fix3_unit_field.py  # Увеличить ширину поля единицы измерения
    ├── Команда для сборки портативной версии.txt  # Однострочная команда PyInstaller
    ├── Porayonka.spec      # PyInstaller spec для обычной сборки
    ├── Porayonka_Win7.spec # PyInstaller spec для Win7
    ├── core/               # Бизнес-логика и данные
    │   ├── __init__.py
    │   ├── models.py       # Department, Status (Enum + dataclass)
    │   ├── data.py         # Загрузка/сохранение departments.json
    │   ├── exporter.py     # ExcelExporter, HTMLExporter
    │   ├── constants.py    # Цвета, список 29 отделов, заголовки
    │   ├── zonal_models.py      # Модели для вкладки «Зональные»
    │   ├── zonal_data.py        # Загрузка/сохранение зональных данных
    │   ├── zonal_constants.py   # Список 16 криминалистов и зон
    │   └── zonal_exporter.py    # ZonalExcelExporter
    ├── assets/
    │   └── styles.py       # Тема Flet (тёмная)
    └── ui/                 # UI-компоненты Flet
        ├── __init__.py
        ├── header.py         # Шапка приложения
        ├── stats_bar.py      # 4 карточки статистики + прогресс-бар
        ├── toolbar.py        # Поиск, кнопки Сохранить/Экспорт/Сброс
        ├── legend.py         # Легенда статусов
        ├── department_table.py  # Таблица 29 отделов + фильтрация
        ├── status_cell.py    # Кликабельная ячейка статуса
        ├── export_modal.py   # Диалог экспорта
        ├── reset_modal.py    # Диалог подтверждения сброса
        ├── toast.py          # SnackBar уведомления
        └── zonal/            # Вкладка «Зональные криминалисты»
            ├── __init__.py
            ├── zonal_tab.py           # Корневая вкладка
            ├── template_builder.py    # Конструктор шаблонов отчётов
            ├── criminalist_tile.py    # Квадратная плашка криминалиста (сетка, фаза 2)
            ├── form_fields.py         # Переиспользуемые блоки ввода формы
            ├── form_input_modal.py    # Модальное окно заполнения формы
            ├── add_criminalist_modal.py  # Добавление/редактирование/удаление криминалиста
            └── summary_panel.py       # Компактная общая сводка (только активные)
```

---

## 4. Возможности приложения

### 4.1 Вкладка «Следственные отделы»

- **29 отделов**: 27 СО/МСО Ростовской области + ОВД-1 + ОВД-2.
- **3 статуса** (циклическое переключение кликом по ячейке):
  - `empty` — не получено (серый)
  - `received` — получено (зелёный)
  - `in_progress` — в работе (жёлтый)
- **Поиск** по названию отдела с фильтрацией таблицы.
- **Статистика** в реальном времени: получено, в работе, не получено, прогресс (%).
- **Автосохранение** при каждом изменении статуса.
- **Ручное сохранение** кнопкой «Сохранить».
- **Сброс** всех статусов с подтверждением.
- **Экспорт**:
  - Excel (`.xlsx`) через `openpyxl` — форматирование, цвета, сводка.
  - HTML — браузерная таблица с кнопкой печати.
- **ОВД-1/ОВД-2** отображаются курсивом, без номера, с разделителем.

### 4.2 Вкладка «Зональные криминалисты»

- **16 криминалистов** по умолчанию (`core/zonal_constants.py`).
- **Конструктор шаблонов отчётов**:
  - Добавление/удаление пунктов.
  - Тип пункта: числовой (`numerical`) или факт сдачи (`deliverable`, да/нет).
  - Единица измерения для числовых пунктов.
  - Режим «По отделам»: детализация значений по каждому закреплённому отделу.
  - Сохранение/загрузка/очистка шаблонов.
- **Сетка плашек криминалистов** (фаза 2):
  - Компактные квадратные плашки в адаптивной сетке (3-4 в ряд, `ResponsiveRow`).
  - На плашке: ФИО, чип активности, закреплённые отделы (обрезка + tooltip), индикатор заполненности (прогресс-бар + %).
  - Быстрое переключение активности (`is_active`) прямо на плашке; неактивные — приглушены (полупрозрачные).
  - Клик по плашке открывает модальное окно заполнения формы; кнопка редактирования открывает модальное окно (ФИО, примечание, закреплённые отделы, удаление криминалиста).
  - Поиск по ФИО + фильтры: «Все» / «Не заполнившие» / «Неактивные».
  - Кнопка «Скопировать список не сдавших» (ФИО + отделы, `page.set_clipboard`) — заглушка под Telegram / Messenger MAX.
  - Обновление конкретной плашки без полной перерисовки сетки (`rebuild_tile_content`).
- **Общая сводка** — компактная панель сверху: активные криминалисты, сдано пунктов, общий прогресс (только активные).
- **Экспорт в Excel** с детализацией по криминалистам и отделам.
- **Автосохранение** всех изменений.

### 4.3 Веб-прототип (React)

- Только функционал вкладки «Следственные отделы».
- Хранение в `localStorage` (`porayonka_departments`).
- Экспорт в CSV и HTML (не Excel).
- Сборка в один файл для встраивания/веба.

---

## 5. Запуск и разработка

### 5.1 Python-приложение

```bash
cd porayonka-app
pip install -r requirements.txt
python main.py
```

### 5.2 React-прототип

```bash
npm install
npm run dev        # dev-сервер
npm run build      # production-сборка в dist/
npm run preview    # просмотр сборки
```

### 5.3 Сборка `.exe`

**Стандартная сборка (PyInstaller):**

```bash
cd porayonka-app
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --onefile --windowed --name "Порайонка" --add-data "core;core" --add-data "ui;ui" --add-data "assets;assets" main.py
```

Результат: `porayonka-app/dist/Порайонка.exe`.

**Сборка для Windows 7:**

```bash
cd porayonka-app
pip install flet==0.21.2 openpyxl
pip install pyinstaller
pyinstaller --onefile --windowed --name "Porayonka_Win7" --add-data "core;core" --add-data "ui;ui" --add-data "assets;assets" --hidden-import flet --hidden-import openpyxl main.py
```

Или запустить `build_win7.bat` (требует Python в PATH).

**Устаревший вариант через `flet pack`:**

Файл `build_exe.bat` использует `flet pack` и устаревший путь `dist\Porayonka.exe`. В v2.0 используется PyInstaller.

---

## 6. Где хранятся данные

### Python-приложение

```
%APPDATA%\porayonka\
├── departments.json          # Данные вкладки «Следственные отделы»
├── zonal_collection.json     # Текущий сбор зональных данных
├── zonal_criminalists.json   # Список криминалистов
└── templates\                # Сохранённые шаблоны зональных отчётов
    └── *.json
```

### React-прототип

```
localStorage["porayonka_departments"]      # массив Department
localStorage["porayonka_departments_meta"] # { lastSaved: ISOString }
```

---

## 7. Форматы данных

### 7.1 `departments.json` (Python)

```json
{
  "departments": [
    {
      "id": 1,
      "name": "СО по г. Азов",
      "status": "received",
      "updated_at": "2026-04-14T10:30:00",
      "is_ovd": false
    }
  ],
  "last_saved": "2026-04-14T10:35:46"
}
```

Статусы: `empty`, `received`, `in_progress`.

### 7.2 Зональные данные

См. `core/zonal_models.py`:

- `ReportTemplate` — шаблон сбора (название, список пунктов, режим по отделам).
- `ReportTemplateItem` — пункт шаблона (id, name, item_type, unit, order).
- `Criminalist` — криминалист (id, full_name, note, zone).
- `CriminalistZone` — закреплённые отделы.
- `ReportData` — значение по криминалисту и пункту.
- `ZonalCollection` — текущий сбор данных.

### 7.3 React `localStorage`

```typescript
interface Department {
  id: number;
  name: string;
  status: "empty" | "received" | "in_progress";
  updatedAt: string | null; // ISOString
  isOvd: boolean;
}
```

---

## 8. Цветовая палитра (тёмная тема)

Определена в `porayonka-app/core/constants.py` и частично в `porayonka-app/assets/styles.py`:

```python
COLORS = {
    "primary":        "#0f172a",   # Глубокий синий (фон шапки)
    "primary_dark":   "#020617",   # Почти чёрный
    "primary_light":  "#1e293b",   # Фон карточек/списков
    "bg":             "#0b1120",   # Фон приложения
    "card":           "#15202e",   # Фон карточек
    "card_hover":     "#1e293b",   # Hover карточек
    "border":         "#334155",   # Границы
    "text":           "#f8fafc",   # Основной текст
    "text_secondary": "#94a3b8",   # Вторичный текст
    "text_muted":     "#64748b",   # Приглушённый текст
    "received":       "#22c55e",   # Получено
    "in_progress":    "#f59e0b",   # В работе
    "empty":          "#64748b",   # Не получено
    "btn_save":       "#3b82f6",   # Сохранить
    "btn_export":     "#10b981",   # Экспорт
}
```

React-версия использует похожие цвета, но hardcoded в `src/App.tsx`.

---

## 9. Архитектурные особенности и соглашения

### Python / Flet

- **Разделение**: `core/` — бизнес-логика, `ui/` — представление, `assets/` — тема.
- **Состояние страницы**: ссылки на важные контролы сохраняются в `page.*` (например, `page.status_cells`, `page.stats_received_text`, `page.open_export_modal`).
- **Обновление UI**: после изменения данных вызываются `update_*` функции, которые обновляют `page.*` ссылки.
- **Фильтрация таблицы**: реализована через замену `page.rows_column.controls`, а не пересоздание строк.
- **Поддержка Flet 0.23.2**: используется `hint_style=ft.TextStyle(...)` вместо устаревшего `hint_text_color`. Все иконки — `ft.icons.*`, а не `ft.Icons.*`.
- **Обработка ошибок**: большинство операций сохранения/обновления обёрнуты в `try/except` с `print` в консоль и `show_error_toast`.

### React

- **Single-file сборка**: Vite собирает всё в один HTML-файл (`vite-plugin-singlefile`).
- **Стили**: Tailwind 4 через `@import "tailwindcss"` в `index.css`.
- **Псевдоним `@/`**: разрешается в `src/`.
- **Состояние**: `useState`, `useEffect`, `useCallback`, `useRef`.
- **Экспорт**: ручная генерация CSV и HTML через Blob и `URL.createObjectURL`.

---

## 10. Известные фиксы и скрипты-патчи

В проекте есть несколько «фикс-скриптов», которые правили код под особенности Flet/Python:

| Файл | Что делает | Зачем |
|------|------------|-------|
| `fix_flet.py` | ~~Заменяет `hint_text_color` на `hint_style`~~ | **Удалён** — исправления уже встроены в код |
| `fix1_zonal_tab.py` | Убирает аннотацию `t: ReportTemplate` во вложенной функции `_select_template` | Избежание проблем с областью видимости / Python версиями |
| `fix2_clear.py` | При очистке шаблона сбрасывает имя на «Новая форма», режим по отделам, пересоздаёт builder | Корректный сброс UI |
| `fix3_unit_field.py` | Увеличивает ширину поля единицы измерения и добавляет padding | UX улучшение |

> Эти скрипты уже применены к текущему коду. Перед повторным запуском убедитесь, что изменения не дублируются.

---

## 11. Подводные камни и что проверять

### Flet / Python

1. **Flet 0.23.2**: параметр `hint_text_color` вызывает ошибку. Везде используется `hint_style=ft.TextStyle(...)`.
2. **Сборка PyInstaller**: не забудьте `--add-data "core;core" --add-data "ui;ui" --add-data "assets;assets"`, иначе импорты пакетов не найдутся.
3. **Windows 7**: требуется Flet 0.21.2 и PyInstaller. Возможны конфликты с более новыми версиями Flet.
4. **Путь к данным**: в собранном `.exe` используется `%APPDATA%\porayonka`. При запуске из исходников — то же самое (зависит от пользователя, а не от расположения проекта).
5. ~~**Дублирование импорта `get_initial_criminalists`**~~: в `zonal_tab.py` теперь единый импорт из `core.zonal_data`.
6. **Сохранение шаблонов**: имена файлов формируются из названия шаблона (замена пробелов на `_`). Дублирование имён перезаписывает существующий файл.
7. **Обновление UI в модальных окнах**: многие `.update()` обёрнуты в `try/except`, чтобы избежать краша при закрытии диалога.

### React

1. **Нет зональной вкладки**: веб-версия — только трекер 29 отделов.
2. **localStorage**: данные не синхронизируются с Python-версией.
3. **Экспорт CSV**: использует `;` разделитель и BOM для Excel.
4. **Single-file**: весь JS/CSS встраивается в `index.html`, удобно для встраивания в десктоп через WebView.

---

## 12. Частые задачи разработки

### Добавить новый следственный отдел

1. Отредактировать `porayonka-app/core/constants.py` → `INITIAL_DEPARTMENTS`.
2. При следующем запуске `load_departments()` в `core/data.py` автоматически добавит новый ID в существующий JSON.
3. Для React: отредактировать `INITIAL_DEPARTMENTS` в `src/App.tsx`.

### Изменить цвета

1. Python: `porayonka-app/core/constants.py` → `COLORS`.
2. React: `src/App.tsx` (цвета захардкожены в inline styles и Tailwind классах).
3. `assets/styles.py` — тема Flet Material.

### Добавить новый пункт в зональный шаблон по умолчанию

1. В `ui/zonal/zonal_tab.py` при создании новой коллекции добавить `template.items.append(...)`.
2. Или через UI: конструктор шаблонов → «Добавить пункт».

### Изменить список криминалистов по умолчанию

1. Отредактировать `core/zonal_constants.py` → `INITIAL_CRIMINALISTS_DATA`.
2. Удалить `%APPDATA%\porayonka\zonal_criminalists.json` для пересоздания.

### Добавить новый тип поля в форму криминалиста

1. Отредактировать `core/zonal_models.py` → `ReportItemType` (добавить enum-значение).
2. Добавить рендеринг в `ui/zonal/form_fields.py` → `build_item_field()`.
3. Обновить сохранение/загрузку в `core/zonal_data.py` (если требуется новый формат).

### Изменить внешний вид плашки криминалиста

1. Отредактировать `ui/zonal/criminalist_tile.py` → `create_criminalist_tile()`.
2. Для обновления одной плашки без перерисовки сетки используйте `rebuild_tile_content(tile, criminalist, ...)`.

### Добавить уведомление не сдавших (Telegram / Messenger MAX)

1. Заглушка уже есть: кнопка «Скопировать список не сдавших» в `ui/zonal/utils.py` → `build_non_submitters_text()`.
2. Для реальной интеграции: заменить копирование в буфер на вызов API/бота в том же файле.

### Добавить новый формат экспорта

1. Python: создать класс в `core/exporter.py` (для отделов) или `core/zonal_exporter.py` (для зональных).
2. Добавить кнопку/карточку в `ui/export_modal.py` или `ui/zonal/zonal_tab.py`.
3. React: добавить функцию экспорта в `src/App.tsx`.

---

## 13. Лицензия и контекст

- Лицензия: MIT (по README.md v1.0).
- Целевая аудитория: Следственный комитет РФ, Ростовская область.
- Версия: v2.0 DARK final (с зональными криминалистами).
- Разработчик: не указан в репозитории.

---

## 14. Что устарело и не использовать

- `porayonka-app/fix_flet.py` — удалён; все исправления `hint_style`/`ft.icons` уже встроены в код.
- `porayonka-app/README.md` — описывает v1.0, светлую тему, один Excel-экспорт, нет зональных.
- `porayonka-app/build_exe.bat` — нацелен на `flet pack` и `dist\Porayonka.exe`, не используется в v2.0.
- `porayonka-app/Порайонка.spec` — стандартный PyInstaller spec, но актуальная сборка описывается в `Команда для сборки портативной версии.txt` или `build_win7.bat`.
- Корневой `Porayonka_Win7.spec` — ссылается на временный файл версии, не используется.

---

*Этот файл создан для агентов, работающих с кодовой базой. При изменении архитектуры, структуры или зависимостей обновляйте этот документ.*
