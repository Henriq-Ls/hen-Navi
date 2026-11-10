from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import QEvent, QPoint, QRect
    from PySide6.QtWidgets import (
        QApplication,
        QStatusBar,
        QToolButton,
        QVBoxLayout,
        QWidget,
    )

    from _APPDATA_.storage import BrowserStorage
    from _APP_.favorites_bar import FavoritesStatusBar
except ModuleNotFoundError:
    PYSIDE6_AVAILABLE = False
else:
    PYSIDE6_AVAILABLE = True


@unittest.skipUnless(
    PYSIDE6_AVAILABLE,
    "PySide6 não está instalado neste ambiente.",
)
class FavoritesBarRefreshQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _is_in_viewport(self, widget: QWidget, bar: FavoritesStatusBar) -> bool:
        point = widget.mapTo(bar.viewport(), QPoint(0, 0))
        return QRect(point, widget.size()).intersects(bar.viewport().rect())

    def test_editing_after_scroll_keeps_the_favorites_bar_and_data_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = BrowserStorage(os.path.join(directory, "favorites.sqlite3"))
            urls = []
            for index in range(12):
                url = f"https://site-{index:02d}.example/"
                urls.append(url)
                storage.add_favorite(url, f"Favorito {index:02d} com um nome longo")

            host = QWidget()
            host_layout = QVBoxLayout(host)
            host_layout.setContentsMargins(0, 0, 0, 0)
            tabs_placeholder = QWidget(host)
            tabs_placeholder.setMinimumHeight(220)
            host_layout.addWidget(tabs_placeholder, 1)
            host_layout.addWidget(QStatusBar(host))

            bar = FavoritesStatusBar(storage, host)
            host_layout.addWidget(bar)

            class ControllerStub:
                refresh_count = 0

                def refresh_home_pages(self):
                    self.refresh_count += 1

            controller = ControllerStub()

            def refresh_favorite_surfaces():
                controller.refresh_home_pages()
                bar.refresh()

            bar.changed.connect(refresh_favorite_surfaces)
            host.resize(560, 300)
            host.show()
            self.app.processEvents()

            self.assertTrue(bar.isVisible())
            self.assertEqual(
                len(bar._content.findChildren(QWidget, "favoriteStatusItem")),
                bar.MAX_VISIBLE_FAVORITES,
            )
            self.assertGreater(bar.horizontalScrollBar().maximum(), 0)

            bar.horizontalScrollBar().setValue(bar.horizontalScrollBar().maximum())
            self.app.processEvents()
            visible_items = [
                item
                for item in bar._content.findChildren(
                    QWidget,
                    "favoriteStatusItem",
                )
                if self._is_in_viewport(
                    item.findChild(QToolButton, "favoriteStatusOpenButton"),
                    bar,
                )
            ]
            self.assertTrue(visible_items, "Não há favorito visível antes da edição.")
            item = visible_items[-1]
            options_button = item.findChild(
                QToolButton,
                "favoriteStatusOptionsButton",
            )
            self.assertIsNotNone(options_button)
            edited_url = str(item.property("favoriteUrl"))
            edit_action = options_button.menu().actions()[0]

            with patch(
                "_APP_.favorites_bar.QInputDialog.getText",
                side_effect=[
                    ("A atualizado", True),
                    ("B atualizado", True),
                ],
            ) as edit_dialog:
                edit_action.trigger()
                QApplication.sendPostedEvents(
                    None,
                    QEvent.Type.DeferredDelete,
                )
                self.app.processEvents()
                edit_action.trigger()
                QApplication.sendPostedEvents(
                    None,
                    QEvent.Type.DeferredDelete,
                )
                self.app.processEvents()

            self.assertTrue(bar.isVisible())
            self.assertTrue(bar.viewport().isVisible())
            self.assertEqual(controller.refresh_count, 2)
            self.assertGreaterEqual(bar.height(), 24)
            self.assertEqual(bar.horizontalScrollBar().value(), 0)
            self.assertIs(bar._favorite_items_by_url[edited_url], item)
            self.assertEqual(edit_dialog.call_args_list[1].args[-1], "A atualizado")
            self.assertEqual(
                len(bar._content.findChildren(QWidget, "favoriteStatusItem")),
                bar.MAX_VISIBLE_FAVORITES,
            )
            self.assertEqual(
                item.findChild(
                    QToolButton,
                    "favoriteStatusOpenButton",
                ).text(),
                "B atualizado",
            )
            visible_open_buttons = [
                button
                for button in bar._content.findChildren(
                    QToolButton,
                    "favoriteStatusOpenButton",
                )
                if self._is_in_viewport(button, bar)
            ]
            self.assertTrue(
                visible_open_buttons,
                "A faixa atualizou, mas nenhum botão de favorito está visível.",
            )

            saved = storage.get_favorites()
            self.assertEqual(len(saved), len(urls))
            self.assertIn(
                "B atualizado",
                {favorite["title"] for favorite in saved},
            )
            self.assertEqual(
                {favorite["url"] for favorite in saved},
                set(urls),
            )
            host.close()
            storage.close()


if __name__ == "__main__":
    unittest.main()
