# CI стенда controls-web (W01)

Файл `controls-web-w01.yml` — готовый workflow первичного CI: установка из lock,
backend-тесты на PostgreSQL 16, frontend type-check, production build, smoke HTTP.

## Почему он лежит здесь, а не в `.github/workflows/`

Публикация из этой сессии отклонена GitHub: токен приложения не имеет права
`workflows` —

```
! [remote rejected] arena/01a0a90c-porayonka (refusing to allow a GitHub App to
  create or update workflow `.github/workflows/controls-web-w01.yml` without
  `workflows` permission)
```

Чтобы не терять содержимое, workflow закоммичен в каталоге проекта. Для включения CI:

```bash
mkdir -p .github/workflows
cp controls-web/ci/controls-web-w01.yml .github/workflows/controls-web-w01.yml
git add .github/workflows/controls-web-w01.yml
git commit -m "CI: включить первичный workflow стенда controls-web (W01)"
git push
```

Коммит должен делать участник (или токен) с правом `workflows`.

## Что делает workflow

| Job | Зависит от | Шаги |
|---|---|---|
| `frontend` | — | Node 22, `npm ci` из lock, `npm run typecheck`, `npm run build`, артефакт `dist` |
| `backend` | `frontend` | Python 3.11, сервис-контейнер `postgres:16` (trust только внутри job), `pip install -r requirements.lock.txt`, скачивание артефакта `dist`, `pytest -v` (64 теста) |
| `smoke` | `backend` | `postgres:16`, установка из lock, наполнение 10 000 записей, `app.seed --verify`, запуск uvicorn, `scripts/smoke_http.sh` (49 проверок), `measure.py --repeats 5` |

Секреты репозитория не используются: тестовая БД поднимается сервис-контейнером
с trust-аутентификацией, действующей только внутри job. Триггеры — изменения в
`controls-web/**` и в самом файле workflow, плюс ручной запуск.

## Локальный эквивалент (без GitHub Actions)

```bash
bash scripts/provision_stand.sh                                  # развёртывание стенда
bash scripts/run_stand.sh &                                      # запуск
bash scripts/smoke_http.sh                                       # 49 проверок
(cd backend && .venv/bin/python -m pytest)                       # 64 теста
(cd frontend && npm run typecheck && npm run build)              # типы и сборка
backend/.venv/bin/python scripts/measure.py --repeats 30         # p50/p95
```
