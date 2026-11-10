"""Prévia local, somente leitura, de arquivos abertos pelo Explorador."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QImageReader, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    from PySide6.QtMultimediaWidgets import QVideoWidget
except ImportError:
    QAudioOutput = None
    QMediaPlayer = None
    QVideoWidget = None

try:
    from PySide6.QtPdf import QPdfDocument
    from PySide6.QtPdfWidgets import QPdfView
except ImportError:
    QPdfDocument = None
    QPdfView = None

from _SERVICOS_.explorer_filesystem import (
    ExplorerError,
    resolve_file_inside_root,
)
from _SERVICOS_.file_preview import (
    FilePreviewError,
    classify_preview_file,
    read_text_preview,
)


MAX_IMAGE_PREVIEW_BYTES = 80 * 1024 * 1024
MAX_IMAGE_PIXELS = 150_000_000
MAX_IMAGE_EDGE = 4096
MAX_COMPACT_TEXT_PREVIEW_BYTES = 64 * 1024
MAX_COMPACT_IMAGE_EDGE = 640
MAX_PDF_PREVIEW_BYTES = 100 * 1024 * 1024


class FilePreviewTab(QWidget):
    """Mostra arquivos locais em uma aba sem editar nem executar seu conteúdo."""

    def __init__(
        self,
        root_path: str,
        relative_path: str,
        texts: dict[str, str],
        parent=None,
        *,
        compact: bool = False,
    ):
        super().__init__(parent)
        self.root_path = root_path
        self.relative_path = relative_path
        self.texts = texts
        self.compact = bool(compact)
        self.file_path: Path | None = None
        self._player = None
        self._audio_output = None
        self._pdf_document = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        title = QLabel(Path(relative_path).name, self)
        title.setObjectName("filePreviewTitle")
        layout.addWidget(title)

        path_label = QLabel(relative_path, self)
        path_label.setObjectName("filePreviewPath")
        path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        path_label.setWordWrap(True)
        layout.addWidget(path_label)

        self.content = QWidget(self)
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.content, 1)

        self._open_file()

    def _open_file(self):
        try:
            self.file_path = resolve_file_inside_root(
                self.root_path,
                self.relative_path,
            )
            file_kind = classify_preview_file(self.file_path)
            if self.compact:
                self._open_compact(file_kind)
                return
            if file_kind == "text":
                self._open_text()
            elif file_kind == "image":
                self._open_image()
            elif file_kind == "audio":
                self._open_media(video=False)
            elif file_kind == "video":
                self._open_media(video=True)
            elif file_kind == "pdf":
                self._open_pdf()
            else:
                self._show_message(
                    self.texts["file_preview_unsupported"].format(
                        name=self.file_path.name
                    )
                )
        except (ExplorerError, FilePreviewError, OSError) as error:
            self._show_message(
                self.texts["file_preview_error"].format(error=str(error))
            )

    def _open_compact(self, file_kind: str):
        if file_kind == "text":
            self._open_text(compact=True)
            return
        if file_kind == "image":
            self._open_image(compact=True)
            return
        message_key = {
            "audio": "file_preview_compact_audio",
            "video": "file_preview_compact_video",
            "pdf": "file_preview_compact_pdf",
        }.get(file_kind)
        if message_key is not None:
            self._show_message(self.texts[message_key])
            return
        self._show_message(
            self.texts["file_preview_unsupported"].format(
                name=self.file_path.name
            )
        )

    def _show_message(self, message: str):
        label = QLabel(message, self.content)
        label.setObjectName("filePreviewMessage")
        label.setWordWrap(True)
        self.content_layout.addWidget(
            label,
            1,
            Qt.AlignmentFlag.AlignCenter,
        )

    def _open_text(self, *, compact: bool = False):
        if compact:
            text, truncated = read_text_preview(
                self.file_path,
                max_bytes=MAX_COMPACT_TEXT_PREVIEW_BYTES,
            )
        else:
            text, truncated = read_text_preview(self.file_path)
        viewer = QPlainTextEdit(self.content)
        viewer.setObjectName("filePreviewText")
        viewer.setReadOnly(True)
        viewer.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.WidgetWidth
            if compact
            else QPlainTextEdit.LineWrapMode.NoWrap
        )
        viewer.setPlainText(text)
        self.content_layout.addWidget(viewer, 1)
        if truncated:
            message_key = (
                "file_preview_compact_text_truncated"
                if compact
                else "file_preview_text_truncated"
            )
            self._show_message(self.texts[message_key])

    def _open_image(self, *, compact: bool = False):
        if self.file_path.stat().st_size > MAX_IMAGE_PREVIEW_BYTES:
            self._show_message(self.texts["file_preview_image_too_large"])
            return

        reader = QImageReader(str(self.file_path))
        reader.setAutoTransform(True)
        size = reader.size()
        if size.isValid():
            if size.width() * size.height() > MAX_IMAGE_PIXELS:
                self._show_message(self.texts["file_preview_image_too_large"])
                return
            max_edge = (
                MAX_COMPACT_IMAGE_EDGE if compact else MAX_IMAGE_EDGE
            )
            if max(size.width(), size.height()) > max_edge:
                from PySide6.QtCore import QSize

                reader.setScaledSize(
                    size.scaled(
                        max_edge,
                        max_edge,
                        Qt.AspectRatioMode.KeepAspectRatio,
                    )
                )

        image = reader.read()
        if image.isNull():
            self._show_message(
                self.texts["file_preview_error"].format(
                    error=reader.errorString()
                    or self.texts["file_preview_image_unreadable"]
                )
            )
            return

        label = QLabel(self.content)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setPixmap(QPixmap.fromImage(image))
        scroll = QScrollArea(self.content)
        scroll.setWidgetResizable(True)
        scroll.setWidget(label)
        self.content_layout.addWidget(scroll, 1)

    def _open_pdf(self):
        if self.file_path.stat().st_size > MAX_PDF_PREVIEW_BYTES:
            self._show_message(self.texts["file_preview_pdf_too_large"])
            return
        if QPdfDocument is None or QPdfView is None:
            self._show_message(self.texts["file_preview_pdf_unavailable"])
            return

        document = QPdfDocument(self)
        result = document.load(str(self.file_path))
        if result != QPdfDocument.Error.None_:
            self._show_message(self.texts["file_preview_pdf_unreadable"])
            return

        viewer = QPdfView(self.content)
        viewer.setDocument(document)
        viewer.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self._pdf_document = document
        self.content_layout.addWidget(viewer, 1)

    def _open_media(self, *, video: bool):
        if QMediaPlayer is None or QAudioOutput is None:
            self._show_message(self.texts["file_preview_media_unavailable"])
            return
        if video and QVideoWidget is None:
            self._show_message(self.texts["file_preview_video_unavailable"])
            return

        media_layout = QVBoxLayout()
        if video:
            video_widget = QVideoWidget(self.content)
            video_widget.setMinimumHeight(220)
            media_layout.addWidget(video_widget, 1)

        controls = QHBoxLayout()
        self.play_button = QPushButton(
            self.texts["file_preview_play"],
            self.content,
        )
        self.play_button.clicked.connect(self._toggle_playback)
        controls.addWidget(self.play_button)

        self.position_label = QLabel("00:00 / 00:00", self.content)
        controls.addWidget(self.position_label)
        self.position_slider = QSlider(
            Qt.Orientation.Horizontal,
            self.content,
        )
        self.position_slider.setRange(0, 0)
        self.position_slider.sliderMoved.connect(self._seek)
        controls.addWidget(self.position_slider, 1)
        media_layout.addLayout(controls)

        self.media_status = QLabel(
            self.texts["file_preview_media_ready"],
            self.content,
        )
        self.media_status.setWordWrap(True)
        media_layout.addWidget(self.media_status)
        self.content_layout.addLayout(media_layout, 1)

        self._audio_output = QAudioOutput(self)
        self._audio_output.setVolume(0.8)
        self._player = QMediaPlayer(self)
        self._player.setAudioOutput(self._audio_output)
        if video:
            self._player.setVideoOutput(video_widget)
        self._player.positionChanged.connect(self._update_position)
        self._player.durationChanged.connect(self._update_duration)
        self._player.playbackStateChanged.connect(
            self._update_play_button
        )
        self._player.errorOccurred.connect(self._on_media_error)
        self._player.setSource(QUrl.fromLocalFile(str(self.file_path)))

    def _toggle_playback(self):
        if self._player is None or QMediaPlayer is None:
            return
        if (
            self._player.playbackState()
            == QMediaPlayer.PlaybackState.PlayingState
        ):
            self._player.pause()
        else:
            self._player.play()

    def _update_play_button(self, state):
        if QMediaPlayer is None:
            return
        label = (
            self.texts["file_preview_pause"]
            if state == QMediaPlayer.PlaybackState.PlayingState
            else self.texts["file_preview_play"]
        )
        self.play_button.setText(label)

    def _seek(self, position: int):
        if self._player is not None:
            self._player.setPosition(position)

    def _update_position(self, position: int):
        if self._player is None:
            return
        self.position_slider.setValue(position)
        self._update_time_label(position, self._player.duration())

    def _update_duration(self, duration: int):
        self.position_slider.setRange(0, max(0, duration))
        self._update_time_label(self._player.position(), duration)

    def _update_time_label(self, position: int, duration: int):
        self.position_label.setText(
            f"{self._format_time(position)} / {self._format_time(duration)}"
        )

    @staticmethod
    def _format_time(milliseconds: int) -> str:
        total_seconds = max(0, milliseconds // 1000)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours}:{minutes:02}:{seconds:02}"
        return f"{minutes:02}:{seconds:02}"

    def _on_media_error(self, _error, message: str):
        if message and self.media_status is not None:
            self.media_status.setText(
                self.texts["file_preview_media_error"].format(error=message)
            )

    def shutdown(self):
        if self._player is not None:
            self._player.stop()
            self._player.setSource(QUrl())
            self._player = None
        self._audio_output = None
        if self._pdf_document is not None:
            self._pdf_document.close()
            self._pdf_document = None

    def closeEvent(self, event):
        self.shutdown()
        super().closeEvent(event)
