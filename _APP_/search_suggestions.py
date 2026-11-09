"""Qt bridge and non-blocking network requests for search suggestions."""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtNetwork import (
    QNetworkAccessManager,
    QNetworkReply,
    QNetworkRequest,
)

from _SERVICOS_.search_suggestions import (
    build_suggestion_url,
    parse_search_suggestions,
)


class SearchSuggestionService(QObject):
    """Fetches suggestions only from the browser's selected search provider."""

    resultsReady = Signal(str, str, list)
    DEBOUNCE_MS = 250
    TIMEOUT_MS = 5000

    def __init__(self, parent=None):
        super().__init__(parent)
        self._network = QNetworkAccessManager(self)
        self._timers: dict[str, QTimer] = {}
        self._pending: dict[str, tuple[str, str, int]] = {}
        self._replies: dict[str, QNetworkReply] = {}
        self._generations: dict[str, int] = {}

    def request(self, source: str, query: str, search_engine: str):
        value = (query or "").strip()
        generation = self._generations.get(source, 0) + 1
        self._generations[source] = generation

        timer = self._timer_for(source)
        timer.stop()
        self._pending.pop(source, None)

        previous_reply = self._replies.pop(source, None)
        if previous_reply is not None:
            previous_reply.abort()

        if len(value) < 2:
            self.resultsReady.emit(source, value, [])
            return

        self._pending[source] = (value, search_engine, generation)
        timer.start(self.DEBOUNCE_MS)

    def cancel(self, source: str):
        self._generations[source] = self._generations.get(source, 0) + 1
        timer = self._timers.get(source)
        if timer is not None:
            timer.stop()
        self._pending.pop(source, None)
        reply = self._replies.pop(source, None)
        if reply is not None:
            reply.abort()

    def _timer_for(self, source: str) -> QTimer:
        timer = self._timers.get(source)
        if timer is None:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(
                lambda request_source=source: self._send_request(request_source)
            )
            self._timers[source] = timer
        return timer

    def _send_request(self, source: str):
        pending = self._pending.pop(source, None)
        if pending is None:
            return
        query, search_engine, generation = pending
        try:
            suggestion_url = build_suggestion_url(query, search_engine)
        except ValueError:
            self.resultsReady.emit(source, query, [])
            return
        if not suggestion_url:
            self.resultsReady.emit(source, query, [])
            return

        request = QNetworkRequest(QUrl(suggestion_url))
        request.setTransferTimeout(self.TIMEOUT_MS)
        request.setRawHeader(b"Accept", b"application/json")
        reply = self._network.get(request)
        self._replies[source] = reply
        reply.finished.connect(
            lambda current_reply=reply, request_source=source,
            requested_query=query, requested_engine=search_engine,
            request_generation=generation:
            self._handle_reply(
                request_source,
                requested_query,
                requested_engine,
                request_generation,
                current_reply,
            )
        )

    def _handle_reply(
        self,
        source: str,
        query: str,
        search_engine: str,
        generation: int,
        reply: QNetworkReply,
    ):
        is_current_reply = self._replies.get(source) is reply
        if is_current_reply:
            self._replies.pop(source, None)
        payload = bytes(reply.readAll())
        request_succeeded = (
            reply.error() == QNetworkReply.NetworkError.NoError
        )
        reply.deleteLater()

        if generation != self._generations.get(source):
            return
        suggestions = (
            parse_search_suggestions(search_engine, payload)
            if request_succeeded and is_current_reply
            else []
        )
        self.resultsReady.emit(source, query, suggestions)


class HomeSearchBridge(QObject):
    """QWebChannel endpoint used only by the local start-page search field."""

    requestReceived = Signal(str)
    searchRequested = Signal(str)
    suggestionsReady = Signal(str, list)

    @Slot(str)
    def requestSuggestions(self, query: str):
        self.requestReceived.emit(query)

    @Slot(str)
    def submitSearch(self, query: str):
        self.searchRequested.emit(query)
