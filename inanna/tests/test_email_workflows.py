from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from core.email_workflows import (
    DEFAULT_EMAIL_CLIENT,
    EMAIL_APP_PATTERNS,
    EMAIL_APP_WINGET_IDS,
    EmailRecord,
    EmailWorkflowResult,
    EmailWorkflows,
    normalize_email_app,
)
from identity import list_permitted_tools


class EmailWorkflowsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.desktop = Mock()
        self.workflows = EmailWorkflows(self.desktop)

    def test_instantiates_with_desktop_backend(self) -> None:
        self.assertIs(self.workflows.desktop, self.desktop)

    def test_normalize_email_app_thunderbird(self) -> None:
        self.assertEqual(normalize_email_app("thunderbird"), "thunderbird")

    def test_normalize_email_app_proton_alias(self) -> None:
        self.assertEqual(normalize_email_app("proton"), "protonmail")

    def test_normalize_email_app_proton_mail_alias(self) -> None:
        self.assertEqual(normalize_email_app("Proton Mail"), "protonmail")

    def test_normalize_email_app_tb_alias(self) -> None:
        self.assertEqual(normalize_email_app("tb"), "thunderbird")

    def test_normalize_email_app_unknown_defaults(self) -> None:
        self.assertEqual(normalize_email_app("outlook"), DEFAULT_EMAIL_CLIENT)

    def test_email_app_patterns_cover_supported_clients(self) -> None:
        self.assertIn("thunderbird", EMAIL_APP_PATTERNS)
        self.assertIn("protonmail", EMAIL_APP_PATTERNS)

    def test_email_app_winget_id_for_thunderbird(self) -> None:
        self.assertEqual(EMAIL_APP_WINGET_IDS["thunderbird"], "Mozilla.Thunderbird")

    def test_email_record_defaults(self) -> None:
        record = EmailRecord()

        self.assertEqual(record.sender, "")
        self.assertEqual(record.subject, "")
        self.assertFalse(record.unread)

    def test_email_workflow_result_defaults(self) -> None:
        result = EmailWorkflowResult(success=True, workflow="read_inbox", app="thunderbird")

        self.assertEqual(result.emails, [])
        self.assertEqual(result.steps_completed, [])
        self.assertFalse(result.draft_visible)

    def test_parse_inbox_returns_empty_for_empty_window(self) -> None:
        self.assertEqual(self.workflows._parse_inbox("", "thunderbird"), [])

    def test_parse_inbox_extracts_subject_lines(self) -> None:
        emails = self.workflows._parse_inbox("Invoice ready\nTeam sync tomorrow", "thunderbird")

        self.assertEqual(len(emails), 2)
        self.assertEqual(emails[0].subject, "Invoice ready")
        self.assertEqual(emails[1].app, "thunderbird")

    def test_parse_inbox_skips_navigation_labels(self) -> None:
        emails = self.workflows._parse_inbox(
            "Inbox\nSent\nDrafts\nQuarterly planning\nSearch",
            "thunderbird",
        )

        self.assertEqual([email.subject for email in emails], ["Quarterly planning"])

    def test_format_result_error_surface(self) -> None:
        result = EmailWorkflowResult(
            success=False,
            workflow="read_inbox",
            app="thunderbird",
            error="boom",
        )

        self.assertEqual(
            self.workflows.format_result(result),
            "email > error in thunderbird: boom",
        )

    def test_format_result_for_draft_ready(self) -> None:
        result = EmailWorkflowResult(
            success=True,
            workflow="compose_draft",
            app="thunderbird",
            draft_visible=True,
            output="Draft body",
        )

        self.assertIn("email > draft ready in thunderbird", self.workflows.format_result(result))

    def test_format_result_for_execute_send(self) -> None:
        result = EmailWorkflowResult(
            success=True,
            workflow="execute_send",
            app="thunderbird",
            output="Email sent via thunderbird.",
        )

        self.assertEqual(
            self.workflows.format_result(result),
            "email > Email sent via thunderbird.",
        )

    def test_read_inbox_parses_emails_from_window_output(self) -> None:
        reader = Mock()
        reader.is_available.return_value = True
        reader.read_inbox.return_value = [
            EmailRecord(sender="Matxalen", subject="Alpha update", app="thunderbird"),
            EmailRecord(sender="Anthropic", subject="Beta follow-up", app="thunderbird"),
        ]
        with patch("core.email_workflows.ThunderbirdDirectReader", return_value=reader):
            result = self.workflows.read_inbox("thunderbird", max_emails=5)

        self.assertTrue(result.success)
        self.assertEqual([email.subject for email in result.emails], ["Alpha update", "Beta follow-up"])

    def test_tools_config_marks_email_read_inbox_as_non_proposal(self) -> None:
        tools = self._load_tools()

        self.assertFalse(tools["email_read_inbox"]["requires_approval"])

    def test_tools_config_marks_email_compose_as_proposal_required(self) -> None:
        tools = self._load_tools()

        self.assertTrue(tools["email_compose"]["requires_approval"])

    def test_permitted_tools_list_includes_all_email_tools(self) -> None:
        tools = set(list_permitted_tools())

        self.assertTrue(
            {
                "email_read_inbox",
                "email_read_message",
                "email_search",
                "email_compose",
                "email_reply",
            }.issubset(tools)
        )

    def _load_tools(self) -> dict[str, dict[str, object]]:
        repo_root = Path(__file__).resolve().parents[1]
        tools_path = repo_root / "config" / "tools.json"
        return json.loads(tools_path.read_text(encoding="utf-8"))["tools"]


if __name__ == "__main__":
    unittest.main()
