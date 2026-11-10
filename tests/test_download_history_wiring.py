import ast
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DownloadHistoryWiringTests(unittest.TestCase):
    def test_download_start_status_timeout_is_imported_and_configured(self):
        browser_source = (PROJECT_ROOT / "browser.py").read_text(encoding="utf-8")
        config_source = (
            PROJECT_ROOT / "_CONFIGURA_" / "__init__.py"
        ).read_text(encoding="utf-8")
        self.assertIn("STATUS_DOWNLOAD_INICIO_MS,", browser_source)
        self.assertIn("STATUS_DOWNLOAD_INICIO_MS = 5000", config_source)

    def test_download_history_uses_shared_panel_and_embedded_sidebar_action(self):
        source = (
            (PROJECT_ROOT / "browser.py").read_text(encoding="utf-8")
            + "\n"
            + (
                PROJECT_ROOT
                / "_APP_"
                / "barra_direita_tools"
                / "manager.py"
            ).read_text(encoding="utf-8")
            + "\n"
            + (
                PROJECT_ROOT / "_BROWSER_" / "window_panels.py"
            ).read_text(encoding="utf-8")
        )
        sidebar_source = (
            PROJECT_ROOT
            / "_APP_"
            / "barra_direita_tools"
            / "sidebar.py"
        ).read_text(encoding="utf-8")

        self.assertIn("self.tools_manager.initialize()", source)
        self.assertIn("self._add_panel(parent.downloads_dock)", source)
        self.assertIn(
            "context.sidebar.add_action_button(\n            context.downloads_action",
            source,
        )
        self.assertIn(
            "self.sidebar_toolbar = RightToolsSidebar(\n"
            "            self._body_row,\n"
            "            translate_callback=self.translate_current_page,\n"
            "            icon_size=theme[\"sidebar_icon_size_px\"],\n"
            "        )",
            source,
        )
        self.assertIn(
            "self.addWidget(button)",
            sidebar_source,
        )
        self.assertNotIn("_add_sidebar_action_button", source)
        self.assertIn('"downloads": (', source)
        self.assertIn("self.toggle_browser_downloads", source)
        self.assertIn('self._toggle_side_panel("downloads")', source)
        self.assertIn("ico_video_download()", source)
        self.assertIn("ico_downloads()", source)

    def test_normal_downloads_are_persisted_and_private_ones_stay_in_memory(self):
        source = (
            (PROJECT_ROOT / "browser.py").read_text(encoding="utf-8")
            + "\n"
            + (
                PROJECT_ROOT
                / "_APP_"
                / "barra_direita_tools"
                / "manager.py"
            ).read_text(encoding="utf-8")
            + "\n"
            + (
                PROJECT_ROOT / "_BROWSER_" / "window_panels.py"
            ).read_text(encoding="utf-8")
        )

        self.assertIn("self.storage.record_browser_download(", source)
        self.assertIn("self.storage.update_browser_download(entry_id, status)", source)
        self.assertIn("window.downloads_dock.add_private_download(", source)
        self.assertIn("window.downloads_dock.update_private_download(", source)
        self.assertIn(
            "None if context.private else context.controller.storage",
            source,
        )

    def test_only_accepted_popup_downloads_close_their_source_tab(self):
        source = (PROJECT_ROOT / "browser.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        controller = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef)
            and node.name == "BrowserController"
        )
        methods = {
            node.name: node
            for node in controller.body
            if isinstance(node, ast.FunctionDef)
        }
        request_method = ast.get_source_segment(
            source,
            methods["_on_download_requested"],
        )
        close_method = ast.get_source_segment(
            source,
            methods["_close_popup_download_tab"],
        )
        owner_method = ast.get_source_segment(
            source,
            methods["_window_for_download"],
        )
        window = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef)
            and node.name == "BrowserWindow"
        )
        create_tab = next(
            node
            for node in window.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "_create_tab"
        )
        create_tab_source = ast.get_source_segment(source, create_tab)

        self.assertIn("source_page = download.page()", request_method)
        self.assertLess(
            request_method.index("if not target:"),
            request_method.index("download.accept()"),
        )
        self.assertLess(
            request_method.index("download.accept()"),
            request_method.index(
                "self._close_popup_download_tab(window, source_page)"
            ),
        )
        self.assertLess(
            request_method.index("except sqlite3.Error"),
            request_method.index(
                "self._close_popup_download_tab(window, source_page)"
            ),
        )
        self.assertIn('view.setProperty("downloadPopup", bool(popup))', create_tab_source)
        self.assertIn("if view.property(\"downloadPopup\"):", close_method)
        self.assertIn("window.close_tab(index)", close_method)
        self.assertIn("view.page() == source_page", owner_method)

    def test_download_progress_updates_the_existing_panel_and_final_states(self):
        browser_source = (PROJECT_ROOT / "browser.py").read_text(encoding="utf-8")
        panel_source = (
            PROJECT_ROOT
            / "_APP_"
            / "barra_direita_tools"
            / "browser_downloads.py"
        ).read_text(encoding="utf-8")
        config_source = (
            PROJECT_ROOT / "_CONFIGURA_" / "__init__.py"
        ).read_text(encoding="utf-8")

        self.assertIn("download.receivedBytesChanged.connect", browser_source)
        self.assertIn("download.totalBytesChanged.connect", browser_source)
        self.assertIn("window.downloads_dock.update_download_progress(", browser_source)
        self.assertIn("QProgressBar", panel_source)
        self.assertIn("def update_download_progress(", panel_source)
        self.assertIn('"browser_download_state_completed": "Concluído"', config_source)
        self.assertIn('"browser_download_state_cancelled": "Cancelado"', config_source)
        self.assertIn('"browser_download_state_interrupted": "Falhou"', config_source)

    def test_navigation_history_has_a_separate_right_sidebar_button(self):
        source = (
            (PROJECT_ROOT / "browser.py").read_text(encoding="utf-8")
            + "\n"
            + (
                PROJECT_ROOT
                / "_APP_"
                / "barra_direita_tools"
                / "manager.py"
            ).read_text(encoding="utf-8")
        )

        self.assertIn(
            "self.context.sidebar.add_action_button(\n            self.context.history_action",
            source,
        )
        self.assertIn('"historyButton"', source)
        self.assertNotIn("_add_sidebar_action_button", source)
        self.assertIn('atalho("historico")', source)
        self.assertIn("self.history_action.setEnabled(not self.private)", source)

    def test_message_boxes_are_created_through_the_shared_popup_module(self):
        forbidden_calls = {"warning", "information", "question", "critical", "about"}
        offenders = []
        for path in PROJECT_ROOT.rglob("*.py"):
            if path == PROJECT_ROOT / "_ULTILIDADES_" / "popups.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not isinstance(
                    node.func, ast.Attribute
                ):
                    continue
                owner = node.func.value
                if (
                    node.func.attr in forbidden_calls
                    and isinstance(owner, ast.Name)
                    and owner.id == "QMessageBox"
                ):
                    offenders.append(f"{path.relative_to(PROJECT_ROOT)}:{node.lineno}")

        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
