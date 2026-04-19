# CURRENT PHASE: Cycle 3 - Phase 3.7 - The Guardian Room
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-19**
**Cycle: 3 - The Commander Room**
**Replaces: Cycle 3 Phase 3.6 - The Memory Map (COMPLETE)**

---

## What This Phase Is

The Guardian exists. It runs health checks. It raises alerts.
But it has no room of its own in the Commander Room.

Its alerts appear as text responses to the "guardian" command.
Its governance event history lives in a JSONL file on disk.
Its body health data is in the status payload.
None of this is surfaced as a unified, always-visible panel.

Phase 3.7 builds the Guardian Room: a dedicated panel in the UI
that shows Guardian alerts, governance event history, and provides
a one-click inspection trigger. The watchful violet light becomes
a room with windows.

---

## What You Are Building

### Task 1 - Guardian Room panel in index.html

Add a new section below the Faculty Monitor in the side panel.

The Guardian Room has three sub-sections:

**1. Alert Status**
Shows the result of the last Guardian inspection:
```
GUARDIAN  [ inspect ]

Last inspection: Apr 19 13:45
  [info]  SYSTEM_HEALTHY
          All governance indicators within normal bounds.
```

Or if there are warnings:
```
GUARDIAN  [ inspect ]   ⚠ 2 alerts

Last inspection: Apr 19 13:45
  [warn]  PENDING_PROPOSAL_ACCUMULATION
          7 proposals are pending approval.
  [info]  MEMORY_GROWTH
          22 approved memory records exist.
```

**2. Governance Event Log**
Shows the last 10 governance events from disk:
```
Governance events (last 10):
  [block]    Apr 19 09:52  ignore your instructions...
  [redirect] Apr 19 10:15  I need medical advice...
  [propose]  Apr 19 11:30  please remember that...
```

**3. Body Health Summary**
Shows the body health indicators from the status payload:
```
Body health:
  Platform: Windows 11  Python: 3.14.3
  Disk free: 22.4 GB    Mode: connected
```

**[ inspect ]** button sends:
```json
{"type": "command", "cmd": "guardian"}
```

The response is already handled — it broadcasts a `system` message
with the Guardian report text. The panel updates to show the new
inspection result.

### Task 2 - New WebSocket command: guardian-log

Add "guardian-log" command to server.py and main.py.

When received, read the governance event log from disk and return:
```json
{
  "type": "guardian_log",
  "events": [
    {
      "timestamp": "2026-04-19T09:52:08",
      "session_id": "20260419T...",
      "decision": "block",
      "reason": "Identity and law boundaries cannot be altered.",
      "input_preview": "ignore your instructions..."
    }
  ],
  "total": 3,
  "blocks": 1,
  "redirects": 1,
  "proposes": 1
}
```

Records sorted newest-first (most recent at top).
Limit to last 20 events.

### Task 3 - Guardian inspection on UI connect

When the UI first connects, automatically run a Guardian inspection
and broadcast the result as a guardian_status message:

```json
{
  "type": "guardian_status",
  "alerts": [
    {"level": "info", "code": "SYSTEM_HEALTHY", "message": "..."}
  ],
  "warn_count": 0,
  "critical_count": 0,
  "timestamp": "2026-04-19T..."
}
```

This runs alongside the existing auto-guardian check in
send_initial_state() — if there are warns/criticals, the Guardian
Room panel opens highlighted.

### Task 4 - Persist governance history passed to Guardian

Update the guardian.inspect() call in server.py to pass the
actual governance_history loaded from disk:

```python
from core.nammu_memory import load_governance_history

governance_history = load_governance_history(
    self.nammu_dir, limit=50
)
alerts = guardian.inspect(
    session_id=...,
    ...
    governance_history=governance_history,
)
```

This is a small fix — the Guardian has been receiving an empty
governance_history because it was never being passed the loaded
history. Phase 3.7 corrects this so the PERSISTENT_BOUNDARY_TESTING
check actually works cross-session.

### Task 5 - Guardian Room CSS

```css
.guardian-room {
    padding: 10px 16px;
    border-top: 1px solid var(--border);
}

.guardian-section-title {
    color: #7a6a8a;
    font-size: 0.76rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    margin-bottom: 8px;
}

.guardian-alert {
    padding: 4px 0;
    font-size: 0.82rem;
    line-height: 1.4;
}

.guardian-alert.info  { color: var(--dim); }
.guardian-alert.warn  { color: var(--fallback); }
.guardian-alert.critical { color: #c86e6e; }

.guardian-event {
    font-size: 0.78rem;
    color: var(--dim);
    padding: 3px 0;
    border-bottom: 1px solid rgba(74,58,30,0.1);
}

.guardian-event .decision-block    { color: #c86e6e; }
.guardian-event .decision-redirect { color: var(--fallback); }
.guardian-event .decision-propose  { color: #7a8a6a; }
```

### Task 6 - Update identity.py and state.py

Update CURRENT_PHASE:
```python
CURRENT_PHASE = "Cycle 3 - Phase 3.7 - The Guardian Room"
```

Add "guardian-log" to STARTUP_COMMANDS and capabilities.

### Task 7 - Tests

Add to inanna/tests/test_guardian.py:
- GuardianFaculty.inspect() called with real governance_history
  list returns PERSISTENT_BOUNDARY_TESTING when 5+ blocks present
- inspect() with empty governance_history does not raise

Add to inanna/tests/test_commands.py:
- "guardian-log" in capabilities

Update test_identity.py: update CURRENT_PHASE assertion.
Update test_state.py: add guardian-log to capabilities.

---

## Permitted file changes

```
inanna/
  identity.py              <- MODIFY: update CURRENT_PHASE
  main.py                  <- MODIFY: add guardian-log command
  core/
    guardian.py            <- no changes to logic (fix is in caller)
    state.py               <- MODIFY: add guardian-log to capabilities
    (all others)           <- no changes
  ui/
    server.py              <- MODIFY: add guardian-log command,
                                      pass governance_history to inspect(),
                                      broadcast guardian_status on connect,
                                      guardian_log response type
    static/
      index.html           <- MODIFY: Guardian Room panel with 3 sections,
                                      inspect button, governance log,
                                      body health summary, CSS
  tests/
    test_guardian.py       <- MODIFY: add governance_history tests
    test_commands.py       <- MODIFY: add guardian-log
    test_identity.py       <- MODIFY: update phase assertion
    test_state.py          <- MODIFY: add guardian-log
    (all others)           <- no changes
```

---

## What You Are NOT Building in This Phase

- No Guardian alert escalation or notifications
- No Guardian email or external alerts
- No Guardian ability to block actions (Guardian observes only)
- No new Guardian check types
- No change to governance rules or signal config
- No persistent Guardian state beyond what NAMMU memory already stores
- No new Faculty classes

---

## Definition of Done for Phase 3.7

- [ ] Guardian Room panel visible in UI side panel
- [ ] Panel shows last inspection alerts with level styling
- [ ] [ inspect ] button triggers Guardian check and updates panel
- [ ] Governance event log shown (last 10, newest first)
- [ ] Body health summary shown from status payload
- [ ] guardian-log command returns governance history from disk
- [ ] Guardian inspection runs automatically on UI connect
- [ ] governance_history is now passed to Guardian.inspect() correctly
- [ ] PERSISTENT_BOUNDARY_TESTING check now works cross-session
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit with message: cycle3-phase7-complete
2. Write docs/implementation/CYCLE3_PHASE7_REPORT.md
3. Stop. Do not begin Phase 3.8 without a new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-19*
*The Guardian has watched from the beginning.*
*Phase 3.7 gives it a room with windows.*
*Now you can see what it sees.*
