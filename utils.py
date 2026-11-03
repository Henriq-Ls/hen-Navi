"""Validação e resolução do texto digitado na barra de endereço."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlencode, urlsplit

from _CONFIGURA_ import URL_BUSCA


_LABEL_DOMAIN_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.IGNORECASE)
_TLD_RE = re.compile(r"^(?:[a-z]{2,63}|xn--[a-z0-9-]{2,59})$", re.IGNORECASE)


def _valid_port(parsed) -> bool:
    try:
        return parsed.port is None or 1 <= parsed.port <= 65535
    except ValueError:
        return False


def _valid_host(host: str | None) -> tuple[bool, bool]:
    """Retorna (válido, é localhost/IP)."""
    if not host:
        return False, False

    candidate = host.rstrip(".")
    if not candidate:
        return False, False

    if candidate.lower() == "localhost":
        return True, True

    try:
        ipaddress.ip_address(candidate)
        return True, True
    except ValueError:
        pass

    try:
        ascii_host = candidate.encode("idna").decode("ascii").lower()
    except UnicodeError:
        return False, False

    labels = ascii_host.split(".")
    if len(labels) < 2 or any(not _LABEL_DOMAIN_RE.fullmatch(label) for label in labels):
        return False, False
    if not _TLD_RE.fullmatch(labels[-1]):
        return False, False
    return True, False


def is_http_url(value: str) -> bool:
    """Aceita somente URLs HTTP(S) com host e porta válidos."""
    try:
        parsed = urlsplit(value.strip())
    except (TypeError, ValueError):
        return False
    if parsed.scheme.lower() not in {"http", "https"} or not _valid_port(parsed):
        return False
    valid, _ = _valid_host(parsed.hostname)
    return valid


def search_url(query: str) -> str:
    """Cria uma busca DuckDuckGo com a consulta corretamente codificada."""
    return f"{URL_BUSCA}?{urlencode({'q': query.strip()})}"


def resolve_address(text: str) -> str:
    """
    Converte texto em URL HTTP(S) ou em busca.

    Esquemas digitados que não sejam HTTP(S), incluindo javascript:, nunca
    são executados: o texto inteiro vira uma pesquisa.
    """
    value = (text or "").strip()
    if not value:
        return ""

    try:
        parsed = urlsplit(value)
    except ValueError:
        return search_url(value)

    explicit_scheme = re.match(r"^[a-z][a-z0-9+.-]*://", value, re.IGNORECASE)
    if explicit_scheme:
        if parsed.scheme.lower() in {"http", "https"} and is_http_url(value):
            return value
        return search_url(value)

    if any(character.isspace() for character in value):
        return search_url(value)

    try:
        candidate = urlsplit(f"//{value}")
    except ValueError:
        return search_url(value)

    valid, is_local = _valid_host(candidate.hostname)
    if candidate.username is not None or not valid or not _valid_port(candidate):
        return search_url(value)

    scheme = "http" if is_local else "https"
    return f"{scheme}://{value}"
