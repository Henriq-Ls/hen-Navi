"""Funções puras para nomes e limites de capturas de página."""

from __future__ import annotations

import re
from datetime import datetime


_INVALID_WINDOWS_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WHITESPACE = re.compile(r"\s+")


def sanitize_capture_name(value: str) -> str:
    cleaned = _INVALID_WINDOWS_FILENAME.sub("_", str(value or ""))
    cleaned = _WHITESPACE.sub("_", cleaned).strip(" ._")
    return cleaned or "captura"


def capture_filename(
    kind: str,
    *,
    extension: str = "png",
    timestamp: datetime | None = None,
) -> str:
    moment = timestamp or datetime.now()
    if not isinstance(moment, datetime):
        raise TypeError("timestamp precisa ser datetime")
    suffix = sanitize_capture_name(extension).lstrip("._") or "png"
    label = sanitize_capture_name(kind)
    return f"hen-Nave_{label}_{moment:%Y%m%d_%H%M%S}.{suffix}"


def capture_bounds(
    document_width: int,
    document_height: int,
    max_width: int,
    max_height: int,
) -> tuple[int, int, bool]:
    dimensions = (document_width, document_height, max_width, max_height)
    if any(int(value) <= 0 for value in dimensions):
        raise ValueError("As dimensões da captura precisam ser positivas.")
    width = min(int(document_width), int(max_width))
    height = min(int(document_height), int(max_height))
    clipped = width < int(document_width) or height < int(document_height)
    return width, height, clipped


def _axis_positions(content_size: int, viewport_size: int) -> tuple[int, ...]:
    if content_size <= 0 or viewport_size <= 0:
        raise ValueError("As dimensões da fatia precisam ser positivas.")
    return tuple(range(0, content_size, viewport_size))


def capture_slices(
    content_width: int,
    content_height: int,
    viewport_width: int,
    viewport_height: int,
) -> tuple[tuple[int, int], ...]:
    """Retorna posições de rolagem em grade, linha por linha."""
    xs = _axis_positions(content_width, viewport_width)
    ys = _axis_positions(content_height, viewport_height)
    return tuple((x, y) for y in ys for x in xs)
