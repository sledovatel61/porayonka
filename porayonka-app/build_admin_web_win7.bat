@echo off
chcp 65001 >nul
cd /d "%~dp0"
cls

echo.
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║  СБОРКА — ПОРАЙОНКА: АДМИН WEB (для Windows 7)                   ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.
echo  Раунд 38 (задача 3, P0): ВОСПРОИЗВОДИМЫЙ build profile Win7:
echo  чистый отдельный venv .venv-win7-web + requirements-win7-web.txt
echo  (FastAPI 0.115.4 / Pydantic v1.10.26 — БЕЗ Rust-расширения
echo  pydantic-core, который на Win7 падал с «DLL load failed while
echo  importing _pydantic_core: Не найдена указанная процедура»).
echo  Flet строго 0.23.2, Python 3.11 x64. Desktop-сборки Win10/11
echo  этим скриптом НЕ затрагиваются.
echo  Режим embedded (первый аргумент) — без pause/explorer, для вызова
echo  из общего сценария сборки.
echo.

set "W7VENV=.venv-win7-web"
set "W7PY=%W7VENV%\Scripts\python.exe"

:: ── Шаг 1: Проверить Python 3.11 ───────────────────────────────
echo [Шаг 1/7] Проверка Python 3.11 (профиль Win7 проверен на 3.11.x)...
set "PYBASE="
py -3.11 --version >nul 2>&1 && set "PYBASE=py -3.11"
if not defined PYBASE (
    python -c "import sys; raise SystemExit(0 if sys.version_info[:2]==(3,11) else 1)" >nul 2>&1 && set "PYBASE=python"
)
if not defined PYBASE (
    echo.
    echo  [ОШИБКА] Python 3.11.x (x64) не найден!
    echo  Установите Python 3.11.x с https://www.python.org/downloads/release/
    echo  (профиль Win7 проверялся именно на 3.11: DLL-стаб под python311.dll).
    echo.
    pause
    exit /b 1
)
%PYBASE% --version
echo  OK — Python 3.11 найден
echo.

:: ── Шаг 2: Чистый venv + pinned зависимости ────────────────────
echo [Шаг 2/7] Чистый venv %W7VENV% + requirements-win7-web.txt...
if exist %W7VENV% rmdir /s /q %W7VENV%
%PYBASE% -m venv %W7VENV%
if errorlevel 1 (
    echo.
    echo  [ОШИБКА] Не удалось создать venv!
    echo.
    pause
    exit /b 1
)
"%W7PY%" -m pip install --upgrade pip -q
"%W7PY%" -m pip install -r requirements-win7-web.txt -q
if errorlevel 1 (
    echo.
    echo  [ОШИБКА] Не удалось установить requirements-win7-web.txt!
    echo  Проверьте подключение к интернету.
    echo.
    pause
    exit /b 1
)
"%W7PY%" -m pip install pyinstaller==6.11.1 pillow -q
if errorlevel 1 (
    echo.
    echo  [ОШИБКА] Не удалось установить pyinstaller==6.11.1/pillow!
    echo.
    pause
    exit /b 1
)
:: ЖЁСТКАЯ проверка профиля: pydantic v1 и ОТСУТСТВИЕ pydantic_core (Rust) —
:: на Windows 7 импорт _pydantic_core падает. Такая сборка недопустима.
"%W7PY%" -c "import importlib.util as u, sys; sys.exit(1 if u.find_spec('pydantic_core') else 0)"
if errorlevel 1 (
    echo.
    echo  [ОШИБКА] В профиле найден pydantic_core (Rust-расширение) —
    echo  сборка заведомо НЕ запустится на Windows 7. Проверьте
    echo  requirements-win7-web.txt (нужен pydantic 1.10.26).
    echo.
    pause
    exit /b 1
)
"%W7PY%" -c "import pydantic, sys; sys.exit(0 if str(pydantic.VERSION).startswith('1.') else 1)"
if errorlevel 1 (
    echo.
    echo  [ОШИБКА] В профиле pydantic НЕ v1 — для Win7 нужен 1.10.26.
    echo.
    pause
    exit /b 1
)
echo  OK — профиль чистый: pydantic v1, pydantic_core отсутствует
echo.

:: ── Шаг 3: Очистка ─────────────────────────────────────────────
echo [Шаг 3/7] Очистка build\ и dist\...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo  OK
echo.

:: ── Шаг 4: Иконка exe (icon.png → icon.ico, необязательно) ─────
echo [Шаг 4/7] Иконка из assets\icon.png (если получится)...
"%W7PY%" -c "from PIL import Image; Image.open('assets/icon.png').save('assets/icon.ico', sizes=[(64,64),(32,32),(16,16)])" >nul 2>&1
if exist assets\icon.ico (echo  OK — assets\icon.ico) else (echo  .. пропуск, будет стандартная иконка)
echo.

:: ── Шаг 5: Сборка exe ──────────────────────────────────────────
:: Раунд 37: ВСТРОЕННЫЙ edition.json (роль user запечатается ВНУТРИ exe) —
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
:: nalexandru/api-ms-win-core-path-HACK, релиз 0.3.1). Он нужен python311.dll
:: на Windows 7 (НЕ связан с ошибкой _pydantic_core — та лечится профилем
:: pydantic v1 выше). Кладём ВНУТРЬ бандла и рядом с exe. Кэш: assets\win7\.
:: Раунд 37, приёмка: архив распаковывается во ВЛОЖЕННУЮ папку
:: api-ms-win-core-path-blender\x64\ — учтены оба пути; контроль SHA256
:: архива и DLL; без валидной DLL сборка ОСТАНАВЛИВАЕТСЯ.
if not exist "assets\win7\api-ms-win-core-path-l1-1-0.dll" call :get_win7_dll
if not exist "assets\win7\api-ms-win-core-path-l1-1-0.dll" (
    echo  [ОШИБКА] api-ms-win-core-path-l1-1-0.dll не получен!
    echo  Скачивание не удалось (нет сети?) или путь распаковки отличается.
    echo  Положите файл вручную в assets\win7\: github.com/nalexandru/
    echo  api-ms-win-core-path-HACK, релиз 0.3.1, архив -^> вложенная папка
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
echo [Шаг 5/7] PyInstaller Porayonka_Admin_Web.spec (3-7 минут)...
"%W7PY%" -m PyInstaller Porayonka_Admin_Web.spec --noconfirm --clean --log-level WARN
if errorlevel 1 (
    echo.
    echo  [ОШИБКА] Сборка завершилась с ошибкой! См. вывод выше.
    echo.
    pause
    exit /b 1
)

:: ── Шаг 6: edition.json + start_web_win7.bat + DLL рядом с exe ─
:: Раунд 36: edition.json через python в UTF-8 (echo даёт OEM/ANSI)
:: Раунд 37: + запасная копия .bak (self-heal) + DLL-стаб рядом с exe.
python -c "import pathlib,json; pathlib.Path('dist/edition.json').write_text(json.dumps({'role':'admin'},ensure_ascii=False,indent=2),encoding='utf-8')"
copy /y "dist\edition.json" "dist\edition.json.bak" >nul
copy /y "start_web_win7.bat" "dist\start_web_win7.bat" >nul
if exist "assets\win7\api-ms-win-core-path-l1-1-0.dll" (
    copy /y "assets\win7\api-ms-win-core-path-l1-1-0.dll" "dist\api-ms-win-core-path-l1-1-0.dll" >nul
)
if exist build_edition rmdir /s /q build_edition

:: ── Шаг 7: Манифест сборки (версии + SHA256 exe) ───────────────
echo [Шаг 7/7] Манифест Win7-сборки (tools\make_web_manifest.py)...
python tools\make_web_manifest.py --venv %W7VENV% --exe "dist\Порайонка_Админ_Web.exe" --out "dist\manifest_win7_web.txt"
if errorlevel 1 (
    echo.
    echo  [ОШИБКА] Профиль сборки не прошёл проверку манифеста
    echo  (см. [MANIFEST-ERROR] выше) — дистрибутив НЕ считается годным.
    echo.
    pause
    exit /b 1
)

echo.
if exist "dist\Порайонка_Админ_Web.exe" (
    echo ╔══════════════════════════════════════════════════════════════╗
    echo ║                   OK — СБОРКА УСПЕШНА!                       ║
    echo ╚══════════════════════════════════════════════════════════════╝
    echo.
    echo  Файл:      dist\Порайонка_Админ_Web.exe
    echo  Редакция:  dist\edition.json  {"role": "admin"}
    echo  Запуск:    dist\start_web_win7.bat  (или сам exe)
    echo  Манифест:  dist\manifest_win7_web.txt
    echo.
    echo  Установка на Win7: скопируйте ВСЮ папку dist на машину
    echo  администратора и запускайте start_web_win7.bat — откроется
    echo  браузер (Chrome/Firefox) с приложением.
    if /I not "%~1"=="embedded" explorer dist
) else (
    echo  [ОШИБКА] Файл dist\Порайонка_Админ_Web.exe не найден!
    if /I "%~1"=="embedded" exit /b 1
)
echo.
if /I not "%~1"=="embedded" pause
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
