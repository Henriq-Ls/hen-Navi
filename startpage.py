"""Geração segura da página inicial HTML do hen-Nave."""

from __future__ import annotations

import html
from urllib.parse import urlsplit

from _CONFIGURA_ import (
    CORES_DOMINIO,
    CSS_PAGINA_INICIAL,
    ESQUEMA_INTERNO,
    TEXTO_AVISO_ANONIMO,
)
from utils import is_http_url


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
    color = CORES_DOMINIO[index % len(CORES_DOMINIO)]
    initial = html.escape((domain[:1] or "?").upper())
    safe_title = html.escape(title, quote=True)
    safe_domain = html.escape(domain, quote=True)
    safe_url = html.escape(url, quote=True)
    return (
        f'<a class="card" href="{safe_url}">'
        f'<span class="letter" style="background:{color}">{initial}</span>'
        f'<span class="card-copy"><span class="name">{safe_title}</span>'
        f'<span class="domain">{safe_domain}</span></span></a>'
    )


def generate_start_page(
    favorites: list[dict] | None = None,
    recent: list[dict] | None = None,
    *,
    private: bool = False,
) -> str:
    """Monta uma página sem scripts nem conteúdo externo, escapando dados dinâmicos."""
    safe_favorites = _safe_items(favorites or [])
    safe_recent = [] if private else _safe_items(recent or [])
    favorite_cards = "".join(_card(item, index) for index, item in enumerate(safe_favorites))
    recent_cards = "".join(_card(item, index + 3) for index, item in enumerate(safe_recent))

    favorite_section = (
        f'<div class="grid">{favorite_cards}</div>'
        if favorite_cards
        else '<div class="empty">Seus favoritos aparecerão aqui.</div>'
    )
    recent_section = (
        f'<div class="grid">{recent_cards}</div>'
        if recent_cards
        else '<div class="empty">As páginas que você visitar aparecerão aqui.</div>'
    )
    private_notice = (
        f'<aside class="private-notice"><strong>Navegação anônima</strong>'
        f'{html.escape(TEXTO_AVISO_ANONIMO)}</aside>'
        if private
        else ""
    )

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>hen-Nave — Início</title>
  <style>{CSS_PAGINA_INICIAL}</style>
</head>
<body>
  <main>
    <header class="brand">
      <div class="brand-mark" aria-hidden="true">h</div>
      <h1>hen-Nave</h1>
      <p class="subtitle">O que você quer descobrir hoje?</p>
    </header>
    <form class="search" action="{ESQUEMA_INTERNO}://search" method="get">
      <input type="search" name="q" placeholder="Pesquisar ou digitar um endereço"
             aria-label="Pesquisar ou digitar um endereço" autofocus>
      <button type="submit">Pesquisar</button>
    </form>
    {private_notice}
    <section aria-labelledby="favorites-heading">
      <h2 class="section-title" id="favorites-heading">Favoritos</h2>
      {favorite_section}
    </section>
    <section aria-labelledby="recent-heading">
      <h2 class="section-title" id="recent-heading">Visitados recentemente</h2>
      {recent_section}
    </section>
    <footer>hen-Nave · Navegação simples e local</footer>
  </main>
</body>
</html>
"""
