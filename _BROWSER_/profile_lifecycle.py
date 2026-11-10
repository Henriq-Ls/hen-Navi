"""Ciclo de vida de perfis WebEngine temporários."""

from __future__ import annotations

from collections.abc import Callable

from _SERVICOS_.adblocker import AdBlockInterceptor
from _SERVICOS_.adblock_rules import BlocklistMatcher
from _APP_.private_startpage import remove_private_start_page
from PySide6.QtCore import QObject
from PySide6.QtWebEngineCore import QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView


class AnonymousProfileLease(QObject):
    """Mantém um perfil anônimo vivo até a última view ser destruída."""

    def __init__(
        self,
        parent,
        start_page_path: str,
        matcher: BlocklistMatcher,
        blocker_enabled: bool,
        configure_profile: Callable[[QWebEngineProfile], None],
        data_saver_enabled: bool = False,
    ):
        super().__init__(parent)
        self.start_page_path = start_page_path
        self.profile = QWebEngineProfile(self)
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies
        )
        configure_profile(self.profile)
        self.interceptor = AdBlockInterceptor(
            matcher,
            enabled=blocker_enabled,
            data_saver_enabled=data_saver_enabled,
            parent=self,
        )
        self.profile.setUrlRequestInterceptor(self.interceptor)
        self._view_count = 0
        self._closing = False

    def register_view(self, view: QWebEngineView):
        self._view_count += 1
        view.destroyed.connect(self._on_view_destroyed)

    def request_close(self):
        self._closing = True
        remove_private_start_page(self.start_page_path)
        self._release_if_ready()

    def _on_view_destroyed(self, *_):
        self._view_count = max(0, self._view_count - 1)
        self._release_if_ready()

    def _release_if_ready(self):
        if self._closing and self._view_count == 0:
            remove_private_start_page(self.start_page_path)
            self.profile.deleteLater()
            self.deleteLater()
