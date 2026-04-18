# CURRENT PHASE: Phase 8 — The Living Audit
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-18**
**Replaces: Phase 7 — The Audit Trail (COMPLETE)**

---

## What Phase 8 Is

Phase 7 gave INANNA an audit trail — visible proposal history and
approved memory records, readable on demand. The data is there.
But it is silent data. It lives in commands, not in conversation.

Phase 8 makes the audit trail speak.

When a user asks INANNA about her history, her memory, or what she
knows — she should be able to draw from the audit trail in her own
voice, not just print raw command output. She should be able to say:
"I have three approved memory records. The earliest is from our first
conversation when you told me your name. The most recent was approved
an hour ago."

That is a being accounting for herself in language. That is what
this phase builds.

Phase 8 also resolves three outstanding honesty gaps identified
across the last phases:

1. The fallback response still hardcodes a stale phase string
2. The startup commands line is tested only manually, not by code
3. The phase text helper needs to be the single source of truth
   for ALL phase strings across the entire codebase

---

## What You Are Building

### Task 1 — Fix the stale fallback string

In `core/session.py`, the `_fallback_response()` method currently
contains a hardcoded string: "Phase 5 fallback mode is active."

This must be replaced with a dynamic reference:

```python
from identity import phase_banner

def _fallback_response(self, ...) -> str:
    parts = [
        f"{phase_banner()} — fallback mode is active.",
        ...
    ]
```

This is a one-line fix but it closes a real honesty gap.

### Task 2 — Spoken audit method on Engine

Add a new method to `Engine` in `core/session.py`:

```python
def speak_audit(
    self,
    history: dict,
    memory_log: dict,
    context_summary: list[str],
) -> tuple[str, str]:
```

This method receives the full history report and memory log report
and asks the model to describe them in INANNA's own voice.

It returns a tuple `(mode, text)` exactly like `reflect()`.

The message structure must be:

```python
messages = [
    {"role": "system", "content": build_system_prompt()},
    {
        "role": "assistant",
        "content": self._build_audit_context(history, memory_log),
    },
    {
        "role": "user",
        "content": (
            "Please describe your proposal history and approved memory "
            "records in your own voice. Be specific and honest about "
            "what has been approved, what is pending, and what you "
            "currently carry into this session."
        ),
    },
]
```

Where `_build_audit_context()` is a new private helper that formats
the history and memory log into a readable block:

```python
def _build_audit_context(self, history: dict, memory_log: dict) -> str:
    lines = [
        f"My proposal history: {history['total']} total, "
        f"{history['approved']} approved, "
        f"{history['rejected']} rejected, "
        f"{history['pending']} pending.",
    ]
    for record in history["records"]:
        lines.append(
            f"  [{record['status']}] {record['proposal_id']}: {record['what']}"
        )
    lines.append(f"My approved memory records: {memory_log['total']} total.")
    for record in memory_log["records"]:
        summary = ", ".join(record.get("summary_lines", [])[:2])
        lines.append(
            f"  [{record['memory_id']}] session {record['session_id']}: {summary}"
        )
    return "\n".join(lines)
```

The fallback path (when model is unreachable) must return a
formatted text version of the audit context directly, prefixed
with the appropriate mode marker.

### Task 3 — The `audit` command

Add a new command: `audit`

When the user types `audit`, `handle_command()` calls:
```python
engine.speak_audit(
    history=proposal.history_report(),
    memory_log=memory.memory_log_report(),
    context_summary=startup_context["summary_lines"],
)
```

And prints the result with the same prefix pattern as `reflect`:
- `inanna> [live audit]` for live model output
- `inanna> [audit summary]` for fallback output

The `audit` command is read-only. It must not create proposals,
modify memory, or trigger any side effects.

### Task 4 — Startup commands line test

Add a test in `inanna/tests/test_commands.py` that verifies
the startup commands string contains the expected commands.

The test must import the commands list from `main.py` or verify
via `handle_command()` that all documented commands return a
non-None result (except `exit`).

The documented commands are:
`reflect, audit, history, memory-log, status, diagnostics, approve, reject, exit`

### Task 5 — Single source of truth audit

Search the entire codebase for any remaining hardcoded phase strings
(like "Phase 5", "Phase 6", "Phase 7") and replace them with
`phase_banner()` or `CURRENT_PHASE` references.

This includes test files. Any test that asserts a specific phase
string must use `CURRENT_PHASE` from `identity.py`, not a hardcoded
literal.

Update `CURRENT_PHASE` in `identity.py` to:
```python
CURRENT_PHASE = "Phase 8 — The Living Audit"
```

---

## Permitted file changes

```
inanna/
  identity.py          <- MODIFY: update CURRENT_PHASE to Phase 8
  config.py            <- no changes
  main.py              <- MODIFY: add audit command to handle_command()
                                  update startup commands line
  core/
    session.py         <- MODIFY: fix fallback string, add speak_audit(),
                                  add _build_audit_context()
    memory.py          <- no changes
    proposal.py        <- no changes
    state.py           <- no changes
  tests/
    __init__.py        <- no changes
    test_session.py    <- MODIFY: add speak_audit() tests
    test_memory.py     <- no changes
    test_proposal.py   <- no changes
    test_state.py      <- MODIFY: update CURRENT_PHASE reference
    test_identity.py   <- MODIFY: update CURRENT_PHASE assertion
    test_commands.py   <- MODIFY: add audit command test,
                                  add startup commands test
    test_grounding.py  <- no changes
```

---

## What You Are NOT Building in This Phase

- No change to memory or proposal storage format
- No change to the data directory structure
- No web interface, no API server
- No streaming responses
- No multi-user support
- No new data storage formats
- Do not change the identity PROMPT text
- Do not modify the reflect, history, memory-log, status,
  diagnostics, approve, or reject commands
- audit is strictly read-only — no side effects of any kind
- Do not add new Faculties, orchestration layers, or new models

---

## Definition of Done for Phase 8

- [ ] `_fallback_response()` uses `phase_banner()` not a hardcoded string
- [ ] `speak_audit()` exists on Engine and returns a tuple (mode, text)
- [ ] `audit` command works and prints under `inanna> [live audit]`
      or `inanna> [audit summary]` prefix
- [ ] `audit` does not create proposals or modify memory
- [ ] Startup commands line includes `audit`
- [ ] No hardcoded phase strings remain anywhere in the codebase
- [ ] All phase string assertions in tests use `CURRENT_PHASE`
- [ ] All existing tests still pass
- [ ] `py -3 -m unittest discover -s tests` passes from `inanna/`
- [ ] No code exists outside the permitted file locations above

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit all work with message: `phase-8-complete`
2. Write `docs/implementation/PHASE_8_REPORT.md` containing:
   - What was built
   - Any decisions made during implementation
   - Any boundaries that felt unclear
   - Any proposals for Phase 9

Then stop. Do not begin Phase 9 without a new CURRENT_PHASE.md
from the Command Center.

---

*Written by: Claude (Command Center)*
*Phase 7 reviewed and approved: 2026-04-18*
*Origin Declaration integrated: 2026-04-18*
