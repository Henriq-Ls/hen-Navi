"""Captura assíncrona de páginas e gravação de imagens/PDF."""

from __future__ import annotations

import json
import math
from pathlib import Path

from PySide6.QtCore import QObject, QRect, QTimer, Qt, Signal
from PySide6.QtGui import QImage, QPainter

from _THREADS_.thread_segura import ThreadSegura
from capture_utils import capture_bounds, capture_slices


class _ImageSaveThread(ThreadSegura):
    imageSaved = Signal(QImage, str, bool)
    failed = Signal(str)

    def __init__(
        self,
        tiles: list[tuple[int, int, QImage]],
        path: str,
        *,
        width: int,
        height: int,
        viewport_width: int,
        viewport_height: int,
        clipped: bool,
        name: str,
    ):
        super().__init__(nome=name)
        self.tiles = tiles
        self.path = path
        self.width = width
        self.height = height
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.clipped = clipped

    def run(self):
        try:
            image = self._compose()
            if not image.save(self.path, "PNG"):
                raise OSError(f"Não foi possível gravar o arquivo: {self.path}")
            self.imageSaved.emit(image, self.path, self.clipped)
        except Exception as error:
            self.failed.emit(str(error))

    def _compose(self) -> QImage:
        if not self.tiles or self.viewport_width <= 0 or self.viewport_height <= 0:
            raise ValueError("A captura não contém fatias válidas.")

        first_image = self.tiles[0][2]
        scale_x = first_image.width() / self.viewport_width
        scale_y = first_image.height() / self.viewport_height
        pixel_width = max(1, math.ceil(self.width * scale_x))
        pixel_height = max(1, math.ceil(self.height * scale_y))
        result = QImage(
            pixel_width,
            pixel_height,
            QImage.Format.Format_ARGB32,
        )
        result.fill(Qt.GlobalColor.white)

        painter = QPainter(result)
        try:
            for x, y, tile in self.tiles:
                destination_x = round(x * scale_x)
                destination_y = round(y * scale_y)
                draw_width = min(tile.width(), pixel_width - destination_x)
                draw_height = min(tile.height(), pixel_height - destination_y)
                if draw_width <= 0 or draw_height <= 0:
                    continue
                painter.drawImage(
                    QRect(destination_x, destination_y, draw_width, draw_height),
                    tile,
                    QRect(0, 0, draw_width, draw_height),
                )
        finally:
            painter.end()
        return result


class CaptureManager(QObject):
    """Coordena capturas sem bloquear a interface."""

    imageSaved = Signal(str, bool)
    pdfSaved = Signal(str)
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state: dict | None = None
        self._pending_pdf: tuple[object, str] | None = None
        self._workers: list[_ImageSaveThread] = []
        self._worker_number = 0

    @property
    def busy(self) -> bool:
        return bool(
            self._state
            or self._pending_pdf
            or any(worker.isRunning() for worker in self._workers)
        )

    def capture_visible(self, view, path: str) -> None:
        if self.busy:
            raise RuntimeError("Já existe uma captura em andamento.")
        image = view.grab().toImage()
        if image.isNull():
            raise ValueError("A janela não produziu uma imagem.")
        image.setDevicePixelRatio(1.0)
        self._queue_image_save(
            [(0, 0, image)],
            path,
            width=image.width(),
            height=image.height(),
            viewport_width=image.width(),
            viewport_height=image.height(),
            clipped=False,
        )

    def capture_full_page(
        self,
        view,
        path: str,
        *,
        max_width: int,
        max_height: int,
        settle_interval_ms: int,
    ) -> None:
        if self.busy:
            raise RuntimeError("Já existe uma captura em andamento.")
        self._state = {
            "view": view,
            "page": view.page(),
            "path": path,
            "max_width": max_width,
            "max_height": max_height,
            "settle_interval_ms": settle_interval_ms,
            "tiles": [],
            "positions": (),
            "index": 0,
        }
        script = """
(() => {
  const root = document.documentElement;
  const body = document.body;
  return JSON.stringify({
    width: Math.max(root.scrollWidth, body ? body.scrollWidth : 0, window.innerWidth),
    height: Math.max(root.scrollHeight, body ? body.scrollHeight : 0, window.innerHeight),
    viewportWidth: window.innerWidth,
    viewportHeight: window.innerHeight,
    scrollX: window.scrollX,
    scrollY: window.scrollY
  });
})()
"""
        try:
            self._state["page"].runJavaScript(script, self._on_page_metrics)
        except RuntimeError as error:
            self._fail(str(error))

    def print_pdf(self, page, path: str) -> None:
        if self.busy:
            raise RuntimeError("Já existe uma captura em andamento.")
        self._pending_pdf = (page, path)
        page.pdfPrintingFinished.connect(self._on_pdf_printing_finished)
        try:
            page.printToPdf(path)
        except RuntimeError:
            self._disconnect_pdf_signal(page)
            self._pending_pdf = None
            raise

    def _on_page_metrics(self, value):
        state = self._state
        if state is None:
            return
        try:
            metrics = self._decode_json(value)
            view = state["view"]
            viewport_width = int(metrics["viewportWidth"])
            viewport_height = int(metrics["viewportHeight"])
            width, height, clipped = capture_bounds(
                int(metrics["width"]),
                int(metrics["height"]),
                state["max_width"],
                state["max_height"],
            )
            if viewport_width <= 0 or viewport_height <= 0:
                raise ValueError("A página não possui uma área visível válida.")
            state.update(
                {
                    "width": width,
                    "height": height,
                    "clipped": clipped,
                    "viewport_width": viewport_width,
                    "viewport_height": viewport_height,
                    "original_x": int(metrics.get("scrollX", 0)),
                    "original_y": int(metrics.get("scrollY", 0)),
                    "positions": capture_slices(
                        width,
                        height,
                        viewport_width,
                        viewport_height,
                    ),
                    "scroll_x": 0,
                    "scroll_y": 0,
                }
            )
            self._capture_next_slice()
        except (KeyError, TypeError, ValueError, RuntimeError) as error:
            self._fail(str(error))

    def _capture_next_slice(self):
        state = self._state
        if state is None:
            return
        positions = state["positions"]
        if state["index"] >= len(positions):
            self._finish_full_page()
            return

        x, y = positions[state["index"]]
        script = (
            "window.scrollTo("
            f"{x}, {y}); "
            "JSON.stringify([window.scrollX, window.scrollY])"
        )
        try:
            state["page"].runJavaScript(script, self._on_scroll_position)
        except RuntimeError as error:
            self._fail(str(error))

    def _on_scroll_position(self, value):
        if self._state is None:
            return
        try:
            scroll_x, scroll_y = self._decode_json(value)
            self._state["scroll_x"] = int(scroll_x)
            self._state["scroll_y"] = int(scroll_y)
            QTimer.singleShot(
                self._state["settle_interval_ms"],
                self._capture_current_slice,
            )
        except (TypeError, ValueError, RuntimeError) as error:
            self._fail(str(error))

    def _capture_current_slice(self):
        state = self._state
        if state is None:
            return
        try:
            tile = state["view"].viewport().grab().toImage()
            if tile.isNull():
                raise ValueError("Não foi possível capturar uma fatia da página.")
            tile.setDevicePixelRatio(1.0)
            state["tiles"].append(
                (state["scroll_x"], state["scroll_y"], tile)
            )
            state["index"] += 1
            self._capture_next_slice()
        except (AttributeError, RuntimeError, ValueError) as error:
            self._fail(str(error))

    def _finish_full_page(self):
        state = self._state
        if state is None:
            return
        try:
            state["page"].runJavaScript(
                f"window.scrollTo({state['original_x']}, {state['original_y']})"
            )
        except RuntimeError:
            pass
        self._queue_image_save(
            state["tiles"],
            state["path"],
            width=state["width"],
            height=state["height"],
            viewport_width=state["viewport_width"],
            viewport_height=state["viewport_height"],
            clipped=state["clipped"],
        )
        self._state = None

    def _queue_image_save(
        self,
        tiles,
        path,
        *,
        width,
        height,
        viewport_width,
        viewport_height,
        clipped,
    ):
        self._worker_number += 1
        worker = _ImageSaveThread(
            tiles,
            path,
            width=width,
            height=height,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            clipped=clipped,
            name=f"captura_imagem_{self._worker_number}",
        )
        self._workers.append(worker)
        worker.imageSaved.connect(self._on_image_saved)
        worker.failed.connect(self.failed.emit)
        worker.finished.connect(self._on_worker_finished)
        worker.start()

    def _on_image_saved(self, image: QImage, path: str, clipped: bool):
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setImage(image)
        self.imageSaved.emit(path, clipped)

    def _on_pdf_printing_finished(self, path: str, success: bool):
        pending = self._pending_pdf
        if pending is None:
            return
        page, expected_path = pending
        self._disconnect_pdf_signal(page)
        self._pending_pdf = None
        if success:
            self.pdfSaved.emit(expected_path)
        else:
            self.failed.emit(f"PDF: {path}")

    def _disconnect_pdf_signal(self, page):
        try:
            page.pdfPrintingFinished.disconnect(self._on_pdf_printing_finished)
        except (RuntimeError, TypeError):
            pass

    def _on_worker_finished(self):
        worker = self.sender()
        if worker in self._workers:
            self._workers.remove(worker)

    def _fail(self, message: str):
        state = self._state
        if state:
            try:
                state["page"].runJavaScript(
                    f"window.scrollTo({state['original_x']}, {state['original_y']})"
                )
            except (KeyError, RuntimeError):
                pass
        self._state = None
        self.failed.emit(message)

    @staticmethod
    def _decode_json(value):
        if isinstance(value, str):
            return json.loads(value)
        if isinstance(value, (dict, list)):
            return value
        raise ValueError("A página retornou medidas inválidas.")
