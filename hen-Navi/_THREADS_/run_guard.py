"""Invólucro Python para registrar exceções de run() em threads seguras."""

from __future__ import annotations

import traceback
from functools import wraps
from typing import Callable


def _log_thread_exception(thread_name: str, details: str) -> None:
    from _LOGS_ import log

    log.crash("ThreadSegura", thread_name, details)


def protect_run_method(run_method: Callable):
    """Captura e registra exceções de qualquer implementação sobrescrita de run."""
    if getattr(run_method, "__threadsegura_guarded__", False):
        return run_method

    @wraps(run_method)
    def guarded(self, *args, **kwargs):
        try:
            return run_method(self, *args, **kwargs)
        except Exception:
            thread_name = getattr(self, "_nome_thread", type(self).__name__)
            _log_thread_exception(thread_name, traceback.format_exc())
            return None

    guarded.__threadsegura_guarded__ = True
    return guarded


def protect_subclass_run(cls) -> None:
    """Aplica a proteção ao run declarado diretamente por uma subclasse."""
    run_method = cls.__dict__.get("run")
    if run_method is not None:
        cls.run = protect_run_method(run_method)
