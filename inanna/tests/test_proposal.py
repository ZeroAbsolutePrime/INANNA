from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.proposal import Proposal


class ProposalTests(unittest.TestCase):
    def test_create_and_resolve_proposal(self) -> None:
        with TemporaryDirectory() as temp_dir:
            proposal_dir = Path(temp_dir)
            proposal = Proposal(proposal_dir)
            created = proposal.create(
                what="Update memory",
                why="Keep context readable",
                payload={"session_id": "session-1", "summary_lines": ["user: hello"]},
            )
            resolved = proposal.resolve_next("approve")
            pending_count = proposal.pending_count()

        self.assertEqual(created["status"], "pending")
        self.assertEqual(resolved["status"], "approved")
        self.assertEqual(pending_count, 0)

    def test_pending_count_tracks_unresolved_records(self) -> None:
        with TemporaryDirectory() as temp_dir:
            proposal = Proposal(Path(temp_dir))
            proposal.create("One", "why", {"session_id": "a", "summary_lines": []})
            proposal.create("Two", "why", {"session_id": "b", "summary_lines": []})

            count = proposal.pending_count()

        self.assertEqual(count, 2)


if __name__ == "__main__":
    unittest.main()
