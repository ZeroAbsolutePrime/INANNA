from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.memory import Memory
from core.realm import RealmConfig
from identity import PROMPT, build_system_prompt


class RealmMemoryTests(unittest.TestCase):
    def test_build_system_prompt_with_non_default_realm_includes_realm_name(self) -> None:
        realm = RealmConfig(
            name="work",
            purpose="Work-related conversations and analysis.",
            created_at="2026-04-19T10:00:00",
            governance_context="Focus on work memory boundaries.",
        )

        prompt = build_system_prompt(realm)

        self.assertIn("Active realm: work.", prompt)
        self.assertIn("Realm purpose: Work-related conversations and analysis.", prompt)
        self.assertIn("Realm governance context: Focus on work memory boundaries.", prompt)

    def test_build_system_prompt_with_default_realm_is_unchanged(self) -> None:
        realm = RealmConfig(
            name="default",
            purpose="The default operational context.",
            created_at="2026-04-19T10:00:00",
            governance_context="Standard governance applies.",
        )

        self.assertEqual(build_system_prompt(realm), PROMPT)

    def test_build_system_prompt_with_none_is_unchanged(self) -> None:
        self.assertEqual(build_system_prompt(None), PROMPT)

    def test_write_memory_accepts_realm_name(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            memory = Memory(
                session_dir=root / "sessions",
                memory_dir=root / "memory",
            )
            memory.session_dir.mkdir()
            memory.memory_dir.mkdir()

            path = memory.write_memory(
                proposal_id="proposal-a",
                session_id="session-1",
                summary_lines=["user: hello"],
                approved_at="2026-04-19T10:00:00",
                realm_name="work",
            )

            self.assertTrue(path.exists())

    def test_memory_record_contains_realm_name_field(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            memory = Memory(
                session_dir=root / "sessions",
                memory_dir=root / "memory",
            )
            memory.session_dir.mkdir()
            memory.memory_dir.mkdir()

            path = memory.write_memory(
                proposal_id="proposal-a",
                session_id="session-1",
                summary_lines=["user: hello"],
                approved_at="2026-04-19T10:00:00",
                realm_name="work",
            )
            payload = json.loads(path.read_text(encoding="utf-8"))

            self.assertEqual(payload["realm_name"], "work")


if __name__ == "__main__":
    unittest.main()
