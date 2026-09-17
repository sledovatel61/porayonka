"""Настройки стенда controls-web (W01). Секреты читаются только из окружения."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_CONTROLS_WEB = BACKEND_DIR.parent


def _bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "да"}


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    try:
        return int(raw) if raw not in (None, "") else default
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    dsn: str
    host: str
    port: int
    frontend_dist: Path | None
    uploads_dir: Path
    enable_test_endpoints: bool
    auto_schema: bool
    debug: bool
    page_size_default: int = 50
    page_size_max: int = 200
    upload_max_bytes: int = 20 * 1024 * 1024

    @property
    def public_uploads(self) -> bool:
        """Раздача вложений вне стендовых endpoint'ов запрещена (см. README)."""
        return False


def load_settings() -> Settings:
    dist_env = os.environ.get("CONTROLS_WEB_FRONTEND_DIST")
    if dist_env:
        dist: Path | None = Path(dist_env)
    else:
        candidate = REPO_CONTROLS_WEB / "frontend" / "dist"
        dist = candidate if candidate.is_dir() else None
    uploads = Path(os.environ.get("CONTROLS_WEB_UPLOADS") or (REPO_CONTROLS_WEB / "uploads"))
    return Settings(
        dsn=os.environ.get("CONTROLS_WEB_DSN")
        or "postgresql://controls_web@127.0.0.1:5433/controls_web_w01",
        host=os.environ.get("CONTROLS_WEB_HOST") or "0.0.0.0",
        port=_int("CONTROLS_WEB_PORT", 8080),
        frontend_dist=dist,
        uploads_dir=uploads,
        enable_test_endpoints=_bool("CONTROLS_WEB_ENABLE_TEST_ENDPOINTS", True),
        auto_schema=_bool("CONTROLS_WEB_AUTO_SCHEMA", True),
        debug=_bool("CONTROLS_WEB_DEBUG", False),
    )
