import base64
import tempfile
import unittest
from pathlib import Path

from _APPDATA_.storage import BrowserStorage


class BrowserStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = BrowserStorage(Path(self.temp_dir.name) / "browser.sqlite3")

    def tearDown(self):
        self.storage.close()
        self.temp_dir.cleanup()

    def test_recent_duplicate_only_updates_title(self):
        url = "https://example.com/"
        self.assertTrue(self.storage.record_visit(url, "Antes", visited_at=1000))
        self.assertFalse(self.storage.record_visit(url, "Depois", visited_at=1002))
        rows = self.storage.get_history()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Depois")
        self.assertEqual(rows[0]["visited_at"], 1000)

    def test_visits_outside_dedup_window_are_kept(self):
        url = "https://example.com/"
        self.storage.record_visit(url, "Primeira", visited_at=1000)
        self.storage.record_visit(url, "Segunda", visited_at=1006)
        self.assertEqual(len(self.storage.get_history()), 2)

    def test_non_http_urls_are_not_stored(self):
        self.assertFalse(self.storage.record_visit("file:///tmp/page.html", "Local"))
        self.assertFalse(self.storage.add_favorite("javascript:alert(1)", "Não permitido"))
        self.assertEqual(self.storage.get_history(), [])
        self.assertEqual(self.storage.get_favorites(), [])

    def test_favorites_can_be_added_searched_and_removed(self):
        self.assertTrue(self.storage.add_favorite("https://example.com/", "Exemplo"))
        self.assertTrue(self.storage.is_favorite("https://example.com/"))
        self.assertEqual(len(self.storage.get_favorites("exem")), 1)
        self.assertTrue(self.storage.remove_favorite("https://example.com/"))
        self.assertFalse(self.storage.is_favorite("https://example.com/"))

    def test_existing_favorite_can_be_renamed(self):
        url = "https://example.com/"
        self.storage.add_favorite(url, "Nome antigo")
        self.assertTrue(self.storage.add_favorite(url, "Nome novo"))
        self.assertEqual(self.storage.get_favorites()[0]["title"], "Nome novo")

    def test_renaming_one_favorite_preserves_the_rest(self):
        urls = (
            "https://one.example/",
            "https://two.example/",
            "https://three.example/",
        )
        for index, url in enumerate(urls):
            self.storage.add_favorite(url, f"Favorito {index}")

        self.storage.add_favorite(urls[1], "Nome atualizado")

        favorites = self.storage.get_favorites()
        self.assertEqual({item["url"] for item in favorites}, set(urls))
        self.assertEqual(
            next(item["title"] for item in favorites if item["url"] == urls[1]),
            "Nome atualizado",
        )

    def test_search_queries_are_normalized_deduplicated_and_limited(self):
        self.assertFalse(self.storage.record_search_query("   "))
        self.assertTrue(
            self.storage.record_search_query(
                "  Pinterest   ideias  ",
                searched_at=10,
            )
        )
        self.assertTrue(
            self.storage.record_search_query(
                "pinterest IDEIAS",
                searched_at=20,
            )
        )
        self.storage.record_search_query("Google imagens", searched_at=30)
        self.assertEqual(
            self.storage.recent_search_queries("IDEIAS"),
            ["pinterest IDEIAS"],
        )
        self.assertEqual(
            self.storage.recent_search_queries(),
            ["Google imagens", "pinterest IDEIAS"],
        )

    def test_search_query_history_keeps_only_the_50_most_recent_terms(self):
        for index in range(51):
            self.storage.record_search_query(
                f"consulta {index}",
                searched_at=index,
            )
        queries = self.storage.recent_search_queries(limit=60)
        self.assertEqual(len(queries), 50)
        self.assertNotIn("consulta 0", queries)
        self.assertEqual(queries[0], "consulta 50")

    def test_favicons_are_cached_per_site_and_validated_as_png(self):
        png = base64.b64encode(b"\x89PNG\r\n\x1a\nfixture").decode("ascii")
        favicon = f"data:image/png;base64,{png}"
        self.assertTrue(
            self.storage.save_favicon(
                "https://www.example.com/page",
                favicon,
            )
        )
        self.assertEqual(
            self.storage.get_favicon("http://example.com/"),
            favicon,
        )
        self.assertFalse(
            self.storage.save_favicon(
                "https://example.com/",
                favicon,
            )
        )
        self.assertFalse(
            self.storage.save_favicon(
                "https://example.com/",
                "data:image/svg+xml,<svg/>",
            )
        )
        self.assertEqual(self.storage.get_favicon("javascript:alert(1)"), "")

    def test_session_filters_invalid_urls_and_deduplicates(self):
        self.storage.save_session(
            [
                "https://one.example/",
                "file:///tmp/no.html",
                "https://one.example/",
                "http://localhost:8080/",
            ]
        )
        self.assertEqual(
            self.storage.load_session(),
            ["https://one.example/", "http://localhost:8080/"],
        )

    def test_history_entry_removal_and_clear(self):
        self.storage.record_visit("https://one.example/", "Um", visited_at=100)
        self.storage.record_visit("https://two.example/", "Dois", visited_at=200)
        self.storage.record_search_query("consulta anterior", searched_at=150)
        first = self.storage.get_history()[1]
        self.assertTrue(self.storage.remove_history_entry(first["id"]))
        self.assertEqual(len(self.storage.get_history()), 1)
        self.storage.clear_history()
        self.assertEqual(self.storage.get_history(), [])
        self.assertEqual(self.storage.recent_search_queries(), [])

    def test_browser_download_history_keeps_terminal_status_until_removed(self):
        download_id = self.storage.record_browser_download(
            "/downloads/arquivo.zip",
            "arquivo.zip",
            started_at=100,
        )
        self.assertEqual(
            self.storage.get_browser_downloads()[0]["status"],
            "active",
        )

        self.assertTrue(
            self.storage.update_browser_download(
                download_id,
                "completed",
                finished_at=125,
            )
        )
        entry = self.storage.get_browser_downloads()[0]
        self.assertEqual(entry["file_name"], "arquivo.zip")
        self.assertEqual(entry["status"], "completed")
        self.assertEqual(entry["finished_at"], 125)

        self.assertTrue(self.storage.remove_browser_download(download_id))
        self.assertEqual(self.storage.get_browser_downloads(), [])

    def test_active_downloads_are_marked_interrupted_after_restart(self):
        self.storage.record_browser_download(
            "/downloads/parcial.zip",
            "parcial.zip",
            started_at=100,
        )
        database_path = self.storage.database_path
        self.storage.close()
        self.storage = BrowserStorage(database_path)

        entries = self.storage.get_browser_downloads()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["status"], "interrupted")
        self.assertIsNotNone(entries[0]["finished_at"])


if __name__ == "__main__":
    unittest.main()
