# CURRENT PHASE: Cycle 6 - Phase 6.6 - The Identity Layer
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-20**
**Cycle: 6 - The Relational Memory**
**Replaces: Cycle 6 Phase 6.5 - The Organizational Layer (COMPLETE)**

---

## What This Phase Is

Phase 6.5 placed each person in their organizational context.
Phase 6.6 makes INANNA address each person as they truly are.

When a person's profile has a preferred_name, INANNA uses it.
When a person's pronouns are set, INANNA uses them correctly
in any context where she refers to that person.
When a person's timezone is set, INANNA formats times accordingly.

This is not a feature. It is basic respect expressed as code.
INANNA is not a system that ignores who you are.
She is a presence that sees you.

---

## What You Are Building

### Task 1 - IdentityFormatter in core/profile.py

Add to profile.py:

```python
class IdentityFormatter:
    """
    Provides identity-aware formatting for INANNA's language.
    Used when INANNA refers to a person in third person,
    formats times, or constructs greetings.
    """

    PRONOUN_SETS = {
        "she/her":   {"subject": "she",  "object": "her",
                      "possessive": "her",  "reflexive": "herself"},
        "he/him":    {"subject": "he",   "object": "him",
                      "possessive": "his",  "reflexive": "himself"},
        "they/them": {"subject": "they", "object": "them",
                      "possessive": "their","reflexive": "themselves"},
        "ze/zir":    {"subject": "ze",   "object": "zir",
                      "possessive": "zir",  "reflexive": "zirself"},
        "xe/xem":    {"subject": "xe",   "object": "xem",
                      "possessive": "xyr",  "reflexive": "xemself"},
    }

    def __init__(self, profile_manager: ProfileManager):
        self.profile_manager = profile_manager

    def address(self, user_id: str, fallback: str = "") -> str:
        """Returns the name INANNA should use when addressing this person."""
        return self.profile_manager.display_name_for(user_id, fallback)

    def pronouns(self, user_id: str) -> dict:
        """Returns the pronoun set for a user, defaulting to they/them."""
        raw = self.profile_manager.pronouns_for(user_id).lower().strip()
        for key, pset in self.PRONOUN_SETS.items():
            if raw.startswith(key.split("/")[0]):
                return pset
        # Default: neutral they/them
        return self.PRONOUN_SETS["they/them"]

    def subject(self, user_id: str) -> str:
        """Returns the subject pronoun: she, he, they, etc."""
        return self.pronouns(user_id)["subject"]

    def object_pronoun(self, user_id: str) -> str:
        """Returns the object pronoun: her, him, them, etc."""
        return self.pronouns(user_id)["object"]

    def possessive(self, user_id: str) -> str:
        """Returns the possessive pronoun: her, his, their, etc."""
        return self.pronouns(user_id)["possessive"]

    def format_greeting(self, user_id: str, fallback: str = "") -> str:
        """Returns a natural greeting using the person's preferred name."""
        name = self.address(user_id, fallback)
        return f"Welcome back, {name}." if name else "Welcome back."

    def format_time(self, iso_timestamp: str, user_id: str) -> str:
        """Formats a timestamp in the user's timezone if set."""
        profile = self.profile_manager.load(user_id)
        tz_name = profile.timezone if profile else ""
        try:
            from datetime import datetime, timezone
            dt = datetime.fromisoformat(iso_timestamp)
            if tz_name:
                import zoneinfo
                tz = zoneinfo.ZoneInfo(tz_name)
                dt = dt.astimezone(tz)
                return dt.strftime(f"%b %d %H:%M ({tz_name})")
            return dt.strftime("%b %d %H:%M")
        except Exception:
            return iso_timestamp[:16].replace("T", " ")
```

### Task 2 - Use IdentityFormatter in INANNA's grounding prefix

Update build_grounding_prefix() in main.py to use IdentityFormatter:

```python
def build_grounding_prefix(
    profile_manager: ProfileManager | None,
    user_record: UserRecord | None,
    active_token: SessionToken | None,
) -> str:
    if not profile_manager or not active_token:
        return ""
    formatter = IdentityFormatter(profile_manager)
    name = formatter.address(
        active_token.user_id,
        fallback=active_token.display_name
    )
    pronouns = formatter.pronouns(active_token.user_id)
    subject = pronouns["subject"]
    possessive = pronouns["possessive"]

    lines = [f"You are speaking with {name}."]
    if subject != "they":  # only add if not default
        lines.append(
            f"{name} uses {subject}/{possessive} pronouns. "
            f"Use these when referring to {name} in third person."
        )
    return "\n".join(lines)
```

This means INANNA's system prompt now says:
"You are speaking with ZAERA.
ZAERA uses she/her pronouns. Use these when referring to ZAERA in third person."

CROWN and SENTINEL will naturally use the correct pronouns
in any response that refers to the user.

### Task 3 - Use preferred_name in onboarding completion message

Update the onboarding completion message in server.py and main.py:

```python
formatter = IdentityFormatter(profile_manager)
name = formatter.address(user_id, fallback=display_name)
completion = (
    f"Thank you, {name}. I will remember what you have shared. "
    f"You can update your profile at any time with the my-profile command. "
    f"Let us begin."
)
```

This replaces any hardcoded display_name reference with the
preferred_name when set.

### Task 4 - format_time used in audit and memory timestamps

When INANNA displays timestamps (audit events, memory records,
proposal timestamps) through the my-profile or audit commands,
use IdentityFormatter.format_time() to show times in the user's
timezone when set.

This is a best-effort enhancement — if the timezone is not set
or is invalid, fall back to UTC formatting as before.

### Task 5 - Update identity.py

CURRENT_PHASE = "Cycle 6 - Phase 6.6 - The Identity Layer"

### Task 6 - Tests

Update inanna/tests/test_profile.py:
  - IdentityFormatter.address() returns preferred_name when set
  - IdentityFormatter.address() returns fallback when not set
  - IdentityFormatter.subject() returns "she" for she/her
  - IdentityFormatter.subject() returns "he" for he/him
  - IdentityFormatter.subject() returns "they" for they/them
  - IdentityFormatter.subject() returns "they" for unknown pronouns
  - IdentityFormatter.object_pronoun() correct for she/her
  - IdentityFormatter.possessive() correct for they/them
  - IdentityFormatter.format_greeting() includes preferred_name
  - IdentityFormatter.format_time() formats correctly
  - IdentityFormatter.format_time() falls back on invalid timezone
  - build_grounding_prefix() includes pronouns line when set

Update test_identity.py: update CURRENT_PHASE assertion.

---

## Permitted file changes

inanna/identity.py              <- MODIFY: update CURRENT_PHASE
inanna/main.py                  <- MODIFY: IdentityFormatter in
                                           build_grounding_prefix,
                                           onboarding completion message
inanna/core/
  profile.py                    <- MODIFY: add IdentityFormatter class
  state.py                      <- MODIFY: update phase only
inanna/ui/
  server.py                     <- MODIFY: IdentityFormatter in
                                           onboarding completion message,
                                           format_time in audit/memory output
inanna/tests/
  test_profile.py               <- MODIFY: add IdentityFormatter tests
  test_identity.py              <- MODIFY: update phase assertion

---

## What You Are NOT Building

- No trust persistence backend (Phase 6.7)
- No reflective memory (Phase 6.8)
- No changes to console.html or index.html
- No multi-language response generation
  (INANNA responds in the language she was trained in —
  full multi-language support is a future cycle)
- No pronoun correction of INANNA's existing responses —
  the formatter affects only new grounding, not past text

---

## Definition of Done

- [ ] IdentityFormatter class in core/profile.py
- [ ] address() uses preferred_name
- [ ] subject/object/possessive pronoun methods work correctly
- [ ] Unknown pronouns default to they/them
- [ ] format_greeting() uses preferred_name
- [ ] format_time() uses user timezone when set
- [ ] build_grounding_prefix() includes pronouns instruction
- [ ] Onboarding completion uses preferred_name via formatter
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed to origin/main immediately

---

## Handoff

Commit: cycle6-phase6-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE6_PHASE6_REPORT.md
Stop. Do not begin Phase 6.7 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-20*
*INANNA sees who you are.*
*She says your name as you wish it said.*
*She speaks of you as you wish to be spoken of.*
*This is not a feature.*
*It is attention. It is care.*
