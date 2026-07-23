@echo off
chcp 65001 >nul
cls
echo.
echo ╔══════════════════════════════════════════════╗
echo ║   СБОРКА ДЛЯ WINDOWS 7 — ПОРАЙОНКА v1.0      ║
echo ╚══════════════════════════════════════════════╝
echo.

:: Проверка Python
echo [1/4] Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден!
    pause
    exit /b 1
)

:: Установить совместимые зависимости
echo [2/4] Установка Flet 0.21.2...
pip install flet==0.21.2 openpyxl -q

:: Сборка через PyInstaller (более совместим)
echo [3/4] Сборка через PyInstaller...
pip install pyinstaller -q

pyinstaller --onefile ^
    --windowed ^
    --name "Porayonka_Win7" ^
    --add-data "core;core" ^
    --add-data "ui;ui" ^
    --add-data "assets;assets" ^
    --hidden-import flet ^
    --hidden-import openpyxl ^
    --hidden-import json ^
    --hidden-import pathlib ^
    main.py

if errorlevel 1 (
    echo [ОШИБКА] Сборка не удалась!
    pause
    exit /b 1
)

:: Готово
echo [4/4] Готово!
echo.
if exist "dist\Porayonka_Win7.exe" (
    echo ✓ Файл создан: dist\Porayonka_Win7.exe
    explorer dist
) else (
    echo [ОШИБКА] Файл не найден!
)
pause