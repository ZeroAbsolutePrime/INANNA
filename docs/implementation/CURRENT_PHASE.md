# CURRENT PHASE: Cycle 4 - Phase 4.9 - The Civic Proof
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-20**
**Cycle: 4 - The Civic Layer**
**Replaces: Cycle 4 Phase 4.8 - The Admin Surface (COMPLETE)**

---

## What This Phase Is

Eight phases built the Civic Layer:
4.1 User Identity, 4.2 Access Gate, 4.3 Privilege Map,
4.4 User Memory, 4.5 User Log, 4.6 Governed Invite,
4.7 Realm Access, 4.8 Admin Surface.

Phase 4.9 is the completion phase.

Its purpose: verify everything works as a coherent whole,
write verify_cycle4.py with 30+ integration checks,
write the Cycle 4 Completion Record,
update the Code Doctrine with Lessons from Cycle 4,
and declare Cycle 4 complete.

Build almost nothing. Verify everything. Document honestly.

---

## What You Are Building

### Task 1 - inanna/verify_cycle4.py

Create a standalone verification script.
Run with: py -3 verify_cycle4.py
No live model or browser required.

The script verifies:

1. ROLES CONFIG
   - config/roles.json exists with 3 roles
   - Role privileges are not hardcoded in Python
   - guardian has "all" privilege
   - operator has "invite_users" privilege
   - user has "converse" and "approve_own_memory"

2. USER IDENTITY
   - UserRecord dataclass has all required fields
   - UserManager can be instantiated
   - ensure_guardian_exists() creates ZAERA on first call
   - ensure_guardian_exists() returns existing on repeat call
   - create_user() stores user to disk as JSON
   - get_user() returns correct UserRecord
   - list_users() returns all users
   - has_privilege() correct for all three roles
   - can_access_realm() correct for assigned and unassigned realms
   - assign_realm() and unassign_realm() work correctly

3. INVITE FLOW
   - InviteRecord dataclass exists
   - create_invite() generates INANNA-XXXX-XXXX format codes
   - accept_invite() creates user and marks invite accepted
   - Double-accept returns None
   - Expired invite returns None from accept_invite()
   - list_invites() filters by status correctly

4. SESSION TOKEN
   - SessionToken dataclass exists with all fields
   - TokenStore.issue() returns a SessionToken
   - TokenStore.validate() returns token for valid string
   - TokenStore.validate() returns None for unknown token
   - TokenStore.validate() returns None for revoked token
   - TokenStore.revoke() deactivates the token
   - One active token per user (issue revokes previous)

5. PRIVILEGE MAP
   - check_privilege() returns (False, reason) for no session
   - check_privilege() returns (True, "") for guardian + any priv
   - check_privilege() returns (True, "") for user + "converse"
   - check_privilege() returns (False, reason) for user + "all"

6. USER MEMORY
   - Memory.write_memory() accepts user_id parameter
   - Memory record stores user_id in JSON
   - load_memory_records(user_id=x) filters correctly
   - Different users see only their own records

7. USER LOG
   - UserLog can be instantiated
   - append() creates log file
   - load() returns correct entries
   - entry_count() correct
   - clear() removes entries and returns count
   - Two users have separate log files

8. REALM ACCESS
   - can_access_realm() True for "all"
   - can_access_realm() True for assigned realm
   - can_access_realm() False for unassigned realm
   - assign_realm() adds realm correctly
   - unassign_realm() protects last realm

9. FACULTY MONITOR
   - FacultyMonitor has 4 records
   - update_model_mode() updates crown and analyst
   - record_call() increments call_count
   - format_report() contains all 4 Faculty names

10. CAPABILITIES
    - All Cycle 4 commands in capabilities:
      login, logout, whoami, users, create-user,
      invite, join, invites, my-log, user-log,
      assign-realm, unassign-realm, switch-user,
      admin-surface, create-realm,
      guardian-clear-events, guardian-dismiss

11. IDENTITY
    - CURRENT_PHASE is "Cycle 4 - Phase 4.9 - The Civic Proof"
    - CYCLE4_PREVIEW constant exists (user roles preview)

12. CYCLE 2 AND 3 REGRESSION
    - py -3 verify_cycle2.py still passes
    - py -3 verify_cycle3.py still passes
    - (Run both and report results)

Format: same as verify_cycle2.py and verify_cycle3.py
[PASS] / [FAIL] per check, exit 0 if all pass.
Target: 35+ checks.

### Task 2 - Fix any integration gaps found

If verify_cycle4.py finds any failing check, fix it
before writing the completion record.
Document every gap found and fixed in the phase report.

### Task 3 - docs/cycle4_completion.md

Create the Cycle 4 Completion Record containing:

- What Cycle 4 set out to build (from cycle4_master_plan.md)
- What was actually built — one paragraph per phase
- The data loss incident: honest account of what happened when
  git reset --hard origin/main wiped the completion commits,
  what was recovered, and what remained thinner after recovery
  (test count dropped from 216 to 166)
- What verify_cycle4.py confirmed
- What Cycle 4 did not build (honest):
  - No email delivery
  - No realm editing via UI
  - No hard block on realm access denial (warning only)
  - No bulk operations
  - Test coverage thinner than pre-loss due to recovery
- The bridge to Cycle 5

### Task 4 - docs/code_doctrine.md update

Add section: "Lessons from Cycle 4"

Must include:

1. PUSH IMMEDIATELY. Every completion commit must be pushed to
   origin/main the moment Codex delivers it. A commit that exists
   only on Codex local machine does not exist. The repo is the
   source of truth. This is not optional. This is law.
   Cycle 4 lost 6 phases of completion commits because they were
   never pushed. The recovery cost a full session and left the
   test suite thinner than before.

2. Config-driven means config-driven. User roles, privileges,
   invite codes, realm names — none of these belong in Python.
   They belong in JSON. Cycle 4 held this rule.
   Future cycles must hold it too.

3. The civic layer is the foundation of the platform.
   Users, roles, invites, logs — these are not features.
   They are the substrate on which every future capability rests.
   Cycle 5 (Operator Console) cannot be built safely without
   the privilege checks Cycle 4 established.

4. Warning before enforcement. Realm access in Phase 4.7 was
   warning-only, not a hard block. This was the right choice.
   Show the person what the system sees before restricting them.
   Hard enforcement comes after the admin surface makes the rules
   visible and editable.

5. The Admin Surface is the governance interface.
   ZAERA should never need to type a command to know who is in
   the system. The Admin panel makes civic state readable at a
   glance. Every future expansion of the civic layer needs a
   corresponding surface in the Admin panel.

### Task 5 - Update identity.py

CURRENT_PHASE = "Cycle 4 - Phase 4.9 - The Civic Proof"

Add CYCLE4_SUMMARY:
```python
CYCLE4_SUMMARY = (
    "Cycle 4 built the Civic Layer: user identity with config-driven "
    "roles and privileges, session tokens, user-scoped memory, "
    "interaction logs, governed invite flow, realm access control, "
    "and the Admin Surface giving the Guardian a full civic overview."
)
```

### Task 6 - Final verification runs

Run: py -3 -m unittest discover -s tests
Run: py -3 verify_cycle2.py
Run: py -3 verify_cycle3.py
Run: py -3 verify_cycle4.py
All must pass. Report all counts in the phase report.

---

## Permitted file changes

inanna/identity.py          <- MODIFY: CURRENT_PHASE, CYCLE4_SUMMARY
inanna/verify_cycle4.py     <- NEW
docs/cycle4_completion.md   <- NEW
docs/code_doctrine.md       <- MODIFY: add Lessons from Cycle 4
tests/test_identity.py      <- MODIFY: update phase assertion
Core/UI files only if fixing gaps found by verify_cycle4.py.

---

## What You Are NOT Building

No new capabilities. No new commands. No new panels.
Verify and document only.
Do not begin Cycle 5 work.

---

## Definition of Done

- [ ] verify_cycle4.py exists and all 35+ checks pass
- [ ] py -3 verify_cycle2.py still passes (regression)
- [ ] py -3 verify_cycle3.py still passes (regression)
- [ ] py -3 -m unittest discover -s tests passes
- [ ] docs/cycle4_completion.md with honest account of data loss
- [ ] docs/code_doctrine.md has Lessons from Cycle 4
- [ ] CURRENT_PHASE updated to Phase 4.9
- [ ] CYCLE4_SUMMARY in identity.py
- [ ] Any gaps found are fixed and documented

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit with message: cycle4-phase9-complete
2. PUSH TO ORIGIN/MAIN IMMEDIATELY.
3. Write docs/implementation/CYCLE4_PHASE9_REPORT.md containing:
   - verify_cycle4.py results (all checks)
   - verify_cycle2.py result (regression)
   - verify_cycle3.py result (regression)
   - Final unittest count
   - Any gaps found and fixed
4. Stop. Cycle 4 is complete.
   Do not begin Cycle 5 without authorization from Command Center.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-20*
*Eight phases of building. One phase of truth.*
*The civic layer proves itself.*
