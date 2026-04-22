from __future__ import annotations

import unittest
from datetime import datetime, timezone

from core.browser_workflows import BrowserComprehension, PageRecord, build_browser_comprehension
from core.calendar_workflows import (
    CalendarComprehension,
    CalendarEvent,
    CalendarResult,
    build_calendar_comprehension,
)
from core.document_workflows import (
    DocumentComprehension,
    DocumentRecord,
    build_document_comprehension,
)
from core.nammu_intent import EmailComprehension, build_comprehension
from ui.server import CROWN_INSTRUCTIONS


class ComprehensionLayerTests(unittest.TestCase):
    def test_browser_comprehension_instantiates_with_defaults(self) -> None:
        comprehension = BrowserComprehension()

        self.assertEqual(comprehension.url, "")
        self.assertEqual(comprehension.key_topics, [])
        self.assertFalse(comprehension.is_search)

    def test_browser_comprehension_to_crown_context_includes_title(self) -> None:
        comprehension = BrowserComprehension(title="Example Domain", url="https://example.com", word_count=42)

        text = comprehension.to_crown_context()

        self.assertIn("WEB PAGE: Example Domain", text)

    def test_browser_comprehension_to_crown_context_includes_url(self) -> None:
        comprehension = BrowserComprehension(title="Example", url="https://example.com", word_count=42)

        self.assertIn("URL: https://example.com", comprehension.to_crown_context())

    def test_browser_comprehension_to_crown_context_handles_error(self) -> None:
        comprehension = BrowserComprehension(error="offline")

        self.assertEqual(comprehension.to_crown_context(), "browser > error: offline")

    def test_browser_comprehension_to_crown_context_marks_search_result(self) -> None:
        comprehension = BrowserComprehension(
            url="search:inanna",
            word_count=50,
            is_search=True,
            query="inanna",
            excerpt="Result body",
        )

        text = comprehension.to_crown_context()

        self.assertIn("WEB SEARCH: 'inanna'", text)
        self.assertIn("CONTENT (50 words):", text)

    def test_build_browser_comprehension_returns_error_comp_on_failed_record(self) -> None:
        record = PageRecord(url="https://example.com", error="timed out")

        comprehension = build_browser_comprehension(record)

        self.assertEqual(comprehension.error, "timed out")

    def test_build_browser_comprehension_extracts_excerpt_from_content(self) -> None:
        record = PageRecord(
            url="https://example.com",
            title="Example",
            content="First line\n\nSecond line\n\nThird line",
            word_count=6,
        )

        comprehension = build_browser_comprehension(record)

        self.assertIn("First line", comprehension.excerpt)
        self.assertIn("Second line", comprehension.excerpt)

    def test_build_browser_comprehension_sets_is_search_true_when_query_provided(self) -> None:
        record = PageRecord(url="search:test", title="Search", content="Alpha Beta", word_count=2)

        comprehension = build_browser_comprehension(record, query="test", is_search=True)

        self.assertTrue(comprehension.is_search)
        self.assertEqual(comprehension.query, "test")

    def test_build_browser_comprehension_word_count_matches_record(self) -> None:
        record = PageRecord(url="https://example.com", title="Example", content="Alpha Beta", word_count=2)

        self.assertEqual(build_browser_comprehension(record).word_count, 2)

    def test_document_comprehension_to_crown_context_includes_title_and_format(self) -> None:
        comprehension = DocumentComprehension(title="Plan", format="docx", word_count=120)

        self.assertIn("DOCUMENT: Plan (docx)", comprehension.to_crown_context())

    def test_document_comprehension_to_crown_context_includes_word_count(self) -> None:
        comprehension = DocumentComprehension(title="Plan", format="docx", word_count=120)

        self.assertIn("Size: 120 words", comprehension.to_crown_context())

    def test_build_document_comprehension_extracts_headings_as_key_points(self) -> None:
        record = DocumentRecord(
            path="report.md",
            title="Report",
            format="md",
            content="# Introduction\n## Risks and mitigations\nThis paragraph explains the plan.",
            word_count=9,
        )

        comprehension = build_document_comprehension(record)

        self.assertIn("Introduction", comprehension.key_points)
        self.assertIn("Risks and mitigations", comprehension.key_points)

    def test_calendar_comprehension_to_crown_context_includes_period_label(self) -> None:
        comprehension = CalendarComprehension(period_label="today", source="thunderbird_sqlite")

        self.assertIn("today", comprehension.to_crown_context().lower())

    def test_calendar_comprehension_to_crown_context_notes_sync_when_zero_events(self) -> None:
        comprehension = CalendarComprehension(
            total_events=0,
            period_label="today",
            source="thunderbird_sqlite",
            has_remote_calendar=True,
        )

        text = comprehension.to_crown_context().lower()

        self.assertIn("zero events", text)
        self.assertIn("open thunderbird", text)

    def test_email_comprehension_to_crown_context_includes_total_count(self) -> None:
        comprehension = EmailComprehension(total=3, unread=1, period="today")

        self.assertIn("Total: 3 emails, 1 unread", comprehension.to_crown_context())

    def test_all_four_comprehension_methods_return_non_empty_str(self) -> None:
        values = [
            BrowserComprehension(url="https://example.com", title="Example", word_count=2, excerpt="Body"),
            DocumentComprehension(title="Plan", format="docx", word_count=2),
            CalendarComprehension(period_label="today", source="thunderbird_sqlite"),
            EmailComprehension(total=1, unread=0),
        ]

        rendered = [item.to_crown_context() for item in values]

        self.assertTrue(all(isinstance(text, str) and text for text in rendered))

    def test_all_four_comprehension_methods_never_raise_exceptions(self) -> None:
        values = [
            BrowserComprehension(error="offline"),
            DocumentComprehension(),
            CalendarComprehension(),
            EmailComprehension(),
        ]

        for item in values:
            self.assertIsInstance(item.to_crown_context(), str)

    def test_crown_instructions_has_all_four_domain_keys(self) -> None:
        self.assertEqual(set(CROWN_INSTRUCTIONS.keys()), {"email", "document", "calendar", "browser"})

    def test_crown_instructions_email_contains_hallucination_guard(self) -> None:
        self.assertIn("hallucination", CROWN_INSTRUCTIONS["email"].lower())

    def test_crown_instructions_document_contains_hallucination_guard(self) -> None:
        self.assertIn("hallucination", CROWN_INSTRUCTIONS["document"].lower())

    def test_build_browser_comprehension_with_real_page_record_extracts_topics(self) -> None:
        record = PageRecord(
            url="https://example.com",
            title="OpenAI Research",
            content="OpenAI Research introduces GPT Systems. OpenAI shares Research updates.",
            word_count=9,
            status_code=200,
        )

        comprehension = build_browser_comprehension(record)

        self.assertEqual(comprehension.status_code, 200)
        self.assertIn("Research", comprehension.key_topics)

    def test_build_calendar_comprehension_with_zero_events_mentions_sync(self) -> None:
        result = CalendarResult(source="thunderbird_sqlite")

        text = build_calendar_comprehension(result, period_label="today").to_crown_context().lower()

        self.assertIn("open thunderbird", text)

    def test_build_comprehension_with_empty_list_returns_zero_total(self) -> None:
        comprehension = build_comprehension([])

        self.assertEqual(comprehension.total, 0)

    def test_document_comprehension_with_no_key_points_still_formats_correctly(self) -> None:
        comprehension = DocumentComprehension(title="Plan", format="txt", word_count=10)

        text = comprehension.to_crown_context()

        self.assertIn("DOCUMENT: Plan (txt)", text)
        self.assertNotIn("KEY POINTS:", text)

    def test_browser_comprehension_search_mode_formats_differently_than_page_mode(self) -> None:
        shared = dict(url="https://example.com", title="Example", word_count=12, excerpt="Alpha Beta")
        page_text = BrowserComprehension(**shared).to_crown_context()
        search_text = BrowserComprehension(**shared, is_search=True, query="example").to_crown_context()

        self.assertIn("WEB PAGE:", page_text)
        self.assertIn("WEB SEARCH:", search_text)

    def test_build_calendar_comprehension_with_events_counts_total(self) -> None:
        result = CalendarResult(
            source="thunderbird_sqlite",
            events=[
                CalendarEvent(title="Today", start=datetime.now(timezone.utc)),
                CalendarEvent(title="Tomorrow", start=datetime.now(timezone.utc)),
            ],
        )

        comprehension = build_calendar_comprehension(result, period_label="today")

        self.assertEqual(comprehension.total_events, 2)


if __name__ == "__main__":
    unittest.main()
