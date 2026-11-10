# _APP_/main_window.py
"""Janela principal do navegador integrada ao template PySide6."""

import os

from _CONFIGURA_ import (
    ALTURA_PADRAO,
    ALTURA_MIN,
    IMAGEM_ICO,
    LARGURA_PADRAO,
    LARGURA_MIN,
    TITULO_APP,
    TEXTO_UI,
    VERSAO_APP,
    VERSAO_ESTADO_JANELA,
)
from _LOGS_ import log
from _APPDATA_ import appdata
from PySide6.QtCore import QByteArray
from PySide6.QtGui import QIcon

from browser import AnonymousProfileLease, BrowserController, BrowserWindow


class MainWindow(BrowserWindow):
    """Adapta a janela do navegador à geometria e ao tema do template."""

    def __init__(
        self,
        controller: BrowserController,
        *,
        private: bool = False,
        restore_urls: list[str] | None = None,
        profile_lease: AnonymousProfileLease | None = None,
        parent=None,
    ):
        super().__init__(
            controller,
            private=private,
            restore_urls=restore_urls,
            profile_lease=profile_lease,
            parent=parent,
        )
        suffix = TEXTO_UI["private_suffix"] if private else ""
        self.setWindowTitle(f"{TITULO_APP}{suffix} {VERSAO_APP}")
        self.setMinimumSize(LARGURA_MIN, ALTURA_MIN)
        self.resize(LARGURA_PADRAO, ALTURA_PADRAO)
        if os.path.isfile(IMAGEM_ICO):
            self.setWindowIcon(QIcon(IMAGEM_ICO))
        self._restore_window_state()
        log.ok("MainWindow", "__init__", "janela do navegador pronta")

    def _restore_window_state(self):
        saved = appdata.ler_sessao()
        try:
            geometry = saved.get("geometria")
            state = saved.get("estado")
            if geometry:
                self.restoreGeometry(QByteArray.fromBase64(geometry.encode()))
            if state:
                self.restoreState(
                    QByteArray.fromBase64(state.encode()),
                    VERSAO_ESTADO_JANELA,
                )
        except (TypeError, ValueError, RuntimeError) as error:
            log.aviso("MainWindow", "_restore_window_state", str(error))

    def _save_window_state(self):
        if self.private:
            return
        try:
            state = {
                "geometria": self.saveGeometry().toBase64().data().decode(),
                "estado": self.saveState(VERSAO_ESTADO_JANELA)
                .toBase64()
                .data()
                .decode(),
            }
            appdata.salvar_sessao(state)
        except (AttributeError, RuntimeError, ValueError) as error:
            log.erro("MainWindow", "_save_window_state", str(error))

    def closeEvent(self, event):
        self._save_window_state()
        super().closeEvent(event)
