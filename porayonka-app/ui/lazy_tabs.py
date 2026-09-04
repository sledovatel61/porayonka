# ui/lazy_tabs.py
# ════════════════════════════════════════════════════════════════════════
# Раунд 39 (задача 2): ЛЕНИВОЕ создание тяжёлых вкладок.
# ════════════════════════════════════════════════════════════════════════
#
# КОРНЕВАЯ ПРИЧИНА медленного старта (ЛОГ.txt: «Порайонка открывается
# несколько секунд»): main.py строил ВСЕ три вкладки сразу —
# create_controls_tab() (131 контроль, канбан, календари, FilePicker'ы) и
# create_zonal_tab() (зональные криминалисты, сводные панели, шаблоны)
# вызывались ЕЩЁ ДО page.add(). Пользователь видит только «Контроли», но
# платит полную цену построения всех трёх деревьев.
#
# Решение: LazyTabHost — реестр builder'ов с кэшем экземпляров.
#  * на старте строится ТОЛЬКО активная вкладка;
#  * остальные — при первом переходе (ровно один вызов builder'а);
#  * экземпляр КЭШИРУЕТСЯ: при возврате на вкладку builder не вызывается
#    повторно, состояние (фильтры, открытая карточка, скролл) сохраняется;
#  * порядок вкладок и активная вкладка по умолчанию НЕ меняются — это
#    зона ответственности main.py (_switch_tab), хост про порядок не знает.
#
# ВАЖНО (сохранность Admin-функционала): хост НИЧЕГО не знает про вкладки.
# Он получает ТЕ ЖЕ существующие builder-функции (create_controls_tab,
# create_zonal_tab и обёртку над прежним inline-кодом отделов), поэтому ни
# одна возможность Admin не теряется: меняются ТОЛЬКО момент и число
# вызовов, не состав вкладок.
#
# Многопоточность: Flet 0.23.2 исполняет тела синхронных обработчиков
# событий в ThreadPoolExecutor (см. разбор в ui/update_lock.py). Два
# быстрых клика по разным вкладкам = два потока в get() одновременно.
# Поэтому построение идёт под lock'ом (по умолчанию — ОБЩИЙ UI-lock
# приложения из ui/update_lock.py, чтобы построение вкладки было неделимо
# относительно page.update() и фонового поллинга).

import threading
from typing import Any, Callable, Dict, Optional


def _shared_lock() -> threading.RLock:
    """Общий UI-lock приложения (ui/update_lock.py).

    Если модуль недоступен (изолированный unit-тест) — собственный RLock,
    поведение identical.
    """
    try:
        from ui.update_lock import ui_lock
        return ui_lock()
    except Exception:
        return threading.RLock()


class LazyTabHost:
    """Реестр ленивых вкладок: build-on-first-use + кэш экземпляра.

    Использование (main.py):

        host = LazyTabHost(page=page)
        host.register("controls",    _build_controls_tab)
        host.register("zonal",       _build_zonal_tab)
        host.register("departments", _build_departments_tab)

        content = host.get("controls")   # 1-й раз -> builder, дальше cache

    on_error: колбэк (key, exc) -> control. Если задан и builder упал —
    его результат используется как заглушка вкладки (main.py показывает
    красный текст ошибки, как и до раунда 39). Без on_error исключение
    пробрасывается наружу.
    """

    def __init__(self, page: Any = None,
                 on_error: Optional[Callable[[str, BaseException], Any]] = None,
                 diag: bool = False,
                 diag_prefix: str = "[LAZY_TABS]"):
        self._page = page
        self._on_error = on_error
        self._diag = bool(diag)
        self._diag_prefix = diag_prefix
        self._lock = _shared_lock()
        self._builders: Dict[str, Callable[[], Any]] = {}
        self._cache: Dict[str, Any] = {}
        self._builds: Dict[str, int] = {}
        self._reuses: Dict[str, int] = {}
        self._failed: Dict[str, str] = {}

    # ── регистрация ────────────────────────────────────────────────
    def register(self, key: str, builder: Callable[[], Any]) -> None:
        """Зарегистрировать builder вкладки. Повторная регистрация —
        перезаписывает builder, НО сохраняет уже построенный кэш
        (иначе возврат на вкладку молча пересоздал бы дерево)."""
        with self._lock:
            self._builders[key] = builder
            self._builds.setdefault(key, 0)
            self._reuses.setdefault(key, 0)

    # ── доступ ─────────────────────────────────────────────────────
    def get(self, key: str) -> Any:
        """Вернуть содержимое вкладки; построить при первом обращении."""
        with self._lock:
            if key in self._cache:
                self._reuses[key] = self._reuses.get(key, 0) + 1
                self._log("reuse %s (total reuse=%d)"
                          % (key, self._reuses[key]))
                return self._cache[key]

            builder = self._builders.get(key)
            if builder is None:
                raise KeyError("LazyTabHost: no builder for %r" % (key,))

            self._log("build %s ..." % (key,))
            try:
                content = builder()
            except BaseException as ex:      # noqa: BLE001 — см. on_error
                self._builds[key] = self._builds.get(key, 0) + 1
                self._failed[key] = "%s: %s" % (type(ex).__name__, ex)
                self._log("build %s FAILED: %s" % (key, self._failed[key]))
                if self._on_error is None:
                    raise
                content = self._on_error(key, ex)
            else:
                self._builds[key] = self._builds.get(key, 0) + 1
                self._log("build %s OK" % (key,))

            self._cache[key] = content
            return content

    # ── диагностика (для тестов раунда 39) ─────────────────────────
    def is_built(self, key: str) -> bool:
        with self._lock:
            return key in self._cache

    def build_count(self, key: str) -> int:
        """Сколько раз builder реально вызывался (не должно быть > 1)."""
        with self._lock:
            return self._builds.get(key, 0)

    def reuse_count(self, key: str) -> int:
        with self._lock:
            return self._reuses.get(key, 0)

    def built_keys(self):
        with self._lock:
            return sorted(self._cache.keys())

    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {k: self._builds.get(k, 0) for k in self._builders}

    def last_error(self, key: str) -> Optional[str]:
        with self._lock:
            return self._failed.get(key)

    def keys(self):
        with self._lock:
            return list(self._builders.keys())

    # ── ASCII-safe диагностика (opt-in) ────────────────────────────
    def _log(self, msg: str) -> None:
        if not self._diag:
            return
        try:
            # ASCII-safe: в frozen console=False / cp1251-терминале Win7
            # не-ASCII print может сам упасть и утащить переход во вкладку.
            safe = msg.encode("ascii", "replace").decode("ascii")
            print("%s %s" % (self._diag_prefix, safe))
        except Exception:
            pass
