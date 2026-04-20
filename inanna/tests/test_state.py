from __future__ import annotations

import unittest
from pathlib import Path

from config import Config
from core.session import Engine, Session
from core.state import StateReport
from identity import CURRENT_PHASE
from main import build_diagnostics_report


class StateTests(unittest.TestCase):
    def test_report_is_honest_and_readable(self) -> None:
        report = StateReport().render(
            session_id="session-1",
            mode="connected",
            memory_count=3,
            pending_count=1,
            total_proposals=6,
            approved_proposals=4,
            rejected_proposals=1,
            realm_name="work",
            realm_memory_count=3,
            realm_session_count=2,
            realm_governance_context="Focus on work memory boundaries.",
            active_user="ZAERA (guardian)",
            realm_access=True,
        )

        self.assertEqual(
            report,
            "\n".join(
                [
                    "Session: session-1",
                    # DECISION POINT: status reads the shared CURRENT_PHASE
                    # constant, so this expectation must move with the active phase.
                    f"Phase: {CURRENT_PHASE}",
                    "Mode: connected",
                    "Active user: ZAERA (guardian)",
                    "Realm: work",
                    "Realm access: allowed",
                    "Memory records: 3",
                    "Realm memory records: 3",
                    "Realm sessions: 2",
                    "Realm governance context: Focus on work memory boundaries.",
                    "Pending proposals: 1",
                    "Total proposals: 6",
                    "Approved proposals: 4",
                    "Rejected proposals: 1",
                    (
                        "Capabilities: respond, users, create-user, login, logout, whoami, "
                        "my-profile, view-profile, my-departments, assign-department, "
                        "unassign-department, assign-group, unassign-group, notify-department, "
                        "reflect, analyse, audit, guardian, faculties, realms, create-realm, "
                        "realm-context, switch-user, assign-realm, unassign-realm, my-log, "
                        "user-log, invite, join, invites, admin-surface, tool-registry, "
                        "faculty-registry, network-status, process-status, history, "
                        "proposal-history, routing-log, nammu-log, memory-log, body, status, "
                        "diagnostics, guardian-dismiss, guardian-clear-events, approve, "
                        "reject, forget, exit"
                    ),
                ]
            ),
        )

    def test_diagnostics_never_prints_api_key_value(self) -> None:
        config = Config(
            model_url="http://localhost:1234/v1",
            model_name="local-model",
            api_key="secret-token",
        )
        engine = Engine()
        session = Session(
            session_id="session-1",
            session_path=Path("C:/tmp/session-1.json"),
            context_summary=[],
        )

        report = build_diagnostics_report(config=config, engine=engine, session=session)

        self.assertIn("Body Report -", report)
        self.assertIn("Model:", report)
        self.assertIn("  URL: http://localhost:1234/v1", report)
        self.assertNotIn("secret-token", report)
        self.assertIn("Mode: fallback", report)


if __name__ == "__main__":
    unittest.main()
