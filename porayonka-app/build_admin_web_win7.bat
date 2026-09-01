@echo off
chcp 65001 >nul
cd /d "%~dp0"
cls

echo.
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║  СБОРКА — ПОРАЙОНКА: АДМИН WEB (для Windows 7)                   ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.
echo  Раунд 37 (задача 3): нативный клиент Flet на Win7 не работает
echo  (нужен Win10+), поэтому собирается exe-обёртка, которая поднимает
echo  web-сервер (main_web.py → main.py --web --host 0.0.0.0 --port 8555)
echo  и открывает браузер. Редакция: АДМИН (полная, edition.json
echo  {"role": "admin"} рядом с exe + встроенный внутрь exe).
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
echo [Шаг 2/6] Установка зависимостей (requirements + pillow pyinstaller)...
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install pillow pyinstaller -q
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
:: Раунд 37: ВСТРОЕННЫЙ edition.json (роль admin запечатается ВНУТРИ exe) —
:: перенос portable-сборки без рядом лежащих файлов редакцию не теряет.
if exist build_edition rmdir /s /q build_edition
python -c "import pathlib,json; pathlib.Path('build_edition').mkdir(exist_ok=True); pathlib.Path('build_edition/edition.json').write_text(json.dumps({'role':'admin'},ensure_ascii=False,indent=2),encoding='utf-8')"
if errorlevel 1 (
    echo.
    echo  [ОШИБКА] Не удалось записать build_edition\edition.json!
    echo.
    pause
    exit /b 1
)
:: Раунд 37 (Win7): api-ms-win-core-path-l1-1-0.dll-стаб (проект
:: nalexandru/api-ms-win-core-path-HACK, релиз 0.3.1). Без него Python 3.11
:: НЕ загружается на Windows 7: «Запуск программы невозможен, отсутствует
:: api-ms-win-core-path-l1-1-0.dll» / «Failed to load Python DLL
:: python311.dll». Кладём ВНУТРЬ бандла (рядом с python311.dll в _MEIPASS)
:: И рядом с exe. Кэшируем в assets\win7\.
:: Раунд 37, приёмка: архив распаковывается во ВЛОЖЕННУЮ папку
:: api-ms-win-core-path-blender\x64\ (а не \x64\) — учтены оба пути;
:: контроль SHA256 архива и DLL; без валидной DLL сборка ОСТАНАВЛИВАЕТСЯ
:: (раньше только предупреждение — dist собирался заведомо битым).
if not exist "assets\win7\api-ms-win-core-path-l1-1-0.dll" call :get_win7_dll
if not exist "assets\win7\api-ms-win-core-path-l1-1-0.dll" (
    echo  [ОШИБКА] api-ms-win-core-path-l1-1-0.dll не получен!
    echo  Скачивание не удалось (нет сети?) или путь распаковки отличается.
    echo  Положите файл вручную в assets\win7\: github.com/nalexandru/
    echo  api-ms-win-core-path-HACK, релиз 0.3.1, архив -> вложенная папка
    echo  api-ms-win-core-path-blender\x64\api-ms-win-core-path-l1-1-0.dll
    pause
    exit /b 1
)
:: Контроль подлинности: SHA256 x64-стаба релиза 0.3.1
certutil -hashfile "assets\win7\api-ms-win-core-path-l1-1-0.dll" SHA256 | find /I "A1F02F8F2B90F89D0BFAE554D2EBD61D07C7454EABBC53236738143180E030CE" >nul
if errorlevel 1 (
    echo  [ОШИБКА] assets\win7\api-ms-win-core-path-l1-1-0.dll - НЕВЕРНАЯ
    echo  контрольная сумма SHA256! Удалите файл и перезапустите сборку:
    echo  заведомо правильный скачается автоматически (релиз 0.3.1).
    pause
    exit /b 1
)
echo  OK — api-ms-win-core-path-l1-1-0.dll (x64, SHA256 проверен) будет в бандле
echo.
echo [Шаг 5/6] PyInstaller Porayonka_Admin_Web.spec (3-7 минут)...
pyinstaller Porayonka_Admin_Web.spec --noconfirm --clean --log-level WARN
if errorlevel 1 (
    echo.
    echo  [ОШИБКА] Сборка завершилась с ошибкой! См. вывод выше.
    echo.
    pause
    exit /b 1
)

:: ── Шаг 6: edition.json + start_web_win7.bat + DLL рядом с exe ─
:: Раунд 37: edition.json через python в UTF-8 + запасная копия .bak
:: (self-heal core/edition.py) + DLL-стаб рядом с exe (папка exe — первое
:: место поиска зависимостей python311.dll); build_edition чистим.
python -c "import pathlib,json; pathlib.Path('dist/edition.json').write_text(json.dumps({'role':'admin'},ensure_ascii=False,indent=2),encoding='utf-8')"
copy /y "dist\edition.json" "dist\edition.json.bak" >nul
copy /y "start_web_win7.bat" "dist\start_web_win7.bat" >nul
if exist "assets\win7\api-ms-win-core-path-l1-1-0.dll" (
    copy /y "assets\win7\api-ms-win-core-path-l1-1-0.dll" "dist\api-ms-win-core-path-l1-1-0.dll" >nul
)
if exist build_edition rmdir /s /q build_edition

echo.
if exist "dist\Порайонка_Админ_Web.exe" (
    echo ╔══════════════════════════════════════════════════════════════╗
    echo ║                   OK — СБОРКА УСПЕШНА!                       ║
    echo ╚══════════════════════════════════════════════════════════════╝
    echo.
    echo  Файл:      dist\Порайонка_Админ_Web.exe
    echo  Редакция:  dist\edition.json  {"role": "admin"} (+ встроенная)
    echo  Запуск:    dist\start_web_win7.bat  (или сам exe)
    echo.
    echo  Установка на Win7: скопируйте ВСЮ папку dist на машину
    echo  администратора и запускайте start_web_win7.bat — откроется
    echo  браузер (Chrome/Firefox) с приложением.
    explorer dist
) else (
    echo  [ОШИБКА] Файл dist\Порайонка_Админ_Web.exe не найден!
)
echo.
pause
goto :eof

:get_win7_dll
:: Раунд 37: скачать zip релиза 0.3.1, проверить SHA256 архива, распаковать
:: и скопировать в кэш assets\win7\ x64-DLL. Архив содержит ВЛОЖЕННУЮ папку
:: api-ms-win-core-path-blender\ — проверяем оба варианта пути к x64.
:: SHA256 архива: 2CFF5E3DC3B0A5E9241C1091230959CDED50E3D2FF543308B68C6FBA653A3BB6
:: SHA256 DLL x64: A1F02F8F2B90F89D0BFAE554D2EBD61D07C7454EABBC53236738143180E030CE
echo  Скачивание api-ms-win-core-path-l1-1-0.dll (релиз 0.3.1, x64)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/nalexandru/api-ms-win-core-path-HACK/releases/download/0.3.1/api-ms-win-core-path-blender-0.3.1.zip' -OutFile \"$env:TEMP\apimswin7.zip\"" >nul 2>&1
powershell -NoProfile -Command "if((Get-FileHash \"$env:TEMP\apimswin7.zip\" -Algorithm SHA256).Hash -ne '2CFF5E3DC3B0A5E9241C1091230959CDED50E3D2FF543308B68C6FBA653A3BB6'){exit 1}" >nul 2>&1 || goto :eof
if exist "%TEMP%\apimswin7" rmdir /s /q "%TEMP%\apimswin7"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Force \"$env:TEMP\apimswin7.zip\" \"$env:TEMP\apimswin7\"" >nul 2>&1
if not exist assets\win7 mkdir assets\win7
if exist "%TEMP%\apimswin7\api-ms-win-core-path-blender\x64\api-ms-win-core-path-l1-1-0.dll" (
    copy /y "%TEMP%\apimswin7\api-ms-win-core-path-blender\x64\api-ms-win-core-path-l1-1-0.dll" "assets\win7\api-ms-win-core-path-l1-1-0.dll" >nul 2>&1
) else if exist "%TEMP%\apimswin7\x64\api-ms-win-core-path-l1-1-0.dll" (
    copy /y "%TEMP%\apimswin7\x64\api-ms-win-core-path-l1-1-0.dll" "assets\win7\api-ms-win-core-path-l1-1-0.dll" >nul 2>&1
)
goto :eof
