from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.memory import Memory


class MemoryTests(unittest.TestCase):
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

    def test_memory_log_report_returns_total_and_expected_fields(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            session_dir = root / "sessions"
            memory_dir = root / "memory"
            session_dir.mkdir()
            memory_dir.mkdir()

            memory = Memory(session_dir=session_dir, memory_dir=memory_dir)
            memory.write_memory(
                proposal_id="proposal-a",
                session_id="session-1",
                summary_lines=["user: hello"],
                approved_at="2026-04-18T20:21:39",
            )
            memory.write_memory(
                proposal_id="proposal-b",
                session_id="session-2",
                summary_lines=["assistant: welcome back"],
                approved_at="2026-04-18T20:40:10",
            )

            report = memory.memory_log_report()

        self.assertEqual(report["total"], 2)
        self.assertEqual(report["records"][0]["memory_id"], "proposal-a")
        self.assertEqual(report["records"][0]["session_id"], "session-1")
        self.assertEqual(report["records"][0]["approved_at"], "2026-04-18T20:21:39")
        self.assertEqual(report["records"][0]["summary_lines"], ["user: hello"])

    def test_write_memory_stores_user_id_and_load_filters_by_user(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            session_dir = root / "sessions"
            memory_dir = root / "memory"
            session_dir.mkdir()
            memory_dir.mkdir()

            memory = Memory(session_dir=session_dir, memory_dir=memory_dir)
            memory.write_memory(
                proposal_id="proposal-a",
                session_id="session-1",
                summary_lines=["user: hello"],
                approved_at="2026-04-18T20:21:39",
                user_id="user_alpha",
            )
            memory.write_memory(
                proposal_id="proposal-b",
                session_id="session-2",
                summary_lines=["assistant: welcome back"],
                approved_at="2026-04-18T20:40:10",
                user_id="user_beta",
            )

            alpha_records = memory.load_memory_records(user_id="user_alpha")
            beta_records = memory.load_memory_records(user_id="user_beta")

        self.assertEqual(len(alpha_records), 1)
        self.assertEqual(alpha_records[0]["user_id"], "user_alpha")
        self.assertEqual(alpha_records[0]["memory_id"], "proposal-a")
        self.assertEqual(len(beta_records), 1)
        self.assertEqual(beta_records[0]["user_id"], "user_beta")
        self.assertEqual(beta_records[0]["memory_id"], "proposal-b")

    def test_load_startup_context_scopes_to_approved_memory_for_user(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            session_dir = root / "sessions"
            memory_dir = root / "memory"
            session_dir.mkdir()
            memory_dir.mkdir()

            memory = Memory(session_dir=session_dir, memory_dir=memory_dir)
            memory.write_memory(
                proposal_id="proposal-a",
                session_id="session-1",
                summary_lines=["user: alpha note"],
                approved_at="2026-04-18T20:21:39",
                user_id="user_alpha",
            )
            memory.write_memory(
                proposal_id="proposal-b",
                session_id="session-2",
                summary_lines=["user: beta note"],
                approved_at="2026-04-18T20:40:10",
                user_id="user_beta",
            )

            payload = memory.load_startup_context(user_id="user_alpha")

        self.assertEqual(payload["memory_count"], 1)
        self.assertEqual(payload["session_count"], 0)
        self.assertEqual(payload["summary_lines"], ["user: alpha note"])

    def test_delete_memory_record_returns_true_and_decreases_count(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            session_dir = root / "sessions"
            memory_dir = root / "memory"
            session_dir.mkdir()
            memory_dir.mkdir()

            memory = Memory(session_dir=session_dir, memory_dir=memory_dir)
            memory.write_memory(
                proposal_id="proposal-a",
                session_id="session-1",
                summary_lines=["user: hello"],
                approved_at="2026-04-18T20:21:39",
            )
            memory.write_memory(
                proposal_id="proposal-b",
                session_id="session-2",
                summary_lines=["assistant: welcome back"],
                approved_at="2026-04-18T20:40:10",
            )

            deleted = memory.delete_memory_record("proposal-a")
            remaining = memory.memory_count()

        self.assertTrue(deleted)
        self.assertEqual(remaining, 1)

    def test_delete_memory_record_returns_false_when_record_is_missing(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            session_dir = root / "sessions"
            memory_dir = root / "memory"
            session_dir.mkdir()
            memory_dir.mkdir()

            memory = Memory(session_dir=session_dir, memory_dir=memory_dir)

            deleted = memory.delete_memory_record("proposal-missing")

        self.assertFalse(deleted)


if __name__ == "__main__":
    unittest.main()
