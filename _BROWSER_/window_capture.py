"""Ações e feedback da captura de páginas pela janela do navegador."""

from __future__ import annotations

from pathlib import Path

from _CONFIGURA_ import (
    CAPTURA_ALTURA_MAXIMA_PX,
    CAPTURA_INTERVALO_REPINTURA_MS,
    CAPTURA_LARGURA_MAXIMA_PX,
    CAPTURA_PASTA,
    STATUS_CURTO_MS,
    STATUS_DOWNLOAD_INICIO_MS,
    TEXTO_UI,
    atalho,
)
from _ULTILIDADES_.capture_utils import capture_filename
from _ULTILIDADES_.explorer import Explorer, ExplorerMode
from _ULTILIDADES_.icones import ico_captura, ico_imagem, ico_pdf
from _ULTILIDADES_.popups import criar_popup, popup_aviso
from PySide6.QtCore import QStandardPaths, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QMenu, QMessageBox


class BrowserWindowCaptureMixin:
    """Ações de captura e mensagens associadas."""

    def _build_capture_menu(self):
        self.capture_menu = QMenu(TEXTO_UI["capture_menu"], self)
        self.visible_capture_action = self._make_action(
            TEXTO_UI["capture_visible"],
            ico_captura(),
            self.capture_visible_page,
        )
        self.full_page_capture_action = self._make_action(
            TEXTO_UI["capture_full_page"],
            ico_imagem(),
            self.capture_full_page,
        )
        self.pdf_capture_action = self._make_action(
            TEXTO_UI["capture_pdf"],
            ico_pdf(),
            self.save_page_as_pdf,
        )
        self.capture_menu.addAction(self.visible_capture_action)
        self.capture_menu.addAction(self.full_page_capture_action)
        self.capture_menu.addAction(self.pdf_capture_action)
        self.capture_button.setMenu(self.capture_menu)

        self.capture_shortcut_action = QAction(TEXTO_UI["capture_menu"], self)
        self.capture_shortcut_action.setShortcut(
            QKeySequence(atalho("captura"))
        )
        self.capture_shortcut_action.setShortcutContext(
            Qt.ShortcutContext.WindowShortcut
        )
        self.capture_shortcut_action.triggered.connect(self.show_capture_menu)
        self.addAction(self.capture_shortcut_action)

    def show_capture_menu(self, *_):
        if self._current_view() is None:
            return
        self.capture_menu.popup(
            self.capture_button.mapToGlobal(
                self.capture_button.rect().bottomLeft()
            )
        )

    def _default_capture_path(self, kind: str, extension: str) -> str:
        pictures = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.PicturesLocation
        )
        base = Path(pictures) if pictures else Path.home() / "Pictures"
        folder = base / CAPTURA_PASTA
        folder.mkdir(parents=True, exist_ok=True)
        return str(folder / capture_filename(kind, extension=extension))

    def _choose_capture_path(
        self,
        *,
        kind: str,
        extension: str,
        title: str,
        file_filter: str,
    ) -> str | None:
        try:
            default_path = self._default_capture_path(kind, extension)
        except OSError as error:
            self._show_capture_error(str(error))
            return None
        target = Explorer.get_save_file_name(
            self,
            caption=title,
            directory=str(Path(default_path).parent),
            name_filters=(file_filter,),
            initial_name=Path(default_path).name,
            remember_location=not self.private,
        )
        if not target:
            return None
        target_path = Path(target)
        expected_suffix = f".{extension.lower().lstrip('.')}"
        if target_path.suffix.lower() != expected_suffix:
            target_path = target_path.with_suffix(expected_suffix)
        return str(target_path)

    def _capture_is_available(self) -> bool:
        if not self.capture_manager.busy:
            return True
        self.statusBar().showMessage(
            TEXTO_UI["capture_busy"],
            STATUS_CURTO_MS,
        )
        return False

    def capture_visible_page(self, *_):
        if not self._capture_is_available():
            return
        view = self._current_view()
        if view is None:
            return
        path = self._choose_capture_path(
            kind="parte_visivel",
            extension="png",
            title=TEXTO_UI["capture_save_title"],
            file_filter=TEXTO_UI["capture_image_filter"],
        )
        if not path:
            return
        try:
            self.capture_manager.capture_visible(view, path)
        except (OSError, RuntimeError, ValueError) as error:
            self._show_capture_error(str(error))
            return
        self.statusBar().showMessage(
            TEXTO_UI["capture_started"],
            STATUS_DOWNLOAD_INICIO_MS,
        )

    def capture_full_page(self, *_):
        if not self._capture_is_available():
            return
        view = self._current_view()
        if view is None:
            return
        path = self._choose_capture_path(
            kind="pagina_inteira",
            extension="png",
            title=TEXTO_UI["capture_save_title"],
            file_filter=TEXTO_UI["capture_image_filter"],
        )
        if not path:
            return
        try:
            self.capture_manager.capture_full_page(
                view,
                path,
                max_width=CAPTURA_LARGURA_MAXIMA_PX,
                max_height=CAPTURA_ALTURA_MAXIMA_PX,
                settle_interval_ms=CAPTURA_INTERVALO_REPINTURA_MS,
            )
        except (OSError, RuntimeError, ValueError) as error:
            self._show_capture_error(str(error))
            return
        self.statusBar().showMessage(
            TEXTO_UI["capture_started"],
            STATUS_DOWNLOAD_INICIO_MS,
        )

    def save_page_as_pdf(self, *_):
        if not self._capture_is_available():
            return
        view = self._current_view()
        if view is None:
            return
        path = self._choose_capture_path(
            kind="pagina",
            extension="pdf",
            title=TEXTO_UI["capture_pdf_save_title"],
            file_filter=TEXTO_UI["capture_pdf_filter"],
        )
        if not path:
            return
        try:
            self.capture_manager.print_pdf(view.page(), path)
        except (OSError, RuntimeError, ValueError) as error:
            self._show_capture_error(str(error))
            return
        self.statusBar().showMessage(
            TEXTO_UI["capture_started"],
            STATUS_DOWNLOAD_INICIO_MS,
        )

    def _show_capture_saved(self, path: str, clipped: bool):
        message = TEXTO_UI["capture_done_message"].format(path=path)
        if clipped:
            message += f"\n\n{TEXTO_UI['capture_truncated_warning']}"
        self._show_capture_result(message, path)

    def _show_pdf_saved(self, path: str):
        self._show_capture_result(
            TEXTO_UI["capture_pdf_done_message"].format(path=path),
            path,
        )

    def _show_capture_result(self, message: str, path: str):
        dialog = criar_popup(
            TEXTO_UI["capture_done_title"],
            message,
            self,
            botoes=QMessageBox.StandardButton.NoButton,
        )
        open_folder_button = dialog.addButton(
            TEXTO_UI["capture_open_folder"],
            QMessageBox.ButtonRole.AcceptRole,
        )
        dialog.addButton(
            TEXTO_UI["capture_close"],
            QMessageBox.ButtonRole.RejectRole,
        )
        dialog.exec()
        if dialog.clickedButton() is open_folder_button:
            explorer = Explorer(
                self,
                mode=ExplorerMode.MANAGE,
                start_path=str(Path(path).parent),
                title=TEXTO_UI["capture_open_folder"],
                remember_location=not self.private,
            )
            explorer.exec()

    def _show_capture_error(self, error: str):
        popup_aviso(
            TEXTO_UI["capture_error_title"],
            TEXTO_UI["capture_error_message"].format(error=error),
            self,
        )
