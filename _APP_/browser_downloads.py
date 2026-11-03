"""Painel de downloads comuns iniciados pelo navegador."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from _CONFIGURA_ import TEXTO_UI
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDockWidget,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from _ULTILIDADES_.popups import popup_aviso, popup_info


_ROLE_DOWNLOAD_ID = int(Qt.ItemDataRole.UserRole)
_ROLE_FILE_PATH = _ROLE_DOWNLOAD_ID + 1
_ROLE_STATUS = _ROLE_DOWNLOAD_ID + 2
_ROLE_SESSION_KEY = _ROLE_DOWNLOAD_ID + 3


class BrowserDownloadsDock(QDockWidget):
    """Lista arquivos baixados pelo perfil normal ou pela janela anônima."""

    def __init__(self, storage, *, private: bool = False, parent=None):
        super().__init__(TEXTO_UI["browser_downloads_title"], parent)
        self.storage = storage
        self.private = private
        self._private_downloads: dict[int, dict] = {}

        content = QWidget(self)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        self.notice_label = QLabel(
            TEXTO_UI[
                "browser_downloads_private_notice"
                if private
                else "browser_downloads_notice"
            ],
            content,
        )
        self.notice_label.setWordWrap(True)
        layout.addWidget(self.notice_label)

        self.empty_label = QLabel(
            TEXTO_UI["browser_downloads_empty"],
            content,
        )
        self.empty_label.setWordWrap(True)
        layout.addWidget(self.empty_label)

        self.download_list = QTreeWidget(content)
        self.download_list.setColumnCount(3)
        self.download_list.setHeaderLabels(
            (
                TEXTO_UI["browser_downloads_file"],
                TEXTO_UI["browser_downloads_status"],
                TEXTO_UI["browser_downloads_date"],
            )
        )
        self.download_list.setRootIsDecorated(False)
        self.download_list.setAlternatingRowColors(True)
        self.download_list.setSelectionMode(
            QTreeWidget.SelectionMode.SingleSelection
        )
        header = self.download_list.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.download_list.itemSelectionChanged.connect(
            self._update_button_states
        )
        self.download_list.itemDoubleClicked.connect(self.open_selected_file)
        layout.addWidget(self.download_list, 1)

        buttons = QHBoxLayout()
        self.open_button = QPushButton(
            TEXTO_UI["browser_downloads_open"],
            content,
        )
        self.open_button.clicked.connect(self.open_selected_file)
        self.open_folder_button = QPushButton(
            TEXTO_UI["browser_downloads_open_folder"],
            content,
        )
        self.open_folder_button.clicked.connect(self.open_selected_folder)
        self.remove_button = QPushButton(
            TEXTO_UI["browser_downloads_remove"],
            content,
        )
        self.remove_button.clicked.connect(self.remove_selected_from_list)
        buttons.addWidget(self.open_button)
        buttons.addWidget(self.open_folder_button)
        buttons.addWidget(self.remove_button)
        layout.addLayout(buttons)

        self.setWidget(content)
        self.refresh()

    def add_private_download(
        self,
        session_key: int,
        file_path: str,
        file_name: str,
    ) -> None:
        if not self.private:
            return
        self._private_downloads[int(session_key)] = {
            "session_key": int(session_key),
            "file_path": str(file_path),
            "file_name": str(file_name),
            "status": "active",
            "started_at": datetime.now().timestamp(),
        }
        self.refresh()

    def update_private_download(self, session_key: int, status: str) -> None:
        entry = self._private_downloads.get(int(session_key))
        if entry is not None:
            entry["status"] = str(status)
            entry["finished_at"] = datetime.now().timestamp()
            self.refresh()

    def refresh(self) -> None:
        selected_key = self._selected_key()
        if self.private:
            entries = sorted(
                self._private_downloads.values(),
                key=lambda entry: (entry["started_at"], entry["session_key"]),
                reverse=True,
            )
        else:
            entries = self.storage.get_browser_downloads()

        self.download_list.clear()
        state_labels = {
            "active": TEXTO_UI["browser_download_state_active"],
            "completed": TEXTO_UI["browser_download_state_completed"],
            "cancelled": TEXTO_UI["browser_download_state_cancelled"],
            "interrupted": TEXTO_UI["browser_download_state_interrupted"],
        }
        for entry in entries:
            status = entry.get("status", "")
            item = QTreeWidgetItem(
                [
                    str(entry.get("file_name", "")),
                    state_labels.get(
                        status,
                        TEXTO_UI["browser_download_state_unknown"],
                    ),
                    self._format_date(entry.get("started_at")),
                ]
            )
            item.setData(0, _ROLE_FILE_PATH, str(entry.get("file_path", "")))
            item.setData(0, _ROLE_STATUS, str(status))
            if self.private:
                item.setData(
                    0,
                    _ROLE_SESSION_KEY,
                    int(entry.get("session_key", -1)),
                )
            else:
                item.setData(0, _ROLE_DOWNLOAD_ID, int(entry.get("id", -1)))
            self.download_list.addTopLevelItem(item)
            if self._item_key(item) == selected_key:
                self.download_list.setCurrentItem(item)

        has_entries = bool(entries)
        self.empty_label.setVisible(not has_entries)
        self.download_list.setVisible(has_entries)
        self._update_button_states()

    def _format_date(self, value) -> str:
        try:
            return datetime.fromtimestamp(float(value)).strftime("%d/%m/%Y %H:%M")
        except (TypeError, ValueError, OSError, OverflowError):
            return ""

    def _selected_item(self) -> QTreeWidgetItem | None:
        items = self.download_list.selectedItems()
        return items[0] if items else None

    def _item_key(self, item: QTreeWidgetItem):
        role = _ROLE_SESSION_KEY if self.private else _ROLE_DOWNLOAD_ID
        return item.data(0, role)

    def _selected_key(self):
        item = self._selected_item()
        return self._item_key(item) if item is not None else None

    def _selected_path(self) -> Path | None:
        item = self._selected_item()
        if item is None:
            return None
        value = item.data(0, _ROLE_FILE_PATH)
        return Path(str(value)) if value else None

    def _update_button_states(self) -> None:
        item = self._selected_item()
        path = self._selected_path()
        status = (
            str(item.data(0, _ROLE_STATUS))
            if item is not None
            else ""
        )
        self.open_button.setEnabled(
            path is not None
            and path.is_file()
            and status == "completed"
        )
        self.open_folder_button.setEnabled(
            path is not None and path.parent.is_dir()
        )
        self.remove_button.setEnabled(item is not None)

    def open_selected_file(self, *_):
        item = self._selected_item()
        path = self._selected_path()
        if item is None or path is None:
            return
        if str(item.data(0, _ROLE_STATUS)) != "completed":
            popup_info(
                TEXTO_UI["browser_downloads_title"],
                TEXTO_UI["browser_download_not_completed"],
                self,
            )
            return
        if not path.is_file():
            popup_aviso(
                TEXTO_UI["browser_downloads_title"],
                TEXTO_UI["browser_download_file_missing"],
                self,
            )
            self._update_button_states()
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
            popup_aviso(
                TEXTO_UI["browser_downloads_title"],
                TEXTO_UI["browser_download_open_failed"],
                self,
            )

    def open_selected_folder(self, *_):
        path = self._selected_path()
        if path is None or not path.parent.is_dir():
            popup_aviso(
                TEXTO_UI["browser_downloads_title"],
                TEXTO_UI["browser_download_folder_missing"],
                self,
            )
            self._update_button_states()
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent))):
            popup_aviso(
                TEXTO_UI["browser_downloads_title"],
                TEXTO_UI["browser_download_open_failed"],
                self,
            )

    def remove_selected_from_list(self, *_):
        item = self._selected_item()
        if item is None:
            return
        if self.private:
            self._private_downloads.pop(int(self._item_key(item)), None)
        else:
            self.storage.remove_browser_download(int(self._item_key(item)))
        self.refresh()
