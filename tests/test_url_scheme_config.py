import ast
import unittest
from pathlib import Path


class InternalUrlSchemeTests(unittest.TestCase):
    def test_browser_package_declares_lazy_public_api(self):
        import _BROWSER_

        self.assertEqual(
            set(_BROWSER_.__all__),
            {
                "BrowserController",
                "BrowserPage",
                "BrowserWindow",
                "register_custom_url_scheme",
            },
        )

    def test_secure_host_scheme_declares_its_default_port(self):
        source = (
            Path(__file__).resolve().parents[1]
            / "_BROWSER_"
            / "url_schemes.py"
        )
        tree = ast.parse(source.read_text(encoding="utf-8"))
        register = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "register_custom_url_scheme"
        )
        default_ports = [
            node.args[0].value
            for node in ast.walk(register)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "setDefaultPort"
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Constant)
        ]

        self.assertIn(443, default_ports)


if __name__ == "__main__":
    unittest.main()
