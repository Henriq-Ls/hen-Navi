"""Registro dos esquemas próprios do navegador antes de QApplication."""

from _CONFIGURA_ import ESQUEMA_INTERNO
from PySide6.QtWebEngineCore import QWebEngineUrlScheme


_SCHEME_REGISTERED = False


def register_custom_url_scheme() -> None:
    """Registra o esquema interno, sem duplicar o registro no mesmo processo."""
    global _SCHEME_REGISTERED
    if _SCHEME_REGISTERED:
        return

    scheme_name = ESQUEMA_INTERNO.encode("ascii")
    existing = QWebEngineUrlScheme.schemeByName(scheme_name)
    if existing.name():
        _SCHEME_REGISTERED = True
        return

    scheme = QWebEngineUrlScheme(scheme_name)
    scheme.setSyntax(QWebEngineUrlScheme.Syntax.HostAndPort)
    scheme.setFlags(QWebEngineUrlScheme.Flag.SecureScheme)
    scheme.setDefaultPort(443)
    QWebEngineUrlScheme.registerScheme(scheme)
    _SCHEME_REGISTERED = True
