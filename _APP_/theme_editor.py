"""Editor visual para as cores e fontes do tema personalizado."""

from PySide6.QtCore import Signal
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
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from _CONFIGURA_ import (
    CHAVES_CORES_PERSONALIZADAS,
    CHAVES_FONTES_PERSONALIZADAS,
    CHAVES_METRICAS_PERSONALIZADAS,
    TEXTO_UI,
)
from _CONFIGURA_.theme_engine import normalizar_tema_personalizado, obter_tema


class CustomThemeDialog(QDialog):
    """Permite editar e salvar cores, fontes e tamanhos do tema."""

    saveRequested = Signal(object)

    def __init__(self, initial_theme: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(TEXTO_UI["theme_custom_title"])
        self.setMinimumSize(620, 620)
        self.resize(700, 720)

        base_theme = obter_tema("personalizado", custom_theme=initial_theme)
        self._values = {
            key: base_theme[key]
            for key in (
                *CHAVES_CORES_PERSONALIZADAS,
                *CHAVES_FONTES_PERSONALIZADAS,
                *CHAVES_METRICAS_PERSONALIZADAS,
            )
        }
        self._color_buttons: dict[str, QPushButton] = {}
        self._metric_spins: dict[str, QSpinBox] = {}

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

        metrics_group = QGroupBox(
            TEXTO_UI["theme_custom_metrics"],
            self,
        )
        metrics_grid = QGridLayout(metrics_group)
        metrics = (
            ("font_size_px", 10, 24),
            ("tab_height_px", 24, 48),
            ("sidebar_icon_size_px", 14, 24),
            ("footer_height_px", 26, 42),
        )
        for index, (key, minimum, maximum) in enumerate(metrics):
            row, column = divmod(index, 2)
            label = QLabel(TEXTO_UI[f"theme_custom_{key.removesuffix('_px')}"])
            spin = self._make_metric_spin(key, minimum, maximum)
            metrics_grid.addWidget(label, row, column * 2)
            metrics_grid.addWidget(spin, row, column * 2 + 1)
        metrics_hint = QLabel(
            TEXTO_UI["theme_custom_metrics_hint"],
            metrics_group,
        )
        metrics_hint.setWordWrap(True)
        metrics_grid.addWidget(metrics_hint, 2, 0, 1, 4)
        layout.addWidget(metrics_group)

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
        save_button.clicked.connect(self._save_and_continue)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        self.save_status = QLabel("", self)
        layout.insertWidget(layout.count() - 1, self.save_status)

        self.ui_font_combo.currentFontChanged.connect(self._refresh_preview)
        self.content_font_combo.currentFontChanged.connect(self._refresh_preview)
        for spin in self._metric_spins.values():
            spin.valueChanged.connect(self._refresh_preview)
        self._refresh_preview()

    def _make_font_combo(self, key: str) -> QFontComboBox:
        combo = QFontComboBox(self)
        combo.setCurrentFont(QFont(self._values[key]))
        return combo

    def _make_metric_spin(
        self,
        key: str,
        minimum: int,
        maximum: int,
    ) -> QSpinBox:
        spin = QSpinBox(self)
        spin.setRange(minimum, maximum)
        spin.setSuffix(" px")
        spin.setValue(int(self._values[key]))
        self._metric_spins[key] = spin
        return spin

    def _save_and_continue(self):
        self.saveRequested.emit(self.custom_theme())
        self.save_status.setText(TEXTO_UI["theme_custom_saved"])

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

    def _current_values(self) -> dict[str, str | int]:
        values = dict(self._values)
        values["font_ui"] = self.ui_font_combo.currentFont().family()
        values["font_content"] = self.content_font_combo.currentFont().family()
        values.update({
            key: spin.value()
            for key, spin in self._metric_spins.items()
        })
        return normalizar_tema_personalizado(values)

    def _refresh_preview(self, *_):
        if hasattr(self, "save_status"):
            self.save_status.clear()
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
            f"font-family: \"{theme['font_ui']}\"; "
            f"font-size: {theme['font_size_px']}px;"
        )
        self.preview_icon.setStyleSheet(
            f"color: {theme['icon']}; "
            f"font-size: {theme['sidebar_icon_size_px'] + 6}px;"
        )
        self.preview_button.setStyleSheet(
            f"QPushButton {{ background: {theme['accent']}; color: {theme['text']}; "
            f"font-family: \"{theme['font_ui']}\"; "
            f"font-size: {theme['font_size_px']}px; border: 1px solid "
            f"{theme['border_strong']}; border-radius: 4px; padding: 6px 10px; }}"
        )
        self.preview_frame.setMinimumHeight(
            max(theme["footer_height_px"], theme["font_size_px"] + 12)
        )

    def custom_theme(self) -> dict[str, str | int]:
        """Retorna apenas valores validados para salvar no config.json."""
        return self._current_values()
