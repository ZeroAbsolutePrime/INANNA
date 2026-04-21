from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.reflection import ReflectionEntry, ReflectiveMemory
from main import build_reflection_grounding, extract_reflection_proposal


class ReflectionTests(unittest.TestCase):
    def make_memory(self) -> tuple[Path, ReflectiveMemory]:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        return root, ReflectiveMemory(root / "self")

    def approve_entry(
        self,
        reflective_memory: ReflectiveMemory,
        observation: str,
        context: str,
        approved_by: str = "guardian",
    ) -> ReflectionEntry:
        entry = reflective_memory.propose(observation, context)
        reflective_memory.approve(entry, approved_by=approved_by)
        return entry

    def test_propose_returns_entry_with_generated_id(self) -> None:
        _, reflective_memory = self.make_memory()

        entry = reflective_memory.propose("Pattern", "Context")

        self.assertTrue(entry.entry_id.startswith("reflect-"))
        self.assertEqual(entry.observation, "Pattern")
        self.assertEqual(entry.context, "Context")
        self.assertTrue(entry.created_at)

    def test_propose_trims_fields(self) -> None:
        _, reflective_memory = self.make_memory()

        entry = reflective_memory.propose("  Pattern  ", "  Context  ")

        self.assertEqual(entry.observation, "Pattern")
        self.assertEqual(entry.context, "Context")

    def test_propose_does_not_write_file(self) -> None:
        _, reflective_memory = self.make_memory()

        reflective_memory.propose("Pattern", "Context")

        self.assertFalse(reflective_memory.reflection_path.exists())

    def test_approve_writes_one_jsonl_record(self) -> None:
        _, reflective_memory = self.make_memory()

        entry = self.approve_entry(reflective_memory, "Pattern", "Context", approved_by="ZAERA")

        lines = reflective_memory.reflection_path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        payload = json.loads(lines[0])
        self.assertEqual(payload["entry_id"], entry.entry_id)
        self.assertEqual(payload["observation"], "Pattern")
        self.assertEqual(payload["context"], "Context")
        self.assertEqual(payload["approved_by"], "ZAERA")
        self.assertTrue(payload["approved_at"])

    def test_approve_appends_in_order(self) -> None:
        _, reflective_memory = self.make_memory()

        first = self.approve_entry(reflective_memory, "First", "One")
        second = self.approve_entry(reflective_memory, "Second", "Two")

        entries = reflective_memory.load_all()
        self.assertEqual([entry.entry_id for entry in entries], [first.entry_id, second.entry_id])

    def test_load_all_returns_empty_when_file_missing(self) -> None:
        _, reflective_memory = self.make_memory()

        self.assertEqual(reflective_memory.load_all(), [])

    def test_load_all_skips_invalid_lines(self) -> None:
        _, reflective_memory = self.make_memory()
        reflective_memory.reflection_path.write_text(
            "\n".join(
                [
                    "not-json",
                    json.dumps(
                        {
                            "entry_id": "reflect-good",
                            "observation": "Useful pattern",
                            "context": "context",
                            "approved_at": "2026-04-21T10:00:00+00:00",
                            "approved_by": "guardian",
                            "created_at": "2026-04-21T09:00:00+00:00",
                        }
                    ),
                    json.dumps({"entry_id": "reflect-bad"}),
                ]
            ),
            encoding="utf-8",
        )

        entries = reflective_memory.load_all()

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].entry_id, "reflect-good")
        self.assertEqual(entries[0].observation, "Useful pattern")

    def test_count_matches_approved_entries(self) -> None:
        _, reflective_memory = self.make_memory()
        self.approve_entry(reflective_memory, "One", "A")
        self.approve_entry(reflective_memory, "Two", "B")

        self.assertEqual(reflective_memory.count(), 2)

    def test_format_for_display_reports_empty_memory(self) -> None:
        _, reflective_memory = self.make_memory()

        result = reflective_memory.format_for_display()

        self.assertEqual(
            result,
            "INANNA's self-knowledge is empty. No reflections have been approved yet.",
        )

    def test_format_for_display_includes_context_and_approval_date(self) -> None:
        _, reflective_memory = self.make_memory()
        entry = self.approve_entry(
            reflective_memory,
            "I tend toward structured formatting when reasoning about technical domains.",
            "observed across multiple code analysis sessions",
            approved_by="ZAERA",
        )

        result = reflective_memory.format_for_display()

        self.assertIn("INANNA's self-knowledge - 1 entry:", result)
        self.assertIn(entry.approved_at[:10], result)
        self.assertIn("structured formatting", result)
        self.assertIn("context: observed across multiple code analysis sessions", result)

    def test_extract_reflection_proposal_parses_tag(self) -> None:
        observation, context = extract_reflection_proposal(
            "Answer. [REFLECT: I become more careful in safety-sensitive domains. | context: repeated governance review sessions]"
        )

        self.assertEqual(
            observation,
            "I become more careful in safety-sensitive domains.",
        )
        self.assertEqual(context, "repeated governance review sessions")

    def test_extract_reflection_proposal_supports_multiline_tag(self) -> None:
        observation, context = extract_reflection_proposal(
            "Answer.\n[REFLECT: I summarize decisions clearly.\n| context: observed during multi-step operator work]"
        )

        self.assertEqual(observation, "I summarize decisions clearly.")
        self.assertEqual(context, "observed during multi-step operator work")

    def test_extract_reflection_proposal_returns_none_without_tag(self) -> None:
        observation, context = extract_reflection_proposal("No reflection here.")

        self.assertIsNone(observation)
        self.assertIsNone(context)

    def test_build_reflection_grounding_returns_empty_without_entries(self) -> None:
        _, reflective_memory = self.make_memory()

        self.assertEqual(build_reflection_grounding(reflective_memory), "")

    def test_build_reflection_grounding_uses_last_five_observations(self) -> None:
        _, reflective_memory = self.make_memory()
        for index in range(6):
            self.approve_entry(
                reflective_memory,
                f"Observation {index}",
                f"Context {index}",
            )

        grounding = build_reflection_grounding(reflective_memory)

        self.assertEqual(
            grounding,
            "Your self-knowledge: Observation 1; Observation 2; Observation 3; Observation 4; Observation 5",
        )

    def test_build_reflection_grounding_ignores_blank_observations(self) -> None:
        _, reflective_memory = self.make_memory()
        reflective_memory.approve(
            ReflectionEntry(
                entry_id="reflect-blank",
                observation="   ",
                context="context",
            )
        )
        self.approve_entry(reflective_memory, "Signal", "context")

        grounding = build_reflection_grounding(reflective_memory)

        self.assertEqual(grounding, "Your self-knowledge: Signal")


if __name__ == "__main__":
    unittest.main()
