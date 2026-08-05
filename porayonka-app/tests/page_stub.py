"""Page-заглушка для headless-смок-тестов вкладки «Контроли» (Flet 0.23.2).

create_controls_tab требует page с: width, window.height, overlay (list),
update/open/close/set_clipboard, on_resize (settable). Контролы не монтируются
(control.page остаётся None), поэтому все обновления через _safe_update
пропускаются — это и есть предмет проверки «чистого» init.
"""


class _Win:
    def __init__(self, height=860):
        self.height = height


class PageStub:
    def __init__(self, width=1280, height=860):
        self.width = width
        self.window = _Win(height)
        self.overlay = []
        self.toasts = []
        self.dialogs = []
        self.on_resize = None
        self.clipboard = None
        self._controls_poll_stop = None

    def update(self):
        pass

    def open(self, dlg):
        self.dialogs.append(dlg)

    def close(self, dlg):
        if dlg in self.dialogs:
            self.dialogs.remove(dlg)

    def set_clipboard(self, text):
        self.clipboard = text
