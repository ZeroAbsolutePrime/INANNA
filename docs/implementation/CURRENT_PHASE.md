# CURRENT PHASE: Cycle 5 - Phase 5.4 - The Process Monitor
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-20**
**Cycle: 5 - The Operator Console**
**Replaces: Cycle 5 Phase 5.3 - The Network Eye (COMPLETE)**

---

## What This Phase Is

This phase has two parts:

PART A — Auto-Memory Fix (immediate, small)
  Remove the friction of approving your own words being remembered.
  Conversation turns auto-write. No proposal interrupts the flow.
  See docs/memory_architecture.md for the full vision.

PART B — The Process Monitor (main phase work)
  The Processes panel in the Operator Console becomes functional.
  INANNA can see what is running, how long it has been running,
  and what its resource usage looks like.

---

## PART A — Auto-Memory Fix

### What to change

In server.py and main.py:

Current behavior after a conversation turn:
  The system calls create_memory_request_proposal() which generates
  a [PROPOSAL] requiring Guardian approval before writing to memory.

New behavior:
  Remove the proposal call for routine conversation turns.
  Write memory directly using write_memory() at:
    - Session end (on WebSocket disconnect)
    - Every 20 conversation turns (configurable threshold)

Proposals REMAIN for (do not remove these):
  - "remember this" explicit command (user-initiated)
  - clear-memory command
  - forget-memory command
  - memory export (future)
  - cross-session promotion (future)

Implementation:

In server.py, find where create_memory_request_proposal() is called
after conversation turns and replace with direct write_memory() call.

Add a turn counter to the session state:
  self.turn_count = 0

After each conversation turn (crown or analyst response):
  self.turn_count += 1
  if self.turn_count % 20 == 0:
      self._auto_write_memory(session_id, recent_turns)

Add _auto_write_memory() method:
  Writes last N turns as a memory record without a proposal.
  Uses the existing write_memory() infrastructure.
  Appends an audit event: "auto-memory: N turns written at threshold"

Also call _auto_write_memory() in the WebSocket close handler
to capture the session's final turns.

The memory panel in the UI continues to show all records.
The memory bar and count continue to update.
Nothing visible changes for the user except proposals no longer
interrupt the conversation.

---

## PART B — The Process Monitor

### Task 1 - ProcessMonitor in core/process_monitor.py

Create: inanna/core/process_monitor.py

```python
import os, sys, time, platform
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ProcessRecord:
    name: str
    pid: Optional[int]
    status: str        # "running" | "ready" | "offline" | "unknown"
    uptime_seconds: int
    description: str
    endpoint: Optional[str] = None
    memory_mb: Optional[float] = None
    cpu_percent: Optional[float] = None

class ProcessMonitor:
    def __init__(self, server_start_time: float):
        self.server_start_time = server_start_time

    def inanna_record(self) -> ProcessRecord:
        uptime = int(time.time() - self.server_start_time)
        return ProcessRecord(
            name="INANNA NYX Server",
            pid=os.getpid(),
            status="running",
            uptime_seconds=uptime,
            description=f"HTTP :8080  WebSocket :8081  Python {sys.version.split()[0]}",
            endpoint="http://localhost:8080",
        )

    def lm_studio_record(self) -> ProcessRecord:
        import urllib.request
        try:
            req = urllib.request.Request(
                "http://localhost:1234/v1/models",
                headers={"User-Agent": "INANNA-monitor"}
            )
            with urllib.request.urlopen(req, timeout=2) as r:
                status = "running" if r.status == 200 else "ready"
        except Exception:
            status = "offline"
        return ProcessRecord(
            name="LM Studio",
            pid=None,
            status=status,
            uptime_seconds=0,
            description="http://localhost:1234/v1  local inference",
            endpoint="http://localhost:1234",
        )

    def all_records(self) -> list[ProcessRecord]:
        records = [self.inanna_record(), self.lm_studio_record()]
        # Try psutil for resource usage (optional — graceful if absent)
        try:
            import psutil
            p = psutil.Process(os.getpid())
            records[0].memory_mb = round(p.memory_info().rss / 1024 / 1024, 1)
            records[0].cpu_percent = p.cpu_percent(interval=0.1)
        except ImportError:
            pass
        return records

    def format_uptime(self, seconds: int) -> str:
        if seconds < 60:
            return f"{seconds}s"
        if seconds < 3600:
            return f"{seconds//60}m {seconds%60}s"
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}h {m}m"
```

### Task 2 - process-status WebSocket command

Add command: process-status

Returns:
```json
{
  "type": "process_status",
  "processes": [
    {
      "name": "INANNA NYX Server",
      "pid": 12345,
      "status": "running",
      "uptime": "2h 15m",
      "description": "HTTP :8080  WebSocket :8081",
      "endpoint": "http://localhost:8080",
      "memory_mb": 145.3,
      "cpu_percent": 2.1
    },
    {
      "name": "LM Studio",
      "pid": null,
      "status": "running",
      "uptime": "unknown",
      "description": "http://localhost:1234/v1  local inference",
      "endpoint": "http://localhost:1234",
      "memory_mb": null,
      "cpu_percent": null
    }
  ]
}
```

Add "process-status" to STARTUP_COMMANDS and capabilities.

### Task 3 - Process panel in console.html

Replace the placeholder in the Processes panel with a live view.

On panel activate (tab click): send process-status command.
Auto-refresh every 30 seconds while panel is visible.

Display:
```
PROCESS MONITOR

  ● INANNA NYX Server                     pid: 12345
    HTTP :8080 · WebSocket :8081 · Python 3.x
    uptime: 2h 15m    memory: 145 MB    cpu: 2.1%
    [ refresh ]

  ● LM Studio                             endpoint: localhost:1234
    http://localhost:1234/v1 · local inference
    status: running    model: connected
    [ refresh ]

  ○ INANNA NYXOS                          Cycle 7
    Sovereign OS substrate
    status: horizon
```

Status indicators:
  ● green = running
  ● amber = ready/degraded
  ○ dim   = offline/horizon

### Task 4 - Server startup time tracking

In server.py __init__, record the startup time:
  self.server_start_time = time.time()

Pass to ProcessMonitor at init.

### Task 5 - Update identity.py and state.py

CURRENT_PHASE = "Cycle 5 - Phase 5.4 - The Process Monitor"
Add "process-status" to STARTUP_COMMANDS and capabilities.

### Task 6 - Tests

Add inanna/tests/test_process_monitor.py:
  - ProcessMonitor can be instantiated
  - inanna_record() returns ProcessRecord with status "running"
  - inanna_record() has correct pid
  - format_uptime(0) returns "0s"
  - format_uptime(90) returns "1m 30s"
  - format_uptime(3700) returns "1h 1m"
  - all_records() returns at least 2 records

Update test_identity.py: update CURRENT_PHASE assertion.
Update test_state.py: add process-status.
Update test_commands.py: add process-status.

---

## Permitted file changes

inanna/identity.py
inanna/main.py              <- auto-memory fix + process-status command
inanna/config/
  (no config changes)
inanna/core/
  process_monitor.py        <- NEW
  state.py                  <- add process-status
inanna/ui/
  server.py                 <- auto-memory fix + process-status command
  static/console.html       <- replace Processes placeholder
inanna/tests/
  test_process_monitor.py   <- NEW
  test_identity.py          <- update phase
  test_state.py             <- add process-status
  test_commands.py          <- add process-status

---

## What You Are NOT Building

- No process killing via the UI
- No log streaming (future phase)
- No custom service registration
- No resource usage graphs
- psutil is optional — graceful fallback if not installed
- Do not modify index.html

---

## Definition of Done

- [ ] PART A: conversation turns no longer generate proposals
- [ ] PART A: memory auto-written at turn threshold and session end
- [ ] PART A: existing "remember this" and clear/forget proposals unchanged
- [ ] PART B: core/process_monitor.py with ProcessMonitor
- [ ] PART B: process-status command returns process data
- [ ] PART B: Processes panel in Console shows live process records
- [ ] PART B: panel auto-refreshes every 30s while visible
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed to origin/main immediately

---

## Handoff

Commit: cycle5-phase4-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE5_PHASE4_REPORT.md
Stop. Do not begin Phase 5.5 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-20*
*Memory flows. The process breathes. The flow is restored.*
