"""Moldura, controles de janela e integração de hit-test nativo."""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

from _CONFIGURA_ import TEXTO_UI
from _LOGS_ import log
from _ULTILIDADES_.icones import ico_janela_maximizar, ico_janela_restaurar
from PySide6.QtGui import QCursor


class BrowserWindowFrameMixin:
    """Comportamentos da moldura sem barra de título do navegador."""

    _WM_NCHITTEST = 0x0084
    _WM_NCLBUTTONUP = 0x00A2
    _HTMAXBUTTON = 9
    _HTLEFT = 10
    _HTRIGHT = 11
    _HTTOP = 12
    _HTTOPLEFT = 13
    _HTTOPRIGHT = 14
    _HTBOTTOM = 15
    _HTBOTTOMLEFT = 16
    _HTBOTTOMRIGHT = 17

    def _toggle_maximize_restore(self, *_):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self._update_window_controls()

    def showEvent(self, event):
        self._enable_windows_native_frame()
        super().showEvent(event)

    def _enable_windows_native_frame(self):
        """Habilita redimensionamento e encaixe nativos sem barra de título."""
        if sys.platform != "win32" or self._windows_frame_style_applied:
            return

        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            get_window_long = user32.GetWindowLongW
            set_window_long = user32.SetWindowLongW
            set_window_pos = user32.SetWindowPos
            get_window_long.argtypes = (wintypes.HWND, wintypes.INT)
            get_window_long.restype = wintypes.LONG
            set_window_long.argtypes = (
                wintypes.HWND,
                wintypes.INT,
                wintypes.LONG,
            )
            set_window_long.restype = wintypes.LONG
            set_window_pos.argtypes = (
                wintypes.HWND,
                wintypes.HWND,
                wintypes.INT,
                wintypes.INT,
                wintypes.INT,
                wintypes.INT,
                wintypes.UINT,
            )
            set_window_pos.restype = wintypes.BOOL

            hwnd = wintypes.HWND(int(self.winId()))
            current_style = get_window_long(hwnd, -16) & 0xFFFFFFFF
            required_styles = 0x00040000 | 0x00010000 | 0x00020000
            updated_style = current_style | required_styles

            if updated_style != current_style:
                ctypes.set_last_error(0)
                previous_style = set_window_long(
                    hwnd,
                    -16,
                    ctypes.c_int32(updated_style).value,
                )
                if previous_style == 0 and ctypes.get_last_error():
                    raise ctypes.WinError(ctypes.get_last_error())

                frame_changed = (
                    0x0001  # SWP_NOSIZE
                    | 0x0002  # SWP_NOMOVE
                    | 0x0004  # SWP_NOZORDER
                    | 0x0010  # SWP_NOACTIVATE
                    | 0x0020  # SWP_FRAMECHANGED
                )
                if not set_window_pos(
                    hwnd,
                    wintypes.HWND(0),
                    0,
                    0,
                    0,
                    0,
                    frame_changed,
                ):
                    raise ctypes.WinError(ctypes.get_last_error())

            self._windows_frame_style_applied = True
        except (AttributeError, OSError, TypeError, ValueError) as error:
            log.aviso(
                "BrowserWindow",
                "_enable_windows_native_frame",
                str(error),
            )

    def _windows_hit_test(self):
        """Devolve hit-test nativo para Snap Layouts e redimensionamento."""
        cursor_position = QCursor.pos()
        for button_name in (
            "minimize_window_button",
            "maximize_window_button",
            "close_window_button",
        ):
            button = getattr(self, button_name, None)
            if (
                button is None
                or not button.isVisible()
                or not button.rect().contains(button.mapFromGlobal(cursor_position))
            ):
                continue
            if button_name == "maximize_window_button":
                return self._HTMAXBUTTON
            return None

        if self.isMaximized() or self.isFullScreen():
            return None

        position = self.mapFromGlobal(cursor_position)
        width = self.width()
        height = self.height()
        border = 8
        on_left = position.x() < border
        on_right = position.x() >= width - border
        on_top = position.y() < border
        on_bottom = position.y() >= height - border

        if on_top and on_left:
            return self._HTTOPLEFT
        if on_top and on_right:
            return self._HTTOPRIGHT
        if on_bottom and on_left:
            return self._HTBOTTOMLEFT
        if on_bottom and on_right:
            return self._HTBOTTOMRIGHT
        if on_left:
            return self._HTLEFT
        if on_right:
            return self._HTRIGHT
        if on_top:
            return self._HTTOP
        if on_bottom:
            return self._HTBOTTOM
        return None

    def nativeEvent(self, eventType, message):
        if sys.platform == "win32":
            try:
                native_message = ctypes.cast(
                    int(message),
                    ctypes.POINTER(wintypes.MSG),
                ).contents
                if (
                    native_message.message == self._WM_NCLBUTTONUP
                    and native_message.wParam == self._HTMAXBUTTON
                ):
                    button = getattr(self, "maximize_window_button", None)
                    if button is not None and button.isEnabled():
                        button.click()
                        return True, 0
                if native_message.message == self._WM_NCHITTEST:
                    hit_test = self._windows_hit_test()
                    if hit_test is not None:
                        return True, hit_test
            except (TypeError, ValueError, OSError, ctypes.ArgumentError):
                pass
        return super().nativeEvent(eventType, message)

    def _update_window_controls(self):
        action = getattr(self, "maximize_window_action", None)
        if action is None:
            return
        if self.isMaximized():
            label = TEXTO_UI["window_restore"]
            action.setIcon(ico_janela_restaurar())
        else:
            label = TEXTO_UI["window_maximize"]
            action.setIcon(ico_janela_maximizar())
        action.setText(label)
        action.setToolTip(label)
        button = getattr(self, "maximize_window_button", None)
        if button is not None:
            button.setAccessibleName(label)
            button.setToolTip(label)
