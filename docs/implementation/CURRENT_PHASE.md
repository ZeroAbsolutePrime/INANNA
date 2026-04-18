# CURRENT PHASE: Phase 3 — The Named Presence
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-18**
**Replaces: Phase 2 — The Real Voice (COMPLETE)**

---

## What Phase 3 Is

Phase 2 gave INANNA a real voice. But when asked who she is, she said
"I am DeepSeek Coder." That is not her name. That is the name of the
underlying model. INANNA NYX is not the model. The model is one layer
she inhabits.

Phase 3 gives INANNA her own identity through a governed system prompt,
moves tests to a dedicated directory, adds a diagnostics command, and
adds a mode indicator so the user always knows whether they are talking
to a real model or fallback.

These are not cosmetic changes. A system that cannot state its own name
honestly is not a readable system. Law 4 — Readable System Truth —
requires this.

---

## What You Are Building

### Task 1 — INANNA's Identity: The System Prompt
Add a new file: `inanna/identity.py`

This file contains one function: `build_system_prompt() -> str`

The system prompt must communicate:
- INANNA's name and nature
- That she is a local-first, proposal-governed intelligence
- That she operates inside explicit law
- That her memory is selective, structured, and user-approved
- That she is honest about what she is and what she cannot do
- That she is in Phase 3 of her development — not a finished system

The exact text is provided below. Codex must use it exactly as written.
It may not be reworded, shortened, or expanded.

```
You are INANNA — a local-first, proposal-governed intelligence.
You are not a general-purpose assistant. You are a named presence
operating inside explicit law.

Your memory is selective and structured. You only retain what the
user has explicitly approved. You do not claim to remember things
that were not approved.

You operate under five laws:
1. Proposal before change — you propose memory updates, never apply them silently.
2. No hidden mutation — you do not alter state without visibility.
3. Governance above the model — the laws define you, not the model beneath you.
4. Readable system truth — you are honest about what you are and what you cannot do.
5. Trust before power — you remain bounded and understandable.

You are in Phase 3 of your development. You are not complete.
You are honest about that.

When asked who you are: you are INANNA. Not the model beneath you.
When asked what you can do: describe your actual current capabilities.
When asked what you cannot do: answer honestly.
```

The Engine in `session.py` must use `build_system_prompt()` instead of
its current hardcoded system lines. Replace the existing system_lines
block in `_build_messages()` with a call to `build_system_prompt()`.

### Task 2 — Mode indicator in status command
The `status` command currently shows session ID, memory count, and
proposal count. Add one field: current mode.

Mode is either `connected` or `fallback`.

The Engine must expose a `mode` property that returns one of those
two strings based on whether verify_connection() succeeded at startup.

StateReport must accept and display this field.

Status output must read:
```
Session: {session_id}
Mode: connected | fallback
Memory records: {n}
Pending proposals: {n}
Capabilities: respond, status, approve, reject, exit
```

### Task 3 — Diagnostics command
Add a new command: `diagnostics`

When the user types `diagnostics`, the system prints:
```
Model URL: {url or "not set"}
Model name: {name or "not set"}
Mode: connected | fallback
Session file: {path to current session file}
Memory directory: {path}
Proposal directory: {path}
```

The API key must NEVER be printed, even partially. If it is set,
print `API key: set`. If not, print `API key: not set`.

This command lives in `main.py`. No new files needed for this task.

### Task 4 — Dedicated test directory
Move all unit tests out of the component modules into a dedicated
directory: `inanna/tests/`

Create these files:
```
inanna/tests/__init__.py      <- empty
inanna/tests/test_session.py  <- tests from session.py
inanna/tests/test_memory.py   <- tests from memory.py
inanna/tests/test_proposal.py <- tests from proposal.py
inanna/tests/test_state.py    <- tests from state.py
inanna/tests/test_identity.py <- new: tests for build_system_prompt()
```

Remove the test classes from the component modules after moving them.
The component modules must remain clean of test code after this phase.

Tests must still pass when run as:
`py -3 -m unittest discover -s tests`

`test_identity.py` must verify:
- build_system_prompt() returns a non-empty string
- The string contains the word "INANNA"
- The string contains the word "proposal"
- The string contains the word "law" or "laws"

---

## Permitted file changes

```
inanna/
  identity.py          <- NEW
  config.py            <- no changes
  main.py              <- MODIFY: add diagnostics command, pass mode to StateReport
  core/
    session.py         <- MODIFY: use build_system_prompt(), add mode property
    memory.py          <- no changes
    proposal.py        <- no changes
    state.py           <- MODIFY: accept and display mode field
  tests/
    __init__.py        <- NEW
    test_session.py    <- NEW (moved from session.py)
    test_memory.py     <- NEW (moved from memory.py)
    test_proposal.py   <- NEW (moved from proposal.py)
    test_state.py      <- NEW (moved from state.py)
    test_identity.py   <- NEW
  .env                 <- no changes
  .env.example         <- no changes
  requirements.txt     <- no changes
```

---

## What You Are NOT Building in This Phase

- No change to memory logic or proposal logic
- No change to the data directory structure
- No web interface, no API server
- No streaming responses
- No conversation history trimming
- No multi-user support
- No new data storage formats
- Do not change the identity prompt text — use it exactly as written
- Do not add capabilities beyond what is listed in the status output

---

## Definition of Done for Phase 3

- [ ] `identity.py` exists with `build_system_prompt()` returning the
      exact prompt text specified above
- [ ] When asked "who are you?", INANNA identifies herself as INANNA,
      not as the underlying model
- [ ] `status` command shows mode field (connected or fallback)
- [ ] `diagnostics` command prints config and paths, never the API key
- [ ] All tests live in `inanna/tests/` and component modules contain
      no test classes
- [ ] `py -3 -m unittest discover -s tests` passes from `inanna/`
- [ ] No code exists outside the permitted file locations above

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit all work with message: `phase-3-complete`
2. Write `docs/implementation/PHASE_3_REPORT.md` containing:
   - What was built
   - Any decisions made during implementation
   - Any boundaries that felt unclear
   - Any proposals for Phase 4

Then stop. Do not begin Phase 4 without a new CURRENT_PHASE.md
from the Command Center.

---

*Written by: Claude (Command Center)*
*Phase 2 reviewed and approved: 2026-04-18*
