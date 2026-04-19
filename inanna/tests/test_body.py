from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from core.body import BodyInspector, BodyReport
import ui.server as ui_server


ROLES_PAYLOAD = {
    "roles": {
        "guardian": {
            "description": "Full system access - assigned directly only",
            "privileges": ["all"],
        },
        "operator": {
            "description": "Realm-scoped admin",
            "privileges": [
                "manage_users_in_realm",
                "approve_proposals_in_realm",
                "read_realm_audit_log",
                "invite_users",
            ],
        },
        "user": {
            "description": "Standard interaction",
            "privileges": [
                "converse",
                "approve_own_memory",
                "read_own_log",
                "forget_own_memory",
            ],
        },
    }
}


def write_roles_config(app_root: Path) -> None:
    config_dir = app_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "roles.json").write_text(
        json.dumps(ROLES_PAYLOAD, indent=2),
        encoding="utf-8",
    )


class BodyInspectorTests(unittest.TestCase):
    def test_body_inspector_can_be_instantiated(self) -> None:
        inspector = BodyInspector()

        self.assertIsInstance(inspector, BodyInspector)

    def test_inspect_returns_body_report(self) -> None:
        with TemporaryDirectory() as temp_dir:
            report = BodyInspector().inspect(
                session_id="session-1",
                session_started_at=datetime.now(timezone.utc).isoformat(),
                realm="default",
                model_url="http://localhost:1234/v1",
                model_name="local-model",
                model_mode="connected",
                data_root=Path(temp_dir),
                memory_record_count=2,
                pending_proposal_count=1,
                routing_log_count=3,
            )

        self.assertIsInstance(report, BodyReport)
        self.assertEqual(report.session_id, "session-1")
        self.assertEqual(report.realm, "default")
        self.assertEqual(report.routing_log_count, 3)

    def test_format_report_contains_expected_sections(self) -> None:
        report = BodyReport(
            timestamp="2026-04-19T12:00:00+00:00",
            platform="Windows 11",
            python_version="3.14.0",
            cpu_count=8,
            memory_total_mb=16000.0,
            memory_available_mb=8000.0,
            memory_used_pct=50.0,
            disk_total_gb=512.0,
            disk_free_gb=256.0,
            disk_used_pct=50.0,
            session_id="session-1",
            session_uptime_seconds=90.0,
            realm="default",
            model_url="http://localhost:1234/v1",
            model_name="local-model",
            model_mode="connected",
            data_root="C:/tmp/data",
            memory_record_count=2,
            pending_proposal_count=1,
            routing_log_count=3,
        )

        formatted = BodyInspector().format_report(report)

        self.assertIn("Body Report", formatted)
        self.assertIn("Platform", formatted)
        self.assertIn("Memory", formatted)
        self.assertIn("Session", formatted)
        self.assertIn("Model", formatted)

    def test_format_uptime_formats_seconds(self) -> None:
        self.assertEqual(BodyInspector()._format_uptime(45), "45s")

    def test_format_uptime_formats_minutes(self) -> None:
        self.assertEqual(BodyInspector()._format_uptime(90), "1m 30s")

    def test_format_uptime_formats_hours(self) -> None:
        self.assertEqual(BodyInspector()._format_uptime(3661), "1h 1m")

    def test_inspect_works_without_psutil(self) -> None:
        with TemporaryDirectory() as temp_dir:
            with patch("core.body.importlib.import_module", side_effect=ModuleNotFoundError()):
                report = BodyInspector().inspect(
                    session_id="session-1",
                    session_started_at=datetime.now(timezone.utc).isoformat(),
                    realm="default",
                    model_url="http://localhost:1234/v1",
                    model_name="local-model",
                    model_mode="fallback",
                    data_root=Path(temp_dir),
                    memory_record_count=0,
                    pending_proposal_count=0,
                    routing_log_count=0,
                )

        self.assertIsInstance(report, BodyReport)


class BodyStatusPayloadTests(unittest.TestCase):
    def test_interface_status_payload_includes_body_summary(self) -> None:
        with TemporaryDirectory() as temp_dir:
            original_app_root = ui_server.APP_ROOT
            try:
                ui_server.APP_ROOT = Path(temp_dir)
                write_roles_config(ui_server.APP_ROOT)
                server = ui_server.InterfaceServer()

                payload = server.build_status_payload()

                self.assertIn("body", payload)
                self.assertEqual(
                    set(payload["body"].keys()),
                    {
                        "platform",
                        "python_version",
                        "model_mode",
                        "session_uptime_seconds",
                        "memory_used_pct",
                        "disk_free_gb",
                    },
                )
            finally:
                ui_server.APP_ROOT = original_app_root


if __name__ == "__main__":
    unittest.main()
