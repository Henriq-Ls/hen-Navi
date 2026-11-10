import ast
from pathlib import Path
import re
import unittest


class CaptureWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(__file__).resolve().parents[1] / "browser.py"
        project_root = Path(__file__).resolve().parents[1]
        cls.browser_source_text = source.read_text(encoding="utf-8")
        cls.manager_source_text = (
            project_root
            / "_APP_"
            / "barra_direita_tools"
            / "manager.py"
        ).read_text(encoding="utf-8")
        cls.panels_source_text = (
            project_root / "_BROWSER_" / "window_panels.py"
        ).read_text(encoding="utf-8")
        cls.capture_source_text = (
            project_root / "_BROWSER_" / "window_capture.py"
        ).read_text(encoding="utf-8")
        cls.source_text = (
            cls.browser_source_text
            + "\n\n"
            + cls.manager_source_text
            + "\n\n"
            + cls.panels_source_text
            + "\n\n"
            + cls.capture_source_text
        )
        tree = ast.parse(cls.source_text)
        cls.ai_config_text = (
            project_root / "_APP_" / "ai_config.py"
        ).read_text(encoding="utf-8")
        cls.sidebar_source_text = (
            project_root
            / "_APP_"
            / "barra_direita_tools"
            / "sidebar.py"
        ).read_text(encoding="utf-8")
        cls.window_controls_source_text = (
            project_root / "_BROWSER_" / "window_controls.py"
        ).read_text(encoding="utf-8")
        cls.window_frame_source_text = (
            project_root / "_BROWSER_" / "window_frame.py"
        ).read_text(encoding="utf-8")
        cls.performance_panel_text = (
            project_root
            / "_APP_"
            / "barra_direita_tools"
            / "performance.py"
        ).read_text(encoding="utf-8")
        cls.performance_status_text = (
            project_root / "_APP_" / "performance_status.py"
        ).read_text(encoding="utf-8")
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
        capture_tree = ast.parse(cls.capture_source_text)
        capture_mixin = next(
            node
            for node in capture_tree.body
            if isinstance(node, ast.ClassDef)
            and node.name == "BrowserWindowCaptureMixin"
        )
        cls.methods.update(
            node.name
            for node in capture_mixin.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        cls.icon_calls = {
            node.func.id
            for node in (
                list(ast.walk(cls.window))
                + list(ast.walk(ast.parse(cls.window_frame_source_text)))
                + list(ast.walk(capture_tree))
            )
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        sidebar_tree = ast.parse(cls.sidebar_source_text)
        cls.icon_calls.update(
            node.func.id
            for node in ast.walk(sidebar_tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        )
        manager_tree = ast.parse(cls.manager_source_text)
        cls.icon_calls.update(
            node.func.id
            for node in ast.walk(manager_tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        )
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
        cls.interceptor_text = (
            project_root / "_SERVICOS_" / "adblocker.py"
        ).read_text(encoding="utf-8")
        cls.theme_text = (
            project_root / "_CONFIGURA_" / "theme_engine.py"
        ).read_text(
            encoding="utf-8"
        )
        cls.theme_editor_text = (
            project_root / "_APP_" / "theme_editor.py"
        ).read_text(encoding="utf-8")

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
        self.assertLess(theme_position, search_position)
        settings_method = self.source_text.split(
            "    def _build_settings_menu(self):",
            1,
        )[1].split("\n    def ", 1)[0]
        self.assertIn(
            "self.main_menu.addSeparator()\n"
            "        settings_menu = self.main_menu.addMenu(",
            settings_method,
        )
        self.assertIn(
            "self.security_performance_menu.addAction("
            "self.blocker_settings_action)",
            settings_method,
        )
        self.assertIn(
            "self.security_performance_menu.addAction("
            "self.blocker_toggle_site_action)",
            settings_method,
        )
        self.assertNotIn("settings_menu.addSection(", settings_method)
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

    def test_video_codec_diagnostic_is_grouped_under_security_menu(self):
        self.assertIn('TEXTO_UI["media_diagnostic"]', self.source_text)
        self.assertIn(
            "self.security_performance_menu.addAction("
            "self.media_diagnostic_action)",
            self.source_text,
        )
        self.assertIn("def check_media_codecs(self, *_)", self.source_text)
        self.assertIn("MEDIA_CAPABILITY_SCRIPT", self.source_text)

    def test_gpu_diagnostic_is_grouped_under_security_menu(self):
        self.assertIn('TEXTO_UI["gpu_diagnostic"]', self.source_text)
        self.assertIn(
            "self.security_performance_menu.addAction("
            "self.gpu_diagnostic_action)",
            self.source_text,
        )
        self.assertIn("def open_gpu_diagnostic(self, *_)", self.source_text)
        self.assertIn("GRAPHICS_CAPABILITY_SCRIPT", self.source_text)
        self.assertIn("graphics_diagnostic_snapshot", self.source_text)
        self.assertIn(
            "def _show_gpu_diagnostic_report(self, page_capabilities)",
            self.source_text,
        )
        gpu_method = self.source_text.split(
            "def open_gpu_diagnostic(self, *_):",
            1,
        )[1].split("\n    def ", 1)[0]
        self.assertIn("runJavaScript(", gpu_method)
        self.assertNotIn("_create_tab(", gpu_method)
        self.assertNotIn("URL_DIAGNOSTICO_GPU", self.source_text)
        self.assertNotIn("URL_DIAGNOSTICO_GPU", self.config_text)
        self.assertIn(
            "def _reset_navigation_samples(self)",
            self.performance_panel_text,
        )
        self.assertIn(
            "reset_navigation_samples()",
            self.performance_panel_text,
        )
        self.assertIn("graphics_diagnostic_snapshot()", self.performance_panel_text)

    def test_site_security_performance_and_blocker_actions_share_one_menu(self):
        for action_name in (
            "site_security_action",
            "password_manager_action",
            "site_privacy_action",
            "performance_action",
            "blocker_settings_action",
            "blocker_toggle_site_action",
        ):
            if action_name == "performance_action":
                self.assertIn(
                    "context.security_performance_menu.addAction(\n"
                    "            parent.performance_action",
                    self.manager_source_text,
                )
            else:
                self.assertIn(
                    "self.security_performance_menu.addAction("
                    f"self.{action_name})",
                    self.source_text,
                )
        self.assertIn(
            '"security_performance_menu": "Segurança e desempenho"',
            self.config_text,
        )

    def test_performance_monitor_is_in_the_right_sidebar(self):
        self.assertIn("self.tools_manager.initialize()", self.browser_source_text)
        self.assertIn("class RightToolsManager", self.manager_source_text)
        self.assertIn("def _toggle_performance_panel(self, *_)", self.source_text)
        self.assertIn("if self.performance_panel is None:", self.source_text)
        self.assertIn(
            "self._add_panel(self.performance_panel)",
            self.source_text,
        )
        self.assertIn(
            "context.sidebar.add_action_button(\n            parent.performance_action",
            self.source_text,
        )
        self.assertIn(
            'context.sidebar.add_action_button(\n            parent.performance_action,\n            "performanceMonitorButton",\n            at_top=True,',
            self.source_text,
        )
        self.assertIn('"performance": (', self.source_text)
        self.assertIn(
            "self._status_bar.addWidget(self.performance_readout)",
            self.source_text,
        )
        self.assertNotIn(
            "self._status_bar.addPermanentWidget(self.performance_readout)",
            self.source_text,
        )
        self.assertIn(
            "self.performance_monitor.start()",
            self.source_text,
        )
        self.assertIn("PerformanceStatusReadout(", self.source_text)
        self.assertIn("PerformanceMonitor(self)", self.source_text)
        self.assertIn("self.performance_panel.start_monitoring()", self.source_text)
        self.assertIn("self.performance_panel.stop_monitoring()", self.source_text)
        self.assertIn("self._timer.setInterval(1000)", self.performance_panel_text)
        self.assertIn("self._timer.start()", self.performance_panel_text)
        self.assertIn("self._timer.stop()", self.performance_panel_text)
        self.assertNotIn("import psutil", self.performance_panel_text)
        self.assertIn("NetworkMetricsSampler", self.performance_status_text)
        self.assertIn("self._network_sampler.sample()", self.performance_status_text)
        self.assertIn("network_download_bytes_per_second", self.performance_panel_text)
        self.assertIn("network_upload_bytes_per_second", self.performance_panel_text)
        self.assertIn("SAMPLE_INTERVAL_MS = 3000", self.performance_status_text)
        self.assertIn("self._sample_timer.start()", self.performance_status_text)

    def test_data_saver_blocks_only_heavy_resource_categories(self):
        resource_block = re.search(
            r"_DATA_SAVER_RESOURCE_TYPES\s*=\s*frozenset\(\s*\{(.*?)\}\s*\)",
            self.interceptor_text,
            re.DOTALL,
        )
        self.assertIsNotNone(resource_block)
        resource_types = set(
            re.findall(r"ResourceType\.(ResourceType\w+)", resource_block.group(1))
        )
        self.assertEqual(
            resource_types,
            {
                "ResourceTypeImage",
                "ResourceTypeMedia",
                "ResourceTypePrefetch",
            },
        )
        self.assertIn(
            "data_saver_enabled\n                and resource_type in "
            "_DATA_SAVER_RESOURCE_TYPES",
            self.interceptor_text,
        )
        self.assertIn("def save_data_saver_enabled", self.source_text)
        self.assertIn(
            "settings[CHAVE_ECONOMIA_DADOS] = value",
            self.source_text,
        )
        self.assertIn("checkable=True", self.source_text)
        self.assertIn("self._set_data_saver_from_button", self.source_text)

    def test_custom_theme_editor_is_available_and_saved(self):
        self.assertIn('TEXTO_UI["theme_custom"]', self.source_text)
        self.assertIn('TEXTO_UI["theme_customize"]', self.source_text)
        self.assertIn(
            "dialog.saveRequested.connect(self.controller.set_custom_theme)",
            self.source_text,
        )
        self.assertIn("settings[CHAVE_TEMA_PERSONALIZADO] = normalized", self.source_text)
        self.assertIn("custom_theme=self.controller.custom_theme", self.source_text)
        self.assertIn('"google": ("Google",', self.config_text)
        self.assertIn('"bing": ("Bing",', self.config_text)

    def test_theme_editor_saves_without_closing_and_has_a_shortcut(self):
        self.assertIn(
            "save_button.clicked.connect(self._save_and_continue)",
            self.theme_editor_text,
        )
        self.assertIn(
            "self.saveRequested.emit(self.custom_theme())",
            self.theme_editor_text,
        )
        self.assertNotIn(
            "button_box.accepted.connect(self.accept)",
            self.theme_editor_text,
        )
        self.assertIn('atalho("tema_personalizado")', self.source_text)
        self.assertIn("self.addAction(self.theme_customize_action)", self.source_text)

    def test_theme_size_metrics_update_the_sidebar_and_footer(self):
        self.assertIn("ICON_SIZE = 18", self.sidebar_source_text)
        self.assertIn(
            "self.button_size = max(self.BUTTON_SIZE - 4, self.icon_size + 8)",
            self.sidebar_source_text,
        )
        self.assertIn(
            "self.setFixedWidth(max(width_from_icon, self.button_size + 8))",
            self.sidebar_source_text,
        )
        self.assertIn("LARGURA_BARRA_CONTROLES_JANELA = 34", self.config_text)
        self.assertIn("self.sidebar_toolbar.apply_metrics(", self.source_text)
        self.assertIn("self.favorites_status_bar.apply_metrics(", self.source_text)
        self.assertIn("self._status_bar.setFixedHeight(footer_height)", self.source_text)

    def test_ai_editor_explains_key_storage_and_requires_a_model(self):
        self.assertIn('TEXTO_UI["ai_key_saved_notice"]', self.ai_config_text)
        self.assertIn('TEXTO_UI["ai_key_will_save"]', self.ai_config_text)
        self.assertIn('if not payload["model"]:', self.ai_config_text)
        self.assertIn('TEXTO_UI["ai_model_required"]', self.ai_config_text)

    def test_toolbar_symbols_use_the_shared_icon_module(self):
        expected = {
            "ico_favorito_vazio",
            "ico_favorito",
            "ico_bloqueador",
            "ico_economia_dados",
            "ico_video_download",
            "ico_inspecionar",
            "ico_ia",
            "ico_nova_aba",
            "ico_fechar_aba",
            "ico_anotacoes",
            "ico_traduzir",
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
        icon_source = (
            Path(__file__).resolve().parents[1] / "_ULTILIDADES_" / "icones.py"
        ).read_text(encoding="utf-8")
        self.assertIn('icone("fa5s.star", _cor_favorito_vazio())', icon_source)
        self.assertIn(
            "visible_icon.addPixmap(pixmap, QIcon.Mode.Disabled, QIcon.State.Off)",
            icon_source,
        )
        self.assertIn('QToolButton#favoriteButton {{ color: {theme["icon"]}; }}', self.theme_text)

    def test_toolbar_button_order(self):
        markers = (
            "self.toolbar.addWidget(self.brand_button)",
            "self.back_action = self._make_action(",
            "self.forward_action = self._make_action(",
            "self.reload_action = self._make_action(",
            "self.toolbar.addAction(action)",
            "self.address_bar = QLineEdit(self)",
            "self.toolbar.addWidget(self.address_bar)",
            "self._create_top_page_buttons()",
            "self._create_top_window_controls()",
            "self._finish_window_layout()",
        )
        positions = [self.source_text.index(marker) for marker in markers]
        self.assertEqual(positions, sorted(positions))
        for moved_button in (
            "blocker_button",
            "data_saver_button",
            "favorite_button",
            "capture_button",
            "video_download_button",
            "notes_button",
            "ai_button",
            "translate_button",
        ):
            self.assertNotIn(
                f"self.toolbar.addWidget(self.{moved_button})",
                self.source_text,
            )
        self.assertLess(
            self.source_text.index("self.toolbar.addWidget(self.brand_button)"),
            self.source_text.index("self.back_action ="),
        )
        self.assertIn("self.addAction(self.home_shortcut_action)", self.source_text)
        self.assertNotIn(
            "self.toolbar.addAction(self.home_shortcut_action)",
            self.source_text,
        )
        self.assertNotIn("self.tools_button", self.source_text)
        self.assertNotIn("self.tools_menu", self.source_text)
        self.assertIn("self.capture_button.setMenu(self.capture_menu)", self.source_text)
        self.assertIn(
            "context.video_download_button.setDefaultAction(\n"
            "            parent.video_download_action",
            self.source_text,
        )
        self.assertIn(
            "context.notes_button.setDefaultAction(parent.notes_action)",
            self.source_text,
        )
        self.assertIn(
            "context.ai_button.setDefaultAction(parent.ai_action)",
            self.source_text,
        )
        self.assertIn(
            "self._translate_callback",
            self.sidebar_source_text,
        )
        self.assertIn(
            "translate_callback=self.translate_current_page",
            self.source_text,
        )
        self.assertNotIn("self.ai_button.setEnabled(False)", self.source_text)

    def test_translation_button_uses_configured_ai_and_existing_consent(self):
        self.assertIn("def translate_current_page(self, *_)", self.source_text)
        self.assertIn("self.ai_dock.request_translation()", self.source_text)
        self.assertIn('TEXTO_UI["ai_translate_prompt"]', self.source_text)
        self.assertIn("self._confirm_ai_cloud_send(provider)", self.source_text)

    def test_capture_manager_is_owned_by_the_right_tools_coordinator(self):
        self.assertIn("def _create_capture_manager(self)", self.manager_source_text)
        self.assertIn(
            "self.capture_manager = CaptureManager(parent)",
            self.manager_source_text,
        )
        self.assertIn(
            'self._callback("capture_image_saved")',
            self.manager_source_text,
        )
        self.assertIn(
            '"capture_image_saved": self._show_capture_saved',
            self.source_text,
        )
        self.assertNotIn(
            "self.capture_manager = CaptureManager(self)",
            self.source_text,
        )

    def test_page_actions_move_above_the_existing_sidebar_tools(self):
        page_markers = (
            "self.blocker_button = self._add_top_page_button(",
            "self.data_saver_button = self._add_top_page_button(",
            "self.favorite_button = self._add_top_page_button(",
        )
        page_positions = [
            self.source_text.index(marker) for marker in page_markers
        ]
        self.assertEqual(page_positions, sorted(page_positions))
        self.assertLess(
            self.source_text.index("self.toolbar.addWidget(self.address_bar)"),
            self.source_text.index("self._create_top_page_buttons()"),
        )

        sidebar_page_markers = (
            "self.capture_button = self._add_page_button(",
            "self.video_download_button = self._add_page_button(",
            "self.notes_button = self._add_page_button(",
            "self.ai_button = self._add_page_button(",
            "self.translate_button = self._add_page_button(",
            "self.addSeparator()",
        )
        sidebar_positions = [
            self.sidebar_source_text.index(marker)
            for marker in sidebar_page_markers
        ]
        self.assertEqual(sidebar_positions, sorted(sidebar_positions))
        for moved_button in (
            "blocker_button",
            "data_saver_button",
            "favorite_button",
        ):
            self.assertNotIn(f"self.{moved_button} =", self.sidebar_source_text)

        action_markers = (
            "self.context.sidebar.add_action_button(\n            self.context.history_action",
            "context.sidebar.add_action_button(\n            context.downloads_action",
            "context.sidebar.add_action_button(\n            parent.inspect_action",
            "context.sidebar.add_action_button(\n            parent.devtools_action",
            "context.sidebar.add_action_button(\n            parent.performance_action",
        )
        action_positions = [
            self.source_text.index(marker) for marker in action_markers
        ]
        self.assertEqual(action_positions, sorted(action_positions))
        self.assertIn('(self.clear_cache_action, "clearCacheButton")', self.source_text)
        self.assertIn('(self.open_app_data_action, "openAppDataButton")', self.source_text)
        self.assertIn(
            "self.sidebar_toolbar = RightToolsSidebar(\n"
            "            self._body_row,\n"
            "            translate_callback=self.translate_current_page,\n"
            "            icon_size=theme[\"sidebar_icon_size_px\"],\n"
            "        )",
            self.source_text,
        )
        self.assertLess(
            action_positions[3],
            action_positions[4],
        )
        self.assertIn(
            'self.sidebar_toolbar.add_action_button(\n            self.explorer_action,\n            "explorerButton",\n            at_top=True,',
            self.source_text,
        )

    def test_window_controls_follow_page_buttons_in_the_top_toolbar(self):
        page_position = self.source_text.index("self._create_top_page_buttons()")
        controls_position = self.source_text.index("self._create_top_window_controls()")
        self.assertLess(page_position, controls_position)
        self.assertIn("self.toolbar.addSeparator()", self.source_text)
        self.assertNotIn("window_controls_toolbar", self.source_text)
        control_order = (
            'self.minimize_window_button = self._add_top_window_control_button(',
            'self.maximize_window_button = self._add_top_window_control_button(',
            'self.close_window_button = self._add_top_window_control_button(',
        )
        control_positions = [
            self.source_text.index(marker) for marker in control_order
        ]
        self.assertEqual(control_positions, sorted(control_positions))
        self.assertIn("self._toggle_maximize_restore", self.source_text)
        self.assertNotIn("snap_layouts_button", self.source_text)
        self.assertNotIn("_show_snap_layout_menu", self.source_text)

    def test_sidebar_actions_are_not_duplicated_in_menus_and_keep_shortcuts(self):
        self.assertNotIn("menu.addAction(self.history_action)", self.source_text)
        self.assertNotIn("menu.addAction(self.downloads_action)", self.source_text)
        self.assertNotIn(
            "settings_menu.addAction(self.open_app_data_action)",
            self.source_text,
        )
        self.assertNotIn(
            "settings_menu.addAction(self.clear_cache_action)",
            self.source_text,
        )
        self.assertIn("self.addAction(self.history_action)", self.source_text)
        self.assertIn("self.addAction(self.open_app_data_action)", self.source_text)
        self.assertIn('atalho("historico")', self.source_text)
        self.assertIn('atalho("appdata")', self.source_text)
        self.assertIn("menu.addAction(self.favorites_action)", self.source_text)

    def test_window_controls_stay_in_the_top_toolbar_after_layout_restore(self):
        self.assertIn("Qt.WindowType.CustomizeWindowHint", self.source_text)
        self.assertIn("menu_bar = self.menuBar()", self.source_text)
        self.assertIn("menu_bar.setFixedHeight(0)", self.source_text)
        self.assertIn("menu_bar.hide()", self.source_text)
        self.assertIn("self.toolbar.setMovable(False)", self.source_text)
        self.assertIn("self._create_top_window_controls()", self.source_text)
        self.assertNotIn("window_controls_toolbar", self.source_text)
        main_window_source = (
            Path(__file__).resolve().parents[1] / "_APP_" / "main_window.py"
        ).read_text(encoding="utf-8")
        self.assertIn("VERSAO_ESTADO_JANELA", main_window_source)
        self.assertIn("VERSAO_ESTADO_JANELA = 6", self.config_text)

    def test_side_panels_start_below_navigation_and_switch_in_one_slot(self):
        self.assertIn("self._window_content_layout = QVBoxLayout", self.source_text)
        self.assertIn("self._window_content_layout.insertWidget(0, self.toolbar)", self.source_text)
        self.assertIn("self._body_row_layout.addWidget(self._side_panel_container)", self.source_text)
        self.assertIn("self._side_panel_layout.addWidget(self._side_panel_tabs_inset)", self.source_text)
        self.assertIn("tab_bar.sizeHint().height()", self.source_text)
        self.assertIn("self._side_panel_layout.addWidget(self._side_panel_stack, 1)", self.source_text)
        for panel_name in (
            "notes_dock",
            "video_download_dock",
            "downloads_dock",
            "inspector_dock",
            "devtools_panel",
            "ai_dock",
            "performance_panel",
        ):
            if panel_name == "performance_panel":
                self.assertIn(
                    "self._add_panel(self.performance_panel)",
                    self.manager_source_text,
                )
            else:
                self.assertIn(
                    f"self._add_panel(parent.{panel_name})",
                    self.manager_source_text,
                )
        self.assertIn("panel.setTitleBarWidget(None)", self.source_text)
        self.assertIn("self._side_panel_stack.setCurrentWidget(panel)", self.source_text)
        self.assertIn("self.close_side_panel_button.clicked.connect(self._close_side_panel)", self.source_text)
        self.assertIn("def _close_side_panel(self, *_)", self.source_text)
        self.assertNotIn("self.addDockWidget(", self.source_text)
        browser_tree = ast.parse(self.source_text)
        build_interface = next(
            node
            for node in self.window.body
            if isinstance(node, ast.FunctionDef) and node.name == "_build_interface"
        )
        build_calls = {
            node.func.attr
            for node in ast.walk(build_interface)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertIn("initialize", build_calls)
        self.assertIn("def _create_ai(self)", self.manager_source_text)
        qt_widgets_imports = {
            alias.name
            for node in ast.walk(browser_tree)
            if isinstance(node, ast.ImportFrom)
            and node.module == "PySide6.QtWidgets"
            for alias in node.names
        }
        self.assertIn("QDockWidget", qt_widgets_imports)

    def test_new_ollama_provider_prefills_url_and_loads_local_models(self):
        self.assertIn(
            "self._platform_changed(self.platform_combo.currentIndex())",
            self.ai_config_text,
        )
        self.assertIn(
            'if self.platform_combo.currentData()[0] == "ollama":',
            self.ai_config_text,
        )
        self.assertIn(
            'if platform == "ollama" and not self._loading_provider:',
            self.ai_config_text,
        )
        self.assertIn('"http://localhost:11434"', self.ai_config_text)

    def test_ai_request_setup_errors_stay_in_panel(self):
        handle_ai_request = next(
            node
            for node in self.window.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "_handle_ai_request"
        )
        settings_calls = [
            node
            for node in ast.walk(handle_ai_request)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "open_ai_settings"
        ]
        self.assertEqual(settings_calls, [])
        self.assertIn(
            'parent.ai_dock.settingsRequested.connect(\n            self._callback("open_ai_settings")',
            self.manager_source_text,
        )

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
        self.assertIn(
            "class TabCloseButton(QToolButton):",
            self.window_controls_source_text,
        )
        self.assertIn(
            "self.setIcon(ico_fechar_aba_hover())",
            self.window_controls_source_text,
        )
        self.assertIn("ico_fechar_aba_hover", self.icon_functions)
        self.assertIn("QToolButton#tabCloseButton:hover", self.config_text)
        self.assertIn("QToolButton#tabCloseButton:hover", self.theme_text)


if __name__ == "__main__":
    unittest.main()
