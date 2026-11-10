"""Ferramentas manuais de diagnóstico seguro para a página atual."""

from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtNetwork import (
    QNetworkAccessManager,
    QNetworkReply,
    QNetworkRequest,
    QSslCertificate,
)
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from _CONFIGURA_ import TEXTO_UI
from _SERVICOS_.security_analysis import (
    analyze_url_safety,
    inspect_security_headers,
)


class SiteSecurityDialog(QDialog):
    """Auditoria local de URL, cabeçalhos HTTP e certificado TLS."""

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(TEXTO_UI["site_security_title"])
        self.resize(620, 560)
        self._url = QUrl(url)
        self._active_reply: QNetworkReply | None = None
        self._active_manager: QNetworkAccessManager | None = None
        self._tls_errors: list[str] = []

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(TEXTO_UI["site_security_notice"], self))
        self.url_report = QPlainTextEdit(self)
        self.url_report.setObjectName("siteUrlSafetyReport")
        self.url_report.setReadOnly(True)
        layout.addWidget(QLabel(TEXTO_UI["url_safety_heading"], self))
        layout.addWidget(self.url_report, 1)

        self.network_report = QPlainTextEdit(self)
        self.network_report.setObjectName("siteNetworkSecurityReport")
        self.network_report.setReadOnly(True)
        self.network_report.setMaximumHeight(190)
        layout.addWidget(QLabel(TEXTO_UI["site_network_report_heading"], self))
        layout.addWidget(self.network_report)

        actions = QHBoxLayout()
        self.headers_button = QPushButton(
            TEXTO_UI["check_security_headers"], self
        )
        self.headers_button.clicked.connect(
            lambda _checked=False: self._request_head("headers")
        )
        self.certificate_button = QPushButton(
            TEXTO_UI["inspect_tls_certificate"], self
        )
        self.certificate_button.clicked.connect(
            lambda _checked=False: self._request_head("certificate")
        )
        close_button = QPushButton(TEXTO_UI["close"], self)
        close_button.clicked.connect(self.accept)
        actions.addWidget(self.headers_button)
        actions.addWidget(self.certificate_button)
        actions.addStretch(1)
        actions.addWidget(close_button)
        layout.addLayout(actions)

        self._show_local_url_report()
        self.certificate_button.setEnabled(
            self._url.scheme().lower() == "https" and bool(self._url.host())
        )
        self.headers_button.setEnabled(
            self._url.scheme().lower() in {"http", "https"}
            and bool(self._url.host())
        )

    def _show_local_url_report(self) -> None:
        result = analyze_url_safety(self._url.toString())
        host = str(result.get("host") or TEXTO_UI["unknown_site"])
        findings = result.get("findings")
        lines = [TEXTO_UI["url_safety_site"].format(host=host)]
        if isinstance(findings, list):
            lines.extend(f"• {finding}" for finding in findings)
        lines.append(TEXTO_UI["url_safety_local_only"])
        self.url_report.setPlainText("\n".join(lines))

    def _request_head(self, report_type: str) -> None:
        if self._active_reply is not None:
            return
        request_url = QUrl(self._url)
        if request_url.scheme().lower() not in {"http", "https"}:
            self.network_report.setPlainText(
                TEXTO_UI["site_security_invalid_url"]
            )
            return

        # Consulta apenas a raiz do mesmo host, sem query, fragmento, cookies
        # do perfil ou seguimento automático de redirecionamentos.
        request_url.setUserName("")
        request_url.setPassword("")
        request_url.setPath("/")
        request_url.setQuery("")
        request_url.setFragment("")
        request = QNetworkRequest(request_url)
        request.setAttribute(
            QNetworkRequest.Attribute.RedirectPolicyAttribute,
            QNetworkRequest.RedirectPolicy.ManualRedirectPolicy,
        )
        request.setTransferTimeout(8000)

        self._tls_errors = []
        manager = QNetworkAccessManager(self)
        reply = manager.head(request)
        reply.sslErrors.connect(self._collect_tls_errors)
        reply.finished.connect(
            lambda current=reply, kind=report_type, owner=manager:
            self._finish_head_request(current, kind, owner)
        )
        self._active_manager = manager
        self._active_reply = reply
        self.headers_button.setEnabled(False)
        self.certificate_button.setEnabled(False)
        self.network_report.setPlainText(TEXTO_UI["site_security_checking"])

    def _collect_tls_errors(self, errors) -> None:
        self._tls_errors = [
            error.errorString()
            for error in errors
            if hasattr(error, "errorString")
        ]

    def _finish_head_request(
        self,
        reply: QNetworkReply,
        report_type: str,
        manager: QNetworkAccessManager,
    ) -> None:
        if reply is not self._active_reply:
            return
        status = reply.attribute(
            QNetworkRequest.Attribute.HttpStatusCodeAttribute
        )
        headers = reply.rawHeaderPairs()
        error = reply.error()

        if report_type == "headers":
            text = self._format_header_report(status, headers, error, reply)
        else:
            text = self._format_certificate_report(status, error, reply)
        self.network_report.setPlainText(text)

        self._active_reply = None
        self._active_manager = None
        self.headers_button.setEnabled(
            self._url.scheme().lower() in {"http", "https"}
            and bool(self._url.host())
        )
        self.certificate_button.setEnabled(
            self._url.scheme().lower() == "https" and bool(self._url.host())
        )
        reply.deleteLater()
        manager.deleteLater()

    def _format_header_report(self, status, headers, error, reply) -> str:
        lines = [TEXTO_UI["site_security_root_only"]]
        if status is not None:
            lines.append(TEXTO_UI["site_security_http_status"].format(status=status))
        if error != QNetworkReply.NetworkError.NoError:
            lines.append(
                TEXTO_UI["site_security_request_error"].format(
                    error=reply.errorString()
                )
            )
            if status is None:
                return "\n".join(lines)
        report = inspect_security_headers(headers)
        for item in report:
            marker = "Encontrado" if item["present"] else "Não apareceu"
            lines.append(f"• {item['name']}: {marker}")
        lines.append(TEXTO_UI["site_security_head_limit"])
        return "\n".join(lines)

    def _format_certificate_report(self, status, error, reply) -> str:
        lines = [TEXTO_UI["site_certificate_root_only"]]
        if status is not None:
            lines.append(TEXTO_UI["site_security_http_status"].format(status=status))
        if self._tls_errors:
            lines.append(
                TEXTO_UI["site_security_request_error"].format(
                    error=reply.errorString()
                )
            )
            lines.extend(
                f"• {message}" for message in self._tls_errors
            )
            lines.append(TEXTO_UI["site_certificate_not_overridden"])
            return "\n".join(lines)

        try:
            certificate = reply.sslConfiguration().peerCertificate()
            if certificate.isNull():
                if error != QNetworkReply.NetworkError.NoError:
                    lines.append(
                        TEXTO_UI["site_security_request_error"].format(
                            error=reply.errorString()
                        )
                    )
                lines.append(TEXTO_UI["site_certificate_unavailable"])
                return "\n".join(lines)
            lines.append(TEXTO_UI["site_certificate_validated"])
            if error != QNetworkReply.NetworkError.NoError:
                lines.append(
                    TEXTO_UI["site_security_request_error"].format(
                        error=reply.errorString()
                    )
                )
            lines.append(
                TEXTO_UI["site_certificate_subject"].format(
                    value=self._certificate_common_name(
                        certificate, QSslCertificate.SubjectInfo.CommonName
                    )
                )
            )
            lines.append(
                TEXTO_UI["site_certificate_issuer"].format(
                    value=self._certificate_common_name(
                        certificate,
                        QSslCertificate.SubjectInfo.CommonName,
                        issuer=True,
                    )
                )
            )
            lines.append(
                TEXTO_UI["site_certificate_from"].format(
                    value=certificate.effectiveDate().toString(
                        Qt.DateFormat.ISODate
                    )
                )
            )
            lines.append(
                TEXTO_UI["site_certificate_until"].format(
                    value=certificate.expiryDate().toString(
                        Qt.DateFormat.ISODate
                    )
                )
            )
        except (AttributeError, RuntimeError, TypeError):
            lines.append(TEXTO_UI["site_certificate_unavailable"])
        return "\n".join(lines)

    @staticmethod
    def _certificate_common_name(
        certificate: QSslCertificate,
        info_type,
        *,
        issuer: bool = False,
    ) -> str:
        values = (
            certificate.issuerInfo(info_type)
            if issuer
            else certificate.subjectInfo(info_type)
        )
        if isinstance(values, (list, tuple)):
            return str(values[0]) if values else TEXTO_UI["unknown_site"]
        return str(values or TEXTO_UI["unknown_site"])

    def closeEvent(self, event) -> None:
        if self._active_reply is not None:
            self._active_reply.abort()
        super().closeEvent(event)
