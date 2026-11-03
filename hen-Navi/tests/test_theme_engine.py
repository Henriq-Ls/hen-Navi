import re
import unittest

from _CONFIGURA_ import (
    CHAVES_TEMA,
    TEMAS,
    TEMA_PADRAO,
    TEMA_PERSONALIZADO,
    VERSAO_APP,
)
from _APP_.startpage import generate_start_page
from _CONFIGURA_.theme_engine import (
    normalizar_tema_personalizado,
    obter_tema,
    startpage_theme_css,
    stylesheet_for_theme,
)


class ThemeConfigurationTests(unittest.TestCase):
    def test_all_themes_have_the_same_complete_keys(self):
        for theme_id, theme in TEMAS.items():
            with self.subTest(tema=theme_id):
                self.assertEqual(set(theme), CHAVES_TEMA)
                self.assertTrue(all(value not in (None, "") for value in theme.values()))

    def test_stylesheets_have_no_empty_or_unresolved_values(self):
        unresolved = re.compile(r"\{[a-zA-Z_][a-zA-Z_0-9]*\}")
        for theme_id in TEMAS:
            with self.subTest(tema=theme_id):
                styles = stylesheet_for_theme(theme_id)
                startpage = startpage_theme_css(theme_id)
                self.assertNotRegex(styles, unresolved)
                self.assertNotRegex(startpage, unresolved)
                self.assertNotRegex(styles, r":\s*;")
                self.assertNotRegex(startpage, r":\s*;")
                self.assertNotIn("None", styles + startpage)

    def test_invalid_theme_is_rejected_and_version_is_updated(self):
        self.assertEqual(obter_tema()["name"], TEMAS[TEMA_PADRAO]["name"])
        with self.assertRaises(ValueError):
            obter_tema("inexistente")
        self.assertEqual(VERSAO_APP, "v0.3.0")

    def test_custom_theme_applies_safe_colors_and_fonts_everywhere(self):
        custom = {
            "background": "#123456",
            "accent": "#E36A4D",
            "icon": "#F0A020",
            "font_ui": "DejaVu Sans",
            "font_content": "Liberation Serif",
        }
        theme = obter_tema(TEMA_PERSONALIZADO, custom_theme=custom)
        styles = stylesheet_for_theme(
            TEMA_PERSONALIZADO,
            custom_theme=custom,
        )
        home_css = startpage_theme_css(
            TEMA_PERSONALIZADO,
            custom_theme=custom,
        )
        home_html = generate_start_page(
            theme_id=TEMA_PERSONALIZADO,
            custom_theme=custom,
        )

        self.assertEqual(theme["background"], "#123456")
        self.assertEqual(theme["accent"], "#E36A4D")
        self.assertEqual(theme["icon"], "#F0A020")
        self.assertEqual(theme["surface"], TEMAS[TEMA_PADRAO]["surface"])
        self.assertIn('font-family: "DejaVu Sans"', styles)
        self.assertIn('body { font-family: "Liberation Serif"', home_css)
        self.assertIn("--bg: #123456;", home_html)

    def test_custom_theme_rejects_invalid_colors_and_unsafe_font_names(self):
        normalized = normalizar_tema_personalizado(
            {
                "background": "#12345;",
                "accent": "red",
                "font_ui": 'Sans"; color: red; /*',
                "font_content": "Noto Sans",
                "unexpected": "#FFFFFF",
            }
        )
        self.assertEqual(
            normalized,
            {"font_content": "Noto Sans"},
        )


if __name__ == "__main__":
    unittest.main()
