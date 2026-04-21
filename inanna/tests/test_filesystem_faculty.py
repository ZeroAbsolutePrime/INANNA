from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.filesystem_faculty import (
    MAX_READ_BYTES,
    FileSystemFaculty,
    FileSystemResult,
)


class FileSystemFacultyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.faculty = FileSystemFaculty()

    def test_faculty_instantiates(self) -> None:
        self.assertIsInstance(self.faculty, FileSystemFaculty)

    def test_is_safe_read_returns_true_for_home_directory(self) -> None:
        self.assertTrue(self.faculty.is_safe_read(Path.home()))

    def test_is_safe_read_returns_true_for_home_subdirectory(self) -> None:
        self.assertTrue(self.faculty.is_safe_read(Path.home() / "Documents"))

    def test_is_safe_read_returns_false_for_etc(self) -> None:
        self.assertFalse(self.faculty.is_safe_read(Path("/etc")))

    def test_is_forbidden_returns_true_for_shadow(self) -> None:
        self.assertTrue(self.faculty.is_forbidden(Path("/etc/shadow")))

    def test_is_forbidden_returns_false_for_home_file(self) -> None:
        self.assertFalse(self.faculty.is_forbidden(Path.home() / "notes.txt"))

    def test_read_file_returns_error_for_nonexistent_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            result = self.faculty.read_file(str(Path(temp_dir) / "missing.txt"))

        self.assertFalse(result.success)
        self.assertIn("File not found", str(result.error))

    def test_read_file_reads_temp_file_correctly(self) -> None:
        with TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "hello.txt"
            target.write_text("hello filesystem", encoding="utf-8")
            result = self.faculty.read_file(str(target))

        self.assertTrue(result.success)
        self.assertEqual("hello filesystem", result.content)
        self.assertFalse(result.truncated)

    def test_read_file_truncates_large_files(self) -> None:
        with TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "large.txt"
            target.write_bytes(b"a" * (MAX_READ_BYTES + 128))
            result = self.faculty.read_file(str(target))

        self.assertTrue(result.success)
        self.assertTrue(result.truncated)
        self.assertEqual(MAX_READ_BYTES, result.bytes_read)
        self.assertEqual(MAX_READ_BYTES, len(result.content or ""))

    def test_list_dir_lists_temp_directory(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            (base / "one.txt").write_text("1", encoding="utf-8")
            (base / "two.txt").write_text("2", encoding="utf-8")
            result = self.faculty.list_dir(str(base))

        names = [entry.name for entry in result.entries]
        self.assertTrue(result.success)
        self.assertIn("one.txt", names)
        self.assertIn("two.txt", names)

    def test_list_dir_returns_error_for_nonexistent_directory(self) -> None:
        with TemporaryDirectory() as temp_dir:
            result = self.faculty.list_dir(str(Path(temp_dir) / "missing"))

        self.assertFalse(result.success)
        self.assertIn("Directory not found", str(result.error))

    def test_file_info_returns_info_for_existing_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "info.txt"
            target.write_text("abc", encoding="utf-8")
            result = self.faculty.file_info(str(target))

        self.assertTrue(result.success)
        self.assertIsNotNone(result.info)
        self.assertEqual("info.txt", result.info.name if result.info else "")

    def test_file_info_returns_error_for_nonexistent_path(self) -> None:
        with TemporaryDirectory() as temp_dir:
            result = self.faculty.file_info(str(Path(temp_dir) / "missing.txt"))

        self.assertFalse(result.success)
        self.assertIn("Path not found", str(result.error))

    def test_search_files_finds_files_matching_pattern(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            (base / "one.py").write_text("print(1)", encoding="utf-8")
            (base / "two.txt").write_text("ignore", encoding="utf-8")
            nested = base / "nested"
            nested.mkdir()
            (nested / "three.py").write_text("print(3)", encoding="utf-8")
            result = self.faculty.search_files(str(base), "*.py")

        paths = [entry.path for entry in result.entries]
        self.assertTrue(result.success)
        self.assertEqual(2, len(result.entries))
        self.assertTrue(any(path.endswith("one.py") for path in paths))
        self.assertTrue(any(path.endswith("three.py") for path in paths))

    def test_write_file_writes_content_to_temp_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "written.txt"
            result = self.faculty.write_file(str(target), "written content")

            self.assertTrue(result.success)
            self.assertEqual("written content", target.read_text(encoding="utf-8"))

    def test_write_file_refuses_to_overwrite_without_flag(self) -> None:
        with TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "written.txt"
            target.write_text("first", encoding="utf-8")
            result = self.faculty.write_file(str(target), "second")

        self.assertFalse(result.success)
        self.assertIn("File already exists", str(result.error))

    def test_write_file_returns_error_for_forbidden_path(self) -> None:
        result = self.faculty.write_file("/etc/shadow", "secret")

        self.assertFalse(result.success)
        self.assertIn("forbidden path", str(result.error))

    def test_format_result_formats_read_result(self) -> None:
        result = FileSystemResult(
            success=True,
            operation="read",
            path="/tmp/notes.txt",
            content="hello",
            bytes_read=5,
        )

        formatted = self.faculty.format_result(result)

        self.assertIn("fs > read: /tmp/notes.txt", formatted)
        self.assertIn("hello", formatted)

    def test_format_result_formats_list_result(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            (base / "file.txt").write_text("x", encoding="utf-8")
            result = self.faculty.list_dir(str(base))

        formatted = self.faculty.format_result(result)

        self.assertIn("fs > list:", formatted)
        self.assertIn("[FILE]", formatted)
        self.assertIn("file.txt", formatted)

    def test_format_result_formats_error(self) -> None:
        result = FileSystemResult(
            success=False,
            operation="read",
            path="/tmp/missing.txt",
            error="File not found.",
        )

        formatted = self.faculty.format_result(result)

        self.assertEqual("fs > error: File not found.", formatted)


if __name__ == "__main__":
    unittest.main()
