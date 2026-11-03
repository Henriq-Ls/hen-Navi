"""Parser e casamento de domínios para a lista simples do bloqueador."""

from __future__ import annotations

import ipaddress
import re
from pathlib import Path
from threading import Lock

from site_utils import extract_host, extract_site_host, normalize_host


BUILTIN_BLOCKLIST = """\
0.0.0.0 doubleclick.net
0.0.0.0 googlesyndication.com
0.0.0.0 googleadservices.com
0.0.0.0 adnxs.com
0.0.0.0 adsrvr.org
0.0.0.0 scorecardresearch.com
"""

_ADBLOCK_DOMAIN_RE = re.compile(r"^\|\|([^|^/$*?]+)\^?$")


def _is_blockable_domain(value: str) -> str:
    domain = normalize_host(value)
    if not domain or domain == "localhost":
        return ""
    try:
        ipaddress.ip_address(domain)
        return ""
    except ValueError:
        return domain


def parse_blocklist(text: str) -> frozenset[str]:
    """
    Lê entradas de hosts e regras simples `||dominio^`.

    Sintaxe avançada do Adblock Plus, exceções e filtros cosméticos são
    intencionalmente ignorados.
    """
    domains: set[str] = set()
    for original_line in (text or "").splitlines():
        line = original_line.strip()
        if not line or line.startswith(("#", "!", "[")):
            continue

        if line.startswith("||"):
            match = _ADBLOCK_DOMAIN_RE.fullmatch(line)
            if match:
                domain = _is_blockable_domain(match.group(1))
                if domain:
                    domains.add(domain)
            continue

        fields = line.split()
        if len(fields) >= 2:
            try:
                ipaddress.ip_address(fields[0])
            except ValueError:
                continue
            candidates = fields[1:]
        elif len(fields) == 1:
            candidates = fields
        else:
            continue

        for candidate in candidates:
            domain = _is_blockable_domain(candidate)
            if domain:
                domains.add(domain)
    return frozenset(domains)


class BlocklistFile:
    """Arquivo de regras guardado na pasta de configuração do AppData."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def ensure(self) -> frozenset[str]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(BUILTIN_BLOCKLIST, encoding="utf-8")
        return self.load()

    def load(self) -> frozenset[str]:
        return parse_blocklist(self.path.read_text(encoding="utf-8-sig"))

    def replace(self, text: str) -> frozenset[str]:
        domains = parse_blocklist(text)
        if not domains:
            raise ValueError("A lista não contém domínios reconhecidos.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_name(self.path.name + ".tmp")
        try:
            temporary_path.write_text(text, encoding="utf-8")
            temporary_path.replace(self.path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()
        return domains


class BlocklistMatcher:
    """Snapshot de regras substituível com segurança durante requisições."""

    def __init__(self, domains=()):
        self._lock = Lock()
        self._domains = frozenset(
            domain for value in domains if (domain := _is_blockable_domain(value))
        )

    def replace(self, domains) -> None:
        clean = frozenset(
            domain for value in domains if (domain := _is_blockable_domain(value))
        )
        with self._lock:
            self._domains = clean

    def snapshot(self) -> frozenset[str]:
        with self._lock:
            return self._domains

    def matching_domain(self, request_url: str) -> str | None:
        host = extract_host(request_url)
        if not host:
            return None
        domains = self.snapshot()
        candidate = host
        while candidate:
            if candidate in domains:
                return candidate
            if "." not in candidate:
                break
            candidate = candidate.split(".", maxsplit=1)[1]
        return None

    def should_block(
        self,
        request_url: str,
        first_party_url: str,
        *,
        is_main_frame: bool,
        enabled: bool,
        exceptions=(),
    ) -> bool:
        if not enabled or is_main_frame:
            return False
        first_party_host = extract_site_host(first_party_url)
        if not first_party_host:
            return False
        exception_domains = frozenset(exceptions)
        candidate = first_party_host
        while candidate:
            if candidate in exception_domains:
                return False
            if "." not in candidate:
                break
            candidate = candidate.split(".", maxsplit=1)[1]
        return self.matching_domain(request_url) is not None
