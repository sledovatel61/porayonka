"""Production-сборка фронтенда: отдача с того же origin, русский интерфейс,
отсутствие CDN/внешних шрифтов и новых browser API ниже согласованного минимума."""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Запрещённый минимум: сборка не должна использовать API/CSS новее согласованного
# порога (Chromium 109 / Firefox 115 — внешний потолок для Windows 7).
BANNED_JS = (
    "toSorted(", "toReversed(", "toSpliced(", "Object.groupBy", "Map.groupBy",
    "Promise.withResolvers", "structuredClone(", "Object.hasOwn(", "URL.canParse(",
    "navigator.share(", "showOpenFilePicker(", "Intl.Segmenter", "findLast(",
    "findLastIndex(", "Array.prototype.at",
)
BANNED_CSS = ("color-mix(", "@scope", "@container", "subgrid", "text-wrap", ":has(")


@pytest.fixture(scope="module")
def dist(settings) -> Path:
    path = settings.frontend_dist
    if path is None or not path.is_dir():
        pytest.skip("frontend/dist отсутствует: выполните `npm run build` в controls-web/frontend")
    return path


def test_index_served_from_same_origin(client: TestClient, dist: Path) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    html = response.text
    assert 'lang="ru"' in html
    assert "<title>Контроли" in html


def test_index_has_no_external_resources(client: TestClient, dist: Path) -> None:
    html = client.get("/").text
    assert not re.search(r"https?://", html), "в index.html не должно быть внешних ссылок (CDN/шрифты/телеметрия)"
    assets = re.findall(r'(?:src|href)="(/[^"]+)"', html)
    assert assets, "index.html должен ссылаться на локальные ассеты"
    for asset in assets:
        assert asset.startswith("/assets/"), asset
        served = client.get(asset)
        assert served.status_code == 200, asset
        assert (dist / asset.lstrip("/")).is_file()


def test_bundle_has_no_banned_apis(dist: Path) -> None:
    bundles = list(dist.glob("assets/*.js")) + list(dist.glob("assets/*.css"))
    assert bundles
    for bundle in bundles:
        text = bundle.read_text(encoding="utf-8", errors="ignore")
        for banned in BANNED_JS + BANNED_CSS:
            assert banned not in text, f"{bundle.name}: найдено запрещённое {banned!r}"


def test_bundle_has_no_external_network_references(dist: Path) -> None:
    allowed_prefixes = (
        "http://www.w3.org/",       # пространства имён XML/SVG: не сетевые запросы
        "https://react.dev/errors", # текст сообщений React: не запрашивается
    )
    for bundle in dist.glob("assets/*.js"):
        text = bundle.read_text(encoding="utf-8", errors="ignore")
        for url in set(re.findall(r"https?://[A-Za-z0-9./_-]+", text)):
            assert url.startswith(allowed_prefixes), f"{bundle.name}: внешняя ссылка {url}"


def test_russian_ui_strings_present_in_bundle(dist: Path) -> None:
    text = "".join(bundle.read_text(encoding="utf-8", errors="ignore") for bundle in dist.glob("assets/*.js"))
    for phrase in ("Без срока", "Просрочено", "Показано", "Технический стенд W01", "только чтение"):
        assert phrase in text, f"в сборке нет русской строки {phrase!r}"


def test_no_sourcemap_and_no_dev_artifacts(dist: Path) -> None:
    assert not list(dist.glob("**/*.map")), "production-сборка не должна содержать sourcemap"
    text = "".join(p.read_text(encoding="utf-8", errors="ignore") for p in dist.glob("assets/*.js"))
    assert "localhost:5173" not in text
    assert "127.0.0.1:8080" not in text, "frontend обязан обращаться по относительным путям того же origin"


def test_api_calls_use_relative_paths(dist: Path) -> None:
    text = "".join(p.read_text(encoding="utf-8", errors="ignore") for p in dist.glob("assets/*.js"))
    assert '"/api/controls' in text or "/api/controls?" in text
    assert "http://localhost" not in text
