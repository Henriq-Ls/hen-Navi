import ast
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SecurityToolsWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.browser_source = (PROJECT_ROOT / "browser.py").read_text(
            encoding="utf-8"
        )
        cls.panels_source = (
            PROJECT_ROOT / "_BROWSER_" / "window_panels.py"
        ).read_text(encoding="utf-8")
        cls.manager_source = (
            PROJECT_ROOT
            / "_APP_"
            / "barra_direita_tools"
            / "manager.py"
        ).read_text(encoding="utf-8")
        cls.tools_source = (
            PROJECT_ROOT / "_APP_" / "security_tools.py"
        ).read_text(encoding="utf-8")
        cls.devtools_source = (
            PROJECT_ROOT
            / "_APP_"
            / "barra_direita_tools"
            / "devtools.py"
        ).read_text(encoding="utf-8")
        cls.privacy_source = (
            PROJECT_ROOT / "_APP_" / "site_privacy.py"
        ).read_text(encoding="utf-8")

    def test_devtools_tracks_selected_tab_and_uses_embedded_webengine(self):
        self.assertIn(
            "page.setDevToolsPage(self.devtools_page)",
            self.devtools_source,
        )
        self.assertIn("self._sync_devtools_page()", self.browser_source)
        self.assertIn(
            'self._callback("toggle_side_panel")(\n                "devtools"',
            self.manager_source,
        )
        self.assertIn(
            "parent.devtools_action = QAction(\n            ico_ferramentas()",
            self.manager_source,
        )
        self.assertIn(
            '"inspect_page": "Inspecionar DOM da página"',
            (PROJECT_ROOT / "_CONFIGURA_" / "__init__.py").read_text(
                encoding="utf-8"
            ),
        )
        self.assertIn(
            '"devtools_action": "Abrir DevTools do Chromium"',
            (PROJECT_ROOT / "_CONFIGURA_" / "__init__.py").read_text(
                encoding="utf-8"
            ),
        )

    def test_devtools_detaches_when_its_panel_is_hidden(self):
        browser_tree = ast.parse(self.browser_source)
        browser_window = next(
            node
            for node in browser_tree.body
            if isinstance(node, ast.ClassDef) and node.name == "BrowserWindow"
        )
        browser_methods = {
            node.name: node
            for node in browser_window.body
            if isinstance(node, ast.FunctionDef)
        }
        panels_tree = ast.parse(self.panels_source)
        panels_class = next(
            node
            for node in panels_tree.body
            if isinstance(node, ast.ClassDef)
            and node.name == "BrowserWindowPanelsMixin"
        )
        methods = {
            node.name: node
            for node in panels_class.body
            if isinstance(node, ast.FunctionDef)
        }
        sync_source = ast.get_source_segment(
            self.browser_source,
            browser_methods["_sync_devtools_page"],
        )
        toggle_source = ast.get_source_segment(
            self.panels_source,
            methods["_toggle_side_panel"],
        )
        close_source = ast.get_source_segment(
            self.panels_source,
            methods["_close_side_panel"],
        )

        self.assertIn('self._active_side_panel != "devtools"', sync_source)
        self.assertIn("not self._side_panel_container.isVisible()", sync_source)
        self.assertIn("devtools.set_page(None)", sync_source)
        self.assertIn("self._sync_devtools_page()", toggle_source)
        self.assertIn("self._sync_devtools_page()", close_source)

    def test_network_checks_are_user_triggered_head_requests(self):
        self.assertIn("manager.head(request)", self.tools_source)
        self.assertIn("ManualRedirectPolicy", self.tools_source)
        self.assertIn("request_url.setQuery(\"\")", self.tools_source)
        self.assertIn("request_url.setPath(\"/\")", self.tools_source)
        self.assertNotIn("manager.get(request)", self.tools_source)

    def test_site_data_removal_is_scoped_to_matching_cookie_domains(self):
        self.assertIn("self._cookie_store.deleteCookie(cookie)", self.privacy_source)
        self.assertIn("self._cookie_matches_site(cookie)", self.privacy_source)
        self.assertIn("host.endswith(f\".{domain}\")", self.privacy_source)
        self.assertNotIn("deleteAllCookies", self.privacy_source)
        self.assertIn("popup_pergunta(", self.privacy_source)

    def test_all_security_ui_text_keys_are_configured(self):
        config_tree = ast.parse(
            (PROJECT_ROOT / "_CONFIGURA_" / "__init__.py").read_text(
                encoding="utf-8"
            )
        )
        ui_assignment = next(
            node
            for node in config_tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "TEXTO_UI"
                for target in node.targets
            )
        )
        configured_keys = {
            ast.literal_eval(key) for key in ui_assignment.value.keys
        }
        used_keys = set()
        for path in PROJECT_ROOT.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            used_keys.update(
                ast.literal_eval(node.slice)
                for node in ast.walk(tree)
                if isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Name)
                and node.value.id == "TEXTO_UI"
                and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)
            )

        self.assertEqual(sorted(used_keys - configured_keys), [])


if __name__ == "__main__":
    unittest.main()
