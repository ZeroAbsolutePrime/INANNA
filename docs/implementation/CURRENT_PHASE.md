# CURRENT PHASE: Cycle 3 - Phase 3.6 - The Memory Map
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-19**
**Cycle: 3 - The Commander Room**
**Replaces: Cycle 3 Phase 3.5 - The Faculty Monitor (COMPLETE)**

---

## What This Phase Is

Memory in INANNA is governed, selective, and meaningful. Every record
was explicitly approved. Each one carries a session ID, a timestamp,
a set of summary lines, and a realm name.

But right now the memory panel in the UI is a flat list: records
stacked one after another with no sense of time, no sense of growth,
no sense of which sessions they came from.

Phase 3.6 transforms the memory panel into a Memory Map: a timeline
view of approved memory that shows when each record was created, how
memory has accumulated over time, and lets the user inspect any record
in depth.

This is not a cosmetic change. Memory is the most personal layer of
the governed system. How it is presented shapes whether the user
trusts it and can steward it.

---

## What You Are Building

### Task 1 - Memory timeline in index.html

Replace the current flat memory list with a timeline view.

Each memory record becomes a timeline entry:

```
MEMORY  (19 records)  [ clear all ]

  ─── Apr 19 00:17 ────────────────────────────
  [proposal-ad53fc1b]  session: 20260419T001708
    1. user: Hello Dear
    2. assistant: Greetings! I am INANNA...
  [ forget ]

  ─── Apr 19 00:40 ────────────────────────────
  [proposal-1f0f1c5c]  session: 20260419T001708
    1. user: I am ZAERA...
    2. assistant: I acknowledge you as ZAERA...
  [ forget ]
```

Timeline separator: a horizontal rule with the formatted date/time.
Each record shows: proposal ID (short), session ID (short), lines.
The [forget] button triggers the existing forget flow.

"Clear all" button at the top: sends a new command "memory-clear-all"
that creates a proposal to clear ALL approved memory records.
This is a governed action — proposal required, approval required.

### Task 2 - Memory growth indicator

Add a small growth indicator above the timeline:

```
MEMORY  (19 records)  ▓▓▓▓▓▓▓▓░░  19/20 lines used
```

The bar shows how full the memory is relative to the max_lines limit
(default 10 per record, but show total lines across all records vs
a configurable display cap of 50).

CSS for the bar:
```css
.memory-bar {
    display: inline-flex;
    gap: 1px;
    vertical-align: middle;
}
.memory-bar-filled { color: var(--voice); }
.memory-bar-empty  { color: var(--dim); }
```

Use block characters: filled = ▓, empty = ░
Show 10 blocks total representing the fill percentage.

### Task 3 - Memory detail expansion

Each memory record is collapsed by default showing only the first line.
Clicking anywhere on the record expands it to show all lines.

Add a subtle expand indicator:
- Collapsed: [proposal-ad53fc1b] ▸ user: Hello Dear...
- Expanded: [proposal-ad53fc1b] ▾ (full content shown)

### Task 4 - New WebSocket command: memory-map

Add "memory-map" command to server.py and main.py.

When received, return all memory records with enriched data:
```json
{
  "type": "memory_map",
  "records": [
    {
      "memory_id": "proposal-ad53fc1b",
      "session_id": "20260419T001708-abc",
      "approved_at": "2026-04-19T00:17:28",
      "realm_name": "default",
      "summary_lines": ["user: Hello Dear", "assistant: Greetings..."],
      "line_count": 2
    }
  ],
  "total_records": 19,
  "total_lines": 38,
  "oldest_at": "2026-04-19T00:17:28",
  "newest_at": "2026-04-19T12:17:30"
}
```

Records sorted oldest first.

### Task 5 - memory-clear-all command

Add "memory-clear-all" command.

When received, create a proposal:
```
what: "Clear all approved memory records"
why:  "User requested full memory reset"
payload: {"action": "clear_all_memory", "count": N}
```

After approval in the normal approve flow, delete ALL memory record
files in the active realm's memory directory.

Add delete_all_memory_records() to Memory class in memory.py:
```python
def delete_all_memory_records(self) -> int:
    count = 0
    for path in list(self.memory_dir.glob("*.json")):
        path.unlink()
        count += 1
    return count
```

The "clear all" button in the UI sends:
```json
{"type": "command", "cmd": "memory-clear-all"}
```

### Task 6 - Memory stats in status payload

Add to the status payload:
```json
{
  "memory_total_lines": 38,
  "memory_oldest_at": "2026-04-19T00:17:28",
  "memory_newest_at": "2026-04-19T12:17:30"
}
```

These are computed from Memory.memory_log_report() at status time.

### Task 7 - Update identity.py and state.py

Update CURRENT_PHASE:
```python
CURRENT_PHASE = "Cycle 3 - Phase 3.6 - The Memory Map"
```

Add "memory-map" and "memory-clear-all" to STARTUP_COMMANDS
and capabilities in state.py.

### Task 8 - Tests

Add to inanna/tests/test_memory.py:
- delete_all_memory_records() removes all json files
- delete_all_memory_records() returns correct count
- delete_all_memory_records() on empty dir returns 0

Add to inanna/tests/test_commands.py:
- "memory-map" in capabilities
- "memory-clear-all" in capabilities

Update test_identity.py: update CURRENT_PHASE assertion.

---

## Permitted file changes

```
inanna/
  identity.py              <- MODIFY: update CURRENT_PHASE
  main.py                  <- MODIFY: add memory-map and
                                      memory-clear-all commands
  core/
    memory.py              <- MODIFY: add delete_all_memory_records()
    state.py               <- MODIFY: add new commands to capabilities
    (all others)           <- no changes
  ui/
    server.py              <- MODIFY: add memory-map command,
                                      memory-clear-all command,
                                      memory stats in status payload
    static/
      index.html           <- MODIFY: memory timeline view,
                                      growth bar, expand/collapse,
                                      clear all button
  tests/
    test_memory.py         <- MODIFY: add delete_all tests
    test_commands.py       <- MODIFY: add new commands
    test_identity.py       <- MODIFY: update phase assertion
    (all others)           <- no changes
```

---

## What You Are NOT Building in This Phase

- No memory search or filtering by content
- No memory editing
- No cross-realm memory view
- No memory export
- No memory import
- No change to how memory is written or approved
- No change to the grounding turn logic
- No new Faculty or governance capability
- The clear-all must go through a proposal — never silent

---

## Definition of Done for Phase 3.6

- [ ] Memory panel shows timeline view with date separators
- [ ] Each record is collapsible, showing first line by default
- [ ] Memory growth bar shows fill percentage
- [ ] "memory-map" command returns enriched records
- [ ] "memory-clear-all" creates a proposal before deleting
- [ ] After approval, all memory records are deleted
- [ ] Memory stats in status payload
- [ ] delete_all_memory_records() exists on Memory and is tested
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit with message: cycle3-phase6-complete
2. Write docs/implementation/CYCLE3_PHASE6_REPORT.md
3. Stop. Do not begin Phase 3.7 without a new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-19*
*Memory is not a log. It is a map.*
*Each record has a place in time.*
*The Memory Map makes that visible.*
