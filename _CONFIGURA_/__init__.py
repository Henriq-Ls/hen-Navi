# _CONFIGURA_/__init__.py
"""
Fonte única de verdade para TODOS os valores fixos do projeto.
Nenhum outro arquivo pode ter cores, atalhos, tamanhos ou qualquer
valor fixo — tudo vem daqui.

SEÇÕES:
    APPDATA
    APLICAÇÃO
    FONTES
    JANELA PRINCIPAL
    ATALHOS
    CORES — paleta base
    CORES — UI escuro
    ESTILOS QSS prontos
"""

import os

# ══════════════════════════════════════════════════════════════════════════════
# MODO DE EXECUÇÃO
# ══════════════════════════════════════════════════════════════════════════════
# True  → desenvolvimento: log em nível DEBUG, erros detalhados
# False → produção: log em nível ERROR apenas, sem stack traces no terminal
MODO_DEV = True

# ══════════════════════════════════════════════════════════════════════════════
# APPDATA — pasta do usuário no sistema operacional
# ══════════════════════════════════════════════════════════════════════════════
# Windows: %APPDATA%\nome_do_projeto
# Linux/Mac: ~/nome_do_projeto
PASTA_APPDATA = os.path.join(
    os.path.expanduser("~"),
    ".hen-nave"
)

# ══════════════════════════════════════════════════════════════════════════════
# APLICAÇÃO
# ══════════════════════════════════════════════════════════════════════════════
VERSAO_APP  = "v0.1.0"
TITULO_APP  = "hen-Nave"
TEMA_QT     = "Fusion"             # tema base do Qt

# Caminhos absolutos — independentes do CWD de execução
_PROJETO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGEM_ICO   = os.path.join(_PROJETO_DIR, "IMAGENS", "icon.ico")
LOGO_MARCA   = os.path.join(_PROJETO_DIR, "IMAGENS", "logo_nome.png")
LOGO_SIMB    = os.path.join(_PROJETO_DIR, "IMAGENS", "logo.png")

# ══════════════════════════════════════════════════════════════════════════════
# FONTES
# ══════════════════════════════════════════════════════════════════════════════
FONTE_NOME_UI       = "Segoe UI"
FONTE_TAMANHO_BASE  = 10     # pontos — fonte padrão da QApplication

FONTE_TAMANHO_TITULO  = 13   # px (CSS/QSS)
FONTE_TAMANHO_INFO    = 12
FONTE_TAMANHO_LABEL   = 11
FONTE_TAMANHO_DETALHE = 10
FONTE_TAMANHO_SUTIL   = 9

# ══════════════════════════════════════════════════════════════════════════════
# JANELA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
LARGURA_PADRAO = 1280
ALTURA_PADRAO  = 800
LARGURA_MIN    = 1024
ALTURA_MIN     = 600

# ══════════════════════════════════════════════════════════════════════════════
# ATALHOS
# ══════════════════════════════════════════════════════════════════════════════
ATALHO_SAIR              = "Alt+F4"
ATALHO_SALVAR            = "Ctrl+S"
ATALHO_ABRIR             = "Ctrl+O"
ATALHO_NOVO               = "Ctrl+N"
ATALHO_NOVA_ABA           = "Ctrl+T"
ATALHO_FECHAR_ABA         = "Ctrl+W"
ATALHO_ENDERECO           = "Ctrl+L"
ATALHO_HISTORICO          = "Ctrl+H"
ATALHO_FAVORITOS          = "Ctrl+Shift+O"
ATALHO_NOVA_JANELA        = "Ctrl+N"
ATALHO_JANELA_ANONIMA     = "Ctrl+Shift+N"
ATALHO_HOME               = "Alt+Home"
ATALHO_FAVORITO           = "Ctrl+D"
ATALHO_LOCALIZAR          = "Ctrl+F"
ATALHO_ZOOM_MAIS          = "Ctrl+="
ATALHO_ZOOM_MENOS         = "Ctrl+-"
ATALHO_ZOOM_RESET         = "Ctrl+0"
ATALHO_RECARREGAR         = "F5"

# ══════════════════════════════════════════════════════════════════════════════
# HEN-NAVE — valores de produto e navegação
# ══════════════════════════════════════════════════════════════════════════════
ESQUEMA_INTERNO = "hennave"
URL_BUSCA = "https://duckduckgo.com/"
ARQUIVO_INICIO = "hen-nave-inicio.html"
ARQUIVO_INICIO_ANONIMO = "hen-nave-inicio-anonimo.html"
ARQUIVO_BANCO = "hen-nave.sqlite3"
ARQUIVO_LOCK = "hen-nave.lock"
NOME_PERFIL_WEB = "hen-nave"
SEGUNDOS_DEDUP_HISTORICO = 5
LIMITE_RECENTES_INICIO = 8
LIMITE_HISTORICO_DIALOGO = 1000
STATUS_CURTO_MS = 3000
STATUS_DOWNLOAD_INICIO_MS = 5000
STATUS_CARREGAMENTO_MS = 3500
STATUS_DOWNLOAD_MS = 8000
ZOOM_INICIAL = 1.0
ZOOM_MINIMO = 0.5
ZOOM_MAXIMO = 3.0
ZOOM_INCREMENTO = 1.15
LARGURA_ENDERECO_MINIMA = 280
ALTURA_BARRA_ENDERECO = 36
LARGURA_DIALOGO_PADRAO = 760
ALTURA_DIALOGO_PADRAO = 540
COR_INCOGNITO = "#a78bfa"
COR_INCOGNITO_ESCURA = "#30234c"
COR_INICIO_FUNDO = "#111318"
COR_INICIO_CARTAO = "#1a1d25"
COR_INICIO_CARTAO_HOVER = "#232733"
COR_INICIO_CAMPO = "#20232c"
COR_INICIO_BORDA = "#303541"
COR_INICIO_TEXTO = "#f2f4f8"
COR_INICIO_SECUNDARIA = "#9ba3b4"
COR_INICIO_LINK = "#8db5ff"
CORES_DOMINIO = (
    "#ef6a6a", "#e6a44b", "#56b889", "#4fa8d8",
    "#8c7be8", "#d26ca7", "#6db6a4", "#c0a652",
)
TEXTO_AVISO_ANONIMO = (
    "A navegação anônima não esconde sua atividade dos sites ou do provedor "
    "de internet. Ela apenas evita salvar histórico, cookies e dados desta "
    "sessão neste computador."
)

def _estilo_navegador_extra():
    return f"""
QLineEdit#addressBar {{
    background: {COR_BG_CAMPO};
    color: {COR_TEXTO};
    border: 1px solid {COR_BORDA_CLARA};
    border-radius: 18px;
    padding: 5px 13px;
    min-height: {ALTURA_BARRA_ENDERECO}px;
    selection-background-color: {COR_ACENTO};
}}
QLineEdit#addressBar:focus {{ border-color: {COR_ACENTO_BORDA}; }}
QTabWidget::pane {{ border: 1px solid {COR_BORDA}; }}
QTabBar::tab {{
    background: {COR_BG_SECUNDARIO};
    color: {COR_TEXTO_SECUNDARIO};
    padding: 8px 14px;
    border: 1px solid {COR_BORDA};
    min-width: 100px;
}}
QTabBar::tab:selected {{
    background: {COR_BG_APP};
    color: {COR_TEXTO};
    border-bottom: 2px solid {COR_ACENTO};
}}
QTabBar::tab:hover {{ background: {COR_BG_TERCIARIO}; }}
QToolButton#favoriteButton {{ color: {AMARELO}; font-size: 16px; }}
QWidget#findBar {{
    background: {COR_BG_SECUNDARIO};
    border-top: 1px solid {COR_BORDA};
    padding: 4px;
}}
QPushButton {{ padding: 5px 9px; }}
"""

def _estilo_navegador_anonimo():
    return f"""
QMainWindow[privateMode="true"] QToolBar {{
    border-bottom: 2px solid {COR_INCOGNITO};
}}
QMainWindow[privateMode="true"] QTabBar::tab:selected {{
    border-bottom: 2px solid {COR_INCOGNITO};
}}
QMainWindow[privateMode="true"] QLineEdit#addressBar:focus {{
    border-color: {COR_INCOGNITO};
}}
QMainWindow[privateMode="true"] QToolButton#privateIndicator {{
    color: {COR_INCOGNITO};
    background: {COR_INCOGNITO_ESCURA};
    border-radius: 8px;
}}
"""

def _css_pagina_inicial():
    return f"""
:root {{
    color-scheme: dark;
    --bg: {COR_INICIO_FUNDO};
    --card: {COR_INICIO_CARTAO};
    --card-hover: {COR_INICIO_CARTAO_HOVER};
    --field: {COR_INICIO_CAMPO};
    --border: {COR_INICIO_BORDA};
    --text: {COR_INICIO_TEXTO};
    --muted: {COR_INICIO_SECUNDARIA};
    --link: {COR_INICIO_LINK};
    --accent: {COR_ACENTO};
    --private: {COR_INCOGNITO};
}}
* {{ box-sizing: border-box; }}
body {{
    margin: 0;
    min-height: 100vh;
    background: var(--bg);
    color: var(--text);
    font-family: "Segoe UI", Arial, sans-serif;
}}
main {{ width: min(920px, calc(100% - 48px)); margin: 0 auto; padding: 72px 0 64px; }}
.brand {{ text-align: center; margin-bottom: 30px; }}
.brand-mark {{
    width: 52px; height: 52px; margin: 0 auto 15px; border-radius: 17px;
    display: grid; place-items: center; color: white; font-weight: 800;
    font-size: 26px; background: linear-gradient(135deg, var(--accent), #63d7ce);
}}
h1 {{ margin: 0; font-size: 34px; letter-spacing: -1px; }}
.subtitle {{ color: var(--muted); margin: 9px 0 0; font-size: 14px; }}
.search {{ display: flex; gap: 10px; max-width: 680px; margin: 0 auto 48px; }}
.search input {{
    flex: 1; min-width: 0; height: 54px; border-radius: 16px;
    border: 1px solid var(--border); background: var(--field); color: var(--text);
    padding: 0 20px; font-size: 16px; outline: none;
}}
.search input:focus {{ border-color: var(--accent); }}
.search button {{
    border: 0; border-radius: 14px; background: var(--accent); color: white;
    padding: 0 21px; font-size: 15px; font-weight: 700; cursor: pointer;
}}
section {{ margin: 0 0 36px; }}
.section-title {{
    display: flex; align-items: center; justify-content: space-between;
    margin: 0 0 14px; color: var(--muted); font-size: 12px;
    font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase;
}}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }}
.card {{
    min-width: 0; min-height: 78px; padding: 14px; display: flex; gap: 12px;
    align-items: center; text-decoration: none; color: var(--text);
    background: var(--card); border: 1px solid var(--border); border-radius: 14px;
    transition: background .15s ease, transform .15s ease;
}}
.card:hover {{ background: var(--card-hover); transform: translateY(-2px); }}
.letter {{
    flex: 0 0 40px; width: 40px; height: 40px; display: grid; place-items: center;
    border-radius: 12px; color: white; font-size: 18px; font-weight: 800;
}}
.card-copy {{ min-width: 0; }}
.name, .domain {{ display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.name {{ font-size: 14px; font-weight: 650; }}
.domain {{ margin-top: 4px; color: var(--muted); font-size: 12px; }}
.empty {{ color: var(--muted); background: var(--card); border: 1px dashed var(--border); border-radius: 14px; padding: 20px; font-size: 14px; }}
.private-notice {{
    margin: 24px auto 0; max-width: 680px; border: 1px solid var(--private);
    background: color-mix(in srgb, var(--private) 12%, var(--card));
    color: var(--text); border-radius: 14px; padding: 15px 18px; line-height: 1.55;
}}
.private-notice strong {{ color: var(--private); display: block; margin-bottom: 4px; }}
footer {{ margin-top: 44px; color: var(--muted); font-size: 12px; text-align: center; }}
@media (max-width: 600px) {{
    main {{ padding-top: 40px; }}
    .search {{ flex-direction: column; }}
    .search button {{ height: 48px; }}
    h1 {{ font-size: 29px; }}
}}
"""

# ══════════════════════════════════════════════════════════════════════════════
# CORES — paleta base (nomes semânticos)
# ══════════════════════════════════════════════════════════════════════════════
PRETO          = "#020202"
PRETO_FOSCO    = "#070706"
CINZA_ESCURO   = "#0F1210"
BRANCO         = "#EDEEF0"
AMARELO        = "#FFC107"
AMBAR          = "#E0A800"
VERDE          = "#4ec994"
TURQUESA       = "#00C2A8"
AZUL_CLARO     = "#2196F3"
AZUL           = "#0057FF"
AZUL_ESCURO    = "#1FB8D0"
CORAL          = "#FF6B6B"
VERMELHO       = "#A10510"
LARANJA_ESCURO = "#9E3B02"

# ══════════════════════════════════════════════════════════════════════════════
# CORES — UI escuro (usadas nos estilos QSS abaixo)
# ══════════════════════════════════════════════════════════════════════════════
COR_BG_APP           = "#1a1a1a"   # fundo principal
COR_BG_SECUNDARIO    = "#0d1f25"   # menubar, toolbar, status bar
COR_BG_TERCIARIO     = "#2a2a2a"   # menus, inputs, cards
COR_BG_CAMPO         = "#1e1e1e"   # dialogs, list widgets
COR_BG_ESCURO        = "#222222"   # scrollbars, fundos muito escuros
COR_BORDA            = "#333333"   # bordas gerais
COR_BORDA_CLARA      = "#444444"   # bordas de inputs, handles
COR_TEXTO            = "#dddddd"   # texto principal
COR_TEXTO_SECUNDARIO = "#aaaaaa"   # labels secundários
COR_TEXTO_SUTIL      = "#777777"   # placeholders
COR_TEXTO_INATIVO    = "#666666"   # botões desabilitados
COR_ACENTO           = "#3a7bd5"   # cor de destaque principal
COR_ACENTO_HOVER     = "#2f6bc4"
COR_ACENTO_ATIVO     = "#3a5a8a"   # seleção / checked
COR_ACENTO_BORDA     = "#5a8aba"   # borda do item ativo
COR_SUCESSO          = "#22aa77"
COR_SUCESSO_HOVER    = "#22cc99"
COR_PERIGO           = "#a10510"

# ══════════════════════════════════════════════════════════════════════════════
# ESTILOS QSS — prontos para uso direto
# ══════════════════════════════════════════════════════════════════════════════

ESTILO_ESCURO_GLOBAL = f"""
QMainWindow, QWidget {{
    background: {COR_BG_APP};
    color: {COR_TEXTO};
    font-family: "{FONTE_NOME_UI}", Arial, sans-serif;
    font-size: {FONTE_TAMANHO_LABEL}px;
}}
QSplitter::handle {{ background: {COR_BORDA}; }}
QMenuBar {{
    background: {COR_BG_SECUNDARIO};
    color: {COR_TEXTO};
    border-bottom: 1px solid {COR_BORDA};
}}
QMenuBar::item:selected {{ background: {COR_ACENTO}; }}
QMenu {{
    background: {COR_BG_TERCIARIO};
    color: {COR_TEXTO};
    border: 1px solid {COR_BORDA_CLARA};
}}
QMenu::item:selected {{ background: {COR_ACENTO}; }}
QToolBar {{
    background: {COR_BG_SECUNDARIO};
    border-bottom: 1px solid {COR_BORDA};
    spacing: 4px;
    padding: 2px;
}}
QToolButton {{
    background: transparent;
    color: {COR_TEXTO};
    border: none;
    padding: 4px 8px;
    border-radius: 3px;
}}
QToolButton:hover   {{ background: #3a3a3a; }}
QToolButton:pressed {{ background: {COR_BG_TERCIARIO}; }}
QStatusBar {{
    background: {COR_BG_SECUNDARIO};
    color: {COR_TEXTO_SECUNDARIO};
    border-top: 1px solid {COR_BORDA};
    font-size: {FONTE_TAMANHO_DETALHE}px;
}}
QScrollBar:vertical {{
    background: {COR_BG_ESCURO}; width: 10px; border: none;
}}
QScrollBar::handle:vertical {{
    background: {COR_BORDA_CLARA}; border-radius: 5px; min-height: 20px;
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: {COR_BG_ESCURO}; height: 10px; border: none;
}}
QScrollBar::handle:horizontal {{
    background: {COR_BORDA_CLARA}; border-radius: 5px; min-width: 20px;
}}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{ width: 0; }}
"""

ESTILO_DIALOGO_ESCURO = f"""
QDialog    {{ background: {COR_BG_CAMPO}; color: {COR_TEXTO}; }}
QLabel     {{ color: {COR_TEXTO_SECUNDARIO}; }}
QGroupBox  {{
    color: #bbbbbb;
    border: 1px solid {COR_BORDA};
    border-radius: 4px;
    margin-top: 8px;
    font-size: {FONTE_TAMANHO_LABEL}px;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 4px; }}
QComboBox, QSpinBox, QLineEdit, QDoubleSpinBox {{
    background: {COR_BG_TERCIARIO};
    color: {COR_TEXTO};
    border: 1px solid {COR_BORDA_CLARA};
    border-radius: 3px;
    padding: 3px;
}}
"""

ESTILO_BTN_PRIMARIO = f"""
QPushButton {{
    background: {COR_ACENTO};
    color: #ffffff;
    border: none;
    padding: 8px 20px;
    border-radius: 4px;
    font-size: {FONTE_TAMANHO_INFO}px;
    font-weight: bold;
}}
QPushButton:hover    {{ background: {COR_ACENTO_HOVER}; }}
QPushButton:disabled {{ background: {COR_BG_TERCIARIO}; color: {COR_TEXTO_INATIVO}; }}
"""

ESTILO_BTN_CANCELAR = f"""
QPushButton {{
    background: {COR_BORDA_CLARA};
    color: {COR_TEXTO_SECUNDARIO};
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
}}
QPushButton:hover {{ background: {COR_TEXTO_SUTIL}; }}
"""

ESTILO_LIST_WIDGET = f"""
QListWidget {{
    background: {COR_BG_APP};
    border: none;
    color: {COR_TEXTO};
}}
QListWidget::item {{ padding: 4px; border-bottom: 1px solid {COR_BORDA}; }}
QListWidget::item:selected {{ background: {COR_ACENTO_ATIVO}; }}
QListWidget::item:hover    {{ background: {COR_BG_TERCIARIO}; }}
"""

ESTILO_PROGRESSBAR = f"""
QProgressBar {{
    background: {COR_BG_TERCIARIO};
    border: 1px solid {COR_BORDA_CLARA};
    border-radius: 3px;
}}
QProgressBar::chunk {{
    background: {COR_ACENTO};
    border-radius: 2px;
}}
"""

ESTILO_NAVEGADOR_EXTRA = _estilo_navegador_extra()
ESTILO_NAVEGADOR_ANONIMO = _estilo_navegador_anonimo()
CSS_PAGINA_INICIAL = _css_pagina_inicial()

IDIOMA_UI = "pt-BR"
FORMATO_DATA_HISTORICO = "%d/%m/%Y %H:%M"
TEXTO_UI = {
    "browser_name": "hen-Nave",
    "home_title": "hen-Nave — Início",
    "brand_initial": "h",
    "home_subtitle": "O que você quer descobrir hoje?",
    "home_search_placeholder": "Pesquisar ou digitar um endereço",
    "search": "Pesquisar",
    "favorites": "Favoritos",
    "favorites_empty": "Seus favoritos aparecerão aqui.",
    "recent": "Visitados recentemente",
    "recent_empty": "As páginas que você visitar aparecerão aqui.",
    "private_heading": "Navegação anônima",
    "home_footer": "hen-Nave · Navegação simples e local",
    "main_tab": "Principal",
    "new_tab": "Nova aba",
    "navigation_toolbar": "Navegação",
    "new_tab_button": "+",
    "menu_symbol": "☰",
    "favorite_empty_symbol": "☆",
    "favorite_active_symbol": "★",
    "wait": "Aguarde...",
    "confirm": "Confirmar",
    "cancel": "Cancelar",
    "already_open_title": "Já está aberto",
    "already_open_message": "O aplicativo já está em execução.",
    "back": "Voltar",
    "forward": "Avançar",
    "reload": "Recarregar",
    "home": "Início",
    "new_tab_tooltip": "Nova aba",
    "address_placeholder": "Pesquisar ou digitar um endereço",
    "favorite_add": "Adicionar aos favoritos",
    "favorite_remove": "Remover dos favoritos",
    "private_short": "Anônima",
    "menu_tooltip": "Menu",
    "ready": "Pronto",
    "history": "Histórico",
    "new_window": "Nova janela",
    "private_window": "Nova janela anônima",
    "find": "Localizar",
    "zoom_in": "Aumentar zoom",
    "zoom_out": "Diminuir zoom",
    "zoom_default": "Zoom padrão",
    "clear_history": "Limpar histórico",
    "about": "Sobre",
    "close_tab": "Fechar aba",
    "focus_address": "Focar endereço",
    "favorite_toggle": "Adicionar/remover favorito",
    "find_placeholder": "Localizar nesta página",
    "previous": "Anterior",
    "next": "Próximo",
    "close": "Fechar",
    "private_suffix": " — Anônima",
    "load_success": "Concluído",
    "load_failure": "Não foi possível carregar a página",
    "loading_prefix": "Carregando…",
    "download_dialog": "Salvar download",
    "download_filter": "Todos os arquivos (*)",
    "download_default_name": "download",
    "download_started": "Baixando: {name}",
    "download_completed": "Download concluído: {name}",
    "download_cancelled": "Download cancelado ou interrompido",
    "favorite_added": "Favorito adicionado",
    "favorite_removed": "Favorito removido",
    "history_cleared": "Histórico removido",
    "about_title": "Sobre o hen-Nave",
    "about_message": "hen-Nave {version}\n\nNavegador desktop em Python, PySide6 e QtWebEngine.",
    "confirm_clear_title": "Limpar histórico",
    "confirm_clear_message": "Remover todo o histórico salvo neste computador?",
    "history_search_label": "Pesquisar no histórico",
    "history_search_placeholder": "Título ou endereço",
    "history_open": "Abrir em nova aba",
    "history_remove": "Remover selecionado",
    "favorites_search_label": "Pesquisar nos favoritos",
    "favorites_search_placeholder": "Nome ou endereço",
    "favorite_open": "Abrir em nova aba",
    "favorite_remove": "Remover favorito",
    "history_entry_format": "{title}\n{url}",
    "history_entry_date_format": "{entry}  ·  {date}",
    "favorite_entry_format": "{title}\n{url}",
}
