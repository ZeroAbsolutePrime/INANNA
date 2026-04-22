from __future__ import annotations

import glob
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any


@dataclass
class CalendarEvent:
    uid: str = ""
    title: str = ""
    start: datetime | None = None
    end: datetime | None = None
    location: str = ""
    description: str = ""
    status: str = ""
    is_all_day: bool = False
    recurrence: str = ""
    calendar_name: str = ""
    source: str = ""

    @property
    def start_str(self) -> str:
        if not self.start:
            return ""
        if self.is_all_day:
            return self.start.strftime("%Y-%m-%d")
        return self.start.strftime("%Y-%m-%d %H:%M")

    @property
    def end_str(self) -> str:
        if not self.end:
            return ""
        if self.is_all_day:
            return self.end.strftime("%Y-%m-%d")
        return self.end.strftime("%Y-%m-%d %H:%M")

    def one_line(self) -> str:
        parts = [self.start_str, self.title[:60]]
        if self.location:
            parts.append(f"@ {self.location[:40]}")
        return " | ".join(part for part in parts if part)


@dataclass
class CalendarResult:
    success: bool = True
    source: str = ""
    events: list[CalendarEvent] = field(default_factory=list)
    todos: list[CalendarEvent] = field(default_factory=list)
    error: str | None = None

    def summary_line(self) -> str:
        total = len(self.events) + len(self.todos)
        return (
            f"calendar > {self.source}: {total} items "
            f"({len(self.events)} events, {len(self.todos)} todos)"
        )


@dataclass
class CalendarComprehension:
    total_events: int = 0
    today_events: list[CalendarEvent] = field(default_factory=list)
    upcoming_events: list[CalendarEvent] = field(default_factory=list)
    overdue_todos: list[CalendarEvent] = field(default_factory=list)
    period_label: str = ""
    source: str = ""
    has_remote_calendar: bool = False

    def to_crown_context(self) -> str:
        lines = [f"CALENDAR ({self.period_label or 'upcoming'} - source: {self.source})"]
        if self.total_events == 0:
            lines.append("Local Thunderbird calendar cache currently shows zero events.")
            if self.has_remote_calendar:
                lines.append(
                    "Your Google Calendar appears to be remote via CalDAV, so the local cache may "
                    "still be empty. Open Thunderbird Calendar to trigger a sync, then ask again."
                )
            else:
                lines.append(
                    "No local events were available in the current calendar source."
                )
            return "\n".join(lines)

        lines.append(f"Total: {self.total_events} events")
        if self.today_events:
            lines.append("TODAY:")
            for event in self.today_events[:5]:
                lines.append(f"  {event.one_line()}")
        if self.upcoming_events:
            lines.append("UPCOMING:")
            for event in self.upcoming_events[:5]:
                lines.append(f"  {event.one_line()}")
        if self.overdue_todos:
            lines.append("OVERDUE TODOS:")
            for todo in self.overdue_todos[:3]:
                lines.append(f"  {todo.title}")
        return "\n".join(lines)


def _normalize_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min, tzinfo=timezone.utc)
    return None


def _tb_ts_to_datetime(ts: int | None) -> datetime | None:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(ts / 1_000_000, tz=timezone.utc)
    except (OSError, OverflowError, ValueError):
        return None


def find_thunderbird_calendar_db() -> str | None:
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        pattern = os.path.join(
            appdata,
            "Thunderbird",
            "Profiles",
            "*",
            "calendar-data",
            "local.sqlite",
        )
    else:
        home = os.path.expanduser("~")
        pattern = os.path.join(home, ".thunderbird", "*", "calendar-data", "local.sqlite")
    matches = glob.glob(pattern)
    return matches[0] if matches else None


class ThunderbirdCalendarReader:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or find_thunderbird_calendar_db()

    def is_available(self) -> bool:
        return bool(self.db_path and Path(self.db_path).exists())

    def read_events(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        max_events: int = 50,
    ) -> CalendarResult:
        if not self.is_available():
            return CalendarResult(
                success=False,
                source="thunderbird_sqlite",
                error="Thunderbird calendar database not found",
            )

        result = CalendarResult(success=True, source="thunderbird_sqlite")
        try:
            connection = sqlite3.connect(str(self.db_path))
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT cal_id, id, title, event_start, event_end,
                       ical_status, flags, recurrence_id
                FROM cal_events
                ORDER BY event_start ASC
                LIMIT ?
                """,
                (max_events,),
            )
            event_rows = cursor.fetchall()
            property_cursor = connection.cursor()
            for row in event_rows:
                cal_id, uid, title, ev_start, ev_end, status, flags, rec_id = row
                start_dt = _tb_ts_to_datetime(ev_start)
                end_dt = _tb_ts_to_datetime(ev_end)
                if start_date and start_dt and start_dt.date() < start_date:
                    continue
                if end_date and start_dt and start_dt.date() > end_date:
                    continue

                is_all_day = bool(flags and (int(flags) & 2))
                location = ""
                description = ""
                try:
                    property_cursor.execute(
                        "SELECT key, value FROM cal_properties WHERE item_id=?",
                        (uid,),
                    )
                    for key, value in property_cursor.fetchall():
                        if key == "LOCATION":
                            location = str(value or "")
                        elif key == "DESCRIPTION":
                            description = str(value or "")[:200]
                except sqlite3.Error:
                    pass

                result.events.append(
                    CalendarEvent(
                        uid=str(uid or ""),
                        title=str(title or "(no title)"),
                        start=start_dt,
                        end=end_dt,
                        location=location,
                        description=description,
                        status=str(status or "CONFIRMED"),
                        is_all_day=is_all_day,
                        recurrence=str(rec_id or ""),
                        calendar_name=str(cal_id or ""),
                        source="sqlite",
                    )
                )

            try:
                cursor.execute(
                    """
                    SELECT id, title, todo_due, ical_status
                    FROM cal_todos
                    ORDER BY todo_due ASC
                    LIMIT ?
                    """,
                    (max_events,),
                )
                for uid, title, due, status in cursor.fetchall():
                    due_dt = _tb_ts_to_datetime(due)
                    result.todos.append(
                        CalendarEvent(
                            uid=str(uid or ""),
                            title=str(title or "(no title)"),
                            start=due_dt,
                            status=str(status or "NEEDS-ACTION"),
                            source="sqlite",
                        )
                    )
            except sqlite3.Error:
                pass
            connection.close()
        except sqlite3.Error as exc:
            result.success = False
            result.error = f"SQLite error: {exc}"
        return result

    def read_today(self) -> CalendarResult:
        today = date.today()
        return self.read_events(start_date=today, end_date=today)

    def read_upcoming(self, days: int = 7) -> CalendarResult:
        today = date.today()
        return self.read_events(start_date=today, end_date=today + timedelta(days=days))


class ICSFileReader:
    def read_file(self, path: str | Path) -> CalendarResult:
        resolved = Path(path).expanduser().resolve()
        result = CalendarResult(source=f"ics:{resolved.name}")
        if not resolved.exists():
            result.success = False
            result.error = f"File not found: {resolved}"
            return result
        try:
            from icalendar import Calendar
        except ImportError:
            result.success = False
            result.error = "icalendar not installed. Run: pip install icalendar"
            return result

        try:
            calendar = Calendar.from_ical(resolved.read_bytes())
            for component in calendar.walk():
                if component.name == "VEVENT":
                    result.events.append(self._parse_vevent(component))
                elif component.name == "VTODO":
                    result.todos.append(self._parse_vtodo(component))
        except Exception as exc:
            result.success = False
            result.error = f"Could not parse ICS: {exc}"
        return result

    def _parse_vevent(self, component: Any) -> CalendarEvent:
        def get_text(key: str, default: str = "") -> str:
            value = component.get(key)
            return str(value) if value is not None else default

        dtstart_raw = component.get("DTSTART")
        dtend_raw = component.get("DTEND")
        start = _normalize_datetime(dtstart_raw.dt if hasattr(dtstart_raw, "dt") else dtstart_raw)
        end = _normalize_datetime(dtend_raw.dt if hasattr(dtend_raw, "dt") else dtend_raw)
        start_value = dtstart_raw.dt if hasattr(dtstart_raw, "dt") else dtstart_raw
        is_all_day = isinstance(start_value, date) and not isinstance(start_value, datetime)
        return CalendarEvent(
            uid=get_text("UID"),
            title=get_text("SUMMARY", "(no title)"),
            start=start,
            end=end,
            location=get_text("LOCATION"),
            description=get_text("DESCRIPTION")[:200],
            status=get_text("STATUS", "CONFIRMED"),
            is_all_day=is_all_day,
            recurrence=get_text("RRULE"),
            source="ics",
        )

    def _parse_vtodo(self, component: Any) -> CalendarEvent:
        def get_text(key: str, default: str = "") -> str:
            value = component.get(key)
            return str(value) if value is not None else default

        due_raw = component.get("DUE")
        start = _normalize_datetime(due_raw.dt if hasattr(due_raw, "dt") else due_raw)
        return CalendarEvent(
            uid=get_text("UID"),
            title=get_text("SUMMARY", "(no title)"),
            start=start,
            status=get_text("STATUS", "NEEDS-ACTION"),
            description=get_text("DESCRIPTION")[:200],
            source="ics",
        )


class CalDAVClient:
    def __init__(self, config_path: str | Path | None = None) -> None:
        self.config_path = Path(config_path).expanduser().resolve() if config_path else None

    def is_configured(self) -> bool:
        return bool(self.config_path and self.config_path.exists())

    def read_events(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> CalendarResult:
        del start_date
        del end_date
        if not self.is_configured():
            return CalendarResult(success=True, source="caldav", events=[], todos=[])
        try:
            import caldav  # noqa: F401
        except ImportError:
            return CalendarResult(
                success=False,
                source="caldav",
                error="caldav not installed. Run: pip install caldav",
            )
        return CalendarResult(
            success=False,
            source="caldav",
            error="CalDAV credentials not configured",
        )


def build_calendar_comprehension(
    result: CalendarResult,
    period_label: str = "",
) -> CalendarComprehension:
    today = date.today()
    now = datetime.now(tz=timezone.utc)
    comprehension = CalendarComprehension(
        total_events=len(result.events),
        period_label=period_label,
        source=result.source,
        has_remote_calendar=True,
    )
    for event in result.events:
        if event.start and event.start.date() == today:
            comprehension.today_events.append(event)
        elif event.start and event.start.date() > today:
            comprehension.upcoming_events.append(event)
    for todo in result.todos:
        if todo.start and todo.start < now:
            comprehension.overdue_todos.append(todo)
    return comprehension


class CalendarWorkflows:
    def __init__(
        self,
        sqlite_reader: ThunderbirdCalendarReader | None = None,
        ics_reader: ICSFileReader | None = None,
        caldav_client: CalDAVClient | None = None,
    ) -> None:
        self.sqlite_reader = sqlite_reader or ThunderbirdCalendarReader()
        self.ics_reader = ics_reader or ICSFileReader()
        self.caldav_client = caldav_client or CalDAVClient()

    def read_today(self) -> tuple[CalendarResult, CalendarComprehension]:
        result = self.sqlite_reader.read_today()
        return result, build_calendar_comprehension(result, period_label="today")

    def read_upcoming(self, days: int = 7) -> tuple[CalendarResult, CalendarComprehension]:
        result = self.sqlite_reader.read_upcoming(days=max(1, days))
        return result, build_calendar_comprehension(result, period_label=f"next {max(1, days)} days")

    def read_ics_file(self, path: str) -> tuple[CalendarResult, CalendarComprehension]:
        result = self.ics_reader.read_file(path)
        return result, build_calendar_comprehension(result, period_label="ics file")

    def format_result(self, result: CalendarResult, comprehension: CalendarComprehension) -> str:
        if not result.success and result.error:
            return f"calendar > error: {result.error}"
        return comprehension.to_crown_context()
