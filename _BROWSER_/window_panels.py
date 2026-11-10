"""Coordenação dos painéis laterais da janela do navegador."""

from __future__ import annotations

from PySide6.QtWidgets import QDockWidget


class BrowserWindowPanelsMixin:
    """Comportamentos de alternância e sincronização dos painéis laterais."""

    def _add_side_panel(self, panel):
        """Adiciona um painel ao card lateral sem uma segunda barra de título."""
        if isinstance(panel, QDockWidget):
            panel.setTitleBarWidget(None)
        self._side_panel_stack.addWidget(panel)

    def _toggle_performance_panel(self, *_):
        if hasattr(self, "tools_manager"):
            self.tools_manager.toggle_performance_panel()

    def translate_current_page(self, *_):
        if self._current_view() is None:
            return
        if (
            self._active_side_panel != "ai"
            or not self._side_panel_container.isVisible()
        ):
            self._toggle_side_panel("ai")
        else:
            self._refresh_ai_provider()
            self.ai_dock.set_context_key(
                self._ai_context_key(self._current_view())
            )
        self.ai_dock.request_translation()

    def _toggle_side_panel(self, panel_name: str):
        if panel_name in {"notes", "video", "inspector", "devtools", "ai"}:
            if self._current_view() is None:
                return
        panels = {
            "notes": (self.notes_dock, getattr(self, "notes_action", None)),
            "video": (
                self.video_download_dock,
                getattr(self, "video_download_action", None),
            ),
            "downloads": (
                self.downloads_dock,
                getattr(self, "downloads_action", None),
            ),
            "inspector": (
                self.inspector_dock,
                getattr(self, "inspect_action", None),
            ),
            "devtools": (
                self.devtools_panel,
                getattr(self, "devtools_action", None),
            ),
            "ai": (
                self.ai_dock,
                getattr(self, "ai_action", None),
            ),
            "performance": (
                self.performance_panel,
                getattr(self, "performance_action", None),
            ),
        }
        panel, _action = panels[panel_name]
        if panel is None:
            return

        if (
            self._active_side_panel == panel_name
            and self._side_panel_container.isVisible()
        ):
            self._side_panel_container.hide()
            self._active_side_panel = None
        else:
            self._active_side_panel = panel_name
            self._side_panel_stack.setCurrentWidget(panel)
            self._side_panel_title.setText(panel.windowTitle())
            self._side_panel_container.show()

        if panel_name == "ai" and self._active_side_panel == "ai":
            self._refresh_ai_provider()
            view = self._current_view()
            self.ai_dock.set_context_key(self._ai_context_key(view))
        elif panel_name == "downloads" and self._active_side_panel == "downloads":
            self.downloads_dock.refresh()

        self._sync_devtools_page()

        if self.performance_panel is not None:
            if (
                self._active_side_panel == "performance"
                and self._side_panel_container.isVisible()
            ):
                self.performance_panel.start_monitoring()
            else:
                self.performance_panel.stop_monitoring()

        for name, (_widget, action) in panels.items():
            if action is not None:
                action.setChecked(name == self._active_side_panel)

    def _close_side_panel(self, *_):
        self._side_panel_container.hide()
        self._side_panel_title.clear()
        self._active_side_panel = None
        self._sync_devtools_page()
        if self.performance_panel is not None:
            self.performance_panel.stop_monitoring()
        for action_name in (
            "notes_action",
            "video_download_action",
            "downloads_action",
            "inspect_action",
            "devtools_action",
            "ai_action",
            "performance_action",
        ):
            action = getattr(self, action_name, None)
            if action is not None:
                action.setChecked(False)

    def _on_inspector_visibility_changed(self, visible: bool):
        if not visible:
            return
        view = self._current_view()
        if view is None:
            return
        self.inspector_dock.set_page(view.page() if view else None)
        self.inspector_dock.refresh_dom()

    def toggle_video_download_dock(self, *_):
        self._toggle_side_panel("video")

    def toggle_browser_downloads(self, *_):
        self._toggle_side_panel("downloads")

    def _on_video_download_visibility_changed(self, visible: bool):
        if not visible or not self.video_download_dock:
            return
        view = self._current_view()
        if view is None:
            return
        url = view.url().toString()
        self.video_download_dock.set_source_url(url)
        self.video_download_dock.analyze_link()
