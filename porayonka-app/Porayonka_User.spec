# -*- mode: python ; coding: utf-8 -*-
# Раунд 24 (задача 1): PyInstaller spec — ПОЛЬЗОВАТЕЛЬСКИЙ дистрибутив.
#
# Сборка:  build_user.bat  (pyinstaller Porayonka_User.spec --noconfirm --clean)
# Результат: dist\Порайонка_Пользователь.exe + dist\edition.json
# {"role": "user"[, "user_name": "ФИО"]} — edition.json рядом с exe кладёт
# build-скрипт (его читает core/edition.py → read-only, алармы каждые 2 ч,
# автозапуск, трей — всё это в frozen Windows-сборке и так активно).
#
# Отличия от admin-spec — только имя exe и edition.json; кодовая база одна
# (редакция определяется файлом, а не кодом — обойти нельзя).
import os

_flet_hooks = []
try:
    import flet as _flet_pkg
    _d = os.path.join(os.path.dirname(_flet_pkg.__file__), "__pyinstaller")
    if os.path.isdir(_d):
        _flet_hooks = [_d]
except Exception:
    pass

_icon = "assets/icon.ico" if os.path.exists("assets/icon.ico") else None

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[("core", "core"), ("ui", "ui"), ("assets", "assets")],
    hiddenimports=[],
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
    name="Порайонка_Пользователь",
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
