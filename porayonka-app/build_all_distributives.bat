@echo off
chcp 65001 >nul
cd /d "%~dp0"
cls

echo.
echo ======================================================================
echo   СБОРКА ВСЕХ ДИСТРИБУТИВОВ "ПОРАЙОНКА" v2 DARK final
echo   Раунд 38: Админ + Пользователь (Win10/11) +
echo             Пользователь Web (Win7) + Админ Web (Win7)
echo ======================================================================
echo.

:: --- Шаг 0: Python и зависимости -----------------------------------------
echo [Шаг 1/10] Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден. Установите Python 3.10+ и добавьте в PATH.
    exit /b 1
)
python --version
echo.

echo [Шаг 2/10] Установка/обновление зависимостей...
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install pystray pillow==10.4.0 pyinstaller -q
if errorlevel 1 (
    echo [ОШИБКА] Не удалось установить зависимости.
    exit /b 1
)
echo OK
echo.

:: --- Шаг 1: Иконка exe ----------------------------------------------------
echo [Шаг 3/10] Генерация иконки из assets/icon.png...
python -c "from PIL import Image; Image.open('assets/icon.png').save('assets/icon.ico', sizes=[(64,64),(32,32),(16,16)])" >nul 2>&1
if exist assets\icon.ico (echo OK) else (echo [ПРЕДУПРЕЖДЕНИЕ] иконка не создана, будет стандартная)
echo.

:: --- Шаг 2: Win7 DLL-стаб для web-сборок ----------------------------------
:: Раунд 37 (задача 2): api-ms-win-core-path-l1-1-0.dll (проект
:: nalexandru/api-ms-win-core-path-HACK, релиз 0.3.1). Без него Python 3.11
:: НЕ загружается на Windows 7: «отсутствует api-ms-win-core-path-l1-1-0.dll» /
:: «Failed to load Python DLL python311.dll». Файл уходит ВНУТРЬ web-бандлов
:: (_MEIPASS, рядом с python311.dll) и рядом с exe в dist. Кэш: assets\win7\.
:: Раунд 37, приёмка: архив 0.3.1 распаковывается во ВЛОЖЕННУЮ папку
:: api-ms-win-core-path-blender\x64\ (а не \x64\) — учтены оба пути;
:: контроль SHA256 архива и DLL; без валидной DLL сборка ОСТАНАВЛИВАЕТСЯ
:: (раньше только предупреждение — web-dist собирался заведомо битым).
echo [Шаг 4/10] api-ms-win-core-path-l1-1-0.dll для Win7-сборок...
if not exist "assets\win7\api-ms-win-core-path-l1-1-0.dll" call :get_win7_dll
if not exist "assets\win7\api-ms-win-core-path-l1-1-0.dll" (
    echo [ОШИБКА] api-ms-win-core-path-l1-1-0.dll не получен - web-сборки под Win7
    echo падут (python311.dll). Положите файл вручную в assets\win7\:
    echo github.com/nalexandru/api-ms-win-core-path-HACK, релиз 0.3.1, архив ->
    echo вложенная папка api-ms-win-core-path-blender\x64\. См. assets\win7\README.txt.
    exit /b 1
)
:: Контроль подлинности: SHA256 x64-стаба релиза 0.3.1
certutil -hashfile "assets\win7\api-ms-win-core-path-l1-1-0.dll" SHA256 | find /I "A1F02F8F2B90F89D0BFAE554D2EBD61D07C7454EABBC53236738143180E030CE" >nul
if errorlevel 1 (
    echo [ОШИБКА] assets\win7\api-ms-win-core-path-l1-1-0.dll - НЕВЕРНАЯ контрольная
    echo сумма SHA256! Удалите файл и перезапустите сборку (скачивается автоматически).
    exit /b 1
)
echo OK - DLL-стаб (x64, SHA256 проверен) будет встроен в web-бандлы
echo.

:: --- Шаг 4b: чистый Win7 WEB venv-профиль ------------------------------
:: Раунд 38 (задача 3, P0): web-сборки собираются ТОЛЬКИ из чистого venv
:: .venv-win7-web с requirements-win7-web.txt (FastAPI 0.115.4 / Pydantic
:: v1.10.26 — БЕЗ Rust-расширения pydantic-core, падавшего на Win7 с
:: «DLL load failed while importing _pydantic_core»). Desktop-ступени выше
:: по-прежнему используют глобальный Python (без downgrade).
set "W7VENV=.venv-win7-web"
set "W7PY=%W7VENV%\Scripts\python.exe"
echo [Шаг 5/11] Чистый Win7 web venv + pinned requirements-win7-web.txt...
set "PYBASE="
py -3.11 --version >nul 2>&1 && set "PYBASE=py -3.11"
if not defined PYBASE (
    python -c "import sys; raise SystemExit(0 if sys.version_info[:2]==(3,11) else 1)" >nul 2>&1 && set "PYBASE=python"
)
if not defined PYBASE (
    echo [ОШИБКА] Python 3.11.x (x64) не найден - web-сборки Win7 невозможны.
    echo Установите Python 3.11.x (профиль проверялся именно на 3.11).
    exit /b 1
)
%PYBASE% --version
if exist %W7VENV% rmdir /s /q %W7VENV%
%PYBASE% -m venv %W7VENV%
if errorlevel 1 (
    echo [ОШИБКА] Не удалось создать venv %W7VENV%.
    exit /b 1
)
"%W7PY%" -m pip install --upgrade pip -q
"%W7PY%" -m pip install -r requirements-win7-web.txt -q
if errorlevel 1 (
    echo [ОШИБКА] Не удалось установить requirements-win7-web.txt.
    exit /b 1
)
"%W7PY%" -m pip install pyinstaller==6.11.1 pillow==10.4.0 -q
if errorlevel 1 (
    echo [ОШИБКА] Не удалось установить pyinstaller==6.11.1.
    exit /b 1
)
:: ЖЁСТКИЙ стоп, если в профиле pydantic_core (Rust) или pydantic не v1 —
:: на Windows 7 такая сборка заведомо падает при импорте _pydantic_core.
"%W7PY%" -c "import importlib.util as u, sys; sys.exit(1 if u.find_spec('pydantic_core') else 0)"
if errorlevel 1 (
    echo [ОШИБКА] В профиле найден pydantic_core (Rust) - сборка НЕ запустится
    echo на Windows 7. Проверьте requirements-win7-web.txt (pydantic 1.10.26).
    exit /b 1
)
"%W7PY%" -c "import pydantic, sys; sys.exit(0 if str(pydantic.VERSION).startswith('1.') else 1)"
if errorlevel 1 (
    echo [ОШИБКА] В профиле pydantic НЕ v1 - для Win7 нужен 1.10.26.
    exit /b 1
)
echo OK - Win7 web профиль чистый: pydantic v1, pydantic_core отсутствует
echo.

:: --- Шаг 3: Админский дистрибутив -----------------------------------------
:: Раунд 37: build_edition\edition.json — РОЛЬ ЗАПЕЧАТЫВАЕТСЯ ВНУТРЬ exe
:: (_MEIPASS) перед каждым pyinstaller; перенос exe без сопутствующих
:: файлов редакцию больше не теряет (источник "embedded" в core/edition.py).
echo [Шаг 6/11] Сборка АДМИНСКОГО дистрибутива (3-7 минут)...
if exist build_admin rmdir /s /q build_admin
if exist dist_admin rmdir /s /q dist_admin
if exist build_edition rmdir /s /q build_edition
python -c "import pathlib,json; pathlib.Path('build_edition').mkdir(exist_ok=True); pathlib.Path('build_edition/edition.json').write_text(json.dumps({'role':'admin'},ensure_ascii=False,indent=2),encoding='utf-8')"
pyinstaller Porayonka_Admin.spec --noconfirm --clean --log-level WARN --distpath dist_admin --workpath build_admin
if errorlevel 1 (
    echo [ОШИБКА] Сборка админского дистрибутива не удалась.
    exit /b 1
)
python -c "import pathlib, json; pathlib.Path('dist_admin/edition.json').write_text(json.dumps({'role': 'admin'}, ensure_ascii=False, indent=2), encoding='utf-8')"
copy /y "dist_admin\edition.json" "dist_admin\edition.json.bak" >nul
echo OK - dist_admin\Порайонка_Админ.exe
echo.

:: --- Шаг 4: Пользовательский дистрибутив ----------------------------------
echo [Шаг 7/11] Сборка ПОЛЬЗОВАТЕЛЬСКОГО дистрибутива (3-7 минут)...
if exist build_user rmdir /s /q build_user
if exist dist_user rmdir /s /q dist_user
if exist build_edition rmdir /s /q build_edition
python -c "import pathlib,json; pathlib.Path('build_edition').mkdir(exist_ok=True); pathlib.Path('build_edition/edition.json').write_text(json.dumps({'role':'user'},ensure_ascii=False,indent=2),encoding='utf-8')"
pyinstaller Porayonka_User.spec --noconfirm --clean --log-level WARN --distpath dist_user --workpath build_user
if errorlevel 1 (
    echo [ОШИБКА] Сборка пользовательского дистрибутива не удалась.
    exit /b 1
)
python -c "import pathlib, json; pathlib.Path('dist_user/edition.json').write_text(json.dumps({'role': 'user'}, ensure_ascii=False, indent=2), encoding='utf-8')"
copy /y "dist_user\edition.json" "dist_user\edition.json.bak" >nul
echo OK - dist_user\Порайонка_Пользователь.exe
echo.

:: --- Шаг 5: Web-дистрибутив (ПОЛЬЗОВАТЕЛЬ) для Windows 7 ------------------
echo [Шаг 8/11] Сборка WEB-дистрибутива ПОЛЬЗОВАТЕЛЬ для Win7 (3-7 минут)...
if exist build_web rmdir /s /q build_web
if exist dist_web rmdir /s /q dist_web
if exist build_edition rmdir /s /q build_edition
python -c "import pathlib,json; pathlib.Path('build_edition').mkdir(exist_ok=True); pathlib.Path('build_edition/edition.json').write_text(json.dumps({'role':'user'},ensure_ascii=False,indent=2),encoding='utf-8')"
"%W7PY%" -m PyInstaller Porayonka_User_Web.spec --noconfirm --clean --log-level WARN --distpath dist_web --workpath build_web
if errorlevel 1 (
    echo [ОШИБКА] Сборка web-дистрибутива пользователя не удалась.
    exit /b 1
)
python -c "import pathlib, json; pathlib.Path('dist_web/edition.json').write_text(json.dumps({'role': 'user'}, ensure_ascii=False, indent=2), encoding='utf-8')"
copy /y "dist_web\edition.json" "dist_web\edition.json.bak" >nul
copy /y "start_web_win7.bat" "dist_web\start_web_win7.bat" >nul
if exist "assets\win7\api-ms-win-core-path-l1-1-0.dll" (
    copy /y "assets\win7\api-ms-win-core-path-l1-1-0.dll" "dist_web\api-ms-win-core-path-l1-1-0.dll" >nul
)
python tools\make_web_manifest.py --venv %W7VENV% --exe "dist_web\Порайонка_Пользователь_Web.exe" --out "dist_web\manifest_win7_web.txt"
if errorlevel 1 (
    echo [ОШИБКА] Манифест web-дистрибутива пользователя не сошёлся.
    exit /b 1
)
echo OK - dist_web\Порайонка_Пользователь_Web.exe
echo.

:: --- Шаг 6: Web-дистрибутив (АДМИН) для Windows 7 -------------------------
echo [Шаг 9/11] Сборка WEB-дистрибутива АДМИН для Win7 (3-7 минут)...
if exist build_admin_web rmdir /s /q build_admin_web
if exist dist_admin_web rmdir /s /q dist_admin_web
if exist build_edition rmdir /s /q build_edition
python -c "import pathlib,json; pathlib.Path('build_edition').mkdir(exist_ok=True); pathlib.Path('build_edition/edition.json').write_text(json.dumps({'role':'admin'},ensure_ascii=False,indent=2),encoding='utf-8')"
"%W7PY%" -m PyInstaller Porayonka_Admin_Web.spec --noconfirm --clean --log-level WARN --distpath dist_admin_web --workpath build_admin_web
if errorlevel 1 (
    echo [ОШИБКА] Сборка web-дистрибутива админа не удалась.
    exit /b 1
)
python -c "import pathlib, json; pathlib.Path('dist_admin_web/edition.json').write_text(json.dumps({'role': 'admin'}, ensure_ascii=False, indent=2), encoding='utf-8')"
copy /y "dist_admin_web\edition.json" "dist_admin_web\edition.json.bak" >nul
copy /y "start_web_win7.bat" "dist_admin_web\start_web_win7.bat" >nul
if exist "assets\win7\api-ms-win-core-path-l1-1-0.dll" (
    copy /y "assets\win7\api-ms-win-core-path-l1-1-0.dll" "dist_admin_web\api-ms-win-core-path-l1-1-0.dll" >nul
)
if exist build_edition rmdir /s /q build_edition
python tools\make_web_manifest.py --venv %W7VENV% --exe "dist_admin_web\Порайонка_Админ_Web.exe" --out "dist_admin_web\manifest_win7_web.txt"
if errorlevel 1 (
    echo [ОШИБКА] Манифест web-дистрибутива админа не сошёлся.
    exit /b 1
)
echo OK - dist_admin_web\Порайонка_Админ_Web.exe
echo.

:: --- Шаг 7: Собираем всё в одну папку -------------------------------------
echo [Шаг 10/11] Копирование всех дистрибутивов в dist_all\...
if exist dist_all rmdir /s /q dist_all
mkdir dist_all

mkdir "dist_all\Порайонка_Админ"
copy /y "dist_admin\Порайонка_Админ.exe" "dist_all\Порайонка_Админ\" >nul
copy /y "dist_admin\edition.json" "dist_all\Порайонка_Админ\" >nul
copy /y "dist_admin\edition.json.bak" "dist_all\Порайонка_Админ\" >nul

mkdir "dist_all\Порайонка_Пользователь"
copy /y "dist_user\Порайонка_Пользователь.exe" "dist_all\Порайонка_Пользователь\" >nul
copy /y "dist_user\edition.json" "dist_all\Порайонка_Пользователь\" >nul
copy /y "dist_user\edition.json.bak" "dist_all\Порайонка_Пользователь\" >nul

mkdir "dist_all\Порайонка_Пользователь_Web"
copy /y "dist_web\Порайонка_Пользователь_Web.exe" "dist_all\Порайонка_Пользователь_Web\" >nul
copy /y "dist_web\edition.json" "dist_all\Порайонка_Пользователь_Web\" >nul
copy /y "dist_web\edition.json.bak" "dist_all\Порайонка_Пользователь_Web\" >nul
copy /y "dist_web\start_web_win7.bat" "dist_all\Порайонка_Пользователь_Web\" >nul
copy /y "dist_web\manifest_win7_web.txt" "dist_all\Порайонка_Пользователь_Web\" >nul
if exist "dist_web\api-ms-win-core-path-l1-1-0.dll" (
    copy /y "dist_web\api-ms-win-core-path-l1-1-0.dll" "dist_all\Порайонка_Пользователь_Web\" >nul
)

mkdir "dist_all\Порайонка_Админ_Web"
copy /y "dist_admin_web\Порайонка_Админ_Web.exe" "dist_all\Порайонка_Админ_Web\" >nul
copy /y "dist_admin_web\edition.json" "dist_all\Порайонка_Админ_Web\" >nul
copy /y "dist_admin_web\edition.json.bak" "dist_all\Порайонка_Админ_Web\" >nul
copy /y "dist_admin_web\start_web_win7.bat" "dist_all\Порайонка_Админ_Web\" >nul
copy /y "dist_admin_web\manifest_win7_web.txt" "dist_all\Порайонка_Админ_Web\" >nul
if exist "dist_admin_web\api-ms-win-core-path-l1-1-0.dll" (
    copy /y "dist_admin_web\api-ms-win-core-path-l1-1-0.dll" "dist_all\Порайонка_Админ_Web\" >nul
)

:: --- Шаг 8: Проверка итогов -----------------------------------------------
echo [Шаг 11/11] Проверка итоговой папки...
echo.
set "ERR=0"
if not exist "dist_all\Порайонка_Админ\Порайонка_Админ.exe" set ERR=1
if not exist "dist_all\Порайонка_Админ\edition.json" set ERR=1
if not exist "dist_all\Порайонка_Пользователь\Порайонка_Пользователь.exe" set ERR=1
if not exist "dist_all\Порайонка_Пользователь\edition.json" set ERR=1
if not exist "dist_all\Порайонка_Пользователь_Web\Порайонка_Пользователь_Web.exe" set ERR=1
if not exist "dist_all\Порайонка_Пользователь_Web\edition.json" set ERR=1
if not exist "dist_all\Порайонка_Пользователь_Web\start_web_win7.bat" set ERR=1
if not exist "dist_all\Порайонка_Пользователь_Web\manifest_win7_web.txt" set ERR=1
if not exist "dist_all\Порайонка_Админ_Web\Порайонка_Админ_Web.exe" set ERR=1
if not exist "dist_all\Порайонка_Админ_Web\edition.json" set ERR=1
if not exist "dist_all\Порайонка_Админ_Web\start_web_win7.bat" set ERR=1
if not exist "dist_all\Порайонка_Админ_Web\manifest_win7_web.txt" set ERR=1

if %ERR%==1 (
    echo [ОШИБКА] Не все файлы собраны. Проверьте dist_all\.
    exit /b 1
)

echo ======================================================================
echo   СБОРКА ЗАВЕРШЕНА УСПЕШНО
echo ======================================================================
echo.
echo  Итоговая папка:  dist_all\
echo.
echo  Состав:
echo    - Порайонка_Админ\Порайонка_Админ.exe  + edition.json (+.bak)
echo    - Порайонка_Пользователь\Порайонка_Пользователь.exe  + edition.json (+.bak)
echo    - Порайонка_Пользователь_Web\Порайонка_Пользователь_Web.exe
echo                                + edition.json (+.bak) + start_web_win7.bat + manifest
echo                                + api-ms-win-core-path-l1-1-0.dll
echo    - Порайонка_Админ_Web\Порайонка_Админ_Web.exe
echo                                + edition.json (+.bak) + start_web_win7.bat + manifest
echo                                + api-ms-win-core-path-l1-1-0.dll
echo.
echo  Установка:
echo    Админ (Win10/11):    скопируйте папку Порайонка_Админ.
echo    Пользователь (Win10/11):  скопируйте папку Порайонка_Пользователь.
echo    Пользователь (Win7):      скопируйте папку Порайонка_Пользователь_Web.
echo    Админ (Win7):             скопируйте папку Порайонка_Админ_Web.
echo.

:: --- Открываем итоговую папку ---------------------------------------------
explorer dist_all
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
