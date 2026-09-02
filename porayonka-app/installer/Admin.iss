; Admin.iss
; Установщик администраторской версии Порайонки
; Раунд 28 (задача 1.1): автозапуск ВСЕГДА (без чекбокса), запуск приложения
; только на ФИНАЛЬНОЙ странице мастера, страница пароля УБРАНА — пароль
; задаётся в настройках приложения (пишется как password_hash в
; %APPDATA%\porayonka\edition.json, поэтому здесь его больше нет).

#include "Common.iss"

; Раунд 38 (задача 4): константы для CommonUninstall.iss
#define EditionExeName "Порайонка_Админ.exe"
#define EditionSuffix "0001"
#define EditionLabel "Администратор"

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

; Раунд 38 (задача 4, P0): после деинсталляции не должно остаться НИЧЕГО
; в {app}: Inno сам считает «своими» только установленные файлы, а приложение
; и установщик создают ещё edition.json.bak, логи и пр. У каждой редакции
; свой {app} — папка другой редакции здесь не затрагивается.
[UninstallDelete]
Type: filesandordirs; Name: "{app}"

; Запуск — только финальная страница мастера (postinstall без Tasks) — раунд 28
[Run]
Filename: "{app}\Порайонка_Админ.exe"; Description: "{cm:LaunchProgram,Порайонка — Администратор}"; Flags: nowait postinstall skipifsilent

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
