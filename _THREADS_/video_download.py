"""Execução assíncrona da consulta e do download de vídeos."""

from __future__ import annotations

from PySide6.QtCore import Signal

from _CONFIGURA_ import TEXTO_UI
from _THREADS_.thread_segura import ThreadSegura
from _SERVICOS_.video_download import VideoDownloadService


class VideoDownloadWorker(ThreadSegura):
    resultReady = Signal(str, object)
    progressChanged = Signal(int, str)
    failed = Signal(str)

    def __init__(
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
        super().__init__(nome=f"video_download_{operation}_{id(self)}")
        self.operation = operation
        self.url = url
        self.destination = destination
        self.resolution = resolution
        self.video_format = video_format
        self.audio_format = audio_format
        self.tasks = tasks or {}
        self.organize_by_video = organize_by_video
        self.service = VideoDownloadService()

    def run(self):
        try:
            if self.operation == "analyze":
                result = self.service.obter_informacoes(self.url)
            elif self.operation == "download":
                result = self.service.baixar_video(
                    self.url,
                    self.destination,
                    resolucao_max=self.resolution,
                    formato=self.video_format,
                    progresso=self.progressChanged.emit,
                )
            elif self.operation == "process":
                result = self.service.processar_midia(
                    self.url,
                    self.destination,
                    **self.tasks,
                    resolucao_max=self.resolution,
                    formato_video=self.video_format,
                    formato_audio=self.audio_format,
                    organizar_por_video=self.organize_by_video,
                    progresso=self.progressChanged.emit,
                )
            else:
                raise ValueError(
                    TEXTO_UI["video_download_invalid_operation"].format(
                        operation=self.operation
                    )
                )
            self.resultReady.emit(self.operation, result)
        except Exception as error:
            self.failed.emit(str(error))
