# core/edition.py
# Раунд 23 (задача 2): редакция дистрибутива — «admin» (полная) / «user»
# (просмотр + уведомления). Редакция задаётся при сборке/установке, а не в
# настройках пользователя: её нельзя переопределить изнутри приложения.
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


def edition_file_candidates():
    """Кандидаты файла редакции (первый существующий побеждает).

    Установщик кладёт `edition.json` рядом с exe; в dev-режиме — рядом с
    main.py; переопределение на уровне пользователя — %APPDATA%/porayonka.
    Раунд 29 (задача 8): между exe-файлом и appdata вставлена запасная
    копия `edition.json.bak` — защита от случайного удаления основного файла
    (иначе приложение молча становилось admin-редакцией по умолчанию).
    """
    return [
        _app_dir() / "edition.json",
        _app_dir() / "edition.json.bak",
        _appdata_edition_file(),
    ]


def _read_edition_file(path: Path) -> Optional[dict]:
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
    except (OSError, ValueError) as e:
        print(f"[EDITION] Oshibka chteniya {path}: {e}")
    return None


def _self_heal_edition_files() -> None:
    """Раунд 29 (задача 8) + раунд 34: самовосстановление edition.json
    рядом с программой — ТОЛЬКО из .bak в ТОЙ ЖЕ папке.

    - основного файла нет, а запасная копия .bak есть -> восстановить из .bak;
    НИКОГДА не копировать edition.json из %APPDATA% в папку exe (иначе
    appdata-наследие «прилипало» бы к дистрибутиву). Запись может быть
    запрещена (Program Files) — мягко пропускаем.
    """
    main_f = _app_dir() / "edition.json"
    bak_f = _app_dir() / "edition.json.bak"
    try:
        if not main_f.exists() and bak_f.exists():
            import shutil
            shutil.copy2(bak_f, main_f)
            print("[EDITION] edition.json vosstanovlen iz edition.json.bak")
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
      4) edition.json в %APPDATA%/porayonka (записывается, напр., первым
         запуском user-редакции после выбора ФИО);
      5) умолчание — admin (обратная совместимость со старыми установками).

    Роль (edition) берётся из самого приоритетного источника, а ФИО — из
    самого приоритетного источника, где оно НЕПУСТОЕ: установщик кладёт рядом
    с exe edition.json только с ролью, а выбранное при первом запуске ФИО
    живёт в %APPDATA% — без такого слияния диалог «Кто вы?» спрашивал бы
    снова при каждом запуске.

    "explicit" (раунд 26, задача 4): True, если роль задана ЯВНО (env /
    файлом), и False для умолчательного admin без edition.json — по нему
    сброс user-роли настроек делается только для настоящих admin-дистрибутивов,
    а старые установки без edition.json (роль из настроек) не ломаются.

    Раунд 26 (задача 5): поля "password" (plain, от установщика) и/или
    "password_hash" (base64 sha256) прокидываются как есть — используются
    парольным входом admin-редакции (ui/admin_gate.py).

    Раунд 31/32 (задача 1): в DEV-режиме (не frozen) env задаёт роль, а
    пароль/ФИО дополняются из %APPDATA%\porayonka\edition.json, если env
    их не задал.
    Раунд 34 (задача 2): ПРИОРИТЕТЫ переработаны:
      1) env (role/user_name/пароль) — ТОЛЬКО для dev/тестов (не frozen);
      2) edition.json РЯДОМ С РЕАЛЬНЫМ exe (_app_dir) — АБСОЛЮТНЫЙ приоритет:
         если файл существует, читается ТОЛЬКО он (appdata НЕ мержится) —
         «Порайонка_Админ.exe» всегда admin, «Порайонка_Пользователь*.exe»
         всегда user, независимо от %APPDATA%;
      3) edition.json.bak рядом с exe;
      4) edition.json в %APPDATA% — только fallback;
      5) умолчание — admin.
    Диагностика (ASCII): путь к exe, _MEIPASS, выбранный app_dir, источник,
    итоговая роль/ФИО — печатаются в load_edition() для отладки на ПК.
    """
    global _cache
    if _cache is not None and not force:
        return _cache
    _self_heal_edition_files()

    # Раунд 34: ASCII-диагностика (frozen onefile: exe vs _MEI)
    try:
        print(f"[EDITION] frozen={bool(getattr(sys, 'frozen', False))} "
              f"exe={getattr(sys, 'executable', '?')}")
        print(f"[EDITION] MEIPASS={getattr(sys, '_MEIPASS', None)}")
    except Exception:
        pass
    app_dir = _app_dir()
    try:
        print(f"[EDITION] app_dir={app_dir}")
    except Exception:
        pass

    def _mk(role_, user_, expl_, pw_, pwh_, src_):
        _cache = {"role": role_, "user_name": user_, "explicit": expl_,
                  "password": pw_, "password_hash": pwh_}
        try:
            print(f"[EDITION] source={src_} role={role_} "
                  f"user={user_ or '-'} explicit={expl_}")
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
    data = _read_edition_file(app_dir / "edition.json")
    if data:
        r = str(data.get("role") or "").strip().lower()
        if r in (EDITION_ADMIN, EDITION_USER):
            return _mk(r,
                       str(data.get("user_name") or "").strip(),
                       True,
                       str(data.get("password") or "").strip(),
                       str(data.get("password_hash") or "").strip(),
                       "app_dir")
    # 3) edition.json.bak ryadom s exe
    data = _read_edition_file(app_dir / "edition.json.bak")
    if data:
        r = str(data.get("role") or "").strip().lower()
        if r in (EDITION_ADMIN, EDITION_USER):
            return _mk(r,
                       str(data.get("user_name") or "").strip(),
                       True,
                       str(data.get("password") or "").strip(),
                       str(data.get("password_hash") or "").strip(),
                       "app_dir.bak")
    # 4) appdata - tolko fallback
    data = _read_edition_file(_appdata_edition_file())
    if data:
        r = str(data.get("role") or "").strip().lower()
        if r in (EDITION_ADMIN, EDITION_USER):
            return _mk(r,
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
    # 5) umolchanie - admin (obratnaya sovmestimost')
    return _mk(EDITION_ADMIN, "", False, "", "", "default")

    return _cache


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
