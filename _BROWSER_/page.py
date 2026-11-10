"""Página WebEngine com políticas de navegação, permissões e uploads."""

from __future__ import annotations

import os

from _APP_.inspector import inspection_pick_marker
from _APP_.password_manager import (
    PASSWORD_SAVE_SUBMIT_MARKER,
    PASSWORD_SAVE_SUBMIT_SCRIPT,
)
from _CONFIGURA_ import ESQUEMA_INTERNO, TEXTO_UI
from _LOGS_ import log
from _SERVICOS_.folder_upload import collect_folder_upload_files
from _ULTILIDADES_.explorer import Explorer
from _ULTILIDADES_.popups import popup_pergunta
from _ULTILIDADES_.utils import is_http_url
from PySide6.QtCore import QMimeDatabase, QUrl, QUrlQuery, Signal
from PySide6.QtWidgets import QMessageBox
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEnginePermission,
    QWebEngineProfile,
    QWebEngineScript,
)
from PySide6.QtWebEngineWidgets import QWebEngineView


class BrowserPage(QWebEnginePage):
    """Página que intercepta buscas internas do navegador."""

    inspectionElementSelected = Signal(str)

    def __init__(
        self,
        profile: QWebEngineProfile,
        parent_view: QWebEngineView,
        browser_window: "BrowserWindow",
        home_file_path: str,
        *,
        start_page: bool = False,
        restored: bool = False,
    ):
        super().__init__(profile, parent_view)
        self.browser_window = browser_window
        self.home_file_path = os.path.realpath(home_file_path)
        self.is_start_page_active = start_page
        self.restore_pending = restored
        self._search_suggestions_channel = None
        self.fullScreenRequested.connect(browser_window._on_fullscreen_requested)
        self.permissionRequested.connect(self._on_permission_requested)
        if not browser_window.private:
            password_submit_script = QWebEngineScript()
            password_submit_script.setName("henNavePasswordSaveOffer")
            password_submit_script.setInjectionPoint(
                QWebEngineScript.InjectionPoint.DocumentCreation
            )
            password_submit_script.setWorldId(
                QWebEngineScript.ScriptWorldId.MainWorld
            )
            password_submit_script.setRunsOnSubFrames(False)
            password_submit_script.setSourceCode(PASSWORD_SAVE_SUBMIT_SCRIPT)
            self.scripts().insert(password_submit_script)

    def set_search_suggestions_channel(self, channel: QWebChannel):
        self._search_suggestions_channel = channel
        self.setWebChannel(channel)

    def _on_permission_requested(self, permission: QWebEnginePermission):
        if not permission.isValid():
            return

        permission_type = permission.permissionType()
        permission_types = QWebEnginePermission.PermissionType
        if permission_type == permission_types.MediaAudioCapture:
            resource = TEXTO_UI["permission_microphone"]
        elif permission_type == permission_types.MediaAudioVideoCapture:
            resource = TEXTO_UI["permission_microphone_camera"]
        else:
            permission.deny()
            return

        origin = permission.origin().toString()
        answer = popup_pergunta(
            TEXTO_UI["permission_request_title"],
            TEXTO_UI["permission_request_message"].format(
                origin=origin,
                resource=resource,
            ),
            self.browser_window,
            botao_padrao=QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            permission.grant()
        else:
            permission.deny()

    def chooseFiles(self, mode, old_files, accepted_mime_types):
        selection_modes = QWebEnginePage.FileSelectionMode
        is_folder = mode == selection_modes.FileSelectUploadFolder
        is_multiple = mode == selection_modes.FileSelectOpenMultiple
        is_save = mode == selection_modes.FileSelectSave
        if mode not in {
            selection_modes.FileSelectOpen,
            selection_modes.FileSelectOpenMultiple,
            selection_modes.FileSelectUploadFolder,
            selection_modes.FileSelectSave,
        }:
            return []

        title = (
            TEXTO_UI["upload_folder_title"]
            if is_folder
            else TEXTO_UI["upload_files_title"]
        )
        previous = str(old_files[0] or "") if old_files else ""
        initial_directory = (
            previous
            if os.path.isdir(previous)
            else os.path.dirname(previous)
            if os.path.isfile(previous)
            else None
        )
        initial_name = (
            os.path.basename(previous) if os.path.isfile(previous) else None
        )
        remember_location = not bool(self.browser_window.private)

        try:
            if is_folder:
                folder = Explorer.get_existing_directory(
                    self.browser_window,
                    caption=title,
                    directory=initial_directory,
                    remember_location=remember_location,
                )
                selected = [folder] if folder else []
            elif is_save:
                target = Explorer.get_save_file_name(
                    self.browser_window,
                    caption=title,
                    directory=initial_directory,
                    name_filters=(TEXTO_UI["upload_all_files_filter"],),
                    initial_name=initial_name,
                    remember_location=remember_location,
                )
                selected = [target] if target else []
            elif is_multiple:
                selected = Explorer.get_open_file_names(
                    self.browser_window,
                    caption=title,
                    directory=initial_directory,
                    name_filters=self._upload_name_filters(
                        accepted_mime_types
                    ),
                    remember_location=remember_location,
                )
            else:
                target = Explorer.get_open_file_name(
                    self.browser_window,
                    caption=title,
                    directory=initial_directory,
                    name_filters=self._upload_name_filters(
                        accepted_mime_types
                    ),
                    initial_name=initial_name,
                    remember_location=remember_location,
                )
                selected = [target] if target else []

            if is_folder and selected:
                upload_files = collect_folder_upload_files(selected[0])
                if upload_files is None:
                    log.aviso(
                        "BrowserPage",
                        "chooseFiles",
                        "Pasta sem arquivo na raiz; mantendo a seleção de pasta do QtWebEngine.",
                    )
                else:
                    selected = upload_files
                    log.info(
                        "BrowserPage",
                        "chooseFiles",
                        f"Upload de pasta preparado com {len(selected)} arquivos.",
                    )
        except Exception as error:
            log.erro(
                "BrowserPage",
                "chooseFiles",
                f"Falha ao abrir o Explorer de arquivos: {type(error).__name__}",
            )
            return []

        if is_folder:
            return selected
        if is_save or not is_multiple:
            return selected[:1]
        return selected

    @staticmethod
    def _upload_name_filters(accepted_mime_types):
        patterns = set()
        database = QMimeDatabase()
        for mime_name in accepted_mime_types or []:
            mime_name = str(mime_name or "").strip()
            if not mime_name or "*" in mime_name:
                continue
            try:
                mime_type = database.mimeTypeForName(mime_name)
                if mime_type.isValid():
                    patterns.update(mime_type.globPatterns())
            except (RuntimeError, TypeError):
                continue
        filters = []
        if patterns:
            filters.append(f"Arquivos aceitos ({' '.join(sorted(patterns))})")
        filters.append(TEXTO_UI["upload_all_files_filter"])
        return filters

    def javaScriptConsoleMessage(self, level, message, line_number, source_id):
        if message == PASSWORD_SAVE_SUBMIT_MARKER:
            self.browser_window._offer_password_save_after_submit(self)
            return
        marker = inspection_pick_marker()
        if message.startswith(marker):
            selector = message[len(marker):]
            if selector:
                self.inspectionElementSelected.emit(selector)
            return
        super().javaScriptConsoleMessage(level, message, line_number, source_id)

    def acceptNavigationRequest(
        self,
        url: QUrl,
        navigation_type,
        is_main_frame: bool,
    ) -> bool:
        scheme = url.scheme().lower()
        if scheme == "file":
            if not is_main_frame:
                return False
            requested_path = os.path.realpath(url.toLocalFile())
            if requested_path != self.home_file_path:
                return False
            if self._search_suggestions_channel is not None:
                self.setWebChannel(self._search_suggestions_channel)
            query = QUrlQuery(url)
            if query.hasQueryItem("q"):
                self.browser_window._queue_home_search(
                    query.queryItemValue("q"),
                    self,
                )
                return False
            return True

        if scheme == ESQUEMA_INTERNO:
            current_url = self.url()
            is_home_document = (
                current_url.scheme().lower() == "file"
                and os.path.realpath(current_url.toLocalFile()) == self.home_file_path
            )
            if not is_main_frame or not (
                self.is_start_page_active or is_home_document
            ):
                return False
            query = QUrlQuery(url).queryItemValue("q")
            self.browser_window._queue_home_search(query, self)
            return False

        if not is_main_frame:
            return True

        if scheme in {"http", "https"}:
            target = url.toString()
            if not is_http_url(target):
                return False
            self.setWebChannel(None)
            self.is_start_page_active = False
            return True

        if scheme == "about" and url.toString().lower() == "about:blank":
            return True
        return False

    def createWindow(self, window_type):
        return self.browser_window._create_popup_page(window_type)
