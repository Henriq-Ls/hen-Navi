"""Aba nativa de leitura local do Explorador."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath

from PySide6.QtCore import QSignalBlocker, QThreadPool, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QStyle,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from _SERVICOS_.explorer_filesystem import (
    ExplorerEntry,
    ExplorerError,
    ExplorerLimits,
    ExplorerSelection,
    ExplorerScanResult,
    ExplorerTreeResult,
    canonical_root,
)
from _SERVICOS_.explorer_settings import (
    ExplorerSettingsError,
    ExplorerSettingsStore,
    validate_ignored_names,
)
from _THREADS_.explorer_worker import ExplorerTask
from _ULTILIDADES_.explorer import Explorer
from _APP_.file_preview import FilePreviewTab


class ExplorerTab(QWidget):
    """Árvore local expansível, seleção recursiva e documento de estrutura."""

    file_open_requested = Signal(str, str)

    def __init__(
        self,
        settings_store: ExplorerSettingsStore,
        default_ignored_names,
        limits: ExplorerLimits,
        texts: dict[str, str],
        parent=None,
        *,
        inspection_mode: bool = False,
        fixed_root: str | None = None,
    ):
        super().__init__(parent)
        self.settings_store = settings_store
        self.default_ignored_names = tuple(default_ignored_names)
        self.limits = limits
        self.texts = texts
        self.inspection_mode = bool(inspection_mode)
        self.fixed_root = str(fixed_root) if fixed_root is not None else None
        if self.inspection_mode and self.fixed_root is None:
            raise ValueError("inspection_mode requires fixed_root")
        self.root_path: str | None = None
        self.selection = ExplorerSelection(
            include_all=not self.inspection_mode
        )
        self.ignored_names: tuple[str, ...] = self.default_ignored_names
        self._tasks: dict[int, ExplorerTask] = {}
        self._scan_contexts: dict[
            int,
            tuple[QTreeWidgetItem, str, int],
        ] = {}
        self._latest_tree_id: int | None = None
        self._next_request_id = 1
        self._root_generation = 0
        self._closed = False
        self._tree_root_item: QTreeWidgetItem | None = None
        self._tree_document_started = False
        self._tree_refresh_timer = QTimer(self)
        self._tree_refresh_timer.setSingleShot(True)
        self._tree_refresh_timer.setInterval(180)
        self._tree_refresh_timer.timeout.connect(self._generate_tree)

        self._load_ignored_settings()
        self._build_ui()
        self._render_ignored_names()
        if self.fixed_root is not None:
            self.set_root(self.fixed_root)

    def _load_ignored_settings(self):
        try:
            self.ignored_names = self.settings_store.load_ignored_names()
        except ExplorerSettingsError:
            self.ignored_names = self.default_ignored_names
            self._settings_warning = True
        else:
            self._settings_warning = False

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.path_controls = QWidget(self)
        path_row = QHBoxLayout(self.path_controls)
        path_row.setContentsMargins(0, 0, 0, 0)
        path_row.addWidget(QLabel(self.texts["explorer_path_label"]))
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText(
            self.texts["explorer_path_placeholder"]
        )
        self.path_input.returnPressed.connect(self._apply_typed_root)
        path_row.addWidget(self.path_input, 1)
        self.open_root_button = QPushButton(self.texts["explorer_open_root"])
        self.open_root_button.clicked.connect(self._apply_typed_root)
        path_row.addWidget(self.open_root_button)
        self.browse_button = QPushButton(self.texts["explorer_browse"])
        self.browse_button.clicked.connect(self._browse_for_root)
        path_row.addWidget(self.browse_button)
        layout.addWidget(self.path_controls)

        self.ignore_section_button = QToolButton()
        self.ignore_section_button.setObjectName("explorerIgnoreSectionButton")
        self.ignore_section_button.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self.ignore_section_button.setArrowType(Qt.ArrowType.RightArrow)
        self.ignore_section_button.setCheckable(True)
        self.ignore_section_button.setText(
            self.texts["explorer_ignore_section"].format(
                count=len(self.ignored_names)
            )
        )
        self.ignore_section_button.toggled.connect(
            self._toggle_ignored_panel
        )
        layout.addWidget(
            self.ignore_section_button,
            0,
            Qt.AlignmentFlag.AlignLeft,
        )

        self.ignore_panel = QFrame()
        self.ignore_panel.setObjectName("explorerIgnoredPanel")
        self.ignore_panel.setFrameShape(QFrame.Shape.StyledPanel)
        ignored_panel_layout = QVBoxLayout(self.ignore_panel)
        ignored_panel_layout.setContentsMargins(8, 8, 8, 8)
        ignored_panel_layout.setSpacing(6)

        ignored_row = QHBoxLayout()
        self.ignore_input = QLineEdit()
        self.ignore_input.setPlaceholderText(
            self.texts["explorer_add_ignore_placeholder"]
        )
        self.ignore_input.returnPressed.connect(self._add_ignored_name)
        ignored_row.addWidget(self.ignore_input, 1)
        self.add_ignore_button = QPushButton(
            self.texts["explorer_add_ignore"]
        )
        self.add_ignore_button.clicked.connect(self._add_ignored_name)
        ignored_row.addWidget(self.add_ignore_button)
        ignored_panel_layout.addLayout(ignored_row)

        ignored_options_row = QHBoxLayout()
        self.show_ignored_checkbox = QCheckBox(
            self.texts["explorer_show_ignored"]
        )
        self.show_ignored_checkbox.setChecked(False)
        self.show_ignored_checkbox.toggled.connect(self._show_ignored_changed)
        ignored_options_row.addWidget(self.show_ignored_checkbox)
        ignored_options_row.addStretch(1)
        ignored_panel_layout.addLayout(ignored_options_row)

        ignored_list_row = QHBoxLayout()
        self.ignored_list = QListWidget()
        self.ignored_list.setMaximumHeight(78)
        self.ignored_list.setSelectionMode(
            QListWidget.SelectionMode.SingleSelection
        )
        self.ignored_list.itemSelectionChanged.connect(
            self._update_remove_ignore_state
        )
        ignored_list_row.addWidget(self.ignored_list, 1)
        self.remove_ignore_button = QPushButton(
            self.texts["explorer_remove_ignore"]
        )
        self.remove_ignore_button.setEnabled(False)
        self.remove_ignore_button.clicked.connect(self._remove_ignored_name)
        ignored_list_row.addWidget(self.remove_ignore_button)
        ignored_panel_layout.addLayout(ignored_list_row)

        self.warning_label = QLabel(
            self.texts["explorer_ignored_warning"]
        )
        self.warning_label.setObjectName("explorerWarningLabel")
        self.warning_label.setWordWrap(True)
        ignored_panel_layout.addWidget(self.warning_label)
        self.ignore_panel.hide()
        layout.addWidget(self.ignore_panel)

        self.status_label = QLabel(self.texts["explorer_choose_root"])
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.file_tree = QTreeWidget()
        self.file_tree.setObjectName("explorerFileTree")
        self.file_tree.setColumnCount(2)
        self.file_tree.setHeaderLabels(
            [
                self.texts["explorer_tree_name"],
                self.texts["explorer_tree_contents"],
            ]
        )
        self.file_tree.setRootIsDecorated(True)
        self.file_tree.setAlternatingRowColors(True)
        self.file_tree.setUniformRowHeights(True)
        self.file_tree.setSelectionMode(
            QTreeWidget.SelectionMode.SingleSelection
        )
        self.file_tree.header().setStretchLastSection(False)
        self.file_tree.header().setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.Stretch,
        )
        self.file_tree.header().setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        self.file_tree.itemExpanded.connect(self._on_tree_item_expanded)
        self.file_tree.itemChanged.connect(self._on_tree_item_changed)
        self.file_tree.currentItemChanged.connect(
            self._on_tree_current_item_changed
        )
        self.file_tree.itemDoubleClicked.connect(
            self._on_tree_item_double_clicked
        )
        self.splitter.addWidget(self.file_tree)

        preview = QWidget()
        self.structure_preview_panel = preview
        preview_layout = QVBoxLayout(preview)
        preview_layout.setContentsMargins(0, 4, 0, 0)
        preview_title = QLabel(self.texts["explorer_preview_title"])
        preview_title.setObjectName("explorerPreviewTitle")
        preview_layout.addWidget(preview_title)
        preview_actions = QHBoxLayout()
        self.char_count_label = QLabel(
            self.texts["explorer_preview_chars"].format(count=0)
        )
        preview_actions.addWidget(self.char_count_label, 1)
        self.copy_button = QPushButton(self.texts["explorer_copy_tree"])
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self._copy_tree)
        preview_actions.addWidget(self.copy_button)
        self.save_button = QPushButton(self.texts["explorer_save_tree"])
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self._save_tree)
        preview_actions.addWidget(self.save_button)
        preview_layout.addLayout(preview_actions)
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText(
            self.texts["explorer_preview_placeholder"]
        )
        preview_layout.addWidget(self.preview, 1)
        self.splitter.addWidget(preview)
        self.item_preview_panel = QWidget()
        item_preview_layout = QVBoxLayout(self.item_preview_panel)
        item_preview_layout.setContentsMargins(0, 4, 0, 0)
        item_preview_layout.setSpacing(6)
        item_preview_title = QLabel(
            self.texts["explorer_item_preview_title"]
        )
        item_preview_title.setObjectName("explorerItemPreviewTitle")
        item_preview_layout.addWidget(item_preview_title)
        self.item_preview_content = QWidget(self.item_preview_panel)
        self.item_preview_layout = QVBoxLayout(self.item_preview_content)
        self.item_preview_layout.setContentsMargins(0, 0, 0, 0)
        item_preview_layout.addWidget(self.item_preview_content, 1)
        self._item_preview_widget = None
        self._set_item_preview_message(
            self.texts["explorer_item_preview_placeholder"]
        )
        self.splitter.addWidget(self.item_preview_panel)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 3)
        self.splitter.setStretchFactor(2, 2)
        self.splitter.setSizes([500, 420, 360])
        layout.addWidget(self.splitter, 1)

        if self.inspection_mode:
            self.path_controls.hide()
            self.ignore_section_button.hide()
            self.ignore_panel.hide()
            self.structure_preview_panel.hide()

        if self._settings_warning:
            self._set_status(self.texts["explorer_settings_read_error"])

    def _toggle_ignored_panel(self, expanded: bool):
        self.ignore_panel.setVisible(expanded)
        self.ignore_section_button.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        )

    def _render_ignored_names(self):
        self.ignored_list.clear()
        for name in self.ignored_names:
            self.ignored_list.addItem(name)
        self.ignore_section_button.setText(
            self.texts["explorer_ignore_section"].format(
                count=len(self.ignored_names)
            )
        )
        self._update_remove_ignore_state()

    def _update_remove_ignore_state(self):
        self.remove_ignore_button.setEnabled(
            self.ignored_list.currentItem() is not None
        )

    def _set_status(self, message: str):
        self.status_label.setText(message)

    def _apply_typed_root(self):
        path = self.path_input.text().strip()
        if not path:
            self._set_status(self.texts["explorer_choose_root"])
            return
        self.set_root(path)

    def _browse_for_root(self):
        start = self.root_path or str(Path.home())
        selected = Explorer.get_existing_directory(
            self,
            caption=self.texts["explorer_browse_dialog_title"],
            directory=start,
            remember_location=not bool(
                getattr(self.window(), "private", False)
            ),
        )
        if selected:
            self.set_root(selected)

    def set_root(self, path: str):
        if self._closed:
            return
        try:
            root = canonical_root(path)
        except ExplorerError:
            self._set_status(self.texts["explorer_invalid_root"])
            return

        if self.fixed_root is not None:
            try:
                expected_root = canonical_root(self.fixed_root)
            except ExplorerError:
                self._set_status(self.texts["explorer_invalid_root"])
                return
            if root != expected_root:
                self._set_status(self.texts["explorer_root_fixed"])
                return

        self._cancel_tasks("scan")
        self._tree_refresh_timer.stop()
        self._tree_document_started = False
        self._invalidate_tree()
        self._root_generation += 1
        self.root_path = str(root)
        self.path_input.setText(self.root_path)
        self.selection = ExplorerSelection(
            include_all=not self.inspection_mode
        )
        self._clear_item_preview()
        self._clear_file_tree()
        self._create_root_item()
        if not self.inspection_mode:
            self._generate_tree()

    def _clear_file_tree(self):
        self.file_tree.clear()
        self._tree_root_item = None

    def _create_root_item(self):
        if self.root_path is None:
            return
        title = Path(self.root_path).name or self.root_path
        root_item = QTreeWidgetItem([title, ""])
        root_item.setIcon(
            0,
            QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon),
        )
        root_item.setData(0, Qt.ItemDataRole.UserRole, "")
        root_item.setData(0, Qt.ItemDataRole.UserRole + 1, "directory")
        root_item.setData(0, Qt.ItemDataRole.UserRole + 2, "unloaded")
        root_item.setChildIndicatorPolicy(
            QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator
        )
        self.file_tree.addTopLevelItem(root_item)
        self._tree_root_item = root_item
        root_item.setExpanded(True)
        self._load_directory(root_item)

    def _load_directory(self, parent_item: QTreeWidgetItem):
        if self.root_path is None:
            return
        scan_state = parent_item.data(
            0,
            Qt.ItemDataRole.UserRole + 2,
        )
        if scan_state in {"loading", "loaded"}:
            return

        relative_directory = parent_item.data(
            0,
            Qt.ItemDataRole.UserRole,
        )
        if relative_directory:
            directory = os.path.join(
                self.root_path,
                *PurePosixPath(relative_directory).parts,
            )
        else:
            directory = self.root_path

        self._clear_tree_children(parent_item)
        parent_item.setData(0, Qt.ItemDataRole.UserRole + 2, "loading")
        self._set_tree_placeholder(
            parent_item,
            self.texts["explorer_loading"],
        )

        request_id = self._next_id()
        self._scan_contexts[request_id] = (
            parent_item,
            relative_directory,
            self._root_generation,
        )
        arguments = (
            self.root_path,
            directory,
            self.ignored_names,
            self.limits,
            self.show_ignored_checkbox.isChecked(),
        )
        self._start_task(request_id, "scan", arguments)
        self._set_status(self.texts["explorer_loading"])

    def _on_tree_item_expanded(self, item: QTreeWidgetItem):
        if item.data(0, Qt.ItemDataRole.UserRole + 1) != "directory":
            return
        self._load_directory(item)

    def _on_tree_item_double_clicked(
        self,
        item: QTreeWidgetItem,
        _column: int,
    ):
        if item.data(0, Qt.ItemDataRole.UserRole + 1) != "file":
            return
        relative_path = item.data(0, Qt.ItemDataRole.UserRole)
        if relative_path and self.root_path is not None:
            self.file_open_requested.emit(self.root_path, relative_path)

    def _on_tree_current_item_changed(
        self,
        item: QTreeWidgetItem | None,
        _previous: QTreeWidgetItem | None,
    ):
        self._clear_item_preview()
        if item is None:
            self._set_item_preview_message(
                self.texts["explorer_item_preview_placeholder"]
            )
            return

        kind = item.data(0, Qt.ItemDataRole.UserRole + 1)
        relative_path = item.data(0, Qt.ItemDataRole.UserRole)
        if kind == "file" and relative_path and self.root_path is not None:
            preview = FilePreviewTab(
                self.root_path,
                relative_path,
                self.texts,
                self.item_preview_content,
                compact=True,
            )
            self._item_preview_widget = preview
            self.item_preview_layout.addWidget(preview, 1)
            return

        if kind == "directory":
            path = relative_path or self.root_path or item.text(0)
            self._set_item_preview_message(
                self.texts["explorer_item_preview_directory"].format(
                    name=item.text(0),
                    path=path,
                    details=item.text(1).strip(),
                )
            )
            return

        if kind in {"link", "blocked"}:
            self._set_item_preview_message(
                self.texts["explorer_item_preview_unavailable"]
            )
            return

        self._set_item_preview_message(
            self.texts["explorer_item_preview_placeholder"]
        )

    def _clear_item_preview(self):
        widget = self._item_preview_widget
        if widget is None:
            return
        shutdown = getattr(widget, "shutdown", None)
        if callable(shutdown):
            shutdown()
        self.item_preview_layout.removeWidget(widget)
        widget.setParent(None)
        widget.deleteLater()
        self._item_preview_widget = None

    def _set_item_preview_message(self, message: str):
        self._clear_item_preview()
        label = QLabel(message, self.item_preview_content)
        label.setObjectName("explorerItemPreviewMessage")
        label.setWordWrap(True)
        self.item_preview_layout.addWidget(
            label,
            1,
            Qt.AlignmentFlag.AlignTop,
        )
        self._item_preview_widget = label

    def _on_tree_item_changed(self, item: QTreeWidgetItem, column: int):
        if column != 0:
            return
        relative_path = item.data(0, Qt.ItemDataRole.UserRole)
        kind = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if not relative_path or kind is None:
            return

        checked = item.checkState(0) != Qt.CheckState.Unchecked
        self.selection.set_checked(relative_path, checked)
        self._invalidate_tree(
            clear_preview=not self._tree_document_started,
        )
        self._update_tree_check_states()
        if self._tree_document_started:
            self._tree_refresh_timer.start()
        if checked and kind == "directory":
            item.setExpanded(True)

    def _update_tree_check_states(self):
        state_by_name = {
            "unchecked": Qt.CheckState.Unchecked,
            "partial": Qt.CheckState.PartiallyChecked,
            "checked": Qt.CheckState.Checked,
        }
        with QSignalBlocker(self.file_tree):
            for item in self._iter_tree_items():
                relative_path = item.data(
                    0,
                    Qt.ItemDataRole.UserRole,
                )
                kind = item.data(0, Qt.ItemDataRole.UserRole + 1)
                if not relative_path or kind is None:
                    continue
                state = self.selection.state(
                    relative_path,
                    kind == "directory",
                )
                item.setCheckState(0, state_by_name[state])

    def _iter_tree_items(self):
        def walk(parent: QTreeWidgetItem):
            for index in range(parent.childCount()):
                child = parent.child(index)
                yield child
                yield from walk(child)

        if self._tree_root_item is not None:
            yield from walk(self._tree_root_item)

    def _clear_tree_children(self, item: QTreeWidgetItem):
        while item.childCount():
            item.takeChild(0)

    def _set_tree_placeholder(
        self,
        parent: QTreeWidgetItem,
        message: str,
    ):
        placeholder = QTreeWidgetItem([message, ""])
        placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
        parent.addChild(placeholder)

    def _create_entry_item(self, entry: ExplorerEntry):
        item = QTreeWidgetItem([entry.name, ""])
        item.setData(0, Qt.ItemDataRole.UserRole, entry.relative_path)
        item.setData(0, Qt.ItemDataRole.UserRole + 1, entry.kind)
        is_directory = entry.kind == "directory"
        if not self.inspection_mode:
            item.setFlags(
                item.flags() | Qt.ItemFlag.ItemIsUserCheckable
            )

        style = QApplication.style()
        if is_directory:
            item.setIcon(
                0,
                style.standardIcon(QStyle.StandardPixmap.SP_DirIcon),
            )
            item.setToolTip(
                0,
                self.texts["explorer_open_folder"],
            )
            item.setData(0, Qt.ItemDataRole.UserRole + 2, "unloaded")
            item.setChildIndicatorPolicy(
                QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator
            )
            if entry.folder_count is None or entry.file_count is None:
                count_text = self.texts["explorer_counts_unavailable"]
            else:
                folder_label = self.texts[
                    "explorer_folder_one"
                    if entry.folder_count == 1
                    else "explorer_folder_many"
                ]
                file_label = self.texts[
                    "explorer_file_one"
                    if entry.file_count == 1
                    else "explorer_file_many"
                ]
                count_text = self.texts["explorer_folder_count"].format(
                    folders=entry.folder_count,
                    files=entry.file_count,
                    folder_label=folder_label,
                    file_label=file_label,
                )
                if entry.counts_incomplete:
                    count_text += " +"
            item.setText(1, count_text)
        else:
            item.setData(0, Qt.ItemDataRole.UserRole + 2, "loaded")
            icon_kind = (
                QStyle.StandardPixmap.SP_FileLinkIcon
                if entry.kind == "link"
                else QStyle.StandardPixmap.SP_FileIcon
            )
            item.setIcon(0, style.standardIcon(icon_kind))
            if entry.kind == "link":
                item.setText(1, self.texts["explorer_link"])
            elif entry.kind == "blocked":
                item.setText(1, self.texts["explorer_blocked"])

        if not self.inspection_mode:
            state = self.selection.state(entry.relative_path, is_directory)
            state_by_name = {
                "unchecked": Qt.CheckState.Unchecked,
                "partial": Qt.CheckState.PartiallyChecked,
                "checked": Qt.CheckState.Checked,
            }
            item.setCheckState(0, state_by_name[state])
        item.setTextAlignment(
            1,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        return item

    def _show_ignored_changed(self, _checked: bool):
        if self.root_path is not None:
            self._reload_root()
        else:
            self._invalidate_tree()

    def _add_ignored_name(self):
        value = self.ignore_input.text()
        if not value.strip():
            self._set_status(self.texts["explorer_invalid_ignore"])
            return
        try:
            updated = validate_ignored_names(
                (*self.ignored_names, value)
            )
            self.ignored_names = self.settings_store.save_ignored_names(updated)
        except ExplorerSettingsError:
            self._set_status(self.texts["explorer_invalid_ignore"])
            return
        self.ignore_input.clear()
        self._render_ignored_names()
        self._reload_root()

    def _remove_ignored_name(self):
        selected = self.ignored_list.currentItem()
        if selected is None:
            return
        name = selected.text()
        updated = tuple(item for item in self.ignored_names if item != name)
        try:
            self.ignored_names = self.settings_store.save_ignored_names(updated)
        except ExplorerSettingsError:
            self._set_status(self.texts["explorer_settings_write_error"])
            return
        self._render_ignored_names()
        self._reload_root()

    def _reload_root(self):
        self._tree_refresh_timer.stop()
        self._invalidate_tree()
        if self.root_path is not None:
            self._cancel_tasks("scan")
            self._root_generation += 1
            self._clear_file_tree()
            self._create_root_item()
            if self._tree_document_started:
                self._tree_refresh_timer.start()

    def _generate_tree(self):
        if self.root_path is None:
            self._set_status(self.texts["explorer_choose_root"])
            return
        self._tree_document_started = True
        timer = getattr(self, "_tree_refresh_timer", None)
        if timer is not None:
            timer.stop()
        self._invalidate_tree(clear_preview=False)

        request_id = self._next_id()
        self._latest_tree_id = request_id
        arguments = (
            self.root_path,
            self.selection.to_dict(),
            self.ignored_names,
            self.limits,
            self.show_ignored_checkbox.isChecked(),
        )
        self._start_task(request_id, "tree", arguments)
        self._set_status(self.texts["explorer_generating_tree"])

    def _show_directory_error(
        self,
        item: QTreeWidgetItem,
        message: str,
    ):
        self._clear_tree_children(item)
        item.setData(0, Qt.ItemDataRole.UserRole + 2, "failed")
        item.setChildIndicatorPolicy(
            QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator
        )
        self._set_tree_placeholder(item, message)
        self._set_status(message)

    def _invalidate_tree(self, *, clear_preview: bool = True):
        if self._latest_tree_id is not None:
            task = self._tasks.get(self._latest_tree_id)
            if task is not None:
                task.cancel()
        self._latest_tree_id = None
        if clear_preview:
            self.preview.clear()
            self.char_count_label.setText(
                self.texts["explorer_preview_chars"].format(count=0)
            )
            self.copy_button.setEnabled(False)
            self.save_button.setEnabled(False)

    def _copy_tree(self):
        text = self.preview.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self._set_status(self.texts["explorer_tree_copied"])

    def _save_tree(self):
        text = self.preview.toPlainText()
        if not text:
            return
        path = Explorer.get_save_file_name(
            self,
            caption=self.texts["explorer_save_dialog_title"],
            name_filters=("Arquivos de texto (*.txt)",),
            initial_name="estrutura.txt",
            remember_location=not bool(
                getattr(self.window(), "private", False)
            ),
        )
        if not path:
            return
        if not path.lower().endswith(".txt"):
            path += ".txt"
        try:
            with open(path, "w", encoding="utf-8") as stream:
                stream.write(text)
        except OSError:
            self._set_status(self.texts["explorer_save_error"])
            return
        self._set_status(self.texts["explorer_tree_saved"])

    def _next_id(self) -> int:
        request_id = self._next_request_id
        self._next_request_id += 1
        return request_id

    def _start_task(self, request_id: int, operation: str, arguments: tuple):
        task = ExplorerTask(request_id, operation, arguments)
        task.signals.result.connect(self._on_task_result)
        task.signals.failed.connect(self._on_task_failed)
        task.signals.finished.connect(self._on_task_finished)
        self._tasks[request_id] = task
        QThreadPool.globalInstance().start(task)

    def _cancel_tasks(self, operation: str | None = None):
        for request_id, task in tuple(self._tasks.items()):
            if operation is None or task.operation == operation:
                task.cancel()
                self._scan_contexts.pop(request_id, None)

    def _on_task_result(self, request_id: int, result):
        if self._closed:
            return
        if isinstance(result, ExplorerScanResult):
            context = self._scan_contexts.pop(request_id, None)
            if context is None:
                return
            parent_item, relative_directory, generation = context
            if (
                generation != self._root_generation
                or parent_item.treeWidget() is not self.file_tree
                or parent_item.data(0, Qt.ItemDataRole.UserRole)
                != relative_directory
            ):
                return
            if result.error == "permission":
                self._show_directory_error(
                    parent_item,
                    self.texts["explorer_permission_error"],
                )
                return
            with QSignalBlocker(self.file_tree):
                self._clear_tree_children(parent_item)
                if result.entries:
                    parent_item.setChildIndicatorPolicy(
                        QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator
                    )
                    for entry in result.entries:
                        parent_item.addChild(self._create_entry_item(entry))
                else:
                    parent_item.setChildIndicatorPolicy(
                        QTreeWidgetItem.ChildIndicatorPolicy.DontShowIndicatorWhenChildless
                    )
                    self._set_tree_placeholder(
                        parent_item,
                        self.texts["explorer_empty_column"],
                    )
                parent_item.setData(
                    0,
                    Qt.ItemDataRole.UserRole + 2,
                    "loaded",
                )
            if result.incomplete:
                message_key = {
                    "items": "explorer_many_items",
                    "permission": "explorer_permission_error",
                }.get(result.limit_reason, "explorer_scan_timeout")
                message = self.texts[message_key]
                self._set_status(message)
            else:
                self._set_status(self.texts["explorer_ready"])
        elif isinstance(result, ExplorerTreeResult):
            if request_id != self._latest_tree_id:
                return
            self.preview.setPlainText(result.text)
            self.char_count_label.setText(
                self.texts["explorer_preview_chars"].format(
                    count=len(result.text)
                )
            )
            self.copy_button.setEnabled(bool(result.text))
            self.save_button.setEnabled(bool(result.text))
            if result.incomplete:
                self._set_status(self.texts["explorer_tree_partial"])
            else:
                self._set_status(self.texts["explorer_tree_ready"])

    def _on_task_failed(self, request_id: int, message: str):
        if self._closed:
            return
        context = self._scan_contexts.pop(request_id, None)
        if context is not None:
            parent_item, _relative_directory, generation = context
            if (
                generation == self._root_generation
                and parent_item.treeWidget() is self.file_tree
            ):
                self._show_directory_error(parent_item, message)
        elif request_id == self._latest_tree_id:
            self._set_status(message)

    def _on_task_finished(self, request_id: int):
        self._tasks.pop(request_id, None)
        self._scan_contexts.pop(request_id, None)

    def shutdown(self):
        if self._closed:
            return
        self._closed = True
        self._tree_refresh_timer.stop()
        self._cancel_tasks()
        self._clear_item_preview()

    def closeEvent(self, event):
        self.shutdown()
        super().closeEvent(event)
