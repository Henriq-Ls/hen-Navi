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

    def test_download_history_uses_shared_side_panel_and_right_toolbar_action(self):
        source = (PROJECT_ROOT / "browser.py").read_text(encoding="utf-8")

        self.assertIn("self._create_browser_downloads_dock()", source)
        self.assertIn(
            "self._side_panel_stack.addWidget(self.downloads_dock)",
            source,
        )
        self.assertIn(
            'self._add_sidebar_action_button(self.downloads_action)',
            source,
        )
        self.assertIn('"downloads": (', source)
        self.assertIn("self.toggle_browser_downloads", source)
        self.assertIn('self._toggle_side_panel("downloads")', source)
        self.assertIn("ico_video_download()", source)
        self.assertIn("ico_downloads()", source)

    def test_normal_downloads_are_persisted_and_private_ones_stay_in_memory(self):
        source = (PROJECT_ROOT / "browser.py").read_text(encoding="utf-8")

        self.assertIn("self.storage.record_browser_download(", source)
        self.assertIn("self.storage.update_browser_download(entry_id, status)", source)
        self.assertIn("window.downloads_dock.add_private_download(", source)
        self.assertIn("window.downloads_dock.update_private_download(", source)
        self.assertIn("None if self.private else self.controller.storage", source)

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
