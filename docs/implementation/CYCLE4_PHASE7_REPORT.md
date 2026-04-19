# Cycle 4 Phase 4.7 Report - The Realm Access

## Scope Completed

Phase 4.7 is implemented in the current repo state.

Delivered:
- `inanna/core/user.py` with `UserRecord`, `UserManager`, `can_access_realm()`,
  `check_privilege()`, `ensure_guardian_exists()`, `assign_realm()`,
  and `unassign_realm()`
- `inanna/config/roles.json` as the config-driven role source required by the
  user manager
- warning-only realm access checks in CLI and WebSocket startup/session state
- proposal-governed `assign-realm` and `unassign-realm` command flow
- `realm_access` plus active-user context in the UI status payload
- `switch-user` realm warning behavior
- updated phase and capability surfaces in `identity.py` and `state.py`
- tests covering user realm access helpers and command flow

## Important Repo-State Note

After resetting to `origin/main`, the active Phase 4.7 document was present,
but the earlier Cycle 4 source files it depends on were not tracked in the
checked-out tree. The Phase 4.7 work therefore included the minimum
doc-aligned prerequisite repair needed to make realm access implementable:
`roles.json`, `core/user.py`, and active-user wiring in `main.py` and
`ui/server.py`.

This repair stayed inside the Cycle 4 civic-layer direction and was limited to
the foundations Phase 4.7 explicitly assumes already exist.

## Verification

Primary verification run:
- `py -3 -m unittest discover -s tests`
- Result: `Ran 125 tests in 8.149s`
- Status: `OK`

Additional verification:
- `git diff --check`
- Status: passed

## Outcome

Realm access is now real in the runtime:
- the active user is tracked
- access is evaluated against assigned realms
- denial is warning-only, not a hard block
- Guardian can govern realm assignment through proposals
- switching into a user who lacks the current realm emits the required warning

No Phase 4.8 work was started.
