# CURRENT PHASE: Cycle 3 - Phase 3.5 - The Faculty Monitor
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-19**
**Cycle: 3 - The Commander Room**
**Replaces: Cycle 3 Phase 3.4 - The Proposal Dashboard (COMPLETE)**

---

## What This Phase Is

The Commander Room now has three pillars: Realm (where), Body (what
substrate), and Proposal Dashboard (governance history). Phase 3.5
adds the fourth: Faculty Monitor.

The system currently has four active Faculties:
- CROWN — primary conversational voice (Engine)
- ANALYST — structured reasoning (AnalystFaculty)
- OPERATOR — bounded tool execution (OperatorFaculty)
- GUARDIAN — system observation (GuardianFaculty)

None of these are visible as entities in the UI. They exist in code
but have no presence in the Commander Room. You cannot see at a glance
which Faculty last spoke, how long it took, whether it is available.

Phase 3.5 gives each Faculty a health record and surfaces them as
named entities in a Faculty Monitor panel.

---

## What You Are Building

### Task 1 - inanna/core/faculty_monitor.py

Create a new file: inanna/core/faculty_monitor.py

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class FacultyRecord:
    name: str           # "crown" | "analyst" | "operator" | "guardian"
    display_name: str   # "CROWN" | "ANALYST" | "OPERATOR" | "GUARDIAN"
    role: str           # one-line description
    mode: str           # "connected" | "fallback" | "ready" | "unavailable"
    last_called_at: str | None = None
    last_response_ms: float | None = None
    call_count: int = 0
    error_count: int = 0


class FacultyMonitor:
    def __init__(self) -> None:
        self._records: dict[str, FacultyRecord] = {
            "crown": FacultyRecord(
                name="crown",
                display_name="CROWN",
                role="Primary conversational voice and relational presence",
                mode="unavailable",
            ),
            "analyst": FacultyRecord(
                name="analyst",
                display_name="ANALYST",
                role="Structured reasoning and comparative analysis",
                mode="unavailable",
            ),
            "operator": FacultyRecord(
                name="operator",
                display_name="OPERATOR",
                role="Bounded tool execution (web_search)",
                mode="ready",
            ),
            "guardian": FacultyRecord(
                name="guardian",
                display_name="GUARDIAN",
                role="System observation and governance health",
                mode="ready",
            ),
        }

    def update_model_mode(self, mode: str) -> None:
        for name in ("crown", "analyst"):
            self._records[name].mode = mode

    def record_call(
        self,
        faculty: str,
        response_ms: float,
        success: bool,
    ) -> None:
        if faculty not in self._records:
            return
        rec = self._records[faculty]
        rec.last_called_at = datetime.now(timezone.utc).isoformat()
        rec.last_response_ms = response_ms
        rec.call_count += 1
        if not success:
            rec.error_count += 1

    def get_record(self, faculty: str) -> FacultyRecord | None:
        return self._records.get(faculty)

    def all_records(self) -> list[FacultyRecord]:
        return list(self._records.values())

    def summary(self) -> list[dict[str, Any]]:
        return [
            {
                "name": r.name,
                "display_name": r.display_name,
                "role": r.role,
                "mode": r.mode,
                "last_called_at": r.last_called_at,
                "last_response_ms": r.last_response_ms,
                "call_count": r.call_count,
                "error_count": r.error_count,
            }
            for r in self._records.values()
        ]

    def format_report(self) -> str:
        lines = ["Faculty Monitor:"]
        for r in self._records.values():
            mode_marker = {
                "connected": "[connected]",
                "fallback":  "[fallback] ",
                "ready":     "[ready]    ",
                "unavailable": "[unavail]  ",
            }.get(r.mode, "[unknown]  ")
            last = "never"
            if r.last_called_at:
                last = r.last_called_at[:19].replace("T", " ")
            ms = f"{r.last_response_ms:.0f}ms" if r.last_response_ms else "-"
            lines.append(
                f"  {mode_marker} {r.display_name:<10} "
                f"calls:{r.call_count:>4}  last:{last}  {ms}"
            )
            lines.append(f"               {r.role}")
        return "\n".join(lines)
```

### Task 2 - Instrument Faculty calls in main.py and server.py

Instantiate FacultyMonitor at startup alongside the other components.

After engine.verify_connection(), call:
```python
monitor.update_model_mode(engine.mode)
```

Wrap every Faculty call with timing:
```python
import time
t0 = time.monotonic()
result = engine.respond(...)
monitor.record_call("crown", (time.monotonic() - t0) * 1000, True)
```

Do this for:
- Engine.respond() -> record_call("crown", ...)
- AnalystFaculty.analyse() -> record_call("analyst", ...)
- OperatorFaculty.execute() -> record_call("operator", ...)
- GuardianFaculty.inspect() -> record_call("guardian", ...)

For fallback responses (model not connected), still record the call
with success=True and a realistic fallback timing.

### Task 3 - The "faculties" command

Add a new command: "faculties"

When the user types "faculties", call monitor.format_report()
and display the result.

CLI prefix: none (plain system output)
UI message type: {"type": "system", "text": "..."}

Add "faculties" to STARTUP_COMMANDS and capabilities in state.py.

### Task 4 - Faculty summary in the status payload

Add to the WebSocket status payload:
```json
{
  "faculties": [
    {
      "name": "crown",
      "display_name": "CROWN",
      "mode": "connected",
      "call_count": 5,
      "last_called_at": "2026-04-19T..."
    },
    ...
  ]
}
```

Updated on every status broadcast.

### Task 5 - Faculty Monitor panel in index.html

Add a new collapsible section below the PROPOSALS section
in the side panel:

```
FACULTIES
  CROWN      [connected]  calls: 5   last: Apr 19 07:25
    Primary conversational voice
  ANALYST    [connected]  calls: 2   last: Apr 19 07:18
    Structured reasoning
  OPERATOR   [ready]      calls: 1   last: Apr 19 07:20
    Bounded tool execution
  GUARDIAN   [ready]      calls: 3   last: Apr 19 07:25
    System observation
```

CSS for faculty entries:
```css
.faculty-entry {
    padding: 6px 0;
    border-bottom: 1px solid rgba(74, 58, 30, 0.12);
}
.faculty-name {
    color: var(--voice);
    font-size: 0.82rem;
    letter-spacing: 0.1em;
}
.faculty-mode {
    font-size: 0.76rem;
    letter-spacing: 0.06em;
}
.faculty-mode.connected { color: var(--connected); }
.faculty-mode.fallback  { color: var(--fallback); }
.faculty-mode.ready     { color: #7a8a7a; }
.faculty-mode.unavailable { color: var(--dim); }
.faculty-role {
    color: var(--dim);
    font-size: 0.76rem;
    margin-top: 2px;
}
```

The panel updates when the status payload includes faculties data.

### Task 6 - Update identity.py and state.py

Update CURRENT_PHASE:
```python
CURRENT_PHASE = "Cycle 3 - Phase 3.5 - The Faculty Monitor"
```

Add "faculties" to STARTUP_COMMANDS and capabilities.

### Task 7 - Tests

Create inanna/tests/test_faculty_monitor.py:
- FacultyMonitor can be instantiated
- all_records() returns 4 FacultyRecord entries
- update_model_mode("connected") updates crown and analyst mode
- record_call() increments call_count correctly
- record_call() updates last_called_at
- record_call() increments error_count on failure
- format_report() contains "CROWN", "ANALYST", "OPERATOR", "GUARDIAN"
- summary() returns list of 4 dicts with required keys

Update test_identity.py, test_state.py, test_commands.py for Phase 3.5.

---

## Permitted file changes

```
inanna/
  identity.py                  <- MODIFY: update CURRENT_PHASE
  main.py                      <- MODIFY: instantiate FacultyMonitor,
                                          instrument Faculty calls,
                                          add faculties command
  core/
    faculty_monitor.py         <- NEW
    state.py                   <- MODIFY: add faculties to capabilities
    (all others)               <- no changes
  ui/
    server.py                  <- MODIFY: instantiate FacultyMonitor,
                                          instrument calls,
                                          faculties in status payload,
                                          faculties command
    static/
      index.html               <- MODIFY: Faculty Monitor panel,
                                          update status handler
  tests/
    test_faculty_monitor.py    <- NEW
    test_identity.py           <- MODIFY: update phase assertion
    test_state.py              <- MODIFY: add faculties capability
    test_commands.py           <- MODIFY: add faculties capability
    (all others)               <- no changes
```

---

## What You Are NOT Building in This Phase

- No Faculty configuration via UI
- No Faculty enable/disable
- No Faculty-specific memory or governance rules
- No new Faculty classes
- No change to Faculty routing or governance logic
- No persistent Faculty metrics across sessions (in-memory only)
- No alerts from Faculty metrics (that is Guardian's role)

---

## Definition of Done for Phase 3.5

- [ ] core/faculty_monitor.py exists with FacultyMonitor and FacultyRecord
- [ ] All four Faculties instrumented with call timing
- [ ] "faculties" command shows formatted report in CLI and UI
- [ ] Status payload includes faculties summary array
- [ ] Faculty Monitor panel visible in UI side panel
- [ ] Faculty mode updates correctly after connection check
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit with message: cycle3-phase5-complete
2. Write docs/implementation/CYCLE3_PHASE5_REPORT.md
3. Stop. Do not begin Phase 3.6 without a new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-19*
*CROWN speaks. ANALYST reasons. OPERATOR acts. GUARDIAN watches.*
*Phase 3.5 makes all four visible at once.*
