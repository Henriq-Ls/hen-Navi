"""Perfil, páginas WebEngine, abas, sessão e downloads do hen-Nave."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from time import perf_counter
from urllib.parse import urlsplit

from _CONFIGURA_ import (
    ARQUIVO_BANCO,
    ARQUIVO_INICIO,
    ARQUIVO_INICIO_ANONIMO,
    ARQUIVO_LISTA_BLOQUEIO,
    BUSCADOR_PADRAO,
    BUSCADORES_PESQUISA,
    CHAVE_BUSCADOR_PADRAO,
    IMAGEM_ICO,
    STATUS_CARREGAMENTO_MS,
    STATUS_CURTO_MS,
    STATUS_DOWNLOAD_MS,
    EXPLORER_DEFAULT_IGNORED_NAMES,
    EXPLORER_MAX_CHARS,
    EXPLORER_MAX_DEPTH,
    EXPLORER_MAX_ITEMS,
    EXPLORER_MAX_LINES,
    EXPLORER_MAX_SECONDS,
    FONTE_PIXEL_ARQUIVO,
    CHAVE_BLOQUEADOR_ATIVO,
    CHAVE_ECONOMIA_DADOS,
    CHAVE_URL_LISTA_BLOQUEIO,
    LARGURA_ENDERECO_MINIMA,
    LIMITE_RECENTES_INICIO,
    NOME_PERFIL_WEB,
    STATUS_DOWNLOAD_INICIO_MS,
    TEMAS,
    TEXTO_UI,
    TAMANHO_BOTAO_CONTROLE_JANELA,
    TAMANHO_ICONE_CONTROLE_JANELA,
    TEMA_PADRAO,
    URL_LISTA_BLOQUEIO_PADRAO,
    VERSAO_APP,
    ZOOM_INCREMENTO,
    ZOOM_INICIAL,
    ZOOM_MAXIMO,
    ZOOM_MINIMO,
    atalho,
)
from _LOGS_ import log
from _APPDATA_ import appdata
from _SERVICOS_.performance_diagnostics import record_page_load
from _SERVICOS_.graphics_diagnostics import (
    GRAPHICS_CAPABILITY_SCRIPT,
    graphics_diagnostic_snapshot,
)
from _THREADS_ import thread_manager
from _THREADS_.ai_assistant import AiProviderWorker
from _BROWSER_.page import BrowserPage
from _BROWSER_.profile_lifecycle import AnonymousProfileLease
from _BROWSER_.url_schemes import register_custom_url_scheme as _register_custom_url_scheme
from _BROWSER_.window_controls import (
    BrandMenuButton,
    TabCloseButton,
    _set_button_icon_or_fallback,
)
from _BROWSER_.window_panels import BrowserWindowPanelsMixin
from _BROWSER_.window_frame import BrowserWindowFrameMixin
from _BROWSER_.window_capture import BrowserWindowCaptureMixin
from _SERVICOS_.explorer_filesystem import ExplorerLimits
from _SERVICOS_.explorer_settings import ExplorerSettingsStore
from _CONFIGURA_.temas import (
    CHAVES_CORES_PERSONALIZADAS,
    CHAVE_TEMA_PERSONALIZADO,
    TEMA_PERSONALIZADO,
)
from PySide6.QtCore import (
    QBuffer,
    QEvent,
    QIODevice,
    QObject,
    QTimer,
    QStandardPaths,
    QStringListModel,
    QSize,
    Qt,
    QUrl,
    Signal,
)
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QFont,
    QFontDatabase,
    QIcon,
    QKeySequence,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QCompleter,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QSizePolicy,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtWebEngineCore import (
    QWebEngineDownloadRequest,
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineSettings,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

from _APP_.Navegador import BrowserTabs
from _APP_.atalhos_dialog import ShortcutsDialog
from _APP_.ai_config import AiSettingsDialog
from _APP_.bloqueador_dialog import BlockerSettingsDialog
from _APP_.barra_direita_tools import (
    FavoritesDialog,
    HistoryDialog,
    NotesDock,
    RightToolsContext,
    RightToolsManager,
    RightToolsSidebar,
)
from _APP_.favorites_bar import FavoritesStatusBar
from _APP_.search_suggestions import HomeSearchBridge, SearchSuggestionService
from _APP_.explorer_tab import ExplorerTab
from _APP_.file_preview import FilePreviewTab
from _APP_.media_support import MEDIA_CAPABILITY_SCRIPT, summarize_media_capabilities
from _APP_.performance_status import (
    PerformanceMonitor,
    PerformanceStatusReadout,
)
from _APP_.password_manager import (
    PASSWORD_SAVE_CANCEL_FALLBACK_SCRIPT,
    PASSWORD_SAVE_RESUME_SCRIPT,
    PasswordManagerDialog,
    SaveLoginDialog,
    _READ_LOGIN_SCRIPT,
)
from _APP_.security_tools import SiteSecurityDialog
from _APP_.site_privacy import SitePrivacyDialog
from _APP_.theme_editor import CustomThemeDialog
from _ULTILIDADES_.icones import (
    ico_abrir,
    ico_anotacoes,
    ico_anonimo,
    ico_atalhos,
    ico_atualizar,
    ico_avancar,
    ico_bloqueador,
    ico_captura,
    ico_config,
    ico_downloads,
    ico_endereco,
    ico_economia_dados,
    ico_favorito,
    ico_favorito_vazio,
    ico_favoritos,
    ico_fechar_aba,
    ico_fechar,
    ico_ferramentas,
    ico_historico,
    ico_ia,
    ico_imagem,
    ico_info,
    ico_janela,
    ico_janela_fechar,
    ico_janela_maximizar,
    ico_janela_minimizar,
    ico_limpar,
    ico_localizar,
    ico_inspecionar,
    ico_nova_aba,
    ico_pdf,
    ico_tema,
    ico_video_download,
    ico_voltar,
    ico_zoom_mais,
    ico_zoom_menos,
    ico_zoom_redefinir,
)
from _ULTILIDADES_.popups import (
    criar_popup,
    popup_aviso,
    popup_erro,
    popup_info,
    popup_pergunta,
)
from _SERVICOS_.ai_provider_store import ProviderStore, ProviderStoreError
from _SERVICOS_.search_suggestions import collect_site_suggestions
from _SERVICOS_.web_credential_store import (
    WebCredentialStore,
    WebCredentialStoreError,
    origin_for_url,
)
from _SERVICOS_.adblock_rules import (
    BUILTIN_BLOCKLIST,
    BlocklistFile,
    BlocklistMatcher,
    parse_blocklist,
)
from _SERVICOS_.adblocker import AdBlockInterceptor, BlocklistDownloadThread
from _APP_.private_startpage import (
    cleanup_private_start_pages,
    create_private_start_page,
    write_private_start_page,
)
from _APP_.startpage import generate_start_page
from _APPDATA_.storage import BrowserStorage
from _ULTILIDADES_.explorer import Explorer
from _ULTILIDADES_.site_utils import extract_site_host, is_valid_https_url
from _ULTILIDADES_.utils import is_http_url, resolve_address, search_url
from _CONFIGURA_.theme_engine import (
    normalizar_tema_personalizado,
    obter_tema,
    stylesheet_for_theme,
)


MAX_TAB_TITLE_CHARS = 40


def register_custom_url_scheme():
    """Registra o esquema interno antes da criação de QApplication."""
    _register_custom_url_scheme()


class BrowserController(QObject):
    """Controlador único para perfis, janelas, páginas iniciais e sessão."""

    blockerSettingsChanged = Signal()

    def __init__(self, application: QApplication):
        super().__init__(application)
        self.application = application
        cleanup_private_start_pages(
            os.path.join(appdata.pasta_cache, ARQUIVO_INICIO_ANONIMO)
        )
        self.storage = BrowserStorage(os.path.join(appdata.pasta_config, ARQUIVO_BANCO))
        self._app_settings = appdata.ler_config()
        if not isinstance(self._app_settings, dict):
            self._app_settings = {}
        saved_theme = self._app_settings.get("tema", TEMA_PADRAO)
        self.custom_theme = normalizar_tema_personalizado(
            self._app_settings.get(CHAVE_TEMA_PERSONALIZADO)
        )
        self.theme_id = (
            saved_theme
            if isinstance(saved_theme, str)
            and (saved_theme in TEMAS or saved_theme == TEMA_PERSONALIZADO)
            else TEMA_PADRAO
        )
        saved_search_engine = self._app_settings.get(
            CHAVE_BUSCADOR_PADRAO,
            BUSCADOR_PADRAO,
        )
        self.search_engine = (
            saved_search_engine
            if isinstance(saved_search_engine, str)
            and saved_search_engine in BUSCADORES_PESQUISA
            else BUSCADOR_PADRAO
        )
        self._pixel_font_id = -1
        self._pixel_font_family = ""
        self._apply_application_theme()
        self.blocker_enabled = bool(
            self._app_settings.get(CHAVE_BLOQUEADOR_ATIVO, True)
        )
        self.data_saver_enabled = bool(
            self._app_settings.get(CHAVE_ECONOMIA_DADOS, False)
        )
        configured_url = str(
            self._app_settings.get(
                CHAVE_URL_LISTA_BLOQUEIO,
                URL_LISTA_BLOQUEIO_PADRAO,
            )
        ).strip()
        self.blocklist_url = configured_url if is_valid_https_url(configured_url) else ""
        self.blocklist_file = BlocklistFile(
            os.path.join(appdata.pasta_config, ARQUIVO_LISTA_BLOQUEIO)
        )
        try:
            domains = self.blocklist_file.ensure()
            if not domains:
                raise ValueError("A lista local não contém domínios válidos.")
        except (OSError, UnicodeError, ValueError) as error:
            log.erro("BrowserController", "blocklist", str(error))
            domains = parse_blocklist(BUILTIN_BLOCKLIST)
            try:
                self.blocklist_file.replace(BUILTIN_BLOCKLIST)
            except OSError as write_error:
                log.erro("BrowserController", "blocklist", str(write_error))
        self.blocklist_matcher = BlocklistMatcher(domains)
        self.normal_windows: list[BrowserWindow] = []
        self.private_windows: list[BrowserWindow] = []
        self.restoring = False
        self._restore_pending = 0
        self._shutting_down = False
        self.active_downloads: dict[int, QWebEngineDownloadRequest] = {}
        self._download_profiles: dict[int, QWebEngineProfile] = {}
        self._download_windows: dict[int, BrowserWindow] = {}
        self._download_entry_ids: dict[int, int | None] = {}
        self._blocklist_threads: list[BlocklistDownloadThread] = []

        self.profile = QWebEngineProfile(NOME_PERFIL_WEB, self)
        self.profile.setPersistentStoragePath(appdata.pasta_raiz)
        self.profile.setCachePath(appdata.pasta_cache)
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
        )
        self.configure_profile(self.profile)
        self.normal_interceptor = AdBlockInterceptor(
            self.blocklist_matcher,
            enabled=self.blocker_enabled,
            data_saver_enabled=self.data_saver_enabled,
            exceptions=self.storage.get_site_blocking_exceptions(),
            parent=self,
        )
        self.profile.setUrlRequestInterceptor(self.normal_interceptor)
        self.profile.downloadRequested.connect(self._on_download_requested)
        self.application.aboutToQuit.connect(self._shutdown)
        self.application.aboutToQuit.connect(thread_manager.encerrar_todas)
        self._write_start_pages()
        self.performance_monitor = PerformanceMonitor(self)
        self.application.aboutToQuit.connect(self.performance_monitor.stop)

    @staticmethod
    def configure_profile(profile: QWebEngineProfile):
        settings = profile.settings()
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.FullScreenSupportEnabled,
            True,
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled,
            True,
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows,
            True,
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalStorageEnabled,
            True,
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
            False,
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls,
            False,
        )

    def _apply_application_theme(self):
        theme = obter_tema(self.theme_id, custom_theme=self.custom_theme)
        self.application.setProperty("henNaveTheme", self.theme_id)
        for color_key in CHAVES_CORES_PERSONALIZADAS:
            self.application.setProperty(
                f"henNaveTheme_{color_key}",
                theme[color_key],
            )
        self.application.setStyleSheet(
            stylesheet_for_theme(
                self.theme_id,
                custom_theme=self.custom_theme,
            )
        )

        font_family = theme["font_ui"]
        if self._pixel_font_id < 0 and os.path.isfile(FONTE_PIXEL_ARQUIVO):
            self._pixel_font_id = QFontDatabase.addApplicationFont(
                FONTE_PIXEL_ARQUIVO
            )
            if self._pixel_font_id >= 0:
                families = QFontDatabase.applicationFontFamilies(
                    self._pixel_font_id
                )
                self._pixel_font_family = families[0] if families else ""
        if self.theme_id == "retro_16bit":
            font_family = self._pixel_font_family or theme["font_fallback"]
        font = QFont(font_family)
        font.setPixelSize(theme["font_size_px"])
        self.application.setFont(font)

    def set_theme(self, theme_id: str):
        if (
            not isinstance(theme_id, str)
            or (theme_id not in TEMAS and theme_id != TEMA_PERSONALIZADO)
        ):
            raise ValueError(f"Tema desconhecido: {theme_id}")
        if (
            theme_id == self.theme_id
            and self._app_settings.get("tema") == theme_id
        ):
            for window in self.normal_windows + self.private_windows:
                window.update_theme_actions()
            return

        settings = appdata.ler_config()
        if not isinstance(settings, dict):
            settings = {}
        settings["tema"] = theme_id
        if (
            theme_id == TEMA_PERSONALIZADO
            and CHAVE_TEMA_PERSONALIZADO not in settings
        ):
            settings[CHAVE_TEMA_PERSONALIZADO] = self.custom_theme
        appdata.salvar_config(settings)
        self._app_settings = settings
        self.theme_id = theme_id
        self._apply_application_theme()
        for window in self.normal_windows + self.private_windows:
            window.apply_theme()
        self.refresh_home_pages()

    def set_custom_theme(self, custom_theme: object):
        """Salva a paleta e a tipografia e ativa o tema personalizado."""
        normalized = normalizar_tema_personalizado(custom_theme)
        settings = appdata.ler_config()
        if not isinstance(settings, dict):
            settings = {}
        settings[CHAVE_TEMA_PERSONALIZADO] = normalized
        settings["tema"] = TEMA_PERSONALIZADO
        appdata.salvar_config(settings)

        self._app_settings = settings
        self.custom_theme = normalized
        self.theme_id = TEMA_PERSONALIZADO
        self._apply_application_theme()
        for window in self.normal_windows + self.private_windows:
            window.apply_theme()
        self.refresh_home_pages()

    def set_search_engine(self, search_engine: str):
        if (
            not isinstance(search_engine, str)
            or search_engine not in BUSCADORES_PESQUISA
        ):
            raise ValueError(
                TEXTO_UI["search_engine_invalid"].format(
                    engine=search_engine
                )
            )
        if (
            search_engine == self.search_engine
            and self._app_settings.get(CHAVE_BUSCADOR_PADRAO) == search_engine
        ):
            for window in self.normal_windows + self.private_windows:
                window.update_search_engine_actions()
            return

        settings = appdata.ler_config()
        if not isinstance(settings, dict):
            settings = {}
        settings[CHAVE_BUSCADOR_PADRAO] = search_engine
        appdata.salvar_config(settings)
        self._app_settings = settings
        self.search_engine = search_engine
        for window in self.normal_windows + self.private_windows:
            window.update_search_engine_actions()

    def start(self) -> "BrowserWindow":
        urls = [
            url for url in self.storage.load_session()
            if is_http_url(url)
        ]
        self.restoring = bool(urls)
        self._restore_pending = len(urls)
        window = self.create_window(private=False, restore_urls=urls, show=False)
        window.tabs.setCurrentIndex(0)
        window.show()
        self.performance_monitor.start()
        return window

    def create_window(
        self,
        *,
        private: bool = False,
        restore_urls: list[str] | None = None,
        show: bool = True,
    ) -> "BrowserWindow":
        from _APP_.main_window import MainWindow

        private_path = (
            create_private_start_page(self._private_start_page_html())
            if private
            else ""
        )
        lease = (
            AnonymousProfileLease(
                self,
                private_path,
                self.blocklist_matcher,
                self.blocker_enabled,
                configure_profile=self.configure_profile,
                data_saver_enabled=self.data_saver_enabled,
            )
            if private
            else None
        )
        if lease is not None:
            lease.profile.downloadRequested.connect(self._on_download_requested)
        try:
            window = MainWindow(
                controller=self,
                private=private,
                restore_urls=restore_urls or [],
                profile_lease=lease,
            )
        except Exception:
            if lease:
                lease.request_close()
            raise
        if private:
            self.private_windows.append(window)
        else:
            self.normal_windows.append(window)
        if show:
            window.show()
            window.raise_()
            window.activateWindow()
        if not private:
            self.notify_session_change()
        return window

    def start_page_path(self) -> str:
        return os.path.join(appdata.pasta_cache, ARQUIVO_INICIO)

    def _start_page_items_with_favicons(
        self,
        items: list[dict],
    ) -> list[dict]:
        return [
            {
                **item,
                "favicon": self.storage.get_favicon(str(item.get("url", ""))),
            }
            for item in items
        ]

    def _private_start_page_html(self) -> str:
        return generate_start_page(
            self._start_page_items_with_favicons(self.storage.get_favorites()),
            [],
            private=True,
            theme_id=self.theme_id,
            custom_theme=self.custom_theme,
        )

    def _write_start_pages(self):
        favorites = self._start_page_items_with_favicons(
            self.storage.get_favorites()
        )
        recent = self._start_page_items_with_favicons(
            self.storage.recent_unique(LIMITE_RECENTES_INICIO)
        )
        search_queries = self.storage.recent_search_queries("", 40)
        page_html = generate_start_page(
            favorites,
            recent,
            search_queries,
            private=False,
            theme_id=self.theme_id,
            custom_theme=self.custom_theme,
        )
        path = Path(self.start_page_path())
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_text(page_html, encoding="utf-8")
        except OSError as error:
            log.erro("BrowserController", "_write_start_pages", str(error))

    def refresh_home_pages(self, *_):
        self._write_start_pages()
        for window in self.normal_windows + self.private_windows:
            if window.private and window.profile_lease:
                try:
                    write_private_start_page(
                        window.profile_lease.start_page_path,
                        self._private_start_page_html(),
                    )
                except OSError as error:
                    log.erro(
                        "BrowserController",
                        "refresh_private_start_page",
                        str(error),
                    )
            window.refresh_start_pages()

    @property
    def blocklist_count(self) -> int:
        return len(self.blocklist_matcher.snapshot())

    def save_blocker_settings(self, enabled: bool, url: str) -> None:
        clean_url = (url or "").strip()
        if clean_url and not is_valid_https_url(clean_url):
            raise ValueError("A URL da lista precisa usar HTTPS.")
        settings = appdata.ler_config()
        if not isinstance(settings, dict):
            settings = {}
        settings[CHAVE_BLOQUEADOR_ATIVO] = bool(enabled)
        settings[CHAVE_URL_LISTA_BLOQUEIO] = clean_url
        appdata.salvar_config(settings)
        self._app_settings = settings
        self.blocker_enabled = bool(enabled)
        self.blocklist_url = clean_url
        self.normal_interceptor.set_enabled(self.blocker_enabled)
        for window in self.private_windows:
            if window.profile_lease:
                window.profile_lease.interceptor.set_enabled(self.blocker_enabled)
        self.blockerSettingsChanged.emit()

    def save_data_saver_enabled(self, enabled: bool) -> None:
        value = bool(enabled)
        settings = appdata.ler_config()
        if not isinstance(settings, dict):
            settings = {}
        settings[CHAVE_ECONOMIA_DADOS] = value
        appdata.salvar_config(settings)
        self._app_settings = settings
        self.data_saver_enabled = value
        self.normal_interceptor.set_data_saver_enabled(value)

    def save_site_blocker_enabled(
        self,
        host: str,
        enabled: bool,
        *,
        private: bool = False,
        interceptor: AdBlockInterceptor | None = None,
    ) -> bool:
        if private:
            return bool(interceptor and interceptor.set_site_enabled(host, enabled))
        if not self.storage.set_site_blocking_enabled(host, enabled):
            return False
        return self.normal_interceptor.set_site_enabled(host, enabled)

    def install_blocklist_text(self, content: str) -> int:
        domains = self.blocklist_file.replace(content)
        self.blocklist_matcher.replace(domains)
        self.blockerSettingsChanged.emit()
        return len(domains)

    def start_blocklist_update(self, url: str, dialog: BlockerSettingsDialog) -> None:
        if not is_valid_https_url(url):
            raise ValueError("A URL da lista precisa usar HTTPS.")
        thread = BlocklistDownloadThread(url, parent=self)
        thread.downloaded.connect(
            dialog.receive_downloaded_list,
            Qt.ConnectionType.QueuedConnection,
        )
        thread.failed.connect(
            dialog.receive_download_error,
            Qt.ConnectionType.QueuedConnection,
        )
        thread.finished.connect(self._on_blocklist_thread_finished)
        self._blocklist_threads.append(thread)
        thread.start()

    def _on_blocklist_thread_finished(self, *_):
        thread = self.sender()
        if thread in self._blocklist_threads:
            self._blocklist_threads.remove(thread)

    def _urls_for_windows(self, windows: list["BrowserWindow"]) -> list[str]:
        urls: list[str] = []
        for window in windows:
            urls.extend(window.session_urls())
        return urls

    def notify_session_change(self):
        if self.restoring or not self.normal_windows or self._shutting_down:
            return
        self.storage.save_session(self._urls_for_windows(self.normal_windows))

    def complete_restore_page(self, page: BrowserPage):
        if not page.restore_pending:
            return
        page.restore_pending = False
        if not self.restoring:
            return
        self._restore_pending = max(0, self._restore_pending - 1)
        if self._restore_pending == 0:
            self.restoring = False
            self.notify_session_change()

    def cancel_restore_page(self, page: BrowserPage):
        self.complete_restore_page(page)

    def unregister_window(self, window: "BrowserWindow"):
        if window.private:
            if window in self.private_windows:
                self.private_windows.remove(window)
            if window.profile_lease:
                window.profile_lease.request_close()
            return

        if window not in self.normal_windows:
            return
        if self.restoring:
            self.restoring = False
            self._restore_pending = 0
            self.normal_windows.remove(window)
            return

        if len(self.normal_windows) == 1:
            self.storage.save_session(self._urls_for_windows([window]))
            self.normal_windows.remove(window)
            return

        self.normal_windows.remove(window)
        self.notify_session_change()

    def _window_for_profile(self, profile: QWebEngineProfile) -> "BrowserWindow | None":
        active = self.application.activeWindow()
        windows = self.normal_windows + self.private_windows
        if active in windows and active.profile is profile:
            return active
        return next((window for window in windows if window.profile is profile), None)

    def _window_for_download(self, profile, source_page):
        if source_page is not None:
            for window in self.normal_windows + self.private_windows:
                if window.profile is not profile:
                    continue
                for index in range(window.tabs.count()):
                    view = window.tabs.widget(index)
                    if (
                        isinstance(view, QWebEngineView)
                        and view.page() == source_page
                    ):
                        return window
        return self._window_for_profile(profile)

    def _on_download_requested(self, download: QWebEngineDownloadRequest):
        profile = self.sender()
        if not isinstance(profile, QWebEngineProfile):
            download.cancel()
            return
        source_page = download.page()
        window = self._window_for_download(profile, source_page)
        if window is None:
            download.cancel()
            return

        downloads_dir = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DownloadLocation
        )
        if not downloads_dir:
            downloads_dir = str(Path.home())
        Path(downloads_dir).mkdir(parents=True, exist_ok=True)
        suggested = (
            os.path.basename(download.suggestedFileName())
            or TEXTO_UI["download_default_name"]
        )
        target = Explorer.get_save_file_name(
            window,
            caption=TEXTO_UI["download_dialog"],
            directory=downloads_dir,
            name_filters=(TEXTO_UI["download_filter"],),
            initial_name=suggested,
            remember_location=not window.private,
        )
        if not target:
            download.cancel()
            return

        target_path = Path(target)
        download.setDownloadDirectory(str(target_path.parent))
        download.setDownloadFileName(target_path.name)
        entry_id = None
        if window.private:
            if window.downloads_dock is not None:
                window.downloads_dock.add_private_download(
                    id(download),
                    str(target_path),
                    target_path.name,
                )
        else:
            try:
                entry_id = self.storage.record_browser_download(
                    str(target_path),
                    target_path.name,
                )
            except sqlite3.Error as error:
                popup_erro(
                    TEXTO_UI["browser_download_history_error_title"],
                    TEXTO_UI["browser_download_history_error"].format(error=error),
                    window,
                )
                download.cancel()
                return
        self.active_downloads[id(download)] = download
        self._download_profiles[id(download)] = profile
        self._download_windows[id(download)] = window
        self._download_entry_ids[id(download)] = entry_id
        download.stateChanged.connect(self._on_download_state_changed)
        download.receivedBytesChanged.connect(self._on_download_progress)
        download.totalBytesChanged.connect(self._on_download_progress)
        download.accept()
        self._close_popup_download_tab(window, source_page)
        self._refresh_download_panels()
        window.statusBar().showMessage(
            TEXTO_UI["download_started"].format(name=target_path.name),
            STATUS_DOWNLOAD_INICIO_MS,
        )

    def _close_popup_download_tab(self, window, source_page):
        if window is None or source_page is None:
            return
        for index in range(window.tabs.count()):
            view = window.tabs.widget(index)
            if not isinstance(view, QWebEngineView) or view.page() != source_page:
                continue
            if view.property("downloadPopup"):
                window.close_tab(index)
            return

    def _on_download_progress(self, *_):
        download = self.sender()
        if download is None:
            return
        download_key = id(download)
        if download_key not in self.active_downloads:
            return
        window = self._download_windows.get(download_key)
        if window is None or window.downloads_dock is None:
            return
        entry_id = self._download_entry_ids.get(download_key)
        progress_key = download_key if window.private else entry_id
        if progress_key is None:
            return
        window.downloads_dock.update_download_progress(
            progress_key,
            download.receivedBytes(),
            download.totalBytes(),
        )

    def _on_download_state_changed(self, *_):
        download = self.sender()
        if download is None or id(download) not in self.active_downloads:
            return
        state = download.state()
        completed = QWebEngineDownloadRequest.DownloadState.DownloadCompleted
        cancelled = QWebEngineDownloadRequest.DownloadState.DownloadCancelled
        interrupted = QWebEngineDownloadRequest.DownloadState.DownloadInterrupted
        if state not in {completed, cancelled, interrupted}:
            return

        download_key = id(download)
        window = self._download_windows.pop(download_key, None)
        profile = self._download_profiles.pop(id(download), None)
        self.active_downloads.pop(id(download), None)
        entry_id = self._download_entry_ids.pop(download_key, None)
        status = (
            "completed"
            if state == completed
            else "cancelled"
            if state == cancelled
            else "interrupted"
        )
        if entry_id is not None:
            self.storage.update_browser_download(entry_id, status)
        if window is None and profile is not None:
            window = self._window_for_profile(profile)
        if window is not None and window.downloads_dock is not None:
            if window.private:
                window.downloads_dock.update_private_download(download_key, status)
            else:
                window.downloads_dock.refresh()
        if window:
            if state == completed:
                message = TEXTO_UI["download_completed"].format(
                    name=download.downloadFileName()
                )
            elif state == interrupted:
                message = TEXTO_UI["download_failed"]
            else:
                message = TEXTO_UI["download_cancelled"]
            window.statusBar().showMessage(message, STATUS_DOWNLOAD_MS)
        self._refresh_download_panels()

    def _refresh_download_panels(self):
        for window in self.normal_windows + self.private_windows:
            if window.downloads_dock is not None and not window.private:
                window.downloads_dock.refresh()

    def _shutdown(self):
        self._shutting_down = True
        self.storage.close()


class BrowserWindow(
    BrowserWindowPanelsMixin,
    BrowserWindowFrameMixin,
    BrowserWindowCaptureMixin,
    QMainWindow,
):
    """Janela de navegação comum ou anônima."""

    def __init__(
        self,
        controller: BrowserController,
        *,
        private: bool = False,
        restore_urls: list[str] | None = None,
        profile_lease: AnonymousProfileLease | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.CustomizeWindowHint
        )
        menu_bar = self.menuBar()
        menu_bar.setFixedHeight(0)
        menu_bar.hide()
        self.controller = controller
        self.private = private
        self._theme = obter_tema(
            self.controller.theme_id,
            custom_theme=self.controller.custom_theme,
        )
        self.ai_store = ProviderStore(appdata.pasta_config)
        self.web_credential_store = WebCredentialStore(appdata.pasta_config)
        self._ai_workers: list[AiProviderWorker] = []
        self._active_ai_worker: AiProviderWorker | None = None
        self._ai_request_generation = 0
        self._ai_pending_context_key = ""
        self.profile_lease = profile_lease
        self.profile = profile_lease.profile if profile_lease else controller.profile
        self._start_page_path = (
            profile_lease.start_page_path
            if profile_lease
            else controller.start_page_path()
        )
        self.blocker_interceptor = (
            profile_lease.interceptor
            if profile_lease
            else controller.normal_interceptor
        )
        self._blocked_counts_cache = self.blocker_interceptor.counts_snapshot()
        self.notes_dock: NotesDock | None = None
        self.video_download_dock: QWidget | None = None
        self.downloads_dock: QWidget | None = None
        self.performance_panel: QWidget | None = None
        self._closing = False
        self._initializing = True
        self._windows_frame_style_applied = False
        self._fullscreen_active = False
        self._window_state_before_fullscreen = Qt.WindowState.WindowNoState
        self._dialogs: list[QWidget] = []
        self._popup_windows: list[QDialog] = []
        self.search_suggestion_service = SearchSuggestionService(self)
        self.search_suggestion_service.resultsReady.connect(
            self._on_search_suggestions_ready
        )
        self._home_suggestion_bridges: dict[
            str, tuple[BrowserPage, HomeSearchBridge]
        ] = {}
        self._address_suggestion_targets: dict[str, str] = {}
        self._address_suggestion_queries: dict[str, str] = {}
        self._address_suggestion_query = ""
        self.setProperty("privateMode", "true" if private else "false")
        self.setStyleSheet(
            stylesheet_for_theme(
                self.controller.theme_id,
                private=self.private,
                custom_theme=self.controller.custom_theme,
            )
        )
        self._build_interface()
        self._create_tab(home=True, select=True)
        if restore_urls:
            for url in restore_urls:
                self._create_tab(
                    url=url,
                    home=False,
                    select=False,
                    restored=True,
                )
        self.tabs.setCurrentIndex(0)
        self._initializing = False
        self._sync_devtools_page()
        self._update_location_and_favorite()

    def statusBar(self):
        status_bar = getattr(self, "_status_bar", None)
        return status_bar if status_bar is not None else super().statusBar()

    def _build_interface(self):
        theme = self._theme
        footer_height = max(
            theme["footer_height_px"],
            theme["font_size_px"] + 12,
        )
        self._window_content = QWidget(self)
        self._window_content.setObjectName("windowContent")
        self._window_content_layout = QVBoxLayout(self._window_content)
        self._window_content_layout.setContentsMargins(0, 0, 0, 0)
        self._window_content_layout.setSpacing(0)

        self._body_row = QWidget(self._window_content)
        self._body_row.setObjectName("browserBodyRow")
        self._body_row_layout = QHBoxLayout(self._body_row)
        self._body_row_layout.setContentsMargins(0, 0, 0, 0)
        self._body_row_layout.setSpacing(0)

        self._left_panel = QWidget(self._body_row)
        self._left_panel.setObjectName("browserContentPanel")
        self._left_layout = QVBoxLayout(self._left_panel)
        self._left_layout.setContentsMargins(0, 0, 0, 0)
        self._left_layout.setSpacing(0)
        self._body_row_layout.addWidget(self._left_panel, 1)

        self._side_panel_container = QWidget(self._body_row)
        self._side_panel_container.setObjectName("sidePanelContainer")
        self._side_panel_layout = QVBoxLayout(self._side_panel_container)
        self._side_panel_layout.setContentsMargins(0, 0, 0, 0)
        self._side_panel_layout.setSpacing(0)

        self._side_panel_tabs_inset = QWidget(self._side_panel_container)
        self._side_panel_tabs_inset.setObjectName("sidePanelTabsInset")
        self._side_panel_tabs_inset.setFixedHeight(0)
        self._side_panel_layout.addWidget(self._side_panel_tabs_inset)

        self._side_panel_header = QWidget(self._side_panel_container)
        self._side_panel_header.setObjectName("sidePanelHeader")
        side_panel_header_layout = QHBoxLayout(self._side_panel_header)
        side_panel_header_layout.setContentsMargins(10, 4, 6, 4)
        self._side_panel_title = QLabel("", self._side_panel_header)
        self._side_panel_title.setObjectName("sidePanelTitle")
        side_panel_header_layout.addWidget(self._side_panel_title, 1)
        self.close_side_panel_button = QToolButton(self._side_panel_header)
        self.close_side_panel_button.setObjectName("closeSidePanelButton")
        self.close_side_panel_button.setIcon(ico_fechar())
        self.close_side_panel_button.setToolTip(TEXTO_UI["close_side_panel"])
        self.close_side_panel_button.setAccessibleName(
            TEXTO_UI["close_side_panel"]
        )
        self.close_side_panel_button.setAutoRaise(True)
        self.close_side_panel_button.clicked.connect(self._close_side_panel)
        side_panel_header_layout.addWidget(self.close_side_panel_button)
        self._side_panel_layout.addWidget(self._side_panel_header)

        self._side_panel_stack = QStackedWidget(self._side_panel_container)
        self._side_panel_stack.setObjectName("rightSidePanelStack")
        self._side_panel_layout.addWidget(self._side_panel_stack, 1)
        self._side_panel_container.hide()
        self._body_row_layout.addWidget(self._side_panel_container)

        self.sidebar_toolbar = RightToolsSidebar(
            self._body_row,
            translate_callback=self.translate_current_page,
            icon_size=theme["sidebar_icon_size_px"],
        )
        self.capture_button = self.sidebar_toolbar.capture_button
        self.video_download_button = self.sidebar_toolbar.video_download_button
        self.notes_button = self.sidebar_toolbar.notes_button
        self.ai_button = self.sidebar_toolbar.ai_button
        self.translate_button = self.sidebar_toolbar.translate_button
        self._body_row_layout.addWidget(self.sidebar_toolbar)

        self._window_content_layout.addWidget(self._body_row, 1)
        self._active_side_panel: str | None = None

        self.close_window_action = self._make_action(
            TEXTO_UI["window_close"],
            ico_janela_fechar(),
            lambda _checked=False: self.close(),
        )
        self.maximize_window_action = self._make_action(
            TEXTO_UI["window_maximize"],
            ico_janela_maximizar(),
            self._toggle_maximize_restore,
        )
        self.minimize_window_action = self._make_action(
            TEXTO_UI["window_minimize"],
            ico_janela_minimizar(),
            lambda _checked=False: self.showMinimized(),
        )
        self.toolbar = QToolBar(
            TEXTO_UI["navigation_toolbar"],
            self._window_content,
        )
        self.toolbar.setObjectName("navigationToolbar")
        self.toolbar.setMovable(False)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self._window_content_layout.insertWidget(0, self.toolbar)

        self.brand_button = BrandMenuButton(self)
        self.brand_button.setObjectName("brandMenuButton")
        self.brand_button.setIcon(QIcon(IMAGEM_ICO))
        self.brand_button.setIconSize(QSize(16, 16))
        #self.brand_button.setText(TITULO_APP)
        self.brand_button.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self.brand_button.setToolTip(TEXTO_UI["window_brand_tooltip"])
        self.brand_button.setAccessibleName(TEXTO_UI["window_brand_tooltip"])
        self.brand_button.setMinimumHeight(TAMANHO_BOTAO_CONTROLE_JANELA)
        self.toolbar.addWidget(self.brand_button)

        self.back_action = self._make_action(TEXTO_UI["back"], ico_voltar(), self.go_back)
        self.forward_action = self._make_action(TEXTO_UI["forward"], ico_avancar(), self.go_forward)
        self.reload_action = self._make_action(
            TEXTO_UI["reload"],
            ico_atualizar(),
            self.reload_current,
            atalho("recarregar"),
        )
        self.home_shortcut_action = self._make_action(
            TEXTO_UI["home"],
            QIcon(),
            self.go_home,
            atalho("inicio"),
        )
        self.addAction(self.home_shortcut_action)
        for action in (
            self.back_action,
            self.forward_action,
            self.reload_action,
        ):
            self.toolbar.addAction(action)

        self.address_bar = QLineEdit(self)
        self.address_bar.setObjectName("addressBar")
        self.address_bar.setPlaceholderText(TEXTO_UI["address_placeholder"])
        self.address_bar.setToolTip(TEXTO_UI["suggestions_privacy_hint"])
        self.address_bar.setMinimumWidth(LARGURA_ENDERECO_MINIMA)
        self.address_bar.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.address_bar.setClearButtonEnabled(True)
        self.address_bar.returnPressed.connect(self.navigate_address)
        self._address_suggestion_model = QStringListModel(self)
        self.address_completer = QCompleter(self.address_bar)
        self.address_completer.setModel(self._address_suggestion_model)
        self.address_completer.setCaseSensitivity(
            Qt.CaseSensitivity.CaseInsensitive
        )
        self.address_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.address_completer.setCompletionMode(
            QCompleter.CompletionMode.PopupCompletion
        )
        self.address_completer.setMaxVisibleItems(10)
        self.address_bar.setCompleter(self.address_completer)
        self.address_bar.textEdited.connect(self._on_address_text_edited)
        self.address_completer.activated[str].connect(
            self._on_address_suggestion_activated
        )
        self.toolbar.addWidget(self.address_bar)
        self._create_top_page_buttons()

        self.blocker_interceptor.blockedCountChanged.connect(
            self._on_blocked_count_changed,
            Qt.ConnectionType.QueuedConnection,
        )
        self.blocker_interceptor.siteEnabledChanged.connect(
            self._on_site_blocker_changed,
            Qt.ConnectionType.QueuedConnection,
        )
        self.blocker_interceptor.enabledChanged.connect(
            self._on_blocker_global_changed,
            Qt.ConnectionType.QueuedConnection,
        )
        self.blocker_interceptor.dataSaverChanged.connect(
            self._update_data_saver_button,
            Qt.ConnectionType.QueuedConnection,
        )
        self.controller.blockerSettingsChanged.connect(self._update_blocker_button)
        self._update_data_saver_button()

        if self.private:
            self.private_indicator = QToolButton(self)
            self.private_indicator.setObjectName("privateIndicator")
            self.private_indicator.setText(TEXTO_UI["private_short"])
            self.private_indicator.setEnabled(False)
            self.toolbar.addWidget(self.private_indicator)

        self._create_top_window_controls()
        self.main_menu = self._build_menu()
        self._create_explorer_action()
        self.brand_button.setMenu(self.main_menu)

        self.tabs = BrowserTabs(self)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self._on_current_changed)
        self.tabs.set_new_tab_button(self._build_new_tab_button())

        self._left_layout.addWidget(self.tabs, 1)
        self._update_side_panel_tabs_inset()
        self._left_layout.addWidget(self._build_find_bar())
        self._status_bar = QStatusBar(self._left_panel)
        self._status_bar.setSizeGripEnabled(False)
        self._status_bar.setFixedSize(220, footer_height)
        self.performance_readout = PerformanceStatusReadout(
            self.controller.performance_monitor,
            self._status_bar,
        )
        # A mensagem temporária do QStatusBar oculta este indicador normal.
        self._status_bar.addWidget(self.performance_readout)
        self.favorites_status_bar = FavoritesStatusBar(
            self.controller.storage,
            self._left_panel,
            font_size_px=theme["font_size_px"],
            bar_height_px=footer_height,
        )
        self.favorites_status_bar.openRequested.connect(self.open_url_new_tab)
        self.favorites_status_bar.openAllRequested.connect(self.open_favorites)
        self.favorites_status_bar.changed.connect(
            self._refresh_favorite_surfaces
        )
        self._footer_bar = QWidget(self._left_panel)
        self._footer_bar.setObjectName("favoritesAndStatusFooter")
        self._footer_layout = QHBoxLayout(self._footer_bar)
        self._footer_layout.setContentsMargins(0, 0, 0, 0)
        self._footer_layout.setSpacing(0)
        self._footer_layout.addWidget(self.favorites_status_bar, 1)
        self._footer_layout.addWidget(self._status_bar, 0)
        self._left_layout.addWidget(self._footer_bar)
        self.favorites_status_bar.setVisible(True)
        self.setCentralWidget(self._window_content)
        self.find_bar.hide()
        self.tools_manager = RightToolsManager(
            RightToolsContext(
                parent=self,
                controller=self.controller,
                profile=self.profile,
                private=self.private,
                panel_stack=self._side_panel_stack,
                sidebar=self.sidebar_toolbar,
                notes_button=self.notes_button,
                video_download_button=self.video_download_button,
                ai_button=self.ai_button,
                history_action=self.history_action,
                downloads_action=self.downloads_action,
                security_performance_menu=self.security_performance_menu,
                callbacks={
                    "open_note_host": self.open_note_host,
                    "note_indicator_changed": self._on_note_indicator_changed,
                    "video_visibility_changed": (
                        self._on_video_download_visibility_changed
                    ),
                    "inspector_visibility_changed": (
                        self._on_inspector_visibility_changed
                    ),
                    "toggle_side_panel": self._toggle_side_panel,
                    "current_view": self._current_view,
                    "handle_ai_request": self._handle_ai_request,
                    "cancel_ai_request": self._cancel_ai_request,
                    "open_ai_settings": self.open_ai_settings,
                    "refresh_ai_provider": self._refresh_ai_provider,
                    "open_gpu_diagnostic": self.open_gpu_diagnostic,
                    "capture_image_saved": self._show_capture_saved,
                    "capture_pdf_saved": self._show_pdf_saved,
                    "capture_failed": self._show_capture_error,
                },
            )
        )
        self.tools_manager.initialize()
        self._build_capture_menu()
        self._build_settings_menu()
        self._finish_window_layout()

    def _make_action(self, label, icon, callback, shortcut=None):
        action = QAction(icon, label, self)
        action.setToolTip(label)
        action.triggered.connect(callback)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
            action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        return action

    def _create_top_page_buttons(self):
        """Coloca os três controles da página ao lado do campo de endereço."""
        self.blocker_button = self._add_top_page_button(
            "blockerButton",
            ico_bloqueador(),
            TEXTO_UI["blocker_tooltip_no_site"],
            self.toggle_site_blocker,
            icon_size=12,
            text="0",
            button_style=Qt.ToolButtonStyle.ToolButtonTextBesideIcon,
            fixed_width=False,
        )
        self.data_saver_button = self._add_top_page_button(
            "dataSaverButton",
            ico_economia_dados(),
            TEXTO_UI["data_saver_name"],
            self._set_data_saver_from_button,
            accessible_name=TEXTO_UI["data_saver_name"],
            checkable=True,
        )
        self.favorite_button = self._add_top_page_button(
            "favoriteButton",
            ico_favorito_vazio(),
            TEXTO_UI["favorite_add"],
            self.toggle_favorite,
            accessible_name=TEXTO_UI["favorite_toggle"],
        )

    def _add_top_page_button(
        self,
        object_name: str,
        icon,
        tooltip: str,
        callback,
        *,
        icon_size: int = 14,
        accessible_name: str | None = None,
        checkable: bool = False,
        text: str | None = None,
        button_style: Qt.ToolButtonStyle | None = None,
        fixed_width: bool = True,
    ) -> QToolButton:
        button = QToolButton(self.toolbar)
        button.setObjectName(object_name)
        button.setIcon(icon)
        button.setIconSize(QSize(icon_size, icon_size))
        button.setToolTip(tooltip)
        if accessible_name:
            button.setAccessibleName(accessible_name)
        if button_style is not None:
            button.setToolButtonStyle(button_style)
        if checkable:
            button.setCheckable(True)
        if text is not None:
            button.setText(text)
        if fixed_width:
            button.setFixedSize(QSize(26, 26))
        else:
            button.setFixedHeight(26)
        button.clicked.connect(callback)
        self.toolbar.addWidget(button)
        return button

    def _create_top_window_controls(self):
        """Anexa os controles da janela após os controles de página."""
        self.toolbar.addSeparator()
        self.minimize_window_button = self._add_top_window_control_button(
            self.minimize_window_action,
            "minimizeWindowButton",
        )
        self.maximize_window_button = self._add_top_window_control_button(
            self.maximize_window_action,
            "maximizeWindowButton",
        )
        self.close_window_button = self._add_top_window_control_button(
            self.close_window_action,
            "closeWindowButton",
        )

    def _add_top_window_control_button(
        self,
        action: QAction,
        object_name: str,
    ) -> QToolButton:
        button = QToolButton(self.toolbar)
        button.setObjectName(object_name)
        button.setDefaultAction(action)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        button.setIconSize(
            QSize(TAMANHO_ICONE_CONTROLE_JANELA, TAMANHO_ICONE_CONTROLE_JANELA)
        )
        button.setFixedSize(
            QSize(
                TAMANHO_BOTAO_CONTROLE_JANELA,
                TAMANHO_BOTAO_CONTROLE_JANELA,
            )
        )
        button.setAccessibleName(action.text())
        button.setToolTip(action.toolTip())
        button.setAutoRaise(True)
        self.toolbar.addWidget(button)
        return button

    def _finish_window_layout(self):
        self.bottom_maintenance_buttons = self.sidebar_toolbar.finish_layout(
            (
                (self.clear_cache_action, "clearCacheButton"),
                (self.open_app_data_action, "openAppDataButton"),
            )
        )
        self._update_window_controls()

    def _update_side_panel_tabs_inset(self):
        inset = getattr(self, "_side_panel_tabs_inset", None)
        tabs = getattr(self, "tabs", None)
        if inset is None or tabs is None:
            return

        tab_bar = tabs.tabBar()
        tab_bar.ensurePolished()
        height = 0 if self._fullscreen_active else tab_bar.sizeHint().height()
        inset.setFixedHeight(max(0, height))

    def _create_explorer_action(self):
        """Registra o atalho do Explorador e sua ação na barra direita."""
        self.explorer_action = self._make_action(
            TEXTO_UI["explorer_action"],
            ico_abrir(),
            self.open_explorer,
            atalho("explorador"),
        )
        self.addAction(self.explorer_action)
        self.sidebar_toolbar.add_action_button(
            self.explorer_action,
            "explorerButton",
            at_top=True,
        )

    def _build_menu(self) -> QMenu:
        menu = QMenu(self)
        self.history_action = self._make_action(
            TEXTO_UI["history"],
            ico_historico(),
            self.open_history,
            atalho("historico"),
        )
        self.history_action.setEnabled(not self.private)
        self.favorites_action = self._make_action(
            TEXTO_UI["favorites"],
            ico_favoritos(),
            self.open_favorites,
            atalho("favoritos"),
        )
        self.downloads_action = self._make_action(
            TEXTO_UI["browser_downloads_button"],
            ico_downloads(),
            self.toggle_browser_downloads,
        )
        self.downloads_action.setCheckable(True)
        self.password_manager_action = self._make_action(
            TEXTO_UI["password_manager"],
            ico_info(),
            self.open_password_manager,
        )
        self.password_manager_action.setEnabled(not self.private)
        self.site_security_action = self._make_action(
            TEXTO_UI["site_security_action"],
            ico_info(),
            self.open_site_security,
        )
        self.site_privacy_action = self._make_action(
            TEXTO_UI["site_privacy_action"],
            ico_config(),
            self.open_site_privacy,
        )
        self.new_window_action = self._make_action(
            TEXTO_UI["new_window"],
            ico_janela(),
            self.open_new_window,
            atalho("nova_janela"),
        )
        self.private_window_action = self._make_action(
            TEXTO_UI["private_window"],
            ico_anonimo(),
            self.open_private_window,
            atalho("janela_anonima"),
        )
        self.find_action = self._make_action(
            TEXTO_UI["find"],
            ico_localizar(),
            self.show_find_bar,
            atalho("localizar"),
        )
        self.zoom_in_action = self._make_action(
            TEXTO_UI["zoom_in"],
            ico_zoom_mais(),
            self.zoom_in,
            atalho("zoom_mais"),
        )
        self.zoom_out_action = self._make_action(
            TEXTO_UI["zoom_out"],
            ico_zoom_menos(),
            self.zoom_out,
            atalho("zoom_menos"),
        )
        self.zoom_reset_action = self._make_action(
            TEXTO_UI["zoom_default"],
            ico_zoom_redefinir(),
            self.zoom_reset,
            atalho("zoom_reset"),
        )
        self.clear_history_action = self._make_action(
            TEXTO_UI["clear_history"],
            ico_limpar(),
            self.clear_history,
        )
        self.clear_history_action.setEnabled(not self.private)
        self.about_action = self._make_action(TEXTO_UI["about"], ico_info(), self.show_about)
        self.media_diagnostic_action = self._make_action(
            TEXTO_UI["media_diagnostic"],
            ico_info(),
            self.check_media_codecs,
        )
        self.gpu_diagnostic_action = self._make_action(
            TEXTO_UI["gpu_diagnostic"],
            ico_info(),
            self.open_gpu_diagnostic,
        )

        menu.addAction(self.favorites_action)
        self.addAction(self.history_action)
        menu.addSeparator()
        menu.addAction(self.new_window_action)
        menu.addAction(self.private_window_action)
        menu.addSeparator()
        menu.addAction(self.find_action)
        menu.addAction(self.zoom_in_action)
        menu.addAction(self.zoom_out_action)
        menu.addAction(self.zoom_reset_action)
        menu.addSeparator()
        menu.addAction(self.clear_history_action)

        self.security_performance_menu = menu.addMenu(
            ico_info(),
            TEXTO_UI["security_performance_menu"],
        )
        self.security_performance_menu.addAction(self.media_diagnostic_action)
        self.security_performance_menu.addAction(self.gpu_diagnostic_action)
        self.security_performance_menu.addSeparator()
        self.security_performance_menu.addAction(self.site_security_action)
        self.security_performance_menu.addAction(self.password_manager_action)
        self.security_performance_menu.addAction(self.site_privacy_action)
        self.security_performance_menu.addSeparator()
        menu.addAction(self.about_action)

        self.new_tab_action = self._make_action(
            TEXTO_UI["new_tab"],
            ico_nova_aba(),
            self.new_tab,
            atalho("nova_aba"),
        )
        self.close_tab_action = self._make_action(
            TEXTO_UI["close_tab"],
            ico_fechar_aba(),
            self.close_current_tab,
            atalho("fechar_aba"),
        )
        self.address_action = self._make_action(
            TEXTO_UI["focus_address"],
            ico_endereco(),
            self.focus_address,
            atalho("endereco"),
        )
        self.favorite_action = self._make_action(
            TEXTO_UI["favorite_toggle"],
            ico_favorito(),
            self.toggle_favorite,
            atalho("favorito"),
        )
        self.addAction(self.new_tab_action)
        self.addAction(self.close_tab_action)
        self.addAction(self.address_action)
        self.addAction(self.favorite_action)
        return menu

    def _ai_context_key(self, view) -> str:
        return str(id(view)) if view is not None else "no-page"

    def _refresh_ai_provider(self):
        try:
            provider = self.ai_store.active_provider()
        except ProviderStoreError as error:
            self.ai_dock.set_provider(None)
            self.ai_dock.show_error(str(error))
            return
        self.ai_dock.set_provider(provider)

    def open_ai_settings(self, *_):
        dialog = AiSettingsDialog(self.ai_store, self)
        dialog.exec()

    def open_site_security(self, *_):
        view = self._current_view()
        if view is None or not is_http_url(view.url().toString()):
            self.statusBar().showMessage(
                TEXTO_UI["site_security_invalid_url"],
                STATUS_CURTO_MS,
            )
            return
        SiteSecurityDialog(view.url().toString(), self).exec()

    def open_site_privacy(self, *_):
        view = self._current_view()
        if view is None or not is_http_url(view.url().toString()):
            self.statusBar().showMessage(
                TEXTO_UI["site_security_invalid_url"],
                STATUS_CURTO_MS,
            )
            return
        SitePrivacyDialog(
            view.page(),
            self.profile,
            view.url().toString(),
            self,
        ).exec()

    def open_password_manager(self, *_):
        if self.private:
            return
        view = self._current_view()
        if view is None:
            return
        dialog = PasswordManagerDialog(
            self.web_credential_store,
            view.page(),
            self,
        )
        dialog.exec()
        self._refresh_ai_provider()

    def _offer_password_save_after_submit(self, page: BrowserPage):
        if self.private:
            page.runJavaScript(PASSWORD_SAVE_RESUME_SCRIPT)
            return
        try:
            origin = origin_for_url(page.url().toString())
        except WebCredentialStoreError:
            page.runJavaScript(PASSWORD_SAVE_RESUME_SCRIPT)
            return

        page.runJavaScript(PASSWORD_SAVE_CANCEL_FALLBACK_SCRIPT)
        page.runJavaScript(
            _READ_LOGIN_SCRIPT,
            lambda values, submit_page=page, submit_origin=origin:
            self._show_password_save_prompt(
                submit_page,
                submit_origin,
                values,
            ),
        )

    def _show_password_save_prompt(
        self,
        page: BrowserPage,
        origin: str,
        values,
    ):
        username = ""
        password = ""
        dialog = None
        try:
            if self.private or origin_for_url(page.url().toString()) != origin:
                return
            values = values if isinstance(values, dict) else {}
            username = str(values.get("username") or "")
            password = str(values.get("password") or "")
            if not password:
                return

            dialog = SaveLoginDialog(
                origin,
                username,
                password,
                self,
            )
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            username, password = dialog.credentials()
            self.web_credential_store.save_login(
                origin,
                username,
                password,
            )
            self.statusBar().showMessage(
                TEXTO_UI["password_saved"],
                STATUS_CURTO_MS,
            )
        except WebCredentialStoreError as error:
            popup_aviso(TEXTO_UI["password_save_title"], str(error), self)
        finally:
            if dialog is not None:
                dialog.clear_sensitive_fields()
            if isinstance(values, dict):
                values.clear()
            username = ""
            password = ""
            try:
                page.runJavaScript(PASSWORD_SAVE_RESUME_SCRIPT)
            except RuntimeError:
                pass

    def _confirm_ai_cloud_send(self, provider: dict) -> bool:
        if self.private:
            message = TEXTO_UI["ai_private_cloud_consent_message"].format(
                provider=provider["name"]
            )
        elif provider.get("suppress_cloud_warning"):
            return True
        else:
            message = TEXTO_UI["ai_cloud_consent_message"].format(
                provider=provider["name"]
            )

        dialog = criar_popup(
            TEXTO_UI["ai_cloud_consent_title"],
            message,
            self,
            icone=QMessageBox.Icon.Warning,
            botoes=(
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            botao_padrao=QMessageBox.StandardButton.No,
        )
        checkbox = None
        if not self.private:
            checkbox = QCheckBox(TEXTO_UI["ai_consent_dismiss_checkbox"], dialog)
            dialog.setCheckBox(checkbox)
        dialog.setDefaultButton(QMessageBox.StandardButton.No)
        if dialog.exec() != QMessageBox.StandardButton.Yes:
            return False
        if checkbox is not None and checkbox.isChecked():
            try:
                self.ai_store.set_cloud_warning_dismissed(provider["id"], True)
            except ProviderStoreError:
                # O envio foi autorizado; se não for possível salvar a preferência,
                # o aviso voltará a aparecer na próxima solicitação.
                pass
        return True

    def _confirm_ai_insecure_key(self, provider: dict) -> bool:
        if (
            not provider.get("credential_id")
            or urlsplit(provider.get("base_url", "")).scheme.lower() != "http"
        ):
            return True
        answer = popup_pergunta(
            TEXTO_UI["ai_insecure_title"],
            TEXTO_UI["ai_insecure_key_warning"],
            self,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _handle_ai_request(self, question: str, summarize: bool, history):
        view = self._current_view()
        if view is None:
            self.ai_dock.show_error(TEXTO_UI["ai_no_page"])
            return
        if self._active_ai_worker and self._active_ai_worker.isRunning():
            log.aviso(
                "BrowserWindow",
                "_handle_ai_request",
                "solicitação ignorada: já existe uma chamada de IA em andamento",
            )
            self.ai_dock.show_error(TEXTO_UI["ai_request_in_progress"])
            return
        try:
            provider = self.ai_store.active_provider()
        except ProviderStoreError as error:
            log.erro("BrowserWindow", "_handle_ai_request", str(error))
            self.ai_dock.show_error(str(error))
            return
        if provider is None:
            log.aviso(
                "BrowserWindow",
                "_handle_ai_request",
                "solicitação bloqueada: nenhuma conexão ativa",
            )
            self.ai_dock.show_error(TEXTO_UI["ai_no_provider"])
            return
        if not provider.get("model"):
            log.aviso(
                "BrowserWindow",
                "_handle_ai_request",
                "solicitação bloqueada: modelo não selecionado",
            )
            self.ai_dock.show_error(TEXTO_UI["ai_model_unselected"])
            return
        if provider.get("platform") in {"groq", "openrouter"} and not provider.get(
            "credential_id"
        ):
            self.ai_dock.show_error(TEXTO_UI["ai_cloud_service_required"])
            return
        is_cloud = provider.get("kind") != "ollama"
        if is_cloud and not self._confirm_ai_cloud_send(provider):
            self.ai_dock.show_error(TEXTO_UI["ai_ready"])
            return
        if not self._confirm_ai_insecure_key(provider):
            self.ai_dock.show_error(TEXTO_UI["ai_ready"])
            return

        page = view.page()
        if page is None:
            log.aviso(
                "BrowserWindow",
                "_handle_ai_request",
                "solicitação bloqueada: aba sem página WebEngine",
            )
            self.ai_dock.show_error(TEXTO_UI["ai_no_page"])
            return
        context_key = self._ai_context_key(view)
        self.ai_dock.set_context_key(context_key)
        self._ai_request_generation += 1
        request_generation = self._ai_request_generation
        self._ai_pending_context_key = context_key
        is_translation = question == TEXTO_UI["ai_translate_prompt"]
        status = (
            (
                TEXTO_UI["ai_translate_local_notice"]
                if is_translation
                else TEXTO_UI["ai_local_notice"]
            )
            if not is_cloud
            else (
                TEXTO_UI["ai_translate_extracting"]
                if is_translation
                else TEXTO_UI["ai_extracting"]
            )
        )
        self.ai_dock.set_busy(True, status)
        action_name = (
            "tradução"
            if is_translation
            else "resumo"
            if summarize
            else "pergunta"
        )
        log.info(
            "BrowserWindow",
            "_handle_ai_request",
            f"solicitação aceita; ação={action_name}; "
            f"plataforma={provider.get('platform', '')}; "
            f"modelo={provider.get('model', '')}; extração da página iniciada",
        )
        try:
            page.runJavaScript(
                "document.body ? document.body.innerText : ''",
                lambda text: self._start_ai_worker(
                    view,
                    provider,
                    question,
                    summarize,
                    list(history or []),
                    text,
                    context_key,
                    request_generation,
                ),
            )
        except Exception as error:
            log.erro(
                "BrowserWindow",
                "_handle_ai_request",
                f"não foi possível iniciar a extração; tipo={type(error).__name__}",
            )
            self.ai_dock.show_error(TEXTO_UI["ai_page_extract_failed"])

    def _start_ai_worker(
        self,
        view,
        provider: dict,
        question: str,
        summarize: bool,
        history: list[dict[str, str]],
        page_text,
        context_key: str,
        request_generation: int,
    ):
        if (
            self._closing
            or request_generation != self._ai_request_generation
            or self.tabs.indexOf(view) < 0
        ):
            log.aviso(
                "BrowserWindow",
                "_start_ai_worker",
                "extração descartada: janela fechando, solicitação antiga ou aba fechada",
            )
            return
        self._ai_pending_context_key = ""
        if not isinstance(page_text, str):
            log.aviso(
                "BrowserWindow",
                "_start_ai_worker",
                f"extração inválida; tipo={type(page_text).__name__}",
            )
            self.ai_dock.show_error(TEXTO_UI["ai_no_page"])
            return
        if not page_text.strip():
            log.aviso(
                "BrowserWindow",
                "_start_ai_worker",
                "extração concluída sem texto legível; caracteres=0",
            )
            self.ai_dock.show_error(TEXTO_UI["ai_page_text_empty"])
            return
        log.info(
            "BrowserWindow",
            "_start_ai_worker",
            f"texto da página extraído; caracteres={len(page_text)}",
        )
        is_translation = question == TEXTO_UI["ai_translate_prompt"]
        if provider.get("kind") == "ollama":
            local_notice = (
                TEXTO_UI["ai_translate_local_notice"]
                if is_translation
                else TEXTO_UI["ai_local_notice"]
            )
            self.ai_dock.show_local_notice(local_notice)
            self.ai_dock.set_busy(True, local_notice)
        worker = AiProviderWorker(
            "ask",
            provider,
            str(self.ai_store.config_directory),
            page_text=page_text,
            question=question,
            summarize=summarize,
            history=history,
            parent=self,
        )
        worker.ai_context_key = context_key
        worker.ai_question = question
        worker.ai_summarize = summarize
        self._ai_workers.append(worker)
        self._active_ai_worker = worker
        worker.answerReady.connect(
            lambda answer, truncated, w=worker: self._on_ai_answer(
                w,
                answer,
                truncated,
            ),
            Qt.ConnectionType.QueuedConnection,
        )
        worker.failed.connect(
            lambda message, w=worker: self._on_ai_failure(w, message),
            Qt.ConnectionType.QueuedConnection,
        )
        worker.finished.connect(
            lambda w=worker: self._on_ai_worker_finished(w),
            Qt.ConnectionType.QueuedConnection,
        )
        worker.start()

    def _on_ai_answer(
        self,
        worker: AiProviderWorker,
        answer: str,
        truncated: bool,
    ):
        if self._closing:
            log.aviso("BrowserWindow", "_on_ai_answer", "resposta descartada: janela fechando")
            return
        if not any(
            isinstance(self.tabs.widget(index), QWebEngineView)
            and self._ai_context_key(self.tabs.widget(index))
            == worker.ai_context_key
            for index in range(self.tabs.count())
        ):
            log.aviso("BrowserWindow", "_on_ai_answer", "resposta descartada: aba de origem fechada")
            return
        log.ok(
            "BrowserWindow",
            "_on_ai_answer",
            f"resposta exibida; caracteres={len(answer)}; "
            f"texto_cortado={truncated}",
        )
        self.ai_dock.show_answer(
            answer,
            question=worker.ai_question,
            summarize=worker.ai_summarize,
            truncated=truncated,
            context_key=worker.ai_context_key,
        )

    def _on_ai_failure(self, worker: AiProviderWorker, message: str):
        if self._closing:
            return
        log.erro(
            "BrowserWindow",
            "_on_ai_failure",
            f"plataforma={worker.provider.get('platform', '')}; "
            f"modelo={worker.provider.get('model', '')}; erro={message}",
        )
        self.ai_dock.show_error(
            TEXTO_UI["ai_cancelled"] if worker.isInterruptionRequested() else message,
            context_key=worker.ai_context_key,
        )

    def _on_ai_worker_finished(self, worker: AiProviderWorker):
        if worker in self._ai_workers:
            self._ai_workers.remove(worker)
        if self._active_ai_worker is worker:
            self._active_ai_worker = None

    def _cancel_ai_request(self):
        self._ai_request_generation += 1
        self._ai_pending_context_key = ""
        worker = self._active_ai_worker
        if worker is not None and worker.isRunning():
            worker.cancel()
            self.ai_dock.set_busy(True, TEXTO_UI["ai_cancelled"])
        else:
            self.ai_dock.set_busy(False, TEXTO_UI["ai_cancelled"])

    def _build_settings_menu(self):
        self.main_menu.addSeparator()
        settings_menu = self.main_menu.addMenu(
            ico_config(),
            TEXTO_UI["settings_menu"],
        )
        self.settings_menu = settings_menu
        self.shortcuts_action = self._make_action(
            TEXTO_UI["keyboard_shortcuts"],
            ico_atalhos(),
            self.show_shortcuts,
            atalho("atalhos"),
        )
        settings_menu.addAction(self.shortcuts_action)
        self.ai_settings_action = self._make_action(
            TEXTO_UI["ai_settings"],
            ico_ia(),
            self.open_ai_settings,
        )
        settings_menu.addAction(self.ai_settings_action)
        settings_menu.addSeparator()
        self.theme_menu = settings_menu.addMenu(
            ico_tema(),
            TEXTO_UI["theme_menu"],
        )
        self.theme_actions = {}
        self.theme_group = QActionGroup(self)
        self.theme_group.setExclusive(True)
        for theme_id, theme in TEMAS.items():
            action = QAction(theme["name"], self)
            action.setCheckable(True)
            action.setChecked(theme_id == self.controller.theme_id)
            action.triggered.connect(
                lambda _checked=False, selected=theme_id:
                self.controller.set_theme(selected)
            )
            self.theme_group.addAction(action)
            self.theme_actions[theme_id] = action
            self.theme_menu.addAction(action)
        self.custom_theme_action = QAction(TEXTO_UI["theme_custom"], self)
        self.custom_theme_action.setCheckable(True)
        self.custom_theme_action.setChecked(
            TEMA_PERSONALIZADO == self.controller.theme_id
        )
        self.custom_theme_action.triggered.connect(
            lambda _checked=False: self.controller.set_theme(TEMA_PERSONALIZADO)
        )
        self.theme_group.addAction(self.custom_theme_action)
        self.theme_actions[TEMA_PERSONALIZADO] = self.custom_theme_action
        self.theme_menu.addAction(self.custom_theme_action)
        self.theme_menu.addSeparator()
        self.theme_customize_action = self._make_action(
            TEXTO_UI["theme_customize"],
            ico_tema(),
            self.open_custom_theme_editor,
            atalho("tema_personalizado"),
        )
        self.addAction(self.theme_customize_action)
        self.theme_menu.addAction(self.theme_customize_action)

        settings_menu.addSeparator()
        self.search_engine_menu = settings_menu.addMenu(
            ico_localizar(),
            TEXTO_UI["search_engine_menu"],
        )
        self.search_engine_group = QActionGroup(self)
        self.search_engine_group.setExclusive(True)
        self.search_engine_actions = {}
        for engine_id, (engine_name, _search_url) in BUSCADORES_PESQUISA.items():
            action = QAction(engine_name, self)
            action.setCheckable(True)
            action.setChecked(engine_id == self.controller.search_engine)
            action.triggered.connect(
                lambda _checked=False, selected=engine_id:
                self.controller.set_search_engine(selected)
            )
            self.search_engine_group.addAction(action)
            self.search_engine_menu.addAction(action)
            self.search_engine_actions[engine_id] = action

        self.blocker_settings_action = self._make_action(
            TEXTO_UI["blocker_settings"],
            ico_bloqueador(),
            self.open_blocker_settings,
        )
        self.security_performance_menu.addAction(self.blocker_settings_action)

        self.blocker_toggle_site_action = self._make_action(
            TEXTO_UI["blocker_toggle_site"],
            ico_bloqueador(),
            self.toggle_site_blocker,
            atalho("bloqueador_site"),
        )
        self.security_performance_menu.addAction(self.blocker_toggle_site_action)

        self.open_app_data_action = self._make_action(
            TEXTO_UI["open_app_data"],
            ico_abrir(),
            self.open_app_data,
            atalho("appdata"),
        )
        self.clear_cache_action = self._make_action(
            TEXTO_UI["clear_cache"],
            ico_limpar(),
            self.clear_browser_cache,
        )

        self.addAction(self.open_app_data_action)

    def open_app_data(self, *_):
        if self.private:
            self.statusBar().showMessage(
                TEXTO_UI["app_data_private_unavailable"],
                STATUS_CURTO_MS,
            )
            return

        for index in range(self.tabs.count()):
            widget = self.tabs.widget(index)
            if (
                isinstance(widget, ExplorerTab)
                and widget.inspection_mode
                and widget.fixed_root is not None
                and os.path.normcase(os.path.realpath(widget.fixed_root))
                == os.path.normcase(os.path.realpath(appdata.pasta_raiz))
            ):
                self.tabs.setCurrentIndex(index)
                return

        explorer = self._new_explorer_tab(
            inspection_mode=True,
            fixed_root=appdata.pasta_raiz,
        )
        self._add_local_tab(
            explorer,
            TEXTO_UI["open_app_data"],
            appdata.pasta_raiz,
            ico_abrir(),
        )
        self.statusBar().showMessage(
            TEXTO_UI["app_data_opened"],
            STATUS_CURTO_MS,
        )

    def clear_browser_cache(self, *_):
        profiles = {id(self.controller.profile): self.controller.profile}
        for window in self.controller.normal_windows + self.controller.private_windows:
            try:
                profile = window.profile
                profiles[id(profile)] = profile
            except RuntimeError:
                continue

        try:
            for profile in profiles.values():
                profile.clearHttpCache()
        except RuntimeError as error:
            log.erro("BrowserWindow", "clear_browser_cache", str(error))
            self.statusBar().showMessage(
                TEXTO_UI["cache_clear_error"],
                STATUS_CURTO_MS,
            )
            return
        self.statusBar().showMessage(
            TEXTO_UI["cache_cleared"],
            STATUS_CURTO_MS,
        )

    def _build_new_tab_button(self):
        button = QToolButton(self)
        button.setObjectName("newTabButton")
        _set_button_icon_or_fallback(button, ico_nova_aba(), "+")
        font_size = self._theme["font_size_px"]
        size = max(24, font_size + 10)
        icon_size = min(22, max(14, font_size + 1))
        button.setIconSize(QSize(icon_size, icon_size))
        button.setFixedSize(QSize(size, size))
        button.setAutoRepeat(False)
        button.setToolTip(TEXTO_UI["new_tab_tooltip"])
        button.setAccessibleName(TEXTO_UI["new_tab_tooltip"])
        button.clicked.connect(self.new_tab)
        return button

    def apply_theme(self):
        self._theme = obter_tema(
            self.controller.theme_id,
            custom_theme=self.controller.custom_theme,
        )
        footer_height = max(
            self._theme["footer_height_px"],
            self._theme["font_size_px"] + 12,
        )
        self.setStyleSheet(
            stylesheet_for_theme(
                self.controller.theme_id,
                private=self.private,
                custom_theme=self.controller.custom_theme,
            )
        )
        self._update_side_panel_tabs_inset()
        if hasattr(self, "sidebar_toolbar"):
            self.sidebar_toolbar.apply_metrics(
                self._theme["sidebar_icon_size_px"]
            )
        if hasattr(self, "_status_bar"):
            self._status_bar.setFixedHeight(footer_height)
        if hasattr(self, "favorites_status_bar"):
            self.favorites_status_bar.apply_metrics(
                self._theme["font_size_px"],
                footer_height,
            )
        icon_factories = (
            ("back_action", ico_voltar),
            ("forward_action", ico_avancar),
            ("reload_action", ico_atualizar),
            ("history_action", ico_historico),
            ("favorites_action", ico_favoritos),
            ("password_manager_action", ico_info),
            ("new_window_action", ico_janela),
            ("private_window_action", ico_anonimo),
            ("find_action", ico_localizar),
            ("zoom_in_action", ico_zoom_mais),
            ("zoom_out_action", ico_zoom_menos),
            ("zoom_reset_action", ico_zoom_redefinir),
            ("clear_history_action", ico_limpar),
            ("about_action", ico_info),
            ("new_tab_action", ico_nova_aba),
            ("close_tab_action", ico_fechar_aba),
            ("address_action", ico_endereco),
            ("favorite_action", ico_favorito),
            ("shortcuts_action", ico_atalhos),
            ("notes_action", ico_anotacoes),
            ("ai_action", ico_ia),
            ("ai_settings_action", ico_ia),
            ("video_download_action", ico_video_download),
            ("downloads_action", ico_downloads),
            ("inspect_action", ico_inspecionar),
            ("devtools_action", ico_ferramentas),
            ("blocker_settings_action", ico_bloqueador),
            ("blocker_toggle_site_action", ico_bloqueador),
            ("visible_capture_action", ico_captura),
            ("full_page_capture_action", ico_imagem),
            ("pdf_capture_action", ico_pdf),
            ("open_app_data_action", ico_abrir),
            ("clear_cache_action", ico_limpar),
            ("close_window_action", ico_janela_fechar),
            ("minimize_window_action", ico_janela_minimizar),
        )
        for attribute, factory in icon_factories:
            action = getattr(self, attribute, None)
            if action:
                action.setIcon(factory())
        if hasattr(self, "close_side_panel_button"):
            self.close_side_panel_button.setIcon(ico_fechar())
        if hasattr(self, "settings_menu"):
            self.settings_menu.menuAction().setIcon(ico_config())
            self.theme_menu.menuAction().setIcon(ico_tema())
            self.theme_customize_action.setIcon(ico_tema())
            self.search_engine_menu.menuAction().setIcon(ico_localizar())
            self.capture_menu.menuAction().setIcon(ico_captura())
        self.brand_button.setIcon(QIcon(IMAGEM_ICO))
        self.blocker_button.setIcon(ico_bloqueador())
        self._update_data_saver_button()
        self.capture_button.setIcon(ico_captura())
        self.notes_button.setIcon(ico_anotacoes())
        self.ai_button.setIcon(ico_ia())
        self._update_window_controls()
        if hasattr(self, "favorites_status_bar"):
            self.favorites_status_bar.refresh()
        new_tab_button = self.tabs.new_tab_button()
        if isinstance(new_tab_button, QToolButton):
            font_size = self._theme["font_size_px"]
            size = max(24, font_size + 10)
            icon_size = min(22, max(14, font_size + 1))
            new_tab_button.setIconSize(QSize(icon_size, icon_size))
            new_tab_button.setFixedSize(QSize(size, size))
            _set_button_icon_or_fallback(
                new_tab_button,
                ico_nova_aba(),
                "+",
            )
        tab_bar = self.tabs.tabBar()
        tab_bar.updateGeometry()
        for index in range(self.tabs.count()):
            close_button = tab_bar.tabButton(
                index,
                tab_bar.ButtonPosition.RightSide,
            )
            if isinstance(close_button, TabCloseButton):
                close_button.apply_metrics(self._theme["font_size_px"])
                close_button.refresh_icon()
        self._update_location_and_favorite()
        self.update_theme_actions()

    def update_theme_actions(self):
        for theme_id, action in getattr(self, "theme_actions", {}).items():
            action.setChecked(theme_id == self.controller.theme_id)

    def open_custom_theme_editor(self):
        current_theme = obter_tema(
            self.controller.theme_id,
            custom_theme=self.controller.custom_theme,
        )
        dialog = CustomThemeDialog(current_theme, self)
        dialog.saveRequested.connect(self.controller.set_custom_theme)
        dialog.exec()

    def update_search_engine_actions(self):
        selected = self.controller.search_engine
        for engine_id, action in getattr(
            self,
            "search_engine_actions",
            {},
        ).items():
            action.setChecked(engine_id == selected)

    def _build_find_bar(self):
        self.find_bar = QWidget(self)
        self.find_bar.setObjectName("findBar")
        layout = QHBoxLayout(self.find_bar)
        layout.setContentsMargins(8, 4, 8, 4)
        self.find_input = QLineEdit(self.find_bar)
        self.find_input.setPlaceholderText(TEXTO_UI["find_placeholder"])
        self.find_input.returnPressed.connect(self.find_next)
        layout.addWidget(self.find_input, 1)
        previous_button = QPushButton(TEXTO_UI["previous"], self.find_bar)
        next_button = QPushButton(TEXTO_UI["next"], self.find_bar)
        close_button = QPushButton(TEXTO_UI["close"], self.find_bar)
        previous_button.clicked.connect(self.find_previous)
        next_button.clicked.connect(self.find_next)
        close_button.clicked.connect(self.hide_find_bar)
        layout.addWidget(previous_button)
        layout.addWidget(next_button)
        layout.addWidget(close_button)
        return self.find_bar

    def _create_tab(
        self,
        *,
        url: str | None = None,
        home: bool = False,
        blank: bool = False,
        select: bool = True,
        restored: bool = False,
        popup: bool = False,
    ) -> BrowserPage:
        view = QWebEngineView(self.tabs)
        view.setProperty("downloadPopup", bool(popup))
        home_path = self._start_page_path
        page = BrowserPage(
            self.profile,
            view,
            self,
            home_path,
            start_page=home,
            restored=restored,
        )
        bridge = HomeSearchBridge(page)
        channel = QWebChannel(page)
        channel.registerObject("homeSearch", bridge)
        page.set_search_suggestions_channel(channel)
        source = f"home:{id(page)}"
        self._home_suggestion_bridges[source] = (page, bridge)
        bridge.requestReceived.connect(
            lambda query, request_source=source, home_page=page:
            self._request_home_search_suggestions(
                request_source,
                home_page,
                query,
            )
        )
        bridge.searchRequested.connect(
            lambda query, home_page=page:
            self._queue_home_search(query, home_page),
            Qt.ConnectionType.QueuedConnection,
        )
        page.destroyed.connect(
            lambda *_args, request_source=source:
            self._forget_home_suggestion_bridge(request_source)
        )
        view.setPage(page)
        view.setZoomFactor(ZOOM_INICIAL)
        view.urlChanged.connect(self._on_view_url_changed)
        view.titleChanged.connect(self._on_view_title_changed)
        view.iconChanged.connect(self._on_view_icon_changed)
        view.loadStarted.connect(self._on_load_started)
        view.loadProgress.connect(self._on_load_progress)
        view.loadFinished.connect(self._on_load_finished)

        if self.profile_lease:
            self.profile_lease.register_view(view)

        label = (
            TEXTO_UI["home_title"]
            if home and not blank
            else TEXTO_UI["new_tab"]
        )
        index = self.tabs.addTab(view, label)
        bar = self.tabs.tabBar()
        close_button = TabCloseButton(
            bar,
            font_size_px=self._theme["font_size_px"],
        )
        close_button.setToolTip(TEXTO_UI["close_tab"])
        close_button.setAccessibleName(TEXTO_UI["close_tab"])
        close_button.clicked.connect(
            lambda _checked=False, tab=view: self.close_tab(
                self.tabs.indexOf(tab)
            )
        )
        bar.setTabButton(
            index,
            bar.ButtonPosition.RightSide,
            close_button,
        )
        close_button.show()
        self.tabs.setTabToolTip(index, label)

        if select:
            self.tabs.setCurrentIndex(index)
        if url:
            view.setUrl(QUrl(url))
        elif home:
            view.setUrl(QUrl.fromLocalFile(home_path))
        elif blank:
            view.setUrl(QUrl("about:blank"))
        elif not popup:
            view.setUrl(QUrl.fromLocalFile(home_path))
            page.is_start_page_active = True
        self._update_location_and_favorite()
        return page

    def _current_view(self) -> QWebEngineView | None:
        widget = self.tabs.currentWidget()
        return widget if isinstance(widget, QWebEngineView) else None

    def _page_index(self, page: BrowserPage) -> int:
        for index in range(self.tabs.count()):
            view = self.tabs.widget(index)
            if isinstance(view, QWebEngineView) and view.page() is page:
                return index
        return -1

    def new_tab(self, *_):
        self._create_tab(home=True, select=True)
        if not self._initializing and not self.private:
            self.controller.notify_session_change()

    def open_explorer(self, *_):
        """Seleciona a aba Explorador existente ou cria uma única instância."""
        for index in range(self.tabs.count()):
            widget = self.tabs.widget(index)
            if isinstance(widget, ExplorerTab) and not widget.inspection_mode:
                self.tabs.setCurrentIndex(index)
                return

        explorer = self._new_explorer_tab()
        self._add_local_tab(
            explorer,
            TEXTO_UI["explorer_action"],
            TEXTO_UI["explorer_action"],
            ico_ferramentas(),
        )

    def _new_explorer_tab(
        self,
        *,
        inspection_mode: bool = False,
        fixed_root: str | None = None,
    ) -> ExplorerTab:
        limits = ExplorerLimits(
            max_items=EXPLORER_MAX_ITEMS,
            max_seconds=EXPLORER_MAX_SECONDS,
            max_depth=EXPLORER_MAX_DEPTH,
            max_lines=EXPLORER_MAX_LINES,
            max_chars=EXPLORER_MAX_CHARS,
        )
        settings_store = ExplorerSettingsStore(
            appdata.pasta_config,
            EXPLORER_DEFAULT_IGNORED_NAMES,
        )
        explorer = ExplorerTab(
            settings_store,
            EXPLORER_DEFAULT_IGNORED_NAMES,
            limits,
            TEXTO_UI,
            self.tabs,
            inspection_mode=inspection_mode,
            fixed_root=fixed_root,
        )
        explorer.file_open_requested.connect(self._open_file_preview)
        return explorer

    def _add_local_tab(
        self,
        widget: QWidget,
        title: str,
        tooltip: str,
        icon: QIcon,
    ):
        index = self.tabs.addTab(widget, self._limited_tab_title(title))
        self.tabs.setTabIcon(index, icon)
        self.tabs.setTabToolTip(index, tooltip)
        bar = self.tabs.tabBar()
        close_button = TabCloseButton(
            bar,
            font_size_px=self._theme["font_size_px"],
        )
        close_button.setToolTip(TEXTO_UI["close_tab"])
        close_button.setAccessibleName(TEXTO_UI["close_tab"])
        close_button.clicked.connect(
            lambda _checked=False, tab=widget: self.close_tab(
                self.tabs.indexOf(tab)
            )
        )
        bar.setTabButton(
            index,
            bar.ButtonPosition.RightSide,
            close_button,
        )
        close_button.show()
        self.tabs.setCurrentIndex(index)

    def _open_file_preview(self, root_path: str, relative_path: str):
        preview = FilePreviewTab(
            root_path,
            relative_path,
            TEXTO_UI,
            self.tabs,
        )
        self._add_local_tab(
            preview,
            Path(relative_path).name,
            relative_path,
            ico_abrir(),
        )

    def _queue_home_search(
        self,
        query: str,
        source_page: BrowserPage | None = None,
    ):
        query = str(query or "")
        QTimer.singleShot(
            0,
            lambda query=query, page=source_page:
            self._search_from_home(query, page),
        )

    def open_url_new_tab(self, url: str):
        if not is_http_url(url):
            return
        self._create_tab(url=url, home=False, select=True)
        if not self._initializing and not self.private:
            self.controller.notify_session_change()

    def _create_popup_page(self, window_type):
        window_types = QWebEnginePage.WebWindowType
        if window_type in (
            window_types.WebBrowserWindow,
            window_types.WebDialog,
        ):
            popup_window = QDialog(self, Qt.WindowType.Window)
            popup_window.setAttribute(
                Qt.WidgetAttribute.WA_DeleteOnClose,
                True,
            )
            popup_window.resize(720, 640)
            popup_window.setWindowTitle(self.windowTitle())

            layout = QVBoxLayout(popup_window)
            layout.setContentsMargins(0, 0, 0, 0)
            view = QWebEngineView(popup_window)
            page = BrowserPage(
                self.profile,
                view,
                self,
                self._start_page_path,
            )
            view.setPage(page)
            view.setZoomFactor(ZOOM_INICIAL)
            layout.addWidget(view)

            page.titleChanged.connect(popup_window.setWindowTitle)
            page.iconChanged.connect(popup_window.setWindowIcon)
            page.windowCloseRequested.connect(popup_window.close)
            popup_window.finished.connect(
                lambda _result, closed_window=popup_window:
                self._forget_popup_window(closed_window)
            )
            self._popup_windows.append(popup_window)
            popup_window.show()
            return page

        select = window_type != window_types.WebBrowserBackgroundTab
        page = self._create_tab(
            home=False,
            select=select,
            popup=True,
        )
        if not self.private:
            self.controller.notify_session_change()
        return page

    def _forget_popup_window(self, popup_window: QDialog) -> None:
        if popup_window in self._popup_windows:
            self._popup_windows.remove(popup_window)

    def _search_from_home(
        self,
        query: str,
        source_page: BrowserPage | None = None,
    ):
        query = (query or "").strip()
        if not query:
            return
        target = resolve_address(
            query,
            self.controller.search_engine,
        )
        if not is_http_url(target):
            return
        if target == search_url(query, self.controller.search_engine):
            self._record_search_query(query)
        if source_page is None:
            view = self._current_view()
        else:
            index = self._page_index(source_page)
            view = self.tabs.widget(index) if index >= 0 else None
        if not isinstance(view, QWebEngineView):
            self.open_url_new_tab(target)
            return
        view.setUrl(QUrl(target))
        if not self.private:
            self.controller.notify_session_change()

    def _record_search_query(self, query: str):
        if self.private:
            return
        self.controller.storage.record_search_query(query)

    def _on_address_text_edited(self, text: str):
        if self._current_view() is None:
            self.search_suggestion_service.cancel("address")
            self._address_suggestion_query = ""
            self._address_suggestion_targets.clear()
            self._address_suggestion_queries.clear()
            self._address_suggestion_model.setStringList([])
            self.address_completer.popup().hide()
            return
        query = (text or "").strip()
        self._address_suggestion_query = query
        self._update_address_suggestions(query)
        self.search_suggestion_service.request(
            "address",
            query,
            self.controller.search_engine,
        )

    def _update_address_suggestions(
        self,
        query: str,
        search_suggestions: list[str] | None = None,
    ):
        local_sites = collect_site_suggestions(
            query,
            self.controller.storage.get_favorites(),
            [] if self.private else self.controller.storage.recent_unique(30),
        )
        targets: dict[str, str] = {}
        search_queries: dict[str, str] = {}
        for entry in local_sites:
            label = f'{entry["title"]} — {entry["host"]}'
            targets.setdefault(label, entry["url"])

        previous_queries = (
            []
            if self.private
            else self.controller.storage.recent_search_queries(query, 30)
        )
        for previous_query in previous_queries:
            label = (
                f'{previous_query} — {TEXTO_UI["search_suggestion_label"]}'
            )
            targets.setdefault(
                label,
                search_url(previous_query, self.controller.search_engine),
            )
            search_queries.setdefault(label, previous_query)

        for suggestion in search_suggestions or []:
            label = (
                f'{suggestion} — {TEXTO_UI["search_suggestion_label"]}'
            )
            targets.setdefault(
                label,
                search_url(suggestion, self.controller.search_engine),
            )
            search_queries.setdefault(label, suggestion)

        self._address_suggestion_targets = targets
        self._address_suggestion_queries = search_queries
        self._address_suggestion_model.setStringList(list(targets))
        if query and targets:
            self.address_completer.setCompletionPrefix("")
            self.address_completer.complete()
        else:
            self.address_completer.popup().hide()

    def _on_address_suggestion_activated(self, label: str):
        target = self._address_suggestion_targets.get(str(label))
        if not target:
            return
        query = self._address_suggestion_queries.get(str(label))
        if query:
            self._record_search_query(query)
        self.search_suggestion_service.cancel("address")
        self.address_bar.setText(target)
        self.navigate_address()

    def _request_home_search_suggestions(
        self,
        source: str,
        page: BrowserPage,
        query: str,
    ):
        page_url = page.url()
        if (
            page_url.scheme().lower() != "file"
            or os.path.realpath(page_url.toLocalFile()) != page.home_file_path
        ):
            return
        self.search_suggestion_service.request(
            source,
            query,
            self.controller.search_engine,
        )

    def _on_search_suggestions_ready(
        self,
        source: str,
        query: str,
        suggestions: list[str],
    ):
        if source == "address":
            if query != self._address_suggestion_query:
                return
            self._update_address_suggestions(query, suggestions)
            return

        bridge_entry = self._home_suggestion_bridges.get(source)
        if bridge_entry is None:
            return
        page, bridge = bridge_entry
        page_url = page.url()
        if (
            page_url.scheme().lower() != "file"
            or os.path.realpath(page_url.toLocalFile()) != page.home_file_path
        ):
            return
        bridge.suggestionsReady.emit(query, suggestions)

    def _forget_home_suggestion_bridge(self, source: str):
        self._home_suggestion_bridges.pop(source, None)
        self.search_suggestion_service.cancel(source)

    def navigate_address(self, *_):
        query = self.address_bar.text().strip()
        target = resolve_address(
            query,
            self.controller.search_engine,
        )
        if not target:
            return
        if target == search_url(query, self.controller.search_engine):
            self._record_search_query(query)
        view = self._current_view()
        if view:
            view.setUrl(QUrl(target))
            if not self.private:
                self.controller.notify_session_change()
        else:
            self.open_url_new_tab(target)

    def go_back(self, *_):
        view = self._current_view()
        if view:
            view.back()

    def go_forward(self, *_):
        view = self._current_view()
        if view:
            view.forward()

    def reload_current(self, *_):
        view = self._current_view()
        if view:
            view.reload()

    def go_home(self, *_):
        self.controller.refresh_home_pages()
        view = self._current_view()
        if view is None:
            self._create_tab(home=True, select=True)
            return
        page = view.page()
        if isinstance(page, BrowserPage):
            page.is_start_page_active = True
        current_url = view.url()
        if (
            current_url.scheme().lower() == "file"
            and os.path.realpath(current_url.toLocalFile())
            == os.path.realpath(self._start_page_path)
        ):
            return
        view.setUrl(QUrl.fromLocalFile(self._start_page_path))

    def focus_address(self, *_):
        self.address_bar.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.address_bar.selectAll()

    def close_current_tab(self, *_):
        self.close_tab(self.tabs.currentIndex())

    def close_tab(self, index: int):
        if index < 0 or index >= self.tabs.count():
            return
        widget = self.tabs.widget(index)
        if isinstance(widget, (ExplorerTab, FilePreviewTab)):
            widget.shutdown()
            if self.tabs.count() == 1:
                self.close()
                return
            self.tabs.removeTab(index)
            widget.deleteLater()
            if not self.private:
                self.controller.notify_session_change()
            return

        view = widget
        if not isinstance(view, QWebEngineView):
            return
        if self.tabs.count() == 1:
            self.close()
            return
        page = view.page()
        if isinstance(page, BrowserPage):
            self.controller.cancel_restore_page(page)
        context_key = self._ai_context_key(view)
        if self._ai_pending_context_key == context_key:
            self._ai_request_generation += 1
            self._ai_pending_context_key = ""
            self.ai_dock.set_busy(False, TEXTO_UI["ai_cancelled"])
        if (
            self._active_ai_worker is not None
            and getattr(self._active_ai_worker, "ai_context_key", "") == context_key
        ):
            self._active_ai_worker.cancel()
        self.ai_dock.release_context(context_key)
        self.tabs.removeTab(index)
        self._dispose_view(view)
        if not self.private:
            self.controller.notify_session_change()

    def _dispose_view(self, view: QWebEngineView):
        page = view.page()
        if page:
            page.setAudioMuted(True)
            page.triggerAction(QWebEnginePage.WebAction.Stop)
        view.stop()
        view.deleteLater()

    def session_urls(self) -> list[str]:
        result: list[str] = []
        for index in range(self.tabs.count()):
            view = self.tabs.widget(index)
            if not isinstance(view, QWebEngineView):
                continue
            url = view.url().toString()
            if is_http_url(url):
                result.append(url)
        return result

    def refresh_start_pages(self):
        for index in range(self.tabs.count()):
            view = self.tabs.widget(index)
            if not isinstance(view, QWebEngineView):
                continue
            page = view.page()
            if isinstance(page, BrowserPage) and page.is_start_page_active:
                view.setUrl(QUrl.fromLocalFile(self._start_page_path))

    def _on_current_changed(self, _index: int):
        self._update_location_and_favorite()
        self._update_navigation_actions()
        self._update_page_action_state()
        self._sync_inspector_page()
        self._sync_devtools_page()
        if hasattr(self, "ai_dock"):
            self.ai_dock.set_context_key(
                self._ai_context_key(self._current_view())
            )

    def _update_page_action_state(self):
        view = self._current_view()
        has_page = view is not None
        url = view.url().toString() if view else ""
        is_http = has_page and is_http_url(url)

        if not has_page:
            if getattr(self, "_active_side_panel", None) in {
                "notes",
                "video",
                "inspector",
                "devtools",
                "ai",
            }:
                self._close_side_panel()
            find_bar = getattr(self, "find_bar", None)
            if find_bar is not None and find_bar.isVisible():
                self.hide_find_bar()

        action_states = {
            "reload_action": has_page,
            "favorite_action": is_http,
            "password_manager_action": is_http and not self.private,
            "site_security_action": is_http,
            "site_privacy_action": is_http,
            "find_action": has_page,
            "zoom_in_action": has_page,
            "zoom_out_action": has_page,
            "zoom_reset_action": has_page,
            "media_diagnostic_action": has_page,
            "gpu_diagnostic_action": has_page,
            "notes_action": is_http and not self.private,
            "video_download_action": is_http,
            "inspect_action": has_page,
            "devtools_action": has_page,
            "ai_action": has_page,
            "visible_capture_action": has_page,
            "full_page_capture_action": has_page,
            "pdf_capture_action": has_page,
            "capture_shortcut_action": has_page,
        }
        for name, enabled in action_states.items():
            action = getattr(self, name, None)
            if action is not None:
                action.setEnabled(bool(enabled))

        button_states = {
            "capture_button": has_page,
            "video_download_button": is_http,
            "notes_button": is_http and not self.private,
            "ai_button": has_page,
            "translate_button": has_page,
        }
        for name, enabled in button_states.items():
            button = getattr(self, name, None)
            if button is not None:
                button.setEnabled(bool(enabled))

    def _sync_inspector_page(self):
        inspector = getattr(self, "inspector_dock", None)
        if inspector is None:
            return
        view = self._current_view()
        inspector.set_page(view.page() if view else None)

    def _sync_devtools_page(self):
        devtools = getattr(self, "devtools_panel", None)
        if devtools is None:
            return
        if (
            self._active_side_panel != "devtools"
            or not self._side_panel_container.isVisible()
        ):
            # The hidden frontend must not query protocol data for stale frames.
            devtools.set_page(None)
            return
        view = self._current_view()
        devtools.set_page(view.page() if view else None)

    def _on_view_url_changed(self, *_):
        self._update_location_and_favorite()
        self._update_navigation_actions()

    def _on_view_title_changed(self, title: str):
        view = self.sender()
        if not isinstance(view, QWebEngineView):
            return
        index = self.tabs.indexOf(view)
        if index < 0:
            return
        full_title = (title or "").strip() or self._host_label(view.url())
        label = self._limited_tab_title(full_title)
        self.tabs.setTabText(index, label)
        url = view.url().toString()
        self.tabs.setTabToolTip(index, f"{full_title}\n{url}")

    def _on_view_icon_changed(self, icon: QIcon):
        view = self.sender()
        if isinstance(view, QWebEngineView):
            index = self.tabs.indexOf(view)
            if index >= 0:
                self.tabs.setTabIcon(index, icon)
            url = view.url().toString()
            if self.private or icon.isNull() or not is_http_url(url):
                return
            pixmap = icon.pixmap(QSize(64, 64))
            if pixmap.isNull():
                return
            buffer = QBuffer()
            if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
                return
            try:
                if not pixmap.save(buffer, "PNG"):
                    return
                encoded = buffer.data().toBase64().data().decode("ascii")
            finally:
                buffer.close()
            if not encoded:
                return
            data_uri = f"data:image/png;base64,{encoded}"
            if self.controller.storage.save_favicon(url, data_uri):
                self.controller.refresh_home_pages()
                self.favorites_status_bar.refresh()

    def _on_load_progress(self, progress: int):
        view = self.sender()
        if view is self._current_view() and progress < 100:
            self.statusBar().showMessage(
                f"{TEXTO_UI['loading_prefix']} {progress}%",
                STATUS_CARREGAMENTO_MS,
            )

    def _on_load_started(self):
        view = self.sender()
        if isinstance(view, QWebEngineView):
            view.setProperty(
                "_henNavePerformanceLoadStartedAt",
                perf_counter(),
            )

    def _on_load_finished(self, success: bool):
        view = self.sender()
        if not isinstance(view, QWebEngineView):
            return
        started_at = view.property("_henNavePerformanceLoadStartedAt")
        if isinstance(started_at, (int, float)) and started_at >= 0:
            view.setProperty("_henNavePerformanceLoadStartedAt", -1.0)
            record_page_load(
                log,
                started_at,
                view.url().scheme(),
                success,
            )
        page = view.page()
        url = view.url().toString()
        home_path = os.path.realpath(self._start_page_path)
        is_home = (
            view.url().scheme() == "file"
            and os.path.realpath(view.url().toLocalFile()) == home_path
        )
        if isinstance(page, BrowserPage):
            page.is_start_page_active = is_home
            self.controller.complete_restore_page(page)

        if success and not self.private and is_http_url(url):
            self.controller.storage.record_visit(url, view.title())
            self.controller.refresh_home_pages()
        if view is self._current_view():
            message = (
                TEXTO_UI["load_success"]
                if success
                else TEXTO_UI["load_failure"]
            )
            self.statusBar().showMessage(message, STATUS_CARREGAMENTO_MS)
            if self.inspector_dock and self.inspector_dock.isVisible():
                self.inspector_dock.set_page(page)
                self.inspector_dock.refresh_dom()
        if not self.private:
            self.controller.notify_session_change()
        self._update_location_and_favorite()
        self._update_tab_title(view)

    def _update_tab_title(self, view: QWebEngineView):
        index = self.tabs.indexOf(view)
        if index < 0:
            return
        full_title = (view.title() or self._host_label(view.url())).strip()
        if not full_title:
            full_title = TEXTO_UI["new_tab"]
        label = self._limited_tab_title(full_title)
        self.tabs.setTabText(index, label)
        self.tabs.setTabToolTip(index, f"{full_title}\n{view.url().toString()}")

    @staticmethod
    def _limited_tab_title(title: str) -> str:
        if len(title) <= MAX_TAB_TITLE_CHARS:
            return title
        return f"{title[: MAX_TAB_TITLE_CHARS - 1].rstrip()}…"

    @staticmethod
    def _host_label(url: QUrl) -> str:
        host = url.host()
        return host or TEXTO_UI["new_tab"]

    def _update_location_and_favorite(self):
        view = self._current_view()
        if not view:
            self.address_bar.clear()
            self.search_suggestion_service.cancel("address")
            self._address_suggestion_query = ""
            self._address_suggestion_targets.clear()
            self._address_suggestion_queries.clear()
            self._address_suggestion_model.setStringList([])
            self.address_completer.popup().hide()
            self.favorite_button.setEnabled(False)
            self.favorite_button.setIcon(ico_favorito_vazio())
            self.favorite_button.setToolTip(TEXTO_UI["favorite_add"])
            self._update_blocker_button("")
            if self.notes_dock:
                self.notes_dock.set_site("")
            if self.video_download_dock:
                self.video_download_dock.set_source_url("")
            return
        url = view.url().toString()
        is_web = is_http_url(url)
        self.address_bar.setText(url if is_web else "")
        self.favorite_button.setEnabled(is_web)
        favorite = is_web and self.controller.storage.is_favorite(url)
        self.favorite_button.setIcon(
            ico_favorito() if favorite else ico_favorito_vazio()
        )
        self.favorite_button.setToolTip(
            TEXTO_UI["favorite_remove"]
            if favorite
            else TEXTO_UI["favorite_add"]
        )
        site = extract_site_host(url) if is_web else ""
        self._update_blocker_button(site)
        if self.notes_dock:
            self.notes_dock.set_site(site)
        if self.video_download_dock:
            self.video_download_dock.set_source_url(url)

    def _update_blocker_button(self, site: str | None = None, *_):
        if not hasattr(self, "blocker_button"):
            return
        if site is None:
            view = self._current_view()
            site = extract_site_host(view.url().toString()) if view else ""
        self._current_blocker_host = site
        count = self._blocked_counts_cache.get(site, 0) if site else 0
        self.blocker_button.setText(str(count))

        globally_enabled = self.blocker_interceptor.is_enabled()
        site_enabled = bool(site and self.blocker_interceptor.site_is_enabled(site))
        self.blocker_button.setEnabled(bool(site and globally_enabled))
        if not globally_enabled:
            tooltip = TEXTO_UI["blocker_tooltip_globally_disabled"]
        elif not site:
            tooltip = TEXTO_UI["blocker_tooltip_no_site"]
        elif site_enabled:
            tooltip = TEXTO_UI["blocker_tooltip_enabled"].format(
                site=site,
                count=count,
            )
        else:
            tooltip = TEXTO_UI["blocker_tooltip_disabled"].format(site=site)
        self.blocker_button.setToolTip(tooltip)

        if hasattr(self, "blocker_toggle_site_action"):
            self.blocker_toggle_site_action.setText(
                (
                    TEXTO_UI["blocker_toggle_site"]
                    if site_enabled
                    else TEXTO_UI["blocker_toggle_site_on"]
                )
                if site
                else TEXTO_UI["blocker_toggle_no_site"]
            )
            self.blocker_toggle_site_action.setToolTip(tooltip)
            self.blocker_toggle_site_action.setEnabled(
                bool(site and globally_enabled)
            )

    def _set_data_saver_from_button(self, enabled: bool):
        if self.private:
            self.blocker_interceptor.set_data_saver_enabled(enabled)
            return
        self.controller.save_data_saver_enabled(enabled)

    def _update_data_saver_button(self, *_):
        button = getattr(self, "data_saver_button", None)
        if button is None:
            return
        enabled = self.blocker_interceptor.is_data_saver_enabled()
        button.blockSignals(True)
        button.setChecked(enabled)
        button.blockSignals(False)
        button.setIcon(ico_economia_dados())
        button.setToolTip(
            TEXTO_UI[
                "data_saver_tooltip_on"
                if enabled
                else "data_saver_tooltip_off"
            ]
        )

    def _on_note_indicator_changed(self, host: str, has_note: bool):
        if (
            self.notes_dock
            and host == self.notes_dock.current_host
            and self.notes_action.isEnabled()
        ):
            self.notes_action.setText(
                TEXTO_UI["notes_title_with_note"]
                if has_note
                else TEXTO_UI["notes_title"]
            )

    def _on_blocked_count_changed(self, site: str, count: int):
        self._blocked_counts_cache[site] = count
        if site == getattr(self, "_current_blocker_host", ""):
            self._update_blocker_button(site)

    def _on_site_blocker_changed(self, *_):
        self._update_blocker_button()

    def _on_blocker_global_changed(self, *_):
        self._update_blocker_button()

    def toggle_site_blocker(self, *_):
        site = getattr(self, "_current_blocker_host", "")
        if not site:
            return
        if not self.blocker_interceptor.is_enabled():
            self.statusBar().showMessage(
                TEXTO_UI["blocker_global_disabled"],
                STATUS_CURTO_MS,
            )
            return
        enabled = not self.blocker_interceptor.site_is_enabled(site)
        changed = self.controller.save_site_blocker_enabled(
            site,
            enabled,
            private=self.private,
            interceptor=self.blocker_interceptor,
        )
        if not changed:
            return
        self.statusBar().showMessage(
            (
                TEXTO_UI["blocker_site_enabled"]
                if enabled
                else TEXTO_UI["blocker_site_disabled"]
            ).format(site=site),
            STATUS_CURTO_MS,
        )
        self._update_blocker_button(site)

    def open_blocker_settings(self, *_):
        dialog = BlockerSettingsDialog(self.controller, self)
        self._show_dialog(dialog)

    def open_note_host(self, host: str):
        if self.private or not host:
            return
        self._create_tab(
            url=f"https://{host}",
            home=False,
            select=True,
        )

    def _update_navigation_actions(self):
        view = self._current_view()
        self.back_action.setEnabled(bool(view and view.history().canGoBack()))
        self.forward_action.setEnabled(bool(view and view.history().canGoForward()))

    def toggle_favorite(self, *_):
        view = self._current_view()
        if not view:
            return
        url = view.url().toString()
        if not is_http_url(url):
            return
        if self.controller.storage.is_favorite(url):
            self.controller.storage.remove_favorite(url)
            self.statusBar().showMessage(
                TEXTO_UI["favorite_removed"],
                STATUS_CURTO_MS,
            )
        else:
            self.controller.storage.add_favorite(url, view.title() or self._host_label(view.url()))
            self.statusBar().showMessage(
                TEXTO_UI["favorite_added"],
                STATUS_CURTO_MS,
            )
        self._refresh_favorite_surfaces()

    def _refresh_favorite_surfaces(self):
        self.controller.refresh_home_pages()
        if hasattr(self, "favorites_status_bar"):
            self.favorites_status_bar.refresh()
        self._update_location_and_favorite()

    def open_history(self, *_):
        if self.private:
            return
        dialog = HistoryDialog(self.controller.storage, self)
        dialog.openRequested.connect(self.open_url_new_tab)
        dialog.changed.connect(self.controller.refresh_home_pages)
        self._show_dialog(dialog)

    def open_favorites(self, *_):
        dialog = FavoritesDialog(self.controller.storage, self)
        dialog.openRequested.connect(self.open_url_new_tab)
        dialog.changed.connect(self._refresh_favorite_surfaces)
        self._show_dialog(dialog)

    def _show_dialog(self, dialog: QWidget):
        self._dialogs.append(dialog)
        dialog.destroyed.connect(self._remove_dialog_reference)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def show_shortcuts(self, *_):
        self._show_dialog(ShortcutsDialog(self))

    def _remove_dialog_reference(self, *_):
        dialog = self.sender()
        if dialog in self._dialogs:
            self._dialogs.remove(dialog)

    def open_new_window(self, *_):
        self.controller.create_window(private=False)

    def open_private_window(self, *_):
        self.controller.create_window(private=True)

    def clear_history(self, *_):
        if self.private:
            return
        answer = popup_pergunta(
            TEXTO_UI["confirm_clear_title"],
            TEXTO_UI["confirm_clear_message"],
            self,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.controller.storage.clear_history()
            self.controller.refresh_home_pages()
            self.statusBar().showMessage(
                TEXTO_UI["history_cleared"],
                STATUS_CURTO_MS,
            )

    def show_about(self, *_):
        popup_info(
            TEXTO_UI["about_title"],
            TEXTO_UI["about_message"].format(version=VERSAO_APP),
            self,
        )

    def check_media_codecs(self, *_):
        view = self._current_view()
        if view is None:
            popup_info(
                TEXTO_UI["media_diagnostic_title"],
                TEXTO_UI["media_diagnostic_no_page"],
                self,
            )
            return
        view.page().runJavaScript(
            MEDIA_CAPABILITY_SCRIPT,
            self._show_media_codec_report,
        )

    def open_gpu_diagnostic(self, *_):
        view = self._current_view()
        if view is None:
            self._show_gpu_diagnostic_report(None)
            return
        view.page().runJavaScript(
            GRAPHICS_CAPABILITY_SCRIPT,
            self._show_gpu_diagnostic_report,
        )

    def _show_gpu_diagnostic_report(self, page_capabilities):
        snapshot = graphics_diagnostic_snapshot(page_capabilities)
        state_key = {
            "renderer_reported": "performance_gpu_state_renderer_reported",
            "software_renderer": "performance_gpu_state_software_renderer",
            "webgl_available": "performance_gpu_state_webgl_available",
            "qt_backend_unsupported": (
                "performance_gpu_state_qt_backend_unsupported"
            ),
            "qt_device_reported": "performance_gpu_state_qt_device_reported",
            "inconclusive": "performance_gpu_state_inconclusive",
        }.get(snapshot["state"], "performance_gpu_state_inconclusive")
        page = snapshot["page"]
        webgl = (
            TEXTO_UI["gpu_report_value_available"]
            if page["webgl_available"] is True
            else TEXTO_UI["gpu_report_value_unavailable"]
            if page["webgl_available"] is False
            else TEXTO_UI["gpu_report_value_inconclusive"]
        )
        if page["webgl_version"] and page["webgl_available"] is True:
            webgl = f"{webgl} ({page['webgl_version']})"
        webgpu = (
            TEXTO_UI["gpu_report_value_available"]
            if page["webgpu_available"] is True
            else TEXTO_UI["gpu_report_value_unavailable"]
            if page["webgpu_available"] is False
            else TEXTO_UI["gpu_report_value_inconclusive"]
        )
        lines = [
            TEXTO_UI["gpu_report_state"].format(
                state=TEXTO_UI[state_key]
            ),
            TEXTO_UI["gpu_report_webgl"].format(value=webgl),
            TEXTO_UI["gpu_report_webgpu"].format(value=webgpu),
        ]
        if page["vendor"]:
            lines.append(
                TEXTO_UI["gpu_report_vendor"].format(value=page["vendor"])
            )
        if page["renderer"]:
            lines.append(
                TEXTO_UI["gpu_report_renderer"].format(
                    value=page["renderer"]
                )
            )
        if snapshot["details"]:
            lines.append(TEXTO_UI["gpu_report_qt_title"])
            lines.extend(f"• {line}" for line in snapshot["details"])
        else:
            lines.append(TEXTO_UI["gpu_report_qt_empty"])
        lines.append(TEXTO_UI["gpu_report_limits"])
        popup_info(
            TEXTO_UI["gpu_diagnostic"],
            "\n".join(lines),
            self,
        )

    def _show_media_codec_report(self, capabilities):
        values = summarize_media_capabilities(capabilities)
        popup_info(
            TEXTO_UI["media_diagnostic_title"],
            TEXTO_UI["media_diagnostic_result"].format(**values),
            self,
        )

    def show_find_bar(self, *_):
        if self._current_view() is None:
            return
        self.find_bar.show()
        self.find_input.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.find_input.selectAll()

    def hide_find_bar(self, *_):
        self.find_bar.hide()
        view = self._current_view()
        if view:
            view.page().findText("")
        view.setFocus(Qt.FocusReason.OtherFocusReason) if view else None

    def find_next(self, *_):
        view = self._current_view()
        if view:
            view.page().findText(self.find_input.text())

    def find_previous(self, *_):
        view = self._current_view()
        if view:
            view.page().findText(
                self.find_input.text(),
                QWebEnginePage.FindFlag.FindBackward,
            )

    def zoom_in(self, *_):
        self._change_zoom(ZOOM_INCREMENTO)

    def zoom_out(self, *_):
        self._change_zoom(1 / ZOOM_INCREMENTO)

    def zoom_reset(self, *_):
        view = self._current_view()
        if view:
            view.setZoomFactor(ZOOM_INICIAL)

    def _change_zoom(self, factor: float):
        view = self._current_view()
        if view:
            view.setZoomFactor(
                min(ZOOM_MAXIMO, max(ZOOM_MINIMO, view.zoomFactor() * factor))
            )

    def _on_fullscreen_requested(self, request):
        if request.toggleOn():
            request.accept()
            self._fullscreen_active = True
            self._window_state_before_fullscreen = self.windowState()
            self.toolbar.hide()
            self.tabs.tabBar().hide()
            self._update_side_panel_tabs_inset()
            self._footer_bar.hide()
            self.showFullScreen()
            return
        request.accept()
        self._fullscreen_active = False
        if self._window_state_before_fullscreen & Qt.WindowState.WindowMaximized:
            self.showMaximized()
        else:
            self.showNormal()
        self.toolbar.show()
        self.tabs.tabBar().show()
        self._update_side_panel_tabs_inset()
        self._footer_bar.show()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self._update_window_controls()

    def closeEvent(self, event):
        if self._closing:
            event.accept()
            return
        self._closing = True
        if self.performance_panel is not None:
            self.performance_panel.stop_monitoring()
        self._ai_request_generation += 1
        self._ai_pending_context_key = ""
        for worker in list(self._ai_workers):
            worker.cancel()
        for worker in list(self._ai_workers):
            worker.wait(2500)
        if self.notes_dock:
            self.notes_dock.save_current_note()
        self.controller.unregister_window(self)
        for index in range(self.tabs.count() - 1, -1, -1):
            widget = self.tabs.widget(index)
            if isinstance(widget, (ExplorerTab, FilePreviewTab)):
                widget.shutdown()
                continue
            view = widget
            if isinstance(view, QWebEngineView):
                page = view.page()
                if isinstance(page, BrowserPage):
                    self.controller.cancel_restore_page(page)
                self._dispose_view(view)
        super().closeEvent(event)
