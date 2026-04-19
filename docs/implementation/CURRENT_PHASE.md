# CURRENT PHASE: Cycle 4 - Phase 4.2 - The Access Gate
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-19**
**Cycle: 4 - The Civic Layer**
**Replaces: Cycle 4 Phase 4.1 - The User Identity (COMPLETE)**

---

## What This Phase Is

Phase 4.1 gave users existence — records on disk with roles
and config-driven privileges.

Phase 4.2 gives sessions identity. When the server starts,
it no longer assumes the single Guardian is the only operator.
A session is now bound to a user. That binding is explicit,
lightweight, and governed.

In this phase: session tokens.

A session token is a short-lived string generated at login.
It is stored in the session state and used to identify which
user is active in the current session. The token is not
cryptographically secure yet — that is Phase 4.3. For now
it is a governed identity binding: a UUID tied to a user_id,
valid for the duration of one server session.

No passwords. No OAuth. No external identity. The access gate
in Phase 4.2 is: you state who you are, a token is issued,
and all subsequent actions in that session are associated
with that user_id. The Guardian can always see who is active.

---

## What You Are Building

### Task 1 - inanna/core/session_token.py

Create: inanna/core/session_token.py

Two classes: SessionToken (dataclass) and TokenStore.

SessionToken fields:
  token: str          (UUID4, generated at login)
  user_id: str
  display_name: str
  role: str
  issued_at: str      (ISO timestamp)
  expires_at: str     (ISO timestamp, issued_at + SESSION_HOURS)
  active: bool        (True until logout or expiry)

SESSION_HOURS = 8  (configurable constant)

TokenStore:
  __init__()
  - in-memory only: dict[str, SessionToken]
  - no disk persistence (tokens are session-scoped)

  issue(user_id, display_name, role) -> SessionToken
  validate(token) -> SessionToken | None
    - Returns None if token not found, inactive, or expired
  revoke(token) -> bool
  active_tokens() -> list[SessionToken]
  revoke_all_for_user(user_id) -> int

### Task 2 - The "login" command

Add "login [display_name]" command to main.py and server.py.

Flow:
1. User types: login ZAERA
2. System looks up user by display_name in UserManager
3. If not found: "No user found with name: ZAERA"
4. If found: issue a SessionToken, store in TokenStore
5. Print:
   login > session started for ZAERA (guardian)
   login > token: {first 8 chars}... valid for 8 hours
   login > session bound to user_id: {user_id}

The active token is stored in server/CLI state:
  self.active_token: SessionToken | None = None

The phase banner in the UI header updates to show the
active user after login:
  CYCLE 4 - PHASE 4.2   REALM: DEFAULT   USER: ZAERA   BODY: OK

### Task 3 - The "logout" command

Add "logout" command.

Flow:
1. If no active token: "No active session."
2. If active token: revoke it, clear self.active_token
3. Print: "logout > session ended for {display_name}"

### Task 4 - The "whoami" command

Add "whoami" command.

Output:
  whoami > ZAERA (guardian)
  whoami > user_id: user_6e250a89
  whoami > session token: {first 8 chars}... (active)
  whoami > session expires: Apr 19 20:30
  whoami > privileges: all

If no active session:
  whoami > No active session. Type "login [name]" to identify.

### Task 5 - Active user in status payload

Add to the WebSocket status payload:
  "active_user": {
    "user_id": "user_6e250a89",
    "display_name": "ZAERA",
    "role": "guardian",
    "token_preview": "a3f7b2c1...",
    "expires_at": "2026-04-19T20:30:00"
  }

Or null if no active session.

The UI header shows the active user name when present.

### Task 6 - Auto-login as Guardian on startup

For Phase 4.2, on server/CLI startup:
  1. Call ensure_guardian_exists()
  2. Auto-issue a session token for the Guardian user
  3. Set self.active_token = the issued token
  4. Print: "Auto-login: ZAERA (guardian) | session active"

This means existing workflows are not disrupted.
The Guardian is always the active user unless someone logs in
as a different user. Phase 4.3 will enforce access control.
For now, the binding is informational and auditable.

### Task 7 - Session token in audit log

When a login or logout event occurs, append to session_audit:
  {"event_type": "login", "summary": "ZAERA (guardian) logged in"}
  {"event_type": "logout", "summary": "ZAERA (guardian) logged out"}

### Task 8 - Update identity.py and state.py

CURRENT_PHASE = "Cycle 4 - Phase 4.2 - The Access Gate"

Add "login", "logout", "whoami" to STARTUP_COMMANDS and capabilities.

### Task 9 - Tests

Create inanna/tests/test_session_token.py:
  - SessionToken can be instantiated with required fields
  - TokenStore.issue() returns a SessionToken with a UUID token
  - TokenStore.validate() returns token for valid token string
  - TokenStore.validate() returns None for unknown token
  - TokenStore.validate() returns None for revoked token
  - TokenStore.validate() returns None for expired token
    (set SESSION_HOURS=0 and issue a token to test expiry)
  - TokenStore.revoke() deactivates the token
  - TokenStore.active_tokens() returns only active tokens
  - TokenStore.revoke_all_for_user() revokes all user tokens

Update test_identity.py: update CURRENT_PHASE assertion.
Update test_state.py and test_commands.py: add new commands.

---

## Permitted file changes

inanna/identity.py                <- MODIFY: update CURRENT_PHASE
inanna/main.py                    <- MODIFY: login/logout/whoami commands,
                                             TokenStore instantiation,
                                             auto-login at startup,
                                             active_token state,
                                             active_user in status
inanna/core/
  session_token.py                <- NEW: SessionToken, TokenStore
  state.py                        <- MODIFY: add new commands
  user.py                         <- no changes
inanna/ui/
  server.py                       <- MODIFY: login/logout/whoami commands,
                                             TokenStore instantiation,
                                             auto-login at startup,
                                             active_user in status payload,
                                             user name in header update
  static/index.html               <- MODIFY: show active user in header,
                                             handle active_user in status
inanna/tests/
  test_session_token.py           <- NEW
  test_identity.py                <- MODIFY: update phase assertion
  test_state.py                   <- MODIFY: add capabilities
  test_commands.py                <- MODIFY: add capabilities

---

## What You Are NOT Building

- No password hashing or verification
- No OAuth or external identity provider
- No access control enforcement (Phase 4.3)
- No per-user memory scoping (Phase 4.4)
- No per-user log (Phase 4.5)
- No token persistence across server restarts
- No multi-session support per user (one active token per user)
- Do not change the UserManager or roles.json

---

## Definition of Done for Phase 4.2

- [ ] core/session_token.py with SessionToken and TokenStore
- [ ] "login [name]" issues a token and binds the session
- [ ] "logout" revokes the token and clears the binding
- [ ] "whoami" shows the active user and session state
- [ ] Auto-login as Guardian at startup
- [ ] Active user shown in UI header and status payload
- [ ] Login/logout events appear in audit log
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit with message: cycle4-phase2-complete
2. Write docs/implementation/CYCLE4_PHASE2_REPORT.md
3. Stop. Do not begin Phase 4.3 without a new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-19*
*A session knows who it belongs to.*
*That is the access gate.*
*Not a wall — a binding.*
