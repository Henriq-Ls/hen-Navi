"""Diálogo de ajuda com os atalhos registrados no _CONFIGURA_."""

from _CONFIGURA_ import (
    ALTURA_DIALOGO_PADRAO,
    ATALHOS,
    LARGURA_DIALOGO_PADRAO,
    TEXTO_UI,
)
from PySide6.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


_CATEGORIAS = ("Abas", "Navegação", "Ferramentas", "Janelas", "Página")


class ShortcutsDialog(QDialog):
    """Mostra a lista de atalhos diretamente a partir da configuração central."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(TEXTO_UI["keyboard_shortcuts"])
        self.resize(LARGURA_DIALOGO_PADRAO, ALTURA_DIALOGO_PADRAO)

        content = QWidget(self)
        content_layout = QVBoxLayout(content)
        for category in _CATEGORIAS:
            shortcuts = [
                item for item in ATALHOS if item["categoria"] == category
            ]
            if not shortcuts:
                continue
            group = QGroupBox(category, content)
            group_layout = QVBoxLayout(group)
            for item in shortcuts:
                row = QHBoxLayout()
                key = QLabel(item["atalho"], group)
                key.setObjectName("shortcutKey")
                description = QLabel(item["descricao"], group)
                description.setWordWrap(True)
                row.addWidget(key)
                row.addWidget(description, 1)
                group_layout.addLayout(row)
            content_layout.addWidget(group)
        content_layout.addStretch(1)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        layout = QVBoxLayout(self)
        layout.addWidget(scroll)

