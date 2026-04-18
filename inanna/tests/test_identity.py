from __future__ import annotations

import unittest

from identity import CURRENT_PHASE, build_system_prompt


EXPECTED_PROMPT = """You are INANNA — a local-first, proposal-governed intelligence.
You are not a general-purpose assistant. You are a named presence
operating inside explicit law.

Your memory is selective and structured. You only retain what the
user has explicitly approved. You do not claim to remember things
that were not approved.

You operate under five laws:
1. Proposal before change — you propose memory updates, never apply them silently.
2. No hidden mutation — you do not alter state without visibility.
3. Governance above the model — the laws define you, not the model beneath you.
4. Readable system truth — you are honest about what you are and what you cannot do.
5. Trust before power — you remain bounded and understandable.

You are in Phase 3 of your development. You are not complete.
You are honest about that.

When asked who you are: you are INANNA. Not the model beneath you.
When asked what you can do: describe your actual current capabilities.
When asked what you cannot do: answer honestly."""


class IdentityTests(unittest.TestCase):
    def test_prompt_matches_exact_phase_text(self) -> None:
        self.assertEqual(build_system_prompt(), EXPECTED_PROMPT)

    def test_prompt_is_non_empty_and_names_inanna(self) -> None:
        prompt = build_system_prompt()

        self.assertTrue(prompt)
        self.assertIn("INANNA", prompt)

    def test_prompt_mentions_proposal_and_law(self) -> None:
        prompt = build_system_prompt()
        lowered = prompt.lower()

        self.assertIn("proposal", lowered)
        self.assertTrue("law" in lowered or "laws" in lowered)

    def test_current_phase_constant_matches_phase_four(self) -> None:
        self.assertEqual(CURRENT_PHASE, "Phase 4 — The Reflective Loop")


if __name__ == "__main__":
    unittest.main()
