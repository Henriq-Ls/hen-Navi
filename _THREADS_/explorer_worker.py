"""Tarefas cooperativas do Explorador; não acessam widgets."""

from __future__ import annotations

from threading import Event

from PySide6.QtCore import QObject, QRunnable, Signal

from _SERVICOS_.explorer_filesystem import (
    ExplorerCancelled,
    ExplorerError,
    ExplorerLimits,
    ExplorerSelection,
    generate_tree,
    scan_directory,
)


class ExplorerTaskSignals(QObject):
    result = Signal(int, object)
    failed = Signal(int, str)
    finished = Signal(int)


class ExplorerTask(QRunnable):
    def __init__(
        self,
        request_id: int,
        operation: str,
        arguments: tuple,
        *,
        cancel_event: Event | None = None,
    ):
        super().__init__()
        self.request_id = request_id
        self.operation = operation
        self.arguments = arguments
        self.cancel_event = cancel_event or Event()
        self.signals = ExplorerTaskSignals()

    def cancel(self):
        self.cancel_event.set()

    def run(self):
        try:
            if self.operation == "scan":
                root, directory, ignored, limits, show_ignored = self.arguments
                result = scan_directory(
                    root,
                    directory,
                    ignored,
                    limits,
                    show_ignored=show_ignored,
                    cancel_event=self.cancel_event,
                )
            elif self.operation == "tree":
                root, selection_data, ignored, limits, show_ignored = self.arguments
                selection = ExplorerSelection(
                    selection_data.get("included", ()),
                    selection_data.get("excluded", ()),
                    include_all=bool(
                        selection_data.get("include_all", False)
                    ),
                )
                result = generate_tree(
                    root,
                    selection,
                    ignored,
                    limits,
                    show_ignored=show_ignored,
                    cancel_event=self.cancel_event,
                )
            else:
                raise ExplorerError("Operação desconhecida do Explorador.")
            if not self.cancel_event.is_set():
                self.signals.result.emit(self.request_id, result)
        except ExplorerCancelled:
            pass
        except ExplorerError as error:
            if not self.cancel_event.is_set():
                self.signals.failed.emit(self.request_id, str(error))
        except Exception:
            if not self.cancel_event.is_set():
                self.signals.failed.emit(
                    self.request_id,
                    "Não foi possível concluir a leitura da pasta.",
                )
        finally:
            self.signals.finished.emit(self.request_id)
