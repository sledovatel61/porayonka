# ui/update_lock.py
# Раунд 20 (задача 4): ГЛОБАЛЬНАЯ сериализация UI-мутаций и page.update().
#
# Причина регрессии из ЛОГ.txt 11.08.2026 (AssertionError
#   «assert self.__uid is not None» в flet_core/control.py:448/480 через
#   page.py:848 __prepare_update) — КОРЕНЬ глубже фикса раунда 19.
#
# Что выяснено по исходникам Flet 0.23.2:
#  1) flet_core/page.py → on_event_async: ЛЮБОЙ синхронный обработчик события
#     запускается через self.run_thread(handler, ce) — в ThreadPoolExecutor
#     (flet_runtime/app.py: executor = ThreadPoolExecutor(), дефолт до 32
#     потоков). То есть ДВА события (две клавиши в поиске, hover + клик,
#     клик + клик) исполняют наши тела обработчиков ПАРАЛЛЕЛЬНО.
#  2) page.update() атомарен сам по себе (внутри threading.Lock), НО лишь
#     против других update(). Мутации дерева (controls.clear()/append(),
#     пересборка строк таблицы из 131 контроля — десятки миллисекунд) этим
#     локом НЕ защищены: diff-движок (control.py build_update_commands,
#     SequenceMatcher по __previous_children) читает списки детей, которые
#     в этот момент перестраивает соседний поток.
#  3) Любое исключение посреди __prepare_update — ЯД: снапшоты
#     __previous_children части узлов уже обновлены, add-команды собраны,
#     но не отправлены (send идёт после полного prepare), uid'ы не
#     присвоены (page.py: __update → __prepare_update → send_commands →
#     __update_control_ids). При следующем update() diff встречает такого
#     потомка в обеих версиях списка («equal»), спускается в него с
#     update=True и падает на assert self.__uid — НАВСЕГДА. Отсюда симптом
#     раунда 20: «после ошибки ни один фильтр не работает», «не добавляется
#     человек в справочник» (перестройки списков молча падают в update).
#
# Решение: ЕДИНЫЙ re-entrant lock на уровне приложения —
#  * page.update оборачивается в lock (control.update() в flet_core внутри
#    зовёт page.update(self) — покрыты ВСЕ точечные обновления);
#  * page.run_thread оборачивается так, что ТЕЛО каждого синхронного
#    обработчика события исполняется под тем же lock — мутации+update
#    одного обработчика неделимы относительно других обработчиков;
#  * фоновый поллинг вкладки «Контроли» и так маршаллизуется в UI-loop
#    (раунд 19, _post_to_ui); его колбэки дополнительно берут этот lock.
# Итого двухсторонняя гонка «пересборка vs diff» устранена конструктивно,
# патч идемпотентен и не трогает версию Flet (апгрейд запрещён ТЗ).

import threading

_UI_LOCK = threading.RLock()
_installed_pages = set()


def ui_lock() -> threading.RLock:
    """Глобальный UI-lock приложения (для фоновых маршаллизованных колбэков)."""
    return _UI_LOCK


def install_update_serialization(page) -> None:
    """Обернуть page.update и page.run_thread глобальным RLock (идемпотентно).

    Безопасно для тестовых заглушек (PageStub): оборачиваем только то, что
    реально существует у объекта.
    """
    if page is None:
        return
    key = id(page)
    if key in _installed_pages:
        return
    _installed_pages.add(key)

    raw_update = getattr(page, "update", None)
    if callable(raw_update):
        def _locked_update(*args, _f=raw_update, **kwargs):
            with _UI_LOCK:
                return _f(*args, **kwargs)
        try:
            page.update = _locked_update
        except Exception:
            pass

    raw_run_thread = getattr(page, "run_thread", None)
    if callable(raw_run_thread):
        def _locked_run_thread(handler, *args, _f=raw_run_thread, **kwargs):
            def _serialized(*h_args, **h_kwargs):
                with _UI_LOCK:
                    return handler(*h_args, **h_kwargs)
            return _f(_serialized, *args, **kwargs)
        try:
            page.run_thread = _locked_run_thread
        except Exception:
            pass
