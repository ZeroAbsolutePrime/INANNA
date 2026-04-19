# CURRENT PHASE: Cycle 4 - Phase 4.5 - The User Log
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-19**
**Cycle: 4 - The Civic Layer**
**Replaces: Cycle 4 Phase 4.4 - The User Memory (COMPLETE)**

---

## What This Phase Is

Phase 4.4 gave memory a user identity.
Phase 4.5 gives interactions a personal record.

Every conversation turn a user has with INANNA is now logged
to that user's personal interaction log. The log is:
  - Private: readable only by that user and the Guardian
  - Persistent: survives across sessions
  - Honest: contains the actual input and response, not a summary
  - Governed: the user can read it, but cannot alter it

This is Law 4 (Readable System Truth) applied to the user:
a person should be able to ask what INANNA has done with
their words, and receive a clear, bounded, honest answer.

This phase also fixes the noted issue from Phase 4.4:
create-user now records the actual Guardian user_id as created_by,
not the string "system".

---

## What You Are Building

### Task 1 - inanna/core/user_log.py

Create: inanna/core/user_log.py

One class: UserLog

UserLog:
  __init__(logs_dir: Path)
  - logs_dir: inanna/data/user_logs/
  - One JSONL file per user: {user_id}.jsonl

  append(user_id, session_id, role, content, response_preview) -> None
  - Appends one entry to the user's log file
  - Entry format:
    {
      "timestamp": "ISO",
      "session_id": "...",
      "role": "user",
      "content": "full input text",
      "response_preview": "first 200 chars of INANNA response"
    }

  load(user_id, limit=50) -> list[dict]
  - Loads the last N entries from the user log
  - Returns [] if no log exists

  entry_count(user_id) -> int
  - Returns total number of log entries for a user

  clear(user_id) -> int
  - Clears all entries for a user
  - Returns count of cleared entries
  - Requires Guardian approval via proposal (handled in main.py/server.py)

### Task 2 - Log every conversation turn

In main.py and server.py, after every successful Faculty response
(crown or analyst), append to the active user's log:

```python
if active_token:
    user_log.append(
        user_id=active_token.user_id,
        session_id=session_id,
        role="user",
        content=user_input,
        response_preview=response_text[:200],
    )
```

Logging is silent — it does not generate a proposal.
It does not appear in the conversation.
It is infrastructure, not governance.

### Task 3 - The "my-log" command

Add command: my-log

Privilege required: read_own_log

Output (newest first):
```
Your interaction log (N entries):

  Apr 19 22:15  Hello, I am ZAERA
    inanna > Hello ZAERA! It is wonderful to have you here...

  Apr 19 21:45  What is the nature of consciousness?
    inanna > That is one of the deepest questions in philosophy...
```

Show last 20 entries by default.

### Task 4 - Guardian log access

Add command: user-log [display_name]

Privilege required: all (Guardian only)

Shows the interaction log for any named user.
Same format as my-log.

Output header:
```
Interaction log for Alice (user_abc12345) — N entries:
```

This is the Guardian's window into any user's history.
It is not surveillance — it is accountability.
The user knows their log exists (Law 4).
The Guardian can read it (Law 3 — governance above the model).

### Task 5 - Log entry count in status payload

Add to the status payload:
  "user_log_count": N   (entries for the active user)

### Task 6 - Fix create-user created_by

In main.py and server.py, when processing a create_user proposal
approval, pass the active_token.user_id as created_by instead of
the string "system":

```python
created_by = active_token.user_id if active_token else "system"
```

### Task 7 - UserLog in the data directory

User logs live at: inanna/data/user_logs/{user_id}.jsonl

This directory is created automatically on first log write.
It is realm-agnostic for now — one global log per user.
(Realm-scoped logs are a future enhancement.)

### Task 8 - Update identity.py and state.py

CURRENT_PHASE = "Cycle 4 - Phase 4.5 - The User Log"

Add "my-log" and "user-log" to STARTUP_COMMANDS and capabilities.

### Task 9 - Tests

Create inanna/tests/test_user_log.py:
  - UserLog can be instantiated with a temp directory
  - append() creates the log file if absent
  - load() returns empty list for missing file
  - load() returns correct entries after append
  - entry_count() returns 0 for missing file
  - entry_count() returns correct count after appends
  - clear() removes all entries and returns count
  - Multiple users have separate log files

Update test_identity.py: update CURRENT_PHASE assertion.
Update test_state.py and test_commands.py: add new commands.

---

## Permitted file changes

inanna/identity.py              <- MODIFY: update CURRENT_PHASE
inanna/main.py                  <- MODIFY: instantiate UserLog,
                                           log every conversation turn,
                                           my-log command,
                                           user-log command,
                                           fix create-user created_by
inanna/core/
  user_log.py                   <- NEW: UserLog class
  state.py                      <- MODIFY: add new commands
inanna/ui/
  server.py                     <- MODIFY: instantiate UserLog,
                                           log every conversation turn,
                                           my-log and user-log commands,
                                           user_log_count in status payload,
                                           fix create-user created_by
  static/index.html             <- no changes
inanna/tests/
  test_user_log.py              <- NEW
  test_identity.py              <- MODIFY: update phase assertion
  test_state.py                 <- MODIFY: add capabilities
  test_commands.py              <- MODIFY: add capabilities

---

## What You Are NOT Building

- No UI panel for the user log (Phase 4.8)
- No log export or download
- No log search or filtering
- No log encryption
- No per-realm log scoping
- Do not log governance blocks (those stay in the governance log)
- Do not log tool execution details (those stay in the audit surface)
- Do not add log entries for commands — only conversation turns

---

## Definition of Done for Phase 4.5

- [ ] core/user_log.py exists with UserLog class
- [ ] Every conversation turn appended to active user log
- [ ] "my-log" shows last 20 entries for the active user
- [ ] "user-log [name]" shows any user log (Guardian only)
- [ ] Log entries include timestamp, content, response preview
- [ ] user_log_count in status payload
- [ ] create-user now records actual Guardian user_id as created_by
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit with message: cycle4-phase5-complete
2. Write docs/implementation/CYCLE4_PHASE5_REPORT.md
3. Stop. Do not begin Phase 4.6 without a new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-19*
*A person should be able to ask what was done with their words.*
*Phase 4.5 makes that question answerable.*
