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
from _SERVICOS_.graphics_diagnostics import graphics_diagnostic_snapshot
from _SERVICOS_.performance_diagnostics import (
    performance_snapshot,
    reset_navigation_samples,
)


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
        network_divider = QFrame(resource_frame)
        network_divider.setFrameShape(QFrame.Shape.HLine)
        network_divider.setFrameShadow(QFrame.Shadow.Sunken)
        resource_layout.addRow(network_divider)

        self.network_title = QLabel(
            TEXTO_UI["performance_network_title"],
            resource_frame,
        )
        self.network_title.setObjectName("performanceNetworkTitle")
        self.network_title.setToolTip(TEXTO_UI["performance_network_note"])
        resource_layout.addRow(self.network_title)

        self.network_ip_value = QLabel(
            TEXTO_UI["performance_network_waiting"],
            resource_frame,
        )
        self.network_ip_value.setWordWrap(True)
        self.network_download_speed_value = QLabel(
            TEXTO_UI["performance_network_waiting"],
            resource_frame,
        )
        self.network_upload_speed_value = QLabel(
            TEXTO_UI["performance_network_waiting"],
            resource_frame,
        )
        self.network_download_total_value = QLabel(
            TEXTO_UI["performance_network_waiting"],
            resource_frame,
        )
        self.network_upload_total_value = QLabel(
            TEXTO_UI["performance_network_waiting"],
            resource_frame,
        )
        resource_layout.addRow(
            TEXTO_UI["performance_network_ip_label"],
            self.network_ip_value,
        )
        resource_layout.addRow(
            TEXTO_UI["performance_network_download_label"],
            self.network_download_speed_value,
        )
        resource_layout.addRow(
            TEXTO_UI["performance_network_upload_label"],
            self.network_upload_speed_value,
        )
        resource_layout.addRow(
            TEXTO_UI["performance_network_download_total"],
            self.network_download_total_value,
        )
        resource_layout.addRow(
            TEXTO_UI["performance_network_upload_total"],
            self.network_upload_total_value,
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

        self.navigation_reset_button = QPushButton(
            TEXTO_UI["performance_reset_navigation"],
            self,
        )
        self.navigation_reset_button.setToolTip(
            TEXTO_UI["performance_reset_navigation_tooltip"]
        )
        self.navigation_reset_button.clicked.connect(
            self._reset_navigation_samples
        )
        layout.addWidget(self.navigation_reset_button)

        self.gpu_state_value = QLabel(
            TEXTO_UI["performance_gpu_state_inconclusive"],
            self,
        )
        self.gpu_state_value.setWordWrap(True)
        layout.addWidget(self.gpu_state_value)

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

    def _reset_navigation_samples(self):
        reset_navigation_samples()
        self._refresh_session_metrics()

    def start_monitoring(self):
        self.refresh_metrics()
        if not self._timer.isActive():
            self._timer.start()

    def stop_monitoring(self):
        self._timer.stop()

    def refresh_metrics(self):
        usage = self._monitor.snapshot
        self._refresh_network_metrics(usage)
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

    def _refresh_network_metrics(self, usage: dict) -> None:
        error = str(usage.get("network_error") or usage.get("error") or "")
        if error:
            unavailable = TEXTO_UI["performance_network_unavailable"]
            self.network_ip_value.setText(unavailable)
            self.network_download_speed_value.setText(unavailable)
            self.network_upload_speed_value.setText(unavailable)
            self.network_download_total_value.setText(unavailable)
            self.network_upload_total_value.setText(unavailable)
            return

        if not usage.get("network_sampled"):
            waiting = TEXTO_UI["performance_network_waiting"]
            self.network_ip_value.setText(waiting)
            self.network_download_speed_value.setText(waiting)
            self.network_upload_speed_value.setText(waiting)
            self.network_download_total_value.setText(waiting)
            self.network_upload_total_value.setText(waiting)
            return

        addresses = tuple(
            str(address)
            for address in usage.get("network_ip_addresses", ())
            if address
        )
        self.network_ip_value.setText(
            ", ".join(addresses)
            if addresses
            else TEXTO_UI["performance_network_ip_not_found"]
        )
        self.network_ip_value.setToolTip(
            TEXTO_UI["performance_network_note"]
        )

        for key, widget in (
            (
                "network_download_bytes_per_second",
                self.network_download_speed_value,
            ),
            (
                "network_upload_bytes_per_second",
                self.network_upload_speed_value,
            ),
        ):
            rate = usage.get(key)
            widget.setText(
                TEXTO_UI["performance_network_waiting"]
                if rate is None
                else f"{self._format_bytes(rate)}/s"
            )

        self.network_download_total_value.setText(
            self._format_bytes(usage.get("network_downloaded_bytes", 0))
        )
        self.network_upload_total_value.setText(
            self._format_bytes(usage.get("network_uploaded_bytes", 0))
        )

    @staticmethod
    def _format_bytes(value: int | float) -> str:
        size = max(0.0, float(value))
        units = ("B", "KiB", "MiB", "GiB", "TiB")
        for unit in units:
            if size < 1024 or unit == units[-1]:
                return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
            size /= 1024
        return "0 B"

    def _refresh_session_metrics(self):
        snapshot = performance_snapshot()
        graphics = graphics_diagnostic_snapshot()
        graphics_state_key = {
            "renderer_reported": "performance_gpu_state_renderer_reported",
            "software_renderer": "performance_gpu_state_software_renderer",
            "webgl_available": "performance_gpu_state_webgl_available",
            "qt_backend_unsupported": (
                "performance_gpu_state_qt_backend_unsupported"
            ),
            "qt_device_reported": "performance_gpu_state_qt_device_reported",
            "inconclusive": "performance_gpu_state_inconclusive",
        }.get(graphics["state"], "performance_gpu_state_inconclusive")
        self.gpu_state_value.setText(
            f"{TEXTO_UI['performance_gpu_state_label']}: "
            f"{TEXTO_UI[graphics_state_key]}"
        )
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
