@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: Раунд 24 (задача 2): запуск web-версии Порайонки на Windows 7.
:: Один клик: поднимается локальный web-сервер приложения
:: (Порайонка_Пользователь_Web.exe / Порайонка_Админ_Web.exe) и открывается
:: браузер.
:: Раунд 37 (задача 3): bat универсален — ищет любой из двух exe (в
:: дистрибутиве лежит ровно один своей редакции).
:: Раунд 38 (задача 3.3): браузер НЕ открывается вслепую через 4 секунды —
:: сначала ждём доступности http://127.0.0.1:8555 (до ~60 сек); при провале
:: показываем путь к логу. Повторный запуск не дублирует сервер: сам exe
:: проверяет, что порт уже обслуживается, и завершится сам, а мы просто
:: откроем браузер.

set LOG=%APPDATA%\porayonka\web_startup.log

echo.
echo  Порайонка — Контроли (web-версия для Windows 7)
echo  Сервер: http://127.0.0.1:8555
echo.
echo  НЕ закрывайте это окно, пока работаете с приложением.
echo.

if exist "Порайонка_Пользователь_Web.exe" (
    start "" "Порайонка_Пользователь_Web.exe"
) else if exist "Порайонка_Админ_Web.exe" (
    start "" "Порайонка_Админ_Web.exe"
) else if exist "main_web.py" (
    start "" python main_web.py
) else (
    echo  [ОШИБКА] Не найдены Порайонка_Пользователь_Web.exe /
    echo  Порайонка_Админ_Web.exe / main_web.py
    pause
    exit /b 1
)

:: Ждём пока сервер начнёт отвечать (максимум ~60 секунд). PowerShell 2.0+
:: (есть на Win7 SP1) — HttpWebRequest к 127.0.0.1:8555 в цикле.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ok=$false; for($i=0;$i -lt 60;$i++){ try { $r=[System.Net.HttpWebRequest]::Create('http://127.0.0.1:8555/'); $r.Timeout=2000; $resp=$r.GetResponse(); $resp.Close(); $ok=$true; break } catch { Start-Sleep -Seconds 1 } }; if($ok){ exit 0 } else { exit 1 }" >nul 2>&1

if errorlevel 1 (
    echo.
    echo  [ОШИБКА] Сервер не ответил за 60 секунд.
    echo  Подробности в логе запуска:
    echo  %LOG%
    echo.
    echo  Откройте лог и пришлите его администратору.
    pause
    exit /b 1
)

echo  Сервер отвечает — открываю браузер...
start http://127.0.0.1:8555
