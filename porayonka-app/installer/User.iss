; User.iss
; Установщик пользовательской версии Порайонки (Win10/11)

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
Name: "startup"; Description: "Добавить в автозапуск Windows"; GroupDescription: "Автозапуск:"; Flags: unchecked
Name: "runafterinstall"; Description: "{cm:LaunchProgram,Порайонка — Пользователь}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist_all\Порайонка_Пользователь\Порайонка_Пользователь.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist_all\Порайонка_Пользователь\edition.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "images\icon_user.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "readme\README_User.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "license.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Порайонка — Пользователь"; Filename: "{app}\Порайонка_Пользователь.exe"; IconFilename: "{app}\icon_user.ico"
Name: "{autodesktop}\Порайонка — Пользователь"; Filename: "{app}\Порайонка_Пользователь.exe"; IconFilename: "{app}\icon_user.ico"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "PorayonkaUser"; ValueData: """{app}\Порайонка_Пользователь.exe"""; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\Порайонка_Пользователь.exe"; Description: "{cm:LaunchProgram,Порайонка — Пользователь}"; Flags: nowait postinstall skipifsilent; Tasks: runafterinstall

[Code]
var
  FIOPage: TInputQueryWizardPage;

procedure InitializeWizard();
begin
  FIOPage := CreateInputQueryPage(wpSelectTasks,
    'ФИО пользователя',
    'Укажите ФИО для привязки контролей и уведомлений',
    'Например: Иванов И.И.');
  FIOPage.Add('ФИО:', False);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = FIOPage.ID then
  begin
    if Trim(FIOPage.Values[0]) = '' then
    begin
      MsgBox('Введите ФИО пользователя.', mbError, MB_OK);
      Result := False;
    end;
  end;
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
    EditionPath := ExpandConstant('{app}\edition.json');
    FIO := Trim(FIOPage.Values[0]);
    Json := '{ "role": "user", "user_name": "' + ReplaceQuotes(FIO) + '" }';
    SaveStringToFile(EditionPath, Json, False);
  end;
end;
