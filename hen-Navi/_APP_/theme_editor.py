"""Editor visual para as cores e fontes do tema personalizado."""

from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFontComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from _CONFIGURA_ import (
    CHAVES_CORES_PERSONALIZADAS,
    CHAVES_FONTES_PERSONALIZADAS,
    TEXTO_UI,
)
from _CONFIGURA_.theme_engine import normalizar_tema_personalizado, obter_tema


class CustomThemeDialog(QDialog):
    """Permite editar e pré-visualizar cores e fontes antes de aplicar."""

    def __init__(self, initial_theme: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(TEXTO_UI["theme_custom_title"])
        self.setMinimumSize(620, 620)
        self.resize(700, 720)

        base_theme = obter_tema("personalizado", custom_theme=initial_theme)
        self._values = {
            key: base_theme[key]
            for key in (*CHAVES_CORES_PERSONALIZADAS, *CHAVES_FONTES_PERSONALIZADAS)
        }
        self._color_buttons: dict[str, QPushButton] = {}

        layout = QVBoxLayout(self)
        description = QLabel(TEXTO_UI["theme_custom_description"], self)
        description.setWordWrap(True)
        layout.addWidget(description)

        fonts_group = QGroupBox(self)
        fonts_group.setTitle(TEXTO_UI["theme_custom_fonts"])
        fonts_form = QFormLayout(fonts_group)
        self.ui_font_combo = self._make_font_combo("font_ui")
        self.content_font_combo = self._make_font_combo("font_content")
        fonts_form.addRow(TEXTO_UI["theme_custom_font_ui"], self.ui_font_combo)
        fonts_form.addRow(
            TEXTO_UI["theme_custom_font_content"],
            self.content_font_combo,
        )
        layout.addWidget(fonts_group)

        colors_group = QGroupBox(TEXTO_UI["theme_custom_colors"], self)
        colors_layout = QVBoxLayout(colors_group)
        color_scroll = QScrollArea(colors_group)
        color_scroll.setWidgetResizable(True)
        color_fields = QWidget(color_scroll)
        color_grid = QGridLayout(color_fields)
        color_grid.setColumnStretch(0, 1)
        color_grid.setColumnStretch(2, 1)
        for index, key in enumerate(CHAVES_CORES_PERSONALIZADAS):
            row = index // 2
            column = (index % 2) * 2
            label = QLabel(TEXTO_UI[f"theme_color_{key}"], color_fields)
            button = QPushButton(color_fields)
            button.setMinimumWidth(96)
            button.clicked.connect(
                lambda _checked=False, selected=key: self._choose_color(selected)
            )
            self._color_buttons[key] = button
            color_grid.addWidget(label, row, column)
            color_grid.addWidget(button, row, column + 1)
            self._render_color_button(key)
        color_scroll.setWidget(color_fields)
        colors_layout.addWidget(color_scroll)
        layout.addWidget(colors_group, 1)

        preview_group = QGroupBox(TEXTO_UI["theme_custom_preview"], self)
        preview_layout = QHBoxLayout(preview_group)
        self.preview_frame = QFrame(preview_group)
        self.preview_frame.setObjectName("customThemePreview")
        preview_inner = QHBoxLayout(self.preview_frame)
        self.preview_label = QLabel("hen-Nave", self.preview_frame)
        self.preview_icon = QLabel("◆", self.preview_frame)
        self.preview_icon.setObjectName("customThemePreviewIcon")
        self.preview_button = QPushButton(
            TEXTO_UI["theme_custom_preview_button"],
            self.preview_frame,
        )
        preview_inner.addWidget(self.preview_label)
        preview_inner.addWidget(self.preview_icon)
        preview_inner.addStretch(1)
        preview_inner.addWidget(self.preview_button)
        preview_layout.addWidget(self.preview_frame)
        layout.addWidget(preview_group)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        save_button = button_box.button(QDialogButtonBox.StandardButton.Save)
        save_button.setText(TEXTO_UI["theme_custom_save"])
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.ui_font_combo.currentFontChanged.connect(self._refresh_preview)
        self.content_font_combo.currentFontChanged.connect(self._refresh_preview)
        self._refresh_preview()

    def _make_font_combo(self, key: str) -> QFontComboBox:
        combo = QFontComboBox(self)
        combo.setCurrentFont(QFont(self._values[key]))
        return combo

    def _choose_color(self, key: str):
        selected = QColorDialog.getColor(
            QColor(self._values[key]),
            self,
            TEXTO_UI[f"theme_color_{key}"],
        )
        if not selected.isValid():
            return
        self._values[key] = selected.name().upper()
        self._render_color_button(key)
        self._refresh_preview()

    def _render_color_button(self, key: str):
        color = QColor(self._values[key])
        foreground = "#111111" if color.lightness() >= 145 else "#FFFFFF"
        button = self._color_buttons[key]
        button.setText(color.name().upper())
        button.setAccessibleName(
            f'{TEXTO_UI[f"theme_color_{key}"]}: {color.name().upper()}'
        )
        button.setStyleSheet(
            f"QPushButton {{ background: {color.name()}; color: {foreground}; "
            "border: 1px solid #777; border-radius: 4px; padding: 4px; }"
        )

    def _current_values(self) -> dict[str, str]:
        values = dict(self._values)
        values["font_ui"] = self.ui_font_combo.currentFont().family()
        values["font_content"] = self.content_font_combo.currentFont().family()
        return normalizar_tema_personalizado(values)

    def _refresh_preview(self, *_):
        theme = obter_tema(
            "personalizado",
            custom_theme=self._current_values(),
        )
        self.preview_frame.setStyleSheet(
            f"QFrame#customThemePreview {{ background: {theme['surface']}; "
            f"border: 1px solid {theme['border']}; border-radius: 6px; }}"
        )
        self.preview_label.setStyleSheet(
            f"color: {theme['text']}; "
            f"font-family: \"{theme['font_ui']}\";"
        )
        self.preview_icon.setStyleSheet(
            f"color: {theme['icon']}; font-size: 24px;"
        )
        self.preview_button.setStyleSheet(
            f"QPushButton {{ background: {theme['accent']}; color: {theme['text']}; "
            f"font-family: \"{theme['font_ui']}\"; border: 1px solid "
            f"{theme['border_strong']}; border-radius: 4px; padding: 6px 10px; }}"
        )

    def custom_theme(self) -> dict[str, str]:
        """Retorna apenas valores validados para salvar no config.json."""
        return self._current_values()
