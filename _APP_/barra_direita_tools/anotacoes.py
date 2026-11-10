"""Painel de anotações vinculado ao site selecionado."""

from __future__ import annotations

from pathlib import Path

from _CONFIGURA_ import (
    ARQUIVO_EXPORTAR_ANOTACOES,
    DEBOUNCE_ANOTACOES_MS,
    LARGURA_DOCK_ANOTACOES,
    TEXTO_UI,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QDockWidget,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from _ULTILIDADES_.explorer import Explorer
from _ULTILIDADES_.popups import popup_aviso, popup_info
from _ULTILIDADES_.site_utils import normalize_host


class NotesDock(QDockWidget):
    """Editor com autosave, busca global e exportação em Markdown."""

    openHostRequested = Signal(str)
    noteChanged = Signal(str, bool)

    def __init__(self, storage, parent=None):
        super().__init__(TEXTO_UI["notes_title"], parent)
        self.storage = storage
        self._current_host = ""
        self._loading_note = False
        self.setObjectName("siteNotesDock")
        self.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        self.setMinimumWidth(LARGURA_DOCK_ANOTACOES)

        content = QWidget(self)
        layout = QVBoxLayout(content)

        self.search_field = QLineEdit(content)
        self.search_field.setPlaceholderText(TEXTO_UI["notes_search_placeholder"])
        self.search_field.textChanged.connect(self._refresh_search_results)
        layout.addWidget(self.search_field)

        self.search_results = QListWidget(content)
        self.search_results.itemDoubleClicked.connect(self._open_search_result)
        layout.addWidget(self.search_results)

        self.note_indicator = QLabel(TEXTO_UI["notes_indicator"], content)
        self.note_indicator.setObjectName("noteIndicator")
        self.note_indicator.hide()
        layout.addWidget(self.note_indicator)

        self.editor = QTextEdit(content)
        self.editor.setPlaceholderText(TEXTO_UI["notes_open_site_hint"])
        self.editor.setEnabled(False)
        self.editor.textChanged.connect(self._queue_save)
        layout.addWidget(self.editor)

        self.export_button = QPushButton(
            TEXTO_UI["notes_export_button"],
            content,
        )
        self.export_button.setToolTip(TEXTO_UI["notes_export_button"])
        self.export_button.clicked.connect(self.export_all)
        layout.addWidget(self.export_button)

        self.setWidget(content)
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(DEBOUNCE_ANOTACOES_MS)
        self._save_timer.timeout.connect(self.save_current_note)
        self._refresh_search_results()

    @property
    def current_host(self) -> str:
        return self._current_host

    def set_site(self, host: str) -> None:
        site = normalize_host(host, strip_www=True)
        if site == self._current_host:
            return
        self.save_current_note()
        self._current_host = site
        self._loading_note = True
        self.editor.setPlainText(self.storage.get_note(site) if site else "")
        self._loading_note = False
        self.editor.setEnabled(bool(site))
        self.editor.setPlaceholderText(
            TEXTO_UI["notes_editor_placeholder"]
            if site
            else TEXTO_UI["notes_open_site_hint"]
        )
        self._update_note_indicator()

    def _queue_save(self) -> None:
        if not self._loading_note and self._current_host:
            self._save_timer.start()
            self._update_note_indicator()

    def save_current_note(self) -> None:
        if self._save_timer.isActive():
            self._save_timer.stop()
        if self._loading_note or not self._current_host:
            return
        self.storage.save_note(self._current_host, self.editor.toPlainText())
        self._update_note_indicator()
        self._refresh_search_results()

    def _update_note_indicator(self) -> None:
        has_note = bool(self._current_host and self.editor.toPlainText().strip())
        self.note_indicator.setVisible(has_note)
        self.noteChanged.emit(self._current_host, has_note)

    def _refresh_search_results(self, *_):
        self.search_results.clear()
        notes = self.storage.search_notes(self.search_field.text())
        for note in notes:
            preview = " ".join(note["texto"].split())
            item = QListWidgetItem(
                TEXTO_UI["notes_search_result_format"].format(
                    host=note["host"],
                    preview=preview,
                )
            )
            item.setData(Qt.ItemDataRole.UserRole, note["host"])
            item.setToolTip(note["texto"])
            self.search_results.addItem(item)
        if not notes:
            empty_item = QListWidgetItem(TEXTO_UI["notes_search_empty"])
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.search_results.addItem(empty_item)

    def _open_search_result(self, item: QListWidgetItem) -> None:
        host = item.data(Qt.ItemDataRole.UserRole)
        if host:
            self.openHostRequested.emit(str(host))

    def export_all(self, *_):
        target = Explorer.get_save_file_name(
            self,
            caption=TEXTO_UI["notes_export_title"],
            name_filters=(TEXTO_UI["notes_export_filter"],),
            initial_name=ARQUIVO_EXPORTAR_ANOTACOES,
            remember_location=not bool(
                getattr(self.window(), "private", False)
            ),
        )
        if not target:
            return

        notes = self.storage.all_notes()
        sections = [TEXTO_UI["notes_markdown_title"]]
        if notes:
            sections.extend(
                TEXTO_UI["notes_markdown_entry"].format(
                    host=note["host"],
                    text=note["texto"],
                )
                for note in notes
            )
        else:
            sections.append(TEXTO_UI["notes_export_empty"])
        try:
            Path(target).write_text("\n\n".join(sections) + "\n", encoding="utf-8")
            popup_info(
                TEXTO_UI["notes_export_done_title"],
                TEXTO_UI["notes_export_done"],
                self,
            )
        except OSError as error:
            popup_aviso(
                TEXTO_UI["notes_export_title"],
                TEXTO_UI["notes_export_error"].format(error=error),
                self,
            )
