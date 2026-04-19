from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from config import Config
from core.memory import Memory
from core.nammu import IntentClassifier
from core.operator import ToolResult
from core.proposal import Proposal
from core.realm import RealmManager
from core.session import AnalystFaculty, Engine, Session
from core.state import StateReport
from main import STARTUP_COMMANDS, handle_command, startup_commands_line


class SuccessfulToolOperator:
    def execute(self, tool: str, params: dict[str, str]) -> ToolResult:
        return ToolResult(
            tool=tool,
            query=params.get("query", ""),
            success=True,
            data={
                "abstract": "Current result abstract",
                "answer": "Current result answer",
                "related": [],
            },
        )


class FlakySummaryEngine:
    def __init__(self) -> None:
        self._connected = True
        self._mode = "connected"

    @property
    def mode(self) -> str:
        return self._mode

    def respond(self, context_summary, conversation) -> str:
        del context_summary
        del conversation
        self._connected = False
        self._mode = "fallback"
        return "Model call failed, so fallback mode continued safely: network down"


class CommandTests(unittest.TestCase):
    def make_runtime(
        self,
    ) -> tuple[
        Session,
        Memory,
        Proposal,
        StateReport,
        Engine,
        AnalystFaculty,
        IntentClassifier,
        list[dict[str, str]],
        dict,
        Config,
    ]:
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
        analyst = AnalystFaculty()
        classifier = IntentClassifier(engine)
        routing_log: list[dict[str, str]] = []
        startup_context = {"summary_lines": [], "memory_count": 0, "session_count": 0}
        config = Config(model_url="", model_name="", api_key="")
        return (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

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
        analyst: AnalystFaculty,
        classifier: IntentClassifier,
        routing_log: list[dict[str, str]],
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
                analyst,
                classifier,
                routing_log,
                startup_context,
                config,
            )
        return result, output.getvalue(), prompts

    def test_status_returns_session_line(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "status",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertIn("Session:", result)
        self.assertIn("routing-log", result)

    def test_diagnostics_returns_model_url_line(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "diagnostics",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertIn("Model URL:", result)

    def test_history_with_no_proposals_returns_zero_total(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "history",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertIn("0 total", result)
        self.assertIn("No proposals recorded yet.", result)

    def test_routing_log_with_no_decisions_returns_zero_total(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "routing-log",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertIn("NAMMU Routing Log (0 decisions)", result)
        self.assertIn("No routing decisions recorded yet.", result)

    def test_memory_log_with_no_memory_returns_zero_records(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "memory-log",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertIn("0 records", result)
        self.assertIn("No approved memory records yet.", result)

    def test_audit_returns_summary_prefix_and_has_no_side_effects(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "audit",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertTrue(result.startswith("inanna> [audit summary] "))
        self.assertEqual(proposal.pending_count(), 0)
        self.assertEqual(memory.memory_count(), 0)
        self.assertEqual(len(routing_log), 0)

    def test_startup_commands_line_lists_expected_commands(self) -> None:
        self.assertEqual(
            STARTUP_COMMANDS,
            (
                "reflect",
                "analyse",
                "audit",
                "guardian",
                "realms",
                "history",
                "routing-log",
                "nammu-log",
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
            (
                "Commands: reflect, analyse, audit, guardian, realms, history, "
                "routing-log, nammu-log, memory-log, status, diagnostics, approve, reject, "
                "forget, exit"
            ),
        )

    def test_realms_command_lists_available_realms(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        realm_manager = RealmManager(session.session_path.parent.parent / "data")
        active_realm = realm_manager.ensure_default_realm()
        realm_manager.create_realm("work", purpose="Work-related conversations and analysis.")

        result = handle_command(
            "realms",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            realm_manager=realm_manager,
            active_realm=active_realm,
        )

        self.assertIn("realms > Available realms (2):", result)
        self.assertIn("[default]  The default operational context.", result)
        self.assertIn("[work]  Work-related conversations and analysis.", result)
        self.assertIn("Active: default", result)

    def test_nammu_log_with_no_history_reports_empty_persistent_state(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "nammu-log",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertIn("NAMMU Memory (0 routing, 0 governance):", result)
        self.assertIn("No persisted routing history yet.", result)
        self.assertIn("No persisted governance history yet.", result)

    def test_guardian_returns_report_without_side_effects(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "guardian",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertTrue(result.startswith("guardian > Guardian Report ("))
        self.assertIn("SYSTEM_HEALTHY", result)
        self.assertEqual(proposal.pending_count(), 0)
        self.assertEqual(memory.memory_count(), 0)
        self.assertEqual(session.events, [])

    def test_tool_resilience_returns_clean_operator_message(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            _engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        engine = FlakySummaryEngine()
        proposal.create(
            what="web_search tool use",
            why="test",
            payload={
                "action": "tool_use",
                "tool": "web_search",
                "query": "latest weather",
                "original_input": "what is the weather today",
                "session_id": session.session_id,
            },
        )

        result = handle_command(
            "approve",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            operator=SuccessfulToolOperator(),
            guardian_metrics={"governance_blocks": 0, "tool_executions": 0},
        )

        self.assertIn("operator > search result:", result)
        self.assertIn("operator > model unavailable to summarize. Raw results shown above.", result)
        self.assertNotIn("inanna >", result)

    def test_forget_cancel_returns_no_memory_removed(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        self.write_memory_record(memory)

        result, output, prompts = self.run_forget_command(
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
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
        self.assertEqual(len(routing_log), 0)

    def test_forget_approve_removes_memory_after_inline_proposal(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        self.write_memory_record(memory, "proposal-a")

        result, output, prompts = self.run_forget_command(
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
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
        self.assertEqual(
            history["records"][0]["payload"],
            {"memory_id": "proposal-a", "action": "forget"},
        )

    def test_forget_reject_retains_memory(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        self.write_memory_record(memory, "proposal-a")

        result, output, prompts = self.run_forget_command(
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
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
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "reflect",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertEqual(
            result,
            "inanna> [memory fallback] I hold no approved memory of our prior conversations yet.",
        )
        self.assertEqual(proposal.pending_count(), 0)
        self.assertEqual(len(routing_log), 0)

    def test_approve_with_no_pending_proposals_returns_honest_message(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "approve",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertEqual(result, "No pending proposals.")

    def test_explicit_analyse_remains_direct_override(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "analyse What patterns do you see?",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertTrue(result.startswith("analyst > [analysis fallback] "))
        self.assertNotIn("nammu >", result)
        self.assertEqual(proposal.pending_count(), 1)
        self.assertEqual(len(routing_log), 0)

    def test_unknown_input_is_auto_routed_to_crown_and_logged(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "hello there",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertIn("nammu > routing to crown faculty", result)
        self.assertIn("inanna >", result)
        self.assertEqual(proposal.pending_count(), 1)
        self.assertEqual(len(routing_log), 1)
        self.assertEqual(routing_log[0]["route"], "crown")

    def test_normal_input_can_be_auto_routed_to_analyst_and_logged(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "Explain why governance needs readable limits",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertIn("nammu > routing to analyst faculty", result)
        self.assertIn("analyst > [analysis fallback] ", result)
        self.assertEqual(proposal.pending_count(), 1)
        self.assertEqual(len(routing_log), 1)
        self.assertEqual(routing_log[0]["route"], "analyst")

    def test_routing_log_reports_recorded_decisions(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        handle_command(
            "hello there",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        result = handle_command(
            "routing-log",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertIn("NAMMU Routing Log (1 decisions):", result)
        self.assertIn("[crown]", result)
        self.assertIn("hello there", result)


if __name__ == "__main__":
    unittest.main()
