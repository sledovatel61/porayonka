; Admin.iss
; Установщик администраторской версии Порайонки
; Раунд 28 (задача 1.1): автозапуск ВСЕГДА (без чекбокса), запуск приложения
; только на ФИНАЛЬНОЙ странице мастера, страница пароля УБРАНА — пароль
; задаётся в настройках приложения (пишется как password_hash в
; %APPDATA%\porayonka\edition.json, поэтому здесь его больше нет).

#include "Common.iss"

[Setup]
AppId={{A26A1A26-0001-0001-0001-0123456789AB}
AppName=Порайонка — Администратор
AppVersion={#AppVersion}
AppVerName=Порайонка v{#AppVersion} — Администратор
AppPublisher={#AppPublisher}
AppComments=Полная редакция для администраторов: импорт, редактирование, управление контролями.
DefaultDirName={#DefaultDirRoot}_Админ
DefaultGroupName={#AppGroupName}
OutputDir={#OutputDir}
OutputBaseFilename=Порайонка_Админ_Setup
SetupIconFile=images\icon_admin.ico
WizardImageFile={#WizardImageFile}
WizardSmallImageFile={#WizardSmallImageFile}
Compression={#Compression}
SolidCompression={#SolidCompression}
PrivilegesRequired={#PrivilegesRequired}
UninstallDisplayName=Порайонка — Администратор
UninstallDisplayIcon={app}\icon_admin.ico
CloseApplications=force

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist_all\Порайонка_Админ\Порайонка_Админ.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist_all\Порайонка_Админ\edition.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "images\icon_admin.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "readme\README_Admin.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "license.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Порайонка — Администратор"; Filename: "{app}\Порайонка_Админ.exe"; IconFilename: "{app}\icon_admin.ico"
Name: "{autodesktop}\Порайонка — Администратор"; Filename: "{app}\Порайонка_Админ.exe"; IconFilename: "{app}\icon_admin.ico"; Tasks: desktopicon

; Автозапуск ВСЕГДА (без чекбокса на странице задач) — раунд 28
[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "PorayonkaAdmin"; ValueData: """{app}\Порайонка_Админ.exe"""; Flags: uninsdeletevalue

; Запуск — только финальная страница мастера (postinstall без Tasks) — раунд 28
[Run]
Filename: "{app}\Порайонка_Админ.exe"; Description: "{cm:LaunchProgram,Порайонка — Администратор}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  EditionPath: String;
  Json: String;
begin
  if CurStep = ssPostInstall then
  begin
    { edition.json admin-редакции; пароль НЕ пишем (живёт в %APPDATA%,
      задаётся из настроек приложения) }
    EditionPath := ExpandConstant('{app}\edition.json');
    Json := '{ "role": "admin" }';
    SaveStringToFile(EditionPath, Json, False);
  end;
end;
