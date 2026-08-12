; Admin.iss
; Установщик администраторской версии Порайонки

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
Name: "startup"; Description: "Добавить в автозапуск Windows"; GroupDescription: "Автозапуск:"; Flags: unchecked
Name: "runafterinstall"; Description: "{cm:LaunchProgram,Порайонка — Администратор}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist_all\Порайонка_Админ\Порайонка_Админ.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist_all\Порайонка_Админ\edition.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "images\icon_admin.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "readme\README_Admin.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "license.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Порайонка — Администратор"; Filename: "{app}\Порайонка_Админ.exe"; IconFilename: "{app}\icon_admin.ico"
Name: "{autodesktop}\Порайонка — Администратор"; Filename: "{app}\Порайонка_Админ.exe"; IconFilename: "{app}\icon_admin.ico"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "PorayonkaAdmin"; ValueData: """{app}\Порайонка_Админ.exe"""; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\Порайонка_Админ.exe"; Description: "{cm:LaunchProgram,Порайонка — Администратор}"; Flags: nowait postinstall skipifsilent; Tasks: runafterinstall

[Code]
var
  PasswordPage: TInputQueryWizardPage;

procedure InitializeWizard();
begin
  PasswordPage := CreateInputQueryPage(wpSelectTasks,
    'Пароль администратора',
    'Установите пароль для входа в администраторскую версию',
    'Если оставить поля пустыми, пароль запрашиваться не будет.');
  PasswordPage.Add('Пароль:', True);
  PasswordPage.Add('Подтверждение пароля:', True);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = PasswordPage.ID then
  begin
    if PasswordPage.Values[0] <> PasswordPage.Values[1] then
    begin
      MsgBox('Пароли не совпадают. Повторите ввод.', mbError, MB_OK);
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
  Password: String;
  Json: String;
begin
  if CurStep = ssPostInstall then
  begin
    EditionPath := ExpandConstant('{app}\edition.json');
    Password := PasswordPage.Values[0];
    if Password <> '' then
      Json := '{ "role": "admin", "password": "' + ReplaceQuotes(Password) + '" }'
    else
      Json := '{ "role": "admin" }';
    SaveStringToFile(EditionPath, Json, False);
  end;
end;
