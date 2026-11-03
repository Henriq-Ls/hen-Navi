# _ULTILIDADES_/icones.py
"""
Centraliza todos os ícones do projeto.

Usa qtawesome como fonte principal.
Se qtawesome não estiver instalado, retorna QIcon vazio silenciosamente.

Uso:
    from _ULTILIDADES_.icones import icone, icone_colorido

    btn.setIcon(icone("fa5s.folder-open"))
    btn.setIcon(icone_colorido("fa5s.save", "#3a7bd5"))

Referência de ícones: https://fontawesome.com/icons (prefixo fa5s, fa5r, fa5b, mdi, ei)
"""

from PySide6.QtGui import QIcon, QColor
from PySide6.QtWidgets import QApplication
from _CONFIGURA_ import (
    AMARELO,
    COR_FAVORITO,
    COR_FAVORITO_VAZIO,
    COR_TEXTO,
    COR_ACENTO,
    COR_PERIGO,
    COR_SUCESSO,
)
from _CONFIGURA_.temas import TEMAS


_COR_POR_TEMA = {
    COR_TEXTO: "icon",
    COR_ACENTO: "accent",
    COR_PERIGO: "danger",
    COR_SUCESSO: "success",
    AMARELO: "accent",
    "#FFC107": "accent",
}


def _cor_ativa(cor: str) -> str:
    app = QApplication.instance()
    if app is None:
        return cor
    theme_key = _COR_POR_TEMA.get(cor, "")
    configured_color = app.property(f"henNaveTheme_{theme_key}") if theme_key else None
    if isinstance(configured_color, str) and configured_color:
        return configured_color
    theme_id = app.property("henNaveTheme")
    theme = TEMAS.get(str(theme_id), {})
    return theme.get(theme_key, cor)


def icone(nome: str, cor: str = COR_TEXTO) -> QIcon:
    """
    Retorna um QIcon do qtawesome.
    Se qtawesome não estiver disponível, retorna QIcon vazio.

    Args:
        nome: nome do ícone (ex: "fa5s.folder-open", "mdi.content-save")
        cor:  cor hexadecimal (padrão: COR_TEXTO do _CONFIGURA_)
    """
    try:
        import qtawesome as qta
        return qta.icon(nome, color=_cor_ativa(cor))
    except Exception:
        return QIcon()


def icone_colorido(nome: str, cor: str) -> QIcon:
    """Ícone com cor específica."""
    return icone(nome, cor)


# ── Ícones pré-definidos (expanda conforme o projeto) ────────────────────────
# Importe estes em vez de escrever strings de ícone espalhadas pelo código.

def ico_salvar()    -> QIcon: return icone("fa5s.save",         COR_ACENTO)
def ico_abrir()     -> QIcon: return icone("fa5s.folder-open",  COR_ACENTO)
def ico_novo()      -> QIcon: return icone("fa5s.file",         COR_ACENTO)
def ico_fechar()    -> QIcon: return icone("fa5s.times",        COR_TEXTO)
def ico_config()    -> QIcon: return icone("fa5s.cog",          COR_TEXTO)
def ico_info()      -> QIcon: return icone("fa5s.info-circle",  COR_ACENTO)
def ico_aviso()     -> QIcon: return icone("fa5s.exclamation-triangle", "#FFC107")
def ico_erro()      -> QIcon: return icone("fa5s.times-circle", COR_PERIGO)
def ico_ok()        -> QIcon: return icone("fa5s.check-circle", COR_SUCESSO)
def ico_atualizar() -> QIcon: return icone("fa5s.sync-alt",     COR_TEXTO)
def ico_buscar()    -> QIcon: return icone("fa5s.search",       COR_TEXTO)
def ico_lixo()      -> QIcon: return icone("fa5s.trash-alt",    COR_PERIGO)
def ico_adicionar() -> QIcon: return icone("fa5s.plus",         COR_SUCESSO)


def ico_menu() -> QIcon: return icone("fa5s.bars", COR_TEXTO)
def ico_favorito_vazio() -> QIcon: return icone("fa5r.star", COR_FAVORITO_VAZIO)
def ico_ferramentas() -> QIcon: return icone("fa5s.tools", COR_TEXTO)
def ico_bloqueador() -> QIcon: return icone("fa5s.shield-alt", COR_TEXTO)
def ico_video_download() -> QIcon: return icone("fa5s.video", COR_TEXTO)
def ico_downloads() -> QIcon: return icone("fa5s.download", COR_TEXTO)
def ico_anotacoes() -> QIcon: return icone("fa5s.sticky-note", COR_TEXTO)
def ico_inspecionar() -> QIcon: return icone("fa5s.code", COR_TEXTO)
def ico_ia() -> QIcon: return icone("fa5s.brain", COR_TEXTO)
def ico_tema() -> QIcon: return icone("fa5s.palette", COR_TEXTO)
def ico_captura() -> QIcon: return icone("fa5s.camera", COR_TEXTO)
def ico_imagem() -> QIcon: return icone("fa5s.file-image", COR_TEXTO)
def ico_pdf() -> QIcon: return icone("fa5s.file-pdf", COR_TEXTO)


def ico_voltar() -> QIcon: return icone("fa5s.arrow-left", COR_TEXTO)
def ico_avancar() -> QIcon: return icone("fa5s.arrow-right", COR_TEXTO)
def ico_home() -> QIcon: return icone("fa5s.home", COR_TEXTO)
def ico_historico() -> QIcon: return icone("fa5s.history", COR_TEXTO)
def ico_favoritos() -> QIcon: return icone("fa5s.star", COR_TEXTO)
def ico_janela() -> QIcon: return icone("fa5s.window-maximize", COR_TEXTO)
def ico_janela_fechar() -> QIcon: return icone("fa5s.times", COR_TEXTO)
def ico_janela_maximizar() -> QIcon: return icone("fa5s.window-maximize", COR_TEXTO)
def ico_janela_restaurar() -> QIcon: return icone("fa5s.window-restore", COR_TEXTO)
def ico_janela_minimizar() -> QIcon: return icone("fa5s.window-minimize", COR_TEXTO)
def ico_anonimo() -> QIcon: return icone("fa5s.user-secret", COR_TEXTO)
def ico_localizar() -> QIcon: return icone("fa5s.search", COR_TEXTO)
def ico_zoom_mais() -> QIcon: return icone("fa5s.search-plus", COR_TEXTO)
def ico_zoom_menos() -> QIcon: return icone("fa5s.search-minus", COR_TEXTO)
def ico_zoom_redefinir() -> QIcon: return icone("fa5s.undo", COR_TEXTO)
def ico_limpar() -> QIcon: return icone("fa5s.trash-alt", COR_PERIGO)
def ico_nova_aba() -> QIcon: return icone("fa5s.plus", COR_SUCESSO)
def ico_fechar_aba() -> QIcon: return icone("fa5s.times", COR_TEXTO)
def ico_fechar_aba_hover() -> QIcon: return icone("fa5s.times", COR_PERIGO)
def ico_endereco() -> QIcon: return icone("fa5s.search-location", COR_TEXTO)
def ico_favorito() -> QIcon: return icone("fa5s.star", COR_FAVORITO)
def ico_atalhos() -> QIcon: return icone("fa5s.keyboard", COR_TEXTO)
