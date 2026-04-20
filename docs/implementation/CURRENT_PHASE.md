# CURRENT PHASE: Cycle 6 - Phase 6.1 - The User Profile
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-20**
**Cycle: 6 - The Relational Memory**
**Master plan: docs/cycle6_master_plan.md**
**Prerequisite: Cycle 5 complete — verify_cycle5.py passed 90 checks**

---

## What This Phase Is

Cycle 5 proved that INANNA knows what she can do.
Cycle 6 teaches her to know who she serves.

Phase 6.1 is the foundation: the UserProfile.

Every person who interacts with INANNA gains a profile —
a living document that begins empty and deepens with every session.
It holds their preferred name, their pronouns, their organizational
context, their communication style, their interests, their trust patterns.

The profile is theirs. They can read it. They can edit it. They can
delete it. INANNA uses it silently to serve them better.
Law IV governs: readable system truth.

---

## What You Are Building

### Task 1 - inanna/core/profile.py

Create: inanna/core/profile.py

```python
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timezone
import json

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

@dataclass
class UserProfile:
    user_id: str
    version: str = "1.0"
    created_at: str = field(default_factory=utc_now)
    last_updated: str = field(default_factory=utc_now)

    # Identity
    preferred_name: str = ""
    pronouns: str = ""
    gender: str = ""
    sex: str = ""
    languages: list[str] = field(default_factory=list)
    timezone: str = ""
    location_city: str = ""
    location_region: str = ""
    location_country: str = ""

    # Organizational
    departments: list[str] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)
    notification_scope: str = "realm"  # "all" | "realm" | "none"

    # Communication (observed by INANNA)
    communication_style: str = ""
    preferred_length: str = ""
    formality: str = ""
    observed_patterns: list[str] = field(default_factory=list)

    # Interests (observed by INANNA)
    domains: list[str] = field(default_factory=list)
    recurring_topics: list[str] = field(default_factory=list)
    named_projects: list[str] = field(default_factory=list)

    # Trust patterns
    session_trusted_tools: list[str] = field(default_factory=list)
    persistent_trusted_tools: list[str] = field(default_factory=list)

    # Onboarding
    onboarding_completed: bool = False
    onboarding_completed_at: str = ""
    survey_responses: dict = field(default_factory=dict)

    # INANNA's observations (proposal-governed)
    inanna_notes: list[str] = field(default_factory=list)


class ProfileManager:
    def __init__(self, profiles_dir: Path):
        self.profiles_dir = profiles_dir
        profiles_dir.mkdir(parents=True, exist_ok=True)

    def _profile_path(self, user_id: str) -> Path:
        return self.profiles_dir / f"{user_id}.json"

    def ensure_profile_exists(self, user_id: str) -> UserProfile:
        if self._profile_path(user_id).exists():
            return self.load(user_id)
        profile = UserProfile(user_id=user_id)
        self.save(profile)
        return profile

    def load(self, user_id: str) -> UserProfile | None:
        path = self._profile_path(user_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            # Remove unknown keys for forward compatibility
            known = {f.name for f in UserProfile.__dataclass_fields__.values()}
            filtered = {k: v for k, v in data.items() if k in known}
            return UserProfile(**filtered)
        except Exception:
            return UserProfile(user_id=user_id)

    def save(self, profile: UserProfile) -> None:
        profile.last_updated = utc_now()
        data = {
            k: getattr(profile, k)
            for k in profile.__dataclass_fields__
        }
        self._profile_path(profile.user_id).write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def update_field(self, user_id: str, field_name: str, value) -> bool:
        profile = self.load(user_id)
        if profile is None:
            profile = UserProfile(user_id=user_id)
        if not hasattr(profile, field_name):
            return False
        setattr(profile, field_name, value)
        self.save(profile)
        return True

    def delete(self, user_id: str) -> bool:
        path = self._profile_path(user_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_profiles(self) -> list[UserProfile]:
        profiles = []
        for path in self.profiles_dir.glob("*.json"):
            p = self.load(path.stem)
            if p:
                profiles.append(p)
        return profiles

    def display_name_for(self, user_id: str, fallback: str = "") -> str:
        profile = self.load(user_id)
        if profile and profile.preferred_name:
            return profile.preferred_name
        return fallback

    def pronouns_for(self, user_id: str) -> str:
        profile = self.load(user_id)
        if profile:
            return profile.pronouns
        return ""
```

### Task 2 - Instantiate ProfileManager in server.py and main.py

Add to server.py __init__ and main.py startup:

```python
from core.profile import ProfileManager

PROFILES_DIR = DATA_ROOT / "profiles"
self.profile_manager = ProfileManager(PROFILES_DIR)
```

When a user logs in or a session starts, call:
```python
self.profile_manager.ensure_profile_exists(active_token.user_id)
```

This creates an empty profile silently on first login.
No output. No proposal. Just the foundation being laid.

### Task 3 - Use preferred_name in grounding

In the grounding text sent to CROWN and SENTINEL,
if the active user has a preferred_name set, use it:

```python
preferred = profile_manager.display_name_for(
    active_token.user_id,
    fallback=active_token.display_name
)
grounding_prefix = f"You are speaking with {preferred}."
```

This is the first moment INANNA uses the profile to personalize.
It is subtle and silent — CROWN simply knows the person's name.

### Task 4 - "profile-status" in status payload

Add to the status payload:
```json
"profile": {
    "exists": true,
    "preferred_name": "ZAERA",
    "onboarding_completed": false,
    "departments": [],
    "pronouns": ""
}
```

This lets the UI know whether to show the onboarding prompt
in a future phase.

### Task 5 - Update identity.py and state.py

CURRENT_PHASE = "Cycle 6 - Phase 6.1 - The User Profile"

Add "profile-status" awareness (no new command yet —
it is part of the status payload, not a standalone command).

### Task 6 - Tests

Create inanna/tests/test_profile.py:
  - UserProfile can be instantiated with user_id only
  - All fields have correct defaults
  - ProfileManager.ensure_profile_exists() creates profile file
  - ProfileManager.load() returns UserProfile for existing profile
  - ProfileManager.load() returns None for missing profile
  - ProfileManager.save() writes JSON to disk
  - ProfileManager.update_field() updates a string field
  - ProfileManager.update_field() updates a list field
  - ProfileManager.update_field() returns False for unknown field
  - ProfileManager.delete() removes profile file
  - ProfileManager.list_profiles() returns all profiles
  - ProfileManager.display_name_for() returns preferred_name if set
  - ProfileManager.display_name_for() returns fallback if not set
  - ProfileManager.pronouns_for() returns pronouns if set
  - ProfileManager.pronouns_for() returns empty string if not set
  - Profile JSON is valid after save/load round-trip

Update test_identity.py: update CURRENT_PHASE assertion.

---

## Permitted file changes

inanna/identity.py              <- MODIFY: update CURRENT_PHASE
inanna/main.py                  <- MODIFY: instantiate ProfileManager,
                                           ensure_profile on login,
                                           preferred_name in grounding,
                                           profile in status payload
inanna/config/
  (no config changes)
inanna/core/
  profile.py                    <- NEW
  state.py                      <- MODIFY: update phase only
inanna/ui/
  server.py                     <- MODIFY: instantiate ProfileManager,
                                           ensure_profile on login,
                                           preferred_name in grounding,
                                           profile in status payload
inanna/tests/
  test_profile.py               <- NEW
  test_identity.py              <- MODIFY: update phase assertion

---

## What You Are NOT Building

- No onboarding survey (Phase 6.2)
- No profile commands (Phase 6.3)
- No communication learning (Phase 6.4)
- No departments/groups UI (Phase 6.5)
- No pronoun use in INANNA's language (Phase 6.6)
- No trust persistence (Phase 6.7)
- No reflective memory (Phase 6.8)
- No changes to console.html or index.html

---

## Definition of Done

- [ ] core/profile.py exists with UserProfile and ProfileManager
- [ ] ProfileManager.ensure_profile_exists() creates profiles silently
- [ ] ProfileManager wired into server.py and main.py
- [ ] Empty profile created on user login
- [ ] preferred_name used in grounding when set
- [ ] profile section in status payload
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed to origin/main immediately

---

## Handoff

Commit: cycle6-phase1-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE6_PHASE1_REPORT.md
Stop. Do not begin Phase 6.2 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-20*
*The first profile is created.*
*Empty. Waiting.*
*INANNA meets someone for the first time.*
*She does not yet know who they are.*
*But she is ready to learn.*
