"""Arquivos temporários e limpeza de páginas iniciais anônimas."""

from __future__ import annotations

import getpass
import hashlib
import os
import tempfile
from pathlib import Path


_TEMP_PREFIX = "hen-nave-anon-"


def _private_directory() -> Path:
    if hasattr(os, "getuid"):
        identity = str(os.getuid())
    else:
        identity = getpass.getuser().casefold()
    token = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
    directory = Path(tempfile.gettempdir()) / f"{_TEMP_PREFIX}{token}"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        directory.chmod(0o700)
    except OSError:
        pass
    return directory


def cleanup_private_start_pages(legacy_path: str | Path | None = None) -> None:
    """Apaga páginas temporárias que sobraram de execuções anteriores."""
    directory = _private_directory()
    for path in directory.glob("*.html"):
        try:
            path.unlink()
        except OSError as error:
            _log_cleanup_error(path, error)

    if legacy_path:
        legacy = Path(legacy_path)
        if legacy.is_file():
            try:
                legacy.unlink()
            except OSError as error:
                _log_cleanup_error(legacy, error)


def create_private_start_page(html: str) -> str:
    """Cria uma página HTML anônima com permissão restrita no diretório temp."""
    directory = _private_directory()
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix="inicio-",
        suffix=".html",
        dir=directory,
        delete=False,
    ) as temporary_file:
        temporary_file.write(html)
        return temporary_file.name


def write_private_start_page(path: str | Path, html: str) -> None:
    Path(path).write_text(html, encoding="utf-8")


def remove_private_start_page(path: str | Path | None) -> None:
    if not path:
        return
    try:
        Path(path).unlink(missing_ok=True)
    except OSError as error:
        _log_cleanup_error(Path(path), error)


def _log_cleanup_error(path: Path, error: OSError) -> None:
    from _LOGS_ import log

    log.aviso(
        "PaginaAnonima",
        "limpar",
        f"não foi possível remover arquivo temporário {path.name}: {error}",
    )
