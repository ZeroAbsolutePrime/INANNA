from __future__ import annotations

import unittest

from core.realm import RealmConfig
from core.session import Engine


class GroundingTests(unittest.TestCase):
    def test_build_grounding_turn_returns_assistant_turn_when_memory_is_empty(self) -> None:
        engine = Engine()

        grounding_turn = engine._build_grounding_turn([])

        self.assertEqual(grounding_turn["role"], "assistant")
        self.assertIn("no approved memory", grounding_turn["content"])

    def test_build_grounding_turn_contains_boundary_assertion_when_memory_exists(self) -> None:
        engine = Engine()

        grounding_turn = engine._build_grounding_turn(["user: hello"])

        self.assertIn("I will not add, invent, or infer", grounding_turn["content"])

    def test_grounding_turn_is_message_index_one_when_memory_is_empty(self) -> None:
        engine = Engine()

        messages = engine._build_messages(
            context_summary=[],
            conversation=[{"role": "user", "content": "what do you know about me?"}],
        )

        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "assistant")
        self.assertIn("no approved memory", messages[1]["content"])

    def test_grounding_turn_is_message_index_one_when_memory_exists(self) -> None:
        engine = Engine()

        messages = engine._build_messages(
            context_summary=["user: hello"],
            conversation=[{"role": "user", "content": "what do you know about me?"}],
        )

        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "assistant")
        self.assertIn("I will not add, invent, or infer", messages[1]["content"])

    def test_cross_realm_memory_line_is_labeled_in_grounding_turn(self) -> None:
        engine = Engine(
            realm=RealmConfig(
                name="work",
                purpose="Work-related conversations and analysis.",
                created_at="2026-04-19T10:00:00",
                governance_context="Focus on work memory boundaries.",
            )
        )

        grounding_turn = engine._build_grounding_turn(
            [{"text": "user: hello", "realm_name": "research"}]
        )

        self.assertIn("user: hello (from realm: research)", grounding_turn["content"])


if __name__ == "__main__":
    unittest.main()
