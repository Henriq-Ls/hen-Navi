"""Barra compacta de favoritos para o rodapé do navegador."""

from __future__ import annotations

import base64
from urllib.parse import urlsplit

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QWidget,
)

from _CONFIGURA_ import COR_TEXTO, TEXTO_UI
from _ULTILIDADES_.icones import ico_editar, ico_favoritos, ico_lixo, icone
from _ULTILIDADES_.popups import popup_pergunta


class FavoritesStatusBar(QScrollArea):
    """Mostra até dez favoritos, com largura proporcional ao nome exibido."""

    openRequested = Signal(str)
    openAllRequested = Signal()
    changed = Signal()

    MAX_VISIBLE_FAVORITES = 10
    MAX_LABEL_CHARS = 18

    def __init__(self, storage, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.setObjectName("favoritesStatusBar")
        self.setAccessibleName(TEXTO_UI["favorites"])
        self.setToolTip(TEXTO_UI["favorites_bar_scroll_hint"])
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet(
            "QScrollArea#favoritesStatusBar, "
            "QWidget#favoritesStatusContent { "
            "background: transparent; border: none; }"
        )
        self.setWidgetResizable(False)
        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.setMinimumHeight(24)
        self.setMaximumHeight(26)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._content = QWidget(self)
        self._content.setObjectName("favoritesStatusContent")
        self._content_layout = QHBoxLayout(self._content)
        self._content_layout.setContentsMargins(2, 0, 2, 0)
        self._content_layout.setSpacing(2)
        self.setWidget(self._content)
        self._favorite_items_by_url: dict[str, QWidget] = {}
        self._all_items_button = self._create_all_items_button()
        self.refresh()

    def _create_all_items_button(self) -> QToolButton:
        button = QToolButton(self._content)
        button.setObjectName("favoritesStatusAllButton")
        button.setIcon(ico_favoritos())
        button.setIconSize(QSize(14, 14))
        button.setFixedSize(QSize(24, 22))
        button.setAutoRaise(True)
        button.setToolTip(TEXTO_UI["favorites"])
        button.setAccessibleName(TEXTO_UI["favorites"])
        button.clicked.connect(
            lambda _checked=False: self.openAllRequested.emit()
        )
        return button

    def refresh(self):
        self.horizontalScrollBar().setValue(0)
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            widget = item.widget()
            if (
                widget is not None
                and widget is not self._all_items_button
                and widget not in self._favorite_items_by_url.values()
            ):
                widget.deleteLater()

        items = self.storage.get_favorites()
        visible_items = items[: self.MAX_VISIBLE_FAVORITES]
        visible_urls = {str(entry.get("url", "")) for entry in visible_items}
        for url, widget in list(self._favorite_items_by_url.items()):
            if url in visible_urls:
                continue
            self._content_layout.removeWidget(widget)
            widget.deleteLater()
            del self._favorite_items_by_url[url]

        self._content_layout.addWidget(
            self._all_items_button,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )

        if not visible_items:
            empty_label = QLabel(TEXTO_UI["favorites_bar_empty"], self._content)
            empty_label.setObjectName("favoritesStatusEmpty")
            self._content_layout.addWidget(
                empty_label,
                0,
                Qt.AlignmentFlag.AlignVCenter,
            )

        for entry in visible_items:
            url = str(entry.get("url", ""))
            item_widget = self._favorite_items_by_url.get(url)
            if item_widget is None:
                item_widget = self._make_favorite_item(entry)
                self._favorite_items_by_url[url] = item_widget
            else:
                self._update_favorite_item(item_widget, entry)
            self._content_layout.addWidget(
                item_widget,
                0,
                Qt.AlignmentFlag.AlignVCenter,
            )

        hidden_count = len(items) - len(visible_items)
        if hidden_count > 0:
            more_button = QToolButton(self._content)
            more_button.setObjectName("favoritesStatusMoreButton")
            more_button.setText(f"+{hidden_count}")
            more_button.setAutoRaise(True)
            more_button.setToolTip(TEXTO_UI["favorites_bar_more"])
            more_button.setAccessibleName(TEXTO_UI["favorites_bar_more"])
            more_button.clicked.connect(
                lambda _checked=False: self.openAllRequested.emit()
            )
            self._content_layout.addWidget(
                more_button,
                0,
                Qt.AlignmentFlag.AlignVCenter,
            )

        self._content_layout.activate()
        content_size = self._content_layout.sizeHint()
        self._content.setFixedSize(
            max(1, content_size.width()),
            max(24, content_size.height()),
        )
        self.horizontalScrollBar().setValue(0)

    def _make_favorite_item(self, entry: dict) -> QWidget:
        url = str(entry.get("url", ""))
        title = str(entry.get("title") or "").strip()
        if not title:
            title = urlsplit(url).hostname or url

        item = QWidget(self._content)
        item.setObjectName("favoriteStatusItem")
        item.setProperty("favoriteUrl", url)
        item.setProperty("favoriteTitle", title)
        layout = QHBoxLayout(item)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        open_button = QToolButton(item)
        open_button.setObjectName("favoriteStatusOpenButton")
        open_button.setIcon(self._favicon_icon(url))
        open_button.setIconSize(QSize(16, 16))
        open_button.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        open_button.setAutoRaise(True)
        open_button.setSizePolicy(
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Fixed,
        )
        open_button.setText(self._visible_title(title))
        open_button.setToolTip(f'{TEXTO_UI["favorite_open"]}: {title}\n{url}')
        open_button.setAccessibleName(
            f'{TEXTO_UI["favorite_open"]}: {title}'
        )
        open_button.setStyleSheet("QToolButton { padding: 1px 4px; }")
        open_button.clicked.connect(
            lambda _checked=False, target=url: self.openRequested.emit(target)
        )
        layout.addWidget(open_button)

        options_button = QToolButton(item)
        options_button.setObjectName("favoriteStatusOptionsButton")
        options_button.setText("⋮")
        options_button.setFixedSize(QSize(22, 22))
        options_button.setAutoRaise(True)
        options_button.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )
        options_button.setToolTip(
            f'{TEXTO_UI["favorite_options_tooltip"]}: {title}'
        )
        options_button.setAccessibleName(
            f'{TEXTO_UI["favorite_options_tooltip"]}: {title}'
        )
        menu = QMenu(options_button)
        edit_action = menu.addAction(
            ico_editar(),
            TEXTO_UI["favorite_edit_action"],
        )
        delete_action = menu.addAction(
            ico_lixo(),
            TEXTO_UI["favorite_remove"],
        )
        edit_action.triggered.connect(
            lambda _checked=False, row=item: self._edit_favorite(
                str(row.property("favoriteUrl") or ""),
                str(row.property("favoriteTitle") or ""),
            )
        )
        delete_action.triggered.connect(
            lambda _checked=False, row=item: self._remove_favorite(
                str(row.property("favoriteUrl") or ""),
                str(row.property("favoriteTitle") or ""),
            )
        )
        options_button.setMenu(menu)
        layout.addWidget(options_button)
        return item

    def _update_favorite_item(self, item: QWidget, entry: dict) -> None:
        url = str(entry.get("url", ""))
        title = str(entry.get("title") or "").strip()
        if not title:
            title = urlsplit(url).hostname or url
        item.setProperty("favoriteUrl", url)
        item.setProperty("favoriteTitle", title)

        open_button = item.findChild(QToolButton, "favoriteStatusOpenButton")
        if open_button is not None:
            open_button.setIcon(self._favicon_icon(url))
            open_button.setText(self._visible_title(title))
            open_button.setToolTip(
                f'{TEXTO_UI["favorite_open"]}: {title}\n{url}'
            )
            open_button.setAccessibleName(
                f'{TEXTO_UI["favorite_open"]}: {title}'
            )

        options_button = item.findChild(
            QToolButton,
            "favoriteStatusOptionsButton",
        )
        if options_button is not None:
            options_button.setToolTip(
                f'{TEXTO_UI["favorite_options_tooltip"]}: {title}'
            )
            options_button.setAccessibleName(
                f'{TEXTO_UI["favorite_options_tooltip"]}: {title}'
            )

    @classmethod
    def _visible_title(cls, title: str) -> str:
        if len(title) <= cls.MAX_LABEL_CHARS:
            return title
        return f"{title[: cls.MAX_LABEL_CHARS - 1].rstrip()}…"

    def _favicon_icon(self, url: str) -> QIcon:
        data_uri = self.storage.get_favicon(url)
        prefix = "data:image/png;base64,"
        if isinstance(data_uri, str) and data_uri.startswith(prefix):
            try:
                image_data = base64.b64decode(
                    data_uri[len(prefix):],
                    validate=True,
                )
                pixmap = QPixmap()
                if pixmap.loadFromData(image_data, "PNG") and not pixmap.isNull():
                    return QIcon(pixmap)
            except (ValueError, base64.binascii.Error):
                pass
        return icone("fa5s.globe", COR_TEXTO)

    def _edit_favorite(self, url: str, title: str):
        new_title, accepted = QInputDialog.getText(
            self,
            TEXTO_UI["favorite_edit_title"],
            TEXTO_UI["favorite_edit_prompt"],
            QLineEdit.EchoMode.Normal,
            title,
        )
        new_title = new_title.strip()
        if not accepted or not new_title:
            return
        if self.storage.add_favorite(url, new_title):
            self.changed.emit()

    def _remove_favorite(self, url: str, title: str):
        answer = popup_pergunta(
            TEXTO_UI["favorite_remove_confirm_title"],
            TEXTO_UI["favorite_remove_confirm_message"].format(title=title),
            self,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        if self.storage.remove_favorite(url):
            self.changed.emit()

    def wheelEvent(self, event):
        delta = event.angleDelta().x() or event.angleDelta().y()
        if not delta:
            super().wheelEvent(event)
            return
        bar = self.horizontalScrollBar()
        bar.setValue(bar.value() - delta)
        event.accept()
