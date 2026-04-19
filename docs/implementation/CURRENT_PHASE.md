# CURRENT PHASE: Cycle 4 - Phase 4.3 - The Privilege Map
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-19**
**Cycle: 4 - The Civic Layer**
**Replaces: Cycle 4 Phase 4.2 - The Access Gate (COMPLETE)**

---

## What This Phase Is

Phase 4.2 gave sessions identity — a token bound to a user.
Phase 4.3 makes that identity mean something.

Right now every command works regardless of who is logged in.
The Guardian and a basic user have the same powers.
That is wrong. The privilege map must be enforced.

Phase 4.3 wires has_privilege() into the command execution path.
Every sensitive command checks the active user before running.
If the privilege is absent, a clean response is returned.
No crash. No silent failure. A clear, honest boundary.

Phase 4.3 also delivers the memory bar improvement:
more blocks, color progression from green to amber to red,
so memory health is readable at a glance.

---

## PART 1: Privilege Enforcement

### Task 1.1 - Privilege check helper

Add to inanna/core/user.py:

```python
def check_privilege(
    active_token,       # SessionToken | None
    user_manager,       # UserManager
    privilege: str,     # required privilege
) -> tuple[bool, str]:
    """Returns (allowed, reason)."""
    if active_token is None:
        return False, "No active session. Type login [name] to identify."
    ok = user_manager.has_privilege(active_token.user_id, privilege)
    if not ok:
        return False, (
            f"Insufficient privileges. "
            f"{active_token.display_name} ({active_token.role}) "
            f"does not have: {privilege}"
        )
    return True, ""
```

### Task 1.2 - Protected commands in main.py and server.py

Apply check_privilege() before executing these commands:

| Command | Required privilege |
|---|---|
| users | all |
| create-user | all |
| memory-clear-all | all |
| forget (all records) | approve_own_memory |
| realm-context [update] | all |
| guardian-log | all |
| nammu-log | all |
| routing-log | all |
| approve | approve_own_memory |
| reject | approve_own_memory |

Commands that remain open to all (no privilege check):
  login, logout, whoami, status, help, history,
  body, diagnostics, realms, memory-map, faculties,
  guardian (read-only inspect), audit-log, proposal-history

Pattern for every protected command:
```python
allowed, reason = check_privilege(self.active_token, self.user_manager, "all")
if not allowed:
    await self.broadcast({"type": "system", "text": f"access > {reason}"})
    return
```

### Task 1.3 - "access" message type in index.html

Add CSS for access denial messages:
```css
.message-access .message-prefix,
.message-access .message-content {
    color: #c86e6e;
    font-size: 0.85rem;
    font-style: italic;
}
```
Prefix: "access :"

Broadcast access denials as:
{"type": "access", "text": "Insufficient privileges..."}

### Task 1.4 - Privilege summary in whoami

Update whoami output to show full privilege list:
```
whoami > ZAERA (guardian)
whoami > privileges: all
whoami > can do: everything
```

For non-guardian roles:
```
whoami > Alice (user)
whoami > privileges: converse, approve_own_memory,
whoami >            read_own_log, forget_own_memory
```

---

## PART 2: Memory Bar Improvement

### Task 2.1 - Richer memory growth bar in index.html

Replace the current simple memory bar with a 20-block
color-progressive bar.

20 blocks total (was 10). Each block is 5% of capacity.
Capacity = 100 lines (was 50 — increase the display cap).

Color progression based on fill percentage:
  0-40%:   green  #6a8a6a  (healthy)
  41-70%:  amber  var(--voice) (growing)
  71-90%:  orange #c8963e (getting full)
  91-100%: red    #c86e6e (at capacity)
  >100%:   red blinking animation

Display text below the bar:
  "{lines} lines used  ({pct}% of {cap} line capacity)"

When over capacity:
  "{lines} / {cap} lines  — over capacity, consider forgetting"
  The text pulses gently (CSS animation, not JS).

CSS for the new bar:
```css
.memory-bar-block {
    display: inline-block;
    width: 8px;
    height: 10px;
    margin: 0 1px;
    border-radius: 1px;
    transition: background-color 0.3s;
}
.memory-bar-block.empty   { background: rgba(200,169,110,0.12); }
.memory-bar-block.green   { background: #6a8a6a; }
.memory-bar-block.amber   { background: var(--voice); }
.memory-bar-block.orange  { background: #c8963e; }
.memory-bar-block.red     { background: #c86e6e; }

@keyframes pulse-warn {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
.memory-over-cap { animation: pulse-warn 2s ease-in-out infinite; }
```

The bar is built in JavaScript from memory_total_lines
and the cap constant (100). Each block gets its color class
based on which fill-percentage zone it falls in.

### Task 2.2 - Update memory cap constant

In server.py and main.py, where memory growth is reported,
update MEMORY_DISPLAY_CAP from 50 to 100.

Update the Guardian MEMORY_GROWTH check threshold in guardian.py
from >= 10 records to >= 20 records (adjust for larger capacity).

---

## Update identity.py and state.py

CURRENT_PHASE = "Cycle 4 - Phase 4.3 - The Privilege Map"

No new commands to add to capabilities.

---

## Tests

Add to inanna/tests/test_user.py:
- check_privilege() returns (False, reason) when token is None
- check_privilege() returns (False, reason) for insufficient privilege
- check_privilege() returns (True, "") for guardian with any privilege
- check_privilege() returns (True, "") for user with "converse"
- check_privilege() returns (False, reason) for user with "all"

Add to inanna/tests/test_guardian.py:
- MEMORY_GROWTH triggers at >= 20 records (updated threshold)

Update test_identity.py: update CURRENT_PHASE assertion.

---

## Permitted file changes

inanna/identity.py              <- MODIFY: update CURRENT_PHASE
inanna/main.py                  <- MODIFY: check_privilege() on protected
                                           commands, update memory cap
inanna/core/
  user.py                       <- MODIFY: add check_privilege() helper
  guardian.py                   <- MODIFY: update MEMORY_GROWTH threshold
  state.py                      <- no changes
inanna/ui/
  server.py                     <- MODIFY: check_privilege() on protected
                                           commands, update memory cap,
                                           broadcast access type messages
  static/index.html             <- MODIFY: 20-block color-progressive
                                           memory bar, access message CSS
inanna/tests/
  test_user.py                  <- MODIFY: add check_privilege tests
  test_guardian.py              <- MODIFY: update threshold test
  test_identity.py              <- MODIFY: update phase assertion

---

## What You Are NOT Building

- No per-user memory scoping (Phase 4.4)
- No per-user interaction log (Phase 4.5)
- No user management UI panel (Phase 4.8)
- No role editing or privilege assignment via UI
- Do not add privilege checks to conversation input —
  the "converse" privilege is assumed for any logged-in user
  interacting with INANNA in normal conversation.
  Only explicit commands are privilege-checked.
- Do not change roles.json

---

## Definition of Done for Phase 4.3

- [ ] check_privilege() helper exists in user.py
- [ ] All listed sensitive commands are privilege-checked
- [ ] Access denials return "access :" messages in muted red
- [ ] Access denials never crash the server
- [ ] whoami shows full privilege list for the active role
- [ ] 20-block color-progressive memory bar in UI
- [ ] Bar colors: green/amber/orange/red by fill percentage
- [ ] Over-capacity text pulses gently
- [ ] Memory display cap updated to 100 lines
- [ ] Guardian MEMORY_GROWTH threshold updated to 20 records
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit with message: cycle4-phase3-complete
2. Write docs/implementation/CYCLE4_PHASE3_REPORT.md
3. Stop. Do not begin Phase 4.4 without a new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-19*
*A privilege is not a wall.*
*It is a shape — the exact outline of what a role can do.*
*Phase 4.3 gives every role its shape.*
