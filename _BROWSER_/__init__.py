"""API pública do navegador, carregada sob demanda para evitar ciclos."""

from __future__ import annotations

__all__ = [
    "BrowserController",
    "BrowserPage",
    "BrowserWindow",
    "register_custom_url_scheme",
]


def __getattr__(name: str):
    if name == "register_custom_url_scheme":
        from .url_schemes import register_custom_url_scheme

        return register_custom_url_scheme
    if name in {"BrowserController", "BrowserPage", "BrowserWindow"}:
        from browser import BrowserController, BrowserPage, BrowserWindow

        return {
            "BrowserController": BrowserController,
            "BrowserPage": BrowserPage,
            "BrowserWindow": BrowserWindow,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
