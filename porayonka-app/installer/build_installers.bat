@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

cd /d "%~dp0"

:: Поиск Inno Setup Compiler
set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\iscc.exe" (
    set "ISCC=C:\Program Files (x86)\Inno Setup 6\iscc.exe"
) else if exist "C:\Program Files\Inno Setup 6\iscc.exe" (
    set "ISCC=C:\Program Files\Inno Setup 6\iscc.exe"
) else (
    for %%p in (iscc.exe) do (
        set "ISCC=%%~$PATH:p"
    )
)

if "%~ISCC%"=="" (
    echo.
    echo [ОШИБКА] Inno Setup 6 (iscc.exe) не найден.
    echo Скачайте и установите с https://jrsoftware.org/isinfo.php
    echo.
    pause
    exit /b 1
)

echo ======================================================================
echo   Сборка установщиков Порайонки v2.0 DARK final
echo   Inno Setup Compiler: %ISCC%
echo ======================================================================
echo.

if not exist output mkdir output

echo [1/3] Сборка администраторского установщика...
"%ISCC%" Admin.iss
if errorlevel 1 (
    echo [ОШИБКА] Admin.iss
    exit /b 1
)

echo [2/3] Сборка пользовательского установщика...
"%ISCC%" User.iss
if errorlevel 1 (
    echo [ОШИБКА] User.iss
    exit /b 1
)

echo [3/3] Сборка web-установщика для Windows 7...
"%ISCC%" UserWeb.iss
if errorlevel 1 (
    echo [ОШИБКА] UserWeb.iss
    exit /b 1
)

echo.
echo ======================================================================
echo   ГОТОВО
echo ======================================================================
echo.
echo  Файлы установщиков в папке output\:
dir /b output\Порайонка_*_Setup.exe
echo.
explorer output
pause
