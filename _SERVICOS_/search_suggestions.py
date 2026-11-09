"""Fontes locais e URLs de autocomplete dos buscadores configurados."""

from __future__ import annotations

import json
import unicodedata
from urllib.parse import urlencode, urlsplit

from _ULTILIDADES_.utils import is_http_url


POPULAR_SITES = (
    ("Google", "https://www.google.com/"),
    ("Gmail", "https://mail.google.com/"),
    ("Pinterest", "https://www.pinterest.com/"),
    ("YouTube", "https://www.youtube.com/"),
    ("Instagram", "https://www.instagram.com/"),
    ("Facebook", "https://www.facebook.com/"),
    ("Wikipedia", "https://www.wikipedia.org/"),
    ("Amazon", "https://www.amazon.com/"),
    ("Netflix", "https://www.netflix.com/"),
    ("TikTok", "https://www.tiktok.com/"),
)

_SEARCH_SUGGESTION_ENDPOINTS = {
    "duckduckgo": (
        "https://duckduckgo.com/ac/",
        lambda query: {"q": query, "type": "list"},
    ),
    "google": (
        "https://suggestqueries.google.com/complete/search",
        lambda query: {"client": "firefox", "q": query},
    ),
    "bing": (
        "https://api.bing.com/osjson.aspx",
        lambda query: {"query": query},
    ),
}


def build_suggestion_url(query: str, search_engine: str) -> str:
    """Monta a consulta HTTPS do provedor selecionado."""
    value = (query or "").strip()[:160]
    try:
        endpoint, parameters = _SEARCH_SUGGESTION_ENDPOINTS[search_engine]
    except (KeyError, TypeError) as error:
        raise ValueError(f"Buscador desconhecido: {search_engine}") from error
    if len(value) < 2:
        return ""
    return f"{endpoint}?{urlencode(parameters(value))}"


def parse_search_suggestions(search_engine: str, payload: bytes | str) -> list[str]:
    """Normaliza os formatos de autocomplete dos três buscadores disponíveis."""
    try:
        text = payload.decode("utf-8") if isinstance(payload, bytes) else payload
        data = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
        return []

    if search_engine == "duckduckgo":
        candidates = (
            [item.get("phrase", "") for item in data if isinstance(item, dict)]
            if isinstance(data, list)
            else []
        )
    elif search_engine in {"google", "bing"}:
        candidates = (
            data[1]
            if isinstance(data, list) and len(data) > 1 and isinstance(data[1], list)
            else []
        )
    else:
        return []

    results = []
    seen = set()
    for candidate in candidates:
        if not isinstance(candidate, str):
            continue
        value = candidate.strip()
        key = value.casefold()
        if not value or key in seen:
            continue
        seen.add(key)
        results.append(value[:160])
        if len(results) >= 8:
            break
    return results


def _normalize_for_match(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).casefold()
    return "".join(
        character
        for character in normalized
        if character.isalnum()
    )


def _site_entry(title: object, url: object) -> dict[str, str] | None:
    address = str(url or "").strip()
    if not is_http_url(address):
        return None
    host = urlsplit(address).hostname or address
    label = str(title or "").strip() or host
    return {"title": label, "url": address, "host": host}


def _site_key(url: str) -> str:
    parsed = urlsplit(url)
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme.lower()}://{parsed.netloc.casefold()}{path}?{parsed.query}"


def collect_site_suggestions(
    query: str = "",
    favorites: list[dict] | None = None,
    recent: list[dict] | None = None,
) -> list[dict[str, str]]:
    """Combina sites conhecidos, favoritos e páginas recentes sem duplicar hosts."""
    entries: dict[str, dict[str, str]] = {}
    for title, url in POPULAR_SITES:
        entry = _site_entry(title, url)
        if entry:
            entries[_site_key(entry["url"])] = entry

    for item in favorites or []:
        if not isinstance(item, dict):
            continue
        entry = _site_entry(item.get("title"), item.get("url"))
        if entry:
            entries[_site_key(entry["url"])] = entry

    for item in recent or []:
        if not isinstance(item, dict):
            continue
        entry = _site_entry(item.get("title"), item.get("url"))
        if entry:
            entries.setdefault(_site_key(entry["url"]), entry)

    needle = _normalize_for_match(query)
    if not needle:
        return list(entries.values())
    return [
        entry
        for entry in entries.values()
        if needle in _normalize_for_match(entry["title"])
        or needle in _normalize_for_match(entry["host"])
    ]
