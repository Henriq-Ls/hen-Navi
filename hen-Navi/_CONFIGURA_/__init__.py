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
# Windows: %APPDATA%\hen-nave
# Linux/Mac: ~/.hen-nave
if os.name == "nt":
    _PASTA_APPDATA_BASE = os.environ.get("APPDATA") or os.path.join(
        os.path.expanduser("~"), "AppData", "Roaming"
    )
    PASTA_APPDATA = os.path.join(_PASTA_APPDATA_BASE, "hen-nave")
else:
    PASTA_APPDATA = os.path.join(os.path.expanduser("~"), ".hen-nave")

# ══════════════════════════════════════════════════════════════════════════════
# APLICAÇÃO
# ══════════════════════════════════════════════════════════════════════════════
VERSAO_APP  = "v0.3.0"
TITULO_APP  = "hen-Nave"
TEMA_QT     = "Fusion"             # tema base do Qt

# Caminhos absolutos — independentes do CWD de execução
_PROJETO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_MIDIAS = os.path.join(_PROJETO_DIR, "midias")
IMAGEM_ICO   = os.path.join(PASTA_MIDIAS, "icone.ico")
LOGO_SIMB    = os.path.join(PASTA_MIDIAS, "logo.png")
FONTE_PIXEL_ARQUIVO = os.path.join(
    _PROJETO_DIR, "assets", "fonts", "PressStart2P-Regular.ttf"
)
PASTA_FFMPEG = os.path.join(_PROJETO_DIR, "FFmpeg")
CAMINHOS_FFMPEG = (
    PASTA_FFMPEG,
    os.path.join(_PROJETO_DIR, "FFMPEG", "FFmpeg"),
    os.path.join(_PROJETO_DIR, "FFMPEG"),
)
PASTAS_RELATIVAS_FFMPEG = ("bin", "")
EXECUTAVEIS_FFMPEG = ("ffmpeg.exe", "ffmpeg")

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
VERSAO_ESTADO_JANELA = 2

# ══════════════════════════════════════════════════════════════════════════════
# ATALHOS
# ══════════════════════════════════════════════════════════════════════════════
ATALHOS = (
    {"id": "nova_aba", "categoria": "Abas", "atalho": "Ctrl+T", "descricao": "Abre uma nova aba."},
    {"id": "fechar_aba", "categoria": "Abas", "atalho": "Ctrl+W", "descricao": "Fecha a aba atual."},
    {"id": "endereco", "categoria": "Navegação", "atalho": "Ctrl+L", "descricao": "Foca a barra de endereço."},
    {"id": "inicio", "categoria": "Navegação", "atalho": "Alt+Home", "descricao": "Abre a página inicial."},
    {"id": "recarregar", "categoria": "Navegação", "atalho": "F5", "descricao": "Recarrega a página atual."},
    {"id": "historico", "categoria": "Navegação", "atalho": "Ctrl+H", "descricao": "Abre o histórico de navegação."},
    {"id": "favoritos", "categoria": "Navegação", "atalho": "Ctrl+Shift+O", "descricao": "Abre a lista de favoritos."},
    {"id": "favorito", "categoria": "Navegação", "atalho": "Ctrl+D", "descricao": "Adiciona ou remove a página dos favoritos."},
    {"id": "localizar", "categoria": "Página", "atalho": "Ctrl+F", "descricao": "Localiza texto na página atual."},
    {"id": "zoom_mais", "categoria": "Página", "atalho": "Ctrl+=", "descricao": "Aumenta o zoom da página."},
    {"id": "zoom_menos", "categoria": "Página", "atalho": "Ctrl+-", "descricao": "Diminui o zoom da página."},
    {"id": "zoom_reset", "categoria": "Página", "atalho": "Ctrl+0", "descricao": "Restaura o zoom padrão."},
    {"id": "captura", "categoria": "Página", "atalho": "Ctrl+Shift+S", "descricao": "Abre as opções de captura da página."},
    {"id": "nova_janela", "categoria": "Janelas", "atalho": "Ctrl+N", "descricao": "Abre uma nova janela normal."},
    {"id": "janela_anonima", "categoria": "Janelas", "atalho": "Ctrl+Shift+N", "descricao": "Abre uma nova janela anônima."},
    {"id": "bloqueador_site", "categoria": "Ferramentas", "atalho": "Ctrl+Shift+B", "descricao": "Ativa ou desativa o bloqueio neste site."},
    {"id": "anotacoes", "categoria": "Ferramentas", "atalho": "Ctrl+Shift+E", "descricao": "Mostra ou oculta as anotações do site."},
    {"id": "assistente_ia", "categoria": "Ferramentas", "atalho": "Ctrl+Shift+Y", "descricao": "Abre o assistente para resumir ou perguntar sobre a página atual."},
    {"id": "atalhos", "categoria": "Ferramentas", "atalho": "F1", "descricao": "Abre esta lista de atalhos."},
    {"id": "appdata", "categoria": "Ferramentas", "atalho": "Ctrl+Shift+D", "descricao": "Abre a pasta de dados do hen-Nave."},
)
ATALHOS_POR_ID = {item["id"]: item for item in ATALHOS}


def atalho(identificador: str) -> str:
    """Obtém o atalho registrado na fonte única de definições."""
    return ATALHOS_POR_ID[identificador]["atalho"]

# ══════════════════════════════════════════════════════════════════════════════
# HEN-NAVE — valores de produto e navegação
# ══════════════════════════════════════════════════════════════════════════════
ESQUEMA_INTERNO = "hennave"
URL_BUSCA = "https://duckduckgo.com/"
CHAVE_BUSCADOR_PADRAO = "buscador_padrao"
BUSCADOR_PADRAO = "duckduckgo"
BUSCADORES_PESQUISA = {
    "duckduckgo": ("DuckDuckGo", URL_BUSCA),
    "google": ("Google", "https://www.google.com/search"),
    "bing": ("Bing", "https://www.bing.com/search"),
}
ARQUIVO_INICIO = "hen-nave-inicio.html"
ARQUIVO_INICIO_ANONIMO = "hen-nave-inicio-anonimo.html"
ARQUIVO_BANCO = "hen-nave.sqlite3"
ARQUIVO_LISTA_BLOQUEIO = "hen-nave-lista-bloqueio.txt"
ARQUIVO_EXPORTAR_ANOTACOES = "hen-nave-anotacoes.md"
ARQUIVO_LOCK = "hen-nave.lock"
NOME_PERFIL_WEB = "hen-nave"
CHAVE_BLOQUEADOR_ATIVO = "bloqueador_ativo"
CHAVE_URL_LISTA_BLOQUEIO = "lista_bloqueio_url"
URL_LISTA_BLOQUEIO_PADRAO = ""
SEGUNDOS_DEDUP_HISTORICO = 5
LIMITE_RECENTES_INICIO = 8
LIMITE_HISTORICO_DIALOGO = 1000
LIMITE_LISTA_BLOQUEIO_BYTES = 5 * 1024 * 1024
TIMEOUT_LISTA_BLOQUEIO_S = 20
CAPTURA_ALTURA_MAXIMA_PX = 12000
CAPTURA_LARGURA_MAXIMA_PX = 4096
CAPTURA_INTERVALO_REPINTURA_MS = 120
CAPTURA_PASTA = "hen-Nave"
DEBOUNCE_ANOTACOES_MS = 800
LARGURA_DOCK_ANOTACOES = 360
LARGURA_DOCK_IA = 380
LIMITE_CARACTERES_PAGINA_IA_MINIMO = 1000
LIMITE_CARACTERES_PAGINA_IA = 12000
LIMITE_CARACTERES_PAGINA_IA_MAXIMO = 100000
ETAPA_LIMITE_CARACTERES_PAGINA_IA = 1000
TIMEOUT_REQUISICAO_IA_SEGUNDOS = 60
LIMITE_RESPOSTA_IA_BYTES = 8 * 1024 * 1024
LIMITE_HISTORICO_IA_MENSAGENS = 8
LIMITE_MENSAGEM_HISTORICO_IA_CARACTERES = 4000
LIMITE_TOKENS_RESPOSTA_IA = 1200
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
LARGURA_BARRA_CONTROLES_JANELA = 40
TAMANHO_BOTAO_CONTROLE_JANELA = 32
TAMANHO_ICONE_CONTROLE_JANELA = 15
LARGURA_DIALOGO_PADRAO = 760
ALTURA_DIALOGO_PADRAO = 540
LARGURA_DOCK_DOWNLOAD_VIDEO = 380
ATRASO_ANALISE_DOWNLOAD_VIDEO_MS = 650
ALTURA_PREVIEW_TRANSCRICAO_DOWNLOAD = 180
FORMATO_VIDEO_DOWNLOAD_PADRAO = "mp4"
FORMATOS_VIDEO_DOWNLOAD = ("mp4", "mkv", "mov", "avi", "flv", "wmv", "webm")
FORMATO_AUDIO_DOWNLOAD_PADRAO = "mp3"
FORMATOS_AUDIO_DOWNLOAD = ("mp3", "m4a", "wav", "flac", "opus")
QUALIDADE_AUDIO_KBPS_DOWNLOAD = "192"
IDIOMAS_LEGENDA_DOWNLOAD = ("pt", "pt-BR", "en", "en-US")
IDIOMA_TRANSCRICAO_DOWNLOAD = "pt"
MODELO_WHISPER_DOWNLOAD = "base"
ORGANIZAR_DOWNLOAD_POR_VIDEO_PADRAO = True
ROTULO_QUALIDADE_AUTOMATICA = "Melhor disponível"
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
    "A janela anônima não salva histórico, cookies nem a sessão de abas neste "
    "computador. Seus favoritos salvos continuam acessíveis e podem ser "
    "alterados. A navegação anônima não esconde sua atividade dos sites nem "
    "do provedor de internet."
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
QToolButton#tabCloseButton {{
    color: {COR_TEXTO_SUTIL};
    background: transparent;
    border: none;
    padding: 0;
}}
QToolButton#tabCloseButton:hover {{
    color: {COR_PERIGO};
    background: {COR_BG_TERCIARIO};
    border: 1px solid {COR_PERIGO};
    border-radius: 4px;
}}
QToolButton#tabCloseButton, QToolButton#newTabButton,
QToolButton#footerActionButton {{
    min-width: 24px;
    max-width: 24px;
    min-height: 24px;
    max-height: 24px;
}}
QToolButton#newTabButton, QToolButton#footerActionButton {{
    background: transparent;
    border: none;
    padding: 0;
}}
QToolButton#newTabButton:hover, QToolButton#footerActionButton:hover {{
    background: {COR_BG_TERCIARIO};
    border-radius: 4px;
}}
QLabel#shortcutKey {{ color: {COR_ACENTO}; font-weight: bold; }}
QToolButton#favoriteButton {{
    background: transparent; border: none; padding: 0;
}}
QToolButton#favoriteButton:hover, QToolButton#toolsButton:hover {{
    background: {COR_BG_TERCIARIO}; border-radius: 4px;
}}
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
.brand-logo {{
    display: block; width: 104px; height: 104px; margin: 0 auto 15px;
    padding: 8px; border-radius: 24px; background: #fff; object-fit: contain;
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
COR_FAVORITO   = "#FFC857"
COR_FAVORITO_VAZIO = "#FFFFFF"
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
    "wait": "Aguarde...",
    "confirm": "Confirmar",
    "cancel": "Cancelar",
    "ok": "OK",
    "yes": "Sim",
    "no": "Não",
    "already_open_title": "Já está aberto",
    "already_open_message": "O aplicativo já está em execução.",
    "back": "Voltar",
    "forward": "Avançar",
    "reload": "Recarregar",
    "home": "Início",
    "new_tab_tooltip": "Nova aba",
    "keyboard_shortcuts": "Atalhos de teclado",
    "address_placeholder": "Pesquisar ou digitar um endereço",
    "favorite_add": "Adicionar aos favoritos",
    "favorite_remove": "Remover dos favoritos",
    "private_short": "Anônima",
    "menu_tooltip": "Menu",
    "window_brand_tooltip": "Menu e configurações do hen-Nave",
    "window_controls_toolbar": "Controles da janela",
    "window_close": "Fechar janela",
    "window_maximize": "Maximizar janela",
    "window_restore": "Restaurar janela",
    "window_minimize": "Minimizar janela",
    "window_resize": "Redimensionar janela",
    "inspect_page": "Inspecionar página",
    "inspect_title": "Inspecionar página",
    "inspect_notice": (
        "Inspeção manual. As edições são locais e temporárias; não alteram "
        "os arquivos do site."
    ),
    "inspect_refresh": "Atualizar DOM",
    "inspect_search_placeholder": "Buscar no DOM por tag, classe ou texto",
    "inspect_search_button": "Buscar",
    "inspect_select_element": "Selecionar elemento",
    "inspect_cancel_selection": "Cancelar seleção",
    "inspect_copy_text": "Copiar texto",
    "inspect_copy_markup": "Copiar marcação",
    "inspect_markup_heading": "HTML selecionado (valores de campos ocultos)",
    "inspect_no_page": "Abra uma página HTTP(S) para inspecionar.",
    "inspect_empty": "Selecione um elemento na árvore ou na página.",
    "inspect_edit_heading": "Experimento temporário",
    "inspect_text_label": "Texto do elemento",
    "inspect_apply_text": "Aplicar texto",
    "inspect_background_label": "Fundo",
    "inspect_foreground_label": "Texto",
    "inspect_apply_style": "Aplicar cores",
    "inspect_no_element": "Selecione um elemento primeiro.",
    "inspect_selection_armed": "Clique em um elemento da página para selecioná-lo.",
    "inspect_selected": "Elemento selecionado: {selector}",
    "inspect_search_empty": "Nenhum elemento corresponde à busca.",
    "inspect_edit_disabled_control": (
        "A edição de texto e cores não está disponível para campos de formulário."
    ),
    "inspect_invalid_color": "Informe cores válidas, por exemplo #334455.",
    "inspect_update_success": "Alteração temporária aplicada à página.",
    "inspect_update_error": "O elemento não está mais disponível na página.",
    "ai_placeholder": "Assistente de página",
    "ai_title": "Assistente da página",
    "ai_settings": "Inteligência Artificial",
    "ai_settings_title": "Conexões de Inteligência Artificial",
    "ai_no_provider": "Nenhum provedor ativo. Use a engrenagem para configurar a IA.",
    "ai_model_unselected": "Nenhum modelo selecionado. Abra as configurações de IA, escolha um modelo e salve.",
    "ai_local_badge": "Local",
    "ai_cloud_badge": "Nuvem",
    "ai_ready": "Só envia o texto da página após uma ação sua.",
    "ai_extracting": "Lendo o texto visível da página atual…",
    "ai_response_placeholder": "A resposta aparecerá aqui em texto simples.",
    "ai_question_placeholder": "Pergunte algo sobre esta página",
    "ai_summarize": "Resumir página",
    "ai_send": "Enviar",
    "ai_cancel": "Cancelar",
    "ai_copy": "Copiar",
    "ai_clear": "Limpar",
    "ai_truncated": "O texto da página foi cortado no limite configurado.",
    "ai_local_notice": "A solicitação vai para o serviço local configurado.",
    "ai_enter_question": "Digite uma pergunta sobre a página.",
    "ai_copied": "Resposta copiada.",
    "ai_cleared": "Conversa temporária limpa.",
    "ai_add": "Adicionar",
    "ai_edit": "Editar",
    "ai_remove": "Remover",
    "ai_activate": "Ativar selecionado",
    "ai_remove_title": "Remover conexão",
    "ai_remove_confirm": "Remover a conexão “{name}” e sua chave do keyring?",
    "ai_add_title": "Adicionar conexão de IA",
    "ai_edit_title": "Editar conexão de IA",
    "ai_name_label": "Nome",
    "ai_platform_label": "Provedor ou protocolo",
    "ai_base_url_label": "URL base",
    "ai_base_url_placeholder": "https://api.exemplo.com/v1",
    "ai_key_label": "Chave/token",
    "ai_key_placeholder": "Vazio mantém a chave já salva",
    "ai_key_saved_notice": "Chave registrada no cofre seguro do sistema; campo vazio mantém a chave.",
    "ai_key_not_saved": "Nenhuma chave registrada para esta conexão.",
    "ai_key_will_save": "A chave será guardada no cofre seguro do sistema ao salvar.",
    "ai_key_will_remove": "A chave guardada será removida ao salvar.",
    "ai_remove_key": "Remover a chave guardada",
    "ai_model_label": "Modelo",
    "ai_model_placeholder": "Busque, selecione ou informe um modelo",
    "ai_model_required": "Escolha um modelo antes de salvar. Se não aparecer, informe o identificador manualmente.",
    "ai_fetch_models": "Buscar modelos",
    "ai_test_connection": "Testar conexão",
    "ai_page_limit": "Máximo de texto da página",
    "ai_request_in_progress": "A solicitação anterior ainda está em andamento. Aguarde a resposta.",
    "ai_page_extract_failed": "Não consegui ler o texto desta página. Recarregue-a e tente novamente.",
    "ai_page_text_empty": "Não encontrei texto legível nesta página para enviar à IA.",
    "ai_default_ollama_name": "Ollama local",
    "ai_connecting": "Testando conexão…",
    "ai_models_found": "{count} modelo(s) encontrado(s).",
    "ai_models_empty": "A API respondeu, mas não listou modelos. Informe o identificador manualmente.",
    "ai_insecure_title": "Conexão sem TLS",
    "ai_insecure_key_warning": (
        "Esta URL usa HTTP. A chave será enviada sem criptografia para o destino "
        "local configurado. Continue somente se você confia nessa rede."
    ),
    "ai_cloud_consent_title": "Enviar texto para provedor externo?",
    "ai_cloud_consent_message": (
        "O texto visível da página atual será enviado ao serviço externo "
        "“{provider}”. Confira a política de dados desse serviço antes de continuar."
    ),
    "ai_private_cloud_consent_message": (
        "Esta janela é anônima. O texto visível da página será enviado ao serviço "
        "externo “{provider}”. A confirmação será solicitada em cada uso; confira "
        "a política de dados do serviço."
    ),
    "ai_consent_dismiss_checkbox": "Não mostrar novamente para esta conexão em janelas normais",
    "ai_cloud_service_required": "Cadastre e salve a chave nas configurações de IA antes de enviar.",
    "ai_no_page": "Não foi possível obter o texto da página atual.",
    "ai_cancelled": "Solicitação cancelada.",
    "ai_shortcut_description": "Abre o assistente para resumir ou perguntar sobre a página atual.",
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
    "browser_downloads_title": "Downloads",
    "browser_downloads_button": "Downloads",
    "close_side_panel": "Fechar painel",
    "browser_downloads_notice": "Os downloads comuns ficam salvos neste histórico.",
    "browser_downloads_private_notice": (
        "Downloads desta janela anônima aparecem somente durante esta sessão."
    ),
    "browser_downloads_empty": "Nenhum download para mostrar.",
    "browser_downloads_file": "Arquivo",
    "browser_downloads_status": "Estado",
    "browser_downloads_date": "Iniciado em",
    "browser_downloads_open": "Abrir arquivo",
    "browser_downloads_open_folder": "Abrir pasta",
    "browser_downloads_remove": "Remover da lista",
    "browser_download_state_active": "Em andamento",
    "browser_download_state_completed": "Concluído",
    "browser_download_state_cancelled": "Cancelado",
    "browser_download_state_interrupted": "Interrompido",
    "browser_download_state_unknown": "Desconhecido",
    "browser_download_not_completed": "Este download ainda não foi concluído.",
    "browser_download_file_missing": "O arquivo não foi encontrado no local salvo.",
    "browser_download_folder_missing": "A pasta do download não foi encontrada.",
    "browser_download_open_failed": "Não foi possível abrir este local.",
    "browser_download_history_error_title": "Falha no histórico de downloads",
    "browser_download_history_error": (
        "Não foi possível salvar o download no histórico. "
        "O download foi cancelado.\n\nDetalhes: {error}"
    ),
    "favorite_added": "Favorito adicionado",
    "favorite_removed": "Favorito removido",
    "history_cleared": "Histórico removido",
    "about_title": "Sobre o hen-Nave",
    "about_message": "hen-Nave {version}\n\nNavegador desktop em Python, PySide6 e QtWebEngine.",
    "media_diagnostic": "Testar suporte a vídeo",
    "media_diagnostic_title": "Diagnóstico de mídia",
    "media_diagnostic_no_page": "Não há uma página ativa para consultar.",
    "media_diagnostic_result": (
        "Suporte informado pelo QtWebEngine:\n"
        "H.264 / MP4: {h264}\n"
        "AAC / MP4: {aac}\n"
        "VP9 / WebM: {vp9}\n"
        "AV1 / MP4: {av1}\n"
        "MediaSource: {media_source}\n"
        "H.264 em MediaSource: {mse_h264}\n\n"
        "O teste consulta apenas formatos anunciados pelo navegador; "
        "não lê nem envia o conteúdo da página."
    ),
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
    "settings_menu": "Configurações",
    "search_engine_menu": "Buscador padrão",
    "search_engine_invalid": "Mecanismo de pesquisa inválido: {engine}",
    "tools_menu": "Ferramentas",
    "theme_menu": "Tema",
    "theme_custom": "Personalizado",
    "theme_customize": "Personalizar cores e fontes…",
    "theme_custom_title": "Personalizar tema",
    "theme_custom_description": "Escolha as cores da interface e as fontes do navegador e da página inicial.",
    "theme_custom_colors": "Cores da interface",
    "theme_custom_fonts": "Fontes",
    "theme_custom_font_ui": "Fonte da interface",
    "theme_custom_font_content": "Fonte de campos e página inicial",
    "theme_custom_preview": "Prévia",
    "theme_custom_preview_button": "Botão de destaque",
    "theme_custom_save": "Salvar e aplicar",
    "theme_color_background": "Plano de fundo",
    "theme_color_surface": "Barras e menus",
    "theme_color_surface_alt": "Painéis e realce",
    "theme_color_field": "Campos",
    "theme_color_border": "Bordas",
    "theme_color_border_strong": "Bordas fortes",
    "theme_color_text": "Texto principal",
    "theme_color_icon": "Ícones e símbolos",
    "theme_color_text_secondary": "Texto secundário",
    "theme_color_muted": "Texto discreto",
    "theme_color_accent": "Cor de destaque",
    "theme_color_accent_hover": "Destaque ao passar o mouse",
    "theme_color_accent_active": "Destaque pressionado",
    "theme_color_success": "Sucesso",
    "theme_color_danger": "Erro e fechar",
    "theme_color_private": "Modo anônimo",
    "theme_color_private_background": "Fundo do modo anônimo",
    "open_app_data": "Abrir pasta de dados",
    "app_data_opened": "Pasta de dados do hen-Nave aberta.",
    "app_data_open_error": "Não foi possível abrir a pasta de dados do hen-Nave.",
    "clear_cache": "Limpar cache",
    "cache_cleared": "Limpeza do cache iniciada. Cookies e histórico foram mantidos.",
    "cache_clear_error": "Não foi possível limpar o cache de navegação.",
    "capture_menu": "Captura",
    "capture_visible": "Parte visível",
    "capture_full_page": "Página inteira",
    "capture_pdf": "Salvar página como PDF",
    "capture_save_title": "Salvar captura",
    "capture_pdf_save_title": "Salvar página como PDF",
    "capture_image_filter": "Imagem PNG (*.png)",
    "capture_pdf_filter": "Arquivo PDF (*.pdf)",
    "capture_done_title": "Captura concluída",
    "capture_done_message": "Arquivo salvo em:\n{path}\n\nA imagem também foi copiada para a área de transferência.",
    "capture_pdf_done_message": "PDF salvo em:\n{path}",
    "capture_truncated_warning": "A captura atingiu o limite configurado; o conteúdo que excede o limite não foi incluído.",
    "capture_open_folder": "Abrir pasta",
    "capture_close": "Fechar",
    "capture_error_title": "Não foi possível capturar",
    "capture_error_message": "Não foi possível concluir a captura: {error}",
    "capture_busy": "Já existe uma captura em andamento.",
    "capture_started": "Preparando captura…",
    "blocker_name": "Bloqueador de anúncios",
    "blocker_settings": "Configurar bloqueador de anúncios",
    "blocker_toggle_site": "Desativar bloqueio neste site",
    "blocker_toggle_site_on": "Ativar bloqueio neste site",
    "blocker_toggle_no_site": "Alterar bloqueio do site",
    "blocker_tooltip_enabled": "Bloqueador ativo em {site}; {count} bloqueios. Clique para desativar neste site.",
    "blocker_tooltip_disabled": "Bloqueador desativado em {site}. Clique para ativar neste site.",
    "blocker_tooltip_no_site": "O bloqueador está ativo; abra um site HTTP(S) para ver a contagem.",
    "blocker_tooltip_globally_disabled": "O bloqueador está desligado nas configurações.",
    "blocker_global_disabled": "Ative o bloqueador nas configurações antes de alterar este site.",
    "blocker_site_enabled": "Bloqueio ativado para {site}.",
    "blocker_site_disabled": "Bloqueio desativado para {site}.",
    "blocker_settings_title": "Configurações do bloqueador de anúncios",
    "blocker_enabled_label": "Ativar o bloqueador de anúncios",
    "blocklist_url_label": "URL da lista pública (HTTPS)",
    "blocklist_url_placeholder": "Deixe vazio para usar somente a lista local",
    "blocklist_update_button": "Atualizar lista",
    "blocklist_save_button": "Salvar",
    "blocklist_status_ready": "Lista local: {count} domínios.",
    "blocklist_status_downloading": "Baixando a lista…",
    "blocklist_status_updated": "Lista atualizada: {count} domínios.",
    "blocklist_status_saved": "Configurações salvas.",
    "blocklist_status_url_required": "Informe uma URL HTTPS antes de atualizar.",
    "blocklist_status_url_invalid": "A URL da lista precisa usar HTTPS e ter um host válido.",
    "blocklist_status_download_error": "Não foi possível atualizar a lista. Verifique a conexão e tente novamente.",
    "blocklist_status_save_error": "A lista foi baixada, mas não pôde ser salva.",
    "blocklist_status_invalid": "A resposta não contém domínios válidos.",
    "blocklist_status_size_limit": "A lista excede o limite de tamanho permitido.",
    "blocklist_help": "A lista inicial é local. Nenhuma fonte pública vem configurada; confira a origem e a licença antes de usar uma URL.",
    "blocklist_confirm_title": "Atualizar lista de bloqueio",
    "blocklist_confirm_message": "Substituir a lista local pela lista baixada?",
    "notes_title": "Anotações por site",
    "notes_title_with_note": "Anotações por site (com nota)",
    "notes_group": "Anotações",
    "notes_search_placeholder": "Buscar em todas as anotações",
    "notes_editor_placeholder": "Escreva uma anotação para este site",
    "notes_open_site_hint": "Abra um site HTTP(S) para editar sua anotação.",
    "notes_indicator": "● Há uma anotação para este site",
    "notes_search_empty": "Nenhuma anotação encontrada.",
    "notes_search_result_format": "{host} — {preview}",
    "notes_export_button": "Exportar tudo em Markdown",
    "notes_export_title": "Exportar anotações",
    "notes_export_filter": "Markdown (*.md)",
    "notes_export_done_title": "Exportação concluída",
    "notes_export_done": "Anotações exportadas.",
    "notes_export_error": "Não foi possível exportar as anotações: {error}",
    "notes_private_unavailable": "Anotações ficam desativadas em janelas anônimas.",
    "notes_markdown_title": "# Anotações do hen-Nave",
    "notes_markdown_entry": "## {host}\n\n{text}",
    "notes_export_empty": "Ainda não há anotações para exportar.",
    "video_download_title": "Baixar vídeo",
    "video_download_button": "Baixar vídeo",
    "video_download_url_label": "Endereço do vídeo",
    "video_download_url_placeholder": "Cole um link HTTP(S) de vídeo",
    "video_download_analyze": "Analisar link",
    "video_download_info_waiting": "Analise o link para consultar título, canal, duração e qualidades.",
    "video_download_info_format": "Título: {title}\nCanal: {uploader}\nDuração: {duration}\nResolução detectada: {resolution}\nFormato de origem: {format}",
    "video_download_no_qualities": "Qualidades não informadas",
    "video_download_tasks_title": "O que você quer fazer?",
    "video_download_task_video": "Baixar vídeo",
    "video_download_task_audio": "Baixar áudio",
    "video_download_task_transcribe": "Criar transcrição",
    "video_download_task_srt": "Criar legenda SRT",
    "video_download_format_section": "Formatos e qualidade",
    "video_download_quality_label": "Qualidade máxima",
    "video_download_format_label": "Formato do arquivo",
    "video_download_audio_format_label": "Formato do áudio",
    "video_download_destination_label": "Salvar em",
    "video_download_destination_placeholder": "Pasta de destino",
    "video_download_choose_folder": "Escolher",
    "video_download_choose_folder_title": "Escolher pasta para o vídeo",
    "video_download_organize_label": "Organizar em uma pasta por vídeo",
    "video_download_organize_tooltip": "Cria uma subpasta com o título e o identificador do vídeo.",
    "video_download_start": "Iniciar tarefas selecionadas",
    "video_download_status_ready": "Cole ou use o endereço da aba e analise o vídeo.",
    "video_download_status_choose_task": "Marque pelo menos uma tarefa para iniciar.",
    "video_download_status_analyzing": "Consultando informações do vídeo…",
    "video_download_status_downloading": "Preparando as tarefas selecionadas…",
    "video_download_status_progress": "Baixando vídeo — {percent}%",
    "video_download_status_finalizing": "Finalizando o arquivo…",
    "video_download_transcribe_progress": "Baixando áudio para transcrição — {percent}%",
    "video_download_status_complete": "Tarefas concluídas.\nArquivos salvos em:\n{folder}",
    "video_download_status_error": "Não foi possível concluir: {error}",
    "video_download_status_invalid_url": "Informe um endereço HTTP ou HTTPS válido.",
    "video_download_status_analyze_first": "Analise o endereço atual antes de baixar.",
    "video_download_status_busy": "Aguarde a operação atual terminar.",
    "video_download_transcription_title": "Transcrição gerada",
    "video_download_transcription_placeholder": "O texto transcrito aparecerá aqui.",
    "video_download_transcription_saved": "Transcrição salva em {path}",
    "video_download_transcription_srt_saved": "Legenda SRT salva em {path}",
    "video_download_status_find_subtitles": "Procurando legendas disponíveis…",
    "video_download_status_transcribe_audio": "Baixando áudio para transcrição…",
    "video_download_status_load_whisper": "Carregando o modelo de transcrição…",
    "video_download_status_whisper": "Transcrevendo áudio…",
    "video_download_status_no_info": "Não foi possível obter informações desse endereço.",
    "video_download_status_quality_positive": "A qualidade máxima precisa ser positiva.",
    "video_download_status_yt_dlp_failed": "O yt-dlp não conseguiu concluir o download.",
    "video_download_status_no_tasks": "Escolha ao menos uma tarefa de mídia.",
    "video_download_status_transcript_empty": "Não foi encontrada legenda nem fala reconhecível para transcrever.",
    "video_download_status_srt_no_segments": "Não foi possível gerar SRT: a transcrição não retornou trechos com horários.",
    "video_download_not_reported": "—",
    "video_download_unknown_title": "Vídeo sem título",
    "video_download_unknown_channel": "Canal não informado",
    "video_download_ffmpeg_missing": (
        "FFmpeg não encontrado. Coloque ffmpeg.exe em {folder}, "
        "em {folder}/bin ou instale-o no PATH do sistema."
    ),
    "video_download_invalid_format": "O formato de vídeo escolhido não está disponível.",
    "video_download_invalid_operation": "Operação interna de vídeo desconhecida: {operation}",
    "video_download_playlist_unsupported": "Informe o link de um vídeo individual, não de uma playlist.",
    "video_download_yt_dlp_missing": (
        "A dependência yt-dlp não está instalada. Instale os pacotes de "
        "requirements.txt do hen-Nave."
    ),
    "video_download_whisper_missing": (
        "A transcrição automática precisa do pacote openai-whisper. "
        "Instale as dependências de requirements.txt do hen-Nave."
    ),
    "video_download_audio_error": "Não foi possível concluir o download de áudio.",
    "video_download_audio_format_error": "O formato de áudio escolhido não está disponível.",
    "video_download_audio_progress": "Baixando áudio — {percent}%",
    "video_download_transcription_failed": "Não foi possível baixar o áudio para transcrição.",
    "video_download_transcription_file_missing": "O áudio foi baixado, mas o arquivo não foi localizado.",
    "video_download_status_playlist": "Informe o link de um vídeo individual, não de uma playlist.",
}

from .temas import (
    CHAVES_CORES_PERSONALIZADAS,
    CHAVES_FONTES_PERSONALIZADAS,
    CHAVES_TEMA,
    CHAVE_TEMA_PERSONALIZADO,
    TEMAS,
    TEMA_PADRAO,
    TEMA_PERSONALIZADO,
)
