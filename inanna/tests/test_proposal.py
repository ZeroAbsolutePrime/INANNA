from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

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

    def test_history_report_tracks_approved_rejected_and_pending_counts(self) -> None:
        with TemporaryDirectory() as temp_dir:
            proposal = Proposal(Path(temp_dir))
            with patch(
                "core.proposal.utc_now",
                side_effect=[
                    "2026-04-18T20:21:39",
                    "2026-04-18T20:40:10",
                    "2026-04-18T20:41:13",
                    "2026-04-18T20:45:00",
                    "2026-04-18T20:46:00",
                ],
            ):
                first = proposal.create("First update", "why", {"session_id": "a", "summary_lines": []})
                second = proposal.create("Second update", "why", {"session_id": "b", "summary_lines": []})
                third = proposal.create("Third update", "why", {"session_id": "c", "summary_lines": []})
                proposal.resolve_next("approve")
                proposal.resolve_next("reject")

            report = proposal.history_report()

        self.assertEqual(report["total"], 3)
        self.assertEqual(report["approved"], 1)
        self.assertEqual(report["rejected"], 1)
        self.assertEqual(report["pending"], 1)
        self.assertEqual(
            [record["proposal_id"] for record in report["records"]],
            [first["proposal_id"], second["proposal_id"], third["proposal_id"]],
        )
        self.assertEqual(
            [record["status"] for record in report["records"]],
            ["approved", "rejected", "pending"],
        )


if __name__ == "__main__":
    unittest.main()
