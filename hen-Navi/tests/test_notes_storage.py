import tempfile
import unittest
from pathlib import Path

from _APPDATA_.storage import BrowserStorage


class NotesStorageTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        database_path = Path(self.temporary_directory.name) / "test.sqlite3"
        self.storage = BrowserStorage(str(database_path))

    def tearDown(self):
        self.storage.close()
        self.temporary_directory.cleanup()

    def test_notes_are_saved_searched_and_normalized_by_site(self):
        self.assertTrue(
            self.storage.save_note(
                "www.example.com",
                "Anotar o prazo da entrega",
                atualizado_em=123.0,
            )
        )
        self.assertEqual(
            self.storage.get_note("example.com"),
            "Anotar o prazo da entrega",
        )
        results = self.storage.search_notes("prazo")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["host"], "example.com")
        self.assertEqual(results[0]["atualizado_em"], 123.0)
        self.assertEqual(len(self.storage.all_notes()), 1)

    def test_empty_note_deletes_saved_entry(self):
        self.storage.save_note("example.com", "Nota temporária")
        self.storage.save_note("example.com", "   ")
        self.assertEqual(self.storage.get_note("example.com"), "")
        self.assertEqual(self.storage.all_notes(), [])

    def test_blocking_exceptions_are_persisted_per_normalized_site(self):
        self.assertTrue(
            self.storage.set_site_blocking_enabled("www.example.com", False)
        )
        self.assertEqual(
            self.storage.get_site_blocking_exceptions(),
            {"example.com"},
        )
        self.storage.set_site_blocking_enabled("example.com", True)
        self.assertEqual(self.storage.get_site_blocking_exceptions(), set())


if __name__ == "__main__":
    unittest.main()
