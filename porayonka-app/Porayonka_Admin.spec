# -*- mode: python ; coding: utf-8 -*-
# Раунд 24 (задача 1): PyInstaller spec — АДМИНСКИЙ дистрибутив.
#
# Сборка:  build_admin.bat  (pyinstaller Porayonka_Admin.spec --noconfirm --clean)
# Результат: dist\Порайонка_Админ.exe + dist\edition.json {"role": "admin"}
# (edition.json рядом с exe кладёт build-скрипт — его читает core/edition.py)
import os

# hooks flet 0.23.2 (flet/__pyinstaller/hook-flet.py) — то же, что делает
# `flet pack`; без них в бандл не попадут flet-клиент и web-ресурсы.
_flet_hooks = []
try:
    import flet as _flet_pkg
    _d = os.path.join(os.path.dirname(_flet_pkg.__file__), "__pyinstaller")
    if os.path.isdir(_d):
        _flet_hooks = [_d]
except Exception:
    pass

# иконка exe: build-скрипт заранее конвертирует assets/icon.png → icon.ico
# (pillow); если конвертации не было — собираем со стандартной иконкой.
_icon = "assets/icon.ico" if os.path.exists("assets/icon.ico") else None

# Раунд 37: ВСТРОЕННЫЙ edition.json — build-скрипт заранее пишет
# build_edition/edition.json (роль дистрибутива); файл попадает в корень
# папки распаковки _MEIPASS — идентичность сборки не теряется, даже если
# рядом лежащий edition.json не доехал до машины пользователя.
_edition_datas = []
if os.path.exists("build_edition/edition.json"):
    _edition_datas = [("build_edition/edition.json", ".")]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[("core", "core"), ("ui", "ui"), ("assets", "assets")] + _edition_datas,
    hiddenimports=[
        "reportlab",
        "reportlab.pdfbase",
        "reportlab.pdfbase.ttfonts",
        "reportlab.platypus",
        "reportlab.lib.styles",
        "reportlab.lib.enums",
        "reportlab.lib.units",
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
    name="Порайонка_Админ",
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
