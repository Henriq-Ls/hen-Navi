"""Medições locais de desempenho sem registrar endereços ou conteúdo de páginas."""

from collections import defaultdict, deque
import ipaddress
import os
import socket
from time import perf_counter


_STARTUP_MILLISECONDS: dict[str, int] = {}
_NAVIGATION_SAMPLES: dict[str, deque] = defaultdict(lambda: deque(maxlen=30))


class ProcessMetricsUnavailable(RuntimeError):
    """Indica que a amostragem de processos não pode ser iniciada."""


class NetworkMetricsUnavailable(RuntimeError):
    """Indica que os contadores locais de rede não estão disponíveis."""


def elapsed_ms(started_at: float, finished_at: float | None = None) -> int:
    """Converte um intervalo de relógio monotônico em milissegundos."""
    end = perf_counter() if finished_at is None else float(finished_at)
    return max(0, round((end - float(started_at)) * 1000))


def page_load_kind(scheme: str) -> str:
    """Agrupa a navegação sem expor sua URL."""
    normalized = str(scheme or "").strip().lower()
    if normalized in {"http", "https"}:
        return "web"
    if normalized == "file":
        return "local"
    return "internal"


def record_startup_stage(
    logger,
    stage: str,
    started_at: float,
    finished_at: float | None = None,
) -> int:
    """Registra uma etapa de inicialização usando somente um rótulo interno."""
    duration = elapsed_ms(started_at, finished_at)
    _STARTUP_MILLISECONDS[stage] = duration
    logger.info(
        "Desempenho",
        "inicializacao",
        f"etapa={stage} duracao_ms={duration}",
    )
    return duration


def record_page_load(
    logger,
    started_at: float,
    scheme: str,
    success: bool,
    finished_at: float | None = None,
) -> int:
    """Registra tipo, duração e resultado, nunca a URL da página."""
    duration = elapsed_ms(started_at, finished_at)
    kind = page_load_kind(scheme)
    _NAVIGATION_SAMPLES[kind].append(
        {"duration_ms": duration, "success": bool(success)}
    )
    logger.info(
        "Desempenho",
        "navegacao",
        (
            f"tipo={kind} "
            f"duracao_ms={duration} "
            f"sucesso={'sim' if success else 'nao'}"
        ),
    )
    return duration


def performance_snapshot() -> dict:
    """Retorna somente métricas agregadas mantidas em memória nesta sessão."""
    navigation = {}
    for kind, samples in _NAVIGATION_SAMPLES.items():
        if not samples:
            continue
        durations = [sample["duration_ms"] for sample in samples]
        last = samples[-1]
        navigation[kind] = {
            "count": len(samples),
            "average_ms": round(sum(durations) / len(durations)),
            "last_ms": last["duration_ms"],
            "last_success": last["success"],
        }
    return {
        "startup_ms": dict(_STARTUP_MILLISECONDS),
        "navigation": navigation,
    }


def reset_performance_metrics() -> None:
    """Limpa o estado agregado; usado para manter testes isolados."""
    _STARTUP_MILLISECONDS.clear()
    _NAVIGATION_SAMPLES.clear()


def reset_navigation_samples() -> None:
    """Reinicia apenas a amostra de navegação desta sessão."""
    _NAVIGATION_SAMPLES.clear()


class ProcessTreeSampler:
    """Mede CPU/RAM do app e dos processos filhos do QtWebEngine."""

    def __init__(
        self,
        root_pid: int | None = None,
        *,
        psutil_module=None,
        clock=perf_counter,
    ):
        if psutil_module is None:
            try:
                import psutil as psutil_module
            except ImportError as error:
                raise ProcessMetricsUnavailable(
                    "psutil não está instalado"
                ) from error
        self.root_pid = os.getpid() if root_pid is None else int(root_pid)
        self._psutil = psutil_module
        self._clock = clock
        self._previous_cpu_times: dict[int, tuple[float, float]] = {}
        self._previous_sample_at: float | None = None

    def sample(self) -> dict:
        """Retorna CPU do intervalo anterior e memória/processos atuais."""
        process_errors = (OSError, getattr(self._psutil, "Error", OSError))
        try:
            root = self._psutil.Process(self.root_pid)
        except process_errors as error:
            raise ProcessMetricsUnavailable(
                "processo raiz indisponível para medição"
            ) from error
        try:
            processes = [root, *root.children(recursive=True)]
            partial = False
        except process_errors:
            processes = [root]
            partial = True

        current_cpu_times: dict[int, tuple[float, float]] = {}
        memory_bytes = 0
        process_count = 0
        cpu_delta_seconds = 0.0

        for process in processes:
            try:
                cpu_times = process.cpu_times()
                memory_info = process.memory_info()
                pid = int(process.pid)
                user_seconds = float(cpu_times.user)
                system_seconds = float(cpu_times.system)
                memory_bytes += int(memory_info.rss)
                process_count += 1
                current_cpu_times[pid] = (user_seconds, system_seconds)
                previous = self._previous_cpu_times.get(pid)
                if previous is not None:
                    previous_total = previous[0] + previous[1]
                    current_total = user_seconds + system_seconds
                    cpu_delta_seconds += max(0.0, current_total - previous_total)
            except process_errors:
                partial = True

        sampled_at = self._clock()
        elapsed_seconds = (
            sampled_at - self._previous_sample_at
            if self._previous_sample_at is not None
            else 0.0
        )
        cpu_percent = None
        if elapsed_seconds > 0:
            logical_cpus = max(1, self._psutil.cpu_count() or 1)
            cpu_percent = round(
                min(
                    100.0,
                    max(
                        0.0,
                        cpu_delta_seconds
                        / elapsed_seconds
                        / logical_cpus
                        * 100,
                    ),
                ),
                1,
            )

        self._previous_cpu_times = current_cpu_times
        self._previous_sample_at = sampled_at
        return {
            "cpu_percent": cpu_percent,
            "memory_bytes": memory_bytes,
            "process_count": process_count,
            "partial": partial,
        }


class NetworkMetricsSampler:
    """Lê IPs locais e contadores de tráfego do sistema sem fazer requisições."""

    def __init__(
        self,
        *,
        psutil_module=None,
        clock=perf_counter,
    ):
        if psutil_module is None:
            try:
                import psutil as psutil_module
            except ImportError as error:
                raise NetworkMetricsUnavailable(
                    "psutil não está instalado"
                ) from error
        self._psutil = psutil_module
        self._clock = clock
        self._previous_counters: tuple[int, int] | None = None
        self._previous_sample_at: float | None = None
        self._session_start_counters: tuple[int, int] | None = None

    def sample(self) -> dict:
        """Retorna endereços locais e tráfego agregado desde o início da amostra."""
        psutil_error = getattr(self._psutil, "Error", OSError)
        try:
            counters = self._psutil.net_io_counters()
            interfaces = self._psutil.net_if_addrs()
        except (AttributeError, OSError, TypeError, psutil_error) as error:
            raise NetworkMetricsUnavailable(
                "contadores de rede indisponíveis"
            ) from error
        if counters is None:
            raise NetworkMetricsUnavailable(
                "contadores de rede indisponíveis"
            )

        try:
            received = max(0, int(counters.bytes_recv))
            sent = max(0, int(counters.bytes_sent))
        except (AttributeError, TypeError, ValueError) as error:
            raise NetworkMetricsUnavailable(
                "contadores de rede inválidos"
            ) from error

        current_counters = (received, sent)
        sampled_at = float(self._clock())
        elapsed_seconds = (
            sampled_at - self._previous_sample_at
            if self._previous_sample_at is not None
            else 0.0
        )

        download_bytes_per_second = None
        upload_bytes_per_second = None
        downloaded_delta = 0
        uploaded_delta = 0
        if self._previous_counters is not None:
            downloaded_delta = max(
                0,
                received - self._previous_counters[0],
            )
            uploaded_delta = max(
                0,
                sent - self._previous_counters[1],
            )
            if elapsed_seconds > 0:
                download_bytes_per_second = round(
                    downloaded_delta / elapsed_seconds
                )
                upload_bytes_per_second = round(
                    uploaded_delta / elapsed_seconds
                )

        if self._session_start_counters is None:
            self._session_start_counters = current_counters

        self._previous_counters = current_counters
        self._previous_sample_at = sampled_at
        return {
            "network_sampled": True,
            "network_ip_addresses": self._local_ip_addresses(interfaces or {}),
            "network_download_bytes_per_second": download_bytes_per_second,
            "network_upload_bytes_per_second": upload_bytes_per_second,
            "network_downloaded_bytes": max(
                0,
                received - self._session_start_counters[0],
            ),
            "network_uploaded_bytes": max(
                0,
                sent - self._session_start_counters[1],
            ),
        }

    @staticmethod
    def _local_ip_addresses(interfaces: dict) -> tuple[str, ...]:
        addresses = set()
        for interface_addresses in interfaces.values():
            for address in interface_addresses:
                if address.family not in (socket.AF_INET, socket.AF_INET6):
                    continue
                value = str(address.address or "").split("%", 1)[0]
                try:
                    ip = ipaddress.ip_address(value)
                except ValueError:
                    continue
                if (
                    ip.is_loopback
                    or ip.is_link_local
                    or ip.is_unspecified
                    or ip.is_multicast
                ):
                    continue
                addresses.add(str(ip))
        return tuple(sorted(addresses))
