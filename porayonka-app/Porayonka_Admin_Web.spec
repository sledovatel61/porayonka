# -*- mode: python ; coding: utf-8 -*-
# Раунд 37 (задача 3): PyInstaller spec — WEB-обёртка для Windows 7,
# АДМИНСКАЯ редакция (импорт/редактирование контролей через браузер).
#
# Сборка:  build_admin_web_win7.bat
#          (pyinstaller Porayonka_Admin_Web.spec --noconfirm --clean)
# Результат: dist\Порайонка_Админ_Web.exe + dist\edition.json
# {"role": "admin"} + dist\start_web_win7.bat
#
# Вход — main_web.py: ставит PORAYONKA_WEB=1 (без трея/автозапуска) и
# запускает main.py --web --host 0.0.0.0 --port 8555 → локальный web-сервер
# + автооткрытие браузера (Win7: Chrome/Firefox; нативный клиент Flet на
# Win7 не работает). Роль НЕ задаётся env с раунда 37 — берётся из
# edition.json рядом с exe / встроенного в бандл (build_edition).
import os

_flet_hooks = []
_flet_datas = []
try:
    import flet as _flet_pkg
    _d = os.path.join(os.path.dirname(_flet_pkg.__file__), "__pyinstaller")
    if os.path.isdir(_d):
        _flet_hooks = [_d]
    # Раунд 27: web-режим Flet требует статические файлы клиента (flet/web),
    # иначе frozen exe падает "Web root path not found: .../flet/web".
    # Добавляем их в datas + скрытые импорты fastapi/uvicorn.
    _flet_root = os.path.dirname(_flet_pkg.__file__)
    _flet_web = os.path.join(_flet_root, "web")
    if os.path.isdir(_flet_web):
        _flet_datas.append((_flet_web, "flet/web"))
    _flet_fastapi = os.path.join(_flet_root, "fastapi")
    if os.path.isdir(_flet_fastapi):
        _flet_datas.append((_flet_fastapi, "flet/fastapi"))
except Exception:
    pass

_icon = "assets/icon.ico" if os.path.exists("assets/icon.ico") else None

# Раунд 37: ВСТРОЕННЫЙ edition.json — build-скрипт заранее пишет
# build_edition/edition.json (роль дистрибутива: admin); файл попадает в
# корень папки распаковки _MEIPASS — идентичность сборки не теряется, даже
# если рядом лежащий edition.json не доехал до машины администратора.
_edition_datas = []
if os.path.exists("build_edition/edition.json"):
    _edition_datas = [("build_edition/edition.json", ".")]

# Раунд 37 (Win7): api-ms-win-core-path-l1-1-0.dll-стаб nalexandru — без него
# Python 3.11 на Windows 7 не загружается («отсутствует
# api-ms-win-core-path-l1-1-0.dll» / «Failed to load Python DLL»). Файл
# скачивает build-скрипт в assets\win7\; кладём ВНУТРЬ бандла (_MEIPASS,
# рядом с python311.dll) — его и находит загрузчик.
_win7_dll_datas = []
if os.path.exists("assets/win7/api-ms-win-core-path-l1-1-0.dll"):
    _win7_dll_datas = [("assets/win7/api-ms-win-core-path-l1-1-0.dll", ".")]

a = Analysis(
    ["main_web.py"],
    pathex=[],
    binaries=[],
    datas=[("core", "core"), ("ui", "ui"), ("assets", "assets")]
          + _flet_datas + _edition_datas + _win7_dll_datas,
    hiddenimports=[
        "flet.web",
        "flet.fastapi",
        "uvicorn",
        "fastapi",
        "starlette",
    ],
    hookspath=_flet_hooks,
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Порайонка_Админ_Web",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon,
)
