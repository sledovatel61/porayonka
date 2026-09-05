# ui/lazy_tabs.py
# Раунд 39 (задача 2): ленивое создание тяжёлых вкладок.
#
# Корень медленного старта: main.py строил ВСЕ три вкладки до page.add(),
# хотя виден только один слот. LazyTabHost — реестр builder'ов с кэшем:
# на старте строится только активная вкладка, остальные — при первом
# переходе (успешная постройка — ровно ОДНА), экземпляр кэшируется,
# поэтому возврат на вкладку не пересоздаёт дерево и сохраняет состояние.
#
# Состав вкладок хост не трогает: получает ТЕ ЖЕ существующие builder-функции,
# меняются только момент и число вызовов — ни одна возможность Admin не
# теряется. Порядок вкладок и активная по умолчанию — зона main.py.
#
# Многопоточность: Flet 0.23.2 исполняет тела синхронных обработчиков в
# ThreadPoolExecutor (см. ui/update_lock.py), поэтому построение идёт под
# общим UI-lock приложения — «проверка кэша -> builder -> публикация» неделима
# относительно page.update() и фонового поллинга.
#
# Ошибка builder'а: вкладка НЕ считается построенной, частичный результат в
# кэш НЕ попадает, следующий переход пробует ещё раз (заглушка с текстом
# ошибки возвращается только для текущего перехода).


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
    его результат показывается вместо вкладки ЭТОТ раз (main.py рисует
    красный текст, как и до раунда 39), но в кэш не попадает: попытка
    повторяется при следующем переходе. Без on_error исключение
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
        self._builds: Dict[str, int] = {}      # успешные постройки (<= 1)
        self._attempts: Dict[str, int] = {}    # вызовы builder'а (с падениями)
        self._reuses: Dict[str, int] = {}
        self._failed: Dict[str, str] = {}

    # ── регистрация ────────────────────────────────────────────────
    _MISSING = object()

    def register(self, key: str, builder: Callable[[], Any]) -> None:
        """Повторная регистрация перезаписывает builder, но сохраняет кэш
        (иначе возврат на вкладку молча пересоздал бы дерево)."""
        with self._lock:
            self._builders[key] = builder
            self._builds.setdefault(key, 0)
            self._attempts.setdefault(key, 0)
            self._reuses.setdefault(key, 0)

    # ── доступ ─────────────────────────────────────────────────────
    def get(self, key: str) -> Any:
        """Вернуть содержимое вкладки; построить при первом обращении."""
        # Быстрый путь — без входа в lock.
        if key in self._cache:
            with self._lock:
                self._reuses[key] = self._reuses.get(key, 0) + 1
                self._log("reuse %s (total reuse=%d)"
                          % (key, self._reuses[key]))
            return self._cache[key]

        with self._lock:
            # ПОВТОРНАЯ проверка кэша уже внутри общего UI-lock: пока поток
            # ждал lock, соседний мог построить эту же вкладку.
            if key in self._cache:
                self._reuses[key] = self._reuses.get(key, 0) + 1
                self._log("reuse %s (total reuse=%d)"
                          % (key, self._reuses[key]))
                return self._cache[key]

            builder = self._builders.get(key)
            if builder is None:
                raise KeyError("LazyTabHost: no builder for %r" % (key,))

            self._attempts[key] = self._attempts.get(key, 0) + 1
            self._log("build %s (attempt=%d) ..." % (key, self._attempts[key]))
            try:
                content = builder()
            except BaseException as ex:      # noqa: BLE001 — см. on_error
                # Вкладка НЕ считается построенной: частичный результат в кэш
                # не кладём, следующий переход повторит попытку.
                self._failed[key] = "%s: %s" % (type(ex).__name__, ex)
                self._log("build %s FAILED: %s" % (key, self._failed[key]))
                if self._on_error is None:
                    raise
                return self._on_error(key, ex)
            self._builds[key] = self._builds.get(key, 0) + 1
            self._failed.pop(key, None)
            self._cache[key] = content
            self._log("build %s OK" % (key,))
            return content

    # ── диагностика (для тестов раунда 39) ─────────────────────────
    def is_built(self, key: str) -> bool:
        with self._lock:
            return key in self._cache

    def build_count(self, key: str) -> int:
        """Число УСПЕШНЫХ построек (больше 1 быть не должно)."""
        with self._lock:
            return self._builds.get(key, 0)

    def attempt_count(self, key: str) -> int:
        """Число вызовов builder'а: >1 только если была ошибка и retry."""
        with self._lock:
            return self._attempts.get(key, 0)

    def reuse_count(self, key: str) -> int:
        with self._lock:
            return self._reuses.get(key, 0)

    def built_keys(self):
        with self._lock:
            return sorted(self._cache.keys())

    def stats(self) -> Dict[str, int]:
        """Успешные постройки на вкладку (1 = построена, 0 = ещё нет)."""
        with self._lock:
            return {k: self._builds.get(k, 0) for k in self._builders}

    def attempt_stats(self) -> Dict[str, int]:
        with self._lock:
            return {k: self._attempts.get(k, 0) for k in self._builders}

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
