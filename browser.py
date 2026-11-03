"""Perfil, páginas WebEngine, abas, sessão e downloads do hen-Nave."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlencode

from _CONFIGURA_ import (
    ARQUIVO_BANCO,
    ARQUIVO_INICIO,
    ARQUIVO_INICIO_ANONIMO,
    ATALHO_ENDERECO,
    ATALHO_FAVORITO,
    ATALHO_FAVORITOS,
    ATALHO_FECHAR_ABA,
    ATALHO_HISTORICO,
    ATALHO_HOME,
    ATALHO_JANELA_ANONIMA,
    ATALHO_LOCALIZAR,
    ATALHO_NOVA_ABA,
    ATALHO_NOVA_JANELA,
    ATALHO_RECARREGAR,
    ATALHO_ZOOM_MAIS,
    ATALHO_ZOOM_MENOS,
    ATALHO_ZOOM_RESET,
    ESQUEMA_INTERNO,
    ESTILO_NAVEGADOR_ANONIMO,
    ESTILO_NAVEGADOR_EXTRA,
    LARGURA_ENDERECO_MINIMA,
    LIMITE_RECENTES_INICIO,
    NOME_PERFIL_WEB,
    ZOOM_INCREMENTO,
    ZOOM_INICIAL,
    ZOOM_MAXIMO,
    ZOOM_MINIMO,
)
from _LOGS_ import log
from _APPDATA_ import appdata
from _THREADS_ import thread_manager
from PySide6.QtCore import QObject, QStandardPaths, Qt, QUrl, QUrlQuery
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
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
from _ULTILIDADES_.icones import icone
from dialogs import FavoritesDialog, HistoryDialog
from startpage import generate_start_page
from storage import BrowserStorage
from utils import is_http_url, resolve_address


_SCHEME_REGISTERED = False


def register_custom_url_scheme():
    """Registra o esquema interno antes da criação de QApplication."""
    global _SCHEME_REGISTERED
    if _SCHEME_REGISTERED:
        return
    scheme_name = ESQUEMA_INTERNO.encode("ascii")
    existing = QWebEngineUrlScheme.schemeByName(scheme_name)
    if existing.schemeName():
        _SCHEME_REGISTERED = True
        return
    scheme = QWebEngineUrlScheme(scheme_name)
    scheme.setSyntax(QWebEngineUrlScheme.Syntax.HostAndPort)
    scheme.setFlags(QWebEngineUrlScheme.Flag.SecureScheme)
    QWebEngineUrlScheme.registerScheme(scheme)
    _SCHEME_REGISTERED = True


class AnonymousProfileLease(QObject):
    """Mantém um perfil anônimo vivo até a última view ser destruída."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.profile = QWebEngineProfile(self)
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies
        )
        BrowserController.configure_profile(self.profile)
        self._view_count = 0
        self._closing = False

    def register_view(self, view: QWebEngineView):
        self._view_count += 1
        view.destroyed.connect(self._on_view_destroyed)

    def request_close(self):
        self._closing = True
        self._release_if_ready()

    def _on_view_destroyed(self, *_):
        self._view_count = max(0, self._view_count - 1)
        self._release_if_ready()

    def _release_if_ready(self):
        if self._closing and self._view_count == 0:
            self.profile.deleteLater()
            self.deleteLater()


class BrowserPage(QWebEnginePage):
    """Página que intercepta buscas internas e protege a aba Principal."""

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

    def acceptNavigationRequest(self, url: QUrl, navigation_type, is_main_frame: bool) -> bool:
        if not is_main_frame:
            return True

        scheme = url.scheme().lower()
        if scheme == ESQUEMA_INTERNO:
            if not self.is_start_page_active:
                return False
            query = QUrlQuery(url).queryItemValue("q")
            self.browser_window._search_from_home(query, self.home_locked)
            return False

        if scheme == "file":
            requested_path = os.path.realpath(url.toLocalFile())
            return requested_path == self.home_file_path

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

    def __init__(self, application: QApplication):
        super().__init__(application)
        self.application = application
        self.storage = BrowserStorage(os.path.join(appdata.pasta_config, ARQUIVO_BANCO))
        self.normal_windows: list[BrowserWindow] = []
        self.private_windows: list[BrowserWindow] = []
        self.restoring = False
        self._restore_pending = 0
        self._shutting_down = False
        self.active_downloads: dict[int, QWebEngineDownloadRequest] = {}
        self._download_profiles: dict[int, QWebEngineProfile] = {}

        self.profile = QWebEngineProfile(NOME_PERFIL_WEB, self)
        self.profile.setPersistentStoragePath(appdata.pasta_raiz)
        self.profile.setCachePath(appdata.pasta_cache)
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
        )
        self.configure_profile(self.profile)
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

        lease = AnonymousProfileLease(self) if private else None
        window = MainWindow(
            controller=self,
            private=private,
            restore_urls=restore_urls or [],
            profile_lease=lease,
        )
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

    def start_page_path(self, private: bool) -> str:
        filename = ARQUIVO_INICIO_ANONIMO if private else ARQUIVO_INICIO
        return os.path.join(appdata.pasta_cache, filename)

    def _write_start_pages(self):
        favorites = self.storage.get_favorites()
        recent = self.storage.recent_unique(LIMITE_RECENTES_INICIO)
        for private in (False, True):
            page_html = generate_start_page(
                favorites,
                [] if private else recent,
                private=private,
            )
            path = Path(self.start_page_path(private))
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                path.write_text(page_html, encoding="utf-8")
            except OSError as error:
                log.erro("BrowserController", "_write_start_pages", str(error))

    def refresh_home_pages(self, *_):
        self._write_start_pages()
        for window in self.normal_windows + self.private_windows:
            window.refresh_start_pages()

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
        suggested = os.path.basename(download.suggestedFileName()) or "download"
        target, _selected_filter = QFileDialog.getSaveFileName(
            window,
            "Salvar download",
            os.path.join(downloads_dir, suggested),
            "Todos os arquivos (*)",
        )
        if not target:
            download.cancel()
            return

        target_path = Path(target)
        download.setDownloadDirectory(str(target_path.parent))
        download.setDownloadFileName(target_path.name)
        self.active_downloads[id(download)] = download
        self._download_profiles[id(download)] = profile
        download.stateChanged.connect(self._on_download_state_changed)
        download.accept()
        window.statusBar().showMessage(f"Baixando: {target_path.name}", 5000)

    def _on_download_state_changed(self, *_):
        download = self.sender()
        if download is None or id(download) not in self.active_downloads:
            return
        state = download.state()
        completed = QWebEngineDownloadRequest.DownloadState.DownloadCompleted
        cancelled = QWebEngineDownloadRequest.DownloadState.DownloadCancelled
        if state not in {completed, cancelled}:
            return

        profile = self._download_profiles.pop(id(download), None)
        self.active_downloads.pop(id(download), None)
        window = self._window_for_profile(profile) if profile is not None else None
        if window:
            if state == completed:
                message = f"Download concluído: {download.downloadFileName()}"
            else:
                message = "Download cancelado ou interrompido"
            window.statusBar().showMessage(message, 8000)

    def _shutdown(self):
        self._shutting_down = True
        self.storage.close()


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
        self.controller = controller
        self.private = private
        self.profile_lease = profile_lease
        self.profile = profile_lease.profile if profile_lease else controller.profile
        self._closing = False
        self._initializing = True
        self._fullscreen_active = False
        self._dialogs: list[QWidget] = []
        self.setProperty("privateMode", "true" if private else "false")
        if private:
            self.setStyleSheet(ESTILO_NAVEGADOR_EXTRA + ESTILO_NAVEGADOR_ANONIMO)
        else:
            self.setStyleSheet(ESTILO_NAVEGADOR_EXTRA)
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

    def _build_interface(self):
        self.toolbar = QToolBar("Navegação", self)
        self.toolbar.setObjectName("navigationToolbar")
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)

        self.back_action = self._make_action("Voltar", "fa5s.arrow-left", self.go_back)
        self.forward_action = self._make_action("Avançar", "fa5s.arrow-right", self.go_forward)
        self.reload_action = self._make_action(
            "Recarregar",
            "fa5s.sync-alt",
            self.reload_current,
            ATALHO_RECARREGAR,
        )
        self.home_action = self._make_action(
            "Início",
            "fa5s.home",
            self.go_home,
            ATALHO_HOME,
        )
        for action in (
            self.back_action,
            self.forward_action,
            self.reload_action,
            self.home_action,
        ):
            self.toolbar.addAction(action)

        self.new_tab_button = QToolButton(self)
        self.new_tab_button.setText("+")
        self.new_tab_button.setToolTip("Nova aba")
        self.new_tab_button.clicked.connect(self.new_home_tab)
        self.toolbar.addWidget(self.new_tab_button)

        self.address_bar = QLineEdit(self)
        self.address_bar.setObjectName("addressBar")
        self.address_bar.setPlaceholderText("Pesquisar ou digitar um endereço")
        self.address_bar.setMinimumWidth(LARGURA_ENDERECO_MINIMA)
        self.address_bar.setClearButtonEnabled(True)
        self.address_bar.returnPressed.connect(self.navigate_address)
        self.toolbar.addWidget(self.address_bar)

        self.favorite_button = QToolButton(self)
        self.favorite_button.setObjectName("favoriteButton")
        self.favorite_button.setText("☆")
        self.favorite_button.setToolTip("Adicionar aos favoritos")
        self.favorite_button.clicked.connect(self.toggle_favorite)
        self.toolbar.addWidget(self.favorite_button)

        if self.private:
            self.private_indicator = QToolButton(self)
            self.private_indicator.setObjectName("privateIndicator")
            self.private_indicator.setText("Anônima")
            self.private_indicator.setEnabled(False)
            self.toolbar.addWidget(self.private_indicator)

        self.menu_button = QToolButton(self)
        self.menu_button.setText("☰")
        self.menu_button.setToolTip("Menu")
        self.menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.menu_button.setMenu(self._build_menu())
        self.toolbar.addWidget(self.menu_button)

        self.tabs = BrowserTabs(self)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self._on_current_changed)
        self.tabs.setCornerWidget(self._build_corner_button())

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.tabs, 1)
        layout.addWidget(self._build_find_bar())
        self.setCentralWidget(central)
        self.find_bar.hide()
        self.statusBar().showMessage("Pronto")

    def _make_action(self, label, icon_name, callback, shortcut=None):
        action = QAction(icone(icon_name), label, self)
        action.triggered.connect(callback)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
            action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        return action

    def _build_menu(self) -> QMenu:
        menu = QMenu(self)
        self.history_action = self._make_action(
            "Histórico",
            "fa5s.history",
            self.open_history,
            ATALHO_HISTORICO,
        )
        self.history_action.setEnabled(not self.private)
        self.favorites_action = self._make_action(
            "Favoritos",
            "fa5s.star",
            self.open_favorites,
            ATALHO_FAVORITOS,
        )
        self.new_window_action = self._make_action(
            "Nova janela",
            "fa5s.window-maximize",
            self.open_new_window,
            ATALHO_NOVA_JANELA,
        )
        self.private_window_action = self._make_action(
            "Nova janela anônima",
            "fa5s.user-secret",
            self.open_private_window,
            ATALHO_JANELA_ANONIMA,
        )
        self.find_action = self._make_action(
            "Localizar",
            "fa5s.search",
            self.show_find_bar,
            ATALHO_LOCALIZAR,
        )
        self.zoom_in_action = self._make_action(
            "Aumentar zoom",
            "fa5s.search-plus",
            self.zoom_in,
            ATALHO_ZOOM_MAIS,
        )
        self.zoom_out_action = self._make_action(
            "Diminuir zoom",
            "fa5s.search-minus",
            self.zoom_out,
            ATALHO_ZOOM_MENOS,
        )
        self.zoom_reset_action = self._make_action(
            "Zoom padrão",
            "fa5s.undo",
            self.zoom_reset,
            ATALHO_ZOOM_RESET,
        )
        self.clear_history_action = self._make_action(
            "Limpar histórico",
            "fa5s.trash-alt",
            self.clear_history,
        )
        self.clear_history_action.setEnabled(not self.private)
        self.about_action = self._make_action("Sobre", "fa5s.info-circle", self.show_about)

        for action in (
            self.history_action,
            self.favorites_action,
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
        menu.addAction(self.about_action)

        self.new_tab_action = self._make_action(
            "Nova aba",
            "fa5s.plus",
            self.new_home_tab,
            ATALHO_NOVA_ABA,
        )
        self.close_tab_action = self._make_action(
            "Fechar aba",
            "fa5s.times",
            self.close_current_tab,
            ATALHO_FECHAR_ABA,
        )
        self.address_action = self._make_action(
            "Focar endereço",
            "fa5s.search",
            self.focus_address,
            ATALHO_ENDERECO,
        )
        self.favorite_action = self._make_action(
            "Adicionar/remover favorito",
            "fa5s.star",
            self.toggle_favorite,
            ATALHO_FAVORITO,
        )
        self.toolbar.addAction(self.new_tab_action)
        self.toolbar.addAction(self.close_tab_action)
        self.toolbar.addAction(self.address_action)
        self.toolbar.addAction(self.favorite_action)
        return menu

    def _build_corner_button(self):
        button = QToolButton(self)
        button.setText("+")
        button.setToolTip("Nova aba")
        button.clicked.connect(self.new_home_tab)
        return button

    def _build_find_bar(self):
        self.find_bar = QWidget(self)
        self.find_bar.setObjectName("findBar")
        layout = QHBoxLayout(self.find_bar)
        layout.setContentsMargins(8, 4, 8, 4)
        self.find_input = QLineEdit(self.find_bar)
        self.find_input.setPlaceholderText("Localizar nesta página")
        self.find_input.returnPressed.connect(self.find_next)
        layout.addWidget(self.find_input, 1)
        previous_button = QPushButton("Anterior", self.find_bar)
        next_button = QPushButton("Próximo", self.find_bar)
        close_button = QPushButton("Fechar", self.find_bar)
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
        home_path = self.controller.start_page_path(self.private)
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

        label = "Principal" if primary else "Nova aba"
        index = self.tabs.insertTab(0 if primary else self.tabs.count(), view, label)
        if primary:
            bar = self.tabs.tabBar()
            bar.setTabButton(index, bar.ButtonPosition.LeftSide, None)
            bar.setTabButton(index, bar.ButtonPosition.RightSide, None)
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
        return page

    def _search_from_home(self, query: str, home_locked: bool):
        query = (query or "").strip()
        if not query:
            return
        target = resolve_address(query)
        if not is_http_url(target):
            return
        if home_locked:
            self.open_url_new_tab(target)
            return
        view = self._current_view()
        if view:
            view.setUrl(QUrl(target))

    def navigate_address(self, *_):
        target = resolve_address(self.address_bar.text())
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
            view.setUrl(QUrl.fromLocalFile(self.controller.start_page_path(self.private)))

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
                view.setUrl(QUrl.fromLocalFile(self.controller.start_page_path(self.private)))

    def _on_current_changed(self, index: int):
        if index == 0 and not self._closing:
            self.controller.refresh_home_pages()
        self._update_location_and_favorite()
        self._update_navigation_actions()

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
            label = "Principal"
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
            self.statusBar().showMessage(f"Carregando… {progress}%")

    def _on_load_finished(self, success: bool):
        view = self.sender()
        if not isinstance(view, QWebEngineView):
            return
        page = view.page()
        url = view.url().toString()
        home_path = os.path.realpath(self.controller.start_page_path(self.private))
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
            self.statusBar().showMessage("Concluído" if success else "Não foi possível carregar a página", 3500)
        if not self.private:
            self.controller.notify_session_change()
        self._update_location_and_favorite()
        self._update_tab_title(view)

    def _update_tab_title(self, view: QWebEngineView):
        index = self.tabs.indexOf(view)
        if index < 0:
            return
        if index == 0:
            label = "Principal"
        elif view.page().url().scheme() == "file":
            label = "Nova aba"
        else:
            label = view.title() or self._host_label(view.url())
        self.tabs.setTabText(index, label)
        self.tabs.setTabToolTip(index, f"{view.title() or label}\n{view.url().toString()}")

    @staticmethod
    def _host_label(url: QUrl) -> str:
        host = url.host()
        return host or "Nova aba"

    def _update_location_and_favorite(self):
        view = self._current_view()
        if not view:
            return
        url = view.url().toString()
        is_web = is_http_url(url)
        self.address_bar.setText(url if is_web else "")
        self.favorite_button.setEnabled(is_web)
        favorite = is_web and self.controller.storage.is_favorite(url)
        self.favorite_button.setText("★" if favorite else "☆")
        self.favorite_button.setToolTip(
            "Remover dos favoritos" if favorite else "Adicionar aos favoritos"
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
            self.statusBar().showMessage("Favorito removido", 3000)
        else:
            self.controller.storage.add_favorite(url, view.title() or self._host_label(view.url()))
            self.statusBar().showMessage("Favorito adicionado", 3000)
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
        answer = QMessageBox.question(
            self,
            "Limpar histórico",
            "Remover todo o histórico salvo neste computador?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.controller.storage.clear_history()
            self.controller.refresh_home_pages()
            self.statusBar().showMessage("Histórico removido", 3000)

    def show_about(self, *_):
        QMessageBox.about(
            self,
            "Sobre o hen-Nave",
            "hen-Nave v0.1.0\n\n"
            "Navegador desktop em Python, PySide6 e QtWebEngine.",
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
            self.toolbar.hide()
            self.tabs.tabBar().hide()
            self.statusBar().hide()
            self.showFullScreen()
            return
        request.accept()
        self._fullscreen_active = False
        self.showNormal()
        self.toolbar.show()
        self.tabs.tabBar().show()
        self.statusBar().show()

    def closeEvent(self, event):
        if self._closing:
            event.accept()
            return
        self._closing = True
        self.controller.unregister_window(self)
        for index in range(self.tabs.count() - 1, -1, -1):
            view = self.tabs.widget(index)
            if isinstance(view, QWebEngineView):
                page = view.page()
                if isinstance(page, BrowserPage):
                    self.controller.cancel_restore_page(page)
                self._dispose_view(view)
        super().closeEvent(event)
