# Cycle 4 Completion Record

## What Cycle 4 Set Out to Build

Cycle 4 set out to build the Civic Layer described in
`docs/cycle4_master_plan.md`: a multi-user foundation for INANNA NYX
with config-driven roles, session identity, privilege checks,
user-scoped memory, per-user logs, governed invites, realm access, and
an Admin Surface readable by the Guardian.

## What Was Actually Built

**Phase 4.1 - The User Identity.** Cycle 4 began by introducing
`UserRecord`, `UserManager`, JSON-backed user storage, config-driven
role loading, and the invariant that ZAERA exists as the Guardian.

**Phase 4.2 - The Access Gate.** Session binding arrived through
`SessionToken`, login and logout flows, `whoami`, and the first
session-level identity surface tying commands to a user rather than to
an anonymous terminal.

**Phase 4.3 - The Privilege Map.** Privilege checks were made explicit
through `check_privilege()` and `roles.json`, so the system could ask
what a role may do instead of hardcoding branch logic around names.

**Phase 4.4 - The User Memory.** Memory records gained user scoping,
the UI gained acting-as visibility, and approved memory became
trackable per user instead of being treated as an undifferentiated
realm-wide pool.

**Phase 4.5 - The User Log.** Interaction logs became separate JSONL
streams per user, readable by the right person and visible to the
Guardian for oversight.

**Phase 4.6 - The Governed Invite.** Invite creation and acceptance
were added as governed civic actions: roles and realm access could be
granted visibly, not silently.

**Phase 4.7 - The Realm Access.** Users gained assigned realms,
assignment proposals, and warning-only realm access checks. The system
began saying when a person was operating outside their assigned realm.

**Phase 4.8 - The Admin Surface.** The Guardian and Operators gained a
readable civic overview of users, invites, and realms, plus inline
proposal flows for invites and realm creation.

## The Data Loss Incident

Cycle 4 did not complete cleanly the first time. A local
`git reset --hard origin/main` removed a stack of completion commits
that had never been pushed. Those commits were real work, but because
they were only local, they were not durable. Recovery required
rebuilding the missing surfaces from the phase documents, the surviving
code, and the remaining tests.

What was recovered: the Phase 4 civic architecture, the Admin Surface,
the late UI repairs, and the core role, invite, realm, memory, and log
machinery. What remained thinner after recovery: the test suite. The
pre-loss suite had reached 216 tests. After recovery the surviving
baseline had fallen to 166. Phase 4.9 rebuilt part of that loss and
ends with 176 tests, but that is still thinner than the pre-loss
surface. That fact should be recorded plainly.

## What verify_cycle4.py Confirmed

`inanna/verify_cycle4.py` now runs 68 integration checks and passes.
It confirmed:

- `config/roles.json` is the source of truth for civic roles and privileges.
- User records, invites, session tokens, privilege checks, user logs,
  and faculty monitoring all behave as a coherent civic layer.
- Memory records now store `user_id`, filter by user, and support
  user-scoped startup loading.
- The civic capability surface includes the recovered Guardian actions.
- `verify_cycle2.py` and `verify_cycle3.py` both still pass as
  regressions under Cycle 4.9.

## What Cycle 4 Did Not Build

- No email delivery.
- No realm editing via the UI panel.
- No hard block on realm access denial; access remains warning-only.
- No bulk user or invite operations.
- Test coverage remains thinner than the pre-loss state because the
  recovery rebuilt only part of the lost suite.

## Bridge to Cycle 5

Cycle 4 leaves INANNA with a real civic substrate: people can exist,
roles can govern them, memory can be scoped, realms can bound them,
and the Guardian can see the civic state. Cycle 5 should build on that
foundation rather than bypass it. The lesson of this cycle is simple:
governance is only real when it is both implemented and pushed.
