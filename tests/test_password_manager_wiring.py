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
        cls.page_source = (
            PROJECT_ROOT / "_BROWSER_" / "page.py"
        ).read_text(encoding="utf-8")
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
        browser_tree = ast.parse(cls.browser_source)
        cls.browser_classes = {
            node.name: node
            for node in browser_tree.body
            if isinstance(node, ast.ClassDef)
        }
        page_tree = ast.parse(cls.page_source)
        cls.page_class = next(
            node
            for node in page_tree.body
            if isinstance(node, ast.ClassDef) and node.name == "BrowserPage"
        )
        cls.page_methods = {
            node.name: node
            for node in cls.page_class.body
            if isinstance(node, ast.FunctionDef)
        }
        cls.window_methods = {
            node.name: node
            for node in cls.browser_classes["BrowserWindow"].body
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

    def test_https_login_submits_offer_save_only_in_normal_windows(self):
        page_init = ast.get_source_segment(
            self.page_source,
            self.page_methods["__init__"],
        )
        console_handler = ast.get_source_segment(
            self.page_source,
            self.page_methods["javaScriptConsoleMessage"],
        )
        self.assertIn("if not browser_window.private", page_init)
        self.assertIn("QWebEngineScript.InjectionPoint.DocumentCreation", page_init)
        self.assertIn("PASSWORD_SAVE_SUBMIT_SCRIPT", page_init)
        self.assertIn("message == PASSWORD_SAVE_SUBMIT_MARKER", console_handler)
        self.assertIn("_offer_password_save_after_submit", console_handler)

        self.assertIn('location.protocol !== "https:"', self.password_source)
        self.assertIn("event.preventDefault()", self.password_source)
        self.assertIn("event.stopImmediatePropagation()", self.password_source)
        self.assertIn("console.info(\"__HEN_NAVE_PASSWORD_SUBMIT__\")", self.password_source)
        self.assertIn('"new-password"', self.password_source)
        self.assertIn("setTimeout(resumeSubmission, 15000)", self.password_source)
        self.assertIn("window.__henNavePendingLoginForm = form", self.password_source)
        self.assertIn("pending.form.requestSubmit", self.password_source)

    def test_auto_save_needs_confirmation_and_resumes_site_submission(self):
        method = self.window_methods["_show_password_save_prompt"]
        source = ast.get_source_segment(self.browser_source, method)
        self.assertIn("SaveLoginDialog(", source)
        self.assertIn("dialog.exec() != QDialog.DialogCode.Accepted", source)
        self.assertIn("self.web_credential_store.save_login(", source)
        self.assertIn("finally:", source)
        self.assertIn("page.runJavaScript(PASSWORD_SAVE_RESUME_SCRIPT)", source)

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
        self.assertIn("password_save_not_now", self.password_source)
        self.assertIn('"password_save_not_now": "Agora não"', self.config_source)

    def test_private_window_policy_is_documented(self):
        self.assertIn("password_manager_action.setEnabled(not self.private)", self.browser_source)
        self.assertIn("password_manager", self.config_source)


if __name__ == "__main__":
    unittest.main()
