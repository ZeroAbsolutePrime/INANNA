from __future__ import annotations

import json
import unittest
from pathlib import Path

from core.desktop_faculty import (
    DesktopFaculty,
    DesktopResult,
    FallbackBackend,
    LinuxAtspiBackend,
    WindowsMCPBackend,
    is_consequential_label,
)
from main import DESKTOP_TOOL_NAMES


TOOLS_PATH = Path(__file__).resolve().parent.parent / "config" / "tools.json"


class DesktopFacultyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.faculty = DesktopFaculty()
        self.tools_payload = json.loads(TOOLS_PATH.read_text(encoding="utf-8"))

    def test_desktop_faculty_instantiates_without_error(self) -> None:
        self.assertIsInstance(self.faculty, DesktopFaculty)

    def test_backend_name_is_non_empty_string(self) -> None:
        self.assertIsInstance(self.faculty.backend_name, str)
        self.assertTrue(self.faculty.backend_name)

    def test_is_consequential_label_send_returns_true(self) -> None:
        self.assertTrue(is_consequential_label("send"))

    def test_is_consequential_label_delete_returns_true(self) -> None:
        self.assertTrue(is_consequential_label("delete"))

    def test_is_consequential_label_read_returns_false(self) -> None:
        self.assertFalse(is_consequential_label("read"))

    def test_is_consequential_label_is_case_insensitive(self) -> None:
        self.assertTrue(is_consequential_label("Send Message"))

    def test_is_consequential_label_handles_button_suffix(self) -> None:
        self.assertTrue(is_consequential_label("Send button"))

    def test_windows_backend_instantiates(self) -> None:
        self.assertIsInstance(WindowsMCPBackend(), WindowsMCPBackend)

    def test_linux_backend_instantiates(self) -> None:
        self.assertIsInstance(LinuxAtspiBackend(), LinuxAtspiBackend)

    def test_fallback_backend_instantiates_with_custom_os_name(self) -> None:
        backend = FallbackBackend("Plan9")
        self.assertEqual("fallback-plan9", backend.name)

    def test_fallback_open_app_returns_success_false(self) -> None:
        result = FallbackBackend("Plan9").open_app("notes")
        self.assertFalse(result.success)

    def test_desktop_result_dataclass_creates_correctly(self) -> None:
        result = DesktopResult(True, "open_app", "firefox", output="Started firefox")
        self.assertTrue(result.success)
        self.assertEqual("open_app", result.tool)
        self.assertEqual("firefox", result.query)

    def test_format_result_for_open_app_success_has_app_name(self) -> None:
        result = DesktopResult(True, "open_app", "firefox", window_title="Mozilla Firefox")
        formatted = self.faculty.format_result(result)
        self.assertIn("opened: firefox", formatted)

    def test_format_result_for_error_shows_desktop_error_prefix(self) -> None:
        formatted = self.faculty.format_result(
            DesktopResult(False, "click", "Send", error="No window found.")
        )
        self.assertEqual("desktop > error: No window found.", formatted)

    def test_format_result_for_read_window_includes_window_content(self) -> None:
        formatted = self.faculty.format_result(
            DesktopResult(True, "read_window", "whatsapp", output="[Button] Send")
        )
        self.assertIn("window content", formatted)
        self.assertIn("[Button] Send", formatted)

    def test_format_result_for_click_consequential_mentions_consequential(self) -> None:
        formatted = self.faculty.format_result(
            DesktopResult(True, "click", "Send", consequential=True)
        )
        self.assertIn("consequential action", formatted)

    def test_desktop_tool_names_contains_all_five_tools(self) -> None:
        self.assertEqual(
            DESKTOP_TOOL_NAMES,
            {
                "desktop_open_app",
                "desktop_read_window",
                "desktop_click",
                "desktop_type",
                "desktop_screenshot",
            },
        )

    def test_tools_json_desktop_open_app_requires_approval(self) -> None:
        definition = self.tools_payload["tools"]["desktop_open_app"]
        self.assertTrue(definition["requires_approval"])

    def test_tools_json_desktop_read_window_requires_no_approval(self) -> None:
        definition = self.tools_payload["tools"]["desktop_read_window"]
        self.assertFalse(definition["requires_approval"])

    def test_tools_json_desktop_screenshot_requires_no_approval(self) -> None:
        definition = self.tools_payload["tools"]["desktop_screenshot"]
        self.assertFalse(definition["requires_approval"])


if __name__ == "__main__":
    unittest.main()
