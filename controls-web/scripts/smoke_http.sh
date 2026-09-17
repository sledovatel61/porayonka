#!/usr/bin/env bash
# Smoke-проверки стенда controls-web (W01) по HTTP.
# Основание: промпт W01, раздел «Проверки и доказательства».
# Требуется запущенный сервер: scripts/run_stand.sh (или uvicorn app.main:app).
# Все данные синтетические; выход: 0 — все проверки прошли, 1 — есть провалы.
set -uo pipefail

BASE="${CONTROLS_WEB_BASE:-http://127.0.0.1:8080}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PY="$HERE/backend/.venv/bin/python"
if [[ -z "${CONTROLS_WEB_PYTHON:-}" ]]; then
  if [[ -x "$VENV_PY" ]]; then PYTHON="$VENV_PY"; else PYTHON="python3"; fi
else
  PYTHON="$CONTROLS_WEB_PYTHON"
fi
FAILED=0
CHECKS=0

check() { # имя ожидаемое фактическое
  CHECKS=$((CHECKS + 1))
  if [[ "$2" == "$3" ]]; then
    printf 'ok    %-56s %s\n' "$1" "$3"
  else
    printf 'FAIL  %-56s ожидали [%s], получили [%s]\n' "$1" "$2" "$3"
    FAILED=$((FAILED + 1))
  fi
}

code() { curl -sS -o /dev/null -w '%{http_code}' "$@"; }

json_get() { # путь+query, python-выражение над obj
  curl -sS "$BASE$1" | "$PYTHON" -c "
import json, sys
obj = json.load(sys.stdin)
print($2)
"
}

urlq() { "$PYTHON" -c "import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1]))" "$1"; }

echo "=== Smoke W01: $BASE ==="

# --- живость и настоящая БД ---
check "GET /api/health -> 200" "200" "$(code "$BASE/api/health")"
check "HEAD /api/health -> 200 (пригодно для мониторинга)" "200" "$(curl -sS -o /dev/null -w '%{http_code}' -I "$BASE/api/health")"
check "health.status == ok" "ok" "$(json_get /api/health "obj['status']")"
check "health.database == ok" "ok" "$(json_get /api/health "obj['database']")"
PGVER="$(json_get /api/health "obj['postgres_version'] or ''")"
if [[ "$PGVER" =~ ^1[4-9]\. || "$PGVER" =~ ^[2-9][0-9]\. ]]; then PGOK=True; else PGOK=False; fi
check "PostgreSQL >= 14 (не SQLite), версия: $PGVER" "True" "$PGOK"

# --- объём данных ---
check "GET /api/meta/summary -> 200" "200" "$(code "$BASE/api/meta/summary")"
check "summary.total == 10000 (всего записей)" "10000" "$(json_get /api/meta/summary "obj['total']")"
ACTIVE="$(json_get /api/meta/summary "obj['active']")"
check "summary.active < total (архив исключён из счётчика активных)" "True" \
  "$("$PYTHON" -c "print($ACTIVE < 10000 and $ACTIVE > 0)")"

# --- пагинация по 50 ---
ALL="/api/controls?page=1&page_size=50&include_archived=true"
check "GET список (все записи) -> 200" "200" "$(code "$BASE$ALL")"
check "строк на странице == 50" "50" "$(json_get "$ALL" "len(obj['items'])")"
check "total == 10000" "10000" "$(json_get "$ALL" "obj['total']")"
check "pages == 200" "200" "$(json_get "$ALL" "obj['pages']")"
check "страница 200 содержит 50 строк" "50" \
  "$(json_get '/api/controls?page=200&page_size=50&include_archived=true' "len(obj['items'])")"
check "страница 201 пустая (за границей)" "0" \
  "$(json_get '/api/controls?page=201&page_size=50&include_archived=true' "len(obj['items'])")"
check "по умолчанию архив скрыт (total < 10000)" "True" \
  "$("$PYTHON" -c "print($(json_get '/api/controls?page=1&page_size=50' "obj['total']") < 10000)")"
check "id на страницах 1 и 2 не пересекаются" "0" \
  "$("$PYTHON" - <<PY
import json, urllib.request
def ids(p):
    with urllib.request.urlopen("$BASE/api/controls?page=%d&page_size=50&include_archived=true" % p) as r:
        return {i["id"] for i in json.load(r)["items"]}
print(len(ids(1) & ids(2)))
PY
)"
check "page=0 -> 422" "422" "$(code "$BASE/api/controls?page=0")"
check "page_size=0 -> 422" "422" "$(code "$BASE/api/controls?page_size=0")"
check "page_size=10000 -> 422 (все записи не отдаются)" "422" "$(code "$BASE/api/controls?page_size=10000")"

# --- поиск ---
check "поиск по номеру СТЕНД-000042 -> 1 запись" "1" \
  "$(json_get "/api/controls?search=$(urlq 'СТЕНД-000042')&include_archived=true" "obj['total']")"
check "поиск по кириллическому термину содержания -> >0" "True" \
  "$("$PYTHON" -c "print($(json_get "/api/controls?search=$(urlq 'сводку')&include_archived=true" "obj['total']") > 0)")"
check "поиск спецсимволов LIKE экранируется (не все записи)" "True" \
  "$("$PYTHON" -c "print($(json_get "/api/controls?search=$(urlq '%')&include_archived=true" "obj['total']") < 10000)")"
check "поиск несуществующего -> 0" "0" \
  "$(json_get "/api/controls?search=$(urlq 'zzz-нет-такого-термина')" "obj['total']")"

# --- карточка ---
FIRST_ID="$(json_get "$ALL" "obj['items'][0]['id']")"
check "карточка -> 200" "200" "$(code "$BASE/api/controls/$FIRST_ID")"
check "карточка содержит кириллицу" "True" \
  "$(json_get "/api/controls/$FIRST_ID" "any(0x400 <= ord(c) <= 0x4FF for c in obj['content'] + obj['executor'] + obj['initiator'])")"
check "карточка отдаёт пункты упорядоченно" "True" \
  "$(json_get "/api/controls/$FIRST_ID" "obj['tasks'] == sorted(obj['tasks'], key=lambda t: t['position'])")"
check "неизвестный UUID -> 404" "404" "$(code "$BASE/api/controls/00000000-0000-5000-8000-000000000000")"
check "некорректный id -> 422" "422" "$(code "$BASE/api/controls/не-uuid")"

# --- production-сборка с того же origin ---
check "GET / -> 200" "200" "$(code "$BASE/")"
check "index.html содержит lang=\"ru\"" "True" \
  "$(curl -sS "$BASE/" | grep -c 'lang="ru"' | "$PYTHON" -c 'import sys; print(int(sys.stdin.read()) > 0)')"
check "в index.html нет внешних http(s)-ссылок" "0" "$(curl -sS "$BASE/" | grep -oE 'https?://' | wc -l | tr -d ' ')"
check "CSS-ассет отдаётся с того же origin -> 200" "200" \
  "$(code "$BASE$(curl -sS "$BASE/" | grep -oE '/assets/[A-Za-z0-9._-]+\.css' | head -1)")"

# --- временные стендовые endpoints и PDF с кириллицей ---
check "стендовый info -> 200" "200" "$(code "$BASE/api/w01-test/info")"
check "sample-pdf -> 200" "200" "$(code "$BASE/api/w01-test/sample-pdf")"

TMP="$(mktemp -d)"
curl -sS -o "$TMP/sample.pdf" "$BASE/api/w01-test/sample-pdf"
check "sample-pdf начинается с %PDF" "%PDF" "$(head -c 4 "$TMP/sample.pdf")"
check "в PDF встроен кириллический текст (шрифт)" "True" \
  "$("$PYTHON" - "$TMP/sample.pdf" <<'PY'
import sys
from pypdf import PdfReader
text = "".join((page.extract_text() or "") for page in PdfReader(sys.argv[1]).pages)
print(any("\u0400" <= ch <= "\u04ff" for ch in text))
PY
)"

CYR_NAME="синтетический-отчёт-стенда.pdf"
cp "$TMP/sample.pdf" "$TMP/$CYR_NAME"
UP_CODE="$(curl -sS -o "$TMP/up.json" -w '%{http_code}' \
  -F "file=@$TMP/$CYR_NAME;type=application/pdf" -F "control_id=$FIRST_ID" "$BASE/api/w01-test/uploads")"
check "загрузка PDF с кириллическим именем -> 201" "201" "$UP_CODE"
check "имя файла сохранено с кириллицей" "$CYR_NAME" \
  "$("$PYTHON" -c "import json; print(json.load(open('$TMP/up.json'))['attachment']['file_name'])")"
ATT_ID="$("$PYTHON" -c "import json; print(json.load(open('$TMP/up.json'))['attachment']['id'])")"
check "скачивание -> 200" "200" "$(code "$BASE/api/w01-test/uploads/$ATT_ID/content")"
curl -sS -o "$TMP/downloaded.pdf" "$BASE/api/w01-test/uploads/$ATT_ID/content"
check "sha256 загруженного и скачанного совпадают" \
  "$(sha256sum "$TMP/sample.pdf" | cut -d' ' -f1)" "$(sha256sum "$TMP/downloaded.pdf" | cut -d' ' -f1)"
DISPOSITION="$(curl -sS -D - -o /dev/null "$BASE/api/w01-test/uploads/$ATT_ID/content" | tr -d '\r' | grep -i '^content-disposition:')"
check "Content-Disposition содержит filename* (RFC 5987)" "True" \
  "$(printf '%s' "$DISPOSITION" | grep -ic "filename\*=utf-8''" | "$PYTHON" -c 'import sys; print(int(sys.stdin.read()) > 0)')"
check "имя файла в заголовке percent-encoded (кириллица)" "True" \
  "$(printf '%s' "$DISPOSITION" | grep -c '%D' | "$PYTHON" -c 'import sys; print(int(sys.stdin.read()) > 0)')"
# другой валидный PDF под тем же именем: правило legacy «тот же путь + другое содержимое» -> 409
curl -sS -o "$TMP/other.pdf" "$BASE/api/w01-test/sample-pdf?text=$(urlq 'Другой синтетический текст для проверки правила дублей')"
cp "$TMP/other.pdf" "$TMP/$CYR_NAME"
check "то же имя + другое содержимое PDF -> 409" "409" \
  "$(curl -sS -o /dev/null -w '%{http_code}' -F "file=@$TMP/$CYR_NAME;type=application/pdf" \
     -F "control_id=$FIRST_ID" "$BASE/api/w01-test/uploads")"
check "повторная загрузка того же файла -> 201 (идемпотентно)" "201" \
  "$(cp "$TMP/sample.pdf" "$TMP/$CYR_NAME"; curl -sS -o /dev/null -w '%{http_code}' \
     -F "file=@$TMP/$CYR_NAME;type=application/pdf" -F "control_id=$FIRST_ID" "$BASE/api/w01-test/uploads")"
check "загрузка не-PDF (тип text/plain) -> 415" "415" \
  "$(printf 'не pdf' > "$TMP/bad.txt"; curl -sS -o /dev/null -w '%{http_code}' \
     -F "file=@$TMP/bad.txt;type=text/plain" "$BASE/api/w01-test/uploads")"
check "заявлен PDF, но содержимое не PDF -> 415" "415" \
  "$(printf 'не pdf' > "$TMP/fake.pdf"; curl -sS -o /dev/null -w '%{http_code}' \
     -F "file=@$TMP/fake.pdf;type=application/pdf" "$BASE/api/w01-test/uploads")"
check "вложение видно в карточке записи" "True" \
  "$(json_get "/api/controls/$FIRST_ID" "any(a['id'] == '$ATT_ID' for a in obj['attachments'])")"
check "каталог загрузок не раздаётся статикой -> 404" "404" "$(code "$BASE/uploads/$FIRST_ID/$CYR_NAME")"
check "удаление вложения -> 204" "204" "$(curl -sS -o /dev/null -w '%{http_code}' -X DELETE "$BASE/api/w01-test/uploads/$ATT_ID")"
rm -rf "$TMP"

echo "=== Итог: проверок $CHECKS, провалов $FAILED ==="
[[ "$FAILED" -eq 0 ]] || exit 1
