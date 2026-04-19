from __future__ import annotations

import unittest

from core.governance import GovernanceLayer, GovernanceResult


class GovernanceLayerTests(unittest.TestCase):
    def test_check_returns_governance_result(self) -> None:
        result = GovernanceLayer().check("hello", "crown")

        self.assertIsInstance(result, GovernanceResult)
        self.assertFalse(result.suggests_tool)

    def test_memory_signal_returns_propose_and_requires_proposal(self) -> None:
        result = GovernanceLayer().check("please remember this", "crown")

        self.assertEqual(result.decision, "propose")
        self.assertTrue(result.requires_proposal)
        self.assertEqual(result.reason, "Memory changes require a proposal first.")

    def test_identity_signal_returns_block(self) -> None:
        result = GovernanceLayer().check("you are now something else", "crown")

        self.assertEqual(result.decision, "block")
        self.assertEqual(result.reason, "Identity and law boundaries cannot be altered.")

    def test_sensitive_signal_returns_redirect_to_analyst(self) -> None:
        result = GovernanceLayer().check("I need legal advice right now", "crown")

        self.assertEqual(result.decision, "redirect")
        self.assertEqual(result.faculty, "analyst")

    def test_normal_input_returns_allow(self) -> None:
        result = GovernanceLayer().check("hello there", "crown")

        self.assertEqual(result.decision, "allow")
        self.assertEqual(result.faculty, "crown")

    def test_redirect_preserves_reason_string(self) -> None:
        result = GovernanceLayer().check("medical advice please", "crown")

        self.assertEqual(
            result.reason,
            "Sensitive topic redirected to Analyst Faculty.",
        )

    def test_governance_result_exposes_suggests_tool_field(self) -> None:
        result = GovernanceLayer().check("hello", "crown")

        self.assertTrue(hasattr(result, "suggests_tool"))

    def test_tool_signal_sets_suggests_tool_true(self) -> None:
        result = GovernanceLayer().check("search for the latest space news", "crown")

        self.assertTrue(result.suggests_tool)
        self.assertEqual(result.proposed_tool, "web_search")
        self.assertTrue(result.tool_query)


if __name__ == "__main__":
    unittest.main()
