from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
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

    def history_report(self) -> dict[str, Any]:
        records = self.list_records()
        approved = [record for record in records if record["status"] == "approved"]
        rejected = [record for record in records if record["status"] == "rejected"]
        pending = [record for record in records if record["status"] == "pending"]
        return {
            "total": len(records),
            "approved": len(approved),
            "rejected": len(rejected),
            "pending": len(pending),
            "records": sorted(records, key=lambda record: record["timestamp"]),
        }

    def resolve_next(self, decision: str) -> dict[str, Any] | None:
        # Sort newest-first: the most recent proposal is what the user just approved
        pending = sorted(
            self.pending_records(),
            key=lambda record: record["timestamp"],
            reverse=True,  # newest first
        )
        if not pending:
            return None

        record = pending[0]
        record["status"] = "approved" if decision == "approve" else "rejected"
        record["resolved_at"] = utc_now()
        self._write_record(record)

        # Auto-reject any older stale pending proposals to keep queue clean
        for stale in pending[1:]:
            stale["status"] = "rejected"
            stale["resolved_at"] = utc_now()
            self._write_record(stale)

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
