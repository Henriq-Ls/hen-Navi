"""Painel lateral para processar mídia da aba atual."""

from __future__ import annotations

from pathlib import Path

from _CONFIGURA_ import (
    ALTURA_PREVIEW_TRANSCRICAO_DOWNLOAD,
    ATRASO_ANALISE_DOWNLOAD_VIDEO_MS,
    FORMATOS_AUDIO_DOWNLOAD,
    FORMATOS_VIDEO_DOWNLOAD,
    FORMATO_AUDIO_DOWNLOAD_PADRAO,
    FORMATO_VIDEO_DOWNLOAD_PADRAO,
    LARGURA_DOCK_DOWNLOAD_VIDEO,
    ORGANIZAR_DOWNLOAD_POR_VIDEO_PADRAO,
    ROTULO_QUALIDADE_AUTOMATICA,
    TEXTO_UI,
)
from PySide6.QtCore import QSize, Qt, QStandardPaths, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDockWidget,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from _THREADS_.video_download import VideoDownloadWorker
from _ULTILIDADES_.icones import ico_abrir, ico_video_download
from _SERVICOS_.video_download import VideoDownloadService


class VideoDownloadDock(QDockWidget):
    """Configura downloads de vídeo/áudio e geração de transcrições e SRT."""

    def __init__(self, parent=None):
        super().__init__(TEXTO_UI["video_download_title"], parent)
        self.setObjectName("videoDownloadDock")
        self.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        self.setMinimumWidth(LARGURA_DOCK_DOWNLOAD_VIDEO)
        self._worker: VideoDownloadWorker | None = None
        self._operation = ""
        self._operation_url = ""
        self._analyzed_url = ""
        self._video_info: dict | None = None

        wrapper = QWidget(self)
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(wrapper)
        scroll.setWidgetResizable(True)
        content = QWidget(scroll)
        layout = QVBoxLayout(content)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.url_field = QLineEdit(content)
        self.url_field.setPlaceholderText(TEXTO_UI["video_download_url_placeholder"])
        self.url_field.textChanged.connect(self._on_url_edited)
        layout.addWidget(QLabel(TEXTO_UI["video_download_url_label"], content))
        url_row = QHBoxLayout()
        url_row.addWidget(self.url_field, 1)
        self.analyze_button = QPushButton(
            TEXTO_UI["video_download_analyze"], content
        )
        self.analyze_button.clicked.connect(
            lambda: self.analyze_link(force=True)
        )
        url_row.addWidget(self.analyze_button)
        layout.addLayout(url_row)

        self.info_label = QLabel(TEXTO_UI["video_download_info_waiting"], content)
        self.info_label.setWordWrap(True)
        self.info_label.setTextFormat(Qt.TextFormat.PlainText)
        self.info_label.setObjectName("videoDownloadInfo")
        layout.addWidget(self.info_label)

        tasks_group = QGroupBox(TEXTO_UI["video_download_tasks_title"], content)
        tasks_layout = QVBoxLayout(tasks_group)
        self.video_task = QCheckBox(TEXTO_UI["video_download_task_video"], tasks_group)
        self.video_task.setChecked(True)
        self.audio_task = QCheckBox(TEXTO_UI["video_download_task_audio"], tasks_group)
        self.transcription_task = QCheckBox(
            TEXTO_UI["video_download_task_transcribe"],
            tasks_group,
        )
        self.srt_task = QCheckBox(
            TEXTO_UI["video_download_task_srt"],
            tasks_group,
        )
        for checkbox in (
            self.video_task,
            self.audio_task,
            self.transcription_task,
            self.srt_task,
        ):
            checkbox.toggled.connect(self._update_task_options)
            tasks_layout.addWidget(checkbox)
        layout.addWidget(tasks_group)

        formats_group = QGroupBox(
            TEXTO_UI["video_download_format_section"],
            content,
        )
        formats = QFormLayout(formats_group)
        self.quality_combo = QComboBox(formats_group)
        self.quality_combo.addItem(ROTULO_QUALIDADE_AUTOMATICA, None)
        self.video_format_combo = QComboBox(formats_group)
        for formato in FORMATOS_VIDEO_DOWNLOAD:
            self.video_format_combo.addItem(formato.upper(), formato)
        video_index = self.video_format_combo.findData(
            FORMATO_VIDEO_DOWNLOAD_PADRAO
        )
        if video_index >= 0:
            self.video_format_combo.setCurrentIndex(video_index)
        self.audio_format_combo = QComboBox(formats_group)
        for formato in FORMATOS_AUDIO_DOWNLOAD:
            self.audio_format_combo.addItem(formato.upper(), formato)
        audio_index = self.audio_format_combo.findData(
            FORMATO_AUDIO_DOWNLOAD_PADRAO
        )
        if audio_index >= 0:
            self.audio_format_combo.setCurrentIndex(audio_index)
        formats.addRow(
            TEXTO_UI["video_download_quality_label"],
            self.quality_combo,
        )
        formats.addRow(
            TEXTO_UI["video_download_format_label"],
            self.video_format_combo,
        )
        formats.addRow(
            TEXTO_UI["video_download_audio_format_label"],
            self.audio_format_combo,
        )
        layout.addWidget(formats_group)

        downloads_dir = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DownloadLocation
        ) or str(Path.home())
        self.destination_field = QLineEdit(downloads_dir, content)
        self.destination_field.setPlaceholderText(
            TEXTO_UI["video_download_destination_placeholder"]
        )
        self.destination_button = QPushButton(
            ico_abrir(),
            TEXTO_UI["video_download_choose_folder"],
            content,
        )
        self.destination_button.setIconSize(QSize(16, 16))
        self.destination_button.clicked.connect(self.choose_destination)
        destination_row = QHBoxLayout()
        destination_row.addWidget(self.destination_field, 1)
        destination_row.addWidget(self.destination_button)
        layout.addWidget(QLabel(TEXTO_UI["video_download_destination_label"], content))
        layout.addLayout(destination_row)

        self.organize_checkbox = QCheckBox(
            TEXTO_UI["video_download_organize_label"],
            content,
        )
        self.organize_checkbox.setChecked(
            ORGANIZAR_DOWNLOAD_POR_VIDEO_PADRAO
        )
        self.organize_checkbox.setToolTip(
            TEXTO_UI["video_download_organize_tooltip"]
        )
        layout.addWidget(self.organize_checkbox)

        self.process_button = QPushButton(
            ico_video_download(),
            TEXTO_UI["video_download_start"],
            content,
        )
        self.process_button.clicked.connect(self.process_selected_tasks)
        layout.addWidget(self.process_button)

        self.progress_bar = QProgressBar(content)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel(TEXTO_UI["video_download_status_ready"], content)
        self.status_label.setWordWrap(True)
        self.status_label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status_label)

        layout.addWidget(QLabel(TEXTO_UI["video_download_transcription_title"], content))
        self.transcription_preview = QPlainTextEdit(content)
        self.transcription_preview.setReadOnly(True)
        self.transcription_preview.setPlaceholderText(
            TEXTO_UI["video_download_transcription_placeholder"]
        )
        self.transcription_preview.setMaximumHeight(
            ALTURA_PREVIEW_TRANSCRICAO_DOWNLOAD
        )
        layout.addWidget(self.transcription_preview)

        scroll.setWidget(content)
        wrapper_layout.addWidget(scroll)
        self.setWidget(wrapper)

        self._analyze_timer = QTimer(self)
        self._analyze_timer.setSingleShot(True)
        self._analyze_timer.setInterval(ATRASO_ANALISE_DOWNLOAD_VIDEO_MS)
        self._analyze_timer.timeout.connect(self.analyze_link)
        self._update_task_options()

    @property
    def task_active(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def set_source_url(self, url: str) -> None:
        endereco = (url or "").strip()
        if endereco == self.url_field.text().strip():
            return
        self.url_field.setText(endereco)
        if self.isVisible():
            self._analyze_timer.start()

    def _on_url_edited(self, *_):
        if self._analyzed_url and self.url_field.text().strip() != self._analyzed_url:
            self._clear_video_info()

    def _clear_video_info(self):
        self._video_info = None
        self._analyzed_url = ""
        self.quality_combo.clear()
        self.quality_combo.addItem(ROTULO_QUALIDADE_AUTOMATICA, None)
        self.info_label.setText(TEXTO_UI["video_download_info_waiting"])
        self._update_task_options()

    def analyze_link(self, force: bool = False):
        if self.task_active:
            return
        url = self.url_field.text().strip()
        try:
            validated_url = VideoDownloadService.validar_url(url)
        except ValueError as error:
            self.status_label.setText(str(error))
            return
        if not force and self._video_info and self._analyzed_url == validated_url:
            return
        self.transcription_preview.clear()
        self._start_worker("analyze", validated_url)

    def process_selected_tasks(self, *_):
        if self.task_active:
            self.status_label.setText(TEXTO_UI["video_download_status_busy"])
            return
        tasks = {
            "baixar_video": self.video_task.isChecked(),
            "baixar_audio": self.audio_task.isChecked(),
            "transcrever": self.transcription_task.isChecked(),
            "criar_srt": self.srt_task.isChecked(),
        }
        if not any(tasks.values()):
            self.status_label.setText(TEXTO_UI["video_download_status_choose_task"])
            return
        url = self.url_field.text().strip()
        if not self._video_info or self._analyzed_url != url:
            self.status_label.setText(
                TEXTO_UI["video_download_status_analyze_first"]
            )
            return
        destination = self.destination_field.text().strip()
        if not destination:
            destination = str(Path.home() / "Downloads")
        self.transcription_preview.clear()
        self._start_worker(
            "process",
            url,
            destination=destination,
            resolution=self.quality_combo.currentData(),
            video_format=str(self.video_format_combo.currentData()),
            audio_format=str(self.audio_format_combo.currentData()),
            tasks=tasks,
            organize_by_video=self.organize_checkbox.isChecked(),
        )

    def _start_worker(
        self,
        operation: str,
        url: str,
        *,
        destination: str = "",
        resolution: int | None = None,
        video_format: str = "",
        audio_format: str = "",
        tasks: dict | None = None,
        organize_by_video: bool = True,
    ):
        self._operation = operation
        self._operation_url = url
        self._set_busy(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.status_label.setText(
            TEXTO_UI["video_download_status_analyzing"]
            if operation == "analyze"
            else TEXTO_UI["video_download_status_downloading"]
        )
        worker = VideoDownloadWorker(
            operation,
            url,
            destination=destination,
            resolution=resolution,
            video_format=video_format,
            audio_format=audio_format,
            tasks=tasks,
            organize_by_video=organize_by_video,
        )
        self._worker = worker
        worker.resultReady.connect(self._on_worker_result)
        worker.progressChanged.connect(self._on_progress)
        worker.failed.connect(self._on_worker_failed)
        worker.finished.connect(self._on_worker_finished)
        worker.start()

    def _on_worker_result(self, operation: str, result: dict):
        if operation == "analyze":
            if self.url_field.text().strip() != self._operation_url:
                self.status_label.setText(
                    TEXTO_UI["video_download_status_analyze_first"]
                )
                if self.isVisible():
                    self._analyze_timer.start()
                return
            self._video_info = result
            self._analyzed_url = self._operation_url
            self._show_video_info(result)
            self.status_label.setText(TEXTO_UI["video_download_status_ready"])
            self._update_task_options()
        elif operation == "process":
            transcription = result.get("transcription") or {}
            if transcription.get("text"):
                self.transcription_preview.setPlainText(
                    str(transcription["text"])
                )
            self.status_label.setText(
                TEXTO_UI["video_download_status_complete"].format(
                    folder=result.get("folder", "")
                )
            )
            saved_paths = []
            if transcription.get("path"):
                saved_paths.append(
                    TEXTO_UI["video_download_transcription_saved"].format(
                        path=transcription["path"]
                    )
                )
            if transcription.get("srt_path"):
                saved_paths.append(
                    TEXTO_UI["video_download_transcription_srt_saved"].format(
                        path=transcription["srt_path"]
                    )
                )
            if saved_paths:
                self.status_label.setText(
                    self.status_label.text()
                    + "\n"
                    + "\n".join(saved_paths)
                )
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)

    def _show_video_info(self, info: dict):
        self.info_label.setText(
            TEXTO_UI["video_download_info_format"].format(
                title=info.get("title") or TEXTO_UI["video_download_not_reported"],
                uploader=info.get("uploader") or TEXTO_UI["video_download_not_reported"],
                duration=info.get("duration") or TEXTO_UI["video_download_not_reported"],
                resolution=info.get("resolution") or TEXTO_UI["video_download_not_reported"],
                format=info.get("format") or TEXTO_UI["video_download_not_reported"],
            )
        )
        self.quality_combo.clear()
        self.quality_combo.addItem(ROTULO_QUALIDADE_AUTOMATICA, None)
        heights = info.get("available_heights") or []
        for altura in heights:
            self.quality_combo.addItem(f"{altura}p", int(altura))
        if not heights:
            self.quality_combo.setItemText(
                0,
                f"{ROTULO_QUALIDADE_AUTOMATICA} "
                f"({TEXTO_UI['video_download_no_qualities']})",
            )

    def _on_progress(self, percent: int, message: str):
        if percent < 0:
            self.progress_bar.setRange(0, 0)
            self.status_label.setText(message)
            return
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)

    def _on_worker_failed(self, error: str):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.status_label.setText(
            TEXTO_UI["video_download_status_error"].format(error=error)
        )

    def _on_worker_finished(self):
        worker = self.sender()
        if worker is self._worker:
            self._worker = None
            self._operation = ""
            self._set_busy(False)

    def _set_busy(self, busy: bool):
        self.url_field.setEnabled(not busy)
        self.analyze_button.setEnabled(not busy)
        for checkbox in (
            self.video_task,
            self.audio_task,
            self.transcription_task,
            self.srt_task,
            self.organize_checkbox,
        ):
            checkbox.setEnabled(not busy)
        self.destination_field.setEnabled(not busy)
        self.destination_button.setEnabled(not busy)
        self._update_task_options(busy=busy)

    def _update_task_options(self, *_args, busy: bool | None = None):
        occupied = self.task_active if busy is None else busy
        video_selected = self.video_task.isChecked()
        audio_selected = self.audio_task.isChecked()
        self.quality_combo.setEnabled(not occupied and video_selected)
        self.video_format_combo.setEnabled(not occupied and video_selected)
        self.audio_format_combo.setEnabled(not occupied and audio_selected)
        self.process_button.setEnabled(
            not occupied
            and self._video_info is not None
            and self.url_field.text().strip() == self._analyzed_url
        )

    def choose_destination(self, *_):
        selected = QFileDialog.getExistingDirectory(
            self,
            TEXTO_UI["video_download_choose_folder_title"],
            self.destination_field.text().strip(),
        )
        if selected:
            self.destination_field.setText(selected)
