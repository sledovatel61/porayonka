# core/edition.py
# Раунд 23 (задача 2): редакция дистрибутива — «admin» (полная) / «user»
# (просмотр + уведомления). Редакция задаётся при сборке/установке, а не в
# настройках пользователя: её нельзя переопределить изнутри приложения.
# Раунд 37: ИДЕНТИЧНОСТЬ сборки сделана живучей к переносу файлов —
# встроенный edition.json ВНУТРИ exe (datas PyInstaller -> _MEIPASS) и
# правило имени exe («пользователь»/«админ») как запасной определитель.
import json
import os
import sys
from pathlib import Path
from typing import Optional

EDITION_ADMIN = "admin"
EDITION_USER = "user"

_cache: Optional[dict] = None


def _app_dir() -> Path:
    """Папка программы (рядом с exe в frozen-сборке / рядом с main.py в dev).

    Раунд 34 (задача 2): в frozen onefile PyInstaller sys.executable — путь
    к РЕАЛЬНОМУ exe, а sys._MEIPASS — временная папка распаковки. edition.json
    лежит РЯДОМ С EXE, поэтому берём Path(sys.executable).parent, НИКОГДА не
    _MEIPASS и не sys.argv[0] (может быть относительным/из ярлыка).
    """
    if getattr(sys, "frozen", False):
        try:
            return Path(sys.executable).resolve().parent
        except Exception:
            pass
    return Path(__file__).resolve().parent.parent


def _appdata_edition_file() -> Path:
    appdata = os.getenv("APPDATA", str(Path.home() / ".config"))
    return Path(appdata) / "porayonka" / "edition.json"


def _embedded_edition_file() -> Optional[Path]:
    """Раунд 37: ВСТРОЕННЫЙ (запечённый при сборке) edition.json ВНУТРИ exe.

    Build-скрипты перед PyInstaller пишут `build_edition/edition.json`, а
    .spec добавляет его в datas с назначением «.» — в корень папки
    распаковки _MEIPASS. Перенос portable-сборки без рядом лежащих файлов
    редакцию больше НЕ теряет: идентичность живёт в самом exe.
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        try:
            return Path(meipass) / "edition.json"
        except Exception:
            return None
    return None


def _role_from_exe_name() -> Optional[str]:
    """Раунд 37: ПРАВИЛО ИМЕНИ exe — запасной определитель редакции, когда
    ВСЕ файлы редакции потеряны или битые, а appdata-наследие врёт.

    Дистрибутивные exe называются «Порайонка_Пользователь*.exe» /
    «Порайонка_Админ*.exe» — имя не теряется при копировании. Нейтральное
    имя (dev/python, переименованный exe) -> None (старое поведение).
    Кейс жалобы «user-сборка с admin-интерфейсом»: edition.json не доехал
    до машины пользователя — но exe называется «Пользователь», поэтому роль
    всё равно user, а не умолчательный admin.
    """
    try:
        name = Path(getattr(sys, "executable", "") or "").name.casefold()
    except Exception:
        return None
    if "пользователь" in name:
        return EDITION_USER
    if "админ" in name:
        return EDITION_ADMIN
    return None


# ── Раунд 37: диагностика определения редакции ──────────────────────────
# Требование промпта PROMPT_fix_user_installer.md: печатать путь exe, app_dir,
# наличие/содержимое edition.json рядом и в %APPDATA%, итоговую роль —
# ТОЛЬКО ASCII в print. У frozen GUI-exe (console=False) sys.stdout=None,
# поэтому вся диагностика дублируется в файл %APPDATA%/porayonka/
# edition_debug.log (перезаписывается на каждом старте приложения — его можно
# прислать разработчику вместо скриншота консоли).
_diag_lines: list = []


def _ascii(value) -> str:
    """ASCII-форма значения для print(): кириллица/прочее -> \\uXXXX-эскейпы
    (без потерь информации), консоли с любой codepage не упадут."""
    try:
        return str(value).encode("unicode_escape", "backslashreplace") \
            .decode("ascii", "replace")
    except Exception:
        return "?"


def _diag(msg: str) -> None:
    """Строка диагностики редакции: print (ASCII) + буфер для файлового лога
    (файл пишется _flush_diag() в конце load_edition)."""
    try:
        _diag_lines.append(str(msg))
    except Exception:
        pass
    try:
        print(_ascii(msg))
    except Exception:
        pass


def _debug_log_file() -> Path:
    appdata = os.getenv("APPDATA", str(Path.home() / ".config"))
    return Path(appdata) / "porayonka" / "edition_debug.log"


def _flush_diag() -> None:
    """Перезаписать %APPDATA%/porayonka/edition_debug.log накопленными
    строками (UTF-8; ошибки записи молча пропускаются — диагностика не
    должна ломать запуск)."""
    global _diag_lines
    lines, _diag_lines = _diag_lines, []
    if not lines:
        return
    try:
        import datetime as _dt37
        hdr = "=== " + _dt37.datetime.now().isoformat(timespec="seconds") + " ==="
        path = _debug_log_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(hdr + "\n" + "\n".join(lines) + "\n")
    except OSError:
        pass


def _diag_file(tag: str, path: Optional[Path]) -> None:
    """Одна строка о состоянии файла редакции: absent / invalid / role+user
    (пароль НЕ логируется — только флаг наличия)."""
    if path is None:
        _diag(f"[EDITION] {tag}: n/a")
        return
    try:
        if not path.exists():
            _diag(f"[EDITION] {tag} {path}: absent")
            return
        d = _read_edition_file(path)
        if d:
            has_pw = bool(str(d.get("password") or "").strip()
                          or str(d.get("password_hash") or "").strip())
            _diag(f"[EDITION] {tag} {path}: role={d.get('role')!r} "
                  f"user={d.get('user_name')!r} "
                  f"password={'set' if has_pw else '-'}")
        else:
            _diag(f"[EDITION] {tag} {path}: exists, INVALID JSON")
    except Exception as e:
        _diag(f"[EDITION] {tag} {path}: diag error: {e}")


def edition_file_candidates():
    """Кандидаты файла редакции (первый существующий побеждает).

    Установщик кладёт `edition.json` рядом с exe; в dev-режиме — рядом с
    main.py; переопределение на уровне пользователя — %APPDATA%/porayonka.
    Раунд 29 (задача 8): между exe-файлом и appdata вставлена запасная
    копия `edition.json.bak` — защита от случайного удаления основного файла
    (иначе приложение молча становилось admin-редакцией по умолчанию).
    Раунд 37: добавлен ВСТРОЕННЫЙ edition.json внутри exe (_MEIPASS).
    """
    candidates = [
        _app_dir() / "edition.json",
        _app_dir() / "edition.json.bak",
    ]
    embedded = _embedded_edition_file()
    if embedded is not None:
        candidates.append(embedded)
    candidates.append(_appdata_edition_file())
    return candidates


def _read_edition_file(path: Path) -> Optional[dict]:
    """Прочитать edition.json. Раунд 36 (задача 1): FALLBACK-КОДИРОВКИ.

    Установщик Inno Setup 6 пишет edition.json через SaveStringToFile в
    системной ANSI-кодировке (на русской Windows — CP1251). Если в JSON есть
    русское ФИО, чтение как UTF-8 падало UnicodeDecodeError и файл считался
    невалидным (раунд 35: -> default admin — «user-установщик даёт admin»).
    Теперь: utf-8-sig -> cp1251 -> locale.getpreferredencoding().
    """
    # cp866 — OEM-кодировка консоли cmd (старые build_user.bat писали
    # edition.json через echo). cp1251 — ANSI Inno Setup SaveStringToFile.
    encodings = ["utf-8-sig", "cp1251", "cp866"]
    try:
        import locale as _loc36
        _pref = _loc36.getpreferredencoding(False)
        if _pref and _pref.lower() not in ("utf-8", "utf8", "cp1251"):
            encodings.append(_pref)
    except Exception:
        pass
    last_err = None
    for enc in encodings:
        try:
            if path.exists():
                with open(path, "r", encoding=enc) as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
        except (OSError, ValueError) as e:
            last_err = e
            continue
    if last_err is not None:
        print(f"[EDITION] Oshibka chteniya {path}: {last_err}")
    return None


def _self_heal_edition_files() -> None:
    """Раунд 29 (задача 8) + раунд 34 + раунд 37: самовосстановление
    edition.json рядом с программой.

    - основного файла нет, а запасная копия .bak есть -> восстановить из
      .bak в ТОЙ ЖЕ папке;
    - раунд 37: нет ни основного, ни .bak, но есть ВСТРОЕННАЯ копия внутри
      exe (_MEIPASS, запечена сборкой) -> восстановить рядом с exe из неё
      (portable-папки доступны на запись; в Program Files запись молча
      пропустится — embedded продолжит работать как источник напрямую);
    - НИКОГДА не копировать edition.json из %APPDATA% в папку exe (иначе
      appdata-наследие «прилипало» бы к дистрибутиву).
    """
    main_f = _app_dir() / "edition.json"
    bak_f = _app_dir() / "edition.json.bak"
    try:
        if not main_f.exists() and bak_f.exists():
            import shutil
            shutil.copy2(bak_f, main_f)
            print("[EDITION] edition.json vosstanovlen iz edition.json.bak")
            return
    except OSError:
        pass
    try:
        embedded = _embedded_edition_file()
        if (not main_f.exists() and not bak_f.exists()
                and embedded is not None and embedded.exists()):
            import shutil
            shutil.copy2(embedded, main_f)
            _diag("[EDITION] edition.json vosstanovlen iz VSTROENNOJ kopii "
                  "vnutri exe (_MEIPASS)")
    except OSError:
        pass


def load_edition(force: bool = False) -> dict:
    """Вернуть редакцию: {"role": ..., "user_name": ..., "explicit": ...,
    "password"/"password_hash": ... (если заданы)}.

    Источники в порядке приоритета:
      1) переменные окружения PORAYONKA_EDITION / PORAYONKA_USER (dev/test);
      2) edition.json рядом с программой;
      3) edition.json.bak рядом с программой (раунд 29, задача 8 — защита
         от случайного удаления основного; при этом сам основной
         восстанавливается из копии — см. _self_heal_edition_files);
      4) ВСТРОЕННЫЙ edition.json внутри exe (раунд 37: datas PyInstaller ->
         _MEIPASS — переживает перенос exe без сопутствующих файлов);
      5) правило имени exe ПРИ КОНФЛИКТЕ (раунд 37): если имя exe даёт роль,
         а %APPDATA% — ДРУГУЮ, идентичность exe побеждает appdata-наследие
         (без унаследованных ФИО/пароля — диалог «Кто вы?» спросит сам);
      6) edition.json в %APPDATA%/porayonka (записывается, напр., первым
         запуском user-редакции после выбора ФИО);
      7) ПРАВИЛО ИМЕНИ exe (раунд 37): «пользователь» -> user,
         «админ» -> admin (только для дистрибутивных имён — спасает, когда
         ВСЕ файлы редакции потерялись при переносе);
      8) умолчание — admin (обратная совместимость со старыми установками).

    Роль (edition) берётся из самого приоритетного источника, а ФИО — из
    самого приоритетного источника, где оно НЕПУСТОЕ: установщик кладёт рядом
    с exe edition.json только с ролью, а выбранное при первом запуске ФИО
    живёт в %APPDATA% — без такого слияния диалог «Кто вы?» спрашивал бы
    снова при каждом запуске.

    "explicit" (раунд 26, задача 4): True, если роль задана ЯВНО (env /
    файлом / встроенно / именем exe), и False для умолчательного admin без
    edition.json — по нему сброс user-роли настроек делается только для
    настоящих admin-дистрибутивов, а старые установки без edition.json
    (роль из настроек) не ломаются.

    Раунд 26 (задача 5): поля "password" (plain, от установщика) и/или
    "password_hash" (base64 sha256) прокидываются как есть — используются
    парольным входом admin-редакции (ui/admin_gate.py).

    Раунд 31/32 (задача 1): в DEV-режиме (не frozen) env задаёт роль, а
    пароль/ФИО дополняются из %APPDATA%\\porayonka\\edition.json, если env
    их не задал.
    Раунд 34 (задача 2): ПРИОРИТЕТЫ переработаны: env — ТОЛЬКО для dev/тестов
    (не frozen); edition.json РЯДОМ С РЕАЛЬНЫМ exe (_app_dir) — АБСОЛЮТНЫЙ
    приоритет: если файл существует и валиден, читается ТОЛЬКО он (appdata
    НЕ мержится) — «Порайонка_Админ.exe» всегда admin,
    «Порайонка_Пользователь*.exe» всегда user, независимо от %APPDATA%.
    Раунд 37: идентичность НЕ теряется при переносе — см. встроенный
    edition.json (шаг 4), правило имени exe (шаг 6) и диагностику в файл
    %APPDATA%/porayonka/edition_debug.log + ASCII-print.
    """
    global _cache
    if _cache is not None and not force:
        return _cache
    _self_heal_edition_files()

    # Раунд 34/37: диагностика (print ASCII + файл edition_debug.log)
    app_dir = _app_dir()
    main_f = app_dir / "edition.json"
    bak_f = app_dir / "edition.json.bak"
    embedded_f = _embedded_edition_file()
    appdata_f = _appdata_edition_file()
    try:
        _diag(f"[EDITION] frozen={bool(getattr(sys, 'frozen', False))} "
              f"exe={getattr(sys, 'executable', '?')}")
        _diag(f"[EDITION] MEIPASS={getattr(sys, '_MEIPASS', None)}")
        _diag(f"[EDITION] app_dir={app_dir}")
        _diag_file("exe edition.json", main_f)
        _diag_file("exe edition.json.bak", bak_f)
        _diag_file("embedded edition.json", embedded_f
                   if getattr(sys, "frozen", False) else None)
        _diag_file("appdata edition.json", appdata_f)
        _diag(f"[EDITION] exe name rule -> {_role_from_exe_name()!r}")
    except Exception:
        pass

    def _mk(role_, user_, expl_, pw_, pwh_, src_):
        # Раунд 37: + "source" (откуда взялась роль: env/app_dir/app_dir.bak/
        # embedded/appdata/name/name.mismatch/default) — виден в диагностике.
        _cache = {"role": role_, "user_name": user_, "explicit": expl_,
                  "password": pw_, "password_hash": pwh_, "source": src_}
        try:
            _diag(f"[EDITION] source={src_} role={role_} "
                  f"user={user_ or '-'} explicit={expl_}")
            _flush_diag()
        except Exception:
            pass
        return _cache

    env_role = (os.getenv("PORAYONKA_EDITION") or "").strip().lower()
    # 1) env - tolko dev/testy
    if env_role in (EDITION_ADMIN, EDITION_USER) and not getattr(sys, "frozen", False):
        user_name = (os.getenv("PORAYONKA_USER") or "").strip()
        password = (os.getenv("PORAYONKA_ADMIN_PASSWORD") or "").strip()
        password_hash = (os.getenv("PORAYONKA_ADMIN_PASSWORD_HASH") or "").strip()
        try:
            _apd = _read_edition_file(_appdata_edition_file())
            if _apd:
                if not user_name:
                    user_name = str(_apd.get("user_name") or "").strip()
                if not password and not password_hash:
                    password = str(_apd.get("password") or "").strip()
                    password_hash = str(_apd.get("password_hash") or "").strip()
        except Exception:
            pass
        return _mk(env_role, user_name, True, password, password_hash, "env")

    # 2) edition.json ryadom s exe - ABSOLYuTNYJ prioritet (bez merge s appdata)
    data = _read_edition_file(main_f)
    if data:
        r = str(data.get("role") or "").strip().lower()
        if r in (EDITION_ADMIN, EDITION_USER):
            return _mk(r,
                       str(data.get("user_name") or "").strip(),
                       True,
                       str(data.get("password") or "").strip(),
                       str(data.get("password_hash") or "").strip(),
                       "app_dir")
    elif main_f.exists():
        # Файл рядом с exe есть, но НЕВАЛИДЕН (например, сборочный bat записал
        # \n как текст) — не падаем в appdata fallback, чтобы старый user-файл
        # в %APPDATA% не переопределял дистрибутив. Раунд 37: сначала
        # правило имени exe (битый json у «Пользователь» не должен давать
        # admin-интерфейс), затем — прежнее умолчание admin.
        named = _role_from_exe_name()
        if named is not None:
            _diag(f"[EDITION] WARN: {main_f} invalid JSON; exe name -> {named}")
            return _mk(named, "", True, "", "", "app_dir.invalid.name")
        print(f"[EDITION] WARN: {main_f} exists but invalid JSON, using default admin")
        return _mk(EDITION_ADMIN, "", True, "", "", "app_dir.invalid")
    # 3) edition.json.bak ryadom s exe
    data = _read_edition_file(bak_f)
    if data:
        r = str(data.get("role") or "").strip().lower()
        if r in (EDITION_ADMIN, EDITION_USER):
            return _mk(r,
                       str(data.get("user_name") or "").strip(),
                       True,
                       str(data.get("password") or "").strip(),
                       str(data.get("password_hash") or "").strip(),
                       "app_dir.bak")
    # 4) VSTROENNYJ edition.json vnutri exe (raund 37) - absolyutnyj,
    #    kak i ryadom lezhashchij: identichnost' zhorstko privyazana k sborki.
    if embedded_f is not None:
        data = _read_edition_file(embedded_f)
        if data:
            r = str(data.get("role") or "").strip().lower()
            if r in (EDITION_ADMIN, EDITION_USER):
                return _mk(r,
                           str(data.get("user_name") or "").strip(),
                           True,
                           str(data.get("password") or "").strip(),
                           str(data.get("password_hash") or "").strip(),
                           "embedded")
    # 5) raund 37: IDENTITY-MISMATCH — imya exe protivorechit appdata-role.
    #    Identichnost' exe (fajl/vstroennyj/IMYa) vazhnee appdata-naslediya:
    #    exe «Pol'zovatel'» na mashine, gde v %APPDATA% ostalsya admin,
    #    DOZhEN stat' user (ishodnaya zhaloba raunda 35/36). Bez merge —
    #    chuzhie FIO/parol' ne nasleduem, dialog «Kto vy?» sprosit sam.
    named = _role_from_exe_name()
    data = _read_edition_file(appdata_f)
    apd_role = ""
    if data:
        apd_role = str(data.get("role") or "").strip().lower()
    if (named is not None and apd_role in (EDITION_ADMIN, EDITION_USER)
            and apd_role != named):
        _diag(f"[EDITION] exe name '{named}' != appdata role "
              f"'{apd_role}'; exe identity wins")
        return _mk(named, "", True, "", "", "name.mismatch")
    # 6) appdata - tolko fallback
    if data:
        if apd_role in (EDITION_ADMIN, EDITION_USER):
            return _mk(apd_role,
                       str(data.get("user_name") or "").strip(),
                       True,
                       str(data.get("password") or "").strip(),
                       str(data.get("password_hash") or "").strip(),
                       "appdata")
        # Файл без role, но с паролем (save_appdata_password_hash из настроек)
        # - admin по умолчанию, пароль подхватывается (UI настроек пароля).
        if (str(data.get("password") or "").strip()
                or str(data.get("password_hash") or "").strip()):
            return _mk(EDITION_ADMIN,
                       str(data.get("user_name") or "").strip(),
                       False,
                       str(data.get("password") or "").strip(),
                       str(data.get("password_hash") or "").strip(),
                       "appdata")
    # 7) raund 37: PRAVILO IMENI exe - esli vse fajly poteryany, no exe
    #    nazyvaetsya «Pol'zovatel'»/«Admin», rol' vse ravno izvestna.
    if named is not None:
        _diag(f"[EDITION] no edition files; exe name rule -> {named}")
        return _mk(named, "", True, "", "", "name")
    # 8) umolchanie - admin (obratnaya sovmestimost')
    return _mk(EDITION_ADMIN, "", False, "", "", "default")


def is_user_edition() -> bool:
    return load_edition().get("role") == EDITION_USER


def save_appdata_edition(role: str, user_name: str = "") -> bool:
    """Записать редакцию в %APPDATA% (выбор ФИО пользователем при первом
    запуске user-редакции — чтобы не спрашивать снова).

    Раунд 28 (задача 7): слияние с существующим файлом — password_hash,
    записанный через настройки admin-редакции, не затирается."""
    path = _appdata_edition_file()
    try:
        data = _read_edition_file(path) or {}
        data["role"] = role
        data["user_name"] = user_name
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        load_edition(force=True)
        return True
    except OSError as e:
        print(f"[EDITION] Oshibka zapisi {path}: {e}")
        return False


def save_appdata_password_hash(password_hash: str = "") -> bool:
    """Раунд 28 (задача 7): записать/удалить password_hash администратора в
    %APPDATA%/porayonka/edition.json (merge; пустой hash — ключ убирается).
    Храним в appdata, а не рядом с exe: {app}\\edition.json затирается
    переустановкой, appdata — переживает обновление (но пропадёт при полном
    удалении профиля — ожидаемо)."""
    path = _appdata_edition_file()
    try:
        data = _read_edition_file(path) or {}
        if password_hash:
            data["password_hash"] = password_hash
        else:
            data.pop("password_hash", None)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        load_edition(force=True)
        return True
    except OSError as e:
        print(f"[EDITION] Oshibka zapisi {path}: {e}")
        return False


def apply_edition_to_settings(settings: dict) -> bool:
    """Перенести редакцию в настройки вкладки (role->network_role, ФИО ->
    network_user). Возвращает True, если settings изменились.

    user-редакция ПРИНУДИТЕЛЬНО переводит сетевую роль в «user» — обойти
    read-only правкой controls_settings.json нельзя.

    Раунд 26 (задача 4): ЯВНАЯ admin-редакция (edition.json/env) симметрично
    СБРАСЫВАЕТ user-роль/ФИО из настроек — иначе после user-сборки на той же
    машине admin-версия фильтровала контроли по старому network_user. Сброс
    только при explicit-редакции: старые установки без edition.json
    (роль хранится в настройках, раунды 7-22) не трогаем."""
    changed = False
    ed = load_edition()
    if ed.get("role") == EDITION_USER:
        if settings.get("network_role") != "user":
            settings["network_role"] = "user"
            changed = True
        nm = (ed.get("user_name") or "").strip()
        if nm and (settings.get("network_user") or "").strip() != nm:
            settings["network_user"] = nm
            changed = True
        # Раунд 27: user-дистрибутив без встроенного ФИО должен сбросить
        # старый network_user (например, после тестов admin), иначе
        # пользователь увидит чужие контроли и диалог "Кто вы?" не появится.
        if not nm and (settings.get("network_user") or "").strip():
            settings["network_user"] = ""
            changed = True
    elif ed.get("role") == EDITION_ADMIN and ed.get("explicit"):
        if settings.get("network_role") != "admin":
            settings["network_role"] = "admin"
            changed = True
        if (settings.get("network_user") or "").strip():
            settings["network_user"] = ""
            changed = True
    return changed


# ── Раунд 26 (задача 5): пароль входа admin-редакции ─────────────────────
# Пароль НЕ храним в открытом виде при сборке: base64(sha256(соль|пароль)) —
# достаточно «от случайного любопытства» (см. промпт). Установщик Inno Setup
# может писать либо "password_hash" (команда генерации ниже), либо plain
# "password" — принимаются оба поля, hash в приоритете.
_PASSWORD_SALT = "porayonka-admin-v26"


def admin_password_hash(password: str) -> str:
    """base64(sha256(salt|password)). Сгенерировать для edition.json:

        python -c "from core.edition import admin_password_hash as h; print(h('ПАРОЛЬ'))"
    """
    import base64
    import hashlib
    raw = hashlib.sha256(
        (_PASSWORD_SALT + "|" + (password or "")).encode("utf-8")).digest()
    return base64.b64encode(raw).decode("ascii")


def admin_password_required(ed: Optional[dict] = None) -> bool:
    """Пароль спрашивается только в admin-редакции и только если задан."""
    if ed is None:
        ed = load_edition()
    if (ed or {}).get("role") != EDITION_ADMIN:
        return False
    return bool((ed.get("password_hash") or ed.get("password") or "").strip())


def check_admin_password(ed: dict, password: str) -> bool:
    """Сверить введённый пароль с edition.json (hash приоритетнее plain)."""
    ph = ((ed or {}).get("password_hash") or "").strip()
    if ph:
        try:
            return admin_password_hash(password or "") == ph
        except Exception:
            return False
    plain = ((ed or {}).get("password") or "").strip()
    return bool(plain) and (password or "").strip() == plain
