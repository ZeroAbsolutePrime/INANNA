from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.orchestration import OrchestrationEngine, OrchestrationPlan, OrchestrationStep
from core.proposal import Proposal
from core.session import Session
from main import create_orchestration_proposal


class OrchestrationTests(unittest.TestCase):
    def test_orchestration_engine_can_be_instantiated(self) -> None:
        engine = OrchestrationEngine(Path("faculties.json"))
        self.assertIsInstance(engine, OrchestrationEngine)

    def test_detect_orchestration_returns_plan_for_security_explain_input(self) -> None:
        engine = OrchestrationEngine(Path("faculties.json"))

        plan = engine.detect_orchestration("Analyze security and explain simply.")

        self.assertIsNotNone(plan)
        self.assertIsInstance(plan, OrchestrationPlan)

    def test_detect_orchestration_returns_none_for_unrelated_input(self) -> None:
        engine = OrchestrationEngine(Path("faculties.json"))

        plan = engine.detect_orchestration("Tell me a short poem about spring.")

        self.assertIsNone(plan)

    def test_format_synthesis_prompt_includes_previous_output(self) -> None:
        engine = OrchestrationEngine(Path("faculties.json"))
        step = OrchestrationStep("crown", "synthesize", "sentinel", "user")

        prompt = engine.format_synthesis_prompt(
            "Analyze security and explain simply.",
            "Potential SQL injection risk in login flow.",
            step,
        )

        self.assertIn("Potential SQL injection risk in login flow.", prompt)

    def test_format_synthesis_prompt_includes_user_input(self) -> None:
        engine = OrchestrationEngine(Path("faculties.json"))
        step = OrchestrationStep("crown", "synthesize", "sentinel", "user")

        prompt = engine.format_synthesis_prompt(
            "Analyze security and explain simply.",
            "Potential SQL injection risk in login flow.",
            step,
        )

        self.assertIn("Analyze security and explain simply.", prompt)

    def test_orchestration_plan_has_correct_step_count(self) -> None:
        engine = OrchestrationEngine(Path("faculties.json"))
        plan = engine.detect_orchestration("Analyze security and explain simply.")

        assert plan is not None
        self.assertEqual(len(plan.steps), 2)

    def test_orchestration_step_fields_are_preserved(self) -> None:
        step = OrchestrationStep("sentinel", "analyze", "user", "crown")

        self.assertEqual(step.faculty, "sentinel")
        self.assertEqual(step.purpose, "analyze")
        self.assertEqual(step.input_from, "user")
        self.assertEqual(step.output_to, "crown")

    def test_create_orchestration_proposal_uses_special_line(self) -> None:
        engine = OrchestrationEngine(Path("faculties.json"))
        plan = engine.detect_orchestration("Analyze security and explain simply.")
        assert plan is not None

        with TemporaryDirectory() as temp_dir:
            proposal_dir = Path(temp_dir) / "proposals"
            session_dir = Path(temp_dir) / "sessions"
            proposal_dir.mkdir()
            session_dir.mkdir()
            proposal = Proposal(proposal_dir=proposal_dir)
            session = Session.create(session_dir=session_dir, context_summary=[])

            created = create_orchestration_proposal(
                proposal=proposal,
                session=session,
                user_input="Analyze security and explain simply.",
                plan=plan,
            )

        self.assertIn("[ORCHESTRATION PROPOSAL]", created["line"])
        self.assertIn("SENTINEL -> CROWN", created["line"])


if __name__ == "__main__":
    unittest.main()
