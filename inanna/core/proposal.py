from __future__ import annotations

import json
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Proposal:
    def __init__(self, proposal_dir: Path) -> None:
        self.proposal_dir = proposal_dir

    def create(self, what: str, why: str, payload: dict[str, Any]) -> dict[str, Any]:
        record = {
            "proposal_id": f"proposal-{uuid.uuid4().hex[:8]}",
            "timestamp": utc_now(),
            "what": what,
            "why": why,
            "status": "pending",
            "payload": payload,
        }
        self._write_record(record)
        return {**record, "line": self.format_line(record)}

    def pending_count(self) -> int:
        return len(self.pending_records())

    def pending_records(self) -> list[dict[str, Any]]:
        return [record for record in self.list_records() if record["status"] == "pending"]

    def resolve_next(self, decision: str) -> dict[str, Any] | None:
        pending = sorted(self.pending_records(), key=lambda record: record["timestamp"])
        if not pending:
            return None

        # DECISION POINT: The phase document does not specify which proposal
        # `approve` or `reject` should target when several are pending, so the
        # oldest pending proposal is resolved first.
        record = pending[0]
        record["status"] = "approved" if decision == "approve" else "rejected"
        record["resolved_at"] = utc_now()
        self._write_record(record)
        return {**record, "line": self.format_line(record)}

    def list_records(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for path in sorted(self.proposal_dir.glob("*.txt")):
            records.append(self._read_record(path))
        return records

    def format_line(self, record: dict[str, Any]) -> str:
        return (
            f"[PROPOSAL] {record['timestamp']} | {record['what']} | "
            f"{record['why']} | status: {record['status']}"
        )

    def _path_for(self, proposal_id: str) -> Path:
        return self.proposal_dir / f"{proposal_id}.txt"

    def _write_record(self, record: dict[str, Any]) -> None:
        path = self._path_for(record["proposal_id"])
        body = json.dumps(record, indent=2)
        path.write_text(f"{self.format_line(record)}\n{body}\n", encoding="utf-8")

    def _read_record(self, path: Path) -> dict[str, Any]:
        lines = path.read_text(encoding="utf-8").splitlines()
        return json.loads("\n".join(lines[1:]))


# DECISION POINT: CURRENT_PHASE.md requires unit tests to pass but only lists
# component file locations, so the basic tests live inside the component module.
class ProposalComponentTests(unittest.TestCase):
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
