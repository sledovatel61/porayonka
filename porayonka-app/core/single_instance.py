# core/single_instance.py
"""
Раунд 39 (задача 4): Single-instance защита настольного приложения.

Гарантирует, что в один момент времени запущен ровно один desktop-процесс
приложения.
- На Windows используется именованный мьютекс (`Local\\Porayonka_SingleInstance_...`).
  При обнаружении работающего экземпляра (ERROR_ALREADY_EXISTS или ERROR_ACCESS_DENIED)
  повторный процесс корректно завершается без создания дублирующих иконок трея.
- На POSIX (Linux/macOS) используется файловая блокировка (fcntl.flock).
- Ошибки API четко диагностируются; fail-open допустим только при невозможности
  вызова API, но НЕ при ERROR_ALREADY_EXISTS / ERROR_ACCESS_DENIED.
"""
import os
import sys
import tempfile
import threading
from typing import Optional

_GLOBAL_GUARD: Optional["SingleInstanceGuard"] = None
_GUARD_LOCK = threading.Lock()

ERROR_ALREADY_EXISTS = 183
ERROR_ACCESS_DENIED = 5


class SingleInstanceGuard:
    """Кроссплатформенный страж единственного экземпляра приложения."""

    def __init__(self, name: str = "porayonka_desktop"):
        self.name = name
        self.mutex_name = f"Local\\Porayonka_SingleInstance_{name}"
        self._handle = None
        self._lock_file = None
        self._acquired = False
        self._lock = threading.Lock()

    @property
    def is_acquired(self) -> bool:
        return self._acquired

    def acquire(self) -> bool:
        """Попытка захватить блокировку единственного экземпляра.
        Возвращает True, если экземпляр единственный и блокировка захвачена.
        Возвращает False, если другой экземпляр уже запущен.
        """
        with self._lock:
            if self._acquired:
                return True

            if sys.platform == "win32":
                return self._acquire_windows()
            else:
                return self._acquire_posix()

    def _acquire_windows(self) -> bool:
        try:
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.windll.kernel32
            create_mutex = kernel32.CreateMutexW
            create_mutex.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
            create_mutex.restype = wintypes.HANDLE

            close_handle = kernel32.CloseHandle
            close_handle.argtypes = [wintypes.HANDLE]
            close_handle.restype = wintypes.BOOL

            handle = create_mutex(None, False, self.mutex_name)
            last_err = kernel32.GetLastError()

            if not handle:
                if last_err in (ERROR_ALREADY_EXISTS, ERROR_ACCESS_DENIED):
                    print(f"[SINGLE_INSTANCE] Mutex '{self.mutex_name}' already exists (err={last_err}). Another instance is running.")
                    return False
                # Неизвестная ошибка API - диагностируем и разрешаем запуск (fail-open)
                print(f"[SINGLE_INSTANCE] CreateMutexW error code: {last_err}. Fail-open allowed.")
                self._acquired = True
                return True

            if last_err in (ERROR_ALREADY_EXISTS, ERROR_ACCESS_DENIED):
                print(f"[SINGLE_INSTANCE] Mutex '{self.mutex_name}' already owned by another process (err={last_err}).")
                try:
                    close_handle(handle)
                except Exception:
                    pass
                return False

            self._handle = handle
            self._acquired = True
            print(f"[SINGLE_INSTANCE] Acquired mutex '{self.mutex_name}'.")
            return True
        except Exception as ex:
            print(f"[SINGLE_INSTANCE] Windows mutex acquisition failed with exception: {ex}")
            # Fail-open при невозможности вызвать API
            self._acquired = True
            return True

    def _acquire_posix(self) -> bool:
        try:
            import fcntl
            lock_dir = tempfile.gettempdir()
            lock_path = os.path.join(lock_dir, f"porayonka_{self.name}.lock")
            f = open(lock_path, "w")
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                self._lock_file = f
                self._acquired = True
                print(f"[SINGLE_INSTANCE] Acquired POSIX lock on '{lock_path}'.")
                return True
            except (BlockingIOError, IOError, OSError):
                f.close()
                print(f"[SINGLE_INSTANCE] POSIX lock '{lock_path}' is busy. Another instance is running.")
                return False
        except Exception as ex:
            print(f"[SINGLE_INSTANCE] POSIX lock exception: {ex}. Fail-open.")
            self._acquired = True
            return True

    def release(self) -> None:
        """Освобождение блокировки единственного экземпляра."""
        with self._lock:
            if not self._acquired:
                return

            if sys.platform == "win32" and self._handle:
                try:
                    import ctypes
                    from ctypes import wintypes
                    close_handle = ctypes.windll.kernel32.CloseHandle
                    close_handle.argtypes = [wintypes.HANDLE]
                    close_handle.restype = wintypes.BOOL
                    close_handle(self._handle)
                    print(f"[SINGLE_INSTANCE] Released mutex '{self.mutex_name}'.")
                except Exception as ex:
                    print(f"[SINGLE_INSTANCE] CloseHandle error: {ex}")
                self._handle = None

            if self._lock_file:
                try:
                    import fcntl
                    fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
                    self._lock_file.close()
                    print("[SINGLE_INSTANCE] Released POSIX lock.")
                except Exception as ex:
                    print(f"[SINGLE_INSTANCE] Unlock error: {ex}")
                self._lock_file = None

            self._acquired = False

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


def acquire_single_instance(name: str = "porayonka_desktop") -> Optional[SingleInstanceGuard]:
    """Глобальный захват стража единственного экземпляра."""
    global _GLOBAL_GUARD
    with _GUARD_LOCK:
        if _GLOBAL_GUARD is not None and _GLOBAL_GUARD.is_acquired:
            return _GLOBAL_GUARD
        guard = SingleInstanceGuard(name)
        if guard.acquire():
            _GLOBAL_GUARD = guard
            return guard
        return None


def release_single_instance() -> None:
    """Глобальное освобождение стража единственного экземпляра."""
    global _GLOBAL_GUARD
    with _GUARD_LOCK:
        if _GLOBAL_GUARD is not None:
            _GLOBAL_GUARD.release()
            _GLOBAL_GUARD = None


def get_active_guard() -> Optional[SingleInstanceGuard]:
    """Возвращает текущий активный страж или None."""
    return _GLOBAL_GUARD
