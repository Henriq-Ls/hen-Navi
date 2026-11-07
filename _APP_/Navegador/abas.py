"""Abas móveis e fecháveis do navegador."""

from PySide6.QtWidgets import QTabWidget


class BrowserTabs(QTabWidget):
    """QTabWidget com suporte a fechamento e movimentação das abas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabsClosable(True)
        self.setMovable(True)
