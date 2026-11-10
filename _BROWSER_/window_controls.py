"""Controles visuais reutilizáveis da janela e das abas do navegador."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QToolButton

from _ULTILIDADES_.icones import ico_fechar_aba, ico_fechar_aba_hover


class TabCloseButton(QToolButton):
    """Botão de fechar aba com feedback visual explícito ao passar o mouse."""

    def __init__(self, parent=None, *, font_size_px: int = 13):
        super().__init__(parent)
        self.setObjectName("tabCloseButton")
        self.setAutoRaise(True)
        self.apply_metrics(font_size_px)
        self.refresh_icon()

    def apply_metrics(self, font_size_px: int):
        size = max(24, int(font_size_px) + 10)
        icon_size = min(22, max(16, int(font_size_px) + 3))
        self.setIconSize(QSize(icon_size, icon_size))
        self.setFixedSize(QSize(size, size))

    def refresh_icon(self):
        icon = (
            ico_fechar_aba_hover() if self.underMouse() else ico_fechar_aba()
        )
        _set_button_icon_or_fallback(self, icon, "×")

    def enterEvent(self, event):
        self.setIcon(ico_fechar_aba_hover())
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setIcon(ico_fechar_aba())
        super().leaveEvent(event)


def _set_button_icon_or_fallback(
    button: QToolButton,
    icon: QIcon,
    fallback_text: str,
):
    """Keep small tab controls visible when the optional icon pack is absent."""
    button.setIcon(icon)
    if icon.isNull():
        button.setText(fallback_text)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        return
    button.setText("")
    button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)


class BrandMenuButton(QToolButton):
    """Botão do app que abre o menu e serve de alça para mover a janela."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._press_position: QPoint | None = None
        self._window_position: QPoint | None = None
        self._drag_started = False
        self._system_move_started = False
        self.clicked.connect(self._show_app_menu)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_position = event.globalPosition().toPoint()
            self._window_position = self.window().pos()
            self._drag_started = False
            self._system_move_started = False
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            self._press_position is None
            or not event.buttons() & Qt.MouseButton.LeftButton
        ):
            super().mouseMoveEvent(event)
            return

        position = event.globalPosition().toPoint()
        delta = position - self._press_position
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
        if event.button() == Qt.MouseButton.LeftButton and self._press_position:
            if not self._drag_started:
                self._show_app_menu()
            self._press_position = None
            self._window_position = None
            self._drag_started = False
            self._system_move_started = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _show_app_menu(self, *_):
        menu = self.menu()
        if menu is not None:
            menu.popup(self.mapToGlobal(QPoint(0, self.height())))
