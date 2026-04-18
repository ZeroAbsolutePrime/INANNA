from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from config import Config
from core.memory import Memory
from core.proposal import Proposal
from core.session import Engine, Session
from core.state import StateReport
from main import STARTUP_COMMANDS, handle_command, startup_commands_line


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

    def write_memory_record(self, memory: Memory, memory_id: str = "proposal-a") -> None:
        memory.write_memory(
            proposal_id=memory_id,
            session_id="session-1",
            summary_lines=["user: hello", "assistant: welcome back"],
            approved_at="2026-04-19T10:00:00",
        )

    def run_forget_command(
        self,
        session: Session,
        memory: Memory,
        proposal: Proposal,
        state_report: StateReport,
        engine: Engine,
        startup_context: dict,
        config: Config,
        answers: list[str],
    ) -> tuple[str, str, list[str]]:
        prompts: list[str] = []
        answer_iter = iter(answers)

        def fake_input(prompt: str) -> str:
            prompts.append(prompt)
            return next(answer_iter)

        output = io.StringIO()
        with patch("builtins.input", side_effect=fake_input), redirect_stdout(output):
            result = handle_command(
                "forget",
                session,
                memory,
                proposal,
                state_report,
                engine,
                startup_context,
                config,
            )
        return result, output.getvalue(), prompts

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
        self.assertIn("forget", result)

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

    def test_audit_returns_summary_prefix_and_has_no_side_effects(self) -> None:
        session, memory, proposal, state_report, engine, startup_context, config = self.make_runtime()

        result = handle_command(
            "audit",
            session,
            memory,
            proposal,
            state_report,
            engine,
            startup_context,
            config,
        )

        self.assertTrue(result.startswith("inanna> [audit summary] "))
        self.assertEqual(proposal.pending_count(), 0)
        self.assertEqual(memory.memory_count(), 0)

    def test_startup_commands_line_lists_expected_commands(self) -> None:
        self.assertEqual(
            STARTUP_COMMANDS,
            (
                "reflect",
                "audit",
                "history",
                "memory-log",
                "status",
                "diagnostics",
                "approve",
                "reject",
                "forget",
                "exit",
            ),
        )
        self.assertEqual(
            startup_commands_line(),
            "Commands: reflect, audit, history, memory-log, status, diagnostics, approve, reject, forget, exit",
        )

    def test_forget_cancel_returns_no_memory_removed(self) -> None:
        session, memory, proposal, state_report, engine, startup_context, config = self.make_runtime()
        self.write_memory_record(memory)

        result, output, prompts = self.run_forget_command(
            session,
            memory,
            proposal,
            state_report,
            engine,
            startup_context,
            config,
            ["cancel"],
        )

        self.assertEqual(result, "No memory removed.")
        self.assertIn("Memory log (1 records):", output)
        self.assertEqual(
            prompts,
            ['Which memory record to remove? Enter memory_id or "cancel":'],
        )
        self.assertEqual(memory.memory_count(), 1)
        self.assertEqual(proposal.history_report()["total"], 0)

    def test_forget_approve_removes_memory_after_inline_proposal(self) -> None:
        session, memory, proposal, state_report, engine, startup_context, config = self.make_runtime()
        self.write_memory_record(memory, "proposal-a")

        result, output, prompts = self.run_forget_command(
            session,
            memory,
            proposal,
            state_report,
            engine,
            startup_context,
            config,
            ["proposal-a", "approve"],
        )

        history = proposal.history_report()
        self.assertEqual(result, "Memory record proposal-a removed.")
        self.assertIn("[PROPOSAL]", output)
        self.assertEqual(
            prompts,
            [
                'Which memory record to remove? Enter memory_id or "cancel":',
                'Type "approve" to confirm removal or "reject" to cancel:',
            ],
        )
        self.assertEqual(memory.memory_count(), 0)
        self.assertEqual(history["approved"], 1)
        self.assertEqual(history["rejected"], 0)
        self.assertEqual(history["records"][0]["payload"], {"memory_id": "proposal-a", "action": "forget"})

    def test_forget_reject_retains_memory(self) -> None:
        session, memory, proposal, state_report, engine, startup_context, config = self.make_runtime()
        self.write_memory_record(memory, "proposal-a")

        result, output, prompts = self.run_forget_command(
            session,
            memory,
            proposal,
            state_report,
            engine,
            startup_context,
            config,
            ["proposal-a", "reject"],
        )

        history = proposal.history_report()
        self.assertEqual(result, "Memory record retained.")
        self.assertIn("[PROPOSAL]", output)
        self.assertEqual(
            prompts,
            [
                'Which memory record to remove? Enter memory_id or "cancel":',
                'Type "approve" to confirm removal or "reject" to cancel:',
            ],
        )
        self.assertEqual(memory.memory_count(), 1)
        self.assertEqual(history["approved"], 0)
        self.assertEqual(history["rejected"], 1)

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
