import ast
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class BrowserPermissionAndUploadWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.browser_source = (PROJECT_ROOT / "browser.py").read_text(
            encoding="utf-8"
        )
        cls.browser_tree = ast.parse(cls.browser_source)
        cls.page_source = (PROJECT_ROOT / "_BROWSER_" / "page.py").read_text(
            encoding="utf-8"
        )
        page_tree = ast.parse(cls.page_source)
        cls.page_class = next(
            node
            for node in page_tree.body
            if isinstance(node, ast.ClassDef) and node.name == "BrowserPage"
        )
        cls.page_methods = {
            node.name: node
            for node in cls.page_class.body
            if isinstance(node, ast.FunctionDef)
        }
        config_tree = ast.parse(
            (PROJECT_ROOT / "_CONFIGURA_" / "__init__.py").read_text(
                encoding="utf-8"
            )
        )
        ui_assignment = next(
            node
            for node in config_tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "TEXTO_UI"
                for target in node.targets
            )
        )
        cls.ui_keys = {ast.literal_eval(key) for key in ui_assignment.value.keys}
        explorer_assignment = next(
            node
            for node in config_tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name)
                and target.id == "EXPLORER_TEXTOS"
                for target in node.targets
            )
        )
        cls.explorer_text_keys = {
            ast.literal_eval(key)
            for key in explorer_assignment.value.keys
        }

    def test_microphone_permission_is_requested_explicitly(self):
        self.assertIn(
            "self.permissionRequested.connect(self._on_permission_requested)",
            self.page_source,
        )
        handler = self.page_methods["_on_permission_requested"]
        handler_source = ast.get_source_segment(self.page_source, handler)
        self.assertIn("MediaAudioCapture", handler_source)
        self.assertIn("MediaAudioVideoCapture", handler_source)
        self.assertIn("permission.grant()", handler_source)
        self.assertIn("permission.deny()", handler_source)
        self.assertIn("QMessageBox.StandardButton.No", handler_source)

    def test_file_selection_uses_the_project_explorer_for_every_mode(self):
        choose_files = self.page_methods["chooseFiles"]
        choose_files_source = ast.get_source_segment(
            self.page_source,
            choose_files,
        )
        self.assertIn("Explorer.get_open_file_name", choose_files_source)
        self.assertIn("Explorer.get_open_file_names", choose_files_source)
        self.assertIn("Explorer.get_existing_directory", choose_files_source)
        self.assertIn("Explorer.get_save_file_name", choose_files_source)
        self.assertNotIn("QFileDialog", choose_files_source)
        self.assertNotIn("super().chooseFiles", choose_files_source)

    def test_folder_upload_uses_folder_mode_and_returns_all_files(self):
        choose_files = self.page_methods["chooseFiles"]
        choose_files_source = ast.get_source_segment(
            self.page_source,
            choose_files,
        )
        self.assertIn("FileSelectUploadFolder", choose_files_source)
        self.assertIn("Explorer.get_existing_directory", choose_files_source)
        self.assertIn("collect_folder_upload_files(selected[0])", choose_files_source)
        self.assertIn("if is_folder:\n            return selected", choose_files_source)

    def test_upload_mime_filters_are_passed_to_the_project_explorer(self):
        choose_files = self.page_methods["chooseFiles"]
        choose_source = ast.get_source_segment(
            self.page_source,
            choose_files,
        )
        self.assertIn(
            "self._upload_name_filters(\n                        accepted_mime_types\n                    )",
            choose_source,
        )
        self.assertIn("mime_type.globPatterns()", self.page_source)
        self.assertIn("QMimeDatabase", self.page_source)
        self.assertIn("TEXTO_UI[\"upload_all_files_filter\"]", self.page_source)

    def test_upload_dialog_respects_accepted_mime_types_and_cancellation(self):
        choose_files = self.page_methods["chooseFiles"]
        choose_files_source = ast.get_source_segment(
            self.page_source,
            choose_files,
        )
        self.assertIn("accepted_mime_types", choose_files_source)
        self.assertIn("return []", choose_files_source)
        self.assertIn("remember_location=remember_location", choose_files_source)

    def test_permission_and_explorer_dialog_text_is_configured(self):
        expected = {
            "permission_request_title",
            "permission_request_message",
            "permission_microphone",
            "permission_microphone_camera",
            "upload_files_title",
            "upload_folder_title",
            "upload_all_files_filter",
        }
        self.assertTrue(expected.issubset(self.ui_keys), expected - self.ui_keys)
        self.assertTrue(
            {
                "title_open_file",
                "title_open_files",
                "title_select_folder",
                "title_save_file",
                "organize",
                "trash_confirm_title",
            }.issubset(self.explorer_text_keys)
        )

    def test_all_application_file_dialogs_are_replaced_by_the_project_explorer(self):
        expected_calls = {
            "_BROWSER_/page.py": (
                "Explorer.get_open_file_name",
                "Explorer.get_open_file_names",
                "Explorer.get_existing_directory",
                "Explorer.get_save_file_name",
            ),
            "_BROWSER_/window_capture.py": (
                "ExplorerMode.MANAGE",
            ),
            "_APP_/explorer_tab.py": (
                "Explorer.get_existing_directory",
                "Explorer.get_save_file_name",
            ),
            "_APP_/barra_direita_tools/download_video.py": (
                "Explorer.get_existing_directory",
            ),
            "_APP_/barra_direita_tools/anotacoes.py": (
                "Explorer.get_save_file_name",
            ),
            "_APP_/browser_downloads.py": ("ExplorerMode.MANAGE",),
            "_APP_/barra_direita_tools/browser_downloads.py": (
                "ExplorerMode.MANAGE",
            ),
        }
        for relative_path, calls in expected_calls.items():
            path = PROJECT_ROOT / relative_path
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("QFileDialog", source, path.name)
            for call in calls:
                self.assertIn(call, source, f"{relative_path}: {call}")

        browser_source = (PROJECT_ROOT / "browser.py").read_text(encoding="utf-8")
        capture_source = (
            PROJECT_ROOT / "_BROWSER_" / "window_capture.py"
        ).read_text(encoding="utf-8")
        self.assertIn("ExplorerMode.MANAGE", capture_source)
        self.assertIn("fixed_root=appdata.pasta_raiz", browser_source)
        self.assertIn("inspection_mode=True", browser_source)
        self.assertIn("app_data_private_unavailable", browser_source)

    def test_explorer_persists_last_path_in_appdata_except_in_private_mode(self):
        source = (
            PROJECT_ROOT / "_ULTILIDADES_" / "explorer.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "self._ler_estado_persistido() if self._remember_location else {}",
            source,
        )
        self.assertIn('if not self._remember_location:\n            return', source)
        self.assertIn('"ultimo_diretorio": caminho', source)
        self.assertIn('config["explorer"] = estado', source)
        self.assertIn("appdata.salvar_config(config)", source)


if __name__ == "__main__":
    unittest.main()
