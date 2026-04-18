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


if __name__ == "__main__":
    unittest.main()
