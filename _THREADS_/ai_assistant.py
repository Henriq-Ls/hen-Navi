"""Workers canceláveis para chamadas de configuração e assistência à página."""

from __future__ import annotations

import uuid

from PySide6.QtCore import Signal

from _LOGS_ import log
from _THREADS_.thread_segura import ThreadSegura
from _SERVICOS_.ai_provider_store import ProviderStore, ProviderStoreError
from _SERVICOS_.ai_service import (
    ProviderClient,
    ProviderRequestError,
    RequestCancelled,
)


class AiProviderWorker(ThreadSegura):
    answerReady = Signal(str, bool)
    modelsReady = Signal(object)
    testReady = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        operation: str,
        provider: dict,
        config_directory: str,
        *,
        page_text: str = "",
        question: str = "",
        summarize: bool = False,
        history: list[dict[str, str]] | None = None,
        secret_override: str | None = None,
        parent=None,
    ):
        super().__init__(
            nome=f"ai_provider_{operation}_{uuid.uuid4().hex[:8]}",
            parent=parent,
        )
        self.operation = operation
        self.provider = dict(provider)
        self.store = ProviderStore(config_directory)
        self.page_text = page_text
        self.question = question
        self.summarize = summarize
        self.history = list(history or [])
        self.secret_override = secret_override
        self._client: ProviderClient | None = None

    def cancel(self) -> None:
        self.requestInterruption()
        if self._client is not None:
            self._client.cancel()

    def run(self):
        try:
            log.info(
                "AiProviderWorker",
                "run",
                f"início; operação={self.operation}; "
                f"plataforma={self.provider.get('platform', '')}; "
                f"modelo={self.provider.get('model', '')}",
            )
            if self.isInterruptionRequested():
                raise RequestCancelled("Solicitação cancelada.")
            secret_source = (
                "temporária"
                if self.secret_override is not None
                else "cofre_do_sistema"
            )
            secret = (
                self.secret_override
                if self.secret_override is not None
                else self.store.get_secret(self.provider)
            )
            log.info(
                "AiProviderWorker",
                "run",
                f"credencial carregada; origem={secret_source}; "
                f"presente={bool(secret)}",
            )
            if self.isInterruptionRequested():
                raise RequestCancelled("Solicitação cancelada.")
            self._client = ProviderClient(self.provider, secret)
            if self.operation == "models":
                models = self._client.list_models()
                log.ok(
                    "AiProviderWorker",
                    "run",
                    f"lista de modelos recebida; quantidade={len(models)}",
                )
                self.modelsReady.emit(models)
            elif self.operation == "test":
                message = self._client.test_connection()
                log.ok("AiProviderWorker", "run", "teste de conexão concluído")
                self.testReady.emit(message)
            elif self.operation == "ask":
                log.info(
                    "AiProviderWorker",
                    "run",
                    f"envio preparado; caracteres_página={len(self.page_text)}; "
                    f"caracteres_pergunta={len(self.question)}",
                )
                answer, truncated = self._client.ask(
                    self.page_text,
                    self.question,
                    summarize=self.summarize,
                    history=self.history,
                    max_page_chars=int(self.provider.get("max_page_chars", 12000)),
                )
                log.ok(
                    "AiProviderWorker",
                    "run",
                    f"resposta da IA recebida; caracteres={len(answer)}; "
                    f"texto_cortado={truncated}",
                )
                self.answerReady.emit(answer, truncated)
            else:
                self.failed.emit("Operação de IA desconhecida.")
        except (ProviderStoreError, ProviderRequestError) as error:
            log.erro(
                "AiProviderWorker",
                "run",
                f"operação={self.operation}; erro={type(error).__name__}: {error}",
            )
            self.failed.emit(str(error))
        except Exception as error:
            # Não encaminha detalhes inesperados do transporte, que podem incluir URL.
            log.erro(
                "AiProviderWorker",
                "run",
                f"operação={self.operation}; falha inesperada; "
                f"tipo={type(error).__name__}",
            )
            self.failed.emit("Ocorreu um erro inesperado na conexão de IA.")
        finally:
            self._client = None
