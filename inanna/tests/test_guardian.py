from __future__ import annotations

import asyncio
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.guardian import GuardianAlert, GuardianFaculty
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


class GuardianFacultyTests(unittest.TestCase):
    def test_inspect_returns_guardian_alert_list(self) -> None:
        alerts = GuardianFaculty().inspect(
            session_id="session-1",
            memory_count=0,
            pending_proposals=0,
            routing_log=[],
            governance_blocks=0,
            tool_executions=0,
        )

        self.assertIsInstance(alerts, list)
        self.assertTrue(all(isinstance(alert, GuardianAlert) for alert in alerts))

    def test_healthy_state_returns_system_healthy_only(self) -> None:
        alerts = GuardianFaculty().inspect(
            session_id="session-1",
            memory_count=0,
            pending_proposals=0,
            routing_log=[],
            governance_blocks=0,
            tool_executions=0,
        )

        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].code, "SYSTEM_HEALTHY")

    def test_pending_proposal_accumulation_warns(self) -> None:
        alerts = GuardianFaculty().inspect(
            session_id="session-1",
            memory_count=0,
            pending_proposals=5,
            routing_log=[],
            governance_blocks=0,
            tool_executions=0,
        )

        self.assertTrue(
            any(
                alert.code == "PENDING_PROPOSAL_ACCUMULATION" and alert.level == "warn"
                for alert in alerts
            )
        )

    def test_repeated_governance_blocks_warn(self) -> None:
        alerts = GuardianFaculty().inspect(
            session_id="session-1",
            memory_count=0,
            pending_proposals=0,
            routing_log=[],
            governance_blocks=3,
            tool_executions=0,
        )

        self.assertTrue(
            any(
                alert.code == "REPEATED_GOVERNANCE_BLOCKS" and alert.level == "warn"
                for alert in alerts
            )
        )

    def test_memory_growth_is_info(self) -> None:
        alerts = GuardianFaculty().inspect(
            session_id="session-1",
            memory_count=10,
            pending_proposals=0,
            routing_log=[],
            governance_blocks=0,
            tool_executions=0,
        )

        self.assertTrue(
            any(alert.code == "MEMORY_GROWTH" and alert.level == "info" for alert in alerts)
        )

    def test_format_report_is_non_empty(self) -> None:
        alerts = [
            GuardianAlert(
                level="warn",
                code="PENDING_PROPOSAL_ACCUMULATION",
                message="5 proposals are pending approval.",
            )
        ]

        report = GuardianFaculty().format_report(alerts)

        self.assertTrue(report)
        self.assertIn("Guardian Report", report)


class DummyConnection:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []

    async def send(self, payload: str) -> None:
        self.messages.append(json.loads(payload))


class InterfaceServerGuardianTests(unittest.TestCase):
    def test_send_initial_state_emits_guardian_when_warns_exist(self) -> None:
        with TemporaryDirectory() as temp_dir:
            original_app_root = ui_server.APP_ROOT
            try:
                ui_server.APP_ROOT = Path(temp_dir)
                write_roles_config(ui_server.APP_ROOT)
                server = ui_server.InterfaceServer()
                for index in range(5):
                    server.proposal.create(
                        what=f"pending proposal {index}",
                        why="test",
                        payload={"session_id": server.session.session_id, "summary_lines": []},
                    )
                connection = DummyConnection()

                asyncio.run(server.send_initial_state(connection))

                guardian_messages = [
                    payload
                    for payload in connection.messages
                    if payload.get("type") == "guardian"
                ]
                self.assertEqual(len(guardian_messages), 1)
                self.assertIn(
                    "PENDING_PROPOSAL_ACCUMULATION",
                    str(guardian_messages[0].get("text", "")),
                )
            finally:
                ui_server.APP_ROOT = original_app_root

    def test_send_initial_state_skips_guardian_when_only_info_exists(self) -> None:
        with TemporaryDirectory() as temp_dir:
            original_app_root = ui_server.APP_ROOT
            try:
                ui_server.APP_ROOT = Path(temp_dir)
                write_roles_config(ui_server.APP_ROOT)
                server = ui_server.InterfaceServer()
                connection = DummyConnection()

                asyncio.run(server.send_initial_state(connection))

                guardian_messages = [
                    payload
                    for payload in connection.messages
                    if payload.get("type") == "guardian"
                ]
                self.assertEqual(guardian_messages, [])
            finally:
                ui_server.APP_ROOT = original_app_root


if __name__ == "__main__":
    unittest.main()
