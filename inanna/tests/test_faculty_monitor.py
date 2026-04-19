from __future__ import annotations

import unittest

from core.faculty_monitor import FacultyMonitor, FacultyRecord


class FacultyMonitorTests(unittest.TestCase):
    def test_faculty_monitor_can_be_instantiated(self) -> None:
        monitor = FacultyMonitor()

        self.assertIsInstance(monitor, FacultyMonitor)

    def test_all_records_returns_four_faculties(self) -> None:
        records = FacultyMonitor().all_records()

        self.assertEqual(len(records), 4)
        self.assertTrue(all(isinstance(record, FacultyRecord) for record in records))

    def test_update_model_mode_updates_crown_and_analyst(self) -> None:
        monitor = FacultyMonitor()

        monitor.update_model_mode("connected")

        self.assertEqual(monitor.get_record("crown").mode, "connected")
        self.assertEqual(monitor.get_record("analyst").mode, "connected")
        self.assertEqual(monitor.get_record("operator").mode, "ready")
        self.assertEqual(monitor.get_record("guardian").mode, "ready")

    def test_record_call_increments_count_and_updates_timestamp(self) -> None:
        monitor = FacultyMonitor()

        monitor.record_call("crown", 123.0, True)

        record = monitor.get_record("crown")
        self.assertEqual(record.call_count, 1)
        self.assertEqual(record.last_response_ms, 123.0)
        self.assertIsNotNone(record.last_called_at)

    def test_record_call_increments_error_count_on_failure(self) -> None:
        monitor = FacultyMonitor()

        monitor.record_call("operator", 50.0, False)

        record = monitor.get_record("operator")
        self.assertEqual(record.call_count, 1)
        self.assertEqual(record.error_count, 1)

    def test_format_report_contains_all_faculties(self) -> None:
        report = FacultyMonitor().format_report()

        self.assertIn("CROWN", report)
        self.assertIn("ANALYST", report)
        self.assertIn("OPERATOR", report)
        self.assertIn("GUARDIAN", report)

    def test_summary_returns_required_keys(self) -> None:
        summary = FacultyMonitor().summary()

        self.assertEqual(len(summary), 4)
        self.assertTrue(
            {
                "name",
                "display_name",
                "role",
                "mode",
                "last_called_at",
                "last_response_ms",
                "call_count",
                "error_count",
            }.issubset(summary[0].keys())
        )


if __name__ == "__main__":
    unittest.main()
