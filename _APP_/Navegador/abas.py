"""Abas do navegador, com a aba Principal presa no índice zero."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QTabBar, QTabWidget


class PinnedTabBar(QTabBar):
    """Impede o arraste da aba zero e corrige tentativas de movê-la para lá."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dragging_primary = False
        self._correcting_move = False

    def mousePressEvent(self, event: QMouseEvent):
        self._dragging_primary = self.tabAt(event.position().toPoint()) == 0
        if self._dragging_primary and event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging_primary:
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._dragging_primary:
            self._dragging_primary = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keep_primary_first(self, from_index: int, to_index: int):
        if self._correcting_move:
            return
        if from_index == 0:
            self._correcting_move = True
            self.moveTab(to_index, 0)
            self._correcting_move = False
        elif to_index == 0:
            self._correcting_move = True
            self.moveTab(0, from_index)
            self._correcting_move = False


class BrowserTabs(QTabWidget):
    """QTabWidget com barra customizada e suporte a fechamento/movimentação."""

    def __init__(self, parent=None):
        super().__init__(parent)
        bar = PinnedTabBar(self)
        self.setTabBar(bar)
        self.setTabsClosable(True)
        self.setMovable(True)
        bar.tabMoved.connect(bar.keep_primary_first)
