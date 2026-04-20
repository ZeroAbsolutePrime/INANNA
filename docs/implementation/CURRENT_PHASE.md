# CURRENT PHASE: Cycle 4 - Phase 4.8 - The Admin Surface
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-20**
**Cycle: 4 - The Civic Layer**
**Replaces: Cycle 4 Phase 4.7 - The Realm Access (COMPLETE)**

## What This Phase Is

Seven phases built the civic infrastructure: user records, session tokens,
privilege maps, user memory, interaction logs, invite flow, realm access.
All of it accessible via commands. None visible at a glance.

Phase 4.8 builds the Admin Surface: a dedicated Guardian/Operator panel
showing the full civic state without typing a single command.
Who exists, what roles they hold, which realms they access,
which invites are active, what the realm structure looks like.

Visible only to Guardian and Operator roles.

---

## Task 1 - Admin Surface panel in index.html

Add a new collapsible section at the top of the side panel.
Visible only when active user has role guardian or operator.
Default state: collapsed.

Header: ADMIN  (3 users  2 realms)  badge  toggle-arrow

When expanded, three sub-sections:

USERS sub-section:
  Shows each user: display_name, role, assigned_realms, status
  Action buttons: [ invite ]  [ + user ]

INVITES sub-section:
  Shows each invite: code, role/realm, status, date
  Action button: [ + invite ]

REALMS sub-section:
  Shows each realm: name, purpose, governance_sensitivity
  Action button: [ + realm ]

Panel sends {"type":"command","cmd":"admin-surface"} on expand.

[ invite ] and [ + invite ] open an inline form:
  Role selector, realm input, [ create invite ] button
  On submit: sends invite command via WebSocket.

[ + realm ] opens inline form:
  Realm name input, purpose input, [ create realm ] button
  On submit: sends create-realm command via WebSocket.

Role-gated visibility:
  Guardian and operator see the panel.
  User role: panel hidden entirely.
  Update visibility in the status handler from active_user.role.

## Task 2 - admin-surface WebSocket command

Privilege required: all OR invite_users

Returns: {"type": "admin_data", "users": [...], "invites": [...],
"realms": [...], "total_users": N, "total_invites": N, "total_realms": N}

Each user record includes: user_id, display_name, role, assigned_realms,
status, log_count (from UserLog.entry_count).

Each invite record includes: invite_code, role, assigned_realms,
status, created_at.

Each realm record includes: name, purpose, governance_sensitivity,
user_count (users assigned to this realm), memory_count.

## Task 3 - create-realm command

Command: create-realm [name] [purpose]
Privilege: all (Guardian only)

Creates a proposal:
  [REALM PROPOSAL] | Create realm: [name] | status: pending
After approval: RealmManager.create_realm(name, purpose)
Shows: create-realm > Realm [name] created.

Add to STARTUP_COMMANDS and capabilities.

## Task 4 - Admin Surface CSS

New CSS classes:
  .admin-panel, .admin-sub-title
  .admin-user-row, .admin-user-name, .admin-user-role
  .admin-user-realms, .admin-user-status (active=green, suspended=amber)
  .admin-invite-row, .admin-invite-code (monospace)
  .admin-realm-row, .admin-realm-name
  .admin-inline-form with select and input styled to match theme

All action buttons use the existing .panel-btn class.

## Task 5 - Role-gated visibility in JS

updateAdminVisibility(activeUser) function:
  Show admin panel only for role guardian or operator.
  Hide completely for role user or null.
  Called from the status handler on every status message.

## Task 6 - Update identity.py and state.py

CURRENT_PHASE = "Cycle 4 - Phase 4.8 - The Admin Surface"
Add "admin-surface" and "create-realm" to STARTUP_COMMANDS and capabilities.

## Task 7 - Tests

Add to test_commands.py: "admin-surface" and "create-realm" in capabilities.
Update test_identity.py: update CURRENT_PHASE assertion.
Update test_state.py: add new commands.

---

## Permitted file changes

inanna/identity.py, main.py, core/state.py,
ui/server.py, ui/static/index.html,
tests/test_commands.py, tests/test_identity.py, tests/test_state.py

---

## What You Are NOT Building

No user editing via the admin panel (commands only).
No user deletion (suspend only).
No bulk operations.
No realm editing via the admin panel.
No cross-realm admin views for operators.
No email notification on invite creation.
Actions go through existing command/proposal flow.

---

## Definition of Done

- [ ] Admin Surface panel in side panel, role-gated
- [ ] Panel hidden for user role, visible for guardian/operator
- [ ] Users sub-section with role, realms, status
- [ ] Invites sub-section with status
- [ ] Realms sub-section with sensitivity
- [ ] admin-surface command returns admin_data payload
- [ ] create-realm command works via proposal
- [ ] Inline invite form triggers invite flow
- [ ] CURRENT_PHASE updated
- [ ] All tests pass

---

## Handoff

Commit: cycle4-phase8-complete
Report: docs/implementation/CYCLE4_PHASE8_REPORT.md
Stop. Do not begin Phase 4.9 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-20*
*The civic layer becomes visible.*
*Who is here. What they can do. Where they can go.*
*All of it, at a glance, for the Guardian.*
