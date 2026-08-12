; UserWeb.iss
; Установщик пользовательской web-версии Порайонки для Windows 7

#include "Common.iss"

[Setup]
AppId={{A26A1A26-0003-0003-0003-0123456789AB}
AppName=Порайонка — Пользователь (Web для Win7)
AppVersion={#AppVersion}
AppVerName=Порайонка v{#AppVersion} — Пользователь (Web для Win7)
AppPublisher={#AppPublisher}
AppComments=Web-версия для Windows 7: локальный сервер + браузер, уведомления в трее.
DefaultDirName={#DefaultDirRoot}_Web
DefaultGroupName={#AppGroupName}
OutputDir={#OutputDir}
OutputBaseFilename=Порайонка_Пользователь_Web_Setup
SetupIconFile=images\icon_user_web.ico
WizardImageFile={#WizardImageFile}
WizardSmallImageFile={#WizardSmallImageFile}
Compression={#Compression}
SolidCompression={#SolidCompression}
PrivilegesRequired={#PrivilegesRequired}
UninstallDisplayName=Порайонка — Пользователь (Web для Win7)
UninstallDisplayIcon={app}\icon_user_web.ico
CloseApplications=force

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startup"; Description: "Добавить в автозапуск Windows"; GroupDescription: "Автозапуск:"; Flags: unchecked
Name: "runafterinstall"; Description: "{cm:LaunchProgram,Порайонка — Пользователь (Web)}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist_all\Порайонка_Пользователь_Web\Порайонка_Пользователь_Web.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist_all\Порайонка_Пользователь_Web\start_web_win7.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist_all\Порайонка_Пользователь_Web\edition.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "images\icon_user_web.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "readme\README_Web.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "license.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Порайонка — Пользователь (Web)"; Filename: "{app}\start_web_win7.bat"; IconFilename: "{app}\icon_user_web.ico"
Name: "{autodesktop}\Порайонка — Пользователь (Web)"; Filename: "{app}\start_web_win7.bat"; IconFilename: "{app}\icon_user_web.ico"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "PorayonkaWeb"; ValueData: """{app}\start_web_win7.bat"""; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\start_web_win7.bat"; Description: "{cm:LaunchProgram,Порайонка — Пользователь (Web)}"; Flags: nowait postinstall skipifsilent; Tasks: runafterinstall

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
