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
        cls.page_source = (
            PROJECT_ROOT / "_BROWSER_" / "page.py"
        ).read_text(encoding="utf-8")
        page_tree = ast.parse(cls.page_source)
        cls.page = next(
            node
            for node in page_tree.body
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

    def test_start_page_tabs_are_movable_and_closable(self):
        self.assertIn("self.setTabsClosable(True)", self.tabs_source)
        self.assertIn("self.setMovable(True)", self.tabs_source)
        self.assertNotIn("pinnedHomeTab", self.browser_source)
        self.assertNotIn("pinned_home", self.browser_source)
        self.assertNotIn("_keep_home_tab_first", self.browser_source)
        create_method = ast.get_source_segment(
            self.browser_source,
            self.methods["_create_tab"],
        )
        self.assertIn("self.tabs.addTab(view, label)", create_method)
        self.assertIn("close_button = TabCloseButton(", create_method)
        self.assertIn(
            'font_size_px=self._theme["font_size_px"]',
            create_method,
        )
        self.assertIn("bar.setTabButton(", create_method)

    def test_home_shortcut_opens_home_without_a_toolbar_button(self):
        method = ast.get_source_segment(
            self.browser_source,
            self.methods["go_home"],
        )
        self.assertIn("self.controller.refresh_home_pages()", method)
        self.assertIn("view = self._current_view()", method)
        self.assertIn("view.setUrl(QUrl.fromLocalFile(self._start_page_path))", method)
        self.assertNotIn("pinned", method)
        interface = ast.get_source_segment(
            self.browser_source,
            self.methods["_build_interface"],
        )
        self.assertIn("self.home_shortcut_action", interface)
        self.assertNotIn("self.toolbar.addAction(self.home_shortcut_action)", interface)
        self.assertIn("self.addAction(self.home_shortcut_action)", interface)

    def test_plus_action_creates_one_selected_home_tab(self):
        method = ast.get_source_segment(
            self.browser_source,
            self.methods["_create_tab"],
        )
        new_tab_method = ast.get_source_segment(
            self.browser_source,
            self.methods["new_tab"],
        )
        button_method = ast.get_source_segment(
            self.browser_source,
            self.methods["_build_new_tab_button"],
        )
        self.assertIn("self.tabs.addTab(view, label)", method)
        self.assertIn("elif home:", method)
        self.assertIn("view.setUrl(QUrl.fromLocalFile(home_path))", method)
        self.assertIn('TEXTO_UI["home_title"]', method)
        self.assertEqual(new_tab_method.count("self._create_tab("), 1)
        self.assertIn("self._create_tab(home=True, select=True)", new_tab_method)
        self.assertNotIn("about:blank", new_tab_method)
        self.assertIn("button.clicked.connect(self.new_tab)", button_method)
        menu_method = ast.get_source_segment(
            self.browser_source,
            self.methods["_build_menu"],
        )
        self.assertIn('self.new_tab,\n            atalho("nova_aba")', menu_method)

    def test_restored_sessions_start_with_a_regular_home_tab(self):
        method = ast.get_source_segment(
            self.browser_source,
            self.methods["__init__"],
        )
        self.assertIn(
            "self._create_tab(home=True, select=True)",
            method,
        )
        self.assertNotIn("pinned_home", method)
        self.assertIn("if restore_urls:", method)
        self.assertLess(
            method.index("self._create_tab(home=True, select=True)"),
            method.index("for url in restore_urls"),
        )

    def test_last_tab_close_closes_the_window_without_reopening_home(self):
        method = ast.get_source_segment(
            self.browser_source,
            self.methods["close_tab"],
        )
        self.assertIn("if index < 0 or index >= self.tabs.count()", method)
        self.assertIn("if self.tabs.count() == 1:", method)
        self.assertIn("self.close()", method)
        self.assertNotIn("self._create_tab(home=True, select=True)", method)
        self.assertNotIn("pinnedHomeTab", method)

    def test_home_search_navigates_its_tab_and_tab_labels_are_limited(self):
        search_method = ast.get_source_segment(
            self.browser_source,
            self.methods["_search_from_home"],
        )
        self.assertIn("view.setUrl(QUrl(target))", search_method)
        self.assertIn("self._record_search_query(query)", search_method)
        self.assertIn("self.open_url_new_tab(target)", search_method)
        self.assertIn("MAX_TAB_TITLE_CHARS = 40", self.browser_source)
        self.assertIn("def _limited_tab_title", self.browser_source)
        self.assertIn("self.tabs.setTabToolTip(index, f\"{full_title}", self.browser_source)

    def test_start_page_search_is_queued_and_does_not_refresh_during_navigation(self):
        method = ast.get_source_segment(
            self.page_source,
            self.page_methods["acceptNavigationRequest"],
        )
        self.assertIn('if scheme == "file":', method)
        self.assertIn('if query.hasQueryItem("q"):', method)
        self.assertIn("self.browser_window._queue_home_search(", method)
        queue_method = ast.get_source_segment(
            self.browser_source,
            self.methods["_queue_home_search"],
        )
        self.assertIn("QTimer.singleShot(", queue_method)
        self.assertIn("self._search_from_home(query, page)", queue_method)
        record_method = ast.get_source_segment(
            self.browser_source,
            self.methods["_record_search_query"],
        )
        self.assertNotIn("refresh_home_pages", record_method)
        startpage = (PROJECT_ROOT / "_APP_" / "startpage.py").read_text(
            encoding="utf-8"
        )
        bridge = (
            PROJECT_ROOT / "_APP_" / "search_suggestions.py"
        ).read_text(encoding="utf-8")
        create_method = ast.get_source_segment(
            self.browser_source,
            self.methods["_create_tab"],
        )
        self.assertIn('form.addEventListener("submit"', startpage)
        self.assertIn("event.preventDefault()", startpage)
        self.assertIn("bridge.submitSearch(input.value.trim())", startpage)
        self.assertIn("searchRequested = Signal(str)", bridge)
        self.assertIn("def submitSearch(self, query: str)", bridge)
        self.assertIn("bridge.searchRequested.connect(", create_method)
        self.assertIn("Qt.ConnectionType.QueuedConnection", create_method)

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
