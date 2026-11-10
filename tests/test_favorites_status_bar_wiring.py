import ast
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FavoritesStatusBarWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.browser_source = (PROJECT_ROOT / "browser.py").read_text(
            encoding="utf-8"
        )
        cls.bar_source = (
            PROJECT_ROOT / "_APP_" / "favorites_bar.py"
        ).read_text(encoding="utf-8")
        bar_tree = ast.parse(cls.bar_source)
        bar_class = next(
            node
            for node in bar_tree.body
            if isinstance(node, ast.ClassDef)
            and node.name == "FavoritesStatusBar"
        )
        cls.bar_methods = {
            node.name: node
            for node in bar_class.body
            if isinstance(node, ast.FunctionDef)
        }
        tree = ast.parse(cls.browser_source)
        window = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "BrowserWindow"
        )
        cls.methods = {
            node.name: node
            for node in window.body
            if isinstance(node, ast.FunctionDef)
        }

    def test_favorites_and_temporary_status_share_one_footer_row(self):
        self.assertIn("FavoritesStatusBar(", self.browser_source)
        self.assertIn(
            "self._footer_layout.addWidget(self.favorites_status_bar, 1)",
            self.browser_source,
        )
        self.assertNotIn(
            "self._left_layout.addWidget(self.favorites_status_bar)",
            self.browser_source,
        )
        self.assertIn("self._footer_bar.hide()", self.browser_source)
        self.assertIn("self._footer_bar.show()", self.browser_source)
        self.assertIn(
            "self._footer_layout.addWidget(self._status_bar, 0)",
            self.browser_source,
        )
        self.assertIn(
            "self._status_bar.addWidget(self.performance_readout)",
            self.browser_source,
        )
        self.assertIn(
            "self._status_bar.setFixedSize(220, footer_height)",
            self.browser_source,
        )
        self.assertNotIn(
            "self._status_bar.addPermanentWidget(self.performance_readout)",
            self.browser_source,
        )
        self.assertNotIn(
            'self._status_bar.showMessage(TEXTO_UI["ready"])',
            self.browser_source,
        )
        self.assertIn(
            "self.favorites_status_bar.setVisible(True)",
            self.browser_source,
        )
        self.assertIn("MAX_VISIBLE_FAVORITES = 10", self.bar_source)
        self.assertIn(
            "visible_items = items[: self.MAX_VISIBLE_FAVORITES]",
            self.bar_source,
        )

    def test_favorite_items_open_and_show_site_icons_and_titles(self):
        self.assertIn("openRequested = Signal(str)", self.bar_source)
        self.assertIn("self.openRequested.emit(target)", self.bar_source)
        self.assertIn("self._favicon_icon(url)", self.bar_source)
        self.assertIn("self._visible_title(title)", self.bar_source)
        self.assertIn("Qt.ToolButtonStyle.ToolButtonTextBesideIcon", self.bar_source)
        self.assertIn("TEXTO_UI[\"favorite_open\"]", self.bar_source)

    def test_three_dot_menu_offers_edit_and_remove_with_confirmation(self):
        self.assertIn('setObjectName("favoriteStatusOptionsButton")', self.bar_source)
        self.assertIn('options_button.setText("⋮")', self.bar_source)
        self.assertIn("QMenu(options_button)", self.bar_source)
        self.assertIn("menu.addAction(", self.bar_source)
        self.assertIn("ico_editar()", self.bar_source)
        self.assertIn("ico_lixo()", self.bar_source)
        self.assertIn("edit_action.triggered.connect(", self.bar_source)
        self.assertIn("self._edit_favorite(", self.bar_source)
        self.assertIn("delete_action.triggered.connect(", self.bar_source)
        self.assertIn("self._remove_favorite(", self.bar_source)
        self.assertIn('TEXTO_UI["favorite_options_tooltip"]', self.bar_source)
        self.assertIn("self.storage.add_favorite(url, new_title)", self.bar_source)
        self.assertIn("self.storage.remove_favorite(url)", self.bar_source)
        self.assertIn("popup_pergunta(", self.bar_source)
        self.assertNotIn("favoriteStatusEditButton", self.bar_source)
        self.assertNotIn("favoriteStatusDeleteButton", self.bar_source)

    def test_edit_refreshes_once_and_resets_horizontal_scroll_position(self):
        edit_method = ast.get_source_segment(
            self.bar_source,
            self.bar_methods["_edit_favorite"],
        )
        remove_method = ast.get_source_segment(
            self.bar_source,
            self.bar_methods["_remove_favorite"],
        )

        self.assertIn("self.changed.emit()", edit_method)
        self.assertIn("self.changed.emit()", remove_method)
        self.assertNotIn("self.refresh()", edit_method)
        self.assertNotIn("self.refresh()", remove_method)
        self.assertGreaterEqual(
            self.bar_source.count("horizontalScrollBar().setValue(0)"),
            2,
        )

    def test_favorites_refresh_after_bar_or_dialog_changes(self):
        toggle_method = ast.get_source_segment(
            self.browser_source,
            self.methods["toggle_favorite"],
        )
        favorites_method = ast.get_source_segment(
            self.browser_source,
            self.methods["open_favorites"],
        )
        self.assertIn("self._refresh_favorite_surfaces()", toggle_method)
        self.assertIn(
            "dialog.changed.connect(self._refresh_favorite_surfaces)",
            favorites_method,
        )
        self.assertIn("self.favorites_status_bar.refresh()", self.browser_source)


if __name__ == "__main__":
    unittest.main()
