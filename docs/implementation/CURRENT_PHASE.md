# CURRENT PHASE: Phase 7 — The Audit Trail
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-18**
**Replaces: Phase 6 — The Honest Boundary (COMPLETE)**

---

## What Phase 7 Is

Six phases have built the living loop, the real voice, the named
presence, the reflective loop, the grounded memory, and the honest
boundary. INANNA can converse, remember, reflect, and hold her
boundary.

What she cannot yet do is account for herself over time.

If you asked INANNA right now: "What proposals have been made in our
history? What was approved? What was rejected? What did you try to
remember and what did I allow?" — she has no answer. The data exists
in flat files on disk, but there is no way to query it conversationally.

Phase 7 adds the audit trail — a read-only window into the governed
history of this system. It is the first step toward the Commander Room
described in the architecture horizon.

This is not a new feature. It is Law 4 made fully operational:
Readable System Truth. The system must be able to account for itself.

---

## What You Are Building

### Task 1 — The `history` command

Add a new command: `history`

When the user types `history`, the system prints a summary of all
proposals ever created, in chronological order, showing:

```
Proposal history ({n} total, {a} approved, {r} rejected, {p} pending):

  [{status}] {proposal_id} — {timestamp}
             {what}
```

Example output:
```
Proposal history (3 total, 2 approved, 0 rejected, 1 pending):

  [approved] proposal-80a45f81 — 2026-04-18T20:21:39
             Update the memory store from the latest session turn

  [approved] proposal-9feacaa7 — 2026-04-18T20:40:10
             Update the memory store from the latest session turn

  [pending]  proposal-7c5524ca — 2026-04-18T20:41:13
             Update the memory store from the latest session turn
```

If no proposals exist yet:
```
Proposal history (0 total):
  No proposals recorded yet.
```

The `history` command is read-only. It does not create proposals,
modify memory, or trigger any side effects.

### Task 2 — history() method on Proposal

Add a method to `Proposal` in `core/proposal.py`:

```python
def history_report(self) -> dict:
    records = self.list_records()
    approved = [r for r in records if r["status"] == "approved"]
    rejected = [r for r in records if r["status"] == "rejected"]
    pending = [r for r in records if r["status"] == "pending"]
    return {
        "total": len(records),
        "approved": len(approved),
        "rejected": len(rejected),
        "pending": len(pending),
        "records": sorted(records, key=lambda r: r["timestamp"]),
    }
```

`handle_command()` in `main.py` calls `proposal.history_report()`
and formats the output as shown above.

### Task 3 — The `memory-log` command

Add a second new command: `memory-log`

When the user types `memory-log`, the system prints all approved
memory records currently on disk, showing what is actually being
carried into sessions:

```
Memory log ({n} records):

  [{memory_id}] approved: {approved_at}
    Session: {session_id}
    Lines:
      1. {line}
      2. {line}
```

If no memory records exist:
```
Memory log (0 records):
  No approved memory records yet.
```

This command is read-only. No side effects.

### Task 4 — memory_log_report() method on Memory

Add a method to `Memory` in `core/memory.py`:

```python
def memory_log_report(self) -> dict:
    records = self._load_memory_records()
    return {
        "total": len(records),
        "records": records,
    }
```

`handle_command()` in `main.py` calls `memory.memory_log_report()`
and formats the output as shown above.

### Task 5 — Shared phase text helper

Add a small helper to `identity.py`:

```python
def phase_banner() -> str:
    return CURRENT_PHASE
```

Update `CURRENT_PHASE` to:
```python
CURRENT_PHASE = "Phase 7 — The Audit Trail"
```

This eliminates any future drift between the banner, status, and
tests. All phase-name references should use `CURRENT_PHASE` or
`phase_banner()` — never a hardcoded string.

### Task 6 — Tests

Add tests in `inanna/tests/test_commands.py`:
- `history` with no proposals returns a string containing
  "0 total"
- `memory-log` with no memory returns a string containing
  "0 records"

Add tests in `inanna/tests/test_proposal.py`:
- `history_report()` returns correct counts for a mix of
  approved, rejected, and pending proposals

Add tests in `inanna/tests/test_memory.py`:
- `memory_log_report()` returns correct total count
- records in the report contain expected fields

Update `inanna/tests/test_identity.py`:
- `CURRENT_PHASE` assertion updated to Phase 7

---

## Permitted file changes

```
inanna/
  identity.py          <- MODIFY: add phase_banner(), update CURRENT_PHASE
  config.py            <- no changes
  main.py              <- MODIFY: add history and memory-log commands
                                  to handle_command()
  core/
    session.py         <- no changes
    memory.py          <- MODIFY: add memory_log_report()
    proposal.py        <- MODIFY: add history_report()
    state.py           <- no changes
  tests/
    __init__.py        <- no changes
    test_session.py    <- no changes
    test_memory.py     <- MODIFY: add memory_log_report() tests
    test_proposal.py   <- MODIFY: add history_report() tests
    test_state.py      <- no changes
    test_identity.py   <- MODIFY: update CURRENT_PHASE assertion
    test_commands.py   <- MODIFY: add history and memory-log tests
    test_grounding.py  <- no changes
```

---

## What You Are NOT Building in This Phase

- No change to the proposal or memory storage format
- No change to session logic or the Engine
- No change to the grounding injection pattern
- No web interface, no API server
- No streaming responses
- No multi-user support
- No new data storage formats
- Do not change the identity prompt text in PROMPT
- Do not modify the reflect, status, or diagnostics commands
- history and memory-log are strictly read-only — no side effects

---

## Definition of Done for Phase 7

- [ ] `history` command prints chronological proposal summary
- [ ] `memory-log` command prints all approved memory records
- [ ] Both commands are listed in the startup commands line
- [ ] `Proposal.history_report()` exists and is tested
- [ ] `Memory.memory_log_report()` exists and is tested
- [ ] `phase_banner()` exists in `identity.py`
- [ ] `CURRENT_PHASE` updated to "Phase 7 — The Audit Trail"
- [ ] All existing tests still pass
- [ ] `py -3 -m unittest discover -s tests` passes from `inanna/`
- [ ] No code exists outside the permitted file locations above

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit all work with message: `phase-7-complete`
2. Write `docs/implementation/PHASE_7_REPORT.md` containing:
   - What was built
   - Any decisions made during implementation
   - Any boundaries that felt unclear
   - Any proposals for Phase 8

Then stop. Do not begin Phase 8 without a new CURRENT_PHASE.md
from the Command Center.

---

*Written by: Claude (Command Center)*
*Phase 6 reviewed and approved: 2026-04-18*
