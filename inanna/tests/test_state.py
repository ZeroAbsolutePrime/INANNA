from __future__ import annotations

import unittest
from pathlib import Path

from config import Config
from core.session import Engine, Session
from core.state import StateReport
from main import build_diagnostics_report


class StateTests(unittest.TestCase):
    def test_report_is_honest_and_readable(self) -> None:
        report = StateReport().render(
            session_id="session-1",
            mode="connected",
            memory_count=3,
            pending_count=1,
        )

        self.assertEqual(
            report,
            "\n".join(
                [
                    "Session: session-1",
                    # DECISION POINT: status reads the shared CURRENT_PHASE
                    # constant, so this expectation must move with the active phase.
                    "Phase: Phase 6 — The Honest Boundary",
                    "Mode: connected",
                    "Memory records: 3",
                    "Pending proposals: 1",
                    "Capabilities: respond, reflect, status, diagnostics, approve, reject, exit",
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

        self.assertIn("API key: set", report)
        self.assertNotIn("secret-token", report)
        self.assertIn("Mode: fallback", report)


if __name__ == "__main__":
    unittest.main()
