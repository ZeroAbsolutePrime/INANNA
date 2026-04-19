# CURRENT PHASE: Cycle 4 - Phase 4.6 - The Governed Invite
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-19**
**Cycle: 4 - The Civic Layer**
**Replaces: Cycle 4 Phase 4.5 - The User Log (COMPLETE)**

---

## What This Phase Is

Phase 4.5 gave every user a personal record.
Phase 4.6 governs how users arrive in the system.

Right now, user creation is a single proposal flow:
the Guardian types "create-user Alice user default",
approves the proposal, and Alice exists.
Alice has no agency in this. She is created, not invited.

Phase 4.6 introduces the Governed Invite:
a two-step onboarding where the Guardian or Operator
generates an invite token, and the new person activates
their account by presenting that token.

This matters for three reasons:

1. Consent: the person chooses to join, not just appears.
2. Identity: the person sets their own display name.
3. Auditability: the full invite chain is recorded.

The invite token is a short, human-readable code.
Not a UUID. Something a person can type or share easily.
Example: INANNA-7X4K-2M9P

---

## What You Are Building

### Task 1 - Invite record in inanna/core/user.py

Add to user.py:

```python
from dataclasses import dataclass

@dataclass
class InviteRecord:
    invite_code: str      # e.g. INANNA-7X4K-2M9P
    role: str
    assigned_realms: list[str]
    created_by: str       # user_id of inviter
    created_at: str
    expires_at: str       # created_at + 48 hours
    status: str           # "pending" | "accepted" | "expired"
    accepted_by: str      # user_id once accepted, else ""
```

Add to UserManager:

  create_invite(role, assigned_realms, created_by) -> InviteRecord
    - Generates invite_code: "INANNA-" + 4 random uppercase chars
      + "-" + 4 random uppercase chars
    - Stores invite in inanna/data/invites/{invite_code}.json
    - expires_at = created_at + 48 hours

  get_invite(invite_code) -> InviteRecord | None

  accept_invite(invite_code, display_name) -> UserRecord | None
    - Validates invite: exists, status==pending, not expired
    - Creates the UserRecord via create_user()
    - Updates invite status to "accepted", accepted_by = new user_id
    - Returns the new UserRecord

  list_invites(status=None) -> list[InviteRecord]
    - Lists all invites, optionally filtered by status

  expire_old_invites() -> int
    - Marks expired invites, returns count
    - Called at startup

### Task 2 - "invite" command

Add command: invite [role] [realm]

Privilege required: invite_users
(operators and guardians have this privilege)

Flow:
1. Check privilege
2. Create a proposal:
   [INVITE PROPOSAL] | Create invite: role=user realm=default | status: pending
3. After approval: generate invite record, show the code:

```
invite > Invite created.
invite > Code: INANNA-7X4K-2M9P
invite > Role: user  Realm: default
invite > Expires: Apr 21 22:00  (48 hours)
invite > Share this code with the person you are inviting.
invite > They join with: join INANNA-7X4K-2M9P [their name]
```

### Task 3 - "join" command

Add command: join [invite_code] [display_name]

No privilege required — this is how new people enter.

Flow:
1. Look up invite by code
2. If not found: "join > Invalid invite code."
3. If expired: "join > This invite has expired."
4. If already accepted: "join > This invite has already been used."
5. If valid:
   - Call accept_invite(code, display_name)
   - Issue a session token for the new user
   - Set active_token to the new user
   - Show:

```
join > Welcome, Alice.
join > Your account has been created.
join > Role: user  Realm: default
join > You are now logged in.
join > Type "whoami" to see your session details.
```

The join command does NOT require a proposal.
The invite itself was proposal-governed.
The acceptance is the fulfillment of that proposal.

### Task 4 - "invites" command

Add command: invites

Privilege required: all (Guardian) or invite_users (Operator)

Shows all invites the active user created (or all, if Guardian):

```
Invites (3 total):
  [pending]   INANNA-7X4K-2M9P  user/default  expires Apr 21
  [accepted]  INANNA-3R8J-5N2Q  user/default  accepted by Alice
  [expired]   INANNA-1M4P-9K7X  operator/arcanum  expired Apr 18
```

### Task 5 - Invite audit events

When an invite is created, append to session_audit:
  {"event_type": "invite", "summary": "invite INANNA-7X4K-2M9P created for user/default"}

When an invite is accepted, append:
  {"event_type": "join", "summary": "Alice joined via invite INANNA-7X4K-2M9P"}

### Task 6 - expire_old_invites at startup

Call expire_old_invites() at server and CLI startup,
alongside ensure_guardian_exists().

Print how many were expired if > 0:
  "Expired N invite(s)."

### Task 7 - Update identity.py and state.py

CURRENT_PHASE = "Cycle 4 - Phase 4.6 - The Governed Invite"

Add "invite", "join", "invites" to STARTUP_COMMANDS and capabilities.

### Task 8 - Tests

Add to inanna/tests/test_user.py:
  - UserManager.create_invite() creates an InviteRecord
  - Invite code starts with "INANNA-"
  - get_invite() returns InviteRecord for valid code
  - get_invite() returns None for unknown code
  - accept_invite() creates a UserRecord and updates invite status
  - accept_invite() returns None for expired invite
  - accept_invite() returns None for already-accepted invite
  - list_invites() returns all invites
  - list_invites(status="pending") filters correctly
  - expire_old_invites() marks past-expiry invites as expired

Update test_identity.py: update CURRENT_PHASE assertion.
Update test_state.py and test_commands.py: add new commands.

---

## Permitted file changes

inanna/identity.py              <- MODIFY: update CURRENT_PHASE
inanna/main.py                  <- MODIFY: invite/join/invites commands,
                                           expire_old_invites at startup
inanna/core/
  user.py                       <- MODIFY: InviteRecord dataclass,
                                           create_invite(), get_invite(),
                                           accept_invite(), list_invites(),
                                           expire_old_invites()
  state.py                      <- MODIFY: add new commands
inanna/ui/
  server.py                     <- MODIFY: invite/join/invites commands,
                                           expire_old_invites at startup,
                                           invite/join audit events
  static/index.html             <- no changes
inanna/tests/
  test_user.py                  <- MODIFY: add invite tests
  test_identity.py              <- MODIFY: update phase assertion
  test_state.py                 <- MODIFY: add capabilities
  test_commands.py              <- MODIFY: add capabilities

---

## What You Are NOT Building

- No email delivery of invite codes
- No invite UI panel (Phase 4.8)
- No invite revocation (the Guardian can always delete a user)
- No invite renewal or extension
- No multi-use invites (each code is single-use)
- No realm creation through the invite flow
- Do not change the existing create-user flow — it stays as is
  (Guardians can still create users directly)

---

## Definition of Done for Phase 4.6

- [ ] InviteRecord dataclass exists in user.py
- [ ] create_invite() generates INANNA-XXXX-XXXX codes
- [ ] "invite [role] [realm]" creates invite via proposal
- [ ] "join [code] [name]" accepts invite and logs in the new user
- [ ] "invites" lists invites with status
- [ ] Expired invites marked at startup
- [ ] Invite and join events in audit trail
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit with message: cycle4-phase6-complete
2. Write docs/implementation/CYCLE4_PHASE6_REPORT.md
3. Stop. Do not begin Phase 4.7 without a new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-19*
*A person chooses to enter. That choice is recorded.*
*The invite is the governance. The joining is the consent.*
