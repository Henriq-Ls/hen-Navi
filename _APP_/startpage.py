"""Geração segura da página inicial HTML do hen-Nave."""

from __future__ import annotations

import base64
import html
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from _CONFIGURA_ import (
    CORES_DOMINIO,
    CSS_PAGINA_INICIAL,
    IDIOMA_UI,
    LOGO_SIMB,
    TEMA_PADRAO,
    TEXTO_AVISO_ANONIMO,
    TEXTO_UI,
)
from _CONFIGURA_.theme_engine import startpage_theme_css
from _ULTILIDADES_.utils import is_http_url


@lru_cache(maxsize=1)
def _logo_data_uri() -> str:
    try:
        encoded_logo = base64.b64encode(Path(LOGO_SIMB).read_bytes()).decode("ascii")
    except OSError:
        return ""
    return f"data:image/png;base64,{encoded_logo}"


def _domain_for(url: str) -> str:
    try:
        return urlsplit(url).hostname or url
    except ValueError:
        return url


def _safe_items(items: list[dict], limit: int | None = None) -> list[dict]:
    result: list[dict] = []
    seen: set[str] = set()
    for item in items:
        url = str(item.get("url", ""))
        if not is_http_url(url) or url in seen:
            continue
        seen.add(url)
        result.append(item)
        if limit is not None and len(result) >= limit:
            break
    return result


def _card(item: dict, index: int) -> str:
    url = str(item["url"])
    domain = _domain_for(url)
    title = str(item.get("title") or domain)
    color_index = sum(ord(character) for character in domain.lower()) % len(CORES_DOMINIO)
    color = CORES_DOMINIO[color_index]
    display_domain = domain[4:] if domain.lower().startswith("www.") else domain
    initial = html.escape((display_domain[:1] or "?").upper())
    safe_title = html.escape(title, quote=True)
    safe_domain = html.escape(domain, quote=True)
    safe_url = html.escape(url, quote=True)
    favicon = _safe_favicon(item.get("favicon"))
    badge_content = (
        f'<img class="favicon" src="{html.escape(favicon, quote=True)}" alt="">'
        if favicon
        else initial
    )
    return (
        f'<a class="card" href="{safe_url}" target="_blank" rel="noopener noreferrer">'
        f'<span class="letter" style="background:{color}">{badge_content}</span>'
        f'<span class="card-copy"><span class="name">{safe_title}</span>'
        f'<span class="domain">{safe_domain}</span></span></a>'
    )


def _safe_favicon(value: object) -> str:
    prefix = "data:image/png;base64,"
    if not isinstance(value, str) or not value.startswith(prefix):
        return ""
    encoded = value[len(prefix):]
    if not encoded or len(encoded) > 350_000:
        return ""
    try:
        image_bytes = base64.b64decode(encoded, validate=True)
    except (ValueError, base64.binascii.Error):
        return ""
    if (
        len(image_bytes) > 256_000
        or not image_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    ):
        return ""
    return value


def generate_start_page(
    favorites: list[dict] | None = None,
    recent: list[dict] | None = None,
    *,
    private: bool = False,
    theme_id: str = TEMA_PADRAO,
    custom_theme: dict | None = None,
) -> str:
    """Monta uma página sem scripts nem conteúdo externo, escapando dados dinâmicos."""
    safe_favorites = _safe_items(favorites or [])
    safe_recent = [] if private else _safe_items(recent or [])
    favorite_cards = "".join(_card(item, index) for index, item in enumerate(safe_favorites))
    recent_cards = "".join(_card(item, index + 3) for index, item in enumerate(safe_recent))

    favorite_section = (
        f'<div class="grid">{favorite_cards}</div>'
        if favorite_cards
        else f'<div class="empty">{html.escape(TEXTO_UI["favorites_empty"])}</div>'
    )
    recent_section = (
        f'<div class="grid">{recent_cards}</div>'
        if recent_cards
        else f'<div class="empty">{html.escape(TEXTO_UI["recent_empty"])}</div>'
    )
    private_notice = (
        f'<aside class="private-notice"><strong>{html.escape(TEXTO_UI["private_heading"])}</strong>'
        f'{html.escape(TEXTO_AVISO_ANONIMO)}</aside>'
        if private
        else ""
    )
    logo_data_uri = _logo_data_uri()
    brand_mark = (
        f'<img class="brand-logo" src="{html.escape(logo_data_uri, quote=True)}" alt="">'
        if logo_data_uri
        else (
            f'<div class="brand-mark" aria-hidden="true">'
            f'{html.escape(TEXTO_UI["brand_initial"])}</div>'
        )
    )

    return f"""<!doctype html>
<html lang="{html.escape(IDIOMA_UI, quote=True)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(TEXTO_UI["home_title"], quote=True)}</title>
  <style>{CSS_PAGINA_INICIAL}{startpage_theme_css(theme_id, custom_theme=custom_theme)}</style>
</head>
<body>
  <main>
    <header class="brand">
      {brand_mark}
      <h1>{html.escape(TEXTO_UI["browser_name"])}</h1>
      <p class="subtitle">{html.escape(TEXTO_UI["home_subtitle"])}</p>
    </header>
    <form class="search" method="get">
      <input type="search" name="q" placeholder="{html.escape(TEXTO_UI["home_search_placeholder"], quote=True)}"
             aria-label="{html.escape(TEXTO_UI["home_search_placeholder"], quote=True)}" autofocus>
      <button type="submit">{html.escape(TEXTO_UI["search"])}</button>
    </form>
    {private_notice}
    <section aria-labelledby="favorites-heading">
      <h2 class="section-title" id="favorites-heading">{html.escape(TEXTO_UI["favorites"])}</h2>
      {favorite_section}
    </section>
    <section aria-labelledby="recent-heading">
      <h2 class="section-title" id="recent-heading">{html.escape(TEXTO_UI["recent"])}</h2>
      {recent_section}
    </section>
    <footer>{html.escape(TEXTO_UI["home_footer"])}</footer>
  </main>
</body>
</html>
"""
