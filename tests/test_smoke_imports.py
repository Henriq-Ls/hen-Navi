import importlib
import importlib.util
import unittest


PYSIDE6_AVAILABLE = importlib.util.find_spec("PySide6") is not None


@unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 não está instalado neste ambiente.")
class QtImportSmokeTests(unittest.TestCase):
    def test_browser_window_and_feature_modules_import(self):
        for module_name in (
            "_CONFIGURA_.temas",
            "_ULTILIDADES_.icones",
            "_CONFIGURA_.theme_engine",
            "_APP_.startpage",
            "browser",
            "_APP_.main_window",
            "_APP_.atalhos_dialog",
        ):
            with self.subTest(modulo=module_name):
                importlib.import_module(module_name)

    def test_browser_window_has_capture_callbacks(self):
        from browser import BrowserWindow

        for method_name in (
            "show_capture_menu",
            "capture_visible_page",
            "capture_full_page",
            "save_page_as_pdf",
            "_show_capture_saved",
            "_show_pdf_saved",
            "_show_capture_error",
        ):
            with self.subTest(metodo=method_name):
                self.assertTrue(callable(getattr(BrowserWindow, method_name, None)))


if __name__ == "__main__":
    unittest.main()
