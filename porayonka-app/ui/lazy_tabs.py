# ui/lazy_tabs.py
"""
Раунд 39 (задача 2): Ленивая инициализация тяжёлых вкладок UI.

Обеспечивает:
1. При старте приложения строится только активная вкладка «Контроли» (index 0).
2. Вкладки «Зональные криминалисты» (index 1) и «Следственные отделы» (index 2)
   строятся исключительно при первом переходе пользователя на них.
3. Построенные экземпляры сохраняются в кэше и при повторных переключениях
   не пересоздаются (build_count строго 1).
4. Безопасность мутаций и обновлений гарантируется синхронизацией через ui_lock().
"""
from typing import Callable, Dict, Optional
import flet as ft
from ui.update_lock import ui_lock


class LazyTabManager:
    """Менеджер ленивой загрузки и кэширования содержимого вкладок."""

    def __init__(self, page: ft.Page, verbose: bool = True):
        self.page = page
        self.verbose = verbose
        self._builders: Dict[int, Callable[[], ft.Control]] = {}
        self._cache: Dict[int, ft.Control] = {}
        self._containers: Dict[int, ft.Container] = {}
        self._build_counts: Dict[int, int] = {}
        self._tab_names: Dict[int, str] = {}
        self._active_index: int = 0

    def register_tab(
        self,
        index: int,
        name: str,
        container: ft.Container,
        builder: Callable[[], ft.Control],
        immediate: bool = False,
    ) -> None:
        """Регистрация вкладки с её builder-функцией и целевым контейнером."""
        self._tab_names[index] = name
        self._containers[index] = container
        self._builders[index] = builder
        self._build_counts[index] = 0
        if immediate:
            self.ensure_built(index)

    def is_built(self, index: int) -> bool:
        """Проверка, было ли уже создано содержимое вкладки."""
        return index in self._cache

    def get_build_count(self, index: int) -> int:
        """Число вызовов builder для указанной вкладки."""
        return self._build_counts.get(index, 0)

    def get_active_index(self) -> int:
        """Текущая активная вкладка."""
        return self._active_index

    def ensure_built(self, index: int) -> ft.Control:
        """Гарантирует построение вкладки (из кэша или вызовом builder)."""
        if index in self._cache:
            if self.verbose:
                print(f"[LAZY_TABS] Tab {index} ({self._tab_names.get(index, '')}) reused from cache [build_count={self._build_counts.get(index, 0)}]")
            return self._cache[index]

        builder = self._builders.get(index)
        if not builder:
            raise ValueError(f"No builder registered for tab index {index}")

        tab_name = self._tab_names.get(index, f"Tab_{index}")
        if self.verbose:
            print(f"[LAZY_TABS] Tab {index} ({tab_name}) building first time...")

        with ui_lock():
            content = builder()
            self._cache[index] = content
            self._build_counts[index] = self._build_counts.get(index, 0) + 1
            container = self._containers.get(index)
            if container is not None:
                container.content = content

        if self.verbose:
            print(f"[LAZY_TABS] Tab {index} ({tab_name}) build complete [count={self._build_counts[index]}]")
        return content

    def switch_to(self, index: int) -> None:
        """Переключение на указанную вкладку с ленивым построением."""
        self._active_index = index
        self.ensure_built(index)
        for i, container in self._containers.items():
            container.visible = (i == index)
