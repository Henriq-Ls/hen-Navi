"""Diálogos de histórico e favoritos."""

from __future__ import annotations

from datetime import datetime

from _CONFIGURA_ import (
    ALTURA_DIALOGO_PADRAO,
    ESTILO_DIALOGO_ESCURO,
    ESTILO_LIST_WIDGET,
    FORMATO_DATA_HISTORICO,
    LARGURA_DIALOGO_PADRAO,
    TEXTO_UI,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)


class HistoryDialog(QDialog):
    openRequested = Signal(str)
    changed = Signal()

    def __init__(self, storage, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.setWindowTitle(TEXTO_UI["history"])
        self.resize(LARGURA_DIALOGO_PADRAO, ALTURA_DIALOGO_PADRAO)
        self.setStyleSheet(ESTILO_DIALOGO_ESCURO + ESTILO_LIST_WIDGET)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(TEXTO_UI["history_search_label"]))
        self.search_field = QLineEdit(self)
        self.search_field.setPlaceholderText(TEXTO_UI["history_search_placeholder"])
        self.search_field.textChanged.connect(self._refresh)
        layout.addWidget(self.search_field)

        self.entries = QListWidget(self)
        self.entries.itemDoubleClicked.connect(self._open_item)
        layout.addWidget(self.entries)

        buttons = QHBoxLayout()
        self.open_button = QPushButton(TEXTO_UI["history_open"], self)
        self.remove_button = QPushButton(TEXTO_UI["history_remove"], self)
        self.clear_button = QPushButton(TEXTO_UI["clear_history"], self)
        self.close_button = QPushButton(TEXTO_UI["close"], self)
        self.open_button.clicked.connect(self._open_selected)
        self.remove_button.clicked.connect(self._remove_selected)
        self.clear_button.clicked.connect(self._clear_all)
        self.close_button.clicked.connect(self.close)
        buttons.addWidget(self.open_button)
        buttons.addWidget(self.remove_button)
        buttons.addWidget(self.clear_button)
        buttons.addStretch(1)
        buttons.addWidget(self.close_button)
        layout.addLayout(buttons)
        self._refresh()

    def _refresh(self, *_):
        self.entries.clear()
        for entry in self.storage.get_history(self.search_field.text()):
            title = entry["title"] or entry["url"]
            try:
                visited = datetime.fromtimestamp(entry["visited_at"]).strftime(FORMATO_DATA_HISTORICO)
            except (TypeError, ValueError, OSError):
                visited = ""
            label = TEXTO_UI["history_entry_format"].format(
                title=title,
                url=entry["url"],
            )
            if visited:
                label = TEXTO_UI["history_entry_date_format"].format(
                    entry=label,
                    date=visited,
                )
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, entry["url"])
            item.setData(Qt.ItemDataRole.UserRole + 1, entry["id"])
            item.setToolTip(entry["url"])
            self.entries.addItem(item)

    def _selected_item(self):
        return self.entries.currentItem()

    def _open_item(self, item: QListWidgetItem):
        url = item.data(Qt.ItemDataRole.UserRole)
        if url:
            self.openRequested.emit(url)

    def _open_selected(self, *_):
        item = self._selected_item()
        if item:
            self._open_item(item)

    def _remove_selected(self, *_):
        item = self._selected_item()
        if not item:
            return
        entry_id = item.data(Qt.ItemDataRole.UserRole + 1)
        if self.storage.remove_history_entry(entry_id):
            self._refresh()
            self.changed.emit()

    def _clear_all(self, *_):
        answer = QMessageBox.question(
            self,
            TEXTO_UI["confirm_clear_title"],
            TEXTO_UI["confirm_clear_message"],
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.storage.clear_history()
            self._refresh()
            self.changed.emit()


class FavoritesDialog(QDialog):
    openRequested = Signal(str)
    changed = Signal()

    def __init__(self, storage, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.setWindowTitle(TEXTO_UI["favorites"])
        self.resize(LARGURA_DIALOGO_PADRAO, ALTURA_DIALOGO_PADRAO)
        self.setStyleSheet(ESTILO_DIALOGO_ESCURO + ESTILO_LIST_WIDGET)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(TEXTO_UI["favorites_search_label"]))
        self.search_field = QLineEdit(self)
        self.search_field.setPlaceholderText(TEXTO_UI["favorites_search_placeholder"])
        self.search_field.textChanged.connect(self._refresh)
        layout.addWidget(self.search_field)

        self.entries = QListWidget(self)
        self.entries.itemDoubleClicked.connect(self._open_item)
        layout.addWidget(self.entries)

        buttons = QHBoxLayout()
        self.open_button = QPushButton(TEXTO_UI["favorite_open"], self)
        self.remove_button = QPushButton(TEXTO_UI["favorite_remove"], self)
        self.close_button = QPushButton(TEXTO_UI["close"], self)
        self.open_button.clicked.connect(self._open_selected)
        self.remove_button.clicked.connect(self._remove_selected)
        self.close_button.clicked.connect(self.close)
        buttons.addWidget(self.open_button)
        buttons.addWidget(self.remove_button)
        buttons.addStretch(1)
        buttons.addWidget(self.close_button)
        layout.addLayout(buttons)
        self._refresh()

    def _refresh(self, *_):
        self.entries.clear()
        for entry in self.storage.get_favorites(self.search_field.text()):
            title = entry["title"] or entry["url"]
            item = QListWidgetItem(
                TEXTO_UI["favorite_entry_format"].format(
                    title=title,
                    url=entry["url"],
                )
            )
            item.setData(Qt.ItemDataRole.UserRole, entry["url"])
            item.setToolTip(entry["url"])
            self.entries.addItem(item)

    def _open_item(self, item: QListWidgetItem):
        url = item.data(Qt.ItemDataRole.UserRole)
        if url:
            self.openRequested.emit(url)

    def _open_selected(self, *_):
        item = self.entries.currentItem()
        if item:
            self._open_item(item)

    def _remove_selected(self, *_):
        item = self.entries.currentItem()
        if not item:
            return
        url = item.data(Qt.ItemDataRole.UserRole)
        if self.storage.remove_favorite(url):
            self._refresh()
            self.changed.emit()
