@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: Раунд 24 (задача 2): запуск web-версии Порайонки на Windows 7.
:: Раунд 37 (задача 3): bat универсален — ищет любой из двух exe (в
:: дистрибутиве лежит ровно один своей редакции).
:: Раунд 38 (задача 3.3): bat ждёт доступности сервера (до ~60 сек), а не
:: открывает браузер вслепую через 4 секунды.
::
:: ════════════════════════════════════════════════════════════════════
:: Раунд 39 (задача 3): bat БОЛЬШЕ НЕ ОТКРЫВАЕТ БРАУЗЕР.
:: ════════════════════════════════════════════════════════════════════
:: Корень «двух окон браузера»: браузер открывали одновременно Flet внутри
:: exe (AppView.WEB_BROWSER) и этот bat (`start http://127.0.0.1:8555`).
:: Единственный владелец — FLET (см. BROWSER_OWNER в main.py). Роль bat'а:
:: 1) запустить сервер; 2) дождаться доступности HTTP и НАПЕЧАТАТЬ адрес.
:: Порт ищем перебором 8555..8564: main_web.py при занятом 8555 уезжает на
:: следующий свободный, а жёстко зашитый 8555 вёл бы на мёртвую вкладку.
:: Если Flet браузер не поднял (не назначен по умолчанию) — адрес виден
:: здесь. Повторный запуск не дублирует ни сервер, ни браузер: exe сам видит,
:: что порт обслуживается, открывает браузер (Flet в нём не стартует) и
:: завершается.

set LOG=%APPDATA%\porayonka\web_startup.log

echo.
echo  Порайонка — Контроли (web-версия для Windows 7)
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

:: Ждём ответ сервера (до ~60 сек) — PowerShell 2.0+ (есть на Win7 SP1),
:: HttpWebRequest по портам 8555..8564. В файл с портом пишем ТОЛЬКО stdout:
:: stderr PowerShell мог испортить первую строку, из которой берётся %WEBPORT%.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$found=0; for($i=0;$i -lt 60;$i++){ foreach($p in 8555..8564){ try { $r=[System.Net.HttpWebRequest]::Create('http://127.0.0.1:'+$p+'/'); $r.Timeout=2000; $resp=$r.GetResponse(); $resp.Close(); Write-Output $p; $found=1; break } catch {} }; if($found){ break }; Start-Sleep -Seconds 1 }; if(-not $found){ exit 1 }" 1> "%TEMP%\porayonka_web_port.txt" 2>nul

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

set /p WEBPORT=<"%TEMP%\porayonka_web_port.txt"
del "%TEMP%\porayonka_web_port.txt" >nul 2>&1
:: в файле могла оказаться не-порт (пустая или битая строка) — берем только 85xx
echo %WEBPORT%|findstr /r "^85[0-9][0-9]$" >nul 2>&1 || set WEBPORT=8555

echo  Сервер запущен и отвечает.
echo.
echo  Адрес приложения:  http://127.0.0.1:%WEBPORT%
echo.
echo  Браузер открывает само приложение. Если окно браузера не
echo  появилось — откройте адрес выше вручную.
echo.
