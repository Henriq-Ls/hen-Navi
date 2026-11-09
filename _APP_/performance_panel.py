"""Painel local para acompanhar recursos e tempos do hen-Nave."""

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from _CONFIGURA_ import TEXTO_UI
from _SERVICOS_.performance_diagnostics import performance_snapshot


class PerformancePanel(QWidget):
    """Apresenta métricas agregadas e tempos desta sessão."""

    def __init__(self, monitor, open_gpu_diagnostic, parent=None):
        super().__init__(parent)
        self.setObjectName("performancePanel")
        self.setWindowTitle(TEXTO_UI["performance_panel_title"])
        self._monitor = monitor
        self._open_gpu_diagnostic = open_gpu_diagnostic

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        description = QLabel(TEXTO_UI["performance_panel_description"], self)
        description.setWordWrap(True)
        layout.addWidget(description)

        resource_frame = QFrame(self)
        resource_frame.setObjectName("performanceResourceFrame")
        resource_layout = QFormLayout(resource_frame)
        resource_layout.setContentsMargins(10, 8, 10, 8)
        self.cpu_value = QLabel(TEXTO_UI["performance_cpu_waiting"], self)
        self.memory_value = QLabel("—", self)
        self.process_count_value = QLabel("—", self)
        resource_layout.addRow(
            TEXTO_UI["performance_cpu_label"],
            self.cpu_value,
        )
        resource_layout.addRow(
            TEXTO_UI["performance_memory_label"],
            self.memory_value,
        )
        resource_layout.addRow(
            TEXTO_UI["performance_processes_label"],
            self.process_count_value,
        )
        layout.addWidget(resource_frame)

        self.startup_label = QLabel("", self)
        self.startup_label.setWordWrap(True)
        layout.addWidget(self.startup_label)

        self.navigation_title = QLabel(
            TEXTO_UI["performance_navigation_title"],
            self,
        )
        self.navigation_title.setObjectName("performanceNavigationTitle")
        layout.addWidget(self.navigation_title)
        self.navigation_label = QLabel(
            TEXTO_UI["performance_navigation_empty"],
            self,
        )
        self.navigation_label.setWordWrap(True)
        layout.addWidget(self.navigation_label)

        self.gpu_button = QPushButton(
            TEXTO_UI["performance_gpu_open"],
            self,
        )
        self.gpu_button.clicked.connect(self._open_gpu_diagnostic)
        layout.addWidget(self.gpu_button)

        gpu_note = QLabel(TEXTO_UI["performance_gpu_note"], self)
        gpu_note.setWordWrap(True)
        layout.addWidget(gpu_note)

        data_saver_note = QLabel(
            TEXTO_UI["performance_data_saver_note"],
            self,
        )
        data_saver_note.setWordWrap(True)
        layout.addWidget(data_saver_note)
        layout.addStretch(1)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self.refresh_metrics)

    def start_monitoring(self):
        self.refresh_metrics()
        if not self._timer.isActive():
            self._timer.start()

    def stop_monitoring(self):
        self._timer.stop()

    def refresh_metrics(self):
        usage = self._monitor.snapshot
        error = str(usage.get("error") or "")
        if error:
            message = (
                TEXTO_UI["performance_dependency_missing"]
                if "psutil" in error.lower()
                else TEXTO_UI["performance_metrics_unavailable"]
            )
            self.cpu_value.setText(message)
            self.memory_value.setText(message)
            self.process_count_value.setText(message)
            self._refresh_session_metrics()
            return

        cpu_percent = usage.get("cpu_percent")
        self.cpu_value.setText(
            TEXTO_UI["performance_cpu_waiting"]
            if cpu_percent is None
            else f"{cpu_percent:.1f}%"
        )
        memory_bytes = usage.get("memory_bytes")
        self.memory_value.setText(
            "—"
            if memory_bytes is None
            else f"{memory_bytes / (1024 * 1024):.0f} MiB"
        )
        process_count = usage.get("process_count")
        if process_count is None:
            self.process_count_value.setText("—")
        elif usage["partial"]:
            self.process_count_value.setText(
                f"{process_count} ({TEXTO_UI['performance_partial']})"
            )
        else:
            self.process_count_value.setText(str(process_count))

        self._refresh_session_metrics()

    def _refresh_session_metrics(self):
        snapshot = performance_snapshot()
        startup_ms = snapshot["startup_ms"].get("janela_exibida")
        self.startup_label.setText(
            TEXTO_UI["performance_startup_value"].format(
                value=(
                    TEXTO_UI["performance_not_measured"]
                    if startup_ms is None
                    else f"{startup_ms / 1000:.2f} s"
                )
            )
        )
        self._refresh_navigation_summary(snapshot["navigation"])

    def _refresh_navigation_summary(self, navigation: dict):
        order = (
            ("local", "performance_nav_local"),
            ("web", "performance_nav_web"),
            ("internal", "performance_nav_internal"),
        )
        rows = []
        for kind, label_key in order:
            summary = navigation.get(kind)
            if not summary:
                continue
            result = TEXTO_UI[
                "performance_nav_success"
                if summary["last_success"]
                else "performance_nav_failed"
            ]
            rows.append(
                TEXTO_UI["performance_nav_row"].format(
                    label=TEXTO_UI[label_key],
                    count=summary["count"],
                    average=summary["average_ms"],
                    last=summary["last_ms"],
                    result=result,
                )
            )
        self.navigation_label.setText(
            "\n".join(rows)
            if rows
            else TEXTO_UI["performance_navigation_empty"]
        )
