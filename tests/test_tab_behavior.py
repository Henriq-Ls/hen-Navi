import ast
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class BrowserTabBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.browser_source = (PROJECT_ROOT / "browser.py").read_text(
            encoding="utf-8"
        )
        cls.browser_tree = ast.parse(cls.browser_source)
        cls.window = next(
            node
            for node in cls.browser_tree.body
            if isinstance(node, ast.ClassDef) and node.name == "BrowserWindow"
        )
        cls.page = next(
            node
            for node in cls.browser_tree.body
            if isinstance(node, ast.ClassDef) and node.name == "BrowserPage"
        )
        cls.methods = {
            node.name: node
            for node in cls.window.body
            if isinstance(node, ast.FunctionDef)
        }
        cls.page_methods = {
            node.name: node
            for node in cls.page.body
            if isinstance(node, ast.FunctionDef)
        }
        cls.tabs_source = (
            PROJECT_ROOT / "_APP_" / "Navegador" / "abas.py"
        ).read_text(encoding="utf-8")

    def test_home_tab_is_pinned_at_the_start_and_other_tabs_stay_movable(self):
        self.assertIn("self.setTabsClosable(True)", self.tabs_source)
        self.assertIn("self.setMovable(True)", self.tabs_source)
        self.assertIn(
            'view.setProperty("pinnedHomeTab", bool(pinned_home))',
            self.browser_source,
        )
        self.assertIn("bar.setTabButton(index, bar.ButtonPosition.RightSide, None)", self.browser_source)
        self.assertIn("self.tabs.tabBar().tabMoved.connect(self._keep_home_tab_first)", self.browser_source)
        self.assertIn("def _keep_home_tab_first", self.browser_source)

    def test_home_button_selects_or_creates_the_single_start_tab(self):
        method = ast.get_source_segment(
            self.browser_source,
            self.methods["go_home"],
        )
        self.assertIn('view.property("pinnedHomeTab")', method)
        self.assertIn("self.tabs.tabBar().moveTab(index, 0)", method)
        self.assertIn(
            "self._create_tab(home=True, pinned_home=True, select=True)",
            method,
        )
        self.assertIn("self.tabs.setCurrentIndex(0)", method)

    def test_plus_action_creates_a_regular_start_tab(self):
        method = ast.get_source_segment(
            self.browser_source,
            self.methods["_create_tab"],
        )
        new_home_method = ast.get_source_segment(
            self.browser_source,
            self.methods["new_home_tab"],
        )
        button_method = ast.get_source_segment(
            self.browser_source,
            self.methods["_build_corner_button"],
        )
        self.assertIn("tab_index = 0 if pinned_home else self.tabs.count()", method)
        self.assertIn("self.tabs.insertTab(tab_index, view, label)", method)
        self.assertIn("self._create_tab(home=True, select=True)", new_home_method)
        self.assertIn("button.clicked.connect(self.new_home_tab)", button_method)

    def test_restored_sessions_start_with_one_home_tab(self):
        method = ast.get_source_segment(
            self.browser_source,
            self.methods["__init__"],
        )
        self.assertIn(
            "self._create_tab(home=True, pinned_home=True, select=True)",
            method,
        )
        self.assertIn("if restore_urls:", method)
        self.assertLess(
            method.index("self._create_tab(home=True, pinned_home=True, select=True)"),
            method.index("for url in restore_urls"),
        )

    def test_home_tab_cannot_be_closed(self):
        method = ast.get_source_segment(
            self.browser_source,
            self.methods["close_tab"],
        )
        self.assertIn("if index < 0 or index >= self.tabs.count()", method)
        self.assertIn('if view.property("pinnedHomeTab"):', method)
        self.assertIn("if self.tabs.count() == 1:", method)

    def test_home_search_opens_a_new_tab_and_tab_labels_are_limited(self):
        search_method = ast.get_source_segment(
            self.browser_source,
            self.methods["_search_from_home"],
        )
        self.assertIn("self.open_url_new_tab(target)", search_method)
        self.assertIn("MAX_TAB_TITLE_CHARS = 40", self.browser_source)
        self.assertIn("def _limited_tab_title", self.browser_source)
        self.assertIn("self.tabs.setTabToolTip(index, f\"{full_title}", self.browser_source)

    def test_start_page_form_is_intercepted_from_its_local_file(self):
        method = ast.get_source_segment(
            self.browser_source,
            self.page_methods["acceptNavigationRequest"],
        )
        self.assertIn('if scheme == "file":', method)
        self.assertIn('if query.hasQueryItem("q"):', method)
        self.assertIn("self.browser_window._search_from_home(", method)

    def test_private_browsing_does_not_persist_site_icons(self):
        method = ast.get_source_segment(
            self.browser_source,
            self.methods["_on_view_icon_changed"],
        )
        self.assertIn("if self.private or icon.isNull() or not is_http_url(url):", method)
        self.assertIn("self.controller.storage.save_favicon(url, data_uri)", method)

    def test_session_saves_urls_from_every_tab(self):
        method = ast.get_source_segment(
            self.browser_source,
            self.methods["session_urls"],
        )
        self.assertIn("range(self.tabs.count())", method)
        self.assertNotIn("range(1, self.tabs.count())", method)


if __name__ == "__main__":
    unittest.main()
