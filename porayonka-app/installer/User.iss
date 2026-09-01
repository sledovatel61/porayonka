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

procedure SaveStringToUTF8File(const FileName, Value: String; Append: Boolean);
var
  Lines: TArrayOfString;
begin
  SetArrayLength(Lines, 1);
  Lines[0] := Value;
  SaveStringsToUTF8File(FileName, Lines, Append);
end;

procedure InitializeWizard();
begin
  FIOPage := CreateInputQueryPage(wpSelectTasks,
    'ФИО пользователя',
    'Укажите ФИО для привязки контролей и уведомлений',
    'Например: Иванов И.И. (можно пропустить — приложение спросит при первом запуске)');
  FIOPage.Add('ФИО:', False);
end;

function Hex4(Value: Integer): String;
begin
  Result := Copy('0123456789abcdef', (Value div 4096) mod 16 + 1, 1) +
            Copy('0123456789abcdef', (Value div 256) mod 16 + 1, 1) +
            Copy('0123456789abcdef', (Value div 16) mod 16 + 1, 1) +
            Copy('0123456789abcdef', Value mod 16 + 1, 1);
end;

function JsonEscape(const S: String): String;
{ Раунд 37, приёмка: ФИО превращаем в ЧИСТЫЙ ASCII-JSON: кириллица и прочие
  не-ASCII символы -> \uXXXX (IntToHex, 4 знака). Так edition.json валиден
  при ЛЮБОЙ кодировке записи (UTF-8/ANSI/OEM) — проблема русского ФИО из
  раунда 36 закрыта окончательно и не зависит от функции записи Inno. }
var
  I: Integer;
  C: Integer;
begin
  Result := '';
  for I := 1 to Length(S) do
  begin
    C := Ord(S[I]);
    if C = 92 then
      Result := Result + '\\'
    else if C = 34 then
      Result := Result + '\"'
    else if (C >= 32) and (C <= 126) then
      Result := Result + Chr(C)
    else
      Result := Result + '\u' + Hex4(C);
  end;
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
    { Раунд 37: запись СТРОГО в UTF-8 (SaveStringToUTF8File, Inno 6.1+); }
    { содержимое к тому же чистый ASCII благодаря JsonEscape (см. выше). }
    EditionPath := ExpandConstant('{app}\edition.json');
    FIO := Trim(FIOPage.Values[0]);
    if FIO <> '' then
      Json := '{ "role": "user", "user_name": "' + JsonEscape(FIO) + '" }'
    else
      Json := '{ "role": "user" }';
    SaveStringToUTF8File(EditionPath, Json, False);
    { Раунд 29 (задача 8): запасная копия .bak — защита от случайного
      удаления edition.json (приложение восстановит основной из копии) }
    SaveStringToUTF8File(ExpandConstant('{app}\edition.json.bak'), Json, False);
  end;
end;
