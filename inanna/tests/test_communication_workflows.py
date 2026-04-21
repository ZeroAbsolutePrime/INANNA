from __future__ import annotations

import json
import unittest
from pathlib import Path

from core.communication_workflows import (
    APP_WINGET_IDS,
    APP_WINDOW_PATTERNS,
    CommunicationWorkflows,
    MessageRecord,
    WorkflowResult,
    normalize_app_name,
)
from main import COMMUNICATION_TOOL_NAMES


TOOLS_PATH = Path(__file__).resolve().parent.parent / "config" / "tools.json"


class DummyDesktop:
    pass


class CommunicationWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workflows = CommunicationWorkflows(DummyDesktop())  # type: ignore[arg-type]
        self.tools_payload = json.loads(TOOLS_PATH.read_text(encoding="utf-8"))

    def test_communication_workflows_instantiates_without_error(self) -> None:
        self.assertIsInstance(self.workflows, CommunicationWorkflows)

    def test_normalize_app_name_whatsapp_returns_whatsapp(self) -> None:
        self.assertEqual("whatsapp", normalize_app_name("whatsapp"))

    def test_normalize_app_name_whatsapp_title_case_returns_whatsapp(self) -> None:
        self.assertEqual("whatsapp", normalize_app_name("WhatsApp"))

    def test_normalize_app_name_signal_messenger_returns_signal(self) -> None:
        self.assertEqual("signal", normalize_app_name("Signal Messenger"))

    def test_normalize_app_name_wa_returns_whatsapp(self) -> None:
        self.assertEqual("whatsapp", normalize_app_name("wa"))

    def test_normalize_app_name_tg_returns_telegram(self) -> None:
        self.assertEqual("telegram", normalize_app_name("tg"))

    def test_app_window_patterns_contains_signal_and_whatsapp(self) -> None:
        self.assertIn("signal", APP_WINDOW_PATTERNS)
        self.assertIn("whatsapp", APP_WINDOW_PATTERNS)

    def test_app_winget_ids_contains_signal_and_whatsapp_ids(self) -> None:
        self.assertEqual("OpenWhisperSystems.Signal", APP_WINGET_IDS["signal"])
        self.assertEqual("WhatsApp.WhatsApp", APP_WINGET_IDS["whatsapp"])

    def test_workflow_result_dataclass_creates_correctly(self) -> None:
        result = WorkflowResult(True, "read_messages", "signal", output="hello")
        self.assertTrue(result.success)
        self.assertEqual("read_messages", result.workflow)
        self.assertEqual("signal", result.app)

    def test_message_record_dataclass_creates_correctly(self) -> None:
        record = MessageRecord("Maria", "Hello", unread=True, app="signal")
        self.assertEqual("Maria", record.sender)
        self.assertEqual("Hello", record.content)
        self.assertTrue(record.unread)
        self.assertEqual("signal", record.app)

    def test_parse_messages_empty_input_returns_empty_list(self) -> None:
        self.assertEqual([], self.workflows._parse_messages("", "signal"))

    def test_parse_messages_non_empty_content_returns_list(self) -> None:
        messages = self.workflows._parse_messages("Hello from Maria\nAnother line here", "signal")
        self.assertGreaterEqual(len(messages), 1)
        self.assertEqual("signal", messages[0].app)

    def test_parse_messages_skips_ui_element_names(self) -> None:
        messages = self.workflows._parse_messages("Send\nSearch\nHello there friend", "signal")
        contents = [message.content for message in messages]
        self.assertEqual(["Hello there friend"], contents)

    def test_format_result_for_error_shows_comm_error_prefix(self) -> None:
        formatted = self.workflows.format_result(
            WorkflowResult(False, "read_messages", "signal", error="Could not open app")
        )
        self.assertIn("comm > error", formatted)

    def test_format_result_for_draft_visible_shows_draft_ready(self) -> None:
        formatted = self.workflows.format_result(
            WorkflowResult(
                True,
                "send_message",
                "signal",
                output='Draft typed in signal to Maria:\n"hello"',
                draft_visible=True,
            )
        )
        self.assertIn("draft ready", formatted)

    def test_format_result_for_execute_send_shows_send_confirmation(self) -> None:
        formatted = self.workflows.format_result(
            WorkflowResult(True, "execute_send", "signal", output="Message sent via signal.")
        )
        self.assertIn("sent", formatted)

    def test_communication_tool_names_contains_all_three_tools(self) -> None:
        self.assertEqual(
            COMMUNICATION_TOOL_NAMES,
            {
                "comm_read_messages",
                "comm_send_message",
                "comm_list_contacts",
            },
        )

    def test_tools_json_comm_read_messages_requires_no_approval(self) -> None:
        definition = self.tools_payload["tools"]["comm_read_messages"]
        self.assertFalse(definition["requires_approval"])

    def test_tools_json_comm_send_message_requires_approval(self) -> None:
        definition = self.tools_payload["tools"]["comm_send_message"]
        self.assertTrue(definition["requires_approval"])

    def test_tools_json_comm_list_contacts_requires_no_approval(self) -> None:
        definition = self.tools_payload["tools"]["comm_list_contacts"]
        self.assertFalse(definition["requires_approval"])


if __name__ == "__main__":
    unittest.main()
