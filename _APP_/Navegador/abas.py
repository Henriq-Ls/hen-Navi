"""Abas móveis e fecháveis do navegador."""

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication, QTabBar, QTabWidget


class BrowserTabBar(QTabBar):
    """Faixa de abas que mantém o botão de nova aba junto à última aba."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setExpanding(False)
        self._new_tab_button = None
        self._drag_origin = None
        self._window_position = None
        self._drag_started = False
        self._system_move_started = False
        self.tabMoved.connect(self._schedule_new_tab_button_position)

    def set_new_tab_button(self, button):
        self._new_tab_button = button
        button.setParent(self)
        button.raise_()
        self.updateGeometry()
        self._schedule_new_tab_button_position()

    def new_tab_button(self):
        return self._new_tab_button

    def _schedule_new_tab_button_position(self, *_):
        QTimer.singleShot(0, self._position_new_tab_button)

    def _position_new_tab_button(self):
        button = self._new_tab_button
        if button is None:
            return
        if self.count() == 0:
            button.hide()
            return

        last_tab = max(
            (self.tabRect(index) for index in range(self.count())),
            key=lambda rect: rect.right(),
        )
        button_size = button.size()
        x = last_tab.right() + 2
        if x + button_size.width() > self.width():
            x = max(0, self.width() - button_size.width())
            if x <= last_tab.right():
                button.hide()
                return
        y = max(0, (self.height() - button_size.height()) // 2)
        button.move(x, y)
        button.raise_()
        button.show()

    def sizeHint(self):
        hint = super().sizeHint()
        button = self._new_tab_button
        if button is not None and self.count() > 0:
            hint.setWidth(hint.width() + button.sizeHint().width() + 2)
        return hint

    def _is_empty_drag_area(self, position):
        button = self._new_tab_button
        return self.tabAt(position) < 0 and not (
            button is not None
            and button.isVisible()
            and button.geometry().contains(position)
        )

    def mousePressEvent(self, event):
        position = event.position().toPoint()
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._is_empty_drag_area(position)
        ):
            self._drag_origin = event.globalPosition().toPoint()
            self._window_position = self.window().pos()
            self._drag_started = False
            self._system_move_started = False
            event.accept()
            return
        self._drag_origin = None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            self._drag_origin is None
            or not event.buttons() & Qt.MouseButton.LeftButton
        ):
            super().mouseMoveEvent(event)
            return

        position = event.globalPosition().toPoint()
        delta = position - self._drag_origin
        if not self._drag_started:
            if delta.manhattanLength() < QApplication.startDragDistance():
                event.accept()
                return
            self._drag_started = True
            handle = self.window().windowHandle()
            if handle is not None:
                try:
                    self._system_move_started = bool(handle.startSystemMove())
                except RuntimeError:
                    self._system_move_started = False

        if not self._system_move_started and self._window_position is not None:
            self.window().move(self._window_position + delta)
        event.accept()

    def mouseReleaseEvent(self, event):
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._drag_origin is not None
        ):
            self._clear_drag_state()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        position = event.position().toPoint()
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._is_empty_drag_area(position)
        ):
            toggle = getattr(self.window(), "_toggle_maximize_restore", None)
            if callable(toggle):
                toggle()
                event.accept()
                return
        super().mouseDoubleClickEvent(event)

    def _clear_drag_state(self):
        self._drag_origin = None
        self._window_position = None
        self._drag_started = False
        self._system_move_started = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_new_tab_button()

    def showEvent(self, event):
        super().showEvent(event)
        self._schedule_new_tab_button_position()

    def tabLayoutChange(self):
        super().tabLayoutChange()
        self._schedule_new_tab_button_position()

    def tabInserted(self, index):
        super().tabInserted(index)
        self.updateGeometry()
        self._schedule_new_tab_button_position()

    def tabRemoved(self, index):
        super().tabRemoved(index)
        self.updateGeometry()
        self._schedule_new_tab_button_position()


class BrowserTabs(QTabWidget):
    """QTabWidget com suporte a fechamento e movimentação das abas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._browser_tab_bar = BrowserTabBar(self)
        self.setTabBar(self._browser_tab_bar)
        self.setTabsClosable(True)
        self.setMovable(True)
        self._browser_tab_bar.setExpanding(False)

    def set_new_tab_button(self, button):
        self._browser_tab_bar.set_new_tab_button(button)

    def new_tab_button(self):
        return self._browser_tab_bar.new_tab_button()
