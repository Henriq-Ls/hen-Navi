"""Coordena a criação e a ligação dos painéis da barra direita."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from _CONFIGURA_ import TEXTO_UI, atalho
from _APP_.barra_direita_tools.ai_assistant import AiAssistantDock
from _APP_.barra_direita_tools.anotacoes import NotesDock
from _APP_.barra_direita_tools.browser_downloads import BrowserDownloadsDock
from _APP_.barra_direita_tools.captura import CaptureManager
from _APP_.barra_direita_tools.devtools import DevToolsPanel
from _APP_.barra_direita_tools.download_video import VideoDownloadDock
from _APP_.inspector import PageInspectorDock
from _APP_.barra_direita_tools.performance import PerformancePanel
from _ULTILIDADES_.icones import (
    ico_anotacoes,
    ico_ferramentas,
    ico_ia,
    ico_info,
    ico_inspecionar,
    ico_video_download,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QDockWidget, QMenu, QStackedWidget, QWidget


@dataclass(frozen=True)
class RightToolsContext:
    """Dependências explícitas fornecidas pela janela do navegador."""

    parent: QWidget
    controller: object
    profile: object
    private: bool
    panel_stack: QStackedWidget
    sidebar: object
    notes_button: object
    video_download_button: object
    ai_button: object
    history_action: QAction
    downloads_action: QAction
    security_performance_menu: QMenu
    callbacks: Mapping[str, Callable]


class RightToolsManager:
    """Instancia painéis, cria ações e conecta eventos das ferramentas."""

    def __init__(self, context: RightToolsContext):
        self.context = context
        self.performance_panel = None
        self.capture_manager = None

    def initialize(self) -> None:
        self._create_capture_manager()
        self._create_notes()
        self._create_video_download()
        self.context.sidebar.add_action_button(
            self.context.history_action,
            "historyButton",
        )
        self._create_downloads()
        self._create_inspector()
        self._create_devtools()
        self._create_ai()
        self._create_performance_action()

    def _create_capture_manager(self) -> None:
        parent = self.context.parent
        self.capture_manager = CaptureManager(parent)
        parent.capture_manager = self.capture_manager
        self.capture_manager.imageSaved.connect(
            self._callback("capture_image_saved")
        )
        self.capture_manager.pdfSaved.connect(
            self._callback("capture_pdf_saved")
        )
        self.capture_manager.failed.connect(
            self._callback("capture_failed")
        )

    def _callback(self, name: str) -> Callable:
        try:
            return self.context.callbacks[name]
        except KeyError as error:
            raise ValueError(f"Callback obrigatório ausente: {name}") from error

    def _add_panel(self, panel: QWidget) -> None:
        if isinstance(panel, QDockWidget):
            panel.setTitleBarWidget(None)
        self.context.panel_stack.addWidget(panel)

    def _create_notes(self) -> None:
        context = self.context
        parent = context.parent
        if context.private:
            parent.notes_dock = None
            parent.notes_action = QAction(TEXTO_UI["notes_title"], parent)
            parent.notes_action.setIcon(ico_anotacoes())
            parent.notes_action.setEnabled(False)
            parent.notes_action.setToolTip(TEXTO_UI["notes_private_unavailable"])
        else:
            parent.notes_dock = NotesDock(
                context.controller.storage,
                context.panel_stack,
            )
            parent.notes_dock.setFeatures(
                QDockWidget.DockWidgetFeature.NoDockWidgetFeatures
            )
            self._add_panel(parent.notes_dock)
            parent.notes_dock.hide()
            parent.notes_dock.openHostRequested.connect(
                self._callback("open_note_host")
            )
            parent.notes_dock.noteChanged.connect(
                self._callback("note_indicator_changed")
            )
            parent.notes_action = QAction(
                ico_anotacoes(),
                TEXTO_UI["notes_title"],
                parent,
            )
            parent.notes_action.setCheckable(True)
            parent.notes_action.setShortcut(QKeySequence(atalho("anotacoes")))
            parent.notes_action.setShortcutContext(
                Qt.ShortcutContext.WindowShortcut
            )
            parent.notes_action.triggered.connect(
                lambda _checked=False: self._callback("toggle_side_panel")(
                    "notes"
                )
            )
        context.notes_button.setDefaultAction(parent.notes_action)

    def _create_video_download(self) -> None:
        context = self.context
        parent = context.parent
        parent.video_download_dock = VideoDownloadDock(context.panel_stack)
        parent.video_download_dock.setFeatures(
            QDockWidget.DockWidgetFeature.NoDockWidgetFeatures
        )
        self._add_panel(parent.video_download_dock)
        parent.video_download_dock.hide()
        parent.video_download_dock.visibilityChanged.connect(
            self._callback("video_visibility_changed")
        )
        parent.video_download_action = QAction(
            ico_video_download(),
            TEXTO_UI["video_download_button"],
            parent,
        )
        parent.video_download_action.setCheckable(True)
        parent.video_download_action.setToolTip(
            TEXTO_UI["video_download_button"]
        )
        parent.video_download_action.triggered.connect(
            lambda _checked=False: self._callback("toggle_side_panel")("video")
        )
        context.video_download_button.setDefaultAction(
            parent.video_download_action
        )

    def _create_downloads(self) -> None:
        context = self.context
        parent = context.parent
        parent.downloads_dock = BrowserDownloadsDock(
            None if context.private else context.controller.storage,
            private=context.private,
            parent=context.panel_stack,
        )
        parent.downloads_dock.setFeatures(
            QDockWidget.DockWidgetFeature.NoDockWidgetFeatures
        )
        self._add_panel(parent.downloads_dock)
        parent.downloads_dock.hide()
        context.sidebar.add_action_button(
            context.downloads_action,
            "browserDownloadsButton",
        )

    def _create_inspector(self) -> None:
        context = self.context
        parent = context.parent
        parent.inspector_dock = PageInspectorDock(context.panel_stack)
        parent.inspector_dock.setFeatures(
            QDockWidget.DockWidgetFeature.NoDockWidgetFeatures
        )
        self._add_panel(parent.inspector_dock)
        parent.inspector_dock.hide()
        parent.inspector_dock.visibilityChanged.connect(
            self._callback("inspector_visibility_changed")
        )
        parent.inspect_action = QAction(
            ico_inspecionar(),
            TEXTO_UI["inspect_page"],
            parent,
        )
        parent.inspect_action.setCheckable(True)
        parent.inspect_action.setToolTip(TEXTO_UI["inspect_page"])
        parent.inspect_action.triggered.connect(
            lambda _checked=False: self._callback("toggle_side_panel")(
                "inspector"
            )
        )
        context.sidebar.add_action_button(
            parent.inspect_action,
            "inspectPageButton",
        )
        view = self._callback("current_view")()
        parent.inspector_dock.set_page(view.page() if view else None)

    def _create_devtools(self) -> None:
        context = self.context
        parent = context.parent
        parent.devtools_panel = DevToolsPanel(
            context.profile,
            context.panel_stack,
        )
        self._add_panel(parent.devtools_panel)
        parent.devtools_panel.hide()
        parent.devtools_action = QAction(
            ico_ferramentas(),
            TEXTO_UI["devtools_action"],
            parent,
        )
        parent.devtools_action.setCheckable(True)
        parent.devtools_action.setToolTip(TEXTO_UI["devtools_action"])
        parent.devtools_action.triggered.connect(
            lambda _checked=False: self._callback("toggle_side_panel")(
                "devtools"
            )
        )
        context.sidebar.add_action_button(
            parent.devtools_action,
            "developerToolsButton",
        )

    def _create_ai(self) -> None:
        context = self.context
        parent = context.parent
        parent.ai_dock = AiAssistantDock(context.panel_stack)
        parent.ai_dock.setFeatures(
            QDockWidget.DockWidgetFeature.NoDockWidgetFeatures
        )
        self._add_panel(parent.ai_dock)
        parent.ai_dock.hide()
        parent.ai_dock.requestRequested.connect(
            self._callback("handle_ai_request")
        )
        parent.ai_dock.cancelRequested.connect(
            self._callback("cancel_ai_request")
        )
        parent.ai_dock.settingsRequested.connect(
            self._callback("open_ai_settings")
        )
        parent.ai_action = QAction(
            ico_ia(),
            TEXTO_UI["ai_placeholder"],
            parent,
        )
        parent.ai_action.setCheckable(True)
        parent.ai_action.setShortcut(QKeySequence(atalho("assistente_ia")))
        parent.ai_action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        parent.ai_action.setToolTip(TEXTO_UI["ai_placeholder"])
        parent.ai_action.triggered.connect(
            lambda _checked=False: self._callback("toggle_side_panel")("ai")
        )
        parent.addAction(parent.ai_action)
        context.ai_button.setDefaultAction(parent.ai_action)
        self._callback("refresh_ai_provider")()

    def _create_performance_action(self) -> None:
        context = self.context
        parent = context.parent
        parent.performance_action = QAction(
            ico_info(),
            TEXTO_UI["performance_panel_title"],
            parent,
        )
        parent.performance_action.setCheckable(True)
        parent.performance_action.setToolTip(
            TEXTO_UI["performance_panel_title"]
        )
        parent.performance_action.triggered.connect(
            self.toggle_performance_panel
        )
        context.security_performance_menu.addAction(
            parent.performance_action
        )
        context.security_performance_menu.addSeparator()
        context.sidebar.add_action_button(
            parent.performance_action,
            "performanceMonitorButton",
            at_top=True,
        )

    def toggle_performance_panel(self, *_args) -> None:
        context = self.context
        parent = context.parent
        if self.performance_panel is None:
            self.performance_panel = PerformancePanel(
                context.controller.performance_monitor,
                self._callback("open_gpu_diagnostic"),
                context.panel_stack,
            )
            parent.performance_panel = self.performance_panel
            self._add_panel(self.performance_panel)
            self.performance_panel.hide()
        self._callback("toggle_side_panel")("performance")
