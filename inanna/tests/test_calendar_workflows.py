from __future__ import annotations

import json
import sqlite3
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from icalendar import Calendar, Event

from core.calendar_workflows import (
    CalDAVClient,
    CalendarComprehension,
    CalendarEvent,
    CalendarResult,
    CalendarWorkflows,
    ICSFileReader,
    ThunderbirdCalendarReader,
    _tb_ts_to_datetime,
    build_calendar_comprehension,
    find_thunderbird_calendar_db,
)
from main import CALENDAR_TOOL_NAMES, detect_calendar_tool_action


class CalendarWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

    def test_calendar_workflows_instantiates(self) -> None:
        self.assertIsInstance(CalendarWorkflows(), CalendarWorkflows)

    def test_thunderbird_calendar_reader_instantiates(self) -> None:
        self.assertIsInstance(ThunderbirdCalendarReader(), ThunderbirdCalendarReader)

    def test_ics_file_reader_instantiates(self) -> None:
        self.assertIsInstance(ICSFileReader(), ICSFileReader)

    def test_caldav_client_instantiates(self) -> None:
        self.assertIsInstance(CalDAVClient(), CalDAVClient)

    def test_caldav_client_is_not_configured_by_default(self) -> None:
        self.assertFalse(CalDAVClient().is_configured())

    def test_calendar_event_defaults_are_correct(self) -> None:
        event = CalendarEvent()

        self.assertEqual(event.uid, "")
        self.assertEqual(event.title, "")
        self.assertFalse(event.is_all_day)

    def test_calendar_event_start_str_returns_empty_when_missing(self) -> None:
        self.assertEqual(CalendarEvent().start_str, "")

    def test_calendar_event_start_str_formats_date(self) -> None:
        event = CalendarEvent(
            start=datetime(2026, 4, 22, 9, 30, tzinfo=timezone.utc),
        )

        self.assertEqual(event.start_str, "2026-04-22 09:30")

    def test_calendar_event_one_line_includes_title(self) -> None:
        event = CalendarEvent(
            title="Architecture Review",
            start=datetime(2026, 4, 22, 9, 30, tzinfo=timezone.utc),
        )

        self.assertIn("Architecture Review", event.one_line())

    def test_calendar_result_summary_line_includes_event_count(self) -> None:
        result = CalendarResult(
            source="ics:test",
            events=[CalendarEvent(title="One")],
            todos=[CalendarEvent(title="Two")],
        )

        self.assertIn("2 items", result.summary_line())

    def test_find_thunderbird_calendar_db_returns_none_or_string(self) -> None:
        discovered = find_thunderbird_calendar_db()
        self.assertTrue(discovered is None or isinstance(discovered, str))

    def test_thunderbird_reader_is_available_returns_bool(self) -> None:
        available = ThunderbirdCalendarReader().is_available()
        self.assertIsInstance(available, bool)

    def test_tb_ts_to_datetime_handles_none(self) -> None:
        self.assertIsNone(_tb_ts_to_datetime(None))

    def test_tb_ts_to_datetime_converts_microseconds(self) -> None:
        converted = _tb_ts_to_datetime(1_700_000_000_000_000)

        self.assertIsNotNone(converted)
        assert converted is not None
        self.assertEqual(converted.tzinfo, timezone.utc)

    def test_build_calendar_comprehension_reports_total_events(self) -> None:
        result = CalendarResult(
            source="thunderbird_sqlite",
            events=[
                CalendarEvent(
                    title="Today",
                    start=datetime.now(timezone.utc),
                ),
                CalendarEvent(
                    title="Tomorrow",
                    start=datetime.now(timezone.utc).replace(day=min(28, date.today().day + 1)),
                ),
            ],
        )

        comprehension = build_calendar_comprehension(result, period_label="today")

        self.assertEqual(comprehension.total_events, 2)

    def test_build_calendar_comprehension_sets_remote_calendar_flag(self) -> None:
        comprehension = build_calendar_comprehension(CalendarResult(source="thunderbird_sqlite"))
        self.assertTrue(comprehension.has_remote_calendar)

    def test_calendar_comprehension_to_crown_context_includes_period_label(self) -> None:
        comprehension = CalendarComprehension(period_label="today", source="thunderbird_sqlite")

        self.assertIn("today", comprehension.to_crown_context().lower())

    def test_calendar_comprehension_empty_context_mentions_sync(self) -> None:
        comprehension = CalendarComprehension(
            total_events=0,
            period_label="today",
            source="thunderbird_sqlite",
            has_remote_calendar=True,
        )

        text = comprehension.to_crown_context().lower()

        self.assertIn("zero events", text)
        self.assertIn("open thunderbird", text)
        self.assertIn("google calendar", text)

    def test_calendar_tool_names_contains_all_three_tools(self) -> None:
        self.assertEqual(
            CALENDAR_TOOL_NAMES,
            {"calendar_today", "calendar_upcoming", "calendar_read_ics"},
        )

    def test_calendar_today_in_tools_json_requires_no_approval(self) -> None:
        tools_path = Path(__file__).resolve().parent.parent / "config" / "tools.json"
        payload = json.loads(tools_path.read_text(encoding="utf-8"))
        tool = payload["tools"]["calendar_today"]

        self.assertFalse(tool["requires_approval"])
        self.assertEqual(tool["category"], "calendar")

    def test_detect_calendar_today_action(self) -> None:
        action = detect_calendar_tool_action("what do I have today")

        self.assertIsNotNone(action)
        assert action is not None
        self.assertEqual(action["tool"], "calendar_today")
        self.assertFalse(action["requires_proposal"])

    def test_detect_calendar_ics_action(self) -> None:
        action = detect_calendar_tool_action("read ics file at C:/tmp/test.ics")

        self.assertIsNotNone(action)
        assert action is not None
        self.assertEqual(action["tool"], "calendar_read_ics")

    def test_ics_reader_parses_event(self) -> None:
        calendar = Calendar()
        event = Event()
        event.add("uid", "alpha")
        event.add("summary", "Council Meeting")
        event.add("dtstart", datetime(2026, 4, 23, 10, 0, tzinfo=timezone.utc))
        event.add("dtend", datetime(2026, 4, 23, 11, 0, tzinfo=timezone.utc))
        calendar.add_component(event)
        path = self.root / "invite.ics"
        path.write_bytes(calendar.to_ical())

        result = ICSFileReader().read_file(path)

        self.assertTrue(result.success)
        self.assertEqual(len(result.events), 1)
        self.assertEqual(result.events[0].title, "Council Meeting")

    def test_thunderbird_reader_reads_empty_sqlite_tables(self) -> None:
        db_path = self.root / "local.sqlite"
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()
        cursor.execute(
            "CREATE TABLE cal_events (cal_id TEXT, id TEXT, title TEXT, event_start INTEGER, event_end INTEGER, ical_status TEXT, flags INTEGER, recurrence_id TEXT)"
        )
        cursor.execute(
            "CREATE TABLE cal_todos (id TEXT, title TEXT, todo_due INTEGER, ical_status TEXT)"
        )
        cursor.execute(
            "CREATE TABLE cal_properties (item_id TEXT, key TEXT, value TEXT)"
        )
        connection.commit()
        connection.close()

        result = ThunderbirdCalendarReader(str(db_path)).read_today()

        self.assertTrue(result.success)
        self.assertEqual(len(result.events), 0)


if __name__ == "__main__":
    unittest.main()
