"""Interceptor Qt e atualização opcional da lista do bloqueador."""

from __future__ import annotations

from threading import Lock
from urllib.request import Request, urlopen

from PySide6.QtCore import Signal
from PySide6.QtWebEngineCore import (
    QWebEngineUrlRequestInfo,
    QWebEngineUrlRequestInterceptor,
)

from _CONFIGURA_ import LIMITE_LISTA_BLOQUEIO_BYTES, TIMEOUT_LISTA_BLOQUEIO_S
from _THREADS_.thread_segura import ThreadSegura
from _SERVICOS_.adblock_rules import BlocklistMatcher
from _ULTILIDADES_.site_utils import extract_site_host, normalize_host


_DATA_SAVER_RESOURCE_TYPES = frozenset(
    {
        QWebEngineUrlRequestInfo.ResourceType.ResourceTypeImage,
        QWebEngineUrlRequestInfo.ResourceType.ResourceTypeMedia,
        QWebEngineUrlRequestInfo.ResourceType.ResourceTypePrefetch,
    }
)


class AdBlockInterceptor(QWebEngineUrlRequestInterceptor):
    """Bloqueia sub-recursos e mantém contagens por site com proteção de lock."""

    blockedCountChanged = Signal(str, int)
    siteEnabledChanged = Signal(str, bool)
    enabledChanged = Signal(bool)
    dataSaverChanged = Signal(bool)

    def __init__(
        self,
        matcher: BlocklistMatcher,
        *,
        enabled: bool = True,
        data_saver_enabled: bool = False,
        exceptions=(),
        parent=None,
    ):
        super().__init__(parent)
        self._matcher = matcher
        self._lock = Lock()
        self._enabled = bool(enabled)
        self._data_saver_enabled = bool(data_saver_enabled)
        self._exceptions = {
            host
            for value in exceptions
            if (host := normalize_host(value, strip_www=True))
        }
        self._blocked_counts: dict[str, int] = {}

    def is_enabled(self) -> bool:
        with self._lock:
            return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        value = bool(enabled)
        with self._lock:
            changed = self._enabled != value
            self._enabled = value
        if changed:
            self.enabledChanged.emit(value)

    def is_data_saver_enabled(self) -> bool:
        with self._lock:
            return self._data_saver_enabled

    def set_data_saver_enabled(self, enabled: bool) -> None:
        value = bool(enabled)
        with self._lock:
            changed = self._data_saver_enabled != value
            self._data_saver_enabled = value
        if changed:
            self.dataSaverChanged.emit(value)

    def site_is_enabled(self, host: str) -> bool:
        site = normalize_host(host, strip_www=True)
        if not site:
            return self.is_enabled()
        with self._lock:
            exceptions = tuple(self._exceptions)
            enabled = self._enabled
        return enabled and not any(
            _site_matches_exception(site, exception) for exception in exceptions
        )

    def set_site_enabled(self, host: str, enabled: bool) -> bool:
        site = normalize_host(host, strip_www=True)
        if not site:
            return False
        with self._lock:
            if enabled:
                self._exceptions.discard(site)
            else:
                self._exceptions.add(site)
        self.siteEnabledChanged.emit(site, bool(enabled))
        return True

    def exceptions_snapshot(self) -> frozenset[str]:
        with self._lock:
            return frozenset(self._exceptions)

    def blocked_count(self, host: str) -> int:
        site = normalize_host(host, strip_www=True)
        with self._lock:
            return self._blocked_counts.get(site, 0)

    def counts_snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._blocked_counts)

    def interceptRequest(self, info: QWebEngineUrlRequestInfo) -> None:
        try:
            resource_type = info.resourceType()
            main_frame_types = {
                QWebEngineUrlRequestInfo.ResourceType.ResourceTypeMainFrame,
                QWebEngineUrlRequestInfo.ResourceType.ResourceTypeNavigationPreloadMainFrame,
            }
            if resource_type in main_frame_types:
                return

            first_party_url = info.firstPartyUrl().toString()
            site = extract_site_host(first_party_url)
            if not site:
                return

            with self._lock:
                enabled = self._enabled
                data_saver_enabled = self._data_saver_enabled
                exceptions = frozenset(self._exceptions)
            if (
                data_saver_enabled
                and resource_type in _DATA_SAVER_RESOURCE_TYPES
            ):
                info.block(True)
                return

            request_url = info.requestUrl().toString()
            if not self._matcher.should_block(
                request_url,
                first_party_url,
                is_main_frame=False,
                enabled=enabled,
                exceptions=exceptions,
            ):
                return

            info.block(True)
            with self._lock:
                count = self._blocked_counts.get(site, 0) + 1
                self._blocked_counts[site] = count
            self.blockedCountChanged.emit(site, count)
        except Exception as error:
            from _LOGS_ import log

            log.erro("AdBlockInterceptor", "interceptRequest", str(error))


def _site_matches_exception(site: str, exception: str) -> bool:
    return site == exception or site.endswith("." + exception)


class BlocklistDownloadThread(ThreadSegura):
    """Baixa uma lista HTTPS fora da interface e emite o texto recebido."""

    downloaded = Signal(str)
    failed = Signal(str)

    def __init__(self, url: str, parent=None):
        super().__init__(nome="atualizar_lista_bloqueio", parent=parent)
        self.url = url

    def run(self):
        try:
            request = Request(
                self.url,
                headers={"User-Agent": "hen-Nave/0.1"},
            )
            with urlopen(request, timeout=TIMEOUT_LISTA_BLOQUEIO_S) as response:
                if not response.geturl().lower().startswith("https://"):
                    raise ValueError("A lista foi redirecionada para uma conexão insegura.")
                content = response.read(LIMITE_LISTA_BLOQUEIO_BYTES + 1)
            if len(content) > LIMITE_LISTA_BLOQUEIO_BYTES:
                raise ValueError("A resposta excedeu o limite de tamanho.")
            self.downloaded.emit(content.decode("utf-8-sig"))
        except Exception as error:
            self.failed.emit(str(error))
            raise
