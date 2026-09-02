; CommonUninstall.iss
; Раунд 38 (задача 4, P0): общая логика ПОЛНОГО и БЕЗОПАСНОГО удаления
; для всех 4 редакций. Подключается (#include) в КОНЦЕ каждого .iss.
; От включающего файла требуются define-константы:
;   EditionExeName — точное имя exe редакции (taskkill ТОЛЬКО по нему,
;                    широкий «taskkill python.exe» категорически запрещён);
;   EditionLabel   — название редакции для сообщений;
;   EditionSuffix  — "0001".."0004" (свой AppId не считается «чужим»).
;
; Семантика:
;   * InitializeUninstall: точечная остановка процесса своей редакции.
;   * usPostUninstall: если осталась папка {userappdata}\porayonka — ЯВНЫЙ
;     вопрос «Удалить локальные данные и резервные копии» (по умолчанию НЕТ,
;     MB_DEFBUTTON2); при наличии рядом другой редакции — предупреждение,
;     что папка у них ОБЩАЯ. UNC/shared workspace НИКОГДА не трогаем.
;   * SILENT-деинсталляция — детерминированно: локальные данные НЕ удаляются
;     (нельзя показать подтверждение; сохранность данных важнее). Поведение
;     задокументировано в readme\<редакция>.txt.
[Code]

function _PorayonkaOtherEditionInstalled(const MySuffix: String): Boolean;
{ Установлена ли ДРУГАЯ редакция рядом (свой AppId пропускаем)? }
var
  Suffixes: array[0..3] of String;
  I: Integer;
  S, KeyU: String;
begin
  Result := False;
  Suffixes[0] := '0001';  { Администратор }
  Suffixes[1] := '0002';  { Пользователь }
  Suffixes[2] := '0003';  { Пользователь Web (Win7) }
  Suffixes[3] := '0004';  { Администратор Web (Win7) }
  for I := 0 to 3 do
  begin
    S := Suffixes[I];
    if S <> MySuffix then
    begin
      KeyU := '{A26A1A26-' + S + '-' + S + '-' + S + '-0123456789AB}_is1';
      if RegKeyExists(HKLM, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\' + KeyU)
         or RegKeyExists(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\' + KeyU)
         or RegKeyExists(HKCU, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\' + KeyU) then
      begin
        Result := True;
        exit;
      end;
    end;
  end;
end;

function InitializeUninstall(): Boolean;
{ Остановить ТОЛЬКО процессы этой редакции перед удалением файлов:
  точное имя образа exe (web-редакции — это и есть серверный процесс,
  запускаемый батником). Широкий «taskkill python.exe» НЕ используется. }
var
  Res: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /T /IM "{#EditionExeName}"',
       '', SW_HIDE, ewWaitUntilTerminated, Res);
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
  WarnOther: Boolean;
  MsgText: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{userappdata}\porayonka');
    if not DirExists(DataDir) then
      exit;
    if UninstallSilent() then
      exit;  { silent: данные НЕ удаляем (детерминированно, см. шапку) }
    WarnOther := _PorayonkaOtherEditionInstalled('{#EditionSuffix}');
    MsgText := 'Удалить локальные данные и резервные копии?' + #13#10#13#10 +
      'Будет безвозвратно удалена папка:' + #13#10 + DataDir + #13#10 +
      '(локальный кэш данных приложения, локальные копии вложений, ' +
      'ежедневные резервные копии).' + #13#10#13#10 +
      'Общая сетевая папка (workspace) НЕ удаляется никогда.' + #13#10#13#10 +
      'Выберите «Да» только при полном удалении программы (#EditionLabel).';
    if WarnOther then
      MsgText := MsgText + #13#10#13#10 +
        'ВНИМАНИЕ: на этом компьютере установлены другие редакции ' +
        '«Порайонки», и эта папка у них ОБЩАЯ — после удаления им ' +
        'придётся заново синхронизировать данные из общей папки.';
    if MsgBox(MsgText, mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
      DelTree(DataDir, True, True, True);
  end;
end;
