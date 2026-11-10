"""Painel DevTools ligado somente à página selecionada."""

from __future__ import annotations

from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QVBoxLayout, QWidget

from _CONFIGURA_ import TEXTO_UI


class DevToolsPanel(QWidget):
    """Frontend DevTools do Chromium ligado somente à aba selecionada."""

    def __init__(self, profile: QWebEngineProfile, parent=None):
        super().__init__(parent)
        self.setWindowTitle(TEXTO_UI["devtools_title"])
        self._attached_page: QWebEnginePage | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.view = QWebEngineView(self)
        self.view.setObjectName("chromiumDevToolsView")
        self.devtools_page = QWebEnginePage(profile, self.view)
        self.view.setPage(self.devtools_page)
        layout.addWidget(self.view, 1)

    def set_page(self, page: QWebEnginePage | None) -> None:
        if page is self._attached_page:
            return
        if self._attached_page is not None:
            try:
                self._attached_page.setDevToolsPage(None)
            except (AttributeError, RuntimeError):
                pass
        self._attached_page = page
        if page is not None:
            try:
                page.setDevToolsPage(self.devtools_page)
            except (AttributeError, RuntimeError):
                self._attached_page = None

    def detach(self) -> None:
        self.set_page(None)
