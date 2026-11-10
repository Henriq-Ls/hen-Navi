"""Gera estilos Qt e CSS da página inicial a partir dos temas configurados."""

import re
from collections.abc import Mapping

from _CONFIGURA_.temas import (
    CHAVES_CORES_PERSONALIZADAS,
    CHAVES_FONTES_PERSONALIZADAS,
    LIMITES_METRICAS_PERSONALIZADAS,
    TEMAS,
    TEMA_PADRAO,
    TEMA_PERSONALIZADO,
)


def normalizar_tema_personalizado(values: object) -> dict[str, str | int]:
    """Mantém cores, fontes e métricas personalizadas dentro de limites seguros."""
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

    for key, (minimum, maximum) in LIMITES_METRICAS_PERSONALIZADAS.items():
        value = values.get(key)
        if (
            isinstance(value, int)
            and not isinstance(value, bool)
            and minimum <= value <= maximum
        ):
            normalized[key] = value
    return normalized


def ensure_contrast_color(
    foreground: str,
    background: str,
    minimum_ratio: float = 3.0,
) -> str:
    """Keep a foreground color when legible; otherwise choose black or white."""
    def luminance(color: str) -> float | None:
        if not isinstance(color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            return None
        channels = [
            int(color[index:index + 2], 16) / 255
            for index in (1, 3, 5)
        ]
        linear = [
            channel / 12.92
            if channel <= 0.04045
            else ((channel + 0.055) / 1.055) ** 2.4
            for channel in channels
        ]
        return (
            0.2126 * linear[0]
            + 0.7152 * linear[1]
            + 0.0722 * linear[2]
        )

    foreground_luminance = luminance(foreground)
    background_luminance = luminance(background)
    if foreground_luminance is None or background_luminance is None:
        return foreground

    def contrast_ratio(first: float, second: float) -> float:
        lighter, darker = max(first, second), min(first, second)
        return (lighter + 0.05) / (darker + 0.05)

    if contrast_ratio(foreground_luminance, background_luminance) >= minimum_ratio:
        return foreground.upper()

    alternatives = ("#FFFFFF", "#111111")
    return max(
        alternatives,
        key=lambda color: contrast_ratio(
            luminance(color),
            background_luminance,
        ),
    )


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
    tab_height = max(
        theme["tab_height_px"],
        theme["font_size_px"] + 10,
    )
    tab_vertical_padding = max(
        0,
        (
            tab_height
            - theme["font_size_px"]
            - 2 * theme["border_width_px"]
        ) // 2,
    )
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
    background: {theme["background"]};
    color: {theme["text_secondary"]};
    padding: {tab_vertical_padding}px {theme["spacing_px"] * 2}px;
    border: {theme["border_width_px"]}px solid {theme["border"]};
}}
QTabBar::tab:selected {{
    background: {theme["surface"]};
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
QToolBar#navigationToolbar::separator {{
    background: {theme["border_strong"]};
    width: {theme["border_width_px"]}px;
    height: 22px;
    margin: 2px {theme["spacing_px"]}px;
}}
QToolBar#browserSidebarToolbar {{
    background: {theme["background"]};
    border-left: {theme["border_width_px"]}px solid {theme["border"]};
    border-top: none;
    border-right: none;
    border-bottom: none;
    spacing: 2px;
    padding: {theme["spacing_px"]}px 0;
}}
QToolBar#browserSidebarToolbar::separator {{
    background: {theme["border_strong"]};
    height: {theme["border_width_px"]}px;
    margin: {theme["spacing_px"]}px 6px;
}}
QToolButton {{
    background: transparent;
    color: {theme["text"]};
    border: {theme["border_width_px"]}px solid transparent;
    padding: {theme["spacing_px"]}px {theme["spacing_px"] + 2}px;
    border-radius: {theme["control_radius_px"]}px;
}}
QToolBar#browserSidebarToolbar QToolButton {{
    background: {theme["background"]};
}}
QToolBar#browserSidebarToolbar QToolButton:hover {{
    background: {theme["surface_alt"]};
}}
QToolBar#browserSidebarToolbar QToolButton:pressed {{
    background: {theme["accent_active"]};
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
QWidget#sidePanelContainer {{
    background: {theme["background"]};
    border-left: {theme["border_width_px"]}px solid {theme["border"]};
}}
QWidget#sidePanelTabsInset {{ background: {theme["background"]}; }}
QWidget#sidePanelHeader {{
    background: {theme["surface"]};
    border-bottom: {theme["border_width_px"]}px solid {theme["border"]};
}}
QLabel#sidePanelTitle {{
    color: {theme["text_secondary"]};
    font-weight: bold;
}}
QStackedWidget#rightSidePanelStack {{
    background: {theme["background"]};
    border: none;
}}
QDockWidget, QDockWidget::widget {{
    background: {theme["background"]};
    border: none;
}}
QToolButton#closeSidePanelButton {{
    color: {theme["muted"]};
    background: transparent;
    border: none;
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
QToolButton#favoriteButton {{ color: {theme["icon"]}; }}
QToolButton#dataSaverButton:checked {{
    background: {theme["accent_active"]};
    border: {theme["border_width_px"]}px solid {theme["accent"]};
    border-radius: {theme["control_radius_px"]}px;
}}
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
QWidget#favoritesAndStatusFooter {{
    background: {theme["background"]};
    border: none;
}}
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
    background: {theme["background"]};
    color: {theme["text_secondary"]};
    border: none;
}}
QStatusBar::item {{ border: none; }}
QStatusBar QLabel {{ background: {theme["background"]}; }}
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
QFrame#explorerToolbar, QFrame#explorerFooter {{
    background: {theme["surface"]};
    border: {theme["border_width_px"]}px solid {theme["border"]};
    border-radius: {theme["control_radius_px"]}px;
}}
QToolButton#explorerNavigationButton {{
    background: transparent;
    color: {theme["text"]};
    border: none;
    padding: {theme["spacing_px"]}px;
}}
QToolButton#explorerNavigationButton:hover {{
    background: {theme["surface_alt"]};
}}
QListWidget#explorerPlaces {{
    background: {theme["background"]};
    color: {theme["text"]};
    border: {theme["border_width_px"]}px solid {theme["border"]};
    border-radius: {theme["control_radius_px"]}px;
}}
QListWidget#explorerPlaces::item:selected {{
    background: {theme["accent_active"]};
    color: {theme["text"]};
}}
QFrame#explorerPlacesSeparator {{
    background: {theme["border"]};
    border: none;
    max-height: 1px;
    min-height: 1px;
    margin: 4px 8px;
}}
QFrame#explorerPreviewPanel {{
    background: {theme["surface"]};
    border: {theme["border_width_px"]}px solid {theme["border"]};
    border-radius: {theme["control_radius_px"]}px;
}}
QLabel#explorerPreviewTitle {{
    color: {theme["text"]};
    font-weight: bold;
}}
QLabel#explorerPreviewImage {{
    background: {theme["background"]};
    color: {theme["text_secondary"]};
    border: {theme["border_width_px"]}px solid {theme["border"]};
    border-radius: {theme["control_radius_px"]}px;
}}
QLabel#explorerPreviewDetails {{ color: {theme["text"]}; }}
QTreeView#explorerFileView {{
    background: {theme["field"]};
    alternate-background-color: {theme["background"]};
    color: {theme["text"]};
    border: {theme["border_width_px"]}px solid {theme["border"]};
    border-radius: {theme["control_radius_px"]}px;
}}
QTreeView#explorerFileView::item:selected {{
    background: {theme["accent_active"]};
    color: {theme["text"]};
}}
QHeaderView::section {{
    background: {theme["surface"]};
    color: {theme["text_secondary"]};
    border: none;
    border-bottom: {theme["border_width_px"]}px solid {theme["border"]};
    padding: {theme["spacing_px"]}px;
}}
QComboBox#explorerPathInput, QLineEdit#explorerSearchInput,
QLineEdit#explorerFilenameInput, QComboBox#explorerFilterCombo {{
    background: {theme["field"]};
    color: {theme["text"]};
    border: {theme["border_width_px"]}px solid {theme["border"]};
    border-radius: {theme["control_radius_px"]}px;
    padding: {theme["spacing_px"]}px;
}}
QComboBox#explorerPathInput:focus, QLineEdit#explorerSearchInput:focus,
QLineEdit#explorerFilenameInput:focus, QComboBox#explorerFilterCombo:focus {{
    border-color: {theme["accent"]};
}}
QPushButton#explorerPrimaryButton {{
    background: {theme["accent"]};
    color: {theme["text"]};
    border-color: {theme["accent"]};
    font-weight: bold;
}}
QPushButton#explorerCancelButton {{
    background: {theme["surface_alt"]};
    color: {theme["text"]};
}}
QLabel#explorerStatusLabel {{ color: {theme["text_secondary"]}; }}
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
