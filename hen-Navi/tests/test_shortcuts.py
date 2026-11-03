import ast
import unittest
from pathlib import Path

from _CONFIGURA_ import ATALHOS, ATALHOS_POR_ID, atalho


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ShortcutDefinitionTests(unittest.TestCase):
    def test_all_shortcuts_are_unique_and_grouped(self):
        keys = [item["atalho"] for item in ATALHOS]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(
            {item["categoria"] for item in ATALHOS},
            {"Abas", "Navegação", "Ferramentas", "Janelas", "Página"},
        )
        self.assertTrue(all(item["descricao"].strip() for item in ATALHOS))

    def test_browser_registrations_are_listed_in_the_central_registry(self):
        source = (PROJECT_ROOT / "browser.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        registered_ids = {
            node.args[0].value
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "atalho"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        }
        self.assertEqual(registered_ids, set(ATALHOS_POR_ID))

    def test_lookup_uses_the_same_definitions_as_the_help_list(self):
        for item in ATALHOS:
            with self.subTest(atalho=item["id"]):
                self.assertEqual(atalho(item["id"]), item["atalho"])


if __name__ == "__main__":
    unittest.main()
