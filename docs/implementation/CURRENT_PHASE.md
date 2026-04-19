# CURRENT PHASE: Cycle 4 - Phase 4.7 - The Realm Access
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-19**
**Cycle: 4 - The Civic Layer**
**Replaces: Cycle 4 Phase 4.6 - The Governed Invite (COMPLETE)**

Phase 4.6 governs how users arrive. Phase 4.7 governs where they can go.

Every user has assigned_realms in their UserRecord but until now that
field is decorative. Phase 4.7 makes realm access real: session startup
checks the active user against the active realm, warnings are shown if
denied, and Guardian commands let realm assignments be managed.

## Task 1 - can_access_realm() and UserManager helpers in user.py

Add module-level function:
  can_access_realm(user_record, realm_name) -> bool
  Returns True if "all" in assigned_realms or realm_name in assigned_realms.

Add to UserManager:
  assign_realm(user_id, realm_name) -> bool
    Adds realm to assigned_realms, saves to disk. Returns False if already present.

  unassign_realm(user_id, realm_name) -> bool
    Removes realm from assigned_realms. Returns False if only realm or if "all".

## Task 2 - Realm access check at session start

In server.py and main.py after active token is set, check can_access_realm().
If denied: broadcast/print a prominent access warning and continue (no hard block).
Warning format:
  access > Alice does not have access to realm work.
  access > Assigned realms: default.
  access > Start with INANNA_REALM=default or use assign-realm.

## Task 3 - assign-realm command

Command: assign-realm [user_name] [realm_name]
Privilege: all (Guardian only)
Creates proposal: [REALM PROPOSAL] | Assign realm X to Y | status: pending
After approval: user_manager.assign_realm()
Shows: assign-realm > Realm X assigned to Y.

## Task 4 - unassign-realm command

Command: unassign-realm [user_name] [realm_name]
Privilege: all (Guardian only)
Same flow, calls unassign_realm().
If only realm: unassign-realm > Cannot remove last realm for Y.

## Task 5 - realm_access in status payload

Add: "realm_access": true | false

## Task 6 - Realm warning in switch-user

When switching to a user who lacks access to the current realm, show:
  switch-user > Warning: Alice does not have access to realm X.
  switch-user > Operating as Alice in an unassigned realm.
  switch-user > Use assign-realm to grant access.
Switch still proceeds - warning is informational only.

## Task 7 - Update identity.py and state.py

CURRENT_PHASE = "Cycle 4 - Phase 4.7 - The Realm Access"
Add assign-realm and unassign-realm to STARTUP_COMMANDS and capabilities.

## Task 8 - Tests

Add to test_user.py:
- can_access_realm() True for "all", True for assigned, False for unassigned
- assign_realm() adds realm, returns False if already present
- unassign_realm() removes realm, returns False when only realm remains

Update test_identity.py, test_state.py, test_commands.py.

## Permitted file changes

inanna/identity.py, main.py, core/user.py, core/state.py,
ui/server.py, tests/test_user.py, tests/test_identity.py,
tests/test_state.py, tests/test_commands.py.
No changes to index.html.

## What You Are NOT Building

No realm creation via command (Phase 4.8). No hard block on access denial.
No UI panel for realm management. No per-realm governance rules.
Do not change invite or create-user flow.

## Definition of Done

- [ ] can_access_realm() exists in user.py
- [ ] assign_realm() and unassign_realm() exist in UserManager
- [ ] Realm access warning shown at session startup if denied
- [ ] assign-realm and unassign-realm work via proposal
- [ ] Last-realm protection in unassign_realm
- [ ] switch-user shows realm warning when target lacks access
- [ ] realm_access in status payload
- [ ] CURRENT_PHASE updated
- [ ] All tests pass

## Handoff

Commit: cycle4-phase7-complete
Report: docs/implementation/CYCLE4_PHASE7_REPORT.md
Stop. Do not begin Phase 4.8 without new CURRENT_PHASE.md.

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-19*
*A realm is not just a name. It is a boundary.*
*Phase 4.7 makes that boundary real.*
