# CURRENT PHASE: Cycle 6 - Phase 6.5 - The Organizational Layer
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-20**
**Cycle: 6 - The Relational Memory**
**Replaces: Cycle 6 Phase 6.4 - The Communication Learner (COMPLETE)**

---

## What This Phase Is

Phases 6.1-6.4 gave each person a profile that knows who they are
and how they communicate.

Phase 6.5 places each person in context.

People do not exist in isolation. They belong to departments,
to groups, to teams. When something happens in the engineering realm,
the engineers should know. When a ceremony update arrives,
the facilitators should receive it. Not everyone. The right ones.

This phase builds the organizational layer of the profile:
departments, groups, and the first notification routing capability.

---

## What You Are Building

### Task 1 - Department and group management commands

Add commands:
  assign-department [user] [department]   (Guardian only)
  unassign-department [user] [department] (Guardian only)
  assign-group [user] [group]             (Guardian only)
  unassign-group [user] [group]           (Guardian only)

Each command updates the user's profile:
  profile_manager.update_field(user_id, 'departments',
      list(set(profile.departments + [dept])))
  profile_manager.update_field(user_id, 'groups',
      list(set(profile.groups + [group])))

Response format:
  "org > Alice assigned to department: engineering"
  "org > Alice removed from department: engineering"
  "org > Alice assigned to group: facilitators"
  "org > Alice removed from group: facilitators"

No proposal required — department/group assignment is a lightweight
organizational operation, governed by the privilege check (Guardian only).

### Task 2 - "my-departments" command (any user)

Shows the active user's departments and groups:

```
Your organizational context:

  Departments  engineering, research
  Groups       core-team

Type "assign-department [dept]" to request assignment (Guardian approves).
```

Any user can see their own context.
Privilege required: converse.

### Task 3 - "notify-department [dept] [message]" command

Privilege required: all (Guardian only)

Sends a notification message to all users in a department.
The notification appears as a "system" message in the conversation
the next time those users open a session.

Implementation:
  1. Find all users whose profile.departments includes [dept]
  2. Write a notification record to:
     inanna/data/notifications/{user_id}.json
     (a list of pending notifications)
  3. When a user logs in, check for pending notifications and
     broadcast them as system messages

Notification record format:
```json
{
  "notification_id": "notif-xxxx",
  "from": "guardian",
  "department": "engineering",
  "message": "...",
  "created_at": "ISO",
  "delivered": false
}
```

### Task 4 - NotificationStore in core/profile.py

Add to profile.py:

```python
class NotificationStore:
    def __init__(self, notifications_dir: Path):
        self.notifications_dir = notifications_dir
        notifications_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, user_id: str) -> Path:
        return self.notifications_dir / f"{user_id}.json"

    def add(self, user_id: str, notification: dict) -> None:
        existing = self.load_pending(user_id)
        existing.append(notification)
        self._path(user_id).write_text(
            json.dumps(existing, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def load_pending(self, user_id: str) -> list[dict]:
        path = self._path(user_id)
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def mark_delivered(self, user_id: str, notification_id: str) -> None:
        notifications = self.load_pending(user_id)
        for n in notifications:
            if n.get("notification_id") == notification_id:
                n["delivered"] = True
        self._path(user_id).write_text(
            json.dumps(notifications, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def clear_delivered(self, user_id: str) -> int:
        notifications = self.load_pending(user_id)
        pending = [n for n in notifications if not n.get("delivered")]
        cleared = len(notifications) - len(pending)
        self._path(user_id).write_text(
            json.dumps(pending, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        return cleared
```

### Task 5 - Deliver notifications on login

In server.py and main.py, after user login:
  1. Load pending notifications for the user
  2. Broadcast each undelivered notification as a system message:
     "📢 [dept notification] [message]"
  3. Mark each as delivered

This means the next time a notified user opens their session,
they see the notification before their first input.

### Task 6 - Departments visible in Admin Surface

Update the admin-surface command response to include
department and group information per user:

```json
{
  "users": [
    {
      "display_name": "Alice",
      "role": "user",
      "departments": ["engineering"],
      "groups": ["core-team"],
      ...
    }
  ]
}
```

### Task 7 - my-profile shows departments and groups

The existing my-profile command already reads these fields.
After Phase 6.5, the output shows:

```
  Organization
  Departments  engineering, research
  Groups       core-team
  Scope        realm
```

No code change needed — the fields are already in UserProfile
and already rendered by my-profile. They just have values now.

### Task 8 - Update identity.py and state.py

CURRENT_PHASE = "Cycle 6 - Phase 6.5 - The Organizational Layer"
Add new commands to STARTUP_COMMANDS and capabilities:
  assign-department, unassign-department,
  assign-group, unassign-group,
  my-departments, notify-department

### Task 9 - Tests

Update inanna/tests/test_profile.py:
  - NotificationStore.add() adds a notification
  - NotificationStore.load_pending() returns pending notifications
  - NotificationStore.mark_delivered() marks correctly
  - NotificationStore.clear_delivered() removes delivered
  - Department assignment updates profile correctly
  - Group assignment updates profile correctly
  - Duplicate department assignment is idempotent
  - Unassign from missing department returns gracefully

Update test_identity.py: update CURRENT_PHASE assertion.
Update test_state.py: add new commands.
Update test_commands.py: add new commands.

---

## Permitted file changes

inanna/identity.py              <- MODIFY: update CURRENT_PHASE
inanna/main.py                  <- MODIFY: assign/unassign dept/group,
                                           my-departments,
                                           notify-department,
                                           deliver notifications on login
inanna/core/
  profile.py                    <- MODIFY: add NotificationStore
  state.py                      <- MODIFY: add new commands
inanna/ui/
  server.py                     <- MODIFY: same commands,
                                           deliver notifications on login,
                                           departments in admin payload
inanna/tests/
  test_profile.py               <- MODIFY: add notification + org tests
  test_identity.py              <- MODIFY: update phase assertion
  test_state.py                 <- MODIFY: add new commands
  test_commands.py              <- MODIFY: add new commands

---

## What You Are NOT Building

- No pronoun use in INANNA's language (Phase 6.6)
- No trust persistence backend (Phase 6.7)
- No reflective memory (Phase 6.8)
- No changes to console.html or index.html
- No cross-realm notification routing (future)
- No notification UI panel (future)
- Notifications are text-only, no attachments

---

## Definition of Done

- [ ] NotificationStore class in core/profile.py
- [ ] assign-department / unassign-department commands work
- [ ] assign-group / unassign-group commands work
- [ ] my-departments command shows context
- [ ] notify-department writes notifications for all dept members
- [ ] Notifications delivered as system messages on login
- [ ] Departments and groups in admin-surface payload
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed to origin/main immediately

---

## Handoff

Commit: cycle6-phase5-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE6_PHASE5_REPORT.md
Stop. Do not begin Phase 6.6 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-20*
*People belong to each other.*
*Departments are not bureaucracy.*
*They are the shape of care —*
*who should know when something matters.*
