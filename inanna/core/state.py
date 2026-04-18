from __future__ import annotations

import unittest


class StateReport:
    def render(self, session_id: str, memory_count: int, pending_count: int) -> str:
        lines = [
            "Readable State Report",
            f"Current session ID: {session_id}",
            f"Memories loaded: {memory_count}",
            f"Pending proposals: {pending_count}",
            "Allowed right now:",
            "- Continue the current text conversation.",
            "- Read prior session logs to assemble bounded startup context.",
            "- Write session logs for this active session.",
            "- Generate proposals for future memory changes.",
            "- Apply or reject pending proposals only when the user types approve or reject.",
            "Not allowed right now:",
            "- Change memory without a proposal and user approval.",
            "- Change behavior without a logged proposal.",
            "- Use web, database, authentication, deployment, or multi-user features in the current phase.",
        ]
        return "\n".join(lines)


# Phase 2 policy: tests remain inside component modules until Phase 3 creates a
# dedicated test layout.
class StateComponentTests(unittest.TestCase):
    def test_report_is_honest_and_readable(self) -> None:
        report = StateReport().render(
            session_id="session-1",
            memory_count=3,
            pending_count=1,
        )

        self.assertIn("Current session ID: session-1", report)
        self.assertIn("Memories loaded: 3", report)
        self.assertIn("Pending proposals: 1", report)
        self.assertIn("Not allowed right now:", report)


if __name__ == "__main__":
    unittest.main()
