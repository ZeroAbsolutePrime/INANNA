from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from core.process_faculty import (
    ProcessFaculty,
    ProcessRecord,
    ProcessResult,
    SystemInfo,
)


class FakeProcess:
    def __init__(self, info: dict[str, object]) -> None:
        self.info = info


class FakeMemoryInfo:
    def __init__(self, rss: int) -> None:
        self.rss = rss


class FakeManagedProcess:
    def name(self) -> str:
        return "python.exe"

    def terminate(self) -> None:
        return None

    def wait(self, timeout: int) -> None:
        del timeout
        return None

    def kill(self) -> None:
        return None


class FakePsutil:
    class NoSuchProcess(Exception):
        pass

    class AccessDenied(Exception):
        pass

    class TimeoutExpired(Exception):
        pass

    def __init__(self) -> None:
        self._records = [
            FakeProcess(
                {
                    "pid": 101,
                    "name": "python.exe",
                    "status": "running",
                    "cpu_percent": 12.5,
                    "memory_info": FakeMemoryInfo(256 * 1024 * 1024),
                    "memory_percent": 3.1,
                    "username": "INANNA NAMMU",
                    "create_time": 1713691200.0,
                    "cmdline": ["python", "app.py"],
                }
            ),
            FakeProcess(
                {
                    "pid": 202,
                    "name": "firefox.exe",
                    "status": "sleeping",
                    "cpu_percent": 4.2,
                    "memory_info": FakeMemoryInfo(512 * 1024 * 1024),
                    "memory_percent": 6.2,
                    "username": "INANNA NAMMU",
                    "create_time": 1713694800.0,
                    "cmdline": ["firefox"],
                }
            ),
        ]

    def process_iter(self, attrs: list[str]) -> list[FakeProcess]:
        del attrs
        return list(self._records)

    def boot_time(self) -> float:
        return 1000.0

    def cpu_percent(self, interval: float = 0.1) -> float:
        del interval
        return 42.0

    def virtual_memory(self):
        return SimpleNamespace(total=16 * 1024**3, used=8 * 1024**3, percent=50.0)

    def disk_usage(self, path: str):
        del path
        return SimpleNamespace(total=100 * 1024**3, used=40 * 1024**3, percent=40.0)

    def cpu_count(self) -> int:
        return 8

    def Process(self, pid: int):
        if pid == 999999:
            raise self.NoSuchProcess()
        return FakeManagedProcess()


class ProcessFacultyTests(unittest.TestCase):
    def test_process_faculty_instantiates(self) -> None:
        faculty = ProcessFaculty()
        self.assertIsInstance(faculty, ProcessFaculty)

    def test_system_info_returns_process_result_with_success_true(self) -> None:
        result = ProcessFaculty().system_info()
        self.assertTrue(result.success)

    def test_system_info_returns_system_info_with_hostname(self) -> None:
        result = ProcessFaculty().system_info()
        self.assertTrue(result.system_info is not None)
        self.assertTrue(bool(result.system_info.hostname if result.system_info else ""))

    def test_system_info_returns_cpu_count_greater_than_zero(self) -> None:
        result = ProcessFaculty().system_info()
        self.assertTrue((result.system_info.cpu_count if result.system_info else 0) > 0)

    def test_system_info_format_result_includes_system_info(self) -> None:
        faculty = ProcessFaculty()
        result = faculty.system_info()
        self.assertIn("proc > system info", faculty.format_result(result))

    def test_list_processes_returns_process_result_with_success_true(self) -> None:
        result = ProcessFaculty().list_processes(limit=5)
        self.assertTrue(result.success)

    def test_list_processes_returns_at_least_one_record(self) -> None:
        result = ProcessFaculty().list_processes(limit=5)
        self.assertGreaterEqual(len(result.records), 1)

    def test_list_processes_filter_works(self) -> None:
        faculty = ProcessFaculty()
        faculty._psutil = FakePsutil()
        result = faculty.list_processes(filter_name="python")
        self.assertTrue(result.success)
        self.assertEqual(1, result.count)
        self.assertEqual("python.exe", result.records[0].name)

    def test_list_processes_format_result_includes_pid(self) -> None:
        faculty = ProcessFaculty()
        faculty._psutil = FakePsutil()
        result = faculty.list_processes()
        self.assertIn("PID", faculty.format_result(result))

    def test_kill_process_with_invalid_pid_returns_success_false(self) -> None:
        faculty = ProcessFaculty()
        faculty._psutil = FakePsutil()
        result = faculty.kill_process(999999)
        self.assertFalse(result.success)

    def test_run_command_echo_hello_returns_success_true(self) -> None:
        result = ProcessFaculty().run_command("echo hello")
        self.assertTrue(result.success)

    def test_run_command_echo_hello_stdout_contains_hello(self) -> None:
        result = ProcessFaculty().run_command("echo hello")
        self.assertIn("hello", result.stdout.lower())

    def test_run_command_with_invalid_command_returns_failure_gracefully(self) -> None:
        result = ProcessFaculty().run_command("command_that_should_not_exist_12345")
        self.assertFalse(result.success)
        self.assertIsNotNone(result.returncode)

    def test_format_result_for_list_shows_process_table_header(self) -> None:
        faculty = ProcessFaculty()
        result = ProcessResult(
            success=True,
            operation="list",
            query="all",
            records=[
                ProcessRecord(
                    pid=101,
                    name="python.exe",
                    status="running",
                    cpu_percent=10.0,
                    memory_mb=100.0,
                    memory_percent=1.0,
                    username="INANNA NAMMU",
                    started_at="10:00",
                    cmdline="python app.py",
                )
            ],
            count=1,
        )
        formatted = faculty.format_result(result)
        self.assertIn("PID", formatted)
        self.assertIn("NAME", formatted)

    def test_format_result_for_system_shows_cpu_line(self) -> None:
        faculty = ProcessFaculty()
        result = ProcessResult(
            success=True,
            operation="system",
            query="system",
            system_info=SystemInfo(
                platform="Windows 11",
                hostname="INANNA NAMMU",
                uptime_seconds=3700,
                uptime_human="1h 1m",
                cpu_count=8,
                cpu_percent=42.0,
                ram_total_gb=16.0,
                ram_used_gb=8.0,
                ram_percent=50.0,
                disk_total_gb=100.0,
                disk_used_gb=40.0,
                disk_percent=40.0,
                python_version="3.12.0",
            ),
        )
        formatted = faculty.format_result(result)
        self.assertIn("CPU (8 cores)", formatted)

    def test_format_result_for_error_shows_proc_error(self) -> None:
        faculty = ProcessFaculty()
        result = ProcessResult(False, "list", "all", error="broken")
        self.assertEqual("proc > error: broken", faculty.format_result(result))

    def test_format_uptime_zero_returns_0s(self) -> None:
        self.assertEqual("0s", ProcessFaculty()._format_uptime(0))

    def test_format_uptime_ninety_returns_1m_30s(self) -> None:
        self.assertEqual("1m 30s", ProcessFaculty()._format_uptime(90))

    def test_format_uptime_three_thousand_seven_hundred_returns_1h_1m(self) -> None:
        self.assertEqual("1h 1m", ProcessFaculty()._format_uptime(3700))

    def test_process_faculty_works_without_psutil_fallback(self) -> None:
        faculty = ProcessFaculty()
        fallback = ProcessResult(
            success=True,
            operation="list",
            query="all",
            records=[],
            count=0,
        )
        faculty._psutil = None
        with patch.object(faculty, "_fallback_list", return_value=fallback) as fallback_mock:
            result = faculty.list_processes()
        fallback_mock.assert_called_once()
        self.assertTrue(result.success)


if __name__ == "__main__":
    unittest.main()
