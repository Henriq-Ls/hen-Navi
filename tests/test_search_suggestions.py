import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from _APP_.startpage import generate_start_page
from _SERVICOS_.search_suggestions import (
    build_suggestion_url,
    collect_site_suggestions,
    parse_search_suggestions,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SearchSuggestionTests(unittest.TestCase):
    def test_selected_search_provider_builds_its_own_https_suggestion_url(self):
        expected = {
            "duckduckgo": "duckduckgo.com",
            "google": "suggestqueries.google.com",
            "bing": "api.bing.com",
        }
        for engine, host in expected.items():
            with self.subTest(engine=engine):
                url = build_suggestion_url("  gatos e cães  ", engine)
                parsed = urlsplit(url)
                self.assertEqual(parsed.scheme, "https")
                self.assertEqual(parsed.netloc, host)
                self.assertTrue(parse_qs(parsed.query))

    def test_short_query_and_unknown_provider_are_handled(self):
        self.assertEqual(build_suggestion_url("g", "google"), "")
        with self.assertRaises(ValueError):
            build_suggestion_url("gatos", "unknown")

    def test_provider_responses_are_normalized_and_deduplicated(self):
        google = parse_search_suggestions(
            "google",
            '["pin",["Pinterest","Pinterest ideias","Pinterest"]]',
        )
        duckduckgo = parse_search_suggestions(
            "duckduckgo",
            '[{"phrase":"receita de bolo"},{"phrase":"Receita de bolo"}]',
        )
        self.assertEqual(google, ["Pinterest", "Pinterest ideias"])
        self.assertEqual(duckduckgo, ["receita de bolo"])
        self.assertEqual(parse_search_suggestions("google", "{"), [])

    def test_common_site_names_match_partial_and_punctuated_input(self):
        google = collect_site_suggestions("GO")
        pinterest = collect_site_suggestions("Pin-T")
        self.assertTrue(any(item["title"] == "Google" for item in google))
        self.assertTrue(any(item["title"] == "Pinterest" for item in pinterest))

    def test_favorites_can_override_the_display_name_and_recent_sites_are_included(self):
        favorites = [
            {
                "url": "https://www.google.com/",
                "title": "Meu Google",
            }
        ]
        recent = [
            {
                "url": "https://example.org/",
                "title": "Exemplo recente",
            }
        ]
        suggestions = collect_site_suggestions("", favorites, recent)
        google = next(item for item in suggestions if item["host"] == "www.google.com")
        recent_site = next(
            item for item in suggestions if item["host"] == "example.org"
        )
        self.assertEqual(google["title"], "Meu Google")
        self.assertEqual(recent_site["title"], "Exemplo recente")

    def test_home_page_has_site_datalist_and_qt_search_suggestion_bridge(self):
        page = generate_start_page()
        self.assertIn('list="home-search-suggestions"', page)
        self.assertIn('<option value="google.com" label="Google">', page)
        self.assertIn('<option value="pinterest.com" label="Pinterest">', page)
        self.assertIn("qrc:///qtwebchannel/qwebchannel.js", page)
        self.assertIn("bridge.requestSuggestions(input.value.trim())", page)

    def test_home_page_shows_saved_searches_only_outside_private_mode(self):
        normal_page = generate_start_page(
            search_queries=["Pinterest ideias"]
        )
        private_page = generate_start_page(
            search_queries=["Pinterest ideias"],
            private=True,
        )
        self.assertIn('value="Pinterest ideias"', normal_page)
        self.assertNotIn("Pinterest ideias", private_page)

    def test_address_bar_uses_completer_and_home_bridge_is_detached_on_web_pages(self):
        browser = (PROJECT_ROOT / "browser.py").read_text(encoding="utf-8")
        page = (
            PROJECT_ROOT / "_BROWSER_" / "page.py"
        ).read_text(encoding="utf-8")
        service = (
            PROJECT_ROOT / "_APP_" / "search_suggestions.py"
        ).read_text(encoding="utf-8")
        self.assertIn("self.address_bar.textEdited.connect", browser)
        self.assertIn("QCompleter.CompletionMode.PopupCompletion", browser)
        self.assertIn("self.setWebChannel(None)", page)
        self.assertIn("self.search_suggestion_service.request(", browser)
        self.assertIn("DEBOUNCE_MS = 250", service)
        self.assertIn(
            "self.controller.storage.recent_search_queries(query, 30)",
            browser,
        )
        self.assertIn("def _record_search_query(self, query: str)", browser)


if __name__ == "__main__":
    unittest.main()
