@echo off
chcp 65001 >nul
cd /d "%~dp0"
cls

echo.
echo ======================================================================
echo   СБОРКА ВСЕХ ДИСТРИБУТИВОВ "ПОРАЙОНКА" v2 DARK final
echo   Раунд 24: Админ + Пользователь (Win10/11) + Пользователь Web (Win7)
echo ======================================================================
echo.

:: --- Шаг 0: Python и зависимости -----------------------------------------
echo [Шаг 1/9] Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден. Установите Python 3.10+ и добавьте в PATH.
    exit /b 1
)
python --version
echo.

echo [Шаг 2/9] Установка/обновление зависимостей...
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install pystray pillow pyinstaller -q
if errorlevel 1 (
    echo [ОШИБКА] Не удалось установить зависимости.
    exit /b 1
)
echo OK
echo.

:: --- Шаг 1: Иконка exe ----------------------------------------------------
echo [Шаг 3/9] Генерация иконки из assets/icon.png...
python -c "from PIL import Image; Image.open('assets/icon.png').save('assets/icon.ico', sizes=[(64,64),(32,32),(16,16)])" >nul 2>&1
if exist assets\icon.ico (echo OK) else (echo [ПРЕДУПРЕЖДЕНИЕ] иконка не создана, будет стандартная)
echo.

:: --- Шаг 2: Админский дистрибутив -----------------------------------------
echo [Шаг 4/9] Сборка АДМИНСКОГО дистрибутива (3-7 минут)...
if exist build_admin rmdir /s /q build_admin
if exist dist_admin rmdir /s /q dist_admin
pyinstaller Porayonka_Admin.spec --noconfirm --clean --log-level WARN --distpath dist_admin --workpath build_admin
if errorlevel 1 (
    echo [ОШИБКА] Сборка админского дистрибутива не удалась.
    exit /b 1
)
python -c "import pathlib; pathlib.Path('dist_admin/edition.json').write_text('{\\n  \"role\": \"admin\"\\n}', encoding='utf-8')"
echo OK - dist_admin\Порайонка_Админ.exe
echo.

:: --- Шаг 3: Пользовательский дистрибутив ----------------------------------
echo [Шаг 5/9] Сборка ПОЛЬЗОВАТЕЛЬСКОГО дистрибутива (3-7 минут)...
if exist build_user rmdir /s /q build_user
if exist dist_user rmdir /s /q dist_user
pyinstaller Porayonka_User.spec --noconfirm --clean --log-level WARN --distpath dist_user --workpath build_user
if errorlevel 1 (
    echo [ОШИБКА] Сборка пользовательского дистрибутива не удалась.
    exit /b 1
)
python -c "import pathlib; pathlib.Path('dist_user/edition.json').write_text('{\\n  \"role\": \"user\"\\n}', encoding='utf-8')"
echo OK - dist_user\Порайонка_Пользователь.exe
echo.

:: --- Шаг 4: Web-дистрибутив для Windows 7 ---------------------------------
echo [Шаг 6/9] Сборка WEB-дистрибутива для Windows 7 (3-7 минут)...
if exist build_web rmdir /s /q build_web
if exist dist_web rmdir /s /q dist_web
pyinstaller Porayonka_User_Web.spec --noconfirm --clean --log-level WARN --distpath dist_web --workpath build_web
if errorlevel 1 (
    echo [ОШИБКА] Сборка web-дистрибутива не удалась.
    exit /b 1
)
python -c "import pathlib; pathlib.Path('dist_web/edition.json').write_text('{\\n  \"role\": \"user\"\\n}', encoding='utf-8')"
copy /y "start_web_win7.bat" "dist_web\start_web_win7.bat" >nul
echo OK - dist_web\Порайонка_Пользователь_Web.exe
echo.

:: --- Шаг 5: Собираем всё в одну папку -------------------------------------
echo [Шаг 7/9] Копирование всех дистрибутивов в dist_all\...
if exist dist_all rmdir /s /q dist_all
mkdir dist_all

mkdir "dist_all\Порайонка_Админ"
copy /y "dist_admin\Порайонка_Админ.exe" "dist_all\Порайонка_Админ\" >nul
copy /y "dist_admin\edition.json" "dist_all\Порайонка_Админ\" >nul

mkdir "dist_all\Порайонка_Пользователь"
copy /y "dist_user\Порайонка_Пользователь.exe" "dist_all\Порайонка_Пользователь\" >nul
copy /y "dist_user\edition.json" "dist_all\Порайонка_Пользователь\" >nul

mkdir "dist_all\Порайонка_Пользователь_Web"
copy /y "dist_web\Порайонка_Пользователь_Web.exe" "dist_all\Порайонка_Пользователь_Web\" >nul
copy /y "dist_web\edition.json" "dist_all\Порайонка_Пользователь_Web\" >nul
copy /y "dist_web\start_web_win7.bat" "dist_all\Порайонка_Пользователь_Web\" >nul

:: --- Шаг 6: Проверка итогов -----------------------------------------------
echo [Шаг 8/9] Проверка итоговой папки...
echo.
set "ERR=0"
if not exist "dist_all\Порайонка_Админ\Порайонка_Админ.exe" set ERR=1
if not exist "dist_all\Порайонка_Админ\edition.json" set ERR=1
if not exist "dist_all\Порайонка_Пользователь\Порайонка_Пользователь.exe" set ERR=1
if not exist "dist_all\Порайонка_Пользователь\edition.json" set ERR=1
if not exist "dist_all\Порайонка_Пользователь_Web\Порайонка_Пользователь_Web.exe" set ERR=1
if not exist "dist_all\Порайонка_Пользователь_Web\edition.json" set ERR=1
if not exist "dist_all\Порайонка_Пользователь_Web\start_web_win7.bat" set ERR=1

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
echo    - Порайонка_Админ\Порайонка_Админ.exe  + edition.json
echo    - Порайонка_Пользователь\Порайонка_Пользователь.exe  + edition.json
echo    - Порайонка_Пользователь_Web\Порайонка_Пользователь_Web.exe
echo                                + edition.json + start_web_win7.bat
echo.
echo  Установка:
echo    Админ:    скопируйте папку Порайонка_Админ на машину администратора.
echo    Пользователь (Win10/11):  скопируйте папку Порайонка_Пользователь.
echo    Пользователь (Win7):      скопируйте папку Порайонка_Пользователь_Web.
echo.

:: --- Открываем итоговую папку ---------------------------------------------
echo [Шаг 9/9] Открываю dist_all\...
explorer dist_all
