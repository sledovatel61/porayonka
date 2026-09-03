# tools/make_web_manifest.py
# Раунд 38 (задача 3.2): манифест Win7 Web-сборки — фиксирует версию Python
# (и разрядность), версии Flet/FastAPI/Starlette/Pydantic/PyInstaller и
# SHA256 итогового exe. Печатается в консоль сборки и сохраняется рядом с
# дистрибутивом (manifest_win7_web.txt).
#
# Использование (из build-скриптов):
#   python tools\make_web_manifest.py --venv .venv-win7-web ^
#       --exe dist_web\Порайонка_Пользователь_Web.exe ^
#       --out dist_web\manifest_win7_web.txt
#
# Возвращает exit code 1, если в профиле venv обнаружен pydantic_core
# (Rust-расширение, несовместимое с Windows 7) — такая сборка заведомо
# битая и должна остановиться.
import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime

TRACKED = ["flet", "flet-core", "flet-runtime", "fastapi", "starlette",
           "pydantic", "uvicorn", "websockets", "anyio", "typing_extensions",
           "pyinstaller"]
# Имя импортируемого модуля, наличие которого НЕДОПУСТИМО в профиле Win7.
FORBIDDEN_MODULES = ["pydantic_core"]
# Допустимая ветка pydantic для Win7 (v1 — чистый Cython C, без Rust).
PYDANTIC_ALLOWED_MAJOR = (1,)


def _sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _venv_python(venv: str) -> str:
    if os.name == "nt":
        cand = os.path.join(venv, "Scripts", "python.exe")
    else:
        cand = os.path.join(venv, "bin", "python")
    return cand if os.path.exists(cand) else sys.executable


def collect_manifest(venv_python: str, exe_path: str) -> dict:
    code = (
        "import sys, json, platform\n"
        "try:\n"
        "    from importlib.metadata import version, PackageNotFoundError\n"
        "except ImportError:\n"
        "    from importlib_metadata import version, PackageNotFoundError\n"
        "pkgs = {}\n"
        f"for name in {TRACKED!r}:\n"
        "    try:\n"
        "        pkgs[name] = version(name)\n"
        "    except PackageNotFoundError:\n"
        "        pkgs[name] = None\n"
        "mods = {}\n"
        "import importlib.util\n"
        f"for m in {FORBIDDEN_MODULES!r}:\n"
        "    mods[m] = importlib.util.find_spec(m) is not None\n"
        "print(json.dumps({\n"
        "    'python': sys.version,\n"
        "    'python_bits': platform.architecture()[0],\n"
        "    'packages': pkgs, 'forbidden': mods}))\n"
    )
    out = subprocess.check_output([venv_python, "-c", code],
                                  text=True, stderr=subprocess.STDOUT)
    probe = json.loads(out.strip().splitlines()[-1])
    exe_sha = _sha256_of(exe_path) if os.path.exists(exe_path) else None
    return {
        "created_at": datetime.now().isoformat(),
        "builder_python": sys.version.replace("\n", " "),
        "profile_python": probe["python"],
        "profile_bits": probe["python_bits"],
        "packages": probe["packages"],
        "forbidden_present": probe["forbidden"],
        "exe": os.path.basename(exe_path),
        "exe_sha256": exe_sha,
        "profile": "requirements-win7-web.txt",
    }


def manifest_text(m: dict) -> str:
    lines = [
        "Porayonka Win7 Web build manifest",
        f"created_at: {m['created_at']}",
        f"builder python: {m['builder_python']}",
        f"profile python: {m['profile_python']}",
        f"profile bits: {m['profile_bits']}",
        f"profile file: {m['profile']}",
        "packages:",
    ]
    for k, v in m["packages"].items():
        lines.append(f"  {k}: {v}")
    lines.append(f"forbidden modules present: {m['forbidden_present']}")
    lines.append(f"exe: {m['exe']}")
    lines.append(f"exe sha256: {m['exe_sha256']}")
    return "\n".join(lines) + "\n"


def check_profile(m: dict) -> list:
    """Ошибки профиля Win7-сборки (пустой список — профиль исправен)."""
    problems = []
    for mod, present in (m.get("forbidden_present") or {}).items():
        if present:
            problems.append(f"v profile est zapreshchennyy modul: {mod}")
    pk = m.get("packages") or {}
    pyd = pk.get("pydantic") or ""
    try:
        if pyd and int(pyd.split(".")[0]) not in PYDANTIC_ALLOWED_MAJOR:
            problems.append(
                f"pydantic {pyd} - dlya Win7 dopustima tolko v1 "
                f"(bez pydantic-core/Rust)")
    except (ValueError, TypeError):
        problems.append(f"ne udalos proverit versiyu pydantic: {pyd}")
    if not m.get("exe_sha256"):
        problems.append("exe ne nayden - sha256 ne poschitan")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--venv", default=".venv-win7-web")
    ap.add_argument("--exe", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    vpy = _venv_python(args.venv)
    m = collect_manifest(vpy, args.exe)
    text = manifest_text(m)
    print(text)
    problems = check_profile(m)
    if problems:
        for p in problems:
            print(f"[MANIFEST-ERROR] {p}")
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"[MANIFEST] written: {args.out}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
