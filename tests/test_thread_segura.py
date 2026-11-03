import unittest
from unittest.mock import patch

from _THREADS_.run_guard import protect_subclass_run


class ThreadSeguraGuardTests(unittest.TestCase):
    def test_overridden_run_logs_exception_and_does_not_escape(self):
        class FakeThread:
            _nome_thread = "worker_de_teste"

            def run(self):
                raise RuntimeError("falha simulada")

        protect_subclass_run(FakeThread)
        thread = FakeThread()

        with patch("_THREADS_.run_guard._log_thread_exception") as log_exception:
            result = thread.run()

        self.assertIsNone(result)
        log_exception.assert_called_once()
        name, details = log_exception.call_args.args
        self.assertEqual(name, "worker_de_teste")
        self.assertIn("RuntimeError: falha simulada", details)

    def test_qthread_override_uses_guard_when_qt_libraries_are_available(self):
        try:
            from PySide6.QtCore import QCoreApplication

            from _THREADS_.thread_segura import ThreadSegura
        except (ImportError, OSError) as error:
            self.skipTest(f"PySide6 nativo indisponível neste ambiente: {error}")

        application = QCoreApplication.instance() or QCoreApplication([])

        class FailingThread(ThreadSegura):
            def run(self):
                raise RuntimeError("falha no QThread")

        thread = FailingThread(nome="qthread_de_teste", parent=application)
        with patch("_THREADS_.run_guard._log_thread_exception") as log_exception:
            thread.start()
            self.assertTrue(thread.wait(5000))

        log_exception.assert_called_once()
        self.assertIn("RuntimeError: falha no QThread", log_exception.call_args.args[1])


if __name__ == "__main__":
    unittest.main()
