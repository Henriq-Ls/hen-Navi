"""Monitor compartilhado e leitura compacta de recursos na barra de status."""

from PySide6.QtCore import QObject, QTimer, Qt, Signal
from PySide6.QtWidgets import QLabel

from _CONFIGURA_ import TEXTO_UI
from _SERVICOS_.performance_diagnostics import (
    ProcessMetricsUnavailable,
    ProcessTreeSampler,
)


class PerformanceMonitor(QObject):
    """Amostra o processo do app e filhos a cada poucos segundos."""

    updated = Signal(object)
    SAMPLE_INTERVAL_MS = 3000

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sampler = None
        self._started = False
        self._snapshot = {
            "cpu_percent": None,
            "memory_bytes": None,
            "process_count": None,
            "partial": False,
            "error": "",
        }
        self._sample_timer = QTimer(self)
        self._sample_timer.setInterval(self.SAMPLE_INTERVAL_MS)
        self._sample_timer.timeout.connect(self.refresh)

    @property
    def snapshot(self) -> dict:
        return dict(self._snapshot)

    def start(self):
        if self._started:
            return
        self._started = True
        self._sample_timer.start()
        QTimer.singleShot(0, self.refresh)

    def stop(self):
        self._sample_timer.stop()

    def refresh(self):
        if self._snapshot["error"]:
            return
        try:
            if self._sampler is None:
                self._sampler = ProcessTreeSampler()
            self._snapshot = self._sampler.sample()
            self._snapshot["error"] = ""
        except ProcessMetricsUnavailable as error:
            self._snapshot = {
                "cpu_percent": None,
                "memory_bytes": None,
                "process_count": None,
                "partial": False,
                "error": str(error),
            }
            self._sample_timer.stop()
        self.updated.emit(self.snapshot)


class PerformanceStatusReadout(QLabel):
    """Exibe CPU/RAM no lado direito da barra de status."""

    def __init__(self, monitor: PerformanceMonitor, parent=None):
        super().__init__(parent)
        self.setObjectName("performanceStatusReadout")
        self.setAccessibleName(TEXTO_UI["performance_panel_title"])
        self.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.setMinimumWidth(190)
        self.setContentsMargins(6, 0, 8, 0)
        self.setText(TEXTO_UI["performance_status_waiting"])
        self.setToolTip(TEXTO_UI["performance_status_tooltip"])
        monitor.updated.connect(self._update_snapshot)
        self._update_snapshot(monitor.snapshot)

    def _update_snapshot(self, snapshot: dict):
        error = str(snapshot.get("error") or "")
        if error:
            self.setText(TEXTO_UI["performance_status_unavailable"])
            self.setToolTip(
                TEXTO_UI["performance_dependency_missing"]
                if "psutil" in error.lower()
                else TEXTO_UI["performance_metrics_unavailable"]
            )
            return

        cpu_percent = snapshot.get("cpu_percent")
        memory_bytes = snapshot.get("memory_bytes")
        cpu_text = "—" if cpu_percent is None else f"{cpu_percent:.1f}%"
        memory_text = (
            "—"
            if memory_bytes is None
            else f"{memory_bytes / (1024 * 1024):.0f} MiB"
        )
        self.setText(
            TEXTO_UI["performance_status_format"].format(
                cpu=cpu_text,
                memory=memory_text,
            )
        )
        self.setToolTip(TEXTO_UI["performance_status_tooltip"])
