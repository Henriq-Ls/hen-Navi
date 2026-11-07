"""Análises locais e limitadas de endereços e cabeçalhos HTTP."""

from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit


def analyze_url_safety(url: str) -> dict[str, object]:
    """Aponta sinais simples no endereço sem consultar serviços externos."""
    try:
        parsed = urlsplit(str(url or "").strip())
        scheme = parsed.scheme.lower()
        host = (parsed.hostname or "").rstrip(".").lower()
        has_user_info = parsed.username is not None or parsed.password is not None
    except (TypeError, ValueError):
        return {
            "host": "",
            "findings": ["O endereço não pôde ser interpretado."],
        }

    findings: list[str] = []
    if scheme not in {"http", "https"}:
        findings.append("O endereço não usa HTTP ou HTTPS.")
    elif scheme == "http":
        findings.append(
            "A conexão usa HTTP sem criptografia; evite enviar informações."
        )

    if not host:
        findings.append("O endereço não contém um domínio válido.")
    if has_user_info:
        findings.append(
            "O endereço contém usuário ou senha antes do domínio."
        )
    if "xn--" in host:
        findings.append(
            "O domínio usa caracteres internacionais em formato punycode; "
            "confira se você reconhece o nome."
        )

    try:
        ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        pass
    else:
        findings.append(
            "O endereço usa um IP diretamente, em vez de um nome de domínio."
        )

    if host and len(host.split(".")) >= 5:
        findings.append(
            "O endereço tem vários subdomínios; confira qual é o domínio principal."
        )

    if not findings:
        findings.append(
            "Nenhum sinal simples foi encontrado no endereço. Isso não garante "
            "que o site seja confiável."
        )

    return {"host": host, "findings": findings}


_SECURITY_HEADERS = (
    ("strict-transport-security", "HSTS"),
    ("content-security-policy", "Content-Security-Policy"),
    ("x-content-type-options", "X-Content-Type-Options"),
    ("referrer-policy", "Referrer-Policy"),
    ("permissions-policy", "Permissions-Policy"),
)


def inspect_security_headers(headers) -> list[dict[str, object]]:
    """Resume cabeçalhos conhecidos sem tratar ausência como prova de falha."""
    normalized: dict[str, str] = {}
    for name, value in headers:
        if isinstance(name, bytes):
            name = name.decode("latin-1", errors="replace")
        if isinstance(value, bytes):
            value = value.decode("latin-1", errors="replace")
        normalized[str(name).strip().lower()] = str(value).strip()

    content_security_policy = normalized.get("content-security-policy", "")
    has_frame_policy = bool(
        "frame-ancestors" in content_security_policy.lower()
        or normalized.get("x-frame-options")
    )
    results = [
        {
            "name": label,
            "present": bool(normalized.get(header_name)),
        }
        for header_name, label in _SECURITY_HEADERS
    ]
    results.append(
        {
            "name": "Proteção contra incorporação em frames",
            "present": has_frame_policy,
        }
    )
    return results
