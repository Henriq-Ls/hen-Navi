"""Janela de configuração e atualização da lista do bloqueador."""

from __future__ import annotations

from _CONFIGURA_ import TEXTO_UI
from _LOGS_ import log
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from site_utils import is_valid_https_url


class BlockerSettingsDialog(QDialog):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle(TEXTO_UI["blocker_settings_title"])

        layout = QVBoxLayout(self)
        self.enabled_checkbox = QCheckBox(
            TEXTO_UI["blocker_enabled_label"],
            self,
        )
        self.enabled_checkbox.setChecked(controller.blocker_enabled)
        layout.addWidget(self.enabled_checkbox)

        form = QFormLayout()
        self.url_field = QLineEdit(self)
        self.url_field.setPlaceholderText(
            TEXTO_UI["blocklist_url_placeholder"]
        )
        self.url_field.setText(controller.blocklist_url)
        form.addRow(TEXTO_UI["blocklist_url_label"], self.url_field)
        layout.addLayout(form)

        self.help_label = QLabel(TEXTO_UI["blocklist_help"], self)
        self.help_label.setWordWrap(True)
        layout.addWidget(self.help_label)

        self.status_label = QLabel(
            TEXTO_UI["blocklist_status_ready"].format(
                count=controller.blocklist_count
            ),
            self,
        )
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        buttons = QHBoxLayout()
        self.update_button = QPushButton(
            TEXTO_UI["blocklist_update_button"],
            self,
        )
        self.update_button.setToolTip(TEXTO_UI["blocklist_update_button"])
        self.update_button.clicked.connect(self._start_update)
        buttons.addWidget(self.update_button)

        self.save_button = QPushButton(TEXTO_UI["blocklist_save_button"], self)
        self.save_button.setToolTip(TEXTO_UI["blocklist_save_button"])
        self.save_button.clicked.connect(self._save_settings)
        buttons.addWidget(self.save_button)
        layout.addLayout(buttons)

    def _save_settings(self, *_):
        url = self.url_field.text().strip()
        if url and not is_valid_https_url(url):
            self.status_label.setText(TEXTO_UI["blocklist_status_url_invalid"])
            return
        self.controller.save_blocker_settings(
            self.enabled_checkbox.isChecked(),
            url,
        )
        self.status_label.setText(TEXTO_UI["blocklist_status_saved"])

    def _start_update(self, *_):
        url = self.url_field.text().strip()
        if not url:
            self.status_label.setText(TEXTO_UI["blocklist_status_url_required"])
            return
        if not is_valid_https_url(url):
            self.status_label.setText(TEXTO_UI["blocklist_status_url_invalid"])
            return
        self._set_busy(True)
        self.status_label.setText(TEXTO_UI["blocklist_status_downloading"])
        try:
            self.controller.start_blocklist_update(url, self)
        except (OSError, RuntimeError, ValueError) as error:
            log.erro(
                "BlockerSettingsDialog",
                "_start_update",
                str(error),
            )
            self.status_label.setText(TEXTO_UI["blocklist_status_download_error"])
            self._set_busy(False)

    def receive_downloaded_list(self, content: str) -> None:
        try:
            count = self.controller.install_blocklist_text(content)
            self.controller.save_blocker_settings(
                self.enabled_checkbox.isChecked(),
                self.url_field.text().strip(),
            )
        except ValueError:
            self.status_label.setText(TEXTO_UI["blocklist_status_invalid"])
        except OSError as error:
            log.erro(
                "BlockerSettingsDialog",
                "receive_downloaded_list",
                str(error),
            )
            self.status_label.setText(TEXTO_UI["blocklist_status_save_error"])
        else:
            self.status_label.setText(
                TEXTO_UI["blocklist_status_updated"].format(count=count)
            )
        self._set_busy(False)

    def receive_download_error(self, error: str) -> None:
        self.status_label.setText(TEXTO_UI["blocklist_status_download_error"])
        self._set_busy(False)

    def _set_busy(self, busy: bool) -> None:
        self.update_button.setEnabled(not busy)
        self.save_button.setEnabled(not busy)
