@echo off
chcp 65001 >nul
cd /d "%~dp0"
cls

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║   СБОРКА ДИСТРИБУТИВА — ПОРАЙОНКА: АДМИН (полная редакция)   ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo  Раунд 24: exe + edition.json {"role": "admin"} рядом с ним.
echo.

:: ── Шаг 1: Проверить Python ────────────────────────────────────
echo [Шаг 1/6] Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ОШИБКА] Python не найден!
    echo  Установите Python 3.10+ с https://www.python.org/downloads/
    echo  ВАЖНО: при установке отметьте "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
python --version
echo  OK — Python найден
echo.

:: ── Шаг 2: Зависимости ─────────────────────────────────────────
echo [Шаг 2/6] Установка зависимостей (requirements + pystray pillow pyinstaller)...
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install pystray pillow pyinstaller -q
if errorlevel 1 (
    echo.
    echo  [ОШИБКА] Не удалось установить зависимости!
    echo  Проверьте подключение к интернету.
    echo.
    pause
    exit /b 1
)
echo  OK — зависимости установлены
echo.

:: ── Шаг 3: Очистка ─────────────────────────────────────────────
echo [Шаг 3/6] Очистка build\ и dist\...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo  OK
echo.

:: ── Шаг 4: Иконка exe (icon.png → icon.ico, необязательно) ─────
echo [Шаг 4/6] Иконка из assets\icon.png (если получится)...
python -c "from PIL import Image; Image.open('assets/icon.png').save('assets/icon.ico', sizes=[(64,64),(32,32),(16,16)])" >nul 2>&1
if exist assets\icon.ico (echo  OK — assets\icon.ico) else (echo  .. пропуск (будет стандартная иконка))
echo.

:: ── Шаг 5: Сборка exe ──────────────────────────────────────────
echo [Шаг 5/6] PyInstaller Porayonka_Admin.spec (3-7 минут)...
pyinstaller Porayonka_Admin.spec --noconfirm --clean --log-level WARN
if errorlevel 1 (
    echo.
    echo  [ОШИБКА] Сборка завершилась с ошибкой! См. вывод выше.
    echo.
    pause
    exit /b 1
)

:: ── Шаг 6: edition.json рядом с exe + проверка ─────────────────
> "dist\edition.json" echo {"role": "admin"}

echo.
if exist "dist\Порайонка_Админ.exe" (
    echo ╔══════════════════════════════════════════════════════════════╗
    echo ║                   OK — СБОРКА УСПЕШНА!                       ║
    echo ╚══════════════════════════════════════════════════════════════╝
    echo.
    echo  Файл:      dist\Порайонка_Админ.exe
    echo  Редакция:  dist\edition.json  {"role": "admin"}
    echo.
    echo  Установка: скопируйте exe + edition.json в одну папку
    echo  на админской машине (Win10/11) и запустите exe.
    explorer dist
) else (
    echo  [ОШИБКА] Файл dist\Порайонка_Админ.exe не найден!
)
echo.
pause
