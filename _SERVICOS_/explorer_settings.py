"""Persistência local da lista de nomes ignorados pelo Explorador."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable


class ExplorerSettingsError(RuntimeError):
    """Erro seguro para apresentar ao usuário sem expor caminhos."""


def validate_ignored_names(names: Iterable[str]) -> tuple[str, ...]:
    result = []
    seen = set()
    for value in names:
        if not isinstance(value, str):
            raise ExplorerSettingsError("A lista de ignorados contém um valor inválido.")
        name = value.strip()
        if (
            not name
            or name in {".", ".."}
            or "/" in name
            or "\\" in name
            or "\x00" in name
            or "*" in name
            or "?" in name
        ):
            raise ExplorerSettingsError(
                "Cada item ignorado precisa ser um nome de pasta ou arquivo."
            )
        key = os.path.normcase(name)
        if key not in seen:
            seen.add(key)
            result.append(name)
    return tuple(result)


class ExplorerSettingsStore:
    """Guarda nomes ignorados em arquivo local de configurações do app."""

    def __init__(self, config_directory: str | os.PathLike[str], defaults):
        self.directory = Path(config_directory)
        self.path = self.directory / "explorer_ignored_names.json"
        self.defaults = validate_ignored_names(defaults)

    def load_ignored_names(self) -> tuple[str, ...]:
        if not self.path.exists():
            return self.defaults
        try:
            with self.path.open("r", encoding="utf-8") as stream:
                data = json.load(stream)
        except (OSError, UnicodeError, json.JSONDecodeError):
            raise ExplorerSettingsError(
                "Não foi possível ler os nomes ignorados do Explorador."
            ) from None
        if not isinstance(data, dict) or not isinstance(data.get("names"), list):
            raise ExplorerSettingsError(
                "A lista salva de nomes ignorados tem um formato inválido."
            )
        return validate_ignored_names(data["names"])

    def save_ignored_names(self, names: Iterable[str]) -> tuple[str, ...]:
        normalized = validate_ignored_names(names)
        temporary = self.path.with_suffix(".json.tmp")
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            with temporary.open("w", encoding="utf-8") as stream:
                json.dump(
                    {"version": 1, "names": list(normalized)},
                    stream,
                    indent=2,
                    ensure_ascii=False,
                )
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        except OSError:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise ExplorerSettingsError(
                "Não foi possível salvar os nomes ignorados."
            ) from None
        return normalized
