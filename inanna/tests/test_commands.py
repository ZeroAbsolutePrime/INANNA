from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from config import Config
from core.memory import Memory
from core.proposal import Proposal
from core.session import Engine, Session
from core.state import StateReport
from main import handle_command


class CommandTests(unittest.TestCase):
    def make_runtime(self) -> tuple[Session, Memory, Proposal, StateReport, Engine, dict, Config]:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        session_dir = root / "sessions"
        memory_dir = root / "memory"
        proposal_dir = root / "proposals"
        session_dir.mkdir()
        memory_dir.mkdir()
        proposal_dir.mkdir()

        session = Session.create(session_dir=session_dir, context_summary=[])
        memory = Memory(session_dir=session_dir, memory_dir=memory_dir)
        proposal = Proposal(proposal_dir=proposal_dir)
        state_report = StateReport()
        engine = Engine()
        startup_context = {"summary_lines": [], "memory_count": 0, "session_count": 0}
        config = Config(model_url="", model_name="", api_key="")
        return session, memory, proposal, state_report, engine, startup_context, config

    def test_status_returns_session_line(self) -> None:
        session, memory, proposal, state_report, engine, startup_context, config = self.make_runtime()

        result = handle_command(
            "status",
            session,
            memory,
            proposal,
            state_report,
            engine,
            startup_context,
            config,
        )

        self.assertIn("Session:", result)

    def test_diagnostics_returns_model_url_line(self) -> None:
        session, memory, proposal, state_report, engine, startup_context, config = self.make_runtime()

        result = handle_command(
            "diagnostics",
            session,
            memory,
            proposal,
            state_report,
            engine,
            startup_context,
            config,
        )

        self.assertIn("Model URL:", result)

    def test_history_with_no_proposals_returns_zero_total(self) -> None:
        session, memory, proposal, state_report, engine, startup_context, config = self.make_runtime()

        result = handle_command(
            "history",
            session,
            memory,
            proposal,
            state_report,
            engine,
            startup_context,
            config,
        )

        self.assertIn("0 total", result)
        self.assertIn("No proposals recorded yet.", result)

    def test_memory_log_with_no_memory_returns_zero_records(self) -> None:
        session, memory, proposal, state_report, engine, startup_context, config = self.make_runtime()

        result = handle_command(
            "memory-log",
            session,
            memory,
            proposal,
            state_report,
            engine,
            startup_context,
            config,
        )

        self.assertIn("0 records", result)
        self.assertIn("No approved memory records yet.", result)

    def test_reflect_with_empty_context_returns_no_memory_message(self) -> None:
        session, memory, proposal, state_report, engine, startup_context, config = self.make_runtime()

        result = handle_command(
            "reflect",
            session,
            memory,
            proposal,
            state_report,
            engine,
            startup_context,
            config,
        )

        self.assertEqual(
            result,
            "inanna> [memory fallback] I hold no approved memory of our prior conversations yet.",
        )
        self.assertEqual(proposal.pending_count(), 0)

    def test_approve_with_no_pending_proposals_returns_honest_message(self) -> None:
        session, memory, proposal, state_report, engine, startup_context, config = self.make_runtime()

        result = handle_command(
            "approve",
            session,
            memory,
            proposal,
            state_report,
            engine,
            startup_context,
            config,
        )

        self.assertEqual(result, "No pending proposals.")

    def test_unknown_input_is_treated_as_conversation(self) -> None:
        session, memory, proposal, state_report, engine, startup_context, config = self.make_runtime()

        result = handle_command(
            "hello there",
            session,
            memory,
            proposal,
            state_report,
            engine,
            startup_context,
            config,
        )

        self.assertIsInstance(result, str)
        self.assertIn("assistant>", result)


if __name__ == "__main__":
    unittest.main()
