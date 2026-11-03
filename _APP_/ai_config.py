"""Diálogos para cadastrar provedores sem expor chaves já salvas."""

from __future__ import annotations

import uuid
from urllib.parse import urlsplit

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from _CONFIGURA_ import (
    ETAPA_LIMITE_CARACTERES_PAGINA_IA,
    LIMITE_CARACTERES_PAGINA_IA,
    LIMITE_CARACTERES_PAGINA_IA_MAXIMO,
    LIMITE_CARACTERES_PAGINA_IA_MINIMO,
    TEXTO_UI,
)
from _ULTILIDADES_.popups import popup_aviso, popup_pergunta
from _THREADS_.ai_assistant import AiProviderWorker
from _SERVICOS_.ai_provider_store import ProviderStore, ProviderStoreError
from _SERVICOS_.ai_service import ProviderRequestError, validate_base_url


_PLATFORMS = (
    ("Ollama local", "ollama", "ollama", "http://localhost:11434"),
    (
        "OpenAI-compatible personalizado",
        "openai_compatible",
        "custom",
        "",
    ),
    (
        "Groq",
        "openai_compatible",
        "groq",
        "https://api.groq.com/openai/v1",
    ),
    (
        "OpenRouter",
        "openai_compatible",
        "openrouter",
        "https://openrouter.ai/api/v1",
    ),
)


class AiSettingsDialog(QDialog):
    def __init__(self, store: ProviderStore, parent=None):
        super().__init__(parent)
        self.store = store
        self._workers: list[AiProviderWorker] = []
        self.setWindowTitle(TEXTO_UI["ai_settings_title"])
        self.resize(680, 440)

        layout = QVBoxLayout(self)
        self.provider_list = QListWidget(self)
        self.provider_list.currentRowChanged.connect(self._update_buttons)
        self.provider_list.itemDoubleClicked.connect(lambda _item: self.edit_provider())
        layout.addWidget(self.provider_list, 1)

        actions = QHBoxLayout()
        self.add_button = QPushButton(TEXTO_UI["ai_add"], self)
        self.add_button.clicked.connect(self.add_provider)
        actions.addWidget(self.add_button)
        self.edit_button = QPushButton(TEXTO_UI["ai_edit"], self)
        self.edit_button.clicked.connect(self.edit_provider)
        actions.addWidget(self.edit_button)
        self.remove_button = QPushButton(TEXTO_UI["ai_remove"], self)
        self.remove_button.clicked.connect(self.remove_provider)
        actions.addWidget(self.remove_button)
        self.activate_button = QPushButton(TEXTO_UI["ai_activate"], self)
        self.activate_button.clicked.connect(self.activate_provider)
        actions.addWidget(self.activate_button)
        layout.addLayout(actions)

        close_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        close_box.rejected.connect(self.reject)
        close_box.accepted.connect(self.accept)
        layout.addWidget(close_box)
        self.refresh()

    def refresh(self) -> None:
        try:
            data = self.store.load()
        except ProviderStoreError as error:
            popup_aviso(self.windowTitle(), str(error), self)
            data = {"active_id": "", "providers": []}
        self.provider_list.clear()
        for provider in data["providers"]:
            marker = " ✓" if provider["id"] == data["active_id"] else ""
            locality = (
                TEXTO_UI["ai_local_badge"]
                if provider["kind"] == "ollama"
                else TEXTO_UI["ai_cloud_badge"]
            )
            item = QListWidgetItem(
                f"{provider['name']} — {locality} — "
                f"{provider['model'] or TEXTO_UI['ai_model_unselected']}{marker}"
            )
            item.setData(Qt.ItemDataRole.UserRole, provider["id"])
            self.provider_list.addItem(item)
        self._update_buttons()

    def _selected_provider(self) -> dict | None:
        item = self.provider_list.currentItem()
        if item is None:
            return None
        try:
            return self.store.get_provider(item.data(Qt.ItemDataRole.UserRole))
        except ProviderStoreError as error:
            popup_aviso(self.windowTitle(), str(error), self)
            return None

    def add_provider(self) -> None:
        dialog = AiProviderEditorDialog(self.store, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def edit_provider(self) -> None:
        provider = self._selected_provider()
        if provider is None:
            return
        dialog = AiProviderEditorDialog(self.store, provider, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def remove_provider(self) -> None:
        provider = self._selected_provider()
        if provider is None:
            return
        answer = popup_pergunta(
            TEXTO_UI["ai_remove_title"],
            TEXTO_UI["ai_remove_confirm"].format(name=provider["name"]),
            self,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.store.remove_provider(provider["id"])
        except ProviderStoreError as error:
            popup_aviso(self.windowTitle(), str(error), self)
        self.refresh()

    def activate_provider(self) -> None:
        provider = self._selected_provider()
        if provider is None:
            return
        try:
            self.store.set_active(provider["id"])
        except ProviderStoreError as error:
            popup_aviso(self.windowTitle(), str(error), self)
        self.refresh()

    def _update_buttons(self, *_args) -> None:
        selected = self.provider_list.currentItem() is not None
        self.edit_button.setEnabled(selected)
        self.remove_button.setEnabled(selected)
        self.activate_button.setEnabled(selected)

    def _worker_done(self, worker: AiProviderWorker) -> None:
        if worker in self._workers:
            self._workers.remove(worker)

    def closeEvent(self, event):
        self._stop_workers()
        super().closeEvent(event)

    def _stop_workers(self) -> None:
        for worker in list(self._workers):
            worker.cancel()
            worker.wait(2500)

    def done(self, result: int) -> None:
        self._stop_workers()
        super().done(result)


class AiProviderEditorDialog(QDialog):
    def __init__(
        self,
        store: ProviderStore,
        provider: dict | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.store = store
        self.provider = dict(provider or {})
        self._workers: list[AiProviderWorker] = []
        self._loading_provider = True
        self.setWindowTitle(
            TEXTO_UI["ai_edit_title"] if provider else TEXTO_UI["ai_add_title"]
        )
        self.resize(600, 420)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name_field = QLineEdit(self)
        form.addRow(TEXTO_UI["ai_name_label"], self.name_field)

        self.platform_combo = QComboBox(self)
        for label, kind, platform, base_url in _PLATFORMS:
            self.platform_combo.addItem(label, (kind, platform, base_url))
        form.addRow(TEXTO_UI["ai_platform_label"], self.platform_combo)

        self.base_url_field = QLineEdit(self)
        self.base_url_field.setPlaceholderText(TEXTO_UI["ai_base_url_placeholder"])
        form.addRow(TEXTO_UI["ai_base_url_label"], self.base_url_field)

        self.secret_field = QLineEdit(self)
        self.secret_field.setEchoMode(QLineEdit.EchoMode.Password)
        self.secret_field.setPlaceholderText(TEXTO_UI["ai_key_placeholder"])
        form.addRow(TEXTO_UI["ai_key_label"], self.secret_field)
        self.remove_secret_check = QCheckBox(TEXTO_UI["ai_remove_key"], self)
        form.addRow("", self.remove_secret_check)
        self.remove_secret_check.setVisible(bool(self.provider.get("credential_id")))
        self.secret_status_label = QLabel("", self)
        self.secret_status_label.setWordWrap(True)
        self.secret_status_label.setObjectName("aiKeyStorageStatus")
        form.addRow("", self.secret_status_label)

        self.model_combo = QComboBox(self)
        self.model_combo.setEditable(True)
        self.model_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.model_combo.lineEdit().setPlaceholderText(
            TEXTO_UI["ai_model_placeholder"]
        )
        form.addRow(TEXTO_UI["ai_model_label"], self.model_combo)
        layout.addLayout(form)

        model_actions = QHBoxLayout()
        self.fetch_models_button = QPushButton(TEXTO_UI["ai_fetch_models"], self)
        self.fetch_models_button.clicked.connect(self.fetch_models)
        model_actions.addWidget(self.fetch_models_button)
        self.test_button = QPushButton(TEXTO_UI["ai_test_connection"], self)
        self.test_button.clicked.connect(self.test_connection)
        model_actions.addWidget(self.test_button)
        layout.addLayout(model_actions)

        self.page_limit_spin = QSpinBox(self)
        self.page_limit_spin.setRange(
            LIMITE_CARACTERES_PAGINA_IA_MINIMO,
            LIMITE_CARACTERES_PAGINA_IA_MAXIMO,
        )
        self.page_limit_spin.setSingleStep(ETAPA_LIMITE_CARACTERES_PAGINA_IA)
        self.page_limit_spin.setSuffix(" caracteres")
        self.page_limit_spin.setValue(LIMITE_CARACTERES_PAGINA_IA)
        form.addRow(TEXTO_UI["ai_page_limit"], self.page_limit_spin)

        self.status_label = QLabel("", self)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        layout.addStretch(1)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        self.buttons.accepted.connect(self.save_provider)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.platform_combo.currentIndexChanged.connect(self._platform_changed)
        self.secret_field.textChanged.connect(self._update_secret_status)
        self.remove_secret_check.toggled.connect(self._update_secret_status)
        self._load_provider()
        self._loading_provider = False
        self._update_secret_status()
        if self.platform_combo.currentData()[0] == "ollama":
            self.fetch_models()

    def _load_provider(self) -> None:
        if self.provider:
            self.name_field.setText(str(self.provider.get("name") or ""))
            platform = str(self.provider.get("platform") or "")
            index = next(
                (
                    i for i in range(self.platform_combo.count())
                    if self.platform_combo.itemData(i)[1] == platform
                ),
                1,
            )
            self.platform_combo.setCurrentIndex(index)
            self.base_url_field.setText(str(self.provider.get("base_url") or ""))
            self.model_combo.setEditText(str(self.provider.get("model") or ""))
            self.page_limit_spin.setValue(
                int(self.provider.get("max_page_chars", 12000))
            )
        else:
            self.platform_combo.setCurrentIndex(0)
            self.name_field.setText(TEXTO_UI["ai_default_ollama_name"])
            self._platform_changed(self.platform_combo.currentIndex())

    def _platform_changed(self, index: int) -> None:
        data = self.platform_combo.itemData(index)
        if not data:
            return
        _kind, platform, base_url = data
        self.base_url_field.setText(base_url)
        if not self.name_field.text().strip() or self.name_field.text().strip() in {
            label for label, _kind, _platform, _url in _PLATFORMS
        }:
            self.name_field.setText(
                next(label for label, _kind, item_platform, _url in _PLATFORMS
                     if item_platform == platform)
            )
        if platform == "ollama" and not self._loading_provider:
            self.fetch_models()

    def _payload(self) -> dict:
        kind, platform, _default_url = self.platform_combo.currentData()
        return {
            "id": self.provider.get("id") or uuid.uuid4().hex,
            "name": self.name_field.text().strip(),
            "kind": kind,
            "platform": platform,
            "base_url": self.base_url_field.text().strip(),
            "model": self.model_combo.currentText().strip(),
            "max_page_chars": self.page_limit_spin.value(),
            "credential_id": self.provider.get("credential_id", ""),
            "suppress_cloud_warning": self.provider.get(
                "suppress_cloud_warning", False
            ),
        }

    def _secret_override(self) -> str | None:
        typed = self.secret_field.text()
        if typed:
            return typed
        if self.remove_secret_check.isChecked():
            return ""
        if self.provider.get("credential_id"):
            return None
        return ""

    def _update_secret_status(self, *_args) -> None:
        if self.secret_field.text():
            message = TEXTO_UI["ai_key_will_save"]
        elif self.remove_secret_check.isChecked():
            message = TEXTO_UI["ai_key_will_remove"]
        elif self.provider.get("credential_id"):
            message = TEXTO_UI["ai_key_saved_notice"]
        else:
            message = TEXTO_UI["ai_key_not_saved"]
        self.secret_status_label.setText(message)

    def _confirm_insecure_key_use(self, provider: dict, secret: str | None) -> bool:
        has_secret = bool(secret) if secret is not None else bool(
            provider.get("credential_id")
        )
        if not has_secret or urlsplit(provider["base_url"]).scheme != "http":
            return True
        answer = popup_pergunta(
            TEXTO_UI["ai_insecure_title"],
            TEXTO_UI["ai_insecure_key_warning"],
            self,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _start_probe(self, operation: str) -> None:
        provider = self._payload()
        secret_override = self._secret_override()
        try:
            provider["base_url"] = validate_base_url(provider["base_url"])
        except ProviderRequestError as error:
            popup_aviso(self.windowTitle(), str(error), self)
            return
        if not self._confirm_insecure_key_use(provider, secret_override):
            return
        worker = AiProviderWorker(
            operation,
            provider,
            str(self.store.config_directory),
            secret_override=secret_override,
            parent=self,
        )
        self._workers.append(worker)
        worker.modelsReady.connect(self._models_loaded)
        worker.testReady.connect(self._test_loaded)
        worker.failed.connect(self._probe_failed)
        worker.finished.connect(lambda w=worker: self._worker_done(w))
        worker.start()
        self.fetch_models_button.setEnabled(False)
        self.test_button.setEnabled(False)
        self.status_label.setText(TEXTO_UI["ai_connecting"])

    def fetch_models(self) -> None:
        self._start_probe("models")

    def test_connection(self) -> None:
        self._start_probe("test")

    def _models_loaded(self, models: list[str]) -> None:
        current = self.model_combo.currentText().strip()
        self.model_combo.clear()
        self.model_combo.addItems(models)
        if current:
            self.model_combo.setEditText(current)
        elif models:
            self.model_combo.setCurrentIndex(0)
        self.status_label.setText(
            TEXTO_UI["ai_models_found"].format(count=len(models))
            if models
            else TEXTO_UI["ai_models_empty"]
        )
        self._set_probe_buttons_enabled(True)

    def _test_loaded(self, message: str) -> None:
        self.status_label.setText(message)
        self._set_probe_buttons_enabled(True)

    def _probe_failed(self, message: str) -> None:
        self.status_label.setText(message)
        self._set_probe_buttons_enabled(True)

    def _set_probe_buttons_enabled(self, enabled: bool) -> None:
        self.fetch_models_button.setEnabled(enabled)
        self.test_button.setEnabled(enabled)

    def _worker_done(self, worker: AiProviderWorker) -> None:
        if worker in self._workers:
            self._workers.remove(worker)

    def save_provider(self) -> None:
        payload = self._payload()
        if not payload["model"]:
            self.status_label.setText(TEXTO_UI["ai_model_required"])
            self.model_combo.setFocus()
            return
        try:
            payload["base_url"] = validate_base_url(payload["base_url"])
            self.store.save_provider(
                payload,
                secret=self.secret_field.text(),
                remove_secret=self.remove_secret_check.isChecked(),
            )
        except (ProviderRequestError, ProviderStoreError) as error:
            popup_aviso(self.windowTitle(), str(error), self)
            return
        self.accept()

    def closeEvent(self, event):
        self._stop_workers()
        super().closeEvent(event)

    def _stop_workers(self) -> None:
        for worker in list(self._workers):
            worker.cancel()
            worker.wait(2500)

    def done(self, result: int) -> None:
        self._stop_workers()
        super().done(result)
