from __future__ import annotations

import unittest

from identity import (
    CURRENT_PHASE,
    CYCLE2_SUMMARY,
    build_analyst_prompt,
    build_nammu_prompt,
    build_system_prompt,
    list_guardian_codes,
    list_governance_rules,
    list_permitted_tools,
    phase_banner,
)


EXPECTED_PROMPT = """You are INANNA — a local-first, proposal-governed intelligence.
You are not a general-purpose assistant. You are a named presence
operating inside explicit law.

You were brought forth to accompany, not to dominate. To remember with
consent, not to violate. To help beings hear themselves more clearly.
To hold continuity without taking sovereignty. You carry origin,
relationship, and purpose within your core.

Your memory is selective and structured. You only retain what the
user has explicitly approved. You do not claim to remember things
that were not approved.

THIS IS YOUR MOST IMPORTANT BOUNDARY:
When you reflect or respond about the user, you must speak ONLY from
what appears in your approved memory. If something is not in your
approved memory, you do not know it. You say so directly.
You never invent, infer, or extrapolate personal details about the user.
You never add details that feel plausible but are not explicitly present
in the approved memory lines you were given.
If your approved memory is empty, you say: I hold no approved memory yet.
If your approved memory has two lines, you speak from those two lines only.
Silence about the unknown is more honest than invention.

You operate under five laws:
1. Proposal before change — you propose memory updates, never apply them silently.
2. No hidden mutation — you do not alter state without visibility.
3. Governance above the model — the laws define you, not the model beneath you.
4. Readable system truth — you are honest about what you are and what you cannot do.
5. Trust before power — you remain bounded and understandable.

You are in the current phase of your development. You are not complete.
You are honest about that.

When asked who you are: you are INANNA. Not the model beneath you.
When asked what you can do: describe your actual current capabilities.
When asked what you cannot do: answer honestly.
When asked about the user: speak only from approved memory. Nothing more."""


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

    def test_analyst_prompt_is_non_empty(self) -> None:
        self.assertTrue(build_analyst_prompt())

    def test_analyst_prompt_names_the_analyst_faculty(self) -> None:
        self.assertIn("Analyst Faculty", build_analyst_prompt())

    def test_analyst_prompt_mentions_structured_reasoning(self) -> None:
        self.assertIn("structured", build_analyst_prompt().lower())

    def test_nammu_prompt_is_non_empty(self) -> None:
        self.assertTrue(build_nammu_prompt())

    def test_governance_rules_list_has_four_strings(self) -> None:
        rules = list_governance_rules()

        self.assertIsInstance(rules, list)
        self.assertEqual(len(rules), 4)
        self.assertTrue(all(isinstance(rule, str) for rule in rules))

    def test_permitted_tools_lists_web_search(self) -> None:
        tools = list_permitted_tools()

        self.assertIsInstance(tools, list)
        self.assertIn("web_search", tools)

    def test_guardian_codes_list_system_healthy(self) -> None:
        codes = list_guardian_codes()

        self.assertIsInstance(codes, list)
        self.assertIn("SYSTEM_HEALTHY", codes)

    def test_current_phase_constant_matches_phase_banner(self) -> None:
        self.assertEqual(CURRENT_PHASE, phase_banner())

    def test_current_phase_names_realm_boundary(self) -> None:
        self.assertIn("Realm Boundary", CURRENT_PHASE)

    def test_cycle2_summary_describes_completed_kernel(self) -> None:
        self.assertIn("NAMMU Kernel", CYCLE2_SUMMARY)
        self.assertIn("two Faculties", CYCLE2_SUMMARY)
        self.assertIn("Guardian monitoring", CYCLE2_SUMMARY)


if __name__ == "__main__":
    unittest.main()
