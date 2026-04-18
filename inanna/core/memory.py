from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Memory:
    def __init__(self, session_dir: Path, memory_dir: Path, max_lines: int = 10) -> None:
        self.session_dir = session_dir
        self.memory_dir = memory_dir
        self.max_lines = max_lines

    def load_startup_context(self) -> dict[str, Any]:
        memory_records = self._load_memory_records()
        session_records = self._load_session_records()

        summary_lines: list[str] = []
        for record in memory_records:
            for line in record.get("summary_lines", []):
                self._append_unique(summary_lines, line)
                if len(summary_lines) >= self.max_lines:
                    return self._startup_payload(
                        summary_lines=summary_lines,
                        memory_count=len(memory_records),
                        session_count=len(session_records),
                    )

        for record in reversed(session_records):
            for line in self._session_lines(record):
                self._append_unique(summary_lines, line)
                if len(summary_lines) >= self.max_lines:
                    break
            if len(summary_lines) >= self.max_lines:
                break

        return self._startup_payload(
            summary_lines=summary_lines,
            memory_count=len(memory_records),
            session_count=len(session_records),
        )

    def build_candidate(
        self,
        session_id: str,
        events: list[dict[str, str]],
    ) -> dict[str, Any]:
        return {
            "session_id": session_id,
            "created_at": utc_now(),
            "summary_lines": self._candidate_lines(events),
        }

    def write_memory(
        self,
        proposal_id: str,
        session_id: str,
        summary_lines: list[str],
        approved_at: str,
    ) -> Path:
        memory_path = self.memory_dir / f"{proposal_id}.json"
        payload = {
            "memory_id": proposal_id,
            "session_id": session_id,
            "approved_at": approved_at,
            "summary_lines": summary_lines[: self.max_lines],
        }
        memory_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return memory_path

    def memory_count(self) -> int:
        return len(self._load_memory_records())

    def _startup_payload(
        self,
        summary_lines: list[str],
        memory_count: int,
        session_count: int,
    ) -> dict[str, Any]:
        return {
            "summary_lines": summary_lines[: self.max_lines],
            "memory_count": memory_count,
            "session_count": session_count,
        }

    def _append_unique(self, lines: list[str], line: str) -> None:
        cleaned = line.strip()
        if cleaned and cleaned not in lines:
            lines.append(cleaned)

    def _candidate_lines(self, events: list[dict[str, str]]) -> list[str]:
        lines: list[str] = []
        for event in events[-6:]:
            content = event.get("content", "").strip()
            if not content:
                continue
            trimmed = content[:140]
            lines.append(f"{event['role']}: {trimmed}")
        return lines[: self.max_lines]

    def _session_lines(self, record: dict[str, Any]) -> list[str]:
        return self._candidate_lines(record.get("events", []))

    def _load_memory_records(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for path in sorted(self.memory_dir.glob("*.json")):
            records.append(json.loads(path.read_text(encoding="utf-8")))
        return records

    def _load_session_records(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for path in sorted(self.session_dir.glob("*.json")):
            records.append(json.loads(path.read_text(encoding="utf-8")))
        return records


# DECISION POINT: CURRENT_PHASE.md requires unit tests to pass but only lists
# component file locations, so the basic tests live inside the component module.
class MemoryComponentTests(unittest.TestCase):
    def test_startup_context_reads_sessions_and_memory(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            session_dir = root / "sessions"
            memory_dir = root / "memory"
            session_dir.mkdir()
            memory_dir.mkdir()

            session_dir.joinpath("one.json").write_text(
                json.dumps(
                    {
                        "session_id": "one",
                        "events": [
                            {"role": "user", "content": "hello"},
                            {"role": "assistant", "content": "welcome back"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            memory_dir.joinpath("approved.json").write_text(
                json.dumps(
                    {
                        "memory_id": "approved",
                        "summary_lines": ["assistant: remembered line"],
                    }
                ),
                encoding="utf-8",
            )

            memory = Memory(session_dir=session_dir, memory_dir=memory_dir)
            payload = memory.load_startup_context()

        self.assertEqual(payload["memory_count"], 1)
        self.assertEqual(payload["session_count"], 1)
        self.assertLessEqual(len(payload["summary_lines"]), 10)
        self.assertIn("assistant: remembered line", payload["summary_lines"])

    def test_candidate_lines_are_bounded(self) -> None:
        memory = Memory(session_dir=Path("."), memory_dir=Path("."), max_lines=3)
        payload = memory.build_candidate(
            session_id="session-1",
            events=[
                {"role": "user", "content": "one"},
                {"role": "assistant", "content": "two"},
                {"role": "user", "content": "three"},
                {"role": "assistant", "content": "four"},
            ],
        )

        self.assertEqual(payload["session_id"], "session-1")
        self.assertEqual(len(payload["summary_lines"]), 3)


if __name__ == "__main__":
    unittest.main()
