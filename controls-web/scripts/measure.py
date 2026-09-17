#!/usr/bin/env python3
"""Измерения стенда controls-web (W01): >=30 повторов, p50/p95, фиксация среды.

Что измеряется: серверная часть по HTTP (полное время запроса и серверное время
из заголовка X-Process-Time-Ms). Браузерные метрики на реальном Win7 этим
скриптом НЕ заменяются — см. docs/measurement-protocol.md и
migration-web/reports/W01.md (статус Win7: ожидает проверки).

Запуск:  python scripts/measure.py --repeats 30 [--base http://127.0.0.1:8080]
Результат: measurements/W01-measurements-<UTC>.md и .json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_file(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="ignore") as handle:
            return handle.read().strip()
    except OSError:
        return ""


def git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(ROOT), capture_output=True, text=True, timeout=10
        )
        return out.stdout.strip() if out.returncode == 0 else "недоступно"
    except Exception:
        return "недоступно"


def environment(base: str) -> dict[str, object]:
    meminfo = read_file("/proc/meminfo")
    mem_total = ""
    mem_avail = ""
    for line in meminfo.splitlines():
        if line.startswith("MemTotal:"):
            mem_total = line.split(":", 1)[1].strip()
        if line.startswith("MemAvailable:"):
            mem_avail = line.split(":", 1)[1].strip()
    health: dict[str, object] = {}
    try:
        with urllib.request.urlopen(f"{base}/api/health", timeout=15) as response:
            health = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        health = {"status": "unavailable", "error": str(exc)}
    dist = ROOT / "frontend" / "dist"
    assets = {}
    if dist.is_dir():
        for path in sorted(dist.rglob("*")):
            if path.is_file():
                assets[str(path.relative_to(dist))] = {
                    "bytes": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest()[:16],
                }
    return {
        "дата_измерения_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "адрес_стенда": base,
        "ОС": f"{platform.system()} {platform.release()} ({read_file('/etc/os-release').splitlines()[0] if read_file('/etc/os-release') else ''})",
        "архитектура": platform.machine(),
        "ядер_cpu": os.cpu_count(),
        "ram_total": mem_total,
        "ram_available": mem_avail,
        "python": platform.python_version(),
        "postgresql": health.get("postgres_version"),
        "версия_приложения": health.get("app_version"),
        "статус_бд": health.get("database"),
        "git_sha": git_sha(),
        "сборка_frontend": assets,
        "диск": read_file("/proc/mounts").splitlines()[0] if read_file("/proc/mounts") else "",
    }


class MeasureError(RuntimeError):
    pass


def one_request(url: str, timeout: float = 30.0) -> tuple[float, float | None, int]:
    """(полное время мс, серверное время мс из заголовка, код ответа)."""
    started = time.perf_counter()
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read()
            status = response.status
            header = response.headers.get("X-Process-Time-Ms")
    except urllib.error.HTTPError as exc:
        status = exc.code
        header = exc.headers.get("X-Process-Time-Ms") if exc.headers else None
    except Exception as exc:  # noqa: BLE001
        raise MeasureError(f"{type(exc).__name__}: {exc}") from exc
    total_ms = (time.perf_counter() - started) * 1000
    server_ms = float(header) if header else None
    return total_ms, server_ms, status


def percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, int(round((pct / 100) * (len(ordered) - 1)))))
    return ordered[index]


def scenario(name: str, url: str, repeats: int, warmup: int, expect_status: int = 200) -> dict[str, object]:
    totals: list[float] = []
    servers: list[float] = []
    statuses: list[int] = []
    error: str | None = None
    for _ in range(warmup):
        try:
            one_request(url)
        except MeasureError as exc:
            error = str(exc)
    for _ in range(repeats):
        try:
            total_ms, server_ms, status = one_request(url)
        except MeasureError as exc:
            error = str(exc)
            continue
        totals.append(total_ms)
        statuses.append(status)
        if server_ms is not None:
            servers.append(server_ms)
    ok = bool(totals) and all(status == expect_status for status in statuses) and error is None
    result: dict[str, object] = {
        "сценарий": name,
        "url": url,
        "повторов": repeats,
        "успешных": len(totals),
        "коды_ответов": sorted(set(statuses)),
        "статус": "ok" if ok else "ошибка",
        "ошибка": error,
    }
    if totals:
        result.update(
            {
                "p50_мс": round(percentile(totals, 50), 2),
                "p95_мс": round(percentile(totals, 95), 2),
                "min_мс": round(min(totals), 2),
                "max_мс": round(max(totals), 2),
                "среднее_мс": round(statistics.fmean(totals), 2),
            }
        )
    if servers:
        result.update(
            {
                "сервер_p50_мс": round(percentile(servers, 50), 2),
                "сервер_p95_мс": round(percentile(servers, 95), 2),
            }
        )
    return result


def pdf_scenario(base: str, repeats: int) -> list[dict[str, object]]:
    """Загрузка и скачивание синтетического PDF с кириллическим именем."""
    out: list[dict[str, object]] = []
    sample_url = f"{base}/api/w01-test/sample-pdf?{urllib.parse.urlencode({'text': 'Синтетический документ для измерений W01'})}"
    try:
        with urllib.request.urlopen(sample_url, timeout=30) as response:
            payload = response.read()
    except Exception as exc:  # noqa: BLE001
        return [{"сценарий": "pdf_подготовка", "статус": "ошибка", "ошибка": str(exc)}]

    with urllib.request.urlopen(f"{base}/api/controls?page=1&page_size=1&include_archived=true", timeout=30) as response:
        control_id = json.loads(response.read().decode("utf-8"))["items"][0]["id"]

    boundary = "----w01measure"
    name = "измерение-синтетический-отчёт.pdf"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="control_id"\r\n\r\n{control_id}\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{name}"\r\n'
        "Content-Type: application/pdf\r\n\r\n"
    ).encode("utf-8") + payload + f"\r\n--{boundary}--\r\n".encode("utf-8")

    upload_times: list[float] = []
    attachment_id: str | None = None
    for _ in range(repeats):
        request = urllib.request.Request(
            f"{base}/api/w01-test/uploads",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload_out = json.loads(response.read().decode("utf-8"))
                attachment_id = payload_out["attachment"]["id"]
        except Exception as exc:  # noqa: BLE001
            return [{"сценарий": "pdf_загрузка", "статус": "ошибка", "ошибка": str(exc)}]
        upload_times.append((time.perf_counter() - started) * 1000)

    out.append(
        {
            "сценарий": "pdf_загрузка_кириллическое_имя",
            "повторов": repeats,
            "успешных": len(upload_times),
            "статус": "ok",
            "p50_мс": round(percentile(upload_times, 50), 2),
            "p95_мс": round(percentile(upload_times, 95), 2),
            "размер_файла_байт": len(payload),
        }
    )
    if attachment_id:
        out.append(
            scenario(
                "pdf_скачивание",
                f"{base}/api/w01-test/uploads/{attachment_id}/content",
                repeats,
                2,
            )
        )
        try:
            with urllib.request.urlopen(f"{base}/api/w01-test/uploads/{attachment_id}/content", timeout=30) as r:
                downloaded = r.read()
            out.append(
                {
                    "сценарий": "pdf_sha256_совпадает",
                    "статус": "ok" if hashlib.sha256(downloaded).hexdigest() == hashlib.sha256(payload).hexdigest() else "ошибка",
                    "sha256": hashlib.sha256(downloaded).hexdigest()[:16],
                }
            )
        except Exception as exc:  # noqa: BLE001
            out.append({"сценарий": "pdf_sha256_совпадает", "статус": "ошибка", "ошибка": str(exc)})
        request = urllib.request.Request(
            f"{base}/api/w01-test/uploads/{attachment_id}", method="DELETE"
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                out.append(
                    {
                        "сценарий": "pdf_удаление_после_измерений",
                        "код": response.status,
                        "статус": "ok" if response.status == 204 else "ошибка",
                    }
                )
        except Exception as exc:  # noqa: BLE001
            out.append({"сценарий": "pdf_удаление_после_измерений", "ошибка": str(exc), "статус": "ошибка"})
    return out


def markdown(report: dict[str, object]) -> str:
    lines = ["# Измерения стенда controls-web (W01)", "", "## Параметры среды", ""]
    for key, value in report["среда"].items():  # type: ignore[union-attr]
        if key == "сборка_frontend":
            lines.append(f"- **{key}**:")
            for name, meta in value.items():  # type: ignore[union-attr]
                lines.append(f"  - `{name}`: {meta['bytes']} байт, sha256 {meta['sha256']}")
        else:
            lines.append(f"- **{key}**: {value}")
    lines += ["", f"Повторов на сценарий: **{report['повторов']}** (warmup {report['warmup']}).", "", "## Результаты", "",
              "| Сценарий | Повторов | p50, мс | p95, мс | min | max | сервер p50 | сервер p95 | Статус |",
              "|---|---|---|---|---|---|---|---|---|"]
    for item in report["сценарии"]:  # type: ignore[union-attr]
        lines.append(
            "| {name} | {n} | {p50} | {p95} | {mn} | {mx} | {sp50} | {sp95} | {st} |".format(
                name=item.get("сценарий", ""),
                n=item.get("повторов", "—"),
                p50=item.get("p50_мс", "—"),
                p95=item.get("p95_мс", "—"),
                mn=item.get("min_мс", "—"),
                mx=item.get("max_мс", "—"),
                sp50=item.get("сервер_p50_мс", "—"),
                sp95=item.get("сервер_p95_мс", "—"),
                st=item.get("статус", ""),
            )
        )
    lines += ["", "## Примечания", "",
              "- Это серверные измерения на синтетических данных в песочнице Arena (2 ядра, ~3.9 ГБ RAM).",
              "- Они НЕ заменяют ручную проверку на настоящем Win7 с Яндекс Браузером 24.10.3.843 corp:",
              "  статус совместимости — «ожидает проверки».",
              "- «Сервер p50/p95» — время обработки внутри приложения (заголовок X-Process-Time-Ms),",
              "  полное время включает клиентскую часть и localhost-сеть.",
              ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Измерения стенда W01")
    parser.add_argument("--base", default=os.environ.get("CONTROLS_WEB_BASE", "http://127.0.0.1:8080"))
    parser.add_argument("--repeats", type=int, default=30)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--out-dir", default=str(ROOT / "measurements"))
    args = parser.parse_args(argv)

    base = args.base.rstrip("/")
    with urllib.request.urlopen(f"{base}/api/controls?page=1&page_size=50&include_archived=true", timeout=30) as response:
        first_page = json.loads(response.read().decode("utf-8"))
    card_id = first_page["items"][0]["id"]
    js_asset = next(
        (f"/assets/{p.name}" for p in sorted((ROOT / "frontend" / "dist" / "assets").glob("*.js"))), None
    )

    scenarios = [
        ("список_страница_1_50_строк", f"{base}/api/controls?page=1&page_size=50&include_archived=true"),
        ("список_страница_100", f"{base}/api/controls?page=100&page_size=50&include_archived=true"),
        ("список_страница_200_последняя", f"{base}/api/controls?page=200&page_size=50&include_archived=true"),
        ("поиск_по_номеру", f"{base}/api/controls?search={urllib.parse.quote('СТЕНД-000042')}&include_archived=true"),
        ("поиск_по_содержанию_кириллица", f"{base}/api/controls?search={urllib.parse.quote('сводку')}&include_archived=true"),
        ("поиск_широкий_термин", f"{base}/api/controls?search={urllib.parse.quote('СТЕНД-0001')}&include_archived=true"),
        ("карточка_записи", f"{base}/api/controls/{card_id}"),
        ("сводные_счётчики", f"{base}/api/meta/summary"),
        ("живость_health", f"{base}/api/health"),
        ("статика_index_html", f"{base}/"),
    ]
    if js_asset:
        scenarios.append(("статика_js_ассет", f"{base}{js_asset}"))

    results = [scenario(name, url, args.repeats, args.warmup) for name, url in scenarios]
    results += pdf_scenario(base, min(args.repeats, 10))

    report: dict[str, object] = {
        "среда": environment(base),
        "повторов": args.repeats,
        "warmup": args.warmup,
        "сценарии": results,
        "итог": (
            "ok"
            if all(item.get("статус") == "ok" for item in results if "статус" in item)
            else "есть ошибки"
        ),
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    json_path = out_dir / f"W01-measurements-{stamp}.json"
    md_path = out_dir / f"W01-measurements-{stamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    print(markdown(report))
    print(f"JSON: {json_path}\nMD:   {md_path}")
    return 0 if report["итог"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
