; User.iss
; Установщик пользовательской версии Порайонки (Win10/11)
; Раунд 28 (задача 1.2): автозапуск ВСЕГДА (без чекбокса), запуск приложения
; только на ФИНАЛЬНОЙ странице мастера. Страница ФИО остаётся; ФИО можно
; пропустить — тогда приложение спросит его при первом запуске.

#include "Common.iss"

[Setup]
AppId={{A26A1A26-0002-0002-0002-0123456789AB}
AppName=Порайонка — Пользователь
AppVersion={#AppVersion}
AppVerName=Порайонка v{#AppVersion} — Пользователь
AppPublisher={#AppPublisher}
AppComments=Пользовательская редакция: просмотр контролей, уведомления о сроках, работа в трее.
DefaultDirName={#DefaultDirRoot}_Пользователь
DefaultGroupName={#AppGroupName}
OutputDir={#OutputDir}
OutputBaseFilename=Порайонка_Пользователь_Setup
SetupIconFile=images\icon_user.ico
WizardImageFile={#WizardImageFile}
WizardSmallImageFile={#WizardSmallImageFile}
Compression={#Compression}
SolidCompression={#SolidCompression}
PrivilegesRequired={#PrivilegesRequired}
UninstallDisplayName=Порайонка — Пользователь
UninstallDisplayIcon={app}\icon_user.ico
CloseApplications=force

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist_all\Порайонка_Пользователь\Порайонка_Пользователь.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist_all\Порайонка_Пользователь\edition.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "images\icon_user.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "readme\README_User.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "license.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Порайонка — Пользователь"; Filename: "{app}\Порайонка_Пользователь.exe"; IconFilename: "{app}\icon_user.ico"
Name: "{autodesktop}\Порайонка — Пользователь"; Filename: "{app}\Порайонка_Пользователь.exe"; IconFilename: "{app}\icon_user.ico"; Tasks: desktopicon

; Автозапуск ВСЕГДА (без чекбокса на странице задач) — раунд 28
[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "PorayonkaUser"; ValueData: """{app}\Порайонка_Пользователь.exe"""; Flags: uninsdeletevalue

; Запуск — только финальная страница мастера (postinstall без Tasks) — раунд 28
[Run]
Filename: "{app}\Порайонка_Пользователь.exe"; Description: "{cm:LaunchProgram,Порайонка — Пользователь}"; Flags: nowait postinstall skipifsilent

[Code]
var
  FIOPage: TInputQueryWizardPage;

procedure InitializeWizard();
begin
  FIOPage := CreateInputQueryPage(wpSelectTasks,
    'ФИО пользователя',
    'Укажите ФИО для привязки контролей и уведомлений',
    'Например: Иванов И.И. (можно пропустить — приложение спросит при первом запуске)');
  FIOPage.Add('ФИО:', False);
end;

function ReplaceQuotes(const S: String): String;
begin
  StringChangeEx(S, '\', '\\', True);
  StringChangeEx(S, '"', '\"', True);
  Result := S;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  EditionPath: String;
  FIO: String;
  Json: String;
begin
  if CurStep = ssPostInstall then
  begin
    { edition.json user-редакции; ФИО пустое — приложение спросит само }
    { Раунд 36: SaveStringToFile пишет в ANSI (CP1251 на русской Windows); }
    { Python _read_edition_file имеет fallback на cp1251 (см. core/edition.py). }
    EditionPath := ExpandConstant('{app}\edition.json');
    FIO := Trim(FIOPage.Values[0]);
    if FIO <> '' then
      Json := '{ "role": "user", "user_name": "' + ReplaceQuotes(FIO) + '" }'
    else
      Json := '{ "role": "user" }';
    SaveStringToFile(EditionPath, Json, False);
    { Раунд 29 (задача 8): запасная копия .bak — защита от случайного
      удаления edition.json (приложение восстановит основной из копии) }
    SaveStringToFile(ExpandConstant('{app}\edition.json.bak'), Json, False);
  end;
end;
