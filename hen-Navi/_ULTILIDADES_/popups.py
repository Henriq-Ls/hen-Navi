# _ULTILIDADES_/popups.py
"""
Diálogos padronizados do projeto.

Todos usam o estilo escuro definido em _CONFIGURA_.

Uso:
    from _ULTILIDADES_.popups import popup_erro, popup_aviso, popup_confirmar, popup_info

    popup_erro("Título", "Mensagem de erro detalhada.")
    popup_aviso("Atenção", "Algo suspeito aconteceu.")
    popup_info("Info", "Operação concluída.")

    if popup_confirmar("Confirmar", "Deseja realmente excluir?"):
        fazer_exclusao()
"""

from PySide6.QtWidgets import QApplication, QMessageBox, QWidget
from _CONFIGURA_ import TEXTO_UI


_BUTTON_LABELS = {
    QMessageBox.StandardButton.Ok: "ok",
    QMessageBox.StandardButton.Yes: "yes",
    QMessageBox.StandardButton.No: "no",
    QMessageBox.StandardButton.Cancel: "cancel",
    QMessageBox.StandardButton.Close: "close",
}


def criar_popup(
    titulo: str,
    mensagem: str,
    parent: QWidget = None,
    *,
    icone: QMessageBox.Icon = QMessageBox.Icon.Information,
    botoes: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
    botao_padrao: QMessageBox.StandardButton | None = None,
) -> QMessageBox:
    """Cria um QMessageBox usando o tema, os textos e os padrões do projeto."""
    dialog = QMessageBox(icone, titulo, mensagem, botoes, parent)

    stylesheet = parent.styleSheet() if parent is not None else ""
    if not stylesheet:
        app = QApplication.instance()
        stylesheet = app.styleSheet() if app is not None else ""
    if stylesheet:
        dialog.setStyleSheet(stylesheet)

    for standard_button, text_key in _BUTTON_LABELS.items():
        button = dialog.button(standard_button)
        if button is not None and text_key in TEXTO_UI:
            button.setText(TEXTO_UI[text_key])
    if botao_padrao is not None:
        dialog.setDefaultButton(botao_padrao)
    return dialog


def popup_erro(titulo: str, mensagem: str, parent: QWidget = None):
    """Exibe diálogo de erro modal."""
    criar_popup(
        titulo,
        mensagem,
        parent,
        icone=QMessageBox.Icon.Critical,
    ).exec()


def popup_aviso(titulo: str, mensagem: str, parent: QWidget = None):
    """Exibe diálogo de aviso modal."""
    criar_popup(
        titulo,
        mensagem,
        parent,
        icone=QMessageBox.Icon.Warning,
    ).exec()


def popup_info(titulo: str, mensagem: str, parent: QWidget = None):
    """Exibe diálogo informativo modal."""
    criar_popup(titulo, mensagem, parent).exec()


def popup_pergunta(
    titulo: str,
    mensagem: str,
    parent: QWidget = None,
    *,
    botoes: QMessageBox.StandardButton = (
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    ),
    botao_padrao: QMessageBox.StandardButton = QMessageBox.StandardButton.No,
) -> QMessageBox.StandardButton:
    """Exibe uma pergunta padronizada e retorna o botão selecionado."""
    dialog = criar_popup(
        titulo,
        mensagem,
        parent,
        icone=QMessageBox.Icon.Question,
        botoes=botoes,
        botao_padrao=botao_padrao,
    )
    return QMessageBox.StandardButton(dialog.exec())


def popup_confirmar(
    titulo: str,
    mensagem: str,
    parent: QWidget = None,
    btn_ok: str | None = None,
    btn_cancelar: str | None = None,
) -> bool:
    """
    Exibe diálogo de confirmação.
    Retorna True se o usuário confirmou, False se cancelou.
    """
    dlg = criar_popup(
        titulo,
        mensagem,
        parent,
        icone=QMessageBox.Icon.Question,
        botoes=QMessageBox.StandardButton.NoButton,
    )

    btn_sim = dlg.addButton(
        btn_ok or TEXTO_UI["confirm"],
        QMessageBox.ButtonRole.AcceptRole,
    )
    dlg.addButton(
        btn_cancelar or TEXTO_UI["cancel"],
        QMessageBox.ButtonRole.RejectRole,
    )
    dlg.setDefaultButton(btn_sim)

    dlg.exec()

    return dlg.clickedButton() == btn_sim


def popup_confirmar_perigo(
    titulo: str,
    mensagem: str,
    parent: QWidget = None
) -> bool:
    """
    Diálogo de confirmação para ações destrutivas (excluir, apagar, resetar).
    Botão de confirmação em vermelho.
    """
    dlg = criar_popup(
        titulo,
        mensagem,
        parent,
        icone=QMessageBox.Icon.Warning,
        botoes=QMessageBox.StandardButton.NoButton,
    )

    btn_sim = dlg.addButton(TEXTO_UI["confirm"], QMessageBox.ButtonRole.AcceptRole)
    btn_sim.setObjectName("dangerButton")
    dlg.addButton(TEXTO_UI["cancel"], QMessageBox.ButtonRole.RejectRole)

    dlg.exec()

    return dlg.clickedButton() == btn_sim
