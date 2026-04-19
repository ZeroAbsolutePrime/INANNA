from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.user_log import UserLog


class UserLogTests(unittest.TestCase):
    def make_log(self) -> tuple[TemporaryDirectory, Path, UserLog]:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        logs_dir = root / "user_logs"
        return temp_dir, logs_dir, UserLog(logs_dir)

    def test_user_log_can_be_instantiated(self) -> None:
        _, logs_dir, user_log = self.make_log()

        self.assertTrue(logs_dir.exists())
        self.assertIsInstance(user_log, UserLog)

    def test_append_creates_log_file_when_missing(self) -> None:
        _, logs_dir, user_log = self.make_log()

        user_log.append(
            user_id="user_abc12345",
            session_id="session-1",
            role="user",
            content="Hello",
            response_preview="Welcome",
        )

        self.assertTrue((logs_dir / "user_abc12345.jsonl").exists())

    def test_load_returns_empty_list_for_missing_file(self) -> None:
        _, _, user_log = self.make_log()

        self.assertEqual(user_log.load("user_abc12345"), [])

    def test_load_returns_appended_entries(self) -> None:
        _, _, user_log = self.make_log()
        user_log.append(
            user_id="user_abc12345",
            session_id="session-1",
            role="user",
            content="Hello",
            response_preview="Welcome",
        )
        user_log.append(
            user_id="user_abc12345",
            session_id="session-2",
            role="user",
            content="What is the nature of consciousness?",
            response_preview="That is one of the deepest questions in philosophy...",
        )

        entries = user_log.load("user_abc12345")

        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["session_id"], "session-1")
        self.assertEqual(entries[1]["session_id"], "session-2")

    def test_append_truncates_response_preview_to_200_chars(self) -> None:
        _, _, user_log = self.make_log()

        user_log.append(
            user_id="user_abc12345",
            session_id="session-1",
            role="user",
            content="Hello",
            response_preview="x" * 300,
        )

        entries = user_log.load("user_abc12345")

        self.assertEqual(len(entries[0]["response_preview"]), 200)

    def test_entry_count_returns_zero_for_missing_file(self) -> None:
        _, _, user_log = self.make_log()

        self.assertEqual(user_log.entry_count("user_abc12345"), 0)

    def test_entry_count_returns_correct_value_after_appends(self) -> None:
        _, _, user_log = self.make_log()
        user_log.append("user_abc12345", "session-1", "user", "Hello", "Welcome")
        user_log.append("user_abc12345", "session-2", "user", "Hello again", "Welcome back")

        self.assertEqual(user_log.entry_count("user_abc12345"), 2)

    def test_clear_removes_entries_and_returns_count(self) -> None:
        _, logs_dir, user_log = self.make_log()
        user_log.append("user_abc12345", "session-1", "user", "Hello", "Welcome")
        user_log.append("user_abc12345", "session-2", "user", "Hello again", "Welcome back")

        count = user_log.clear("user_abc12345")

        self.assertEqual(count, 2)
        self.assertFalse((logs_dir / "user_abc12345.jsonl").exists())
        self.assertEqual(user_log.load("user_abc12345"), [])

    def test_multiple_users_have_separate_log_files(self) -> None:
        _, logs_dir, user_log = self.make_log()
        user_log.append("user_abc12345", "session-1", "user", "Hello", "Welcome")
        user_log.append("user_def67890", "session-2", "user", "Hi", "Greetings")

        self.assertEqual(user_log.entry_count("user_abc12345"), 1)
        self.assertEqual(user_log.entry_count("user_def67890"), 1)
        self.assertTrue((logs_dir / "user_abc12345.jsonl").exists())
        self.assertTrue((logs_dir / "user_def67890.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
