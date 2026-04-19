# CURRENT PHASE: Cycle 3 - Phase 3 - The Body Report
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-19**
**Cycle: 3 - The Commander Room**
**Replaces: Cycle 3 Phase 2 - The Realm Memory (COMPLETE)**

---

## What This Phase Is

The system ontology says: "The Body is the embodiment substrate:
machine, host, guest, node, or infrastructure instance. It contains
real system state, permissions, capabilities, and constraints."

Foundational Law 4: "Readable System Truth — a person should be able
to ask what the system is, what it is doing, and what it can do,
and receive answers that are clear, bounded, and honest."

The current diagnostics command shows model URL, mode, session file,
and directories. But it says nothing about the machine INANNA inhabits —
memory available, disk used, Python version, session uptime, model health.

Phase 3.3 builds the Body Report: a full, honest account of the physical
and computational substrate INANNA inhabits, readable on demand.

This is the third pillar of the Commander Room — after Realm (where)
and Memory (what is remembered), we add Body (what is running).

---

## What You Are Building

### Task 1 - inanna/core/body.py

Create inanna/core/body.py with two classes: BodyReport (dataclass)
and BodyInspector.

BodyReport fields:
- timestamp: str
- platform: str (e.g. "Windows 10")
- python_version: str
- cpu_count: int | None
- memory_total_mb: float | None
- memory_available_mb: float | None
- memory_used_pct: float | None
- disk_total_gb: float | None
- disk_free_gb: float | None
- disk_used_pct: float | None
- session_id: str
- session_uptime_seconds: float
- realm: str
- model_url: str
- model_name: str
- model_mode: str
- data_root: str
- memory_record_count: int
- pending_proposal_count: int
- routing_log_count: int

BodyInspector.inspect() collects all fields and returns a BodyReport.

Memory/disk info: try psutil first (optional, not in requirements.txt),
fall back to /proc/meminfo on Linux, fall back to None if unavailable.
Disk info uses shutil.disk_usage() from standard library.

BodyInspector.format_report() returns a formatted multi-section string:
  Body Report - {timestamp}
    Machine / Memory / Disk / Session / Model / Data sections.

_format_uptime(seconds): 45->"45s", 90->"1m 30s", 3661->"1h 1m"

### Task 2 - The "body" command

Add "body" command to main.py and server.py.
"diagnostics" remains as a backward-compatible alias calling the same handler.

The body command passes session.started_at to BodyInspector.inspect().
routing_log_count is read from the NAMMU routing log file line count.

### Task 3 - Body summary in status payload

Add to the WebSocket status payload a "body" dict with:
platform, python_version, model_mode, session_uptime_seconds,
memory_used_pct, disk_free_gb.

Updated on every status broadcast.

### Task 4 - Body indicator in UI header

Add a body health indicator to the right of the realm indicator.
Show "body: ok" in green when model connected and memory < 80%.
Show "body: warn" in amber when memory >= 80% or disk_free < 1GB.
Show "body: fallback" in amber when model in fallback mode.

CSS class: .body-indicator (color #6a8a6a), .body-indicator.warn (amber).

### Task 5 - Update identity.py and state.py

CURRENT_PHASE = "Cycle 3 - Phase 3 - The Body Report"
Add "body" to STARTUP_COMMANDS and capabilities line.
Keep "diagnostics" in capabilities as alias.

### Task 6 - Tests

Create inanna/tests/test_body.py:
- BodyInspector can be instantiated
- inspect() returns a BodyReport
- format_report() contains "Body Report", "Platform", "Memory", "Session", "Model"
- _format_uptime(45) == "45s"
- _format_uptime(90) == "1m 30s"
- _format_uptime(3661) == "1h 1m"
- Works without psutil (graceful degradation)

Update test_identity.py, test_state.py, test_commands.py for Phase 3.3.

---

## Permitted file changes

inanna/identity.py, main.py, core/body.py (NEW), core/state.py,
ui/server.py, ui/static/index.html,
tests/test_body.py (NEW), tests/test_identity.py,
tests/test_state.py, tests/test_commands.py.
No other files.

Do NOT add psutil to requirements.txt.
Do NOT remove the diagnostics command.

---

## Definition of Done

- [ ] core/body.py exists with BodyInspector and BodyReport
- [ ] "body" command shows full report in CLI and UI
- [ ] "diagnostics" still works as alias
- [ ] Status payload includes body summary dict
- [ ] Body health indicator in UI header
- [ ] Session uptime shown correctly
- [ ] Works without psutil
- [ ] CURRENT_PHASE updated
- [ ] All tests pass

---

## Handoff

Commit: cycle3-phase3-complete
Report: docs/implementation/CYCLE3_PHASE3_REPORT.md
Stop. Do not begin Phase 3.4 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-19*
*The body speaks its truth plainly.*
*A system that cannot account for its substrate*
*cannot claim to be readable.*
