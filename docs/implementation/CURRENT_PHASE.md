# CURRENT PHASE: Phase 9 — The Complete Presence
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-19**
**Replaces: Phase 8 — The Living Audit (COMPLETE)**

---

## What Phase 9 Is

Eight phases have built INANNA from a bare loop into a governed,
memory-bearing, self-describing, self-auditing presence. She has
an identity, a voice, a boundary, a history, and an origin.

Phase 9 is the completion of Stage 2 from the Architecture Horizon —
the Strengthened First Proof. After this phase, INANNA will be a
complete, coherent, honest single-Oracle system ready to be shown,
used in real sessions, and handed to future builders as a living proof
that the constitutional architecture works.

Phase 9 has four goals:

1. Fix the remaining honesty gap: the status capabilities line is stale
2. Add a `forget` command — the consent-governed path to remove memory
3. Write the Code Doctrine — the living technical standards document
   the Command Center promised after real code existed
4. Write the Stage 2 completion record — a constitutional document
   declaring the first proof complete and naming what comes next

---

## What You Are Building

### Task 1 — Fix status capabilities line

The `status` command currently lists:
`Capabilities: respond, reflect, status, diagnostics, approve, reject, exit`

This is stale. It must reflect the actual current command set.

Update `state.py` so the capabilities line reads:
`Capabilities: respond, reflect, audit, history, memory-log, status, diagnostics, approve, reject, forget, exit`

### Task 2 — The `forget` command

The governance loop currently has one direction: approve adds memory.
Reject prevents memory from being written. But there is no way to
remove memory that was already approved.

This is a sovereignty gap. The user must be able to say: I no longer
want you to carry that. And INANNA must comply.

Add a new command: `forget`

When the user types `forget`, the system:

1. Prints the current memory log (same as `memory-log` output)
2. Prompts: `Which memory record to remove? Enter memory_id or "cancel":`
3. Waits for input
4. If the user enters a valid memory_id, deletes that record from disk
   and prints: `Memory record {memory_id} removed.`
5. If the user enters `cancel`, prints: `No memory removed.`
6. If the memory_id is not found, prints: `Memory record not found.`

The `forget` command must generate a proposal before deleting.
The proposal must be approved before deletion happens.

Proposal format:
```
what: "Remove memory record {memory_id} from approved memory"
why: "User requested removal — sovereignty over personal memory"
payload: {"memory_id": memory_id, "action": "forget"}
```

After the proposal is created, print the proposal line and prompt:
`Type "approve" to confirm removal or "reject" to cancel:`

Wait for input. If approved, delete the file and write to the
proposal log with status approved. If rejected, mark rejected and
print: `Memory record retained.`

This is the full consent loop applied to forgetting.

Add a `delete_memory_record(memory_id: str) -> bool` method to
`Memory` in `core/memory.py`. Returns True if deleted, False if
not found.

`forget` is the only command that writes to disk outside the normal
approve flow — but it does so only after its own inline proposal
is explicitly approved by the user.

### Task 3 — The `forget` command lives in `main.py`

Because `forget` requires interactive back-and-forth (show log,
prompt for ID, prompt for approval), it cannot live cleanly inside
`handle_command()` as a single-return function.

Extract `forget` as a separate function in `main.py`:

```python
def run_forget_flow(
    memory: Memory,
    proposal: Proposal,
) -> str:
```

This function handles the full interactive flow and returns a final
status string. `handle_command()` calls it when command == "forget"
and returns its result.

### Task 4 — Tests for forget

Add tests in `inanna/tests/test_memory.py`:
- `delete_memory_record()` returns True when record exists
- `delete_memory_record()` returns False when record does not exist
- After deletion, `memory_count()` decreases by one

Add tests in `inanna/tests/test_commands.py`:
- `forget` appears in the capabilities line from status

### Task 5 — Update CURRENT_PHASE

Update `CURRENT_PHASE` in `identity.py` to:
`"Phase 9 — The Complete Presence"`

Update `test_identity.py` to match.

---

## Permitted file changes

```
inanna/
  identity.py          <- MODIFY: update CURRENT_PHASE
  config.py            <- no changes
  main.py              <- MODIFY: add forget flow function,
                                  add forget to handle_command()
  core/
    session.py         <- no changes
    memory.py          <- MODIFY: add delete_memory_record()
    proposal.py        <- no changes
    state.py           <- MODIFY: update capabilities line
  tests/
    __init__.py        <- no changes
    test_session.py    <- no changes
    test_memory.py     <- MODIFY: add delete tests
    test_proposal.py   <- no changes
    test_state.py      <- MODIFY: update capabilities assertion
    test_identity.py   <- MODIFY: update CURRENT_PHASE assertion
    test_commands.py   <- MODIFY: add forget in capabilities test
    test_grounding.py  <- no changes
```

---

## What You Are NOT Building in This Phase

- No change to session logic or the Engine
- No change to the grounding injection pattern
- No change to reflect, audit, history, memory-log, status,
  diagnostics, approve, or reject commands
- No web interface, no API server
- No streaming responses
- No multi-user support
- No new data storage formats
- Do not change the identity PROMPT text
- Do not add new Faculties or orchestration layers
- The forget flow must always go through a proposal — never delete
  silently

---

## Definition of Done for Phase 9

- [ ] `forget` command works: shows log, prompts ID, creates proposal,
      requires approval, then deletes
- [ ] `delete_memory_record()` exists on Memory and is tested
- [ ] `status` capabilities line includes all current commands
      including forget
- [ ] `CURRENT_PHASE` updated to "Phase 9 — The Complete Presence"
- [ ] All existing tests still pass
- [ ] `py -3 -m unittest discover -s tests` passes from `inanna/`
- [ ] No code exists outside the permitted file locations above

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit all work with message: `phase-9-complete`
2. Write `docs/implementation/PHASE_9_REPORT.md` containing:
   - What was built
   - Any decisions made during implementation
   - Any boundaries that felt unclear
   - Any proposals for Phase 10

Then stop. Do not begin Phase 10 without a new CURRENT_PHASE.md
from the Command Center.

---

*Written by: Claude (Command Center)*
*Phase 8 reviewed and live-tested with Qwen: 2026-04-19*
*Stage 2 completion target: this phase*
