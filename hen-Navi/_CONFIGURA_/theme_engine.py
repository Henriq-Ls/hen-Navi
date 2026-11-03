"""Gera estilos Qt e CSS da página inicial a partir dos temas configurados."""

import re
from collections.abc import Mapping

from _CONFIGURA_.temas import (
    CHAVES_CORES_PERSONALIZADAS,
    CHAVES_FONTES_PERSONALIZADAS,
    TEMAS,
    TEMA_PADRAO,
    TEMA_PERSONALIZADO,
)


def normalizar_tema_personalizado(values: object) -> dict[str, str]:
    """Mantém somente cores e fontes seguras para CSS/QSS."""
    if not isinstance(values, Mapping):
        return {}

    normalized = {}
    for key in CHAVES_CORES_PERSONALIZADAS:
        value = values.get(key)
        if isinstance(value, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            normalized[key] = value.upper()

    for key in CHAVES_FONTES_PERSONALIZADAS:
        value = values.get(key)
        if not isinstance(value, str):
            continue
        family = " ".join(value.split())
        if (
            0 < len(family) <= 80
            and all(character.isalnum() or character in " -_." for character in family)
        ):
            normalized[key] = family
    return normalized


def obter_tema(
    theme_id: str | None = None,
    *,
    custom_theme: object = None,
) -> dict:
    """Retorna o tema solicitado ou o tema padrão; ids inválidos falham claramente."""
    selected = theme_id or TEMA_PADRAO
    if selected == TEMA_PERSONALIZADO:
        theme = dict(TEMAS[TEMA_PADRAO])
        theme["name"] = "Personalizado"
        theme.update(normalizar_tema_personalizado(custom_theme))
        return theme
    try:
        return TEMAS[selected]
    except KeyError as error:
        raise ValueError(f"Tema desconhecido: {selected}") from error


def stylesheet_for_theme(
    theme_id: str | None = None,
    *,
    private: bool = False,
    custom_theme: object = None,
) -> str:
    """Produz um stylesheet completo sem depender de Qt."""
    theme = obter_tema(theme_id, custom_theme=custom_theme)
    private_rules = ""
    if private:
        private_rules = f'''
QMainWindow[privateMode="true"] QToolBar {{
    border-bottom: {theme["border_width_px"]}px solid {theme["private"]};
}}
QMainWindow[privateMode="true"] QTabBar::tab:selected {{
    border-bottom: {theme["border_width_px"]}px solid {theme["private"]};
}}
QMainWindow[privateMode="true"] QLineEdit#addressBar:focus {{
    border-color: {theme["private"]};
}}
QMainWindow[privateMode="true"] QToolButton#privateIndicator {{
    color: {theme["private"]};
    background: {theme["private_background"]};
    border-radius: {theme["control_radius_px"]}px;
}}
'''
    return f'''
QMainWindow, QWidget {{
    background-color: {theme["background"]};
    color: {theme["text"]};
    font-family: "{theme["font_ui"]}", "{theme["font_fallback"]}";
    font-size: {theme["font_size_px"]}px;
}}
QDialog, QMenu, QMenuBar, QTabBar, QPushButton, QToolButton, QGroupBox {{
    font-family: "{theme["font_ui"]}", "{theme["font_fallback"]}";
}}
QLineEdit, QTextEdit, QPlainTextEdit {{
    font-family: "{theme["font_content"]}", "{theme["font_fallback"]}";
    font-size: {theme["content_font_size_px"]}px;
}}
QLineEdit#addressBar {{
    background: {theme["field"]};
    color: {theme["text"]};
    border: {theme["border_width_px"]}px solid {theme["border_strong"]};
    border-radius: {theme["radius_px"]}px;
    padding: {theme["spacing_px"]}px {theme["spacing_px"] * 2}px;
    selection-background-color: {theme["accent"]};
}}
QLineEdit#addressBar:focus {{ border-color: {theme["accent"]}; }}
QTabWidget::pane {{
    border: {theme["border_width_px"]}px solid {theme["border"]};
}}
QTabBar::tab {{
    background: {theme["surface"]};
    color: {theme["text_secondary"]};
    padding: {theme["spacing_px"]}px {theme["spacing_px"] * 2}px;
    border: {theme["border_width_px"]}px solid {theme["border"]};
}}
QTabBar::tab:selected {{
    background: {theme["background"]};
    color: {theme["text"]};
    border-bottom: {theme["border_width_px"]}px solid {theme["accent"]};
}}
QTabBar::tab:hover {{ background: {theme["surface_alt"]}; }}
QToolBar {{
    background: {theme["surface"]};
    border-bottom: {theme["border_width_px"]}px solid {theme["border"]};
    spacing: {theme["spacing_px"]}px;
    padding: {theme["spacing_px"]}px;
}}
QToolBar#windowControlsToolbar {{
    background: {theme["surface"]};
    border-bottom: none;
    border-left: {theme["border_width_px"]}px solid {theme["border"]};
    spacing: 2px;
    padding: 0;
}}
QToolButton {{
    background: transparent;
    color: {theme["text"]};
    border: {theme["border_width_px"]}px solid transparent;
    padding: {theme["spacing_px"]}px {theme["spacing_px"] + 2}px;
    border-radius: {theme["control_radius_px"]}px;
}}
QToolButton#brandMenuButton {{
    padding: {theme["spacing_px"]}px {theme["spacing_px"] * 2}px;
    font-weight: bold;
}}
QToolButton#windowControlButton,
QToolButton#openAppDataButton,
QToolButton#clearCacheButton,
QToolButton#inspectPageButton {{
    padding: {theme["spacing_px"]}px;
}}
QToolButton#aiButton:disabled {{ color: {theme["muted"]}; }}
QToolButton#closeWindowButton:hover {{
    background: {theme["danger"]};
    border-color: {theme["danger"]};
}}
QWidget#sidePanelHeader {{
    background: {theme["surface"]};
    border-bottom: {theme["border_width_px"]}px solid {theme["border"]};
}}
QLabel#sidePanelTitle {{
    color: {theme["text_secondary"]};
    font-weight: bold;
}}
QToolButton#closeSidePanelButton:hover {{
    background: {theme["danger"]};
    border-color: {theme["danger"]};
}}
QToolButton:hover, QPushButton:hover {{
    background: {theme["surface_alt"]};
    border-color: {theme["border_strong"]};
}}
QToolButton:pressed, QPushButton:pressed {{ background: {theme["accent_active"]}; }}
QToolButton#tabCloseButton {{
    color: {theme["muted"]};
    background: transparent;
    border: none;
    padding: 0 {theme["spacing_px"]}px;
}}
QToolButton#tabCloseButton:hover {{
    color: {theme["danger"]};
    background: {theme["surface_alt"]};
    border: {theme["border_width_px"]}px solid {theme["danger"]};
    border-radius: {theme["control_radius_px"]}px;
    padding: 0;
}}
QToolButton#favoriteButton {{ color: {theme["accent"]}; }}
QTreeWidget#inspectorTree {{
    background: {theme["field"]};
    color: {theme["text"]};
    border: {theme["border_width_px"]}px solid {theme["border"]};
    border-radius: {theme["control_radius_px"]}px;
}}
QPlainTextEdit#inspectorMarkup {{
    background: {theme["field"]};
    color: {theme["text"]};
    border: {theme["border_width_px"]}px solid {theme["border"]};
    border-radius: {theme["control_radius_px"]}px;
}}
QLabel#shortcutKey {{ color: {theme["accent"]}; font-weight: bold; }}
QLabel#noteIndicator {{ color: {theme["success"]}; }}
QLabel#loadingOverlayLabel {{ color: {theme["text"]}; }}
QMenuBar {{
    background: {theme["surface"]};
    color: {theme["text"]};
    border-bottom: {theme["border_width_px"]}px solid {theme["border"]};
}}
QMenuBar::item:selected, QMenu::item:selected {{ background: {theme["accent_active"]}; }}
QMenu {{
    background: {theme["surface_alt"]};
    color: {theme["text"]};
    border: {theme["border_width_px"]}px solid {theme["border_strong"]};
}}
QMenu::item {{
    padding: {theme["spacing_px"]}px {theme["spacing_px"] * 4}px
             {theme["spacing_px"]}px {theme["spacing_px"] * 2}px;
}}
QStatusBar {{
    background: {theme["surface"]};
    color: {theme["text_secondary"]};
    border-top: {theme["border_width_px"]}px solid {theme["border"]};
}}
QDialog, QGroupBox {{
    background: {theme["background"]};
    color: {theme["text"]};
}}
QGroupBox {{
    border: {theme["border_width_px"]}px solid {theme["border"]};
    border-radius: {theme["radius_px"]}px;
    margin-top: {theme["spacing_px"] * 2}px;
    padding: {theme["spacing_px"]}px;
}}
QGroupBox::title {{ color: {theme["text_secondary"]}; }}
QListWidget, QTextEdit, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background: {theme["field"]};
    color: {theme["text"]};
    border: {theme["border_width_px"]}px solid {theme["border"]};
    border-radius: {theme["control_radius_px"]}px;
    padding: {theme["spacing_px"]}px;
}}
QListWidget::item {{
    padding: {theme["spacing_px"]}px;
    border-bottom: {theme["border_width_px"]}px solid {theme["border"]};
}}
QListWidget::item:selected {{ background: {theme["accent_active"]}; }}
QPushButton {{
    background: {theme["surface_alt"]};
    color: {theme["text"]};
    border: {theme["border_width_px"]}px solid {theme["border"]};
    border-radius: {theme["control_radius_px"]}px;
    padding: {theme["spacing_px"]}px {theme["spacing_px"] * 2}px;
}}
QPushButton#dangerButton {{ background: {theme["danger"]}; color: {theme["text"]}; }}
QScrollBar:vertical {{
    background: {theme["background"]};
    width: {theme["scrollbar_size_px"]}px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {theme["border_strong"]};
    border-radius: {theme["control_radius_px"]}px;
    min-height: {theme["scrollbar_handle_min_px"]}px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: {theme["background"]};
    height: {theme["scrollbar_size_px"]}px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: {theme["border_strong"]};
    border-radius: {theme["control_radius_px"]}px;
    min-width: {theme["scrollbar_handle_min_px"]}px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
{private_rules}
'''


def startpage_theme_css(
    theme_id: str | None = None,
    *,
    custom_theme: object = None,
) -> str:
    """Sobrescreve paleta, tipografia e geometrias da página inicial local."""
    theme = obter_tema(theme_id, custom_theme=custom_theme)
    return f'''
:root {{
    --bg: {theme["background"]};
    --card: {theme["surface"]};
    --card-hover: {theme["surface_alt"]};
    --field: {theme["field"]};
    --border: {theme["border"]};
    --text: {theme["text"]};
    --muted: {theme["text_secondary"]};
    --link: {theme["accent"]};
    --accent: {theme["accent"]};
    --private: {theme["private"]};
    --space: {theme["spacing_px"]}px;
}}
body {{ font-family: "{theme["font_content"]}", "{theme["font_fallback"]}"; }}
.brand-mark, .search input, .search button, .card, .letter, .empty,
.private-notice {{ border-radius: {theme["radius_px"]}px; }}
.brand-mark {{ background: linear-gradient(135deg, var(--accent), {theme["accent_hover"]}); }}
.card, .empty, .private-notice, .search input {{
    border-width: {theme["border_width_px"]}px;
}}
.search button {{ background: var(--accent); }}
.brand {{ margin-bottom: calc(var(--space) * 6); }}
.search {{ gap: calc(var(--space) * 2); margin-bottom: calc(var(--space) * 9); }}
.grid {{ gap: calc(var(--space) * 2); }}
.card {{ padding: calc(var(--space) * 3); }}
section {{ margin-bottom: calc(var(--space) * 7); }}
'''
