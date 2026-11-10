"""Barra vertical de ações da página, ferramentas e manutenção."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QToolBar,
    QToolButton,
    QSizePolicy,
    QWidget,
)

from _CONFIGURA_ import LARGURA_BARRA_CONTROLES_JANELA, TEXTO_UI
from _ULTILIDADES_.icones import (
    ico_anotacoes,
    ico_captura,
    ico_ia,
    ico_traduzir,
    ico_video_download,
)


class RightToolsSidebar(QToolBar):
    """Cria e mantém os controles próprios da barra vertical direita."""

    BUTTON_SIZE = 26
    ICON_SIZE = 18

    def __init__(
        self,
        parent=None,
        *,
        translate_callback,
        icon_size: int = ICON_SIZE,
    ):
        super().__init__(parent)
        self._translate_callback = translate_callback
        self.setObjectName("browserSidebarToolbar")
        self.setOrientation(Qt.Orientation.Vertical)
        self.setMovable(False)
        self.setFloatable(False)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Expanding,
        )
        self.icon_size = self.ICON_SIZE
        self.button_size = self.BUTTON_SIZE
        self.apply_metrics(icon_size, update_buttons=False)
        self._create_page_buttons()

    def apply_metrics(self, icon_size: int, *, update_buttons: bool = True) -> None:
        """Aumenta ícones e coluna juntos sem cortar os botões."""
        self.icon_size = max(14, int(icon_size))
        self.button_size = max(self.BUTTON_SIZE - 4, self.icon_size + 8)
        width_from_icon = (
            LARGURA_BARRA_CONTROLES_JANELA
            + self.icon_size
            - self.ICON_SIZE
        )
        self.setFixedWidth(max(width_from_icon, self.button_size + 8))
        self.setIconSize(QSize(self.icon_size, self.icon_size))
        if not update_buttons:
            return
        for button in self.findChildren(QToolButton):
            button.setIconSize(QSize(self.icon_size, self.icon_size))
            button.setFixedSize(QSize(self.button_size, self.button_size))

    def _create_page_buttons(self) -> None:
        self.capture_button = self._add_page_button(
            "captureButton",
            ico_captura(),
            TEXTO_UI["capture_menu"],
            accessible_name=TEXTO_UI["capture_menu"],
            instant_popup=True,
        )
        self.video_download_button = self._add_page_button(
            "videoDownloadButton",
            ico_video_download(),
            TEXTO_UI["video_download_button"],
            accessible_name=TEXTO_UI["video_download_button"],
        )
        self.notes_button = self._add_page_button(
            "notesButton",
            ico_anotacoes(),
            TEXTO_UI["notes_title"],
            accessible_name=TEXTO_UI["notes_title"],
        )
        self.ai_button = self._add_page_button(
            "aiButton",
            ico_ia(),
            TEXTO_UI["ai_placeholder"],
            accessible_name=TEXTO_UI["ai_placeholder"],
        )
        self.translate_button = self._add_page_button(
            "translateButton",
            ico_traduzir(),
            TEXTO_UI["translate_page"],
            self._translate_callback,
            accessible_name=TEXTO_UI["translate_page"],
        )
        self.addSeparator()

    def _add_page_button(
        self,
        object_name: str,
        icon,
        tooltip: str,
        callback=None,
        *,
        icon_size: int | None = None,
        accessible_name: str | None = None,
        checkable: bool = False,
        text: str | None = None,
        button_style: Qt.ToolButtonStyle | None = None,
        instant_popup: bool = False,
        fixed_width: bool = True,
    ) -> QToolButton:
        button = QToolButton(self)
        button.setObjectName(object_name)
        button.setIcon(icon)
        icon_size = self.icon_size if icon_size is None else icon_size
        button.setIconSize(QSize(icon_size, icon_size))
        button.setToolTip(tooltip)
        if accessible_name:
            button.setAccessibleName(accessible_name)
        if button_style is not None:
            button.setToolButtonStyle(button_style)
        if checkable:
            button.setCheckable(True)
        if text is not None:
            button.setText(text)
        if instant_popup:
            button.setPopupMode(
                QToolButton.ToolButtonPopupMode.InstantPopup
            )
        if fixed_width:
            button.setFixedSize(QSize(self.button_size, self.button_size))
        else:
            button.setFixedHeight(self.button_size)
        if callback is not None:
            button.clicked.connect(callback)
        self.addWidget(button)
        return button

    def add_action_button(
        self,
        action,
        object_name: str,
        *,
        icon_size: int | None = None,
        button_size: int | None = None,
        at_top: bool = False,
    ) -> QToolButton:
        """Exibe uma ação existente sem criar outra conexão ou comando."""
        button = QToolButton(self)
        button.setObjectName(object_name)
        button.setDefaultAction(action)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        icon_size = self.icon_size if icon_size is None else icon_size
        button_size = self.button_size if button_size is None else button_size
        button.setIconSize(QSize(icon_size, icon_size))
        button.setFixedSize(QSize(button_size, button_size))
        button.setAccessibleName(action.text())
        button.setToolTip(action.toolTip())
        button.setAutoRaise(True)
        if at_top and self.actions():
            self.insertWidget(self.actions()[0], button)
        else:
            self.addWidget(button)
        return button

    def finish_layout(
        self,
        bottom_actions: tuple[tuple[object, str], ...],
    ) -> tuple[QToolButton, ...]:
        """Coloca ações de manutenção no rodapé após o espaço expansível."""
        spacer = QWidget(self)
        spacer.setObjectName("sidebarBottomSpacer")
        spacer.setSizePolicy(
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Expanding,
        )
        self.addWidget(spacer)

        self.addSeparator()
        buttons = tuple(
            self.add_action_button(action, object_name)
            for action, object_name in bottom_actions
        )
        return buttons
