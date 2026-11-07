"""Controles de privacidade limitados à origem aberta no navegador."""

from __future__ import annotations

import json

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEnginePermission,
    QWebEngineProfile,
)
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from _CONFIGURA_ import TEXTO_UI
from _ULTILIDADES_.popups import popup_pergunta


_CLEAR_SITE_DATA_SCRIPT = r"""
(expectedOrigin) => {
    if (location.origin !== expectedOrigin) return false;
    try { localStorage.clear(); } catch (_) {}
    try { sessionStorage.clear(); } catch (_) {}
    try {
        if (window.caches) {
            caches.keys().then((keys) =>
                Promise.all(keys.map((key) => caches.delete(key)))
            ).catch(() => {});
        }
    } catch (_) {}
    try {
        if (window.indexedDB && indexedDB.databases) {
            indexedDB.databases().then((databases) =>
                databases.forEach((database) => {
                    if (database.name) indexedDB.deleteDatabase(database.name);
                })
            ).catch(() => {});
        }
    } catch (_) {}
    try {
        if (navigator.serviceWorker) {
            navigator.serviceWorker.getRegistrations().then((registrations) =>
                registrations.forEach((registration) => registration.unregister())
            ).catch(() => {});
        }
    } catch (_) {}
    return true;
}
"""

_PERMISSION_TYPES = (
    ("Microfone", "MediaAudioCapture"),
    ("Câmera", "MediaVideoCapture"),
    ("Microfone e câmera", "MediaAudioVideoCapture"),
    ("Localização", "Geolocation"),
    ("Notificações", "Notifications"),
)


class SitePrivacyDialog(QDialog):
    """Mostra permissões e limpa dados da origem atual, sem afetar outros sites."""

    def __init__(
        self,
        page: QWebEnginePage,
        profile: QWebEngineProfile,
        url: str,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(TEXTO_UI["site_privacy_title"])
        self.resize(560, 430)
        self.page = page
        self.profile = profile
        self.url = QUrl(url)
        self.origin = QUrl(self.url)
        self.origin.setPath("")
        self.origin.setQuery("")
        self.origin.setFragment("")
        self.host = self.url.host().lower().rstrip(".")
        self._cookie_store = profile.cookieStore()
        self._cookies: list[object] = []
        self._cookie_keys: set[bytes] = set()
        self._collecting_cookies = False
        self._pending_cookie_count = 0
        self._local_clear_finished = False
        self._local_clear_succeeded = False

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                TEXTO_UI["site_privacy_site"].format(
                    origin=self.origin.toString()
                ),
                self,
            )
        )
        layout.addWidget(QLabel(TEXTO_UI["site_permissions_heading"], self))
        self.permissions_view = QPlainTextEdit(self)
        self.permissions_view.setObjectName("sitePermissionsReport")
        self.permissions_view.setReadOnly(True)
        self.permissions_view.setMaximumHeight(170)
        layout.addWidget(self.permissions_view)

        permission_actions = QHBoxLayout()
        self.refresh_permissions_button = QPushButton(
            TEXTO_UI["site_permissions_refresh"], self
        )
        self.refresh_permissions_button.clicked.connect(
            self.refresh_permissions
        )
        self.revoke_permissions_button = QPushButton(
            TEXTO_UI["site_permissions_revoke"], self
        )
        self.revoke_permissions_button.clicked.connect(
            self.revoke_site_permissions
        )
        permission_actions.addWidget(self.refresh_permissions_button)
        permission_actions.addWidget(self.revoke_permissions_button)
        layout.addLayout(permission_actions)

        self.clear_status = QLabel(TEXTO_UI["site_data_scope_note"], self)
        self.clear_status.setWordWrap(True)
        layout.addWidget(self.clear_status)

        bottom_actions = QHBoxLayout()
        self.clear_site_data_button = QPushButton(
            TEXTO_UI["site_data_clear"], self
        )
        self.clear_site_data_button.clicked.connect(self.clear_site_data)
        close_button = QPushButton(TEXTO_UI["close"], self)
        close_button.clicked.connect(self.accept)
        bottom_actions.addWidget(self.clear_site_data_button)
        bottom_actions.addStretch(1)
        bottom_actions.addWidget(close_button)
        layout.addLayout(bottom_actions)

        self._cookie_quiet_timer = QTimer(self)
        self._cookie_quiet_timer.setSingleShot(True)
        self._cookie_quiet_timer.setInterval(1200)
        self._cookie_quiet_timer.timeout.connect(self._delete_loaded_cookies)

        self.refresh_permissions()

    def refresh_permissions(self) -> None:
        query_permission = getattr(self.profile, "queryPermission", None)
        permission_types = getattr(QWebEnginePermission, "PermissionType", None)
        if not callable(query_permission) or permission_types is None:
            self.permissions_view.setPlainText(
                TEXTO_UI["site_permissions_unavailable"]
            )
            return

        lines = []
        for label, enum_name in _PERMISSION_TYPES:
            permission_type = getattr(permission_types, enum_name, None)
            if permission_type is None:
                continue
            try:
                permission = query_permission(self.origin, permission_type)
                state = permission.state()
                state_name = getattr(state, "name", str(state)).lower()
                state_name = state_name.rsplit(".", 1)[-1]
            except (AttributeError, RuntimeError, TypeError):
                continue
            if "granted" in state_name:
                status = TEXTO_UI["site_permission_allowed"]
            elif "denied" in state_name:
                status = TEXTO_UI["site_permission_denied"]
            else:
                status = TEXTO_UI["site_permission_not_set"]
            lines.append(f"• {label}: {status}")

        self.permissions_view.setPlainText(
            "\n".join(lines) if lines else TEXTO_UI["site_permissions_empty"]
        )

    def revoke_site_permissions(self, *_):
        answer = popup_pergunta(
            TEXTO_UI["site_permissions_revoke_title"],
            TEXTO_UI["site_permissions_revoke_confirm"].format(
                origin=self.origin.toString()
            ),
            self,
            botoes=(
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            botao_padrao=QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        query_permission = getattr(self.profile, "queryPermission", None)
        permission_types = getattr(QWebEnginePermission, "PermissionType", None)
        if not callable(query_permission) or permission_types is None:
            self.clear_status.setText(TEXTO_UI["site_permissions_unavailable"])
            return

        reset_count = 0
        for _label, enum_name in _PERMISSION_TYPES:
            permission_type = getattr(permission_types, enum_name, None)
            if permission_type is None:
                continue
            try:
                permission = query_permission(self.origin, permission_type)
                state = permission.state()
                state_name = getattr(state, "name", str(state)).lower()
                if "ask" in state_name or "unknown" in state_name:
                    continue
                permission.reset()
                reset_count += 1
            except (AttributeError, RuntimeError, TypeError):
                continue

        self.refresh_permissions()
        self.clear_status.setText(
            TEXTO_UI["site_permissions_revoked"].format(count=reset_count)
        )

    def clear_site_data(self, *_):
        answer = popup_pergunta(
            TEXTO_UI["site_data_clear_title"],
            TEXTO_UI["site_data_clear_confirm"].format(
                origin=self.origin.toString()
            ),
            self,
            botoes=(
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            botao_padrao=QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        if self.page is None or not self.host:
            self.clear_status.setText(TEXTO_UI["site_data_clear_unavailable"])
            return

        self.clear_site_data_button.setEnabled(False)
        self.clear_status.setText(TEXTO_UI["site_data_clearing"])
        self._cookies.clear()
        self._cookie_keys.clear()
        self._pending_cookie_count = 0
        self._local_clear_finished = False
        self._local_clear_succeeded = False
        self._collecting_cookies = True
        self._cookie_store.cookieAdded.connect(self._collect_cookie)
        self._cookie_quiet_timer.start()
        self._cookie_store.loadAllCookies()
        self.page.runJavaScript(
            f"({_CLEAR_SITE_DATA_SCRIPT})({json.dumps(self.origin.toString())})",
            self._on_local_data_cleared,
        )

    def _collect_cookie(self, cookie) -> None:
        if not self._collecting_cookies or not self._cookie_matches_site(cookie):
            return
        try:
            key = bytes(cookie.toRawForm())
        except (AttributeError, TypeError, RuntimeError):
            return
        if key not in self._cookie_keys:
            self._cookie_keys.add(key)
            self._cookies.append(cookie)
        self._cookie_quiet_timer.start()

    def _cookie_matches_site(self, cookie) -> bool:
        try:
            domain = cookie.domain()
            if isinstance(domain, bytes):
                domain = domain.decode("utf-8", errors="ignore")
            domain = str(domain).lower().lstrip(".").rstrip(".")
            host = self.host.encode("idna").decode("ascii").lower()
            domain = domain.encode("idna").decode("ascii").lower()
        except (AttributeError, UnicodeError, TypeError):
            return False
        return host == domain or host.endswith(f".{domain}")

    def _delete_loaded_cookies(self) -> None:
        if not self._collecting_cookies:
            return
        self._collecting_cookies = False
        try:
            self._cookie_store.cookieAdded.disconnect(self._collect_cookie)
        except (RuntimeError, TypeError):
            pass
        for cookie in self._cookies:
            try:
                self._cookie_store.deleteCookie(cookie)
                self._pending_cookie_count += 1
            except (AttributeError, RuntimeError, TypeError):
                continue
        self._maybe_finish_clear()

    def _on_local_data_cleared(self, succeeded) -> None:
        self._local_clear_finished = True
        self._local_clear_succeeded = bool(succeeded)
        self._maybe_finish_clear()

    def _maybe_finish_clear(self) -> None:
        if self._collecting_cookies or not self._local_clear_finished:
            return
        self.clear_site_data_button.setEnabled(True)
        if not self._local_clear_succeeded:
            self.clear_status.setText(TEXTO_UI["site_data_origin_changed"])
            return
        self.clear_status.setText(
            TEXTO_UI["site_data_clear_done"].format(
                count=self._pending_cookie_count
            )
        )
