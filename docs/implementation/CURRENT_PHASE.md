# CURRENT PHASE: Cycle 4 - Phase 4.1 - The User Identity
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-19**
**Cycle: 4 - The Civic Layer**
**Prerequisite: Cycle 3 complete - verify_cycle3.py passed 46 checks**

---

## What This Phase Is

INANNA has served one person until now: the Guardian.
One session. One realm. One memory store. One voice.

Phase 4.1 introduces the foundation of the Civic Layer:
user records with roles, a user manager, and the config
file that defines what each role can do.

No login yet. No session binding yet. No access control yet.
Those come in Phases 4.2 and 4.3.

Phase 4.1 is purely: the data model, the manager, the config,
and the Guardian command to create and list users.
This is the identity foundation everything else will build on.

---

## What You Are Building

### Task 1 - inanna/config/roles.json

Create: inanna/config/roles.json

This is the single source of truth for roles and privileges.
Python code NEVER hardcodes role names or privilege lists.

Content:
{
  "roles": {
    "guardian": {
      "description": "Full system access - assigned directly only",
      "privileges": ["all"]
    },
    "operator": {
      "description": "Realm-scoped admin",
      "privileges": [
        "manage_users_in_realm",
        "approve_proposals_in_realm",
        "read_realm_audit_log",
        "invite_users"
      ]
    },
    "user": {
      "description": "Standard interaction",
      "privileges": [
        "converse",
        "approve_own_memory",
        "read_own_log",
        "forget_own_memory"
      ]
    }
  }
}

### Task 2 - inanna/core/user.py

Create: inanna/core/user.py

Two classes: UserRecord (dataclass) and UserManager.

UserRecord fields:
  user_id: str          (generated: "user_" + 8 hex chars)
  display_name: str
  role: str             ("guardian" | "operator" | "user")
  assigned_realms: list[str]  (realm names this user can access)
  created_at: str       (ISO timestamp)
  created_by: str       (user_id of creator, or "system")
  status: str           ("active" | "suspended")

UserManager:
  __init__(data_root: Path, roles_config_path: Path)
  - users_dir = data_root / "users"
  - loads roles.json at init

  Methods:
  create_user(display_name, role, assigned_realms, created_by) -> UserRecord
  get_user(user_id) -> UserRecord | None
  list_users() -> list[UserRecord]
  list_users_by_realm(realm) -> list[UserRecord]
  suspend_user(user_id) -> bool
  activate_user(user_id) -> bool
  has_privilege(user_id, privilege) -> bool
  get_role_privileges(role) -> list[str]

has_privilege() logic:
  - Load user record
  - Get role from record
  - Load role privileges from roles.json
  - If role privileges contains "all": return True
  - Return privilege in role privileges

All user records stored as JSON:
  inanna/data/users/{user_id}.json

ensure_guardian_exists(): called at startup.
  If no user with role "guardian" exists, create one:
  display_name="ZAERA", role="guardian",
  assigned_realms=["all"], created_by="system"
  Print: "Guardian user created: {user_id}"

### Task 3 - The "users" command

Add "users" command to main.py and server.py.

Output:
Users (N total):
  [guardian]  ZAERA           active   realms: all
  [operator]  ThyArcanum      active   realms: default, arcanum
  [user]      Alice            active   realms: default

Only accessible by users with "all" privilege (guardian).
For now in CLI and UI, no auth check yet — that is Phase 4.2.
Show a note: "(access control active in Phase 4.2)"

### Task 4 - The "create-user" command

Add "create-user [display_name] [role] [realm]" command.

This is a GOVERNED action — it creates a proposal:
[USER PROPOSAL] | Create user: {name} with role {role} | status: pending

After approval, UserManager.create_user() is called.
Print: "User created: {display_name} ({user_id}) role: {role}"

Only guardian can create users with operator or guardian role.
For Phase 4.1 no auth check — proposal is the gate.

### Task 5 - Update identity.py and state.py

CURRENT_PHASE = "Cycle 4 - Phase 4.1 - The User Identity"

Add "users" and "create-user" to STARTUP_COMMANDS and capabilities.

### Task 6 - Tests

Create inanna/tests/test_user.py:
  - UserRecord can be instantiated with required fields
  - UserManager can be instantiated with temp directory
  - create_user() creates a JSON file in users_dir
  - get_user() returns correct UserRecord
  - list_users() returns all users
  - has_privilege("all") returns True for guardian role
  - has_privilege("converse") returns True for user role
  - has_privilege("manage_users_in_realm") returns False for user role
  - suspend_user() changes status to "suspended"
  - ensure_guardian_exists() creates guardian if none exists
  - ensure_guardian_exists() does not duplicate if already exists

Update test_identity.py: update CURRENT_PHASE assertion.
Update test_state.py and test_commands.py: add users, create-user.

---

## Permitted file changes

inanna/identity.py              <- MODIFY: update CURRENT_PHASE
inanna/config/roles.json        <- NEW: role and privilege definitions
inanna/main.py                  <- MODIFY: users and create-user commands,
                                           instantiate UserManager,
                                           ensure_guardian_exists()
inanna/core/
  user.py                       <- NEW: UserRecord, UserManager
  state.py                      <- MODIFY: add users, create-user
inanna/ui/
  server.py                     <- MODIFY: users command,
                                           create-user command,
                                           UserManager instantiation
  static/index.html             <- no changes (Phase 4.2 adds UI)
inanna/tests/
  test_user.py                  <- NEW
  test_identity.py              <- MODIFY: update phase assertion
  test_state.py                 <- MODIFY: add capabilities
  test_commands.py              <- MODIFY: add capabilities

---

## What You Are NOT Building

- No login or session token (Phase 4.2)
- No access control enforcement (Phase 4.3)
- No per-user memory scoping (Phase 4.4)
- No per-user interaction log (Phase 4.5)
- No UI user management panel (Phase 4.8)
- No password or OAuth
- No email or external identity
- Do not hardcode role names or privilege lists in Python

---

## Definition of Done for Phase 4.1

- [ ] inanna/config/roles.json exists with 3 roles and privilege lists
- [ ] inanna/core/user.py exists with UserRecord and UserManager
- [ ] UserManager reads privileges from roles.json (not hardcoded)
- [ ] has_privilege() works correctly for all three roles
- [ ] ensure_guardian_exists() creates ZAERA on first startup
- [ ] "users" command lists all users in CLI and UI
- [ ] "create-user" command creates user via proposal flow
- [ ] User records persisted as JSON in data/users/
- [ ] CURRENT_PHASE updated to Phase 4.1
- [ ] All tests pass: py -3 -m unittest discover -s tests

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit with message: cycle4-phase1-complete
2. Write docs/implementation/CYCLE4_PHASE1_REPORT.md
3. Stop. Do not begin Phase 4.2 without a new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-19*
*The civic layer begins with a name.*
*Before roles, before permissions, before access:*
*a person must exist in the system.*
*Phase 4.1 gives them existence.*
