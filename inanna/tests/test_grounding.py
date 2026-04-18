from __future__ import annotations

import unittest

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


if __name__ == "__main__":
    unittest.main()
