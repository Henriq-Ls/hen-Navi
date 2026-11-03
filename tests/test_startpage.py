import unittest

from startpage import generate_start_page


class StartPageTests(unittest.TestCase):
    def test_renders_favorites_and_unique_recent_urls(self):
        favorite = {"url": "https://example.com/", "title": "Exemplo"}
        recent = [
            {"url": "https://example.com/", "title": "Exemplo recente"},
            {"url": "https://example.com/", "title": "Duplicado"},
            {"url": "https://other.example/", "title": "Outro"},
        ]
        page = generate_start_page([favorite], recent)
        self.assertIn("Favoritos", page)
        self.assertIn("Exemplo", page)
        self.assertEqual(page.count('href="https://example.com/"'), 2)
        self.assertIn("other.example", page)
        example_cards = [
            card.split('style="background:', 1)[1].split('"', 1)[0]
            for card in page.split('href="https://example.com/"')[1:]
        ]
        self.assertEqual(example_cards[0], example_cards[1])

    def test_dynamic_html_is_escaped(self):
        page = generate_start_page(
            [
                {
                    "url": 'https://example.com/?q="<script>',
                    "title": '<img src=x onerror="alert(1)">',
                }
            ],
            [],
        )
        self.assertNotIn('<img src=x onerror="alert(1)">', page)
        self.assertIn("&lt;img", page)
        self.assertIn("&quot;", page)

    def test_private_page_shows_warning_without_recent_history(self):
        page = generate_start_page(
            [],
            [{"url": "https://private-history.example/", "title": "Não mostrar"}],
            private=True,
        )
        self.assertIn("Navegação anônima", page)
        self.assertIn("provedor de internet", page)
        self.assertNotIn("private-history.example", page)
        self.assertNotIn("Não mostrar", page)

    def test_non_http_links_are_omitted(self):
        page = generate_start_page(
            [{"url": "javascript:alert(1)", "title": "No"}],
            [],
        )
        self.assertNotIn("javascript:", page)


if __name__ == "__main__":
    unittest.main()
