# Cycle 8 Phase 8.6 - Calendar Faculty

## Installed Libraries

- `icalendar`: available
- `recurring-ical-events`: available
- `caldav`: available

All three were verified from the local Python environment. `caldav` remains optional at runtime because credentials are still intentionally unconfigured in this phase.

## Thunderbird Ground Truth

- Thunderbird calendar reader availability check: completed through `ThunderbirdCalendarReader.is_available()`
- Thunderbird SQLite discovery path pattern confirmed:
  - Windows: `C:\Users\{user}\AppData\Roaming\Thunderbird\Profiles\{profile}\calendar-data\local.sqlite`
  - NixOS/Linux: `~/.thunderbird/{profile}/calendar-data/local.sqlite`

## Architecture Delivered

- `core/calendar_workflows.py` added with:
  - `ThunderbirdCalendarReader`
  - `ICSFileReader`
  - `CalDAVClient`
  - `CalendarWorkflows`
- Three observation-only calendar tools registered:
  - `calendar_today`
  - `calendar_upcoming`
  - `calendar_read_ics`
- Calendar routing wired into both CLI and WebSocket paths.

## Zero-Events Note

Zero events is not treated as a bug. When the Thunderbird local cache is empty, CROWN now receives context explaining that the calendar is remote via Google Calendar / CalDAV and that ZAERA should open Thunderbird Calendar to trigger a sync before asking again. The faculty does not flatten this state into a misleading bare "no events" response.

## NixOS Equivalents

- `python311Packages.icalendar`
- `python311Packages.recurring-ical-events`
- `python311Packages.caldav` (optional)
- `programs.thunderbird.enable = true`

## Verification

- Offline calendar workflow tests added
- Identity, operator, and command tests updated for the 41-tool surface
- Full suite run after integration
