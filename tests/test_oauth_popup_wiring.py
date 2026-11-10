import ast
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class OAuthPopupWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (PROJECT_ROOT / "browser.py").read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        cls.classes = {
            node.name: node
            for node in cls.tree.body
            if isinstance(node, ast.ClassDef)
        }
        cls.page_source = (
            PROJECT_ROOT / "_BROWSER_" / "page.py"
        ).read_text(encoding="utf-8")
        page_tree = ast.parse(cls.page_source)
        cls.page_class = next(
            node
            for node in page_tree.body
            if isinstance(node, ast.ClassDef) and node.name == "BrowserPage"
        )

    def _method_source(self, class_name, method_name):
        class_node = self.classes[class_name]
        method = next(
            node
            for node in class_node.body
            if isinstance(node, ast.FunctionDef) and node.name == method_name
        )
        return ast.get_source_segment(self.source, method)

    def test_page_forwards_requested_window_type(self):
        method = next(
            node
            for node in self.page_class.body
            if isinstance(node, ast.FunctionDef) and node.name == "createWindow"
        )
        source = ast.get_source_segment(self.page_source, method)
        self.assertIn(
            "self.browser_window._create_popup_page(window_type)",
            source,
        )

    def test_popup_windows_keep_profile_and_close_with_web_page(self):
        source = self._method_source("BrowserWindow", "_create_popup_page")
        self.assertIn("window_types.WebBrowserWindow", source)
        self.assertIn("window_types.WebDialog", source)
        self.assertIn("BrowserPage(\n                self.profile", source)
        self.assertIn("page.windowCloseRequested.connect(popup_window.close)", source)
        self.assertIn("self._forget_popup_window(closed_window)", source)

    def test_web_features_required_for_sign_in_and_popups_are_explicit(self):
        source = self._method_source("BrowserController", "configure_profile")
        for feature in (
            "JavascriptEnabled",
            "JavascriptCanOpenWindows",
            "LocalStorageEnabled",
        ):
            with self.subTest(feature=feature):
                self.assertIn(
                    f"QWebEngineSettings.WebAttribute.{feature},\n            True",
                    source,
                )


if __name__ == "__main__":
    unittest.main()
