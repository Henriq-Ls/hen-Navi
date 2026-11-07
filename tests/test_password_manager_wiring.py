import ast
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PasswordManagerWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.browser_source = (PROJECT_ROOT / "browser.py").read_text(
            encoding="utf-8"
        )
        cls.password_source = (
            PROJECT_ROOT / "_APP_" / "password_manager.py"
        ).read_text(encoding="utf-8")
        cls.config_source = (
            PROJECT_ROOT / "_CONFIGURA_" / "__init__.py"
        ).read_text(encoding="utf-8")
        cls.password_tree = ast.parse(cls.password_source)
        cls.dialog_class = next(
            node
            for node in cls.password_tree.body
            if isinstance(node, ast.ClassDef)
            and node.name == "PasswordManagerDialog"
        )
        cls.dialog_methods = {
            node.name: node
            for node in cls.dialog_class.body
            if isinstance(node, ast.FunctionDef)
        }

    def test_password_manager_is_disabled_for_private_windows(self):
        self.assertIn(
            'self.password_manager_action.setEnabled(not self.private)',
            self.browser_source,
        )
        open_manager = next(
            node
            for node in ast.parse(self.browser_source).body
            if isinstance(node, ast.ClassDef) and node.name == "BrowserWindow"
        )
        method = next(
            node
            for node in open_manager.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "open_password_manager"
        )
        method_source = ast.get_source_segment(self.browser_source, method)
        self.assertIn("if self.private:", method_source)

    def test_capture_only_runs_after_user_invokes_save_action(self):
        method = self.dialog_methods["save_current_login"]
        source = ast.get_source_segment(self.password_source, method)
        self.assertIn("_READ_LOGIN_SCRIPT", source)
        self.assertIn("self.page.runJavaScript", source)
        self.assertIn("self._page_matches_origin()", source)

    def test_fill_checks_exact_origin_and_does_not_submit_form(self):
        script_source = self.password_source.split(
            "def _fill_login_script", 1
        )[1]
        self.assertIn("location.origin !==", script_source)
        self.assertIn("self.page.runJavaScript(script", self.password_source)
        self.assertNotIn(".submit()", self.password_source)

    def test_credentials_use_confirmation_and_system_keyring(self):
        credential_store = (
            PROJECT_ROOT / "_SERVICOS_" / "web_credential_store.py"
        ).read_text(encoding="utf-8")
        self.assertIn("QDialogButtonBox.StandardButton.Save", self.password_source)
        self.assertIn("get_secure_keyring", credential_store)
        self.assertIn("password_save_notice", self.password_source)

    def test_private_window_policy_is_documented(self):
        self.assertIn("password_manager_action.setEnabled(not self.private)", self.browser_source)
        self.assertIn("password_manager", self.config_source)


if __name__ == "__main__":
    unittest.main()
