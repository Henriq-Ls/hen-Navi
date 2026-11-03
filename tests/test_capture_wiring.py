import ast
from pathlib import Path
import unittest


class CaptureWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(__file__).resolve().parents[1] / "browser.py"
        cls.source_text = source.read_text(encoding="utf-8")
        tree = ast.parse(cls.source_text)
        project_root = Path(__file__).resolve().parents[1]
        cls.window = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "BrowserWindow"
        )
        cls.methods = {
            node.name
            for node in cls.window.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        cls.icon_calls = {
            node.func.id
            for node in ast.walk(cls.window)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        icon_source = project_root / "_ULTILIDADES_" / "icones.py"
        icon_tree = ast.parse(icon_source.read_text(encoding="utf-8"))
        cls.icon_functions = {
            node.name
            for node in icon_tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        cls.config_text = (
            project_root / "_CONFIGURA_" / "__init__.py"
        ).read_text(encoding="utf-8")
        cls.theme_text = (project_root / "theme_engine.py").read_text(
            encoding="utf-8"
        )

    def test_capture_and_settings_handlers_exist(self):
        expected = {
            "_build_settings_menu",
            "_build_capture_menu",
            "show_capture_menu",
            "capture_visible_page",
            "capture_full_page",
            "save_page_as_pdf",
            "_show_capture_saved",
            "_show_pdf_saved",
            "_show_capture_error",
            "open_app_data",
            "clear_browser_cache",
        }
        self.assertTrue(expected.issubset(self.methods), expected - self.methods)

    def test_search_engine_menu_is_below_theme_and_persisted(self):
        theme_position = self.source_text.index(
            'self.theme_menu = settings_menu.addMenu('
        )
        search_position = self.source_text.index(
            'self.search_engine_menu = settings_menu.addMenu('
        )
        blocker_position = self.source_text.index(
            'settings_menu.addSection(TEXTO_UI["blocker_name"])'
        )
        self.assertLess(theme_position, search_position)
        self.assertLess(search_position, blocker_position)
        self.assertIn("def set_search_engine(self, search_engine: str)", self.source_text)
        self.assertIn("settings[CHAVE_BUSCADOR_PADRAO] = search_engine", self.source_text)
        self.assertIn("self.controller.search_engine", self.source_text)

    def test_ui_text_lookups_exist_in_config(self):
        config_tree = ast.parse(self.config_text)
        ui_assignment = next(
            node
            for node in config_tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "TEXTO_UI"
                for target in node.targets
            )
        )
        configured_keys = {
            ast.literal_eval(key) for key in ui_assignment.value.keys
        }
        project_root = Path(__file__).resolve().parents[1]
        used_keys = set()
        for source_path in project_root.rglob("*.py"):
            source_tree = ast.parse(source_path.read_text(encoding="utf-8"))
            used_keys.update(
                ast.literal_eval(node.slice)
                for node in ast.walk(source_tree)
                if isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Name)
                and node.value.id == "TEXTO_UI"
                and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)
            )
        self.assertEqual(sorted(used_keys - configured_keys), [])

    def test_custom_theme_editor_is_available_and_saved(self):
        self.assertIn('TEXTO_UI["theme_custom"]', self.source_text)
        self.assertIn('TEXTO_UI["theme_customize"]', self.source_text)
        self.assertIn("self.controller.set_custom_theme(dialog.custom_theme())", self.source_text)
        self.assertIn("settings[CHAVE_TEMA_PERSONALIZADO] = normalized", self.source_text)
        self.assertIn("custom_theme=self.controller.custom_theme", self.source_text)
        self.assertIn('"google": ("Google",', self.config_text)
        self.assertIn('"bing": ("Bing",', self.config_text)

    def test_toolbar_symbols_use_the_shared_icon_module(self):
        expected = {
            "ico_favorito_vazio",
            "ico_favorito",
            "ico_bloqueador",
            "ico_video_download",
            "ico_inspecionar",
            "ico_ia",
            "ico_nova_aba",
            "ico_fechar_aba",
            "ico_anotacoes",
            "ico_captura",
            "ico_imagem",
            "ico_pdf",
            "ico_tema",
            "ico_janela_fechar",
            "ico_janela_maximizar",
            "ico_janela_restaurar",
            "ico_janela_minimizar",
        }
        self.assertTrue(expected.issubset(self.icon_calls), expected - self.icon_calls)
        self.assertTrue(expected.issubset(self.icon_functions), expected - self.icon_functions)
        self.assertIn('COR_FAVORITO_VAZIO = "#FFFFFF"', self.config_text)
        self.assertIn(
            "COR_FAVORITO_VAZIO",
            (Path(__file__).resolve().parents[1] / "_ULTILIDADES_" / "icones.py")
            .read_text(encoding="utf-8"),
        )

    def test_toolbar_button_order(self):
        markers = (
            "self.toolbar.addWidget(self.brand_button)",
            "self.toolbar.addWidget(self.blocker_button)",
            "self.toolbar.addWidget(self.favorite_button)",
            "self.toolbar.addWidget(self.video_download_button)",
            "self.toolbar.addWidget(self.capture_button)",
            "self.toolbar.addWidget(self.notes_button)",
            "self.toolbar.addWidget(self.ai_button)",
        )
        positions = [self.source_text.index(marker) for marker in markers]
        self.assertEqual(positions, sorted(positions))
        self.assertLess(
            self.source_text.index("self.toolbar.addWidget(self.brand_button)"),
            self.source_text.index("self.back_action ="),
        )
        self.assertNotIn("self.tools_button", self.source_text)
        self.assertNotIn("self.tools_menu", self.source_text)
        self.assertIn("self.capture_button.setMenu(self.capture_menu)", self.source_text)
        self.assertIn(
            "self.video_download_button.setDefaultAction(self.video_download_action)",
            self.source_text,
        )
        self.assertIn("self.notes_button.setDefaultAction(self.notes_action)", self.source_text)
        self.assertIn("self.ai_button.setEnabled(False)", self.source_text)

    def test_window_controls_form_a_fixed_right_edge_sidebar(self):
        markers = (
            'self.close_window_button = self._add_window_control_button(',
            'self.maximize_window_button = self._add_window_control_button(',
            'self.minimize_window_button = self._add_window_control_button(',
            'self.window_controls_toolbar.addSeparator()',
            'self._add_sidebar_action_button(self.inspect_action)',
            'self._add_sidebar_action_button(self.open_app_data_action)',
            'self._add_sidebar_action_button(self.clear_cache_action)',
        )
        positions = [self.source_text.index(marker) for marker in markers]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("Qt.WindowType.FramelessWindowHint", self.source_text)
        self.assertIn("Qt.ToolBarArea.RightToolBarArea", self.source_text)
        self.assertIn("self.addToolBar(", self.source_text)
        self.assertIn("self.window_controls_toolbar.hide()", self.source_text)
        self.assertNotIn("window_controls_dock", self.source_text)

    def test_blank_top_menu_bar_is_removed_and_saved_layout_keeps_controls_right(self):
        self.assertIn("Qt.WindowType.CustomizeWindowHint", self.source_text)
        self.assertIn("menu_bar = self.menuBar()", self.source_text)
        self.assertIn("menu_bar.setFixedHeight(0)", self.source_text)
        self.assertIn("menu_bar.hide()", self.source_text)
        self.assertIn(
            "self.addToolBar(\n            Qt.ToolBarArea.RightToolBarArea,\n            self.window_controls_toolbar,",
            self.source_text,
        )
        self.assertNotIn("window_controls_dock", self.source_text)
        main_window_source = (
            Path(__file__).resolve().parents[1] / "_APP_" / "main_window.py"
        ).read_text(encoding="utf-8")
        self.assertIn("self._pin_window_controls_to_right()", main_window_source)
        self.assertIn("VERSAO_ESTADO_JANELA", main_window_source)

    def test_side_panels_start_below_navigation_and_switch_in_one_slot(self):
        self.assertIn("self._window_content_layout = QVBoxLayout", self.source_text)
        self.assertIn("self._window_content_layout.insertWidget(0, self.toolbar)", self.source_text)
        self.assertIn("self._body_row_layout.addWidget(self._side_panel_stack)", self.source_text)
        self.assertIn("self._side_panel_stack.addWidget(self.notes_dock)", self.source_text)
        self.assertIn("self._side_panel_stack.addWidget(self.video_download_dock)", self.source_text)
        self.assertIn("self._side_panel_stack.addWidget(self.inspector_dock)", self.source_text)
        self.assertIn("self._side_panel_stack.setCurrentWidget(panel)", self.source_text)
        self.assertNotIn("self.addDockWidget(", self.source_text)
        browser_tree = ast.parse(self.source_text)
        qt_widgets_imports = {
            alias.name
            for node in ast.walk(browser_tree)
            if isinstance(node, ast.ImportFrom)
            and node.module == "PySide6.QtWidgets"
            for alias in node.names
        }
        self.assertIn("QDockWidget", qt_widgets_imports)

    def test_inspector_uses_active_page_and_redacts_form_values(self):
        self.assertIn("self._sync_inspector_page()", self.source_text)
        inspector_source = (
            Path(__file__).resolve().parents[1] / "_APP_" / "inspector.py"
        ).read_text(encoding="utf-8")
        self.assertIn("page.inspectionElementSelected.connect(", inspector_source)
        self.assertIn("control.removeAttribute(\"value\")", inspector_source)
        self.assertIn("element.textContent = {text}", inspector_source)
        self.assertIn("element.style.backgroundColor", inspector_source)

    def test_tab_close_button_has_red_hover_feedback(self):
        self.assertIn("class TabCloseButton(QToolButton):", self.source_text)
        self.assertIn("self.setIcon(ico_fechar_aba_hover())", self.source_text)
        self.assertIn("ico_fechar_aba_hover", self.icon_functions)
        self.assertIn("QToolButton#tabCloseButton:hover", self.config_text)
        self.assertIn("QToolButton#tabCloseButton:hover", self.theme_text)


if __name__ == "__main__":
    unittest.main()
