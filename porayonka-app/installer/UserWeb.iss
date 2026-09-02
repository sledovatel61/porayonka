; UserWeb.iss
; Установщик пользовательской web-версии Порайонки для Windows 7
; Раунд 28 (задача 1.3): автозапуск ВСЕГДА (без чекбокса), запуск приложения
; только на ФИНАЛЬНОЙ странице мастера. Страница ФИО остаётся; ФИО можно
; пропустить — тогда приложение спросит его при первом запуске.

#include "Common.iss"

; Раунд 38 (задача 4): константы для CommonUninstall.iss
#define EditionExeName "Порайонка_Пользователь_Web.exe"
#define EditionSuffix "0003"
#define EditionLabel "Пользователь (Web)"

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

[Files]
Source: "..\dist_all\Порайонка_Пользователь_Web\Порайонка_Пользователь_Web.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist_all\Порайонка_Пользователь_Web\start_web_win7.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist_all\Порайонка_Пользователь_Web\edition.json"; DestDir: "{app}"; Flags: ignoreversion
; Раунд 37 (задача 2): DLL-стаб для Python 3.11 на Windows 7 (рядом с exe —
; первый каталог поиска зависимостей python311.dll). Файл обязателен:
; build_all_distributives.bat останавливается до запуска Inno Setup, если DLL
; отсутствует или не проходит проверку SHA256.
Source: "..\dist_all\Порайонка_Пользователь_Web\api-ms-win-core-path-l1-1-0.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "images\icon_user_web.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "readme\README_Web.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "license.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Порайонка — Пользователь (Web)"; Filename: "{app}\start_web_win7.bat"; IconFilename: "{app}\icon_user_web.ico"
Name: "{autodesktop}\Порайонка — Пользователь (Web)"; Filename: "{app}\start_web_win7.bat"; IconFilename: "{app}\icon_user_web.ico"; Tasks: desktopicon

; Автозапуск ВСЕГДА (без чекбокса на странице задач) — раунд 28
[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "PorayonkaWeb"; ValueData: """{app}\start_web_win7.bat"""; Flags: uninsdeletevalue

; Раунд 38 (задача 4, P0): после деинсталляции не должно остаться НИЧЕГО
; в {app}: Inno сам считает «своими» только установленные файлы, а приложение
; и установщик создают ещё edition.json.bak, логи и пр. У каждой редакции
; свой {app} — папка другой редакции здесь не затрагивается.
[UninstallDelete]
Type: filesandordirs; Name: "{app}"

; Запуск — только финальная страница мастера (postinstall без Tasks) — раунд 28
[Run]
Filename: "{app}\start_web_win7.bat"; Description: "{cm:LaunchProgram,Порайонка — Пользователь (Web)}"; Flags: nowait postinstall skipifsilent

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

; Раунд 38 (задача 4): полное и безопасное удаление (общий код 4 редакций)
#include "CommonUninstall.iss"
