@echo off
chcp 65001 >nul
cd /d "%~dp0"
cls

echo.
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║  СБОРКА ДИСТРИБУТИВА — ПОРАЙОНКА: ПОЛЬЗОВАТЕЛЬ (read-only, трей) ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.
echo  Раунд 24: exe + edition.json {"role": "user"} рядом с ним.
echo  Пользовательская редакция: только просмотр контролей, напоминания
echo  о сроке каждые 2 часа со звуком, автозапуск Windows, значок в трее.
echo.

:: ── Шаг 0: ФИО пользователя (запишется в edition.json) ─────────
set "PORAYONKA_USER_FIO="
set /p PORAYONKA_USER_FIO=  ФИО пользователя (Enter — приложение спросит при первом запуске): 
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
if exist assets\icon.ico (echo  OK — assets\icon.ico) else (echo  .. пропуск, будет стандартная иконка)
echo.

:: ── Шаг 5: Сборка exe ──────────────────────────────────────────
echo [Шаг 5/6] PyInstaller Porayonka_User.spec (3-7 минут)...
pyinstaller Porayonka_User.spec --noconfirm --clean --log-level WARN
if errorlevel 1 (
    echo.
    echo  [ОШИБКА] Сборка завершилась с ошибкой! См. вывод выше.
    echo.
    pause
    exit /b 1
)

:: ── Шаг 6: edition.json рядом с exe + проверка ─────────────────
:: Раунд 36: edition.json пишем через python в UTF-8 (echo в cmd даёт
:: OEM/ANSI-кодировку, и русское ФИО ломало чтение edition.json).
set "PYFIO=%PORAYONKA_USER_FIO%"
python -c "import pathlib,json,os; fio=os.environ.get('PYFIO','').strip(); d={'role':'user'}; d.update({'user_name':fio} if fio else {}); pathlib.Path('dist/edition.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')"

echo.
if exist "dist\Порайонка_Пользователь.exe" (
    echo ╔══════════════════════════════════════════════════════════════╗
    echo ║                   OK — СБОРКА УСПЕШНА!                       ║
    echo ╚══════════════════════════════════════════════════════════════╝
    echo.
    echo  Файл:      dist\Порайонка_Пользователь.exe
    echo  Редакция:  dist\edition.json  {"role": "user"}
    if not "%PORAYONKA_USER_FIO%"=="" echo  ФИО:       %PORAYONKA_USER_FIO%
    echo.
    echo  Установка: скопируйте exe + edition.json в одну папку
    echo  на машине пользователя (Win10/11) и запустите exe.
    echo  Автозапуск и трей включатся сами (только frozen-сборка).
    explorer dist
) else (
    echo  [ОШИБКА] Файл dist\Порайонка_Пользователь.exe не найден!
)
echo.
pause
