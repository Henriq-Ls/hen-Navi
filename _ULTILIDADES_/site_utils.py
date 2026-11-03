"""Normalização de hosts usados pelo bloqueador e pelas anotações por site."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit


_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.IGNORECASE)


def normalize_host(value: str | None, *, strip_www: bool = False) -> str:
    """Normaliza um hostname, preservando IPs e recusando entradas malformadas."""
    if not value:
        return ""
    host = value.strip().rstrip(".").lower()
    if not host or any(character.isspace() for character in host):
        return ""

    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    try:
        return ipaddress.ip_address(host).compressed.lower()
    except ValueError:
        pass

    if ":" in host or "/" in host or "@" in host:
        return ""
    try:
        host = host.encode("idna").decode("ascii").lower()
    except UnicodeError:
        return ""

    labels = host.split(".")
    if host != "localhost" and (
        len(labels) < 2 or any(not _LABEL_RE.fullmatch(label) for label in labels)
    ):
        return ""
    if host == "localhost":
        return host
    if strip_www and host.startswith("www."):
        host = host[4:]
    return host


def extract_site_host(url: str) -> str:
    """Extrai o host de uma URL HTTP(S), removendo o prefixo www."""
    return extract_host(url, strip_www=True)


def extract_host(url: str, *, strip_www: bool = False) -> str:
    """Extrai o hostname de uma URL HTTP(S), opcionalmente mantendo www."""
    try:
        parsed = urlsplit((url or "").strip())
        if parsed.scheme.lower() not in {"http", "https"}:
            return ""
        return normalize_host(parsed.hostname, strip_www=strip_www)
    except (TypeError, ValueError):
        return ""


def is_valid_https_url(value: str) -> bool:
    """Valida URL HTTPS sem credenciais para a atualização opcional da lista."""
    try:
        parsed = urlsplit((value or "").strip())
        return bool(
            parsed.scheme.lower() == "https"
            and normalize_host(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
            and (parsed.port is None or 1 <= parsed.port <= 65535)
        )
    except (TypeError, ValueError):
        return False


def domain_matches(host: str, domain: str) -> bool:
    """Retorna se host é o domínio ou um subdomínio dele, sem falsos sufixos."""
    candidate = normalize_host(host)
    rule = normalize_host(domain)
    return bool(candidate and rule and (candidate == rule or candidate.endswith("." + rule)))
