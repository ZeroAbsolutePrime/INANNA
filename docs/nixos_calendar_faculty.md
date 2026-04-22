# NixOS Calendar Faculty

Cycle 8 Phase 8.6 adds the Calendar Faculty for local Thunderbird calendar reads, `.ics` parsing, and deferred CalDAV infrastructure.

## Python Packages

- `python311Packages.icalendar`
- `python311Packages.recurring-ical-events`
- `python311Packages.caldav` (optional)

## Thunderbird

Enable Thunderbird on NixOS:

```nix
programs.thunderbird.enable = true;
```

## Calendar SQLite Path

Thunderbird stores the local calendar cache at:

```text
~/.thunderbird/{profile}/calendar-data/local.sqlite
```

This is a cache, not necessarily the full remote Google Calendar truth.

## Google Calendar CalDAV URL

Google Calendar exposes CalDAV using the pattern:

```text
https://apidata.googleusercontent.com/caldav/v2/{user}/events/
```

## Triggering Sync

To open Thunderbird calendar view and encourage a sync:

```bash
thunderbird -calendar
```

If the local SQLite still shows zero events, that means the local cache has not populated yet. The Calendar Faculty explains that state explicitly instead of claiming the user has no events.

## Future Credentials Path

Future CalDAV activation can read credentials from:

```text
inanna/data/{realm}/calendar_config.json
```
