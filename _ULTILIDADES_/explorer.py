# _ULTILIDADES_/explorer.py
"""
Explorer — navegador de arquivos reutilizável para projetos PySide6.

O componente é desenhado pela aplicação e não abre QFileDialog nem o seletor
nativo do Windows, macOS ou Linux.

Uso rápido:
    caminho = Explorer.get_open_file_name(self)
    caminhos = Explorer.get_open_file_names(self)
    pasta = Explorer.get_existing_directory(self)
    destino = Explorer.get_save_file_name(self)

Para navegação com ações de gerenciamento:
    dialogo = Explorer(self, mode=ExplorerMode.MANAGE)
    dialogo.file_activated.connect(self.abrir_arquivo_no_app)
    dialogo.exec()
"""

from __future__ import annotations

import fnmatch
import os
import re
import shutil
import stat
import subprocess
import sys
import threading
import time
from enum import Enum
from typing import Sequence

from PySide6.QtCore import (
    QFile,
    QDir,
    QModelIndex,
    QObject,
    QRunnable,
    QSortFilterProxyModel,
    QSize,
    QThreadPool,
    QTimer,
    Qt,
    QStandardPaths,
    Signal,
)
from PySide6.QtGui import QAction, QImage, QImageReader, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QToolButton,
    QTreeView,
    QVBoxLayout,
    QFileSystemModel,
    QMenu,
)

from _CONFIGURA_ import (
    EXPLORER_ALTURA_MIN,
    EXPLORER_ALTURA_PADRAO,
    EXPLORER_CABECALHOS,
    EXPLORER_ESPACAMENTO,
    EXPLORER_FILTROS,
    EXPLORER_LARGURA_COLUNA_DATA,
    EXPLORER_LARGURA_COLUNA_TAMANHO,
    EXPLORER_LARGURA_COLUNA_TIPO,
    EXPLORER_LARGURA_LOCAIS,
    EXPLORER_LARGURA_MIN,
    EXPLORER_LARGURA_PADRAO,
    EXPLORER_MARGEM,
    EXPLORER_PREVIEW_ALTURA,
    EXPLORER_PREVIEW_DEBOUNCE_MS,
    EXPLORER_PREVIEW_MAX_BYTES,
    EXPLORER_PREVIEW_MAX_ITEMS,
    EXPLORER_PREVIEW_MAX_PIXELS,
    EXPLORER_PREVIEW_MAX_SECONDS,
    EXPLORER_PREVIEW_TAMANHO,
    EXPLORER_TAMANHO_ICONE,
    EXPLORER_TEXTOS,
)
from _ULTILIDADES_.icones import (
    ico_abrir,
    ico_adicionar,
    ico_atualizar,
    ico_avancar,
    ico_buscar,
    ico_copiar,
    ico_home as ico_inicio,
    ico_lixo,
    ico_nova_pasta,
    ico_renomear,
    ico_subir,
    ico_voltar,
)
from _ULTILIDADES_.popups import (
    popup_aviso,
    popup_confirmar,
    popup_confirmar_perigo,
    popup_erro,
)

_IMAGE_EXTENSIONS = {
    ".bmp", ".gif", ".ico", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp",
}
_VIDEO_EXTENSIONS = {
    ".avi", ".m4v", ".mkv", ".mov", ".mp4", ".mpeg", ".mpg", ".webm", ".wmv",
}


class _ExplorerPreviewSignals(QObject):
    completed = Signal(int, str, object)


class _ExplorerPreviewTask(QRunnable):
    """Lê metadados e gera miniaturas sem bloquear a janela."""

    def __init__(self, request_id: int, path: str, cancel_event) -> None:
        super().__init__()
        self.request_id = request_id
        self.path = path
        self.cancel_event = cancel_event
        self.signals = _ExplorerPreviewSignals()

    def run(self) -> None:
        try:
            result = self._inspect_path()
        except Exception:
            result = {"kind": "error"}
        self.signals.completed.emit(self.request_id, self.path, result)

    def _inspect_path(self) -> dict:
        if self.cancel_event.is_set():
            return {"kind": "cancelled"}

        metadata = os.stat(self.path, follow_symlinks=False)
        common = {
            "name": os.path.basename(self.path) or self.path,
            "path": self.path,
            "modified": metadata.st_mtime,
        }
        if stat.S_ISLNK(metadata.st_mode):
            return {**common, "kind": "link"}
        if stat.S_ISDIR(metadata.st_mode):
            return {**common, "kind": "folder", **self._folder_properties()}
        if not stat.S_ISREG(metadata.st_mode):
            return {**common, "kind": "unsupported", "size": metadata.st_size}

        suffix = os.path.splitext(self.path)[1].casefold()
        kind = (
            "image" if suffix in _IMAGE_EXTENSIONS
            else "video" if suffix in _VIDEO_EXTENSIONS
            else "file"
        )
        result = {**common, "kind": kind, "size": metadata.st_size}
        if kind == "image":
            result["image"], result["issue"] = self._load_image()
        elif kind == "video":
            result["image"] = self._load_video_frame()
        return result

    def _folder_properties(self) -> dict:
        started = time.monotonic()
        pending = [self.path]
        total_bytes = 0
        file_count = 0
        folder_count = 0
        visited = 0
        partial = False

        while pending:
            if self.cancel_event.is_set():
                return {"cancelled": True}
            if (
                visited >= EXPLORER_PREVIEW_MAX_ITEMS
                or time.monotonic() - started >= EXPLORER_PREVIEW_MAX_SECONDS
            ):
                partial = True
                break

            current = pending.pop()
            try:
                with os.scandir(current) as entries:
                    for entry in entries:
                        if self.cancel_event.is_set():
                            return {"cancelled": True}
                        visited += 1
                        if visited > EXPLORER_PREVIEW_MAX_ITEMS:
                            partial = True
                            break
                        if entry.is_symlink():
                            continue
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                folder_count += 1
                                pending.append(entry.path)
                            elif entry.is_file(follow_symlinks=False):
                                file_count += 1
                                total_bytes += entry.stat(
                                    follow_symlinks=False
                                ).st_size
                        except OSError:
                            partial = True
                        if time.monotonic() - started >= EXPLORER_PREVIEW_MAX_SECONDS:
                            partial = True
                            break
            except OSError:
                partial = True
            if partial:
                break

        return {
            "size": total_bytes,
            "files": file_count,
            "folders": folder_count,
            "partial": partial,
        }

    def _load_image(self):
        try:
            if os.path.getsize(self.path) > EXPLORER_PREVIEW_MAX_BYTES:
                return None, "too_large"
            reader = QImageReader(self.path)
            reader.setAutoTransform(True)
            image_size = reader.size()
            if image_size.isValid():
                if image_size.width() * image_size.height() > EXPLORER_PREVIEW_MAX_PIXELS:
                    return None, "too_large"
                reader.setScaledSize(
                    image_size.scaled(
                        EXPLORER_PREVIEW_TAMANHO,
                        EXPLORER_PREVIEW_ALTURA,
                        Qt.AspectRatioMode.KeepAspectRatio,
                    )
                )
            image = reader.read()
            return (image, "") if not image.isNull() else (None, "unreadable")
        except OSError:
            return None, "unreadable"

    @staticmethod
    def _localizar_ffmpeg() -> str | None:
        nomes = ("ffmpeg", "ffmpeg.exe")
        pastas = (
            "",
            "bin",
            "FFmpeg",
            os.path.join("FFmpeg", "bin"),
            os.path.join("FFMPEG", "FFmpeg"),
            os.path.join("FFMPEG", "FFmpeg", "bin"),
        )
        raizes = [
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        ]
        if getattr(sys, "frozen", False):
            raizes.insert(0, os.path.dirname(sys.executable))
        for raiz in raizes:
            for pasta in pastas:
                for nome in nomes:
                    candidato = os.path.join(raiz, pasta, nome)
                    if os.path.isfile(candidato):
                        return candidato
        return shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")

    def _load_video_frame(self):
        ffmpeg = self._localizar_ffmpeg()
        if not ffmpeg or self.cancel_event.is_set():
            return None
        for timestamp in ("0.5", "0"):
            comando = [
                ffmpeg,
                "-hide_banner",
                "-loglevel", "error",
                "-nostdin",
                "-ss", timestamp,
                "-i", self.path,
                "-frames:v", "1",
                "-vf",
                f"scale={EXPLORER_PREVIEW_TAMANHO}:"
                f"{EXPLORER_PREVIEW_ALTURA}:"
                "force_original_aspect_ratio=decrease",
                "-an",
                "-f", "image2pipe",
                "-vcodec", "png",
                "pipe:1",
            ]
            try:
                resultado = subprocess.run(
                    comando,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    timeout=4,
                    check=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except (OSError, subprocess.TimeoutExpired):
                continue
            if resultado.returncode != 0 or not resultado.stdout:
                continue
            image = QImage()
            if image.loadFromData(resultado.stdout, "PNG"):
                return image
        return None


class ExplorerMode(str, Enum):
    """Operações suportadas pelo mesmo Explorer."""

    OPEN_FILE = "open_file"
    OPEN_FILES = "open_files"
    SELECT_FOLDER = "select_folder"
    SAVE_FILE = "save_file"
    MANAGE = "manage"


class _ExplorerProxyModel(QSortFilterProxyModel):
    """Aplica busca e filtros de extensão sem esconder pastas navegáveis."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._patterns: tuple[str, ...] = ("*",)
        self._directories_only = False
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setFilterKeyColumn(0)
        self.setRecursiveFilteringEnabled(True)

    def set_patterns(self, patterns: Sequence[str]) -> None:
        self._patterns = tuple(patterns) or ("*",)
        self.invalidateFilter()

    def set_directories_only(self, enabled: bool) -> None:
        self._directories_only = enabled
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()
        source_index = model.index(source_row, 0, source_parent)
        if not source_index.isValid():
            return False
        if model.isDir(source_index):
            return super().filterAcceptsRow(source_row, source_parent)
        if self._directories_only:
            return False

        filename = model.fileName(source_index).casefold()
        if not any(fnmatch.fnmatchcase(filename, pattern.casefold()) for pattern in self._patterns):
            return False
        return super().filterAcceptsRow(source_row, source_parent)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
            and 0 <= section < len(EXPLORER_CABECALHOS)
        ):
            return EXPLORER_CABECALHOS[section]
        return super().headerData(section, orientation, role)


class Explorer(QDialog):
    """
    Janela de navegação local com modos de abrir, selecionar, salvar e gerenciar.

    ``name_filters`` aceita filtros no formato Qt, como
    ``("Projetos (*.json *.yaml)", "Todos os arquivos (*)")``.
    Em ``MANAGE``, a renomeação, o envio para a Lixeira e arrastar/soltar
    ficam disponíveis; a exclusão nunca é feita permanentemente pelo componente.
    """

    file_activated = Signal(str)

    def __init__(
        self,
        parent=None,
        *,
        mode: ExplorerMode | str = ExplorerMode.OPEN_FILE,
        start_path: str | None = None,
        name_filters: Sequence[str] | str | None = None,
        title: str | None = None,
        initial_name: str | None = None,
        remember_location: bool = True,
    ) -> None:
        super().__init__(parent)
        self._mode = mode if isinstance(mode, ExplorerMode) else ExplorerMode(mode)
        self._current_directory = QDir.homePath()
        self._history: list[str] = []
        self._history_index = -1
        self._selected_paths: tuple[str, ...] = ()
        self._manager_mode = self._mode == ExplorerMode.MANAGE
        self._filters = self._normalizar_filtros(name_filters)
        self._remember_location = bool(remember_location)
        self._explorer_state = (
            self._ler_estado_persistido() if self._remember_location else {}
        )
        caminhos_recentes = self._explorer_state.get("caminhos_recentes", [])
        if not isinstance(caminhos_recentes, list):
            caminhos_recentes = []
        self._recent_paths = [
            path
            for path in caminhos_recentes
            if isinstance(path, str) and os.path.isdir(path)
        ]
        self._sort_column = 0
        self._sort_order = Qt.SortOrder.AscendingOrder
        self._preview_request_id = 0
        self._preview_path: str | None = None
        self._preview_pending = False
        self._preview_cancel_event = threading.Event()
        self._preview_tasks = {}
        self._preview_hover_path: str | None = None

        self.setObjectName("explorerDialog")
        self.setWindowTitle(title or self._titulo_modo())
        self.setMinimumSize(EXPLORER_LARGURA_MIN, EXPLORER_ALTURA_MIN)
        self.resize(EXPLORER_LARGURA_PADRAO, EXPLORER_ALTURA_PADRAO)

        self._criar_modelos()
        self._montar_interface()
        if initial_name and self._modo_usa_nome():
            self._filename_input.setText(os.path.basename(initial_name))
        self._montar_acoes()
        self._popular_locais()

        destino = self._resolver_caminho_inicial(start_path)
        self._navegar_para(destino, registrar_historico=True, avisar=False)

    @staticmethod
    def _normalizar_filtros(
        name_filters: Sequence[str] | str | None,
    ) -> tuple[tuple[str, tuple[str, ...]], ...]:
        if name_filters is None:
            return tuple(EXPLORER_FILTROS)
        if isinstance(name_filters, str):
            itens = tuple(parte for parte in name_filters.split(";;") if parte.strip())
        else:
            itens = tuple(name_filters)
        resultado = []
        for item in itens:
            match = re.search(r"\(([^()]*)\)", item)
            patterns = tuple(match.group(1).split()) if match else ("*",)
            resultado.append((item, patterns or ("*",)))
        return tuple(resultado) or tuple(EXPLORER_FILTROS)

    def _titulo_modo(self) -> str:
        chaves = {
            ExplorerMode.OPEN_FILE: "title_open_file",
            ExplorerMode.OPEN_FILES: "title_open_files",
            ExplorerMode.SELECT_FOLDER: "title_select_folder",
            ExplorerMode.SAVE_FILE: "title_save_file",
            ExplorerMode.MANAGE: "title_manage",
        }
        return EXPLORER_TEXTOS[chaves[self._mode]]

    def _criar_modelos(self) -> None:
        self._source_model = QFileSystemModel(self)
        self._source_model.setReadOnly(not self._manager_mode)
        self._source_model.setFilter(
            QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot
        )
        self._proxy_model = _ExplorerProxyModel(self)
        self._proxy_model.setSourceModel(self._source_model)
        self._proxy_model.set_directories_only(
            self._mode == ExplorerMode.SELECT_FOLDER
        )

    def _montar_interface(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            EXPLORER_MARGEM,
            EXPLORER_MARGEM,
            EXPLORER_MARGEM,
            EXPLORER_MARGEM,
        )
        layout.setSpacing(EXPLORER_ESPACAMENTO)

        toolbar = QFrame(self)
        toolbar.setObjectName("explorerToolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(
            EXPLORER_ESPACAMENTO,
            EXPLORER_ESPACAMENTO,
            EXPLORER_ESPACAMENTO,
            EXPLORER_ESPACAMENTO,
        )
        toolbar_layout.setSpacing(EXPLORER_ESPACAMENTO)

        self._btn_back = self._botao_navegacao(ico_voltar(), "tooltip_back")
        self._btn_forward = self._botao_navegacao(ico_avancar(), "tooltip_forward")
        self._btn_up = self._botao_navegacao(ico_subir(), "tooltip_up")
        self._btn_home = self._botao_navegacao(ico_inicio(), "tooltip_home")
        self._btn_refresh = self._botao_navegacao(ico_atualizar(), "tooltip_refresh")
        toolbar_layout.addWidget(self._btn_back)
        toolbar_layout.addWidget(self._btn_forward)
        toolbar_layout.addWidget(self._btn_up)
        toolbar_layout.addWidget(self._btn_home)

        location_label = QLabel(EXPLORER_TEXTOS["location"], toolbar)
        toolbar_layout.addWidget(location_label)
        self._path_input = QComboBox(toolbar)
        self._path_input.setObjectName("explorerPathInput")
        self._path_input.setEditable(True)
        self._path_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._path_input.setMinimumContentsLength(24)
        self._path_input.lineEdit().setPlaceholderText(
            EXPLORER_TEXTOS["path_placeholder"]
        )
        for path in self._recent_paths:
            self._path_input.addItem(path)
        toolbar_layout.addWidget(self._path_input, 1)
        toolbar_layout.addWidget(self._btn_refresh)

        self._btn_organize = QToolButton(toolbar)
        self._btn_organize.setObjectName("explorerNavigationButton")
        self._btn_organize.setText(EXPLORER_TEXTOS["organize"])
        self._btn_organize.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )
        self._montar_menu_organizar()
        toolbar_layout.addWidget(self._btn_organize)

        self._search_input = QLineEdit(toolbar)
        self._search_input.setObjectName("explorerSearchInput")
        self._search_input.setPlaceholderText(EXPLORER_TEXTOS["search_placeholder"])
        self._search_input.addAction(
            ico_buscar(),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        self._search_input.setMaximumWidth(EXPLORER_LARGURA_LOCAIS * 2)
        toolbar_layout.addWidget(self._search_input)
        layout.addWidget(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setObjectName("explorerContentSplitter")
        self._places = QListWidget(splitter)
        self._places.setObjectName("explorerPlaces")
        self._places.setMinimumWidth(EXPLORER_LARGURA_LOCAIS)
        self._places.setMaximumWidth(EXPLORER_LARGURA_LOCAIS)

        self._file_view = QTreeView(splitter)
        self._file_view.setObjectName("explorerFileView")
        self._file_view.setModel(self._proxy_model)
        self._file_view.setMouseTracking(True)
        self._file_view.viewport().setMouseTracking(True)
        self._file_view.setRootIsDecorated(False)
        self._file_view.setItemsExpandable(False)
        self._file_view.setAlternatingRowColors(True)
        self._file_view.setSortingEnabled(True)
        self._file_view.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self._file_view.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        selection_mode = (
            QAbstractItemView.SelectionMode.ExtendedSelection
            if self._mode in (ExplorerMode.OPEN_FILES, ExplorerMode.MANAGE)
            else QAbstractItemView.SelectionMode.SingleSelection
        )
        self._file_view.setSelectionMode(selection_mode)
        self._file_view.setEditTriggers(
            QAbstractItemView.EditTrigger.EditKeyPressed
            if self._manager_mode
            else QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._file_view.setDragEnabled(self._manager_mode)
        self._file_view.setAcceptDrops(self._manager_mode)
        self._file_view.setDropIndicatorShown(self._manager_mode)
        if self._manager_mode:
            self._file_view.setDragDropMode(
                QAbstractItemView.DragDropMode.DragDrop
            )
            self._file_view.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._file_view.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self._configurar_colunas()
        splitter.addWidget(self._places)
        splitter.addWidget(self._file_view)
        self._preview_panel = self._montar_painel_previa(splitter)
        splitter.addWidget(self._preview_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setCollapsible(2, False)
        splitter.setSizes(
            (
                EXPLORER_LARGURA_LOCAIS,
                EXPLORER_LARGURA_PADRAO
                - EXPLORER_LARGURA_LOCAIS
                - EXPLORER_PREVIEW_TAMANHO
                - 40,
                EXPLORER_PREVIEW_TAMANHO + 40,
            )
        )
        layout.addWidget(splitter, 1)

        footer = QFrame(self)
        footer.setObjectName("explorerFooter")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(
            EXPLORER_ESPACAMENTO,
            EXPLORER_ESPACAMENTO,
            EXPLORER_ESPACAMENTO,
            EXPLORER_ESPACAMENTO,
        )
        footer_layout.setSpacing(EXPLORER_ESPACAMENTO)

        options_layout = QHBoxLayout()
        options_layout.setSpacing(EXPLORER_ESPACAMENTO)
        self._filename_label = QLabel(EXPLORER_TEXTOS["filename"], footer)
        self._filename_input = QLineEdit(footer)
        self._filename_input.setObjectName("explorerFilenameInput")
        self._filename_label.setVisible(self._modo_usa_nome())
        self._filename_input.setVisible(self._modo_usa_nome())
        if self._mode == ExplorerMode.OPEN_FILES:
            self._filename_input.setEnabled(False)
        options_layout.addWidget(self._filename_label)
        options_layout.addWidget(self._filename_input, 1)

        self._filter_label = QLabel(EXPLORER_TEXTOS["file_type"], footer)
        self._filter_combo = QComboBox(footer)
        self._filter_combo.setObjectName("explorerFilterCombo")
        for label, patterns in self._filters:
            self._filter_combo.addItem(label, patterns)
        self._filter_label.setVisible(self._mode != ExplorerMode.SELECT_FOLDER)
        self._filter_combo.setVisible(self._mode != ExplorerMode.SELECT_FOLDER)
        options_layout.addWidget(self._filter_label)
        options_layout.addWidget(self._filter_combo)

        self._show_hidden = QCheckBox(EXPLORER_TEXTOS["show_hidden"], footer)
        self._show_hidden.setVisible(self._manager_mode)
        options_layout.addWidget(self._show_hidden)
        footer_layout.addLayout(options_layout)

        actions_layout = QHBoxLayout()
        self._status_label = QLabel(EXPLORER_TEXTOS["ready"], footer)
        self._status_label.setObjectName("explorerStatusLabel")
        actions_layout.addWidget(self._status_label, 1)

        self._primary_button = QPushButton(self._texto_botao_primario(), footer)
        self._primary_button.setObjectName("explorerPrimaryButton")
        self._cancel_button = QPushButton(
            EXPLORER_TEXTOS["close"]
            if self._manager_mode
            else EXPLORER_TEXTOS["cancel"],
            footer,
        )
        self._cancel_button.setObjectName("explorerCancelButton")
        actions_layout.addWidget(self._primary_button)
        actions_layout.addWidget(self._cancel_button)
        footer_layout.addLayout(actions_layout)
        layout.addWidget(footer)

        self._conectar_sinais()

    def _montar_painel_previa(self, parent) -> QFrame:
        panel = QFrame(parent)
        panel.setObjectName("explorerPreviewPanel")
        panel.setMinimumWidth(EXPLORER_PREVIEW_TAMANHO + 24)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(
            EXPLORER_ESPACAMENTO,
            EXPLORER_ESPACAMENTO,
            EXPLORER_ESPACAMENTO,
            EXPLORER_ESPACAMENTO,
        )
        layout.setSpacing(EXPLORER_ESPACAMENTO)

        title = QLabel(EXPLORER_TEXTOS["preview_title"], panel)
        title.setObjectName("explorerPreviewTitle")
        self._preview_image = QLabel(
            EXPLORER_TEXTOS["preview_image_placeholder"],
            panel,
        )
        self._preview_image.setObjectName("explorerPreviewImage")
        self._preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_image.setMinimumSize(
            QSize(EXPLORER_PREVIEW_TAMANHO, EXPLORER_PREVIEW_ALTURA)
        )
        self._preview_image.setMaximumHeight(EXPLORER_PREVIEW_ALTURA + 24)
        self._preview_image.setWordWrap(True)

        self._preview_details = QLabel(EXPLORER_TEXTOS["preview_empty"], panel)
        self._preview_details.setObjectName("explorerPreviewDetails")
        self._preview_details.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self._preview_details.setWordWrap(True)
        self._preview_details.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        layout.addWidget(title)
        layout.addWidget(self._preview_image)
        layout.addWidget(self._preview_details, 1)
        return panel

    def _botao_navegacao(self, icon, texto_key: str) -> QToolButton:
        button = QToolButton(self)
        button.setObjectName("explorerNavigationButton")
        button.setIcon(icon)
        button.setIconSize(
            __import__("PySide6.QtCore", fromlist=["QSize"]).QSize(
                EXPLORER_TAMANHO_ICONE,
                EXPLORER_TAMANHO_ICONE,
            )
        )
        button.setToolTip(EXPLORER_TEXTOS[texto_key])
        button.setAutoRaise(True)
        return button

    def _configurar_colunas(self) -> None:
        header = self._file_view.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._file_view.setColumnWidth(1, EXPLORER_LARGURA_COLUNA_TAMANHO)
        self._file_view.setColumnWidth(2, EXPLORER_LARGURA_COLUNA_TIPO)
        self._file_view.setColumnWidth(3, EXPLORER_LARGURA_COLUNA_DATA)

    def _conectar_sinais(self) -> None:
        self._btn_back.clicked.connect(self._voltar)
        self._btn_forward.clicked.connect(self._avancar)
        self._btn_up.clicked.connect(self._subir)
        self._btn_home.clicked.connect(self._ir_para_inicio)
        self._btn_refresh.clicked.connect(self._atualizar)
        self._path_input.lineEdit().returnPressed.connect(
            self._navegar_pelo_campo
        )
        self._path_input.activated.connect(self._navegar_pelo_campo)
        self._file_view.header().sortIndicatorChanged.connect(
            self._indicador_ordenacao_alterado
        )
        self._search_input.textChanged.connect(
            self._proxy_model.setFilterFixedString
        )
        self._places.itemClicked.connect(self._abrir_local)
        self._file_view.clicked.connect(self._item_clicado)
        self._file_view.doubleClicked.connect(self._item_ativado)
        self._file_view.customContextMenuRequested.connect(
            self._mostrar_menu_contextual
        )
        self._file_view.entered.connect(self._previsualizar_hover)
        self._file_view.selectionModel().selectionChanged.connect(
            self._previsualizar_selecao
        )
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(EXPLORER_PREVIEW_DEBOUNCE_MS)
        self._preview_timer.timeout.connect(self._previsualizar_hover_pendente)
        self.finished.connect(self._cancelar_previsualizacao)
        self._filter_combo.currentIndexChanged.connect(self._filtro_alterado)
        self._show_hidden.toggled.connect(self._itens_ocultos_alterados)
        self._primary_button.clicked.connect(self._aceitar_selecao)
        self._cancel_button.clicked.connect(self.reject)
        self._source_model.directoryLoaded.connect(self._atualizar_status)

    def _previsualizar_hover(self, proxy_index: QModelIndex) -> None:
        if not proxy_index.isValid():
            return
        source_index = self._proxy_model.mapToSource(proxy_index)
        path = self._source_model.filePath(source_index)
        if path and path != self._preview_path:
            self._preview_hover_path = path
            self._preview_timer.start()

    def _previsualizar_hover_pendente(self) -> None:
        if self._preview_hover_path:
            self._solicitar_previa(self._preview_hover_path)

    def _previsualizar_selecao(self, *_args) -> None:
        indexes = self._file_view.selectionModel().selectedRows(0)
        if len(indexes) > 1:
            self._limpar_previa()
            self._preview_details.setText(
                EXPLORER_TEXTOS["preview_selected_count"].format(
                    count=len(indexes)
                )
            )
            return
        if not indexes:
            self._limpar_previa()
            return
        source_index = self._proxy_model.mapToSource(indexes[0])
        path = self._source_model.filePath(source_index)
        if path:
            self._solicitar_previa(path)

    def _solicitar_previa(self, path: str) -> None:
        caminho = os.path.abspath(path)
        if caminho == self._preview_path:
            return
        self._preview_timer.stop()
        self._preview_cancel_event.set()
        self._preview_request_id += 1
        request_id = self._preview_request_id
        self._preview_path = caminho
        self._preview_pending = True
        self._preview_cancel_event = threading.Event()
        self._preview_image.clear()
        self._preview_image.setText(EXPLORER_TEXTOS["preview_loading"])
        self._preview_details.setText(EXPLORER_TEXTOS["preview_loading"])

        task = _ExplorerPreviewTask(
            request_id,
            caminho,
            self._preview_cancel_event,
        )
        task.signals.completed.connect(self._previsualizacao_concluida)
        self._preview_tasks[request_id] = task
        QThreadPool.globalInstance().start(task)

    def _previsualizacao_concluida(
        self,
        request_id: int,
        path: str,
        result: dict,
    ) -> None:
        self._preview_tasks.pop(request_id, None)
        if (
            request_id != self._preview_request_id
            or path != self._preview_path
            or result.get("kind") == "cancelled"
        ):
            return
        self._preview_pending = False

        kind = result.get("kind")
        if kind == "folder":
            self._mostrar_icone_previa(path)
            details = EXPLORER_TEXTOS["preview_folder_details"].format(
                name=result.get("name", os.path.basename(path)),
                size=self._formatar_tamanho_previa(result.get("size", 0)),
                files=result.get("files", 0),
                folders=result.get("folders", 0),
                modified=self._formatar_data_previa(result.get("modified")),
                path=path,
            )
            if result.get("partial"):
                details += "\n\n" + EXPLORER_TEXTOS["preview_partial"]
            self._preview_details.setText(details)
            return

        if kind == "link":
            self._mostrar_icone_previa(path)
            self._preview_details.setText(
                f'{os.path.basename(path)}\n{EXPLORER_TEXTOS["preview_link"]}\n{path}'
            )
            return

        if kind == "error":
            self._preview_image.setText(EXPLORER_TEXTOS["preview_unavailable"])
            self._preview_details.setText(EXPLORER_TEXTOS["preview_unavailable"])
            return

        if kind in {"image", "video"}:
            image = result.get("image")
            if image is not None and not image.isNull():
                pixmap = QPixmap.fromImage(image).scaled(
                    self._preview_image.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._preview_image.setText("")
                self._preview_image.setPixmap(pixmap)
            else:
                issue = result.get("issue")
                message_key = (
                    "preview_image_too_large"
                    if issue == "too_large"
                    else "preview_image_unreadable"
                    if kind == "image"
                    else "preview_video_unavailable"
                )
                self._preview_image.setText(EXPLORER_TEXTOS[message_key])
            self._mostrar_detalhes_arquivo(path, result, kind)
            return

        self._mostrar_icone_previa(path)
        self._mostrar_detalhes_arquivo(path, result, "file")
        self._preview_image.setText(EXPLORER_TEXTOS["preview_unavailable"])

    def _mostrar_detalhes_arquivo(self, path: str, result: dict, kind: str) -> None:
        kind_key = {
            "image": "preview_kind_image",
            "video": "preview_kind_video",
            "file": "preview_kind_file",
        }.get(kind, "preview_kind_unknown")
        extension = os.path.splitext(path)[1].lstrip(".").upper()
        self._preview_details.setText(
            EXPLORER_TEXTOS["preview_file_details"].format(
                name=result.get("name", os.path.basename(path)),
                kind=EXPLORER_TEXTOS[kind_key],
                file_type=extension or EXPLORER_TEXTOS["preview_kind_unknown"],
                size=self._formatar_tamanho_previa(result.get("size", 0)),
                modified=self._formatar_data_previa(result.get("modified")),
                path=path,
            )
        )

    def _mostrar_icone_previa(self, path: str) -> None:
        index = self._source_model.index(path)
        icon = self._source_model.fileIcon(index)
        self._preview_image.setText("")
        self._preview_image.setPixmap(
            icon.pixmap(QSize(72, 72))
        )

    @staticmethod
    def _formatar_tamanho_previa(size: int) -> str:
        valor = float(max(0, size))
        for unidade in ("B", "KiB", "MiB", "GiB", "TiB"):
            if valor < 1024 or unidade == "TiB":
                return f"{valor:.1f} {unidade}" if unidade != "B" else f"{int(valor)} B"
            valor /= 1024
        return f"{valor:.1f} TiB"

    @staticmethod
    def _formatar_data_previa(timestamp) -> str:
        try:
            return time.strftime("%d/%m/%Y %H:%M", time.localtime(timestamp))
        except (TypeError, ValueError, OverflowError):
            return EXPLORER_TEXTOS["preview_kind_unknown"]

    def _limpar_previa(self) -> None:
        self._preview_timer.stop()
        self._preview_cancel_event.set()
        self._preview_request_id += 1
        self._preview_path = None
        self._preview_pending = False
        self._preview_hover_path = None
        self._preview_image.clear()
        self._preview_image.setText(EXPLORER_TEXTOS["preview_image_placeholder"])
        self._preview_details.setText(EXPLORER_TEXTOS["preview_empty"])

    def _cancelar_previsualizacao(self, *_args) -> None:
        self._preview_timer.stop()
        self._preview_cancel_event.set()
        self._preview_request_id += 1

    def _montar_acoes(self) -> None:
        self._action_open = QAction(ico_abrir(), EXPLORER_TEXTOS["open"], self)
        self._action_copy_path = QAction(
            ico_copiar(), EXPLORER_TEXTOS["copy_path"], self
        )
        self._action_new_folder = QAction(
            ico_nova_pasta(), EXPLORER_TEXTOS["new_folder"], self
        )
        self._action_rename = QAction(
            ico_renomear(), EXPLORER_TEXTOS["rename"], self
        )
        self._action_trash = QAction(
            ico_lixo(), EXPLORER_TEXTOS["move_to_trash"], self
        )
        self._action_open.triggered.connect(self._abrir_item_atual)
        self._action_copy_path.triggered.connect(self._copiar_caminho)
        self._action_new_folder.triggered.connect(self._criar_pasta)
        self._action_rename.triggered.connect(self._renomear_item)
        self._action_trash.triggered.connect(self._mover_para_lixeira)

        self._btn_back.clicked.connect(self._atualizar_botoes_navegacao)
        self._btn_forward.clicked.connect(self._atualizar_botoes_navegacao)

    def _montar_menu_organizar(self) -> None:
        menu = QMenu(self._btn_organize)
        colunas = (
            (0, "sort_name"),
            (1, "sort_size"),
            (2, "sort_type"),
            (3, "sort_modified"),
        )
        for coluna, chave in colunas:
            action = QAction(EXPLORER_TEXTOS[chave], menu)
            action.triggered.connect(
                lambda _checked=False, coluna=coluna: self._ordenar_por(coluna)
            )
            menu.addAction(action)

        menu.addSeparator()
        self._action_sort_descending = QAction(
            EXPLORER_TEXTOS["sort_descending"], menu
        )
        self._action_sort_descending.setCheckable(True)
        self._action_sort_descending.toggled.connect(
            self._ordem_decrescente_alterada
        )
        menu.addAction(self._action_sort_descending)
        self._btn_organize.setMenu(menu)

    def _popular_locais(self) -> None:
        texto = EXPLORER_TEXTOS
        locais = [
            (texto["place_home"], QDir.homePath()),
            (
                texto["place_desktop"],
                QStandardPaths.writableLocation(
                    QStandardPaths.StandardLocation.DesktopLocation
                ),
            ),
            (
                texto["place_documents"],
                QStandardPaths.writableLocation(
                    QStandardPaths.StandardLocation.DocumentsLocation
                ),
            ),
            (
                texto["place_downloads"],
                QStandardPaths.writableLocation(
                    QStandardPaths.StandardLocation.DownloadLocation
                ),
            ),
            (
                texto["place_pictures"],
                QStandardPaths.writableLocation(
                    QStandardPaths.StandardLocation.PicturesLocation
                ),
            ),
            (
                texto["place_music"],
                QStandardPaths.writableLocation(
                    QStandardPaths.StandardLocation.MusicLocation
                ),
            ),
            (
                texto["place_videos"],
                QStandardPaths.writableLocation(
                    QStandardPaths.StandardLocation.MoviesLocation
                ),
            ),
            (texto["place_computer"], QDir.rootPath()),
        ]
        vistos = set()
        for label, path in locais:
            if label == texto["place_computer"] and self._places.count():
                self._adicionar_separador_locais()
            if not path or not os.path.isdir(path):
                continue
            normalizado = os.path.normcase(os.path.abspath(path))
            if normalizado in vistos:
                continue
            vistos.add(normalizado)
            self._adicionar_local(label, path)

        for drive in QDir.drives():
            path = drive.absoluteFilePath()
            normalizado = os.path.normcase(os.path.abspath(path))
            if normalizado not in vistos:
                vistos.add(normalizado)
                self._adicionar_local(path, path)

    def _adicionar_separador_locais(self) -> None:
        item = QListWidgetItem()
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        item.setSizeHint(QSize(1, 10))
        self._places.addItem(item)
        separator = QFrame(self._places)
        separator.setObjectName("explorerPlacesSeparator")
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Plain)
        separator.setFixedHeight(1)
        self._places.setItemWidget(item, separator)

    def _adicionar_local(self, label: str, path: str) -> None:
        item = QListWidgetItem(
            self._source_model.fileIcon(self._source_model.index(path)),
            label,
        )
        item.setData(Qt.ItemDataRole.UserRole, path)
        self._places.addItem(item)

    def _resolver_caminho_inicial(self, start_path: str | None) -> str:
        if start_path:
            caminho = os.path.abspath(
                os.path.expanduser(os.path.expandvars(start_path))
            )
            if os.path.isfile(caminho):
                return os.path.dirname(caminho)
            if os.path.isdir(caminho):
                return caminho

        ultimo_caminho = self._explorer_state.get("ultimo_diretorio", "")
        if isinstance(ultimo_caminho, str) and os.path.isdir(ultimo_caminho):
            return ultimo_caminho
        return QDir.homePath()

    def _navegar_para(
        self,
        path: str,
        *,
        registrar_historico: bool = True,
        avisar: bool = True,
    ) -> bool:
        caminho = os.path.abspath(os.path.expanduser(os.path.expandvars(path)))
        if not os.path.isdir(caminho):
            if avisar:
                popup_aviso(
                    EXPLORER_TEXTOS["error_title"],
                    EXPLORER_TEXTOS["invalid_location"],
                    self,
                )
            return False

        self._limpar_previa()
        if registrar_historico:
            if self._history_index < 0 or self._history[self._history_index] != caminho:
                self._history = self._history[: self._history_index + 1]
                self._history.append(caminho)
                self._history_index = len(self._history) - 1

        self._current_directory = caminho
        self._path_input.setEditText(caminho)
        source_root = self._source_model.setRootPath(caminho)
        if not source_root.isValid():
            source_root = self._source_model.index(caminho)
        self._file_view.setRootIndex(self._proxy_model.mapFromSource(source_root))
        self._atualizar_botoes_navegacao()
        self._atualizar_status()
        self._registrar_caminho_recente(caminho)
        return True

    def _navegar_pelo_campo(self, *_args) -> None:
        caminho = self._path_input.currentText().strip()
        if os.path.isfile(caminho):
            caminho = os.path.dirname(caminho)
        self._navegar_para(caminho)

    def _voltar(self, _checked: bool = False) -> None:
        if self._history_index > 0:
            self._history_index -= 1
            self._navegar_para(
                self._history[self._history_index],
                registrar_historico=False,
            )

    def _avancar(self, _checked: bool = False) -> None:
        if self._history_index + 1 < len(self._history):
            self._history_index += 1
            self._navegar_para(
                self._history[self._history_index],
                registrar_historico=False,
            )

    def _subir(self, _checked: bool = False) -> None:
        parent = os.path.dirname(self._current_directory)
        if parent and parent != self._current_directory:
            self._navegar_para(parent)

    def _ir_para_inicio(self, _checked: bool = False) -> None:
        self._navegar_para(QDir.homePath())

    def _atualizar(self, _checked: bool = False) -> None:
        self._navegar_para(
            self._current_directory,
            registrar_historico=False,
        )

    def _abrir_local(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self._navegar_para(path)

    def _item_clicado(self, proxy_index: QModelIndex) -> None:
        source_index = self._proxy_model.mapToSource(proxy_index)
        path = self._source_model.filePath(source_index)
        if self._mode == ExplorerMode.SAVE_FILE and os.path.isfile(path):
            self._filename_input.setText(os.path.basename(path))
        elif self._modo_usa_nome() and os.path.isfile(path):
            self._filename_input.setText(os.path.basename(path))
        self._atualizar_status()

    def _item_ativado(self, proxy_index: QModelIndex) -> None:
        source_index = self._proxy_model.mapToSource(proxy_index)
        path = self._source_model.filePath(source_index)
        if os.path.isdir(path):
            self._navegar_para(path)
            return
        if not os.path.isfile(path):
            return
        if self._mode == ExplorerMode.MANAGE:
            self.file_activated.emit(path)
        elif self._mode in (ExplorerMode.OPEN_FILE, ExplorerMode.OPEN_FILES):
            self._selected_paths = (path,)
            self.accept()
        elif self._mode == ExplorerMode.SAVE_FILE:
            self._filename_input.setText(os.path.basename(path))

    def _filtro_alterado(self, index: int) -> None:
        patterns = self._filter_combo.itemData(index) or ("*",)
        self._proxy_model.set_patterns(patterns)
        self._atualizar_status()

    def _ordenar_por(self, coluna: int) -> None:
        self._sort_column = coluna
        self._file_view.sortByColumn(coluna, self._sort_order)

    def _ordem_decrescente_alterada(self, decrescente: bool) -> None:
        self._sort_order = (
            Qt.SortOrder.DescendingOrder
            if decrescente
            else Qt.SortOrder.AscendingOrder
        )
        self._file_view.sortByColumn(self._sort_column, self._sort_order)

    def _indicador_ordenacao_alterado(self, coluna: int, ordem) -> None:
        self._sort_column = coluna
        self._sort_order = ordem
        action = self._action_sort_descending
        sinais_anteriores = action.blockSignals(True)
        action.setChecked(ordem == Qt.SortOrder.DescendingOrder)
        action.blockSignals(sinais_anteriores)

    def _itens_ocultos_alterados(self, mostrar: bool) -> None:
        filtros = QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot
        if mostrar:
            filtros |= QDir.Filter.Hidden | QDir.Filter.System
        self._source_model.setFilter(filtros)
        self._atualizar()

    def _mostrar_menu_contextual(self, posicao) -> None:
        index = self._file_view.indexAt(posicao)
        if index.isValid() and not self._file_view.selectionModel().isSelected(index):
            self._file_view.setCurrentIndex(index)
            self._file_view.selectRow(index.row())

        menu = QMenu(self)
        tem_selecao = self._file_view.currentIndex().isValid()
        if tem_selecao:
            menu.addAction(self._action_open)
            menu.addAction(self._action_copy_path)
            if self._manager_mode:
                menu.addSeparator()
                menu.addAction(self._action_rename)
                menu.addAction(self._action_trash)
            menu.addSeparator()
        menu.addAction(self._action_new_folder)
        menu.exec(self._file_view.viewport().mapToGlobal(posicao))

    def _caminho_item_atual(self) -> str | None:
        index = self._file_view.currentIndex()
        if not index.isValid():
            return None
        source_index = self._proxy_model.mapToSource(index)
        return self._source_model.filePath(source_index)

    def _abrir_item_atual(self, _checked: bool = False) -> None:
        path = self._caminho_item_atual()
        if not path:
            return
        if os.path.isdir(path):
            self._navegar_para(path)
        elif self._manager_mode:
            self.file_activated.emit(path)
        else:
            self._aceitar_selecao()

    def _copiar_caminho(self, _checked: bool = False) -> None:
        path = self._caminho_item_atual()
        if path:
            QApplication.clipboard().setText(path)
            self._status_label.setText(path)

    def _criar_pasta(self, _checked: bool = False) -> None:
        nome, aceito = QInputDialog.getText(
            self,
            EXPLORER_TEXTOS["new_folder_title"],
            EXPLORER_TEXTOS["new_folder_prompt"],
        )
        nome = nome.strip()
        if not aceito or not nome:
            return
        if (
            nome in (".", "..")
            or os.path.basename(nome) != nome
            or "/" in nome
            or "\\" in nome
        ):
            popup_aviso(
                EXPLORER_TEXTOS["error_title"],
                EXPLORER_TEXTOS["invalid_name"],
                self,
            )
            return
        try:
            os.mkdir(os.path.join(self._current_directory, nome))
            self._atualizar()
        except OSError as erro:
            popup_erro(
                EXPLORER_TEXTOS["error_title"],
                f'{EXPLORER_TEXTOS["new_folder_error"]}\n{erro}',
                self,
            )

    def _renomear_item(self, _checked: bool = False) -> None:
        if not self._manager_mode:
            return
        origem = self._caminho_item_atual()
        if not origem:
            return
        nome_atual = os.path.basename(origem.rstrip(os.sep))
        nome, aceito = QInputDialog.getText(
            self,
            EXPLORER_TEXTOS["rename_title"],
            EXPLORER_TEXTOS["rename_prompt"],
            QLineEdit.EchoMode.Normal,
            nome_atual,
        )
        nome = nome.strip()
        if not aceito or not nome or nome == nome_atual:
            return
        if (
            nome in (".", "..")
            or os.path.basename(nome) != nome
            or "/" in nome
            or "\\" in nome
        ):
            popup_aviso(
                EXPLORER_TEXTOS["error_title"],
                EXPLORER_TEXTOS["invalid_name"],
                self,
            )
            return
        destino = os.path.join(os.path.dirname(origem), nome)
        if os.path.exists(destino):
            popup_aviso(
                EXPLORER_TEXTOS["error_title"],
                EXPLORER_TEXTOS["rename_error"],
                self,
            )
            return
        try:
            os.rename(origem, destino)
            self._atualizar()
        except OSError as erro:
            popup_erro(
                EXPLORER_TEXTOS["error_title"],
                f'{EXPLORER_TEXTOS["rename_error"]}\n{erro}',
                self,
            )

    def _mover_para_lixeira(self, _checked: bool = False) -> None:
        if not self._manager_mode:
            return
        path = self._caminho_item_atual()
        if not path:
            return
        if not popup_confirmar_perigo(
            EXPLORER_TEXTOS["trash_confirm_title"],
            EXPLORER_TEXTOS["trash_confirm_message"],
            self,
        ):
            return
        if not QFile.moveToTrash(path):
            popup_erro(
                EXPLORER_TEXTOS["error_title"],
                EXPLORER_TEXTOS["trash_error"],
                self,
            )
            return
        self._atualizar()

    def _aceitar_selecao(self, _checked: bool = False) -> None:
        if self._mode in (ExplorerMode.SELECT_FOLDER, ExplorerMode.MANAGE):
            selecionados = self._caminhos_selecionados()
            pasta = next((path for path in selecionados if os.path.isdir(path)), None)
            self._selected_paths = (pasta or self._current_directory,)
            self.accept()
            return

        if self._mode == ExplorerMode.SAVE_FILE:
            nome = self._filename_input.text().strip()
            if not nome:
                popup_aviso(
                    EXPLORER_TEXTOS["error_title"],
                    EXPLORER_TEXTOS["empty_filename"],
                    self,
                )
                return
            if os.path.basename(nome) != nome or "/" in nome or "\\" in nome:
                popup_aviso(
                    EXPLORER_TEXTOS["error_title"],
                    EXPLORER_TEXTOS["invalid_name"],
                    self,
                )
                return
            destino = os.path.abspath(os.path.join(self._current_directory, nome))
            if os.path.isdir(destino):
                popup_aviso(
                    EXPLORER_TEXTOS["error_title"],
                    EXPLORER_TEXTOS["save_folder_error"],
                    self,
                )
                return
            if os.path.exists(destino) and not popup_confirmar(
                EXPLORER_TEXTOS["overwrite_title"],
                EXPLORER_TEXTOS["overwrite_message"],
                self,
            ):
                return
            self._selected_paths = (destino,)
            self.accept()
            return

        selecionados = [
            path for path in self._caminhos_selecionados() if os.path.isfile(path)
        ]
        if not selecionados and self._mode == ExplorerMode.OPEN_FILE:
            nome = self._filename_input.text().strip()
            candidato = nome if os.path.isabs(nome) else os.path.join(
                self._current_directory, nome
            )
            if nome and os.path.isfile(candidato):
                selecionados = [os.path.abspath(candidato)]
        if not selecionados:
            popup_aviso(
                EXPLORER_TEXTOS["error_title"],
                EXPLORER_TEXTOS["file_required"],
                self,
            )
            return
        if self._mode == ExplorerMode.OPEN_FILE:
            selecionados = selecionados[:1]
        self._selected_paths = tuple(selecionados)
        self.accept()

    def _caminhos_selecionados(self) -> list[str]:
        paths = []
        for index in self._file_view.selectionModel().selectedRows(0):
            source_index = self._proxy_model.mapToSource(index)
            path = self._source_model.filePath(source_index)
            if path:
                paths.append(path)
        return paths

    def _modo_usa_nome(self) -> bool:
        return self._mode in (
            ExplorerMode.OPEN_FILE,
            ExplorerMode.OPEN_FILES,
            ExplorerMode.SAVE_FILE,
        )

    def _texto_botao_primario(self) -> str:
        if self._mode == ExplorerMode.SELECT_FOLDER:
            return EXPLORER_TEXTOS["select_folder"]
        if self._mode == ExplorerMode.SAVE_FILE:
            return EXPLORER_TEXTOS["save"]
        if self._mode == ExplorerMode.MANAGE:
            return EXPLORER_TEXTOS["select_folder"]
        return EXPLORER_TEXTOS["open"]

    def _atualizar_botoes_navegacao(self, _checked: bool = False) -> None:
        self._btn_back.setEnabled(self._history_index > 0)
        self._btn_forward.setEnabled(self._history_index + 1 < len(self._history))
        self._btn_up.setEnabled(os.path.dirname(self._current_directory) != self._current_directory)

    def _atualizar_status(self, *_args) -> None:
        selecionados = len(self._caminhos_selecionados())
        if selecionados:
            texto = EXPLORER_TEXTOS["items_selected"].format(count=selecionados)
        else:
            count = self._proxy_model.rowCount(self._file_view.rootIndex())
            texto = EXPLORER_TEXTOS["items_count"].format(count=count)
        self._status_label.setText(texto)

    @staticmethod
    def _ler_estado_persistido() -> dict:
        """Lê o estado do Explorer pelo serviço central de AppData."""
        try:
            from _APPDATA_ import appdata

            appdata.inicializar()
            config = appdata.ler_config()
            estado = config.get("explorer", {})
            return estado if isinstance(estado, dict) else {}
        except Exception as erro:
            from _LOGS_ import log

            log.aviso(
                "Explorer",
                "_ler_estado_persistido",
                f"não foi possível ler as preferências: {erro}",
            )
            return {}

    def _registrar_caminho_recente(self, caminho: str) -> None:
        recentes = [caminho]
        recentes.extend(path for path in self._recent_paths if path != caminho)
        self._recent_paths = recentes[:20]

        self._path_input.clear()
        self._path_input.addItems(self._recent_paths)
        self._path_input.setEditText(caminho)

        if not self._remember_location:
            return

        estado = {
            "ultimo_diretorio": caminho,
            "caminhos_recentes": self._recent_paths,
        }
        if estado == self._explorer_state:
            return

        try:
            from _APPDATA_ import appdata

            config = appdata.ler_config()
            config["explorer"] = estado
            appdata.salvar_config(config)
            self._explorer_state = estado
        except Exception as erro:
            from _LOGS_ import log

            log.aviso(
                "Explorer",
                "_registrar_caminho_recente",
                f"não foi possível salvar a pasta atual: {erro}",
            )

    def selected_paths(self) -> tuple[str, ...]:
        """Retorna os caminhos aceitos; fica vazio quando o diálogo é cancelado."""
        return self._selected_paths

    @classmethod
    def get_open_file_name(
        cls,
        parent=None,
        caption: str | None = None,
        directory: str | None = None,
        name_filters: Sequence[str] | str | None = None,
        initial_name: str | None = None,
        remember_location: bool = True,
    ) -> str:
        dialog = cls(
            parent,
            mode=ExplorerMode.OPEN_FILE,
            start_path=directory,
            name_filters=name_filters,
            title=caption,
            initial_name=initial_name,
            remember_location=remember_location,
        )
        return (
            dialog.selected_paths()[0]
            if dialog.exec() == QDialog.DialogCode.Accepted
            and dialog.selected_paths()
            else ""
        )

    @classmethod
    def get_open_file_names(
        cls,
        parent=None,
        caption: str | None = None,
        directory: str | None = None,
        name_filters: Sequence[str] | str | None = None,
        remember_location: bool = True,
    ) -> list[str]:
        dialog = cls(
            parent,
            mode=ExplorerMode.OPEN_FILES,
            start_path=directory,
            name_filters=name_filters,
            title=caption,
            remember_location=remember_location,
        )
        return (
            list(dialog.selected_paths())
            if dialog.exec() == QDialog.DialogCode.Accepted
            else []
        )

    @classmethod
    def get_existing_directory(
        cls,
        parent=None,
        caption: str | None = None,
        directory: str | None = None,
        remember_location: bool = True,
    ) -> str:
        dialog = cls(
            parent,
            mode=ExplorerMode.SELECT_FOLDER,
            start_path=directory,
            title=caption,
            remember_location=remember_location,
        )
        return (
            dialog.selected_paths()[0]
            if dialog.exec() == QDialog.DialogCode.Accepted
            and dialog.selected_paths()
            else ""
        )

    @classmethod
    def get_save_file_name(
        cls,
        parent=None,
        caption: str | None = None,
        directory: str | None = None,
        name_filters: Sequence[str] | str | None = None,
        initial_name: str | None = None,
        remember_location: bool = True,
    ) -> str:
        dialog = cls(
            parent,
            mode=ExplorerMode.SAVE_FILE,
            start_path=directory,
            name_filters=name_filters,
            title=caption,
            initial_name=initial_name,
            remember_location=remember_location,
        )
        return (
            dialog.selected_paths()[0]
            if dialog.exec() == QDialog.DialogCode.Accepted
            and dialog.selected_paths()
            else ""
        )
