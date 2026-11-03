"""Painel de inspeção manual do DOM da aba atual."""

import json

from _CONFIGURA_ import TEXTO_UI
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDockWidget,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


_PICK_MARKER = "__HENNAVE_INSPECTOR_PICK__:"

_DOM_TREE_SCRIPT = r"""
(() => {
    const pathFor = (element) => {
        const parts = [];
        let current = element;
        while (current && current.nodeType === Node.ELEMENT_NODE) {
            if (current.id && document.getElementById(current.id) === current) {
                parts.unshift("#" + CSS.escape(current.id));
                break;
            }
            let position = 1;
            for (let sibling = current.previousElementSibling; sibling;
                 sibling = sibling.previousElementSibling) {
                if (sibling.tagName === current.tagName) position += 1;
            }
            parts.unshift(current.tagName.toLowerCase() +
                          ":nth-of-type(" + position + ")");
            current = current.parentElement;
        }
        return parts.join(" > ");
    };
    const describe = (element) => {
        const tag = element.tagName.toLowerCase();
        const id = element.id ? "#" + element.id : "";
        const classes = typeof element.className === "string"
            ? element.className.trim().split(/\s+/).filter(Boolean).slice(0, 3)
            : [];
        return {
            label: "<" + tag + id +
                   (classes.length ? "." + classes.join(".") : "") + ">",
            selector: pathFor(element),
            tag
        };
    };
    let visited = 0;
    const build = (element, depth) => {
        if (!element || visited >= 650) return null;
        visited += 1;
        const item = describe(element);
        item.children = [];
        if (depth < 6) {
            for (const child of element.children) {
                if (visited >= 650) break;
                const node = build(child, depth + 1);
                if (node) item.children.push(node);
            }
        }
        return item;
    };
    return document.documentElement ? build(document.documentElement, 0) : null;
})()
"""

_DOM_SEARCH_SCRIPT = r"""
(term) => {
    const pathFor = (element) => {
        const parts = [];
        let current = element;
        while (current && current.nodeType === Node.ELEMENT_NODE) {
            if (current.id && document.getElementById(current.id) === current) {
                parts.unshift("#" + CSS.escape(current.id));
                break;
            }
            let position = 1;
            for (let sibling = current.previousElementSibling; sibling;
                 sibling = sibling.previousElementSibling) {
                if (sibling.tagName === current.tagName) position += 1;
            }
            parts.unshift(current.tagName.toLowerCase() +
                          ":nth-of-type(" + position + ")");
            current = current.parentElement;
        }
        return parts.join(" > ");
    };
    const needle = String(term || "").toLocaleLowerCase();
    const results = [];
    for (const element of document.querySelectorAll("*")) {
        const classes = typeof element.className === "string"
            ? element.className.trim().split(/\s+/).filter(Boolean).slice(0, 3)
            : [];
        const directText = Array.from(element.childNodes)
            .filter((node) => node.nodeType === Node.TEXT_NODE)
            .map((node) => node.nodeValue || "")
            .join(" ");
        const searchable = [
            element.tagName,
            element.id,
            classes.join(" "),
            element.getAttribute("role") || "",
            directText
        ].join(" ").toLocaleLowerCase();
        if (!needle || searchable.includes(needle)) {
            const tag = element.tagName.toLowerCase();
            results.push({
                label: "<" + tag + (element.id ? "#" + element.id : "") +
                       (classes.length ? "." + classes.join(".") : "") + ">",
                selector: pathFor(element),
                tag,
                children: []
            });
            if (results.length >= 150) break;
        }
    }
    return results;
}
"""

_SELECT_ELEMENT_SCRIPT = r"""
(() => {
    if (window.__henNaveInspectorPickHandler) {
        document.removeEventListener(
            "click", window.__henNaveInspectorPickHandler, true
        );
    }
    const handler = (event) => {
        const element = event.target instanceof Element
            ? event.target
            : event.target.parentElement;
        if (!element) return;
        event.preventDefault();
        event.stopImmediatePropagation();
        event.stopPropagation();
        let current = element;
        const parts = [];
        while (current && current.nodeType === Node.ELEMENT_NODE) {
            if (current.id && document.getElementById(current.id) === current) {
                parts.unshift("#" + CSS.escape(current.id));
                break;
            }
            let position = 1;
            for (let sibling = current.previousElementSibling; sibling;
                 sibling = sibling.previousElementSibling) {
                if (sibling.tagName === current.tagName) position += 1;
            }
            parts.unshift(current.tagName.toLowerCase() +
                          ":nth-of-type(" + position + ")");
            current = current.parentElement;
        }
        const selector = parts.join(" > ");
        document.removeEventListener("click", handler, true);
        window.__henNaveInspectorPickHandler = null;
        console.log("__HENNAVE_INSPECTOR_PICK__:" + selector);
    };
    window.__henNaveInspectorPickHandler = handler;
    document.addEventListener("click", handler, true);
    return true;
})()
"""


def _selected_markup_script(selector: str) -> str:
    encoded = json.dumps(selector)
    return f"""
(() => {{
    const element = document.querySelector({encoded});
    if (!element) return null;
    const copy = element.cloneNode(true);
    const controls = [];
    if (copy.matches && copy.matches("input, textarea, select, option")) {{
        controls.push(copy);
    }}
    controls.push(...copy.querySelectorAll("input, textarea, select, option"));
    for (const control of controls) {{
        control.removeAttribute("value");
        control.removeAttribute("selected");
        if ("value" in control) control.value = "";
        if (control.tagName === "TEXTAREA") control.textContent = "";
        if (control.tagName === "SELECT") control.selectedIndex = -1;
    }}
    return {{
        markup: copy.outerHTML,
        text: element.innerText || "",
        tag: element.tagName.toLowerCase()
    }};
}})()
"""


class PageInspectorDock(QDockWidget):
    """Inspeção manual: consulta o DOM ativo e permite mudanças locais temporárias."""

    selectionRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(TEXTO_UI["inspect_title"], parent)
        self._page = None
        self._selected_selector = ""
        self._selected_tag = ""
        self._picking = False

        content = QWidget(self)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.notice_label = QLabel(TEXTO_UI["inspect_notice"], content)
        self.notice_label.setWordWrap(True)
        layout.addWidget(self.notice_label)

        action_row = QHBoxLayout()
        self.pick_button = QPushButton(TEXTO_UI["inspect_select_element"], content)
        self.pick_button.clicked.connect(self.toggle_element_pick)
        self.refresh_button = QPushButton(TEXTO_UI["inspect_refresh"], content)
        self.refresh_button.clicked.connect(self.refresh_dom)
        action_row.addWidget(self.pick_button)
        action_row.addWidget(self.refresh_button)
        layout.addLayout(action_row)

        search_row = QHBoxLayout()
        self.search_field = QLineEdit(content)
        self.search_field.setPlaceholderText(TEXTO_UI["inspect_search_placeholder"])
        self.search_field.returnPressed.connect(self.search_dom)
        self.search_button = QPushButton(TEXTO_UI["inspect_search_button"], content)
        self.search_button.clicked.connect(self.search_dom)
        search_row.addWidget(self.search_field, 1)
        search_row.addWidget(self.search_button)
        layout.addLayout(search_row)

        self.tree = QTreeWidget(content)
        self.tree.setObjectName("inspectorTree")
        self.tree.setHeaderHidden(True)
        self.tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
        layout.addWidget(self.tree, 2)

        self.selected_label = QLabel(TEXTO_UI["inspect_empty"], content)
        self.selected_label.setWordWrap(True)
        layout.addWidget(self.selected_label)

        layout.addWidget(QLabel(TEXTO_UI["inspect_markup_heading"], content))
        self.markup_view = QPlainTextEdit(content)
        self.markup_view.setObjectName("inspectorMarkup")
        self.markup_view.setReadOnly(True)
        self.markup_view.setMaximumHeight(150)
        layout.addWidget(self.markup_view)

        copy_row = QHBoxLayout()
        self.copy_text_button = QPushButton(TEXTO_UI["inspect_copy_text"], content)
        self.copy_text_button.clicked.connect(self.copy_selected_text)
        self.copy_markup_button = QPushButton(TEXTO_UI["inspect_copy_markup"], content)
        self.copy_markup_button.clicked.connect(self.copy_selected_markup)
        copy_row.addWidget(self.copy_text_button)
        copy_row.addWidget(self.copy_markup_button)
        layout.addLayout(copy_row)

        layout.addWidget(QLabel(TEXTO_UI["inspect_edit_heading"], content))
        form = QFormLayout()
        self.text_edit = QPlainTextEdit(content)
        self.text_edit.setMaximumHeight(72)
        form.addRow(TEXTO_UI["inspect_text_label"], self.text_edit)
        self.background_field = QLineEdit(content)
        self.background_field.setPlaceholderText("#334455")
        form.addRow(TEXTO_UI["inspect_background_label"], self.background_field)
        self.foreground_field = QLineEdit(content)
        self.foreground_field.setPlaceholderText("#ffffff")
        form.addRow(TEXTO_UI["inspect_foreground_label"], self.foreground_field)
        layout.addLayout(form)

        edit_row = QHBoxLayout()
        self.apply_text_button = QPushButton(TEXTO_UI["inspect_apply_text"], content)
        self.apply_text_button.clicked.connect(self.apply_text_edit)
        self.apply_style_button = QPushButton(TEXTO_UI["inspect_apply_style"], content)
        self.apply_style_button.clicked.connect(self.apply_style_edit)
        edit_row.addWidget(self.apply_text_button)
        edit_row.addWidget(self.apply_style_button)
        layout.addLayout(edit_row)

        self.setWidget(content)
        self._set_page_controls_enabled(False)

    def set_page(self, page) -> None:
        if page is self._page:
            return
        self.cancel_element_pick()
        if self._page is not None:
            try:
                self._page.inspectionElementSelected.disconnect(
                    self._on_page_element_selected
                )
            except (AttributeError, RuntimeError, TypeError):
                pass
        self._page = page
        self._selected_selector = ""
        self._selected_tag = ""
        self.tree.clear()
        self.markup_view.clear()
        self.text_edit.clear()
        self.selected_label.setText(
            TEXTO_UI["inspect_empty"] if page else TEXTO_UI["inspect_no_page"]
        )
        if page is not None:
            try:
                page.inspectionElementSelected.connect(
                    self._on_page_element_selected
                )
            except AttributeError:
                pass
        self._set_page_controls_enabled(page is not None)
        if page is not None and self.isVisible():
            self.refresh_dom()

    def refresh_dom(self) -> None:
        if self._page is None:
            self.selected_label.setText(TEXTO_UI["inspect_no_page"])
            return
        self._selected_selector = ""
        self._selected_tag = ""
        self.markup_view.clear()
        self.text_edit.clear()
        self.copy_text_button.setEnabled(False)
        self.copy_markup_button.setEnabled(False)
        self.apply_text_button.setEnabled(False)
        self.apply_style_button.setEnabled(False)
        self._page.runJavaScript(_DOM_TREE_SCRIPT, self._populate_tree)

    def search_dom(self) -> None:
        if self._page is None:
            self.selected_label.setText(TEXTO_UI["inspect_no_page"])
            return
        term = json.dumps(self.search_field.text())
        self._page.runJavaScript(
            f"({_DOM_SEARCH_SCRIPT})({term})",
            self._populate_search_results,
        )

    def toggle_element_pick(self) -> None:
        if self._page is None:
            return
        if self._picking:
            self.cancel_element_pick()
            return
        self._picking = True
        self.pick_button.setText(TEXTO_UI["inspect_cancel_selection"])
        self.selected_label.setText(TEXTO_UI["inspect_selection_armed"])
        self._page.runJavaScript(_SELECT_ELEMENT_SCRIPT)
        self.selectionRequested.emit()

    def cancel_element_pick(self) -> None:
        if self._picking and self._page is not None:
            self._page.runJavaScript(
                """
                (() => {
                    if (window.__henNaveInspectorPickHandler) {
                        document.removeEventListener(
                            "click", window.__henNaveInspectorPickHandler, true
                        );
                        window.__henNaveInspectorPickHandler = null;
                    }
                })()
                """
            )
        self._picking = False
        self.pick_button.setText(TEXTO_UI["inspect_select_element"])

    def _on_page_element_selected(self, selector: str) -> None:
        if not self._picking:
            return
        self.cancel_element_pick()
        self._select_element(selector)

    def _populate_tree(self, data) -> None:
        self.tree.clear()
        if not isinstance(data, dict):
            return
        root = self._add_tree_node(data)
        if root is not None:
            self.tree.addTopLevelItem(root)
            root.setExpanded(True)

    def _populate_search_results(self, results) -> None:
        self.tree.clear()
        if not isinstance(results, list) or not results:
            self.selected_label.setText(TEXTO_UI["inspect_search_empty"])
            return
        for data in results:
            if isinstance(data, dict):
                item = self._add_tree_node(data)
                if item is not None:
                    self.tree.addTopLevelItem(item)

    def _add_tree_node(self, data) -> QTreeWidgetItem | None:
        label = data.get("label")
        selector = data.get("selector")
        if not isinstance(label, str) or not isinstance(selector, str):
            return None
        item = QTreeWidgetItem([label])
        item.setData(0, Qt.ItemDataRole.UserRole, selector)
        item.setData(0, Qt.ItemDataRole.UserRole + 1, data.get("tag", ""))
        for child in data.get("children", []):
            if isinstance(child, dict):
                child_item = self._add_tree_node(child)
                if child_item is not None:
                    item.addChild(child_item)
        return item

    def _on_tree_selection_changed(self) -> None:
        item = self.tree.currentItem()
        if item is None:
            return
        selector = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(selector, str) and selector:
            self._select_element(selector)

    def _select_element(self, selector: str) -> None:
        if self._page is None:
            return
        self._selected_selector = selector
        self._page.runJavaScript(
            _selected_markup_script(selector),
            self._show_selected_element,
        )

    def _show_selected_element(self, details) -> None:
        if not isinstance(details, dict):
            self.selected_label.setText(TEXTO_UI["inspect_update_error"])
            return
        self._selected_tag = str(details.get("tag") or "")
        self.selected_label.setText(
            TEXTO_UI["inspect_selected"].format(
                selector=self._selected_selector
            )
        )
        self.markup_view.setPlainText(str(details.get("markup") or "")[:16000])
        self.text_edit.setPlainText(str(details.get("text") or "")[:4000])
        self.copy_text_button.setEnabled(True)
        self.copy_markup_button.setEnabled(bool(self.markup_view.toPlainText()))
        editable = self._selected_tag not in {
            "input", "textarea", "select", "option"
        }
        self.text_edit.setEnabled(editable)
        self.background_field.setEnabled(editable)
        self.foreground_field.setEnabled(editable)
        self.apply_text_button.setEnabled(editable)
        self.apply_style_button.setEnabled(editable)

    def copy_selected_text(self) -> None:
        if self._page is None or not self._selected_selector:
            self.selected_label.setText(TEXTO_UI["inspect_no_element"])
            return
        selector = json.dumps(self._selected_selector)
        self._page.runJavaScript(
            f"""(() => {{
                const element = document.querySelector({selector});
                return element ? (element.innerText || "") : "";
            }})()""",
            self._copy_to_clipboard,
        )

    def copy_selected_markup(self) -> None:
        if not self.markup_view.toPlainText():
            self.selected_label.setText(TEXTO_UI["inspect_no_element"])
            return
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(self.markup_view.toPlainText())

    def _copy_to_clipboard(self, text) -> None:
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(str(text or ""))

    def apply_text_edit(self) -> None:
        if not self._can_edit_selected():
            return
        selector = json.dumps(self._selected_selector)
        text = json.dumps(self.text_edit.toPlainText())
        self._page.runJavaScript(
            f"""(() => {{
                const element = document.querySelector({selector});
                if (!element) return false;
                element.textContent = {text};
                return true;
            }})()""",
            self._edit_applied,
        )

    def apply_style_edit(self) -> None:
        if not self._can_edit_selected():
            return
        background = self.background_field.text().strip()
        foreground = self.foreground_field.text().strip()
        colors = []
        for value in (background, foreground):
            if value and not QColor.isValidColor(value):
                QMessageBox.warning(
                    self,
                    TEXTO_UI["inspect_title"],
                    TEXTO_UI["inspect_invalid_color"],
                )
                return
            colors.append(QColor(value).name(QColor.NameFormat.HexRgb) if value else "")
        selector = json.dumps(self._selected_selector)
        background_js = json.dumps(colors[0])
        foreground_js = json.dumps(colors[1])
        self._page.runJavaScript(
            f"""(() => {{
                const element = document.querySelector({selector});
                if (!element) return false;
                if ({background_js}) element.style.backgroundColor = {background_js};
                if ({foreground_js}) element.style.color = {foreground_js};
                return true;
            }})()""",
            self._edit_applied,
        )

    def _edit_applied(self, succeeded) -> None:
        if not succeeded:
            self.selected_label.setText(TEXTO_UI["inspect_update_error"])
            return
        self.selected_label.setText(TEXTO_UI["inspect_update_success"])
        self._select_element(self._selected_selector)

    def _can_edit_selected(self) -> bool:
        if self._page is None or not self._selected_selector:
            self.selected_label.setText(TEXTO_UI["inspect_no_element"])
            return False
        if self._selected_tag in {"input", "textarea", "select", "option"}:
            self.selected_label.setText(TEXTO_UI["inspect_edit_disabled_control"])
            return False
        return True

    def _set_page_controls_enabled(self, enabled: bool) -> None:
        for widget in (
            self.pick_button,
            self.refresh_button,
            self.search_field,
            self.search_button,
            self.tree,
        ):
            widget.setEnabled(enabled)
        self.copy_text_button.setEnabled(False)
        self.copy_markup_button.setEnabled(False)
        self.apply_text_button.setEnabled(False)
        self.apply_style_button.setEnabled(False)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._page is not None:
            self.refresh_dom()

    def hideEvent(self, event) -> None:
        self.cancel_element_pick()
        super().hideEvent(event)


def inspection_pick_marker() -> str:
    """Prefix privado usado para entregar seleções de JS à janela Qt."""
    return _PICK_MARKER
