; AdminWeb.iss
; Установщик АДМИНСКОЙ web-версии Порайонки для Windows 7 (раунд 37, задача 3)
; Нативный клиент Flet на Win7 не работает — web-режим: локальный сервер +
; браузер. Полная редакция (импорт/редактирование), без страницы ФИО.
; Автозапуск ВСЕГДА (как в остальных редакциях, раунд 28), запуск приложения
; только на ФИНАЛЬНОЙ странице мастера.

#include "Common.iss"

; Раунд 38 (задача 4): константы для CommonUninstall.iss
#define EditionExeName "Порайонка_Админ_Web.exe"
#define EditionSuffix "0004"
#define EditionLabel "Администратор (Web)"

[Setup]
AppId={{A26A1A26-0004-0004-0004-0123456789AB}
AppName=Порайонка — Администратор (Web для Win7)
AppVersion={#AppVersion}
AppVerName=Порайонка v{#AppVersion} — Администратор (Web для Win7)
AppPublisher={#AppPublisher}
AppComments=Полная web-редакция для Windows 7: импорт, редактирование, управление контролями.
DefaultDirName={#DefaultDirRoot}_Админ_Web
DefaultGroupName={#AppGroupName}
OutputDir={#OutputDir}
OutputBaseFilename=Порайонка_Админ_Web_Setup
SetupIconFile=images\icon_admin_web.ico
WizardImageFile={#WizardImageFile}
WizardSmallImageFile={#WizardSmallImageFile}
Compression={#Compression}
SolidCompression={#SolidCompression}
PrivilegesRequired={#PrivilegesRequired}
UninstallDisplayName=Порайонка — Администратор (Web для Win7)
UninstallDisplayIcon={app}\icon_admin_web.ico
CloseApplications=force

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist_all\Порайонка_Админ_Web\Порайонка_Админ_Web.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist_all\Порайонка_Админ_Web\start_web_win7.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist_all\Порайонка_Админ_Web\edition.json"; DestDir: "{app}"; Flags: ignoreversion
; Раунд 37 (задача 2): DLL-стаб для Python 3.11 на Windows 7 (рядом с exe —
; первый каталог поиска зависимостей python311.dll). Файл обязателен:
; build_all_distributives.bat останавливается до запуска Inno Setup, если DLL
; отсутствует или не проходит проверку SHA256.
Source: "..\dist_all\Порайонка_Админ_Web\api-ms-win-core-path-l1-1-0.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "images\icon_admin_web.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "readme\README_AdminWeb.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "license.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Порайонка — Администратор (Web)"; Filename: "{app}\start_web_win7.bat"; IconFilename: "{app}\icon_admin_web.ico"
Name: "{autodesktop}\Порайонка — Администратор (Web)"; Filename: "{app}\start_web_win7.bat"; IconFilename: "{app}\icon_admin_web.ico"; Tasks: desktopicon

; Автозапуск ВСЕГДА (без чекбокса на странице задач) — раунд 28
[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "PorayonkaAdminWeb"; ValueData: """{app}\start_web_win7.bat"""; Flags: uninsdeletevalue

; Раунд 38 (задача 4, P0): после деинсталляции не должно остаться НИЧЕГО
; в {app}: Inno сам считает «своими» только установленные файлы, а приложение
; и установщик создают ещё edition.json.bak, логи и пр. У каждой редакции
; свой {app} — папка другой редакции здесь не затрагивается.
[UninstallDelete]
Type: filesandordirs; Name: "{app}"

; Запуск — только финальная страница мастера (postinstall без Tasks) — раунд 28
[Run]
Filename: "{app}\start_web_win7.bat"; Description: "{cm:LaunchProgram,Порайонка — Администратор (Web)}"; Flags: nowait postinstall skipifsilent

[Code]
procedure SaveStringToUTF8File(const FileName, Value: String; Append: Boolean);
var
  Lines: TArrayOfString;
begin
  SetArrayLength(Lines, 1);
  Lines[0] := Value;
  SaveStringsToUTF8File(FileName, Lines, Append);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  EditionPath: String;
  Json: String;
begin
  if CurStep = ssPostInstall then
  begin
    { edition.json admin-редакции; пароль НЕ пишем (живёт в %APPDATA%,
      задаётся из настроек приложения) }
    { Раунд 37: запись СТРОГО в UTF-8 (SaveStringToUTF8File, Inno 6.1+) }
    EditionPath := ExpandConstant('{app}\edition.json');
    Json := '{ "role": "admin" }';
    SaveStringToUTF8File(EditionPath, Json, False);
    { Раунд 29 (задача 8): запасная копия .bak — защита от случайного
      удаления edition.json (приложение восстановит основной из копии) }
    SaveStringToUTF8File(ExpandConstant('{app}\edition.json.bak'), Json, False);
  end;
end;

; Раунд 38 (задача 4): полное и безопасное удаление (общий код 4 редакций)
#include "CommonUninstall.iss"
