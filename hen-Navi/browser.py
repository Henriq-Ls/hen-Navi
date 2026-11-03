"""Perfil, páginas WebEngine, abas, sessão e downloads do hen-Nave."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
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
    CAPTURA_ALTURA_MAXIMA_PX,
    CAPTURA_INTERVALO_REPINTURA_MS,
    CAPTURA_LARGURA_MAXIMA_PX,
    CAPTURA_PASTA,
    STATUS_CARREGAMENTO_MS,
    STATUS_CURTO_MS,
    STATUS_DOWNLOAD_MS,
    ESQUEMA_INTERNO,
    FONTE_PIXEL_ARQUIVO,
    CHAVE_BLOQUEADOR_ATIVO,
    CHAVE_URL_LISTA_BLOQUEIO,
    LARGURA_ENDERECO_MINIMA,
    LARGURA_BARRA_CONTROLES_JANELA,
    LIMITE_RECENTES_INICIO,
    NOME_PERFIL_WEB,
    TEMAS,
    TEXTO_UI,
    TAMANHO_BOTAO_CONTROLE_JANELA,
    TAMANHO_ICONE_CONTROLE_JANELA,
    TEMA_PADRAO,
    TITULO_APP,
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
from _THREADS_ import thread_manager
from _THREADS_.ai_assistant import AiProviderWorker
from _CONFIGURA_.temas import (
    CHAVES_CORES_PERSONALIZADAS,
    CHAVE_TEMA_PERSONALIZADO,
    TEMA_PERSONALIZADO,
)
from PySide6.QtCore import (
    QEvent,
    QObject,
    QPoint,
    QStandardPaths,
    QSize,
    Qt,
    QUrl,
    QUrlQuery,
    Signal,
)
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QDesktopServices,
    QFont,
    QFontDatabase,
    QIcon,
    QKeySequence,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDockWidget,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizeGrip,
    QSizePolicy,
    QStackedWidget,
    QStatusBar,
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
    QWebEngineUrlScheme,
)
from PySide6.QtWebEngineWidgets import QWebEngineView

from _APP_.Navegador import BrowserTabs
from _APP_.atalhos_dialog import ShortcutsDialog
from _APP_.anotacoes import NotesDock
from _APP_.ai_assistant import AiAssistantDock
from _APP_.ai_config import AiSettingsDialog
from _APP_.bloqueador_dialog import BlockerSettingsDialog
from _APP_.browser_downloads import BrowserDownloadsDock
from _APP_.dialogs import FavoritesDialog, HistoryDialog
from _APP_.download_video import VideoDownloadDock
from _APP_.captura import CaptureManager
from _APP_.inspector import PageInspectorDock, inspection_pick_marker
from _APP_.media_support import MEDIA_CAPABILITY_SCRIPT, summarize_media_capabilities
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
    ico_favorito,
    ico_favorito_vazio,
    ico_favoritos,
    ico_fechar_aba,
    ico_fechar_aba_hover,
    ico_fechar,
    ico_home,
    ico_historico,
    ico_ia,
    ico_imagem,
    ico_info,
    ico_janela,
    ico_janela_fechar,
    ico_janela_maximizar,
    ico_janela_minimizar,
    ico_janela_restaurar,
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
    remove_private_start_page,
    write_private_start_page,
)
from _APP_.startpage import generate_start_page
from _APPDATA_.storage import BrowserStorage
from _ULTILIDADES_.capture_utils import capture_filename
from _ULTILIDADES_.site_utils import extract_site_host, is_valid_https_url
from _ULTILIDADES_.utils import is_http_url, resolve_address
from _CONFIGURA_.theme_engine import (
    normalizar_tema_personalizado,
    obter_tema,
    stylesheet_for_theme,
)


_SCHEME_REGISTERED = False


def register_custom_url_scheme():
    """Registra o esquema interno antes da criação de QApplication."""
    global _SCHEME_REGISTERED
    if _SCHEME_REGISTERED:
        return
    scheme_name = ESQUEMA_INTERNO.encode("ascii")
    existing = QWebEngineUrlScheme.schemeByName(scheme_name)
    if existing.name():
        _SCHEME_REGISTERED = True
        return
    scheme = QWebEngineUrlScheme(scheme_name)
    scheme.setSyntax(QWebEngineUrlScheme.Syntax.HostAndPort)
    scheme.setFlags(QWebEngineUrlScheme.Flag.SecureScheme)
    scheme.setDefaultPort(443)
    QWebEngineUrlScheme.registerScheme(scheme)
    _SCHEME_REGISTERED = True


class AnonymousProfileLease(QObject):
    """Mantém um perfil anônimo vivo até a última view ser destruída."""

    def __init__(
        self,
        parent,
        start_page_path: str,
        matcher: BlocklistMatcher,
        blocker_enabled: bool,
    ):
        super().__init__(parent)
        self.start_page_path = start_page_path
        self.profile = QWebEngineProfile(self)
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies
        )
        BrowserController.configure_profile(self.profile)
        self.interceptor = AdBlockInterceptor(
            matcher,
            enabled=blocker_enabled,
            parent=self,
        )
        self.profile.setUrlRequestInterceptor(self.interceptor)
        self._view_count = 0
        self._closing = False

    def register_view(self, view: QWebEngineView):
        self._view_count += 1
        view.destroyed.connect(self._on_view_destroyed)

    def request_close(self):
        self._closing = True
        remove_private_start_page(self.start_page_path)
        self._release_if_ready()

    def _on_view_destroyed(self, *_):
        self._view_count = max(0, self._view_count - 1)
        self._release_if_ready()

    def _release_if_ready(self):
        if self._closing and self._view_count == 0:
            remove_private_start_page(self.start_page_path)
            self.profile.deleteLater()
            self.deleteLater()


class BrowserPage(QWebEnginePage):
    """Página que intercepta buscas internas e protege a aba Principal."""

    inspectionElementSelected = Signal(str)

    def __init__(
        self,
        profile: QWebEngineProfile,
        parent_view: QWebEngineView,
        browser_window: "BrowserWindow",
        home_file_path: str,
        *,
        home_locked: bool = False,
        start_page: bool = False,
        restored: bool = False,
    ):
        super().__init__(profile, parent_view)
        self.browser_window = browser_window
        self.home_file_path = os.path.realpath(home_file_path)
        self.home_locked = home_locked
        self.is_start_page_active = start_page
        self.restore_pending = restored
        self.fullScreenRequested.connect(browser_window._on_fullscreen_requested)

    def javaScriptConsoleMessage(self, level, message, line_number, source_id):
        marker = inspection_pick_marker()
        if message.startswith(marker):
            selector = message[len(marker):]
            if selector:
                self.inspectionElementSelected.emit(selector)
            return
        super().javaScriptConsoleMessage(level, message, line_number, source_id)

    def acceptNavigationRequest(self, url: QUrl, navigation_type, is_main_frame: bool) -> bool:
        scheme = url.scheme().lower()
        if scheme == "file":
            if not is_main_frame:
                return False
            requested_path = os.path.realpath(url.toLocalFile())
            return requested_path == self.home_file_path

        if scheme == ESQUEMA_INTERNO:
            if not is_main_frame or not self.is_start_page_active:
                return False
            query = QUrlQuery(url).queryItemValue("q")
            self.browser_window._search_from_home(query, self.home_locked)
            return False

        if not is_main_frame:
            return True

        if scheme in {"http", "https"}:
            target = url.toString()
            if not is_http_url(target):
                return False
            if self.home_locked and self.is_start_page_active:
                self.browser_window.open_url_new_tab(target)
                return False
            self.is_start_page_active = False
            return True

        if scheme == "about" and url.toString().lower() == "about:blank":
            return True
        return False

    def createWindow(self, window_type):
        return self.browser_window._create_popup_page()


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
            exceptions=self.storage.get_site_blocking_exceptions(),
            parent=self,
        )
        self.profile.setUrlRequestInterceptor(self.normal_interceptor)
        self.profile.downloadRequested.connect(self._on_download_requested)
        self.application.aboutToQuit.connect(self._shutdown)
        self.application.aboutToQuit.connect(thread_manager.encerrar_todas)
        self._write_start_pages()

    @staticmethod
    def configure_profile(profile: QWebEngineProfile):
        settings = profile.settings()
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.FullScreenSupportEnabled,
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
        urls = self.storage.load_session()
        self.restoring = bool(urls)
        self._restore_pending = len(urls)
        window = self.create_window(private=False, restore_urls=urls, show=False)
        window.tabs.setCurrentIndex(0)
        window.show()
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

    def _private_start_page_html(self) -> str:
        return generate_start_page(
            self.storage.get_favorites(),
            [],
            private=True,
            theme_id=self.theme_id,
            custom_theme=self.custom_theme,
        )

    def _write_start_pages(self):
        favorites = self.storage.get_favorites()
        recent = self.storage.recent_unique(LIMITE_RECENTES_INICIO)
        page_html = generate_start_page(
            favorites,
            recent,
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

    def _on_download_requested(self, download: QWebEngineDownloadRequest):
        profile = self.sender()
        if not isinstance(profile, QWebEngineProfile):
            download.cancel()
            return
        window = self._window_for_profile(profile)
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
        target, _selected_filter = QFileDialog.getSaveFileName(
            window,
            TEXTO_UI["download_dialog"],
            os.path.join(downloads_dir, suggested),
            TEXTO_UI["download_filter"],
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
        self._download_entry_ids[id(download)] = entry_id
        download.stateChanged.connect(self._on_download_state_changed)
        download.accept()
        self._refresh_download_panels()
        window.statusBar().showMessage(
            TEXTO_UI["download_started"].format(name=target_path.name),
            STATUS_DOWNLOAD_INICIO_MS,
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
        window = self._window_for_profile(profile) if profile is not None else None
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


class TabCloseButton(QToolButton):
    """Botão de fechar aba com feedback visual explícito ao passar o mouse."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("tabCloseButton")
        self.setIconSize(QSize(14, 14))
        self.setFixedSize(QSize(24, 24))
        self.setAutoRaise(True)
        self.refresh_icon()

    def refresh_icon(self):
        self.setIcon(
            ico_fechar_aba_hover() if self.underMouse() else ico_fechar_aba()
        )

    def enterEvent(self, event):
        self.setIcon(ico_fechar_aba_hover())
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setIcon(ico_fechar_aba())
        super().leaveEvent(event)


class BrandMenuButton(QToolButton):
    """Botão do app que abre o menu e serve de alça para mover a janela."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._press_position: QPoint | None = None
        self._window_position: QPoint | None = None
        self._drag_started = False
        self._system_move_started = False
        self.clicked.connect(self._show_app_menu)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_position = event.globalPosition().toPoint()
            self._window_position = self.window().pos()
            self._drag_started = False
            self._system_move_started = False
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            self._press_position is None
            or not event.buttons() & Qt.MouseButton.LeftButton
        ):
            super().mouseMoveEvent(event)
            return

        position = event.globalPosition().toPoint()
        delta = position - self._press_position
        if not self._drag_started:
            if delta.manhattanLength() < QApplication.startDragDistance():
                event.accept()
                return
            self._drag_started = True
            handle = self.window().windowHandle()
            if handle is not None:
                try:
                    self._system_move_started = bool(handle.startSystemMove())
                except RuntimeError:
                    self._system_move_started = False

        if not self._system_move_started and self._window_position is not None:
            self.window().move(self._window_position + delta)
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._press_position:
            if not self._drag_started:
                self._show_app_menu()
            self._press_position = None
            self._window_position = None
            self._drag_started = False
            self._system_move_started = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _show_app_menu(self, *_):
        menu = self.menu()
        if menu is not None:
            menu.popup(self.mapToGlobal(QPoint(0, self.height())))


class BrowserWindow(QMainWindow):
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
        self.ai_store = ProviderStore(appdata.pasta_config)
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
        self.video_download_dock: VideoDownloadDock | None = None
        self.downloads_dock: BrowserDownloadsDock | None = None
        self._closing = False
        self._initializing = True
        self._fullscreen_active = False
        self._window_state_before_fullscreen = Qt.WindowState.WindowNoState
        self._dialogs: list[QWidget] = []
        self.capture_manager = CaptureManager(self)
        self.capture_manager.imageSaved.connect(self._show_capture_saved)
        self.capture_manager.pdfSaved.connect(self._show_pdf_saved)
        self.capture_manager.failed.connect(self._show_capture_error)
        self.setProperty("privateMode", "true" if private else "false")
        self.setStyleSheet(
            stylesheet_for_theme(
                self.controller.theme_id,
                private=self.private,
                custom_theme=self.controller.custom_theme,
            )
        )
        self._build_interface()
        self._create_tab(primary=True, home=True, select=True)
        for url in restore_urls or []:
            if is_http_url(url):
                self._create_tab(
                    url=url,
                    primary=False,
                    home=False,
                    select=False,
                    restored=True,
                )
        self.tabs.setCurrentIndex(0)
        self._initializing = False
        self._update_location_and_favorite()

    def statusBar(self):
        status_bar = getattr(self, "_status_bar", None)
        return status_bar if status_bar is not None else super().statusBar()

    def _build_interface(self):
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
        self._window_content_layout.addWidget(self._body_row, 1)
        self._active_side_panel: str | None = None

        self.window_controls_toolbar = QToolBar(
            TEXTO_UI["window_controls_toolbar"],
            self,
        )
        self.window_controls_toolbar.setObjectName("windowControlsToolbar")
        self.window_controls_toolbar.setOrientation(Qt.Orientation.Vertical)
        self.window_controls_toolbar.setMovable(False)
        self.window_controls_toolbar.setFloatable(False)
        self.window_controls_toolbar.setAllowedAreas(
            Qt.ToolBarArea.RightToolBarArea
        )
        self.window_controls_toolbar.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonIconOnly
        )
        self.window_controls_toolbar.setIconSize(
            QSize(TAMANHO_ICONE_CONTROLE_JANELA, TAMANHO_ICONE_CONTROLE_JANELA)
        )
        self.window_controls_toolbar.setFixedWidth(
            LARGURA_BARRA_CONTROLES_JANELA
        )

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
        self.close_window_button = self._add_window_control_button(
            self.close_window_action,
            "closeWindowButton",
        )
        self.maximize_window_button = self._add_window_control_button(
            self.maximize_window_action,
            "maximizeWindowButton",
        )
        self.minimize_window_button = self._add_window_control_button(
            self.minimize_window_action,
            "minimizeWindowButton",
        )
        self.window_controls_toolbar.addSeparator()

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
        self.brand_button.setText(TITULO_APP)
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
        self.home_action = self._make_action(
            TEXTO_UI["home"],
            ico_home(),
            self.go_home,
            atalho("inicio"),
        )
        for action in (
            self.back_action,
            self.forward_action,
            self.reload_action,
            self.home_action,
        ):
            self.toolbar.addAction(action)

        self.address_bar = QLineEdit(self)
        self.address_bar.setObjectName("addressBar")
        self.address_bar.setPlaceholderText(TEXTO_UI["address_placeholder"])
        self.address_bar.setMinimumWidth(LARGURA_ENDERECO_MINIMA)
        self.address_bar.setClearButtonEnabled(True)
        self.address_bar.returnPressed.connect(self.navigate_address)
        self.toolbar.addWidget(self.address_bar)

        self.blocker_button = QToolButton(self)
        self.blocker_button.setObjectName("blockerButton")
        self.blocker_button.setIcon(ico_bloqueador())
        self.blocker_button.setIconSize(QSize(14, 14))
        self.blocker_button.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self.blocker_button.setText("0")
        self.blocker_button.setToolTip(TEXTO_UI["blocker_tooltip_no_site"])
        self.blocker_button.clicked.connect(self.toggle_site_blocker)
        self.toolbar.addWidget(self.blocker_button)

        self.favorite_button = QToolButton(self)
        self.favorite_button.setObjectName("favoriteButton")
        self.favorite_button.setIcon(ico_favorito_vazio())
        self.favorite_button.setIconSize(QSize(16, 16))
        self.favorite_button.setFixedSize(QSize(28, 28))
        self.favorite_button.setToolTip(TEXTO_UI["favorite_add"])
        self.favorite_button.setAccessibleName(TEXTO_UI["favorite_toggle"])
        self.favorite_button.clicked.connect(self.toggle_favorite)
        self.toolbar.addWidget(self.favorite_button)

        self.video_download_button = QToolButton(self)
        self.video_download_button.setObjectName("videoDownloadButton")
        self.video_download_button.setIcon(ico_video_download())
        self.video_download_button.setIconSize(QSize(16, 16))
        self.video_download_button.setFixedSize(QSize(28, 28))
        self.video_download_button.setToolTip(TEXTO_UI["video_download_button"])
        self.video_download_button.setAccessibleName(
            TEXTO_UI["video_download_button"]
        )
        self.toolbar.addWidget(self.video_download_button)

        self.capture_button = QToolButton(self)
        self.capture_button.setObjectName("captureButton")
        self.capture_button.setIcon(ico_captura())
        self.capture_button.setIconSize(QSize(16, 16))
        self.capture_button.setFixedSize(QSize(28, 28))
        self.capture_button.setToolTip(TEXTO_UI["capture_menu"])
        self.capture_button.setAccessibleName(TEXTO_UI["capture_menu"])
        self.capture_button.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )
        self.toolbar.addWidget(self.capture_button)

        self.notes_button = QToolButton(self)
        self.notes_button.setObjectName("notesButton")
        self.notes_button.setIcon(ico_anotacoes())
        self.notes_button.setIconSize(QSize(16, 16))
        self.notes_button.setFixedSize(QSize(28, 28))
        self.notes_button.setToolTip(TEXTO_UI["notes_title"])
        self.notes_button.setAccessibleName(TEXTO_UI["notes_title"])
        self.toolbar.addWidget(self.notes_button)

        self.ai_button = QToolButton(self)
        self.ai_button.setObjectName("aiButton")
        self.ai_button.setIcon(ico_ia())
        self.ai_button.setIconSize(QSize(16, 16))
        self.ai_button.setFixedSize(QSize(28, 28))
        self.ai_button.setToolTip(TEXTO_UI["ai_placeholder"])
        self.ai_button.setAccessibleName(TEXTO_UI["ai_placeholder"])
        self.toolbar.addWidget(self.ai_button)

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
        self.controller.blockerSettingsChanged.connect(self._update_blocker_button)

        if self.private:
            self.private_indicator = QToolButton(self)
            self.private_indicator.setObjectName("privateIndicator")
            self.private_indicator.setText(TEXTO_UI["private_short"])
            self.private_indicator.setEnabled(False)
            self.toolbar.addWidget(self.private_indicator)

        self.main_menu = self._build_menu()
        self.brand_button.setMenu(self.main_menu)

        self.tabs = BrowserTabs(self)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self._on_current_changed)
        self.tabs.setCornerWidget(self._build_corner_button())

        self._left_layout.addWidget(self.tabs, 1)
        self._left_layout.addWidget(self._build_find_bar())
        self._status_bar = QStatusBar(self._left_panel)
        self._status_bar.setSizeGripEnabled(False)
        self._left_layout.addWidget(self._status_bar)
        self.setCentralWidget(self._window_content)
        self.find_bar.hide()
        self._status_bar.showMessage(TEXTO_UI["ready"])
        self._create_notes_dock()
        self.notes_button.setDefaultAction(self.notes_action)
        self._create_video_download_dock()
        self.video_download_button.setDefaultAction(self.video_download_action)
        self._create_browser_downloads_dock()
        self._create_inspector_dock()
        self._create_ai_dock()
        self._build_capture_menu()
        self._build_settings_menu()
        self._finish_window_controls_toolbar()
        self._arrange_right_docks()

    def _make_action(self, label, icon, callback, shortcut=None):
        action = QAction(icon, label, self)
        action.setToolTip(label)
        action.triggered.connect(callback)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
            action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        return action

    def _add_window_control_button(
        self,
        action: QAction,
        object_name: str,
    ) -> QToolButton:
        button = QToolButton(self.window_controls_toolbar)
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
        self.window_controls_toolbar.addWidget(button)
        return button

    def _add_sidebar_action_button(self, action: QAction) -> QToolButton:
        object_name = {
            getattr(self, "downloads_action", None): "browserDownloadsButton",
            getattr(self, "inspect_action", None): "inspectPageButton",
            getattr(self, "open_app_data_action", None): "openAppDataButton",
            getattr(self, "clear_cache_action", None): "clearCacheButton",
        }.get(action, "sidebarActionButton")
        return self._add_window_control_button(action, object_name)

    def _finish_window_controls_toolbar(self):
        spacer = QWidget(self.window_controls_toolbar)
        spacer.setObjectName("windowControlsSpacer")
        spacer.setSizePolicy(
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Expanding,
        )
        self.window_controls_toolbar.addWidget(spacer)

        self.window_resize_grip = QSizeGrip(self.window_controls_toolbar)
        self.window_resize_grip.setObjectName("windowResizeGrip")
        self.window_resize_grip.setFixedSize(
            QSize(
                TAMANHO_BOTAO_CONTROLE_JANELA,
                TAMANHO_BOTAO_CONTROLE_JANELA,
            )
        )
        self.window_resize_grip.setToolTip(TEXTO_UI["window_resize"])
        self.window_controls_toolbar.addWidget(self.window_resize_grip)
        self._update_window_controls()

    def _toggle_maximize_restore(self, *_):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self._update_window_controls()

    def _update_window_controls(self):
        action = getattr(self, "maximize_window_action", None)
        if action is None:
            return
        if self.isMaximized():
            label = TEXTO_UI["window_restore"]
            action.setIcon(ico_janela_restaurar())
        else:
            label = TEXTO_UI["window_maximize"]
            action.setIcon(ico_janela_maximizar())
        action.setText(label)
        action.setToolTip(label)
        button = getattr(self, "maximize_window_button", None)
        if button is not None:
            button.setAccessibleName(label)
            button.setToolTip(label)

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

        for action in (
            self.history_action,
            self.favorites_action,
            self.downloads_action,
        ):
            menu.addAction(action)
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
        menu.addAction(self.media_diagnostic_action)
        menu.addAction(self.about_action)

        self.new_tab_action = self._make_action(
            TEXTO_UI["new_tab"],
            ico_nova_aba(),
            self.new_home_tab,
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

    def _create_notes_dock(self):
        if self.private:
            self.notes_action = QAction(TEXTO_UI["notes_title"], self)
            self.notes_action.setIcon(ico_anotacoes())
            self.notes_action.setEnabled(False)
            self.notes_action.setToolTip(TEXTO_UI["notes_private_unavailable"])
            return

        self.notes_dock = NotesDock(
            self.controller.storage,
            self._side_panel_stack,
        )
        self.notes_dock.setFeatures(
            QDockWidget.DockWidgetFeature.NoDockWidgetFeatures
        )
        self._side_panel_stack.addWidget(self.notes_dock)
        self.notes_dock.hide()
        self.notes_dock.openHostRequested.connect(self.open_note_host)
        self.notes_action = QAction(
            ico_anotacoes(),
            TEXTO_UI["notes_title"],
            self,
        )
        self.notes_action.setCheckable(True)
        self.notes_action.setIcon(ico_anotacoes())
        self.notes_action.setToolTip(TEXTO_UI["notes_title"])
        self.notes_action.setShortcut(QKeySequence(atalho("anotacoes")))
        self.notes_action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.notes_action.triggered.connect(
            lambda _checked=False: self._toggle_side_panel("notes")
        )
        self.notes_dock.noteChanged.connect(self._on_note_indicator_changed)

    def _create_video_download_dock(self):
        self.video_download_dock = VideoDownloadDock(
            self._side_panel_stack,
        )
        self.video_download_dock.setFeatures(
            QDockWidget.DockWidgetFeature.NoDockWidgetFeatures
        )
        self._side_panel_stack.addWidget(self.video_download_dock)
        self.video_download_dock.hide()
        self.video_download_dock.visibilityChanged.connect(
            self._on_video_download_visibility_changed
        )
        self.video_download_action = QAction(
            ico_video_download(),
            TEXTO_UI["video_download_button"],
            self,
        )
        self.video_download_action.setCheckable(True)
        self.video_download_action.setIcon(ico_video_download())
        self.video_download_action.setToolTip(TEXTO_UI["video_download_button"])
        self.video_download_action.triggered.connect(
            lambda _checked=False: self._toggle_side_panel("video")
        )

    def _create_browser_downloads_dock(self):
        self.downloads_dock = BrowserDownloadsDock(
            None if self.private else self.controller.storage,
            private=self.private,
            parent=self._side_panel_stack,
        )
        self.downloads_dock.setFeatures(
            QDockWidget.DockWidgetFeature.NoDockWidgetFeatures
        )
        self._side_panel_stack.addWidget(self.downloads_dock)
        self.downloads_dock.hide()
        self._add_sidebar_action_button(self.downloads_action)

    def _create_inspector_dock(self):
        self.inspector_dock = PageInspectorDock(
            self._side_panel_stack,
        )
        self.inspector_dock.setFeatures(
            QDockWidget.DockWidgetFeature.NoDockWidgetFeatures
        )
        self._side_panel_stack.addWidget(self.inspector_dock)
        self.inspector_dock.hide()
        self.inspector_dock.visibilityChanged.connect(
            self._on_inspector_visibility_changed
        )
        self.inspect_action = QAction(
            ico_inspecionar(),
            TEXTO_UI["inspect_page"],
            self,
        )
        self.inspect_action.setCheckable(True)
        self.inspect_action.setIcon(ico_inspecionar())
        self.inspect_action.setToolTip(TEXTO_UI["inspect_page"])
        self.inspect_action.triggered.connect(
            lambda _checked=False: self._toggle_side_panel("inspector")
        )
        self._add_sidebar_action_button(self.inspect_action)
        view = self._current_view()
        self.inspector_dock.set_page(view.page() if view else None)

    def _create_ai_dock(self):
        self.ai_dock = AiAssistantDock(self._side_panel_stack)
        self.ai_dock.setFeatures(
            QDockWidget.DockWidgetFeature.NoDockWidgetFeatures
        )
        self._side_panel_stack.addWidget(self.ai_dock)
        self.ai_dock.hide()
        self.ai_dock.requestRequested.connect(self._handle_ai_request)
        self.ai_dock.cancelRequested.connect(self._cancel_ai_request)
        self.ai_dock.settingsRequested.connect(self.open_ai_settings)
        self.ai_action = QAction(
            ico_ia(),
            TEXTO_UI["ai_placeholder"],
            self,
        )
        self.ai_action.setCheckable(True)
        self.ai_action.setShortcut(QKeySequence(atalho("assistente_ia")))
        self.ai_action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.ai_action.setToolTip(TEXTO_UI["ai_placeholder"])
        self.ai_action.triggered.connect(
            lambda _checked=False: self._toggle_side_panel("ai")
        )
        self.addAction(self.ai_action)
        self.ai_button.setDefaultAction(self.ai_action)
        self._refresh_ai_provider()

    def _arrange_right_docks(self):
        self.addToolBar(
            Qt.ToolBarArea.RightToolBarArea,
            self.window_controls_toolbar,
        )

    def _pin_window_controls_to_right(self):
        """Mantém a barra na área externa direita, fora do layout dos painéis."""
        self.addToolBar(
            Qt.ToolBarArea.RightToolBarArea,
            self.window_controls_toolbar,
        )
        self.window_controls_toolbar.setMovable(False)
        self.window_controls_toolbar.setFloatable(False)
        self.window_controls_toolbar.setAllowedAreas(
            Qt.ToolBarArea.RightToolBarArea
        )

    def _toggle_side_panel(self, panel_name: str):
        panels = {
            "notes": (self.notes_dock, getattr(self, "notes_action", None)),
            "video": (
                self.video_download_dock,
                getattr(self, "video_download_action", None),
            ),
            "downloads": (
                self.downloads_dock,
                getattr(self, "downloads_action", None),
            ),
            "inspector": (
                self.inspector_dock,
                getattr(self, "inspect_action", None),
            ),
            "ai": (
                self.ai_dock,
                getattr(self, "ai_action", None),
            ),
        }
        panel, _action = panels[panel_name]
        if panel is None:
            return

        if (
            self._active_side_panel == panel_name
            and self._side_panel_container.isVisible()
        ):
            self._side_panel_container.hide()
            self._active_side_panel = None
        else:
            self._active_side_panel = panel_name
            self._side_panel_stack.setCurrentWidget(panel)
            self._side_panel_title.setText(panel.windowTitle())
            self._side_panel_container.show()

        if panel_name == "ai" and self._active_side_panel == "ai":
            self._refresh_ai_provider()
            view = self._current_view()
            self.ai_dock.set_context_key(self._ai_context_key(view))
        elif panel_name == "downloads" and self._active_side_panel == "downloads":
            self.downloads_dock.refresh()

        for name, (_widget, action) in panels.items():
            if action is not None:
                action.setChecked(name == self._active_side_panel)

    def _close_side_panel(self, *_):
        self._side_panel_container.hide()
        self._side_panel_title.clear()
        self._active_side_panel = None
        for action_name in (
            "notes_action",
            "video_download_action",
            "downloads_action",
            "inspect_action",
            "ai_action",
        ):
            action = getattr(self, action_name, None)
            if action is not None:
                action.setChecked(False)

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
        self._refresh_ai_provider()

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

        view = self._current_view()
        page = view.page() if view else None
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
        status = (
            TEXTO_UI["ai_local_notice"]
            if not is_cloud
            else TEXTO_UI["ai_extracting"]
        )
        self.ai_dock.set_busy(True, status)
        log.info(
            "BrowserWindow",
            "_handle_ai_request",
            f"solicitação aceita; ação={'resumo' if summarize else 'pergunta'}; "
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
        if provider.get("kind") == "ollama":
            self.ai_dock.show_local_notice()
            self.ai_dock.set_busy(True, TEXTO_UI["ai_local_notice"])
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
            self._ai_context_key(self.tabs.widget(index)) == worker.ai_context_key
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

    def _on_inspector_visibility_changed(self, visible: bool):
        if not visible:
            return
        view = self._current_view()
        self.inspector_dock.set_page(view.page() if view else None)
        self.inspector_dock.refresh_dom()

    def toggle_video_download_dock(self, *_):
        self._toggle_side_panel("video")

    def toggle_browser_downloads(self, *_):
        self._toggle_side_panel("downloads")

    def _on_video_download_visibility_changed(self, visible: bool):
        if not visible or not self.video_download_dock:
            return
        view = self._current_view()
        url = view.url().toString() if view else ""
        self.video_download_dock.set_source_url(url)
        self.video_download_dock.analyze_link()

    def _build_capture_menu(self):
        self.capture_menu = QMenu(TEXTO_UI["capture_menu"], self)
        self.visible_capture_action = self._make_action(
            TEXTO_UI["capture_visible"],
            ico_captura(),
            self.capture_visible_page,
        )
        self.full_page_capture_action = self._make_action(
            TEXTO_UI["capture_full_page"],
            ico_imagem(),
            self.capture_full_page,
        )
        self.pdf_capture_action = self._make_action(
            TEXTO_UI["capture_pdf"],
            ico_pdf(),
            self.save_page_as_pdf,
        )
        self.capture_menu.addAction(self.visible_capture_action)
        self.capture_menu.addAction(self.full_page_capture_action)
        self.capture_menu.addAction(self.pdf_capture_action)
        self.capture_button.setMenu(self.capture_menu)

        self.capture_shortcut_action = QAction(TEXTO_UI["capture_menu"], self)
        self.capture_shortcut_action.setShortcut(
            QKeySequence(atalho("captura"))
        )
        self.capture_shortcut_action.setShortcutContext(
            Qt.ShortcutContext.WindowShortcut
        )
        self.capture_shortcut_action.triggered.connect(self.show_capture_menu)
        self.addAction(self.capture_shortcut_action)

    def _build_settings_menu(self):
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
        )
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

        settings_menu.addSeparator()
        settings_menu.addSection(TEXTO_UI["blocker_name"])

        self.blocker_settings_action = self._make_action(
            TEXTO_UI["blocker_settings"],
            ico_bloqueador(),
            self.open_blocker_settings,
        )
        settings_menu.addAction(self.blocker_settings_action)

        self.blocker_toggle_site_action = self._make_action(
            TEXTO_UI["blocker_toggle_site"],
            ico_bloqueador(),
            self.toggle_site_blocker,
            atalho("bloqueador_site"),
        )
        settings_menu.addAction(self.blocker_toggle_site_action)

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
        settings_menu.addAction(self.open_app_data_action)
        settings_menu.addAction(self.clear_cache_action)

        self._add_sidebar_action_button(self.open_app_data_action)
        self._add_sidebar_action_button(self.clear_cache_action)

    def open_app_data(self, *_):
        opened = QDesktopServices.openUrl(
            QUrl.fromLocalFile(appdata.pasta_raiz)
        )
        message = (
            TEXTO_UI["app_data_opened"]
            if opened
            else TEXTO_UI["app_data_open_error"]
        )
        self.statusBar().showMessage(message, STATUS_CURTO_MS)

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

    def show_capture_menu(self, *_):
        self.capture_menu.popup(
            self.capture_button.mapToGlobal(
                self.capture_button.rect().bottomLeft()
            )
        )

    def _default_capture_path(self, kind: str, extension: str) -> str:
        pictures = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.PicturesLocation
        )
        base = Path(pictures) if pictures else Path.home() / "Pictures"
        folder = base / CAPTURA_PASTA
        folder.mkdir(parents=True, exist_ok=True)
        return str(folder / capture_filename(kind, extension=extension))

    def _choose_capture_path(
        self,
        *,
        kind: str,
        extension: str,
        title: str,
        file_filter: str,
    ) -> str | None:
        try:
            default_path = self._default_capture_path(kind, extension)
        except OSError as error:
            self._show_capture_error(str(error))
            return None
        target, _selected_filter = QFileDialog.getSaveFileName(
            self,
            title,
            default_path,
            file_filter,
        )
        if not target:
            return None
        target_path = Path(target)
        expected_suffix = f".{extension.lower().lstrip('.')}"
        if target_path.suffix.lower() != expected_suffix:
            target_path = target_path.with_suffix(expected_suffix)
        return str(target_path)

    def _capture_is_available(self) -> bool:
        if not self.capture_manager.busy:
            return True
        self.statusBar().showMessage(
            TEXTO_UI["capture_busy"],
            STATUS_CURTO_MS,
        )
        return False

    def capture_visible_page(self, *_):
        if not self._capture_is_available():
            return
        view = self._current_view()
        if view is None:
            return
        path = self._choose_capture_path(
            kind="parte_visivel",
            extension="png",
            title=TEXTO_UI["capture_save_title"],
            file_filter=TEXTO_UI["capture_image_filter"],
        )
        if not path:
            return
        try:
            self.capture_manager.capture_visible(view, path)
        except (OSError, RuntimeError, ValueError) as error:
            self._show_capture_error(str(error))
            return
        self.statusBar().showMessage(
            TEXTO_UI["capture_started"],
            STATUS_DOWNLOAD_INICIO_MS,
        )

    def capture_full_page(self, *_):
        if not self._capture_is_available():
            return
        view = self._current_view()
        if view is None:
            return
        path = self._choose_capture_path(
            kind="pagina_inteira",
            extension="png",
            title=TEXTO_UI["capture_save_title"],
            file_filter=TEXTO_UI["capture_image_filter"],
        )
        if not path:
            return
        try:
            self.capture_manager.capture_full_page(
                view,
                path,
                max_width=CAPTURA_LARGURA_MAXIMA_PX,
                max_height=CAPTURA_ALTURA_MAXIMA_PX,
                settle_interval_ms=CAPTURA_INTERVALO_REPINTURA_MS,
            )
        except (OSError, RuntimeError, ValueError) as error:
            self._show_capture_error(str(error))
            return
        self.statusBar().showMessage(
            TEXTO_UI["capture_started"],
            STATUS_DOWNLOAD_INICIO_MS,
        )

    def save_page_as_pdf(self, *_):
        if not self._capture_is_available():
            return
        view = self._current_view()
        if view is None:
            return
        path = self._choose_capture_path(
            kind="pagina",
            extension="pdf",
            title=TEXTO_UI["capture_pdf_save_title"],
            file_filter=TEXTO_UI["capture_pdf_filter"],
        )
        if not path:
            return
        try:
            self.capture_manager.print_pdf(view.page(), path)
        except (OSError, RuntimeError, ValueError) as error:
            self._show_capture_error(str(error))
            return
        self.statusBar().showMessage(
            TEXTO_UI["capture_started"],
            STATUS_DOWNLOAD_INICIO_MS,
        )

    def _show_capture_saved(self, path: str, clipped: bool):
        message = TEXTO_UI["capture_done_message"].format(path=path)
        if clipped:
            message += f"\n\n{TEXTO_UI['capture_truncated_warning']}"
        self._show_capture_result(message, path)

    def _show_pdf_saved(self, path: str):
        self._show_capture_result(
            TEXTO_UI["capture_pdf_done_message"].format(path=path),
            path,
        )

    def _show_capture_result(self, message: str, path: str):
        dialog = criar_popup(
            TEXTO_UI["capture_done_title"],
            message,
            self,
            botoes=QMessageBox.StandardButton.NoButton,
        )
        open_folder_button = dialog.addButton(
            TEXTO_UI["capture_open_folder"],
            QMessageBox.ButtonRole.AcceptRole,
        )
        dialog.addButton(
            TEXTO_UI["capture_close"],
            QMessageBox.ButtonRole.RejectRole,
        )
        dialog.exec()
        if dialog.clickedButton() is open_folder_button:
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(Path(path).parent))
            )

    def _show_capture_error(self, error: str):
        popup_aviso(
            TEXTO_UI["capture_error_title"],
            TEXTO_UI["capture_error_message"].format(error=error),
            self,
        )

    def _build_corner_button(self):
        button = QToolButton(self)
        button.setObjectName("newTabButton")
        button.setIcon(ico_nova_aba())
        button.setIconSize(QSize(14, 14))
        button.setFixedSize(QSize(24, 24))
        button.setToolTip(TEXTO_UI["new_tab_tooltip"])
        button.setAccessibleName(TEXTO_UI["new_tab_tooltip"])
        button.clicked.connect(self.new_home_tab)
        return button

    def apply_theme(self):
        self.setStyleSheet(
            stylesheet_for_theme(
                self.controller.theme_id,
                private=self.private,
                custom_theme=self.controller.custom_theme,
            )
        )
        icon_factories = (
            ("back_action", ico_voltar),
            ("forward_action", ico_avancar),
            ("reload_action", ico_atualizar),
            ("home_action", ico_home),
            ("history_action", ico_historico),
            ("favorites_action", ico_favoritos),
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
        self.capture_button.setIcon(ico_captura())
        self.notes_button.setIcon(ico_anotacoes())
        self.ai_button.setIcon(ico_ia())
        self._update_window_controls()
        corner_button = self.tabs.cornerWidget()
        if isinstance(corner_button, QToolButton):
            corner_button.setIcon(ico_nova_aba())
        tab_bar = self.tabs.tabBar()
        for index in range(1, self.tabs.count()):
            close_button = tab_bar.tabButton(
                index,
                tab_bar.ButtonPosition.RightSide,
            )
            if isinstance(close_button, TabCloseButton):
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
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.controller.set_custom_theme(dialog.custom_theme())

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
        primary: bool = False,
        home: bool = False,
        select: bool = True,
        restored: bool = False,
        popup: bool = False,
    ) -> BrowserPage:
        view = QWebEngineView(self.tabs)
        home_path = self._start_page_path
        page = BrowserPage(
            self.profile,
            view,
            self,
            home_path,
            home_locked=primary,
            start_page=home,
            restored=restored,
        )
        view.setPage(page)
        view.setZoomFactor(ZOOM_INICIAL)
        view.urlChanged.connect(self._on_view_url_changed)
        view.titleChanged.connect(self._on_view_title_changed)
        view.iconChanged.connect(self._on_view_icon_changed)
        view.loadProgress.connect(self._on_load_progress)
        view.loadFinished.connect(self._on_load_finished)

        if self.profile_lease:
            self.profile_lease.register_view(view)

        label = TEXTO_UI["main_tab"] if primary else TEXTO_UI["new_tab"]
        index = self.tabs.insertTab(0 if primary else self.tabs.count(), view, label)
        bar = self.tabs.tabBar()
        if primary:
            bar.setTabButton(index, bar.ButtonPosition.LeftSide, None)
            bar.setTabButton(index, bar.ButtonPosition.RightSide, None)
        else:
            close_button = TabCloseButton(bar)
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
        self.tabs.setTabToolTip(index, label)

        if select:
            self.tabs.setCurrentIndex(index)
        if url:
            view.setUrl(QUrl(url))
        elif home:
            view.setUrl(QUrl.fromLocalFile(home_path))
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

    def new_home_tab(self, *_):
        self._create_tab(home=True, primary=False, select=True)
        if not self._initializing and not self.private:
            self.controller.notify_session_change()

    def open_url_new_tab(self, url: str):
        if not is_http_url(url):
            return
        self._create_tab(url=url, primary=False, home=False, select=True)
        if not self._initializing and not self.private:
            self.controller.notify_session_change()

    def _create_popup_page(self):
        page = self._create_tab(
            primary=False,
            home=False,
            select=True,
            popup=True,
        )
        if not self.private:
            self.controller.notify_session_change()
        return page

    def _search_from_home(self, query: str, home_locked: bool):
        query = (query or "").strip()
        if not query:
            return
        target = resolve_address(
            query,
            self.controller.search_engine,
        )
        if not is_http_url(target):
            return
        if home_locked:
            self.open_url_new_tab(target)
            return
        view = self._current_view()
        if view:
            view.setUrl(QUrl(target))

    def navigate_address(self, *_):
        target = resolve_address(
            self.address_bar.text(),
            self.controller.search_engine,
        )
        if not target:
            return
        if self.tabs.currentIndex() == 0:
            self.open_url_new_tab(target)
        else:
            view = self._current_view()
            if view:
                view.setUrl(QUrl(target))
                if not self.private:
                    self.controller.notify_session_change()

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
        self.tabs.setCurrentIndex(0)
        view = self.tabs.widget(0)
        if isinstance(view, QWebEngineView):
            view.setUrl(QUrl.fromLocalFile(self._start_page_path))

    def focus_address(self, *_):
        self.address_bar.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.address_bar.selectAll()

    def close_current_tab(self, *_):
        self.close_tab(self.tabs.currentIndex())

    def close_tab(self, index: int):
        if index <= 0 or index >= self.tabs.count():
            return
        view = self.tabs.widget(index)
        if not isinstance(view, QWebEngineView):
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
        for index in range(1, self.tabs.count()):
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

    def _on_current_changed(self, index: int):
        if index == 0 and not self._closing:
            self.controller.refresh_home_pages()
        self._update_location_and_favorite()
        self._update_navigation_actions()
        self._sync_inspector_page()
        if hasattr(self, "ai_dock"):
            self.ai_dock.set_context_key(
                self._ai_context_key(self._current_view())
            )

    def _sync_inspector_page(self):
        inspector = getattr(self, "inspector_dock", None)
        if inspector is None:
            return
        view = self._current_view()
        inspector.set_page(view.page() if view else None)

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
        page = view.page()
        if index == 0:
            label = TEXTO_UI["main_tab"]
        else:
            label = (title or "").strip() or self._host_label(view.url())
        self.tabs.setTabText(index, label)
        url = view.url().toString()
        self.tabs.setTabToolTip(index, f"{title or label}\n{url}")

    def _on_view_icon_changed(self, icon: QIcon):
        view = self.sender()
        if isinstance(view, QWebEngineView):
            index = self.tabs.indexOf(view)
            if index >= 0 and index != 0:
                self.tabs.setTabIcon(index, icon)

    def _on_load_progress(self, progress: int):
        view = self.sender()
        if view is self._current_view() and progress < 100:
            self.statusBar().showMessage(
                f"{TEXTO_UI['loading_prefix']} {progress}%",
                STATUS_CARREGAMENTO_MS,
            )

    def _on_load_finished(self, success: bool):
        view = self.sender()
        if not isinstance(view, QWebEngineView):
            return
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
        if index == 0:
            label = TEXTO_UI["main_tab"]
        elif view.page().url().scheme() == "file":
            label = TEXTO_UI["new_tab"]
        else:
            label = view.title() or self._host_label(view.url())
        self.tabs.setTabText(index, label)
        self.tabs.setTabToolTip(index, f"{view.title() or label}\n{view.url().toString()}")

    @staticmethod
    def _host_label(url: QUrl) -> str:
        host = url.host()
        return host or TEXTO_UI["new_tab"]

    def _update_location_and_favorite(self):
        view = self._current_view()
        if not view:
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
            primary=False,
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
        self.controller.refresh_home_pages()
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
        dialog.changed.connect(self.controller.refresh_home_pages)
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

    def _show_media_codec_report(self, capabilities):
        values = summarize_media_capabilities(capabilities)
        popup_info(
            TEXTO_UI["media_diagnostic_title"],
            TEXTO_UI["media_diagnostic_result"].format(**values),
            self,
        )

    def show_find_bar(self, *_):
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
            self.window_controls_toolbar.hide()
            self.tabs.tabBar().hide()
            self.statusBar().hide()
            self.showFullScreen()
            return
        request.accept()
        self._fullscreen_active = False
        if self._window_state_before_fullscreen & Qt.WindowState.WindowMaximized:
            self.showMaximized()
        else:
            self.showNormal()
        self.toolbar.show()
        self.window_controls_toolbar.show()
        self.tabs.tabBar().show()
        self.statusBar().show()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self._update_window_controls()

    def closeEvent(self, event):
        if self._closing:
            event.accept()
            return
        self._closing = True
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
            view = self.tabs.widget(index)
            if isinstance(view, QWebEngineView):
                page = view.page()
                if isinstance(page, BrowserPage):
                    self.controller.cancel_restore_page(page)
                self._dispose_view(view)
        super().closeEvent(event)
