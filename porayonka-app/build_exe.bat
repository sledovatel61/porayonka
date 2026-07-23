@echo off
chcp 65001 >nul
cls

echo.
echo ╔══════════════════════════════════════════════╗
echo ║   СБОРКА ПОРТАТИВНОГО .EXE — ПОРАЙОНКА v1.0  ║
echo ╚══════════════════════════════════════════════╝
echo.

:: ── Шаг 1: Проверить Python ────────────────────────────────────
echo [Шаг 1/5] Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ОШИБКА] Python не найден!
    echo.
    echo  Установите Python 3.10+ с официального сайта:
    echo  https://www.python.org/downloads/
    echo.
    echo  ВАЖНО: При установке отметьте галочку
    echo         "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
python --version
echo  ✓ Python найден
echo.

:: ── Шаг 2: Обновить pip ────────────────────────────────────────
echo [Шаг 2/5] Обновление pip...
python -m pip install --upgrade pip -q
echo  ✓ pip обновлён
echo.

:: ── Шаг 3: Установить зависимости ─────────────────────────────
echo [Шаг 3/5] Установка зависимостей (flet, openpyxl)...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo.
    echo  [ОШИБКА] Не удалось установить зависимости!
    echo  Проверьте подключение к интернету.
    echo.
    pause
    exit /b 1
)
echo  ✓ Зависимости установлены
echo.

:: ── Шаг 4: Собрать .exe ────────────────────────────────────────
echo [Шаг 4/5] Сборка .exe через flet pack...
echo  Это может занять 3-7 минут. Пожалуйста, подождите...
echo.

flet pack main.py ^
    --name "Porayonka" ^
    --product-name "Порайонка" ^
    --file-description "Трекер статусов следственных отделов СК РФ" ^
    --product-version "1.0.0" ^
    --file-version "1.0.0.0" ^
    --add-data "core;core" ^
    --add-data "ui;ui" ^
    --add-data "assets;assets" ^
    --onefile ^
    --windowed

if errorlevel 1 (
    echo.
    echo  [ОШИБКА] Сборка завершилась с ошибкой!
    echo.
    echo  Возможные причины:
    echo  1. Не установлен flet: pip install flet
    echo  2. Антивирус блокирует сборку
    echo  3. Недостаточно прав (запустите от администратора)
    echo.
    echo  Попробуйте переустановить flet:
    echo    pip uninstall flet -y
    echo    pip install flet
    echo.
    pause
    exit /b 1
)

:: ── Шаг 5: Готово ──────────────────────────────────────────────
echo.
echo [Шаг 5/5] Проверка результата...
if exist "dist\Porayonka.exe" (
    echo.
    echo ╔══════════════════════════════════════════════╗
    echo ║              ✓ СБОРКА УСПЕШНА!               ║
    echo ╚══════════════════════════════════════════════╝
    echo.
    echo  Файл создан: dist\Porayonka.exe
    echo.
    echo  📌 Как использовать:
    echo     1. Откройте папку dist\
    echo     2. Скопируйте Porayonka.exe куда удобно
    echo     3. Запустите двойным кликом
    echo     4. Python НЕ нужен!
    echo.
    echo  💾 Данные сохраняются в:
    echo     %%APPDATA%%\porayonka\departments.json
    echo.
    echo ══════════════════════════════════════════════
    echo.
    :: Открыть папку dist
    explorer dist
) else (
    echo  [ОШИБКА] Файл dist\Porayonka.exe не найден!
    echo  Что-то пошло не так при сборке.
)

pause
