import unittest
from pathlib import Path

from _APP_.private_startpage import (
    cleanup_private_start_pages,
    create_private_start_page,
    remove_private_start_page,
)


class PrivateStartPageTests(unittest.TestCase):
    def test_temporary_page_is_removed_and_stale_pages_are_cleaned(self):
        active_path = create_private_start_page("<html>private</html>")
        stale_path = create_private_start_page("<html>stale</html>")
        self.assertTrue(Path(active_path).is_file())
        self.assertTrue(Path(stale_path).is_file())

        cleanup_private_start_pages()
        self.assertFalse(Path(active_path).exists())
        self.assertFalse(Path(stale_path).exists())

        replacement_path = create_private_start_page("<html>closing</html>")
        remove_private_start_page(replacement_path)
        self.assertFalse(Path(replacement_path).exists())


if __name__ == "__main__":
    unittest.main()
