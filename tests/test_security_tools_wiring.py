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
        cls.tools_source = (
            PROJECT_ROOT / "_APP_" / "security_tools.py"
        ).read_text(encoding="utf-8")
        cls.privacy_source = (
            PROJECT_ROOT / "_APP_" / "site_privacy.py"
        ).read_text(encoding="utf-8")

    def test_devtools_tracks_selected_tab_and_uses_embedded_webengine(self):
        self.assertIn("page.setDevToolsPage(self.devtools_page)", self.tools_source)
        self.assertIn("self._sync_devtools_page()", self.browser_source)
        self.assertIn('self._toggle_side_panel("devtools")', self.browser_source)

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
