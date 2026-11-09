import unittest
from pathlib import Path

from _SERVICOS_.performance_diagnostics import (
    ProcessTreeSampler,
    elapsed_ms,
    page_load_kind,
    performance_snapshot,
    record_page_load,
    record_startup_stage,
    reset_performance_metrics,
)


class FakeLogger:
    def __init__(self):
        self.entries = []

    def info(self, module, function, message):
        self.entries.append((module, function, message))


class FakeCpuTimes:
    def __init__(self, user, system):
        self.user = user
        self.system = system


class FakeMemoryInfo:
    def __init__(self, rss):
        self.rss = rss


class FakeProcess:
    def __init__(self, pid, user=0.0, system=0.0, rss=0, children=None):
        self.pid = pid
        self.user = user
        self.system = system
        self.rss = rss
        self._children = list(children or [])

    def children(self, recursive=False):
        return list(self._children)

    def cpu_times(self):
        return FakeCpuTimes(self.user, self.system)

    def memory_info(self):
        return FakeMemoryInfo(self.rss)


class FakePsutil:
    class Error(Exception):
        pass

    def __init__(self, root):
        self.root = root

    def Process(self, _pid):
        return self.root

    def cpu_count(self):
        return 4


class PerformanceDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        reset_performance_metrics()

    def tearDown(self):
        reset_performance_metrics()

    def test_startup_measurements_are_connected_to_app_milestones(self):
        project_root = Path(__file__).resolve().parents[1]
        main_source = (project_root / "main.py").read_text(encoding="utf-8")

        self.assertIn(
            'record_startup_stage(log, "qapplication_criado", _PROCESS_STARTED_AT)',
            main_source,
        )
        self.assertIn(
            'record_startup_stage(log, "controlador_criado", _PROCESS_STARTED_AT)',
            main_source,
        )
        self.assertIn(
            'record_startup_stage(log, "janela_exibida", _PROCESS_STARTED_AT)',
            main_source,
        )

    def test_page_load_measurement_is_connected_to_webengine_signals(self):
        project_root = Path(__file__).resolve().parents[1]
        browser_source = (project_root / "browser.py").read_text(encoding="utf-8")

        self.assertIn(
            "view.loadStarted.connect(self._on_load_started)",
            browser_source,
        )
        self.assertIn(
            '"_henNavePerformanceLoadStartedAt"',
            browser_source,
        )
        self.assertIn("perf_counter(),", browser_source)
        self.assertIn("view.url().scheme(),", browser_source)
        self.assertIn("record_page_load(", browser_source)

    def test_elapsed_ms_uses_monotonic_seconds(self):
        self.assertEqual(elapsed_ms(10.25, 11.0), 750)

    def test_elapsed_ms_never_returns_negative_time(self):
        self.assertEqual(elapsed_ms(2.0, 1.0), 0)

    def test_page_load_kind_groups_schemes_without_url_data(self):
        self.assertEqual(page_load_kind("HTTPS"), "web")
        self.assertEqual(page_load_kind("file"), "local")
        self.assertEqual(page_load_kind("hennave"), "internal")

    def test_startup_stage_logs_duration(self):
        logger = FakeLogger()

        duration = record_startup_stage(
            logger,
            "janela_exibida",
            started_at=1.0,
            finished_at=1.125,
        )

        self.assertEqual(duration, 125)
        self.assertEqual(
            logger.entries,
            [("Desempenho", "inicializacao", "etapa=janela_exibida duracao_ms=125")],
        )

    def test_page_load_logs_only_category_duration_and_result(self):
        logger = FakeLogger()

        duration = record_page_load(
            logger,
            started_at=4.0,
            scheme="https",
            success=True,
            finished_at=4.35,
        )

        self.assertEqual(duration, 350)
        self.assertEqual(
            logger.entries,
            [("Desempenho", "navegacao", "tipo=web duracao_ms=350 sucesso=sim")],
        )

    def test_snapshot_aggregates_navigation_without_page_identifiers(self):
        logger = FakeLogger()
        record_page_load(logger, 1.0, "https", True, 2.0)
        record_page_load(logger, 2.0, "https", False, 4.0)

        snapshot = performance_snapshot()

        self.assertEqual(
            snapshot["navigation"]["web"],
            {
                "count": 2,
                "average_ms": 1500,
                "last_ms": 2000,
                "last_success": False,
            },
        )
        self.assertNotIn("url", str(snapshot).lower())
        self.assertNotIn("title", str(snapshot).lower())

    def test_process_sampler_aggregates_app_and_chromium_children(self):
        child = FakeProcess(202, user=1.0, system=0.5, rss=20 * 1024 * 1024)
        root = FakeProcess(
            101,
            user=3.0,
            system=1.0,
            rss=80 * 1024 * 1024,
            children=[child],
        )
        times = iter([10.0, 11.0])
        sampler = ProcessTreeSampler(
            root_pid=101,
            psutil_module=FakePsutil(root),
            clock=lambda: next(times),
        )

        first = sampler.sample()
        self.assertIsNone(first["cpu_percent"])
        self.assertEqual(first["memory_bytes"], 100 * 1024 * 1024)
        self.assertEqual(first["process_count"], 2)

        root.user += 0.25
        child.user += 0.25
        second = sampler.sample()

        self.assertEqual(second["cpu_percent"], 12.5)
        self.assertEqual(second["memory_bytes"], 100 * 1024 * 1024)
        self.assertEqual(second["process_count"], 2)
        self.assertFalse(second["partial"])


if __name__ == "__main__":
    unittest.main()
