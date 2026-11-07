"""Diálogo de credenciais web com captura e preenchimento iniciados pelo usuário."""

from __future__ import annotations

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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
    QVBoxLayout,
)

from _CONFIGURA_ import TEXTO_UI
from _SERVICOS_.web_credential_store import (
    WebCredentialStore,
    WebCredentialStoreError,
    origin_for_url,
)
from _ULTILIDADES_.popups import popup_aviso, popup_pergunta


_READ_LOGIN_SCRIPT = r"""
(() => {
    const visible = (input) => {
        if (!(input instanceof HTMLInputElement) || input.disabled) return false;
        const style = getComputedStyle(input);
        return input.type !== "hidden" &&
            style.display !== "none" &&
            style.visibility !== "hidden" &&
            input.getClientRects().length > 0;
    };
    const password = Array.from(
        document.querySelectorAll('input[type="password"]')
    ).find(visible);
    if (!password) return {username: "", password: ""};

    const scope = password.form || document;
    const candidates = Array.from(scope.querySelectorAll("input"))
        .filter((input) => visible(input) && input !== password)
        .map((input) => {
            const hint = [
                input.name,
                input.id,
                input.placeholder,
                input.getAttribute("aria-label") || ""
            ].join(" ").toLowerCase();
            let score = 0;
            if ((input.autocomplete || "").toLowerCase() === "username") {
                score = 10;
            } else if (input.type === "email") {
                score = 8;
            } else if (/(email|user|login|account)/.test(hint)) {
                score = 5;
            } else if (input.type === "text") {
                score = 1;
            }
            return {input, score};
        })
        .filter((candidate) => candidate.score > 0)
        .sort((left, right) => right.score - left.score);

    return {
        username: candidates.length ? candidates[0].input.value : "",
        password: password.value || ""
    };
})()
"""


def _fill_login_script(origin: str, username: str, password: str) -> str:
    expected_origin = json.dumps(origin)
    username_json = json.dumps(username)
    password_json = json.dumps(password)
    return f"""
(() => {{
    if (location.origin !== {expected_origin}) return false;
    const visible = (input) => {{
        if (!(input instanceof HTMLInputElement) || input.disabled) return false;
        const style = getComputedStyle(input);
        return input.type !== "hidden" &&
            style.display !== "none" &&
            style.visibility !== "hidden" &&
            input.getClientRects().length > 0;
    }};
    const passwordInput = Array.from(
        document.querySelectorAll('input[type="password"]')
    ).find(visible);
    if (!passwordInput) return false;

    const scope = passwordInput.form || document;
    const usernameCandidates = Array.from(scope.querySelectorAll("input"))
        .filter((input) => visible(input) && input !== passwordInput)
        .map((input) => {{
            const autocomplete = (input.autocomplete || "").toLowerCase();
            const hint = [
                input.name,
                input.id,
                input.placeholder,
                input.getAttribute("aria-label") || ""
            ].join(" ").toLowerCase();
            let score = 0;
            if (autocomplete === "username") score = 10;
            else if (input.type === "email") score = 8;
            else if (/(email|user|login|account)/.test(hint)) score = 5;
            else if (input.type === "text") score = 1;
            return {{input, score}};
        }})
        .filter((candidate) => candidate.score > 0)
        .sort((left, right) => right.score - left.score);
    const usernameInput = usernameCandidates.length
        ? usernameCandidates[0].input
        : null;

    const setValue = (input, value) => {{
        const setter = Object.getOwnPropertyDescriptor(
            HTMLInputElement.prototype, "value"
        ).set;
        setter.call(input, value);
        input.dispatchEvent(new Event("input", {{bubbles: true}}));
        input.dispatchEvent(new Event("change", {{bubbles: true}}));
    }};
    if (usernameInput) setValue(usernameInput, {username_json});
    setValue(passwordInput, {password_json});
    passwordInput.focus();
    return true;
}})()
"""


class SaveLoginDialog(QDialog):
    def __init__(
        self,
        origin: str,
        username: str = "",
        password: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(TEXTO_UI["password_save_title"])
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        site_label = QLabel(origin, self)
        site_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        form.addRow(TEXTO_UI["password_site"], site_label)

        self.username_field = QLineEdit(self)
        self.username_field.setText(username)
        self.username_field.setMaxLength(4096)
        form.addRow(TEXTO_UI["password_username"], self.username_field)

        self.password_field = QLineEdit(self)
        self.password_field.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_field.setText(password)
        self.password_field.setMaxLength(4096)
        form.addRow(TEXTO_UI["password_password"], self.password_field)
        layout.addLayout(form)

        note = QLabel(TEXTO_UI["password_save_notice"], self)
        note.setWordWrap(True)
        layout.addWidget(note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def credentials(self) -> tuple[str, str]:
        return self.username_field.text(), self.password_field.text()

    def clear_sensitive_fields(self) -> None:
        self.password_field.clear()
        self.username_field.clear()


class PasswordManagerDialog(QDialog):
    """Mostra e usa apenas os logins da origem HTTPS aberta."""

    def __init__(self, store: WebCredentialStore, page, parent=None):
        super().__init__(parent)
        self.store = store
        self.page = page
        try:
            self.origin = origin_for_url(page.url().toString())
        except WebCredentialStoreError:
            self.origin = ""

        self.setWindowTitle(TEXTO_UI["password_manager_title"])
        self.resize(520, 360)
        layout = QVBoxLayout(self)

        self.site_label = QLabel(
            TEXTO_UI["password_site"].format(
                origin=self.origin or TEXTO_UI["password_https_required"]
            ),
            self,
        )
        self.site_label.setWordWrap(True)
        layout.addWidget(self.site_label)

        self.status_label = QLabel("", self)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.entries = QListWidget(self)
        self.entries.currentItemChanged.connect(self._update_buttons)
        self.entries.itemDoubleClicked.connect(
            lambda _item: self.fill_selected()
        )
        layout.addWidget(self.entries, 1)

        buttons = QHBoxLayout()
        self.save_button = QPushButton(
            TEXTO_UI["password_save_current"], self
        )
        self.save_button.clicked.connect(self.save_current_login)
        buttons.addWidget(self.save_button)

        self.fill_button = QPushButton(TEXTO_UI["password_fill"], self)
        self.fill_button.clicked.connect(self.fill_selected)
        buttons.addWidget(self.fill_button)

        self.delete_button = QPushButton(TEXTO_UI["password_delete"], self)
        self.delete_button.clicked.connect(self.delete_selected)
        buttons.addWidget(self.delete_button)

        self.close_button = QPushButton(TEXTO_UI["close"], self)
        self.close_button.clicked.connect(self.accept)
        buttons.addWidget(self.close_button)
        layout.addLayout(buttons)
        self._refresh()

    def _page_matches_origin(self) -> bool:
        try:
            return bool(
                self.origin
                and origin_for_url(self.page.url().toString()) == self.origin
            )
        except WebCredentialStoreError:
            return False

    def _refresh(self) -> None:
        self.entries.clear()
        if not self.origin:
            self.status_label.setText(TEXTO_UI["password_https_required"])
            self._update_buttons()
            return
        try:
            accounts = self.store.list_for_origin(self.origin)
        except WebCredentialStoreError as error:
            self.status_label.setText(str(error))
            self._update_buttons()
            return

        self.status_label.setText(
            TEXTO_UI["password_none"] if not accounts else ""
        )
        for account in accounts:
            item = QListWidgetItem(
                account["username"] or TEXTO_UI["password_account"]
            )
            item.setData(Qt.ItemDataRole.UserRole, account["id"])
            self.entries.addItem(item)
        self._update_buttons()

    def _update_buttons(self, *_args) -> None:
        origin_matches = self._page_matches_origin()
        self.save_button.setEnabled(origin_matches)
        selected = origin_matches and self.entries.currentItem() is not None
        self.fill_button.setEnabled(selected)
        self.delete_button.setEnabled(selected)

    def save_current_login(self) -> None:
        if not self._page_matches_origin():
            popup_aviso(
                self.windowTitle(),
                TEXTO_UI["password_page_changed"],
                self,
            )
            return
        self.page.runJavaScript(_READ_LOGIN_SCRIPT, self._on_login_captured)

    def _on_login_captured(self, values) -> None:
        if not self._page_matches_origin():
            popup_aviso(
                self.windowTitle(),
                TEXTO_UI["password_page_changed"],
                self,
            )
            return
        values = values if isinstance(values, dict) else {}
        dialog = SaveLoginDialog(
            self.origin,
            str(values.get("username") or ""),
            str(values.get("password") or ""),
            self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            dialog.clear_sensitive_fields()
            return
        username, password = dialog.credentials()
        dialog.clear_sensitive_fields()
        try:
            self.store.save_login(self.origin, username, password)
        except WebCredentialStoreError as error:
            popup_aviso(self.windowTitle(), str(error), self)
            return
        finally:
            password = ""
        self._refresh()
        self.status_label.setText(TEXTO_UI["password_saved"])

    def fill_selected(self) -> None:
        if not self._page_matches_origin():
            popup_aviso(
                self.windowTitle(),
                TEXTO_UI["password_page_changed"],
                self,
            )
            return
        item = self.entries.currentItem()
        if item is None:
            return
        credential_id = str(item.data(Qt.ItemDataRole.UserRole) or "")
        try:
            login = self.store.get_login(credential_id, self.origin)
        except WebCredentialStoreError as error:
            popup_aviso(self.windowTitle(), str(error), self)
            self._refresh()
            return

        script = _fill_login_script(
            self.origin,
            login["username"],
            login["password"],
        )
        login["password"] = ""
        self.page.runJavaScript(script, self._on_login_filled)
        script = ""

    def _on_login_filled(self, filled) -> None:
        if filled:
            self.accept()
            return
        popup_aviso(
            self.windowTitle(),
            TEXTO_UI["password_fields_missing"],
            self,
        )

    def delete_selected(self) -> None:
        item = self.entries.currentItem()
        if item is None or not self._page_matches_origin():
            return
        credential_id = str(item.data(Qt.ItemDataRole.UserRole) or "")
        answer = popup_pergunta(
            TEXTO_UI["password_delete_title"],
            TEXTO_UI["password_delete_confirm"].format(
                username=item.text(),
                origin=self.origin,
            ),
            self,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.store.delete_login(credential_id, self.origin)
        except WebCredentialStoreError as error:
            popup_aviso(self.windowTitle(), str(error), self)
            return
        self._refresh()
