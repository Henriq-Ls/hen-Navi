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
        cls.page_class = next(
            node
            for node in cls.browser_tree.body
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

    def test_microphone_permission_is_requested_explicitly(self):
        self.assertIn(
            "self.permissionRequested.connect(self._on_permission_requested)",
            self.browser_source,
        )
        handler = self.page_methods["_on_permission_requested"]
        handler_source = ast.get_source_segment(self.browser_source, handler)
        self.assertIn("MediaAudioCapture", handler_source)
        self.assertIn("MediaAudioVideoCapture", handler_source)
        self.assertIn("permission.grant()", handler_source)
        self.assertIn("permission.deny()", handler_source)
        self.assertIn("QMessageBox.StandardButton.No", handler_source)

    def test_file_selection_uses_a_controlled_non_native_qt_dialog(self):
        choose_files = self.page_methods["chooseFiles"]
        choose_files_source = ast.get_source_segment(
            self.browser_source,
            choose_files,
        )
        self.assertIn("QFileDialog.Option.DontUseNativeDialog", choose_files_source)
        self.assertIn("dialog.exec()", choose_files_source)
        self.assertIn("dialog.selectedFiles()", choose_files_source)
        self.assertNotIn("super().chooseFiles", choose_files_source)

    def test_folder_upload_uses_folder_mode_and_returns_all_files(self):
        choose_files = self.page_methods["chooseFiles"]
        choose_files_source = ast.get_source_segment(
            self.browser_source,
            choose_files,
        )
        self.assertIn("FileSelectUploadFolder", choose_files_source)
        self.assertIn("QFileDialog.FileMode.Directory", choose_files_source)
        self.assertIn("QFileDialog.Option.ShowDirsOnly", choose_files_source)
        self.assertIn("collect_folder_upload_files(selected[0])", choose_files_source)
        self.assertIn("if is_folder:\n            return selected", choose_files_source)
        self.assertIn("self._translate_directory_filter(dialog)", choose_files_source)

    def test_upload_picker_is_portuguese_sorted_and_has_common_locations(self):
        localize_dialog = self.page_methods["_localize_upload_dialog"]
        localize_source = ast.get_source_segment(
            self.browser_source,
            localize_dialog,
        )
        self.assertIn("QFileDialog.DialogLabel.LookIn", localize_source)
        self.assertIn("QFileDialog.DialogLabel.Accept", localize_source)
        self.assertIn("dialog.setSidebarUrls", localize_source)
        self.assertIn("tree_view.sortByColumn(0, Qt.SortOrder.AscendingOrder)", localize_source)

        shortcuts = self.page_methods["_upload_sidebar_shortcuts"]
        shortcuts_source = ast.get_source_segment(self.browser_source, shortcuts)
        self.assertIn("StandardLocation.DesktopLocation", shortcuts_source)
        self.assertIn("StandardLocation.DownloadLocation", shortcuts_source)
        self.assertIn("StandardLocation.HomeLocation", shortcuts_source)

    def test_folder_filter_label_is_translated_without_changing_selection(self):
        translate_filter = self.page_methods["_translate_directory_filter"]
        translate_source = ast.get_source_segment(
            self.browser_source,
            translate_filter,
        )
        self.assertIn('"directories"', translate_source)
        self.assertIn('"folders"', translate_source)
        self.assertIn("filter_combo.setItemText", translate_source)
        self.assertIn('TEXTO_UI["upload_dialog_directories"]', translate_source)

    def test_upload_dialog_respects_accepted_mime_types_and_cancellation(self):
        choose_files = self.page_methods["chooseFiles"]
        choose_files_source = ast.get_source_segment(
            self.browser_source,
            choose_files,
        )
        self.assertIn("accepted_mime_types", choose_files_source)
        self.assertIn("return []", choose_files_source)
        self.assertIn("QMimeDatabase", self.browser_source)
        self.assertIn("mime_type.globPatterns()", self.browser_source)

    def test_permission_and_folder_dialog_text_is_configured(self):
        expected = {
            "permission_request_title",
            "permission_request_message",
            "permission_microphone",
            "permission_microphone_camera",
            "upload_files_title",
            "upload_folder_title",
            "upload_all_files_filter",
            "upload_dialog_location_label",
            "upload_dialog_name_label",
            "upload_dialog_type_label",
            "upload_dialog_directories",
            "upload_dialog_select_folder",
            "upload_dialog_open",
            "upload_dialog_save",
            "upload_dialog_cancel",
            "upload_dialog_desktop",
            "upload_dialog_downloads",
            "upload_dialog_home",
            "upload_dialog_back",
            "upload_dialog_back_description",
            "upload_dialog_forward",
            "upload_dialog_forward_description",
            "upload_dialog_parent",
            "upload_dialog_parent_description",
            "upload_dialog_new_folder",
            "upload_dialog_new_folder_description",
            "upload_dialog_list_view",
            "upload_dialog_list_view_description",
            "upload_dialog_detail_view",
            "upload_dialog_detail_view_description",
        }
        self.assertTrue(expected.issubset(self.ui_keys), expected - self.ui_keys)


if __name__ == "__main__":
    unittest.main()
