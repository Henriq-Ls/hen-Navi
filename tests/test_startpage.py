import base64
import unittest

from _APP_.startpage import generate_start_page


class StartPageTests(unittest.TestCase):
    def test_renders_project_logo_on_start_page(self):
        page = generate_start_page()
        if 'class="brand-logo"' in page:
            self.assertIn('src="data:image/png;base64,', page)
        else:
            self.assertIn('class="brand-mark"', page)

    def test_home_search_uses_the_local_page_and_cards_open_in_new_tabs(self):
        page = generate_start_page(
            recent=[{"url": "https://example.com/", "title": "Exemplo"}]
        )
        self.assertIn('<form class="search" method="get">', page)
        self.assertIn(
            'href="https://example.com/" target="_blank" rel="noopener noreferrer"',
            page,
        )

    def test_cards_show_saved_favicon_and_fallback_to_domain_initial(self):
        png = base64.b64encode(b"\x89PNG\r\n\x1a\nfixture").decode("ascii")
        favicon = f"data:image/png;base64,{png}"
        page = generate_start_page(
            favorites=[
                {
                    "url": "https://www.google.com/",
                    "title": "Google",
                    "favicon": favicon,
                }
            ]
        )
        self.assertIn(f'<img class="favicon" src="{favicon}" alt="">', page)

        fallback_page = generate_start_page(
            favorites=[{"url": "https://www.google.com/", "title": "Google"}]
        )
        self.assertIn('style="background:', fallback_page)
        self.assertIn(">G</span>", fallback_page)

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
