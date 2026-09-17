# controls-web — технический стенд этапа W01

Браузерный стенд для проверки выбранной платформы **до** переноса функций и рабочих данных.
Это не рабочая система и не начало миграции: данные синтетические, интерфейс только для чтения,
авторизации и бизнес-операций нет. План проекта — в `../migration-web/`.

- Этап: **W01** (минимальная работающая версия и испытание Win7).
- Стек: Python 3.11 + FastAPI + **PostgreSQL ≥ 14** (проверено на 16.14), React 19 + TypeScript 5.9 + Vite 7.
- Статус совместимости с Windows 7: **ожидает проверки** (см. `docs/win7-checklist.md`).
- Ограничения стенда: `docs/stand-limitations.md`. Браузерный минимум: `docs/browser-target.md`.

## Состав

```
controls-web/
├── AGENTS.md                 правила работы с новой системой (для агентов и разработчиков)
├── README.md                 этот файл: воспроизводимый запуск и ограничения
├── backend/
│   ├── requirements.txt      runtime-зависимости (зафиксированные версии)
│   ├── requirements-dev.txt  зависимости тестов и инструментов
│   ├── requirements.lock.txt lock (pip freeze) — из него ставит CI
│   ├── pytest.ini
│   ├── app/                  schema.sql, config, db, repo, models, seed, main, w01test, sample_pdf
│   └── tests/                64 автоматических теста (настоящий PostgreSQL, не SQLite)
├── frontend/
│   ├── package.json, package-lock.json, tsconfig*.json, vite.config.ts, index.html
│   └── src/                  React-приложение: таблица, пагинация, поиск, карточка, статус-строка
├── tools/pg-stand/           бинарники PostgreSQL для песочницы (вариант B), см. ниже
├── scripts/                  provision_stand.sh, run_stand.sh, smoke_http.sh, measure.py
├── docs/                     browser-target, stand-limitations, win7-checklist, measurement-protocol,
│                             measurements-w01-sandbox.md/.json (фактические результаты)
└── measurements/             локальные результаты измерений (в git не попадают)
```

## Быстрый запуск в песочнице Arena (вариант B)

В песочнице недоступны apt-зеркала Debian (http и https) и Docker, поэтому настоящий PostgreSQL 16.14
берётся из npm-пакета `@embedded-postgres/linux-x64` (версия зафиксирована в `tools/pg-stand/package.json`).
Это настоящий сервер PostgreSQL, а не замена на SQLite.

```bash
bash scripts/provision_stand.sh        # СУБД + зависимости из lock + сборка + 10 000 записей
bash scripts/run_stand.sh              # API и production-статика с одного origin: http://0.0.0.0:8080
```

Проверки (ожидаемые результаты фактически получены 17.09.2026):

```bash
bash scripts/smoke_http.sh                                        # 49 проверок, 0 провалов, exit 0
(cd backend && .venv/bin/python -m pytest)                        # 64 passed, exit 0
(cd backend && .venv/bin/python -m app.seed --verify)             # "ok": true, exit 0
backend/.venv/bin/python scripts/measure.py --repeats 30          # p50/p95, exit 0
bash tools/pg-stand/pg_stand.sh stop                              # остановить СУБД
```

## Запуск на сервере (вариант A/C: Debian/Ubuntu + PostgreSQL из пакета ОС)

```bash
# 1. PostgreSQL (версия — по согласованию, требуется >= 14)
sudo apt-get update && sudo apt-get install -y postgresql-16 postgresql-client-16
sudo -u postgres psql -c "SELECT version();"
sudo -u postgres createuser --pwprompt controls_web           # пароль вводите, не храните в git
sudo -u postgres createdb -O controls_web controls_web_w01
sudo -u postgres psql -c "ALTER SYSTEM SET timezone = 'Europe/Moscow';" && sudo systemctl reload postgresql
systemctl is-enabled postgresql

# 2. Backend
cd controls-web/backend
python3 -m venv .venv && .venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.lock.txt

# 3. Frontend (Node.js >= 20.19)
cd ../frontend && npm ci && npm run build

# 4. Наполнение и запуск
# пароль БД в git и в отчёты не попадает: передаётся через окружение или ~/.pgpass
export PGPASSWORD="$(cat /etc/controls-web/db-password)"     # файл вне репозитория, права 600
export CONTROLS_WEB_DSN="postgresql://controls_web@127.0.0.1:5432/controls_web_w01"
cd ../backend && .venv/bin/python -m app.seed --reset --count 10000 --seed 20260917
CONTROLS_WEB_ENABLE_TEST_ENDPOINTS=0 bash ../scripts/run_stand.sh   # без временных endpoints
```

Production-запуск (число работников, systemd-служба, HTTPS, автозапуск, пул соединений, резервные копии)
— задача этапа **W07**; в W01 это намеренно не делается.

## Конфигурация (переменные окружения)

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `CONTROLS_WEB_DSN` | `postgresql://controls_web@127.0.0.1:5433/controls_web_w01` | DSN PostgreSQL. Пароль — только из окружения |
| `CONTROLS_WEB_HOST` / `CONTROLS_WEB_PORT` | `0.0.0.0` / `8080` | адрес стенда |
| `CONTROLS_WEB_FRONTEND_DIST` | `../frontend/dist` (если существует) | каталог production-сборки |
| `CONTROLS_WEB_UPLOADS` | `../uploads` | каталог вложений стенда (в git не попадает, статикой не раздаётся) |
| `CONTROLS_WEB_ENABLE_TEST_ENDPOINTS` | `1` | временные endpoints W01 + `/api/docs`; для показа владельцу ставить `0` |
| `CONTROLS_WEB_AUTO_SCHEMA` | `1` | идемпотентно применить `schema.sql` при старте |
| `CONTROLS_WEB_DEBUG` | `0` | debug-режим FastAPI; в показе и в production — `0` |
| `CONTROLS_WEB_PDF_FONT` | автопоиск DejaVu/Liberation/Arial | TTF с кириллицей для генератора PDF |
| `CONTROLS_WEB_TEST_DB` | `controls_web_w01_test` | отдельная база для тестов |

## API стенда

| Метод и путь | Назначение | Примечание |
|---|---|---|
| `GET /api/health` (GET, HEAD) | живость приложения и БД | возвращает версию PostgreSQL |
| `GET /api/meta/summary` | счётчики для шапки | всего / в работе / исполнено / просрочено / в архиве |
| `GET /api/controls?page=&page_size=&search=&include_archived=` | постраничный список | `page_size` по умолчанию 50, максимум 200; все 10 000 записей не отдаются |
| `GET /api/controls/{id}` | карточка (только чтение) | 404 — нет записи, 422 — не UUID |
| `GET /` | production-сборка интерфейса | тот же origin, внешних ресурсов нет |
| `GET /api/w01-test/info` | справка о временных endpoints | **временный** |
| `GET /api/w01-test/sample-pdf` | синтетический PDF с кириллицей | **временный** |
| `POST /api/w01-test/uploads` | загрузка PDF (multipart) | **временный**; 415/422/409/413 |
| `GET /api/w01-test/uploads/{id}` и `/content` | метаданные и скачивание | **временный** |
| `DELETE /api/w01-test/uploads/{id}` | уборка стенда | **временный** |

Временные endpoints `/api/w01-test/*` должны быть удалены или закрыты до передачи W02. Публичной раздачи
каталога загрузок нет: файлы доступны только по идентификатору вложения через эти endpoints.

## Совместимость зафиксированных версий

| Пакет | Версия | Обоснование |
|---|---|---|
| fastapi | 0.141.1 | текущая стабильная; pydantic v2; Python 3.11 поддерживается |
| uvicorn | 0.53.0 | ASGI-сервер, работает без uvloop-зависимостей |
| psycopg[binary] | 3.3.5 | драйвер PostgreSQL 3.x, manylinux-колесо, без сборки на сервере |
| python-multipart | 0.0.32 | требуется FastAPI для загрузки файлов |
| pytest / httpx | 9.1.1 / 0.28.1 | тесты и TestClient |
| reportlab | 5.0.1 | только генератор синтетического PDF (инструмент стенда) |
| pypdf | 6.1.1 | только проверка кириллицы внутри PDF в тестах |
| react / react-dom | 19.3.0 | без тяжёлой UI-библиотеки; интерфейс на обычном CSS |
| typescript | 5.9.3 | стабильная ветка 5.x (не 7.x) для предсказуемой сборки |
| vite | 7.3.6 | требует Node ≥ 20.19/22.12; `build.target` задан явно |
| @vitejs/plugin-react | 5.2.0 | peer-зависимость: vite ^4…^7 |
| @embedded-postgres/linux-x64 | 16.14.0-beta.17 | только песочница (PostgreSQL 16.14): apt и Docker недоступны |

Браузерный минимум и запрещённые API — в `docs/browser-target.md`; список проверяется тестом
`backend/tests/test_frontend_build.py`.

## Первичный CI

Workflow подготовлен и лежит в **`ci/controls-web-w01.yml`** (три job'а: frontend → backend на
PostgreSQL 16 → smoke HTTP; установка из lock, секретов не требует). В `.github/workflows/` он
не опубликован: токен GitHub-приложения в этой сессии не имеет права `workflows`, push отклонён
(`refusing to allow a GitHub App to create or update workflow … without workflows permission`).
Инструкция по включению — в `ci/README.md`; копирует и пушит участник с правом `workflows`.
Локальный эквивалент всех шагов CI приведён там же.

## Данные стенда

Наполнение детерминированное: `--seed 20260917 --count 10000` даёт 10 000 контролей и 14 925 пунктов,
digest `57f798ebe0739224b1715f829d28e34e612a5d87b7ea7ff14b113ed1b9ddcb20` (сверяется с БД таблицей `seed_meta`).
Все ФИО, организации, номера (`СТЕНД-000001`…) и тексты вымышлены; реальные рабочие данные, сканы,
UNC-адреса и настоящие номера в стенд не загружались.

## Проверено фактически (17.09.2026, песочница Arena)

| Проверка | Результат |
|---|---|
| Чистая установка из lock (`pip install -r requirements.lock.txt`, `npm ci`) | выполнено |
| Подключение к настоящему PostgreSQL 16.14 (не SQLite) | выполнено, `database: ok` |
| Повторяемое наполнение 10 000 записей | выполнено, `verify.ok = true` |
| Страницы по 50, 200 страниц, полный проход без потерь и повторов | выполнено (тест `slow`) |
| Поиск по кириллице и экранирование LIKE | выполнено |
| Production-сборка и отдача с того же origin | выполнено (238 КБ JS / 75 КБ gzip) |
| Кириллица в карточке и внутри синтетического PDF | выполнено (извлечение текста pypdf) |
| Загрузка и скачивание PDF, sha256 совпадает, дубли отклоняются | выполнено |
| Smoke HTTP | 49 проверок, 0 провалов |
| Тесты backend | 64 passed |
| Измерения 30 повторов, p50/p95 | выполнено, `docs/measurements-w01-sandbox.md` |
| Ручная проверка на настоящем Win7 | **не выполнено — ожидает проверки** |
