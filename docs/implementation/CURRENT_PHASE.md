# CURRENT PHASE: Cycle 4 - Phase 4.4 - The User Memory
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-19**
**Cycle: 4 - The Civic Layer**
**Replaces: Cycle 4 Phase 4.3 - The Privilege Map (COMPLETE)**

---

## What This Phase Is

Phase 4.4 has four goals that belong together:

**Goal 1 - User-scoped memory.**
Memory records now carry a user_id. When ZAERA approves a memory,
it is tagged as ZAERA's. When Alice approves a memory, it is Alice's.
The grounding turn only injects memory that belongs to the active user.

**Goal 2 - Guardian user management actions.**
Beyond inspect, the Guardian can now: clear governance event history,
dismiss all current alerts, and switch active user context.
The Guardian Room panel gains these actions as small buttons.

**Goal 3 - switch-user command.**
ZAERA (guardian role only) can type "switch-user Alice" to experience
the system as Alice — her memory, her privileges, her context.
A clear banner shows when operating as another user.
Switch back with "switch-user ZAERA" or "switch-user off".

**Goal 4 - UI button sizing.**
All panel action buttons reduced to compact size.
More breathing room. Less visual weight.

---

## GOAL 1: User-Scoped Memory

### Task 1.1 - Add user_id to memory records

Update Memory.write_memory() in memory.py to accept user_id parameter.
Store it in the memory record JSON alongside realm_name.

```python
def write_memory(self, session_id, summary_lines, proposal_id,
                 realm_name="", user_id="") -> str:
```

Existing records without user_id are treated as belonging to
the guardian (backward compatible).

### Task 1.2 - Filter memory by active user in grounding

In Engine._build_grounding_turn() and startup_context(),
filter loaded memory records to only those matching the active user_id.

If no user_id is set (no active session), load all records
(preserves existing behavior for backward compat).

Pass active user_id through from main.py and server.py when
building the startup context and grounding turn.

### Task 1.3 - Pass user_id when writing memory

In main.py and server.py, when a memory proposal is approved
and write_memory() is called, pass the active_token.user_id
(or "" if no active token).

---

## GOAL 2: Guardian Room Actions

### Task 2.1 - "guardian-clear-events" command

Add command: guardian-clear-events

Requires privilege: all

Clears the governance event log file on disk:
  inanna/data/nammu/governance_log.jsonl -> truncated to empty

Creates a proposal first:
  [GUARDIAN PROPOSAL] | Clear governance event log | status: pending

After approval, truncate the file and broadcast:
  guardian > Governance event log cleared.

Add to STARTUP_COMMANDS and capabilities.

### Task 2.2 - "guardian-dismiss" command

Add command: guardian-dismiss

Clears the in-memory alert list in the server's guardian state.
The next inspection will re-populate if conditions still exist.

No proposal needed — dismissing alerts is a read action,
not a data mutation.

Broadcast:
  guardian > Alerts dismissed. Next inspection will re-evaluate.

Add [ clear events ] and [ dismiss ] buttons to Guardian Room panel.
These appear below the [ inspect ] button.

### Task 2.3 - Guardian Room panel button layout

Replace the current single [ inspect ] button with a row of three:
  [ inspect ]  [ dismiss ]  [ clear events ]

All three are small compact buttons (see Goal 4 for sizing).

---

## GOAL 3: switch-user Command

### Task 3.1 - switch-user in main.py and server.py

Add command: switch-user [display_name]

Requires privilege: all (guardian only)

Flow:
1. Validate requester has "all" privilege
2. Look up target user by display_name
3. If not found: "switch-user > No user found: [name]"
4. Issue a new SessionToken for the target user
5. Set self.active_token to the new token
6. Broadcast:
   switch-user > Now operating as: Alice (user)
   switch-user > Type "switch-user ZAERA" to return to Guardian.

"switch-user off" or "switch-user [guardian_name]" returns to Guardian.

When operating as another user:
- The UI header shows: USER: Alice [as ZAERA]
- The status payload includes:
    "acting_as": {"display_name": "Alice", "role": "user"},
    "original_user": {"display_name": "ZAERA", "role": "guardian"}
- Memory grounding uses Alice's memory
- Privilege checks use Alice's privileges
- A warning banner appears in the conversation area:
    "⚠ Operating as Alice (user) — Guardian context suspended"

Add switch-user to STARTUP_COMMANDS and capabilities.

---

## GOAL 4: Button Size Reduction

### Task 4.1 - Compact button CSS

Update all panel action buttons to compact size:

```css
.panel-btn {
    padding: 3px 10px;
    font-size: 0.75rem;
    letter-spacing: 0.08em;
    border: 1px solid var(--border);
    background: transparent;
    color: var(--dim);
    cursor: pointer;
    border-radius: 2px;
    transition: color 0.15s, border-color 0.15s;
}
.panel-btn:hover {
    color: var(--voice);
    border-color: var(--voice);
}
.panel-btn.warn:hover {
    color: var(--fallback);
    border-color: var(--fallback);
}
```

Apply .panel-btn class to:
  [ inspect ] [ dismiss ] [ clear events ]  (Guardian Room)
  [ approve ] [ reject ]                    (Proposals)
  [ load full history ]                     (Proposals)
  [ clear all ]                             (Memory)
  [ forget ]                                (Memory records)

---

## Update identity.py and state.py

CURRENT_PHASE = "Cycle 4 - Phase 4.4 - The User Memory"

Add "guardian-clear-events", "guardian-dismiss", "switch-user"
to STARTUP_COMMANDS and capabilities in state.py.

---

## Tests

Update inanna/tests/test_memory.py:
- write_memory() accepts user_id parameter
- Memory record contains user_id field when written
- load_memory_records() filters by user_id when provided

Add to inanna/tests/test_user.py:
- check_privilege() returns False for switch-user when role is user

Update test_identity.py: update CURRENT_PHASE assertion.
Update test_state.py and test_commands.py: add new commands.

---

## Permitted file changes

inanna/identity.py              <- MODIFY: update CURRENT_PHASE
inanna/main.py                  <- MODIFY: pass user_id to write_memory,
                                           pass user_id to startup_context,
                                           guardian-clear-events command,
                                           guardian-dismiss command,
                                           switch-user command
inanna/core/
  memory.py                     <- MODIFY: write_memory() user_id param,
                                           filter by user_id in load
  session.py                    <- MODIFY: pass user_id to grounding
  state.py                      <- MODIFY: add new commands
  user.py                       <- no changes
  guardian.py                   <- no changes
inanna/ui/
  server.py                     <- MODIFY: same as main.py goals,
                                           acting_as in status payload
  static/index.html             <- MODIFY: compact .panel-btn class,
                                           Guardian Room 3-button row,
                                           acting-as banner in conversation,
                                           USER: Alice [as ZAERA] in header,
                                           acting_as in status handler
inanna/tests/
  test_memory.py                <- MODIFY: user_id tests
  test_user.py                  <- MODIFY: switch-user privilege test
  test_identity.py              <- MODIFY: update phase assertion
  test_state.py                 <- MODIFY: add capabilities
  test_commands.py              <- MODIFY: add capabilities

---

## What You Are NOT Building

- No per-user interaction log (Phase 4.5)
- No user management UI panel (Phase 4.8)
- No cross-user memory sharing
- No memory export or import
- Do not change the proposal flow or governance rules
- Do not add new Faculty classes
- The switch-user command is Guardian-only (privilege: all)

---

## Definition of Done for Phase 4.4

- [ ] Memory records carry user_id field
- [ ] Grounding turn filters memory by active user_id
- [ ] write_memory() passes active user_id from token
- [ ] guardian-clear-events creates proposal then clears log
- [ ] guardian-dismiss clears in-memory alerts
- [ ] Guardian Room has 3 compact buttons: inspect/dismiss/clear events
- [ ] switch-user works for guardian role only
- [ ] UI header shows "USER: Alice [as ZAERA]" when switched
- [ ] Warning banner appears in conversation when switched
- [ ] All panel buttons use compact .panel-btn class
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit with message: cycle4-phase4-complete
2. Write docs/implementation/CYCLE4_PHASE4_REPORT.md
3. Stop. Do not begin Phase 4.5 without a new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-19*
*Memory is personal. The Guardian can walk in other shoes.*
*But she always knows whose shoes she is wearing.*
