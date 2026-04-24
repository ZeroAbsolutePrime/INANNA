# CURRENT PHASE: Cycle 8 - Phase 8.6 - Calendar Faculty
**Status: ACTIVE**
**Authorized by: INANNA NAMMU (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-22**
**Cycle: 8 - The Desktop Bridge**
**Replaces: Cycle 8 Phase 8.5 - Browser Faculty (COMPLETE)**

---

## MANDATORY READING — in this exact order

1. docs/platform_architecture.md
2. docs/cycle8_master_plan.md
3. docs/cycle9_master_plan.md
4. docs/implementation/CURRENT_PHASE.md (this file)
5. CODEX_DOCTRINE.md
6. ABSOLUTE_PROTOCOL.md

---

## Current System State (discovered before writing this phase)

Calendar infrastructure found:
  Thunderbird 24.2 with Lightning calendar built-in
  Local SQLite: calendar-data/local.sqlite (819KB, schema intact)
  cal_events table: 0 local events (events are remote)
  Remote calendar: Google Calendar via CalDAV
  prefs.js confirms: calendar.caldav.googleResync active
  moz-storage-calendar:// = local cache URI

Windows Calendar: microsoft.windowscommunicationsapps installed

Python calendar libraries: NONE installed
  icalendar, caldav, vobject — all missing

Key insight:
  Events live in Google Calendar (remote CalDAV).
  The local SQLite is empty — it's just a cache.
  To read real events we need either:
    (a) CalDAV client talking directly to Google Calendar
    (b) Read Thunderbird's ICS cache files if they exist
    (c) Use Google Calendar API (requires OAuth2)
  The safest offline approach: install icalendar + parse
  any .ics files that exist, and provide CalDAV infrastructure
  for when credentials are available.

Tools registered: 38 across 10 categories
Tests passing: 543
Phase: Cycle 8 - Phase 8.5 - Browser Faculty

---

## Architecture Decision

The Calendar Faculty uses a three-level approach:

### Level 1 — Local SQLite (instant, no network)
Read Thunderbird's calendar-data/local.sqlite directly.
Schema is known: cal_events, cal_todos tables.
Works offline. Zero latency. No credentials needed.
Currently has 0 events — events are remote.
Will populate as Thunderbird syncs.

### Level 2 — ICS File Reader (offline, file-based)
Parse any .ics files found in Thunderbird profile
or user's filesystem. icalendar library.
Works offline. No credentials needed.
Standard format — works for any calendar export.

### Level 3 — CalDAV Client (online, real events)
Connect to Google Calendar via CalDAV.
Requires: caldav library + stored credentials.
Returns real future/past events from Google Calendar.
Credentials: NOT stored in this phase.
Infrastructure built, activation deferred until
ZAERA configures credentials.

This follows the same ground-truth principle as email:
  Level 1 reads what exists locally (instant).
  Level 3 reads what exists remotely (when configured).
  No hallucination at either level.

---

## Governance Model

```
OBSERVATION (no proposal needed):
  - Reading calendar events (local or remote)
  - Listing today's events / upcoming events
  - Searching events by date or keyword

LIGHT ACTION (proposal required):
  - Creating a new calendar event
  - Updating event title/time

CONSEQUENTIAL ACTION (mandatory proposal):
  - Deleting a calendar event
  - Sharing an event
  - Accepting/declining invitations

FORBIDDEN (never):
  - Accessing other users' private calendars
  - Modifying past events that have already occurred
```

---

## What You Are Building

### Task 1 — Install Python calendar libraries

```bash
pip install icalendar recurring-ical-events --break-system-packages
```

Note: caldav requires network for actual CalDAV connections.
Install it but the connection is not used in tests:
```bash
pip install caldav --break-system-packages
```

If caldav fails to install, it is optional — skip gracefully.
icalendar is REQUIRED. recurring-ical-events is REQUIRED.

### Task 2 — inanna/core/calendar_workflows.py

Create: inanna/core/calendar_workflows.py

```python
"""
INANNA NYX Calendar Faculty
Reads, creates, and manages calendar events.

Three-level architecture:
  Level 1: ThunderbirdCalendarReader
    Reads local SQLite database directly.
    Zero latency. Works offline.
    Returns events from cal_events and cal_todos tables.
    NOTE: Currently 0 events (remote calendar not yet synced).
    Will populate as Thunderbird syncs with Google Calendar.

  Level 2: ICSFileReader
    Parses .ics files from filesystem.
    Uses icalendar library.
    Works for exported calendars and .ics attachments.
    Standard iCalendar RFC 5545 format.

  Level 3: CalDAVClient
    Connects to Google Calendar via CalDAV protocol.
    Requires: caldav library + configured credentials.
    Infrastructure present. Not activated in this phase.
    Activation: when ZAERA configures calendar credentials.

Governance:
  Reading events: no proposal (observation)
  Creating events: proposal required
  Deleting events: ALWAYS mandatory proposal
  Accessing others' calendars: FORBIDDEN

Thunderbird calendar SQLite path:
  C:\\Users\\{user}\\AppData\\Roaming\\Thunderbird\\Profiles\\
  {profile}\\calendar-data\\local.sqlite

ICS schema (RFC 5545):
  VEVENT: calendar event
  VTODO: task/todo item
  VCALENDAR: container

See docs/platform_architecture.md for platform context.
See docs/cycle8_master_plan.md for Cycle 8 architecture.
"""
from __future__ import annotations

import glob
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from typing import Optional


@dataclass
class CalendarEvent:
    """Structured representation of a calendar event."""
    uid: str = ""
    title: str = ""
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    location: str = ""
    description: str = ""
    status: str = ""         # CONFIRMED, TENTATIVE, CANCELLED
    is_all_day: bool = False
    recurrence: str = ""
    calendar_name: str = ""
    source: str = ""         # sqlite, ics, caldav

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
        return " | ".join(p for p in parts if p)


@dataclass
class CalendarResult:
    """Result of a calendar read operation."""
    success: bool = True
    source: str = ""
    events: list[CalendarEvent] = field(default_factory=list)
    todos: list[CalendarEvent] = field(default_factory=list)
    error: Optional[str] = None

    def summary_line(self) -> str:
        total = len(self.events) + len(self.todos)
        return f"calendar > {self.source}: {total} items ({len(self.events)} events, {len(self.todos)} todos)"


# ── TIMESTAMP HELPERS ─────────────────────────────────────────────────

def _tb_ts_to_datetime(ts: int | None) -> Optional[datetime]:
    """Convert Thunderbird's microsecond epoch timestamp to datetime."""
    if ts is None:
        return None
    try:
        # Thunderbird stores times in microseconds since epoch
        return datetime.fromtimestamp(ts / 1_000_000, tz=timezone.utc)
    except (OSError, ValueError, OverflowError):
        return None


# ── LEVEL 1: THUNDERBIRD SQLITE READER ───────────────────────────────

def find_thunderbird_calendar_db() -> Optional[str]:
    """Auto-discover Thunderbird's calendar SQLite file."""
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        pattern = os.path.join(
            appdata, "Thunderbird", "Profiles", "*",
            "calendar-data", "local.sqlite"
        )
    else:
        home = os.path.expanduser("~")
        pattern = os.path.join(
            home, ".thunderbird", "*",
            "calendar-data", "local.sqlite"
        )
    matches = glob.glob(pattern)
    return matches[0] if matches else None


class ThunderbirdCalendarReader:
    """
    Reads calendar events directly from Thunderbird's local SQLite.
    Zero network. Zero credentials. Ground truth from local cache.
    NOTE: Returns 0 events if remote calendar has not synced locally.
    """

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or find_thunderbird_calendar_db()

    def is_available(self) -> bool:
        return bool(self.db_path and Path(self.db_path).exists())

    def read_events(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        max_events: int = 50,
    ) -> CalendarResult:
        """Read events from local SQLite calendar database."""
        if not self.is_available():
            return CalendarResult(
                success=False,
                source="thunderbird_sqlite",
                error="Thunderbird calendar database not found",
            )
        result = CalendarResult(success=True, source="thunderbird_sqlite")
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()

            # Query events
            cur.execute("""
                SELECT cal_id, id, title, event_start, event_end,
                       ical_status, flags, recurrence_id
                FROM cal_events
                ORDER BY event_start ASC
                LIMIT ?
            """, (max_events,))
            for row in cur.fetchall():
                cal_id, uid, title, ev_start, ev_end, status, flags, rec_id = row
                start_dt = _tb_ts_to_datetime(ev_start)
                end_dt = _tb_ts_to_datetime(ev_end)

                # Apply date filter if provided
                if start_date and start_dt and start_dt.date() < start_date:
                    continue
                if end_date and start_dt and start_dt.date() > end_date:
                    continue

                # flags & 2 = all-day event
                is_all_day = bool(flags and (flags & 2))
                # Get location and description from cal_properties
                location = ""
                description = ""
                cur2 = conn.cursor()
                cur2.execute(
                    "SELECT key, value FROM cal_properties WHERE item_id=?",
                    (uid,)
                )
                for key, value in cur2.fetchall():
                    if key == "LOCATION":
                        location = value or ""
                    elif key == "DESCRIPTION":
                        description = (value or "")[:200]

                result.events.append(CalendarEvent(
                    uid=uid or "",
                    title=title or "(no title)",
                    start=start_dt,
                    end=end_dt,
                    location=location,
                    description=description,
                    status=status or "CONFIRMED",
                    is_all_day=is_all_day,
                    recurrence=rec_id or "",
                    source="sqlite",
                ))

            # Query todos
            cur.execute("""
                SELECT id, title, todo_due, ical_status
                FROM cal_todos
                ORDER BY todo_due ASC
                LIMIT ?
            """, (max_events,))
            for row in cur.fetchall():
                uid, title, due, status = row
                due_dt = _tb_ts_to_datetime(due)
                result.todos.append(CalendarEvent(
                    uid=uid or "",
                    title=title or "(no title)",
                    start=due_dt,
                    status=status or "NEEDS-ACTION",
                    source="sqlite",
                ))

            conn.close()
        except sqlite3.Error as e:
            result.success = False
            result.error = f"SQLite error: {e}"
        return result

    def read_today(self) -> CalendarResult:
        today = date.today()
        return self.read_events(start_date=today, end_date=today)

    def read_upcoming(self, days: int = 7) -> CalendarResult:
        today = date.today()
        end = today + timedelta(days=days)
        return self.read_events(start_date=today, end_date=end)


# ── LEVEL 2: ICS FILE READER ──────────────────────────────────────────

class ICSFileReader:
    """
    Reads .ics (iCalendar) files from the filesystem.
    Uses the icalendar library (RFC 5545).
    Works for exported calendars, .ics email attachments, etc.
    """

    def read_file(self, path: str | Path) -> CalendarResult:
        """Parse an .ics file and return structured events."""
        p = Path(path).expanduser().resolve()
        result = CalendarResult(source=f"ics:{p.name}")

        if not p.exists():
            result.success = False
            result.error = f"File not found: {p}"
            return result

        try:
            from icalendar import Calendar
        except ImportError:
            result.success = False
            result.error = "icalendar not installed. Run: pip install icalendar"
            return result

        try:
            raw = p.read_bytes()
            cal = Calendar.from_ical(raw)
            for component in cal.walk():
                if component.name == "VEVENT":
                    result.events.append(self._parse_vevent(component))
                elif component.name == "VTODO":
                    result.todos.append(self._parse_vtodo(component))
            result.success = True
        except Exception as e:
            result.success = False
            result.error = f"Could not parse ICS: {e}"
        return result

    def _parse_vevent(self, component) -> CalendarEvent:
        """Parse a VEVENT component into CalendarEvent."""
        def get(key: str, default: str = "") -> str:
            val = component.get(key)
            return str(val) if val else default

        def get_dt(key: str) -> Optional[datetime]:
            val = component.get(key)
            if val is None:
                return None
            dt = val.dt if hasattr(val, "dt") else val
            if isinstance(dt, datetime):
                return dt
            if isinstance(dt, date):
                return datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc)
            return None

        start = get_dt("DTSTART")
        end = get_dt("DTEND")
        # Detect all-day events
        dtstart_raw = component.get("DTSTART")
        is_all_day = (
            dtstart_raw is not None
            and isinstance(
                dtstart_raw.dt if hasattr(dtstart_raw, "dt") else dtstart_raw,
                date
            )
            and not isinstance(
                dtstart_raw.dt if hasattr(dtstart_raw, "dt") else dtstart_raw,
                datetime
            )
        )

        return CalendarEvent(
            uid=get("UID"),
            title=get("SUMMARY", "(no title)"),
            start=start,
            end=end,
            location=get("LOCATION"),
            description=get("DESCRIPTION")[:200],
            status=get("STATUS", "CONFIRMED"),
            is_all_day=is_all_day,
            source="ics",
        )

    def _parse_vtodo(self, component) -> CalendarEvent:
        """Parse a VTODO component into CalendarEvent."""
        def get(key: str, default: str = "") -> str:
            val = component.get(key)
            return str(val) if val else default

        return CalendarEvent(
            uid=get("UID"),
            title=get("SUMMARY", "(no title)"),
            status=get("STATUS", "NEEDS-ACTION"),
            description=get("DESCRIPTION")[:200],
            source="ics",
        )


# ── LEVEL 3: CALDAV CLIENT (infrastructure, not yet activated) ────────

class CalDAVClient:
    """
    Connects to Google Calendar (or any CalDAV server).
    Infrastructure present. NOT activated in Phase 8.6.
    Activation requires: credentials configuration by ZAERA.

    To activate (future):
    1. ZAERA configures credentials in data/{realm}/calendar_config.json
    2. CalDAVClient.is_configured() returns True
    3. CalDAVClient.read_events() returns real Google Calendar events

    Google Calendar CalDAV URL:
      https://apidata.googleusercontent.com/caldav/v2/{user}/events/
    """

    def is_configured(self) -> bool:
        """Returns True when credentials are configured."""
        # TODO Phase 8.6 extension: check data/{realm}/calendar_config.json
        return False

    def read_events(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> CalendarResult:
        """
        Read events from CalDAV server.
        Currently returns empty result with explanation.
        Will return real events once credentials are configured.
        """
        if not self.is_configured():
            return CalendarResult(
                success=True,
                source="caldav",
                events=[],
                error=None,
            )
        try:
            import caldav
        except ImportError:
            return CalendarResult(
                success=False,
                source="caldav",
                error="caldav not installed. Run: pip install caldav",
            )
        # Full CalDAV implementation deferred to credential configuration phase
        return CalendarResult(
            success=False,
            source="caldav",
            error="CalDAV credentials not configured",
        )


# ── CALENDAR WORKFLOWS ────────────────────────────────────────────────

@dataclass
class CalendarComprehension:
    """
    Structured summary of calendar events.
    Produced after reading — given to CROWN for natural presentation.
    No LLM needed — pure deterministic analysis.
    """
    total_events: int = 0
    today_events: list[CalendarEvent] = field(default_factory=list)
    upcoming_events: list[CalendarEvent] = field(default_factory=list)
    overdue_todos: list[CalendarEvent] = field(default_factory=list)
    period_label: str = ""
    source: str = ""
    has_remote_calendar: bool = False

    def to_crown_context(self) -> str:
        """Format for CROWN to present naturally."""
        lines = [f"CALENDAR ({self.period_label or 'upcoming'} — source: {self.source})"]
        if self.total_events == 0:
            lines.append("No events found in local calendar.")
            if self.has_remote_calendar:
                lines.append(
                    "Note: Your Google Calendar is configured but events"
                    " have not synced to the local cache yet."
                    " Open Thunderbird to trigger a sync, then ask again."
                )
            return "\n".join(lines)

        lines.append(f"Total: {self.total_events} events")
        if self.today_events:
            lines.append("TODAY:")
            for e in self.today_events[:5]:
                lines.append(f"  {e.one_line()}")
        if self.upcoming_events:
            lines.append("UPCOMING:")
            for e in self.upcoming_events[:5]:
                lines.append(f"  {e.one_line()}")
        if self.overdue_todos:
            lines.append("OVERDUE TODOS:")
            for t in self.overdue_todos[:3]:
                lines.append(f"  {t.title}")
        return "\n".join(lines)


def build_calendar_comprehension(
    result: CalendarResult,
    period_label: str = "",
) -> CalendarComprehension:
    """
    Build structured comprehension from CalendarResult.
    Separates today's events from upcoming. Detects overdue todos.
    No LLM. Deterministic. No hallucination.
    """
    now = datetime.now(tz=timezone.utc)
    today = date.today()

    comp = CalendarComprehension(
        total_events=len(result.events),
        period_label=period_label,
        source=result.source,
        has_remote_calendar=True,  # Known from prefs.js inspection
    )

    for event in result.events:
        if event.start and event.start.date() == today:
            comp.today_events.append(event)
        elif event.start and event.start.date() > today:
            comp.upcoming_events.append(event)

    for todo in result.todos:
        if todo.start and todo.start < now:
            comp.overdue_todos.append(todo)

    return comp


class CalendarWorkflows:
    """
    Orchestrates calendar reading and event management.
    Uses ThunderbirdCalendarReader (Level 1) as primary.
    Uses ICSFileReader (Level 2) for .ics files.
    CalDAV (Level 3) deferred until credentials configured.
    """

    def __init__(self) -> None:
        self.sqlite_reader = ThunderbirdCalendarReader()
        self.ics_reader = ICSFileReader()
        self.caldav_client = CalDAVClient()

    def read_today(self) -> tuple[CalendarResult, CalendarComprehension]:
        """Read today's events. No proposal needed."""
        result = self.sqlite_reader.read_today()
        comp = build_calendar_comprehension(result, period_label="today")
        return result, comp

    def read_upcoming(self, days: int = 7) -> tuple[CalendarResult, CalendarComprehension]:
        """Read upcoming events for the next N days. No proposal needed."""
        result = self.sqlite_reader.read_upcoming(days=days)
        comp = build_calendar_comprehension(
            result, period_label=f"next {days} days"
        )
        return result, comp

    def read_ics_file(
        self, path: str
    ) -> tuple[CalendarResult, CalendarComprehension]:
        """Read a .ics file. No proposal needed."""
        result = self.ics_reader.read_file(path)
        comp = build_calendar_comprehension(result, period_label="ics file")
        return result, comp

    def format_result(
        self, result: CalendarResult, comp: CalendarComprehension
    ) -> str:
        """Format calendar result for CROWN."""
        if not result.success and result.error:
            return f"calendar > error: {result.error}"
        return comp.to_crown_context()
```

### Task 3 — Register calendar tools in tools.json

Add to inanna/config/tools.json under category "calendar":

```json
"calendar_today": {
  "display_name": "Today's Events",
  "description": "Read today's calendar events from Thunderbird",
  "category": "calendar",
  "requires_approval": false,
  "enabled": true,
  "parameters": {}
},
"calendar_upcoming": {
  "display_name": "Upcoming Events",
  "description": "Read upcoming calendar events for next N days",
  "category": "calendar",
  "requires_approval": false,
  "enabled": true,
  "parameters": {
    "days": "Number of days to look ahead (default: 7)"
  }
},
"calendar_read_ics": {
  "display_name": "Read ICS File",
  "description": "Parse a .ics calendar file from the filesystem",
  "category": "calendar",
  "requires_approval": false,
  "enabled": true,
  "parameters": {
    "path": "Path to .ics file"
  }
}
```

Total tools after this phase: 41

### Task 4 — Wire CalendarWorkflows into server.py and main.py

Add CALENDAR_TOOL_NAMES:
```python
CALENDAR_TOOL_NAMES = {
    "calendar_today",
    "calendar_upcoming",
    "calendar_read_ics",
}
```

Instantiate in InterfaceServer.__init__:
```python
from core.calendar_workflows import CalendarWorkflows
self.calendar_workflows = CalendarWorkflows()
```

Add run_calendar_tool() following the established pattern.
All 3 calendar tools require no proposal — observation only.

### Task 5 — Natural language routing in main.py

Add calendar domain hints to governance_signals.json:
```json
"calendar": [
  "calendar", "events", "schedule", "agenda",
  "what do i have today", "what is today", "today's events",
  "this week", "next week", "upcoming", "appointments",
  "do i have anything", "what is scheduled",
  "show me my calendar", "my schedule",
  "read ics", "open ics", "ics file"
]
```

Add extract_calendar_tool_request() in main.py:

Patterns:
  "what do I have today" → calendar_today()
  "show my calendar today" → calendar_today()
  "upcoming events" → calendar_upcoming(days=7)
  "next week" → calendar_upcoming(days=14)
  "next N days" → calendar_upcoming(days=N)
  "read ics file at [path]" → calendar_read_ics(path)

### Task 6 — Update help_system.py

Add CALENDAR section to HELP_COMMON:
```
  CALENDAR (Thunderbird / Google Calendar)
    "what do I have today"         Today's events (no approval)
    "upcoming events"              Next 7 days (no approval)
    "next 14 days"                 Next 14 days (no approval)
    "read ics file at ~/path.ics"  Read .ics file (no approval)

  Note: Google Calendar events sync via Thunderbird Lightning.
  Open Thunderbird to trigger a sync if events are missing.
  CalDAV direct connection available in future phase.
```

### Task 7 — Update identity.py

CURRENT_PHASE = "Cycle 8 - Phase 8.6 - Calendar Faculty"

### Task 8 — Tests (all offline — no actual calendar access)

Create inanna/tests/test_calendar_workflows.py (20 tests):

  - CalendarWorkflows instantiates
  - ThunderbirdCalendarReader instantiates
  - ICSFileReader instantiates
  - CalDAVClient instantiates
  - CalDAVClient.is_configured() returns False (not yet configured)
  - CalendarEvent defaults are correct
  - CalendarEvent.start_str returns empty string when start is None
  - CalendarEvent.start_str returns formatted date string
  - CalendarEvent.one_line includes title
  - CalendarResult.summary_line includes event count
  - find_thunderbird_calendar_db returns a path or None (no exception)
  - ThunderbirdCalendarReader.is_available() returns bool
  - _tb_ts_to_datetime handles None gracefully
  - _tb_ts_to_datetime converts valid timestamp correctly
  - build_calendar_comprehension returns correct total_events
  - build_calendar_comprehension sets has_remote_calendar=True
  - CalendarComprehension.to_crown_context includes period label
  - CalendarComprehension.to_crown_context notes empty local cache
    and mentions Google Calendar sync (when 0 events)
  - CALENDAR_TOOL_NAMES contains all 3 tools
  - calendar_today in tools.json with requires_approval=False

### Task 9 — docs/nixos_calendar_faculty.md (mandatory)

Create: docs/nixos_calendar_faculty.md

Document:
  - NixOS packages:
      python311Packages.icalendar
      python311Packages.caldav (optional)
      python311Packages.recurring-ical-events
  - Thunderbird on NixOS: programs.thunderbird.enable = true
  - Calendar SQLite path on NixOS:
      ~/.thunderbird/{profile}/calendar-data/local.sqlite
  - Google Calendar CalDAV URL format
  - How to trigger Thunderbird calendar sync via CLI:
      thunderbird -calendar (opens calendar view, triggers sync)
  - Future: CalDAV credentials configuration path

Update test_identity.py, test_operator.py, test_commands.py.

---

## Permitted file changes

inanna/core/calendar_workflows.py      <- NEW
inanna/main.py                         <- MODIFY
inanna/ui/server.py                    <- MODIFY
inanna/config/tools.json               <- MODIFY: 3 calendar tools
inanna/config/governance_signals.json  <- MODIFY: calendar hints
inanna/requirements.txt                <- MODIFY: icalendar, caldav
inanna/core/help_system.py             <- MODIFY: calendar section
inanna/identity.py                     <- MODIFY
inanna/tests/test_calendar_workflows.py <- NEW
inanna/tests/test_identity.py          <- MODIFY
inanna/tests/test_operator.py          <- MODIFY
inanna/tests/test_commands.py          <- MODIFY
docs/nixos_calendar_faculty.md         <- NEW (mandatory)

---

## What You Are NOT Building

- No event creation in this phase (future extension)
- No event deletion
- No CalDAV credential configuration
- No recurring event expansion (infrastructure present, not wired)
- No browser automation, no email changes
- Do NOT attempt to open Thunderbird in tests
- Do NOT make network calls in tests

---

## Important Note for Codex: Zero Events Is Not a Bug

When ThunderbirdCalendarReader.read_today() returns 0 events:
  This is CORRECT BEHAVIOUR.
  The local SQLite is empty because events are in Google Calendar
  (remote CalDAV, not yet synced locally).
  The CalendarComprehension.to_crown_context() MUST explain this
  clearly to ZAERA — tell her to open Thunderbird to sync,
  then ask again. Do NOT say "no events found" without context.
  Do NOT invent events. Do NOT hallucinate.

---

## Definition of Done

- [ ] core/calendar_workflows.py complete with all 3 levels
- [ ] icalendar installed, caldav installed (or graceful skip)
- [ ] 3 calendar tools in tools.json (41 total)
- [ ] CALENDAR_TOOL_NAMES in main.py
- [ ] CalendarWorkflows wired into server.py
- [ ] Natural language routing for calendar commands
- [ ] help_system.py updated with calendar section
- [ ] to_crown_context correctly explains empty local cache
- [ ] docs/nixos_calendar_faculty.md written
- [ ] CURRENT_PHASE = "Cycle 8 - Phase 8.6 - Calendar Faculty"
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed as cycle8-phase6-complete

---

## Handoff

Commit: cycle8-phase6-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE8_PHASE6_REPORT.md

The report MUST include:
  - icalendar and caldav install status
  - ThunderbirdCalendarReader availability check result
  - Thunderbird SQLite path confirmed
  - NixOS equivalents for all dependencies
  - Note on zero events and why this is correct

Stop. Do not begin Phase 8.7 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: INANNA NAMMU*
*Date: 2026-04-22*
*Time is the architecture of intention.*
*The calendar is the map of what matters.*
*INANNA reads it honestly —*
*zero events with context*
*is more truthful than invented presence.*
*When the hardware arrives,*
*CalDAV will speak the full truth.*
