from pathlib import Path
import tempfile
import unittest

from _SERVICOS_.folder_upload import collect_folder_upload_files


class FolderUploadTests(unittest.TestCase):
    def test_returns_files_in_relative_path_order_with_root_file_first(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "hen-Navi"
            nested = root / "nucleo" / "subpasta"
            nested.mkdir(parents=True)
            (root / "zeta.txt").write_text("z", encoding="utf-8")
            (root / "alpha.txt").write_text("a", encoding="utf-8")
            (root / ".hidden").write_text("h", encoding="utf-8")
            (root / "nucleo" / "main.py").write_text("m", encoding="utf-8")
            (nested / "config.py").write_text("c", encoding="utf-8")

            result = collect_folder_upload_files(str(root))

            self.assertEqual(
                [
                    Path(path).relative_to(root).as_posix()
                    for path in result
                ],
                [
                    ".hidden",
                    "alpha.txt",
                    "zeta.txt",
                    "nucleo/main.py",
                    "nucleo/subpasta/config.py",
                ],
            )
            self.assertTrue(
                all("/./" not in path and not path.endswith("/.") for path in result)
            )

    def test_uses_qt_folder_enumeration_when_no_file_exists_at_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "nested-only"
            child = root / "child"
            child.mkdir(parents=True)
            (child / "file.txt").write_text("x", encoding="utf-8")

            self.assertIsNone(collect_folder_upload_files(str(root)))

    def test_empty_folder_returns_no_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            self.assertEqual(collect_folder_upload_files(temporary), [])

    def test_rejects_non_directory_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            file_path = Path(temporary) / "file.txt"
            file_path.write_text("x", encoding="utf-8")

            with self.assertRaises(ValueError):
                collect_folder_upload_files(str(file_path))


if __name__ == "__main__":
    unittest.main()
