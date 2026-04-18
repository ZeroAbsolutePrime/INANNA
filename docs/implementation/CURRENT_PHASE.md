# CURRENT PHASE: Phase 4 — The Reflective Loop
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-18**
**Replaces: Phase 3 — The Named Presence (COMPLETE)**

---

## What Phase 4 Is

Phase 3 gave INANNA her name and made the system readable.
Phase 4 makes the memory layer *meaningful in conversation*.

Until now, memory has been a technical mechanism — it loads context,
it receives proposals, it writes records. But the user cannot ask INANNA
what she remembers. She cannot reflect. She cannot show her own inner state
in language.

Phase 4 adds three things:
1. A `reflect` command — INANNA speaks her own memory aloud
2. A testable conversation loop — so command behavior can be validated
   without terminal scripting
3. Two small honesty fixes Codex identified: phase name in status,
   and diagnostics listed in capabilities

These deepen what already exists. Nothing new is invented.

---

## What You Are Building

### Task 1 — The `reflect` command

When the user types `reflect`, INANNA responds in her own voice,
summarizing what she currently holds in memory about this user and
their conversation history.

This is NOT a raw dump of memory files. It is a model-generated
reflection, grounded in the startup context lines already loaded.

Implementation:

In `main.py`, add a `reflect` command handler in the input loop.
When triggered, call a new Engine method: `engine.reflect(context_summary)`.

In `core/session.py`, add this method to the Engine class:

```python
def reflect(self, context_summary: list[str]) -> str:
    if not context_summary:
        return "I hold no approved memory of our prior conversations yet."
    messages = [
        {
            "role": "system",
            "content": build_system_prompt(),
        },
        {
            "role": "user",
            "content": (
                "Please reflect on what you currently remember about me "
                "and our conversation history, based only on your approved memory. "
                "Speak honestly about what you know and what you do not know."
            ),
        },
    ]
    # Inject memory as assistant context before the reflection request
    if context_summary:
        memory_block = "\n".join(context_summary)
        messages.insert(1, {
            "role": "assistant",
            "content": f"From my approved memory:\n{memory_block}",
        })
    if self.model_url and self.model_name and self._connected:
        try:
            return self._call_openai_compatible(messages)
        except Exception:
            pass
    return (
        "From my approved memory I hold these lines:\n"
        + "\n".join(f"  {line}" for line in context_summary)
    )
```

The reflect command must NOT generate a proposal. Reflection is
read-only. It does not trigger a memory update.

The reflect command must print the response prefixed with `inanna> `
(not `assistant> `) to distinguish it as a first-person reflection.

### Task 2 — Testable conversation loop

Refactor the main input loop into a function that can be called
from tests without requiring a live terminal.

Extract the command-dispatch logic from `main()` into a new function:

```python
def handle_command(
    command: str,
    session: Session,
    memory: Memory,
    proposal: Proposal,
    state_report: StateReport,
    engine: Engine,
    startup_context: dict,
    config: Config,
) -> str | None:
```

This function:
- Takes a command string
- Returns a string response (what would be printed)
- Returns None if the command means exit
- Does NOT call print() itself — the caller handles output
- Does NOT call input() — it receives the command as a parameter

`main()` calls `handle_command()` in its loop and prints the result.

Add tests in `inanna/tests/test_commands.py` covering:
- `status` returns a string containing "Session:"
- `diagnostics` returns a string containing "Model URL:"
- `reflect` with empty context returns the no-memory message
- `approve` with no pending proposals returns "No pending proposals."
- unknown input is treated as conversation and returns a string

### Task 3 — Honesty fixes

**Fix 1: Phase name in status**
Add one line to the status output:
```
Phase: {current phase name}
```
The current phase name must come from `identity.py`, not be hardcoded
in `state.py`. Add a constant to `identity.py`:
```python
CURRENT_PHASE = "Phase 4 — The Reflective Loop"
```
`StateReport` imports and uses this constant.

**Fix 2: diagnostics in capabilities**
The status output currently lists:
`Capabilities: respond, status, approve, reject, exit`

Change it to:
`Capabilities: respond, reflect, status, diagnostics, approve, reject, exit`

This change lives in `state.py`.

---

## Permitted file changes

```
inanna/
  identity.py        <- MODIFY: add CURRENT_PHASE constant
  config.py          <- no changes
  main.py            <- MODIFY: add reflect command, extract handle_command()
  core/
    session.py       <- MODIFY: add reflect() method to Engine
    memory.py        <- no changes
    proposal.py      <- no changes
    state.py         <- MODIFY: add phase field, update capabilities line
  tests/
    __init__.py      <- no changes
    test_session.py  <- no changes
    test_memory.py   <- no changes
    test_proposal.py <- no changes
    test_state.py    <- MODIFY: add test for phase field in status output
    test_identity.py <- MODIFY: add test for CURRENT_PHASE constant
    test_commands.py <- NEW: tests for handle_command()
```

---

## What You Are NOT Building in This Phase

- No change to memory logic or proposal logic
- No change to the data directory structure
- No web interface, no API server
- No streaming responses
- No new data storage formats
- No multi-user support
- The reflect command must not generate proposals
- handle_command() must not call print() or input()
- Do not change the identity prompt text in PROMPT
- Do not add capabilities beyond what is listed above

---

## Definition of Done for Phase 4

- [ ] `reflect` command works and prints under `inanna> ` prefix
- [ ] `reflect` with no memory returns the honest no-memory message
- [ ] `reflect` does NOT generate a proposal
- [ ] `handle_command()` exists in `main.py` and is imported by tests
- [ ] `py -3 -m unittest discover -s tests` passes from `inanna/`
- [ ] `test_commands.py` covers all five cases listed above
- [ ] `status` output includes `Phase: Phase 4 — The Reflective Loop`
- [ ] `status` capabilities line includes reflect and diagnostics
- [ ] `CURRENT_PHASE` constant exists in `identity.py`
- [ ] No code exists outside the permitted file locations above

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit all work with message: `phase-4-complete`
2. Write `docs/implementation/PHASE_4_REPORT.md` containing:
   - What was built
   - Any decisions made during implementation
   - Any boundaries that felt unclear
   - Any proposals for Phase 5

Then stop. Do not begin Phase 5 without a new CURRENT_PHASE.md
from the Command Center.

---

*Written by: Claude (Command Center)*
*Phase 3 reviewed and approved: 2026-04-18*
