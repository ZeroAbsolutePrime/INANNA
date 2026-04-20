from __future__ import annotations

import os
import time
import unittest
from unittest.mock import patch

from core.process_monitor import ProcessMonitor


class _FakeResponse:
    status = 200

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        del exc_type, exc, tb
        return False


class ProcessMonitorTests(unittest.TestCase):
    def test_process_monitor_can_be_instantiated(self) -> None:
        monitor = ProcessMonitor(time.time())

        self.assertIsInstance(monitor, ProcessMonitor)

    def test_inanna_record_reports_running_process(self) -> None:
        monitor = ProcessMonitor(time.time() - 5)

        record = monitor.inanna_record()

        self.assertEqual(record.status, "running")
        self.assertEqual(record.pid, os.getpid())
        self.assertEqual(record.name, "INANNA NYX Server")

    def test_format_uptime_handles_seconds_minutes_and_hours(self) -> None:
        monitor = ProcessMonitor(time.time())

        self.assertEqual(monitor.format_uptime(0), "0s")
        self.assertEqual(monitor.format_uptime(90), "1m 30s")
        self.assertEqual(monitor.format_uptime(3700), "1h 1m")

    @patch("core.process_monitor.urllib.request.urlopen", return_value=_FakeResponse())
    def test_all_records_returns_multiple_processes(self, _mock_urlopen) -> None:
        monitor = ProcessMonitor(time.time() - 90)

        records = monitor.all_records()

        self.assertGreaterEqual(len(records), 2)
        self.assertEqual(records[0].name, "INANNA NYX Server")
        self.assertEqual(records[1].name, "LM Studio")
