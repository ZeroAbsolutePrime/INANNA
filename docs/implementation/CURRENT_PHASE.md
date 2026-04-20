# CURRENT PHASE: Cycle 6 - Phase 6.3 - The Profile Command
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-20**
**Cycle: 6 - The Relational Memory**
**Replaces: Cycle 6 Phase 6.2 - The Onboarding Survey (COMPLETE)**

---

## What This Phase Is

Phase 6.1 created the profile infrastructure.
Phase 6.2 filled it through the onboarding conversation.
Phase 6.3 makes the profile visible and editable.

After this phase, any user can type `my-profile` and see
their profile rendered beautifully in the conversation —
not as raw JSON, but as a warm, human-readable portrait.

They can update any field with `my-profile edit [field] [value]`.
They can clear sensitive fields with `my-profile clear [field]`.
The Guardian can view any user's profile with `view-profile [name]`.

This is Law IV expressed at the user level:
you should be able to ask what INANNA knows about you
and receive a clear, honest, readable answer.

---

## What You Are Building

### Task 1 - "my-profile" command

Add command: my-profile

Privilege required: converse (any logged-in user)

Output format (rendered as a "profile" message type in the UI):

```
Your profile

  Name         ZAERA
  Preferred    ZAERA
  Pronouns     she/her
  Languages    es, en, pt
  Location     Barcelona, Catalonia, Spain

  Organization
  Departments  —
  Groups       —

  Communication
  Style        —
  Formality    —
  Patterns     —

  Interests
  Domains      —
  Topics       —
  Projects     —

  Trust
  Session      —
  Persistent   —

  Onboarding   completed Apr 19 22:15

Type "my-profile edit [field] [value]" to update any field.
Type "my-profile clear [field]" to remove a field.
```

Empty fields show "—". Missing sections are shown but empty.
The output is a single "system" message with clean formatting.

### Task 2 - "my-profile edit [field] [value]" command

Allows the user to update any profile field directly.

```
my-profile edit preferred_name Zohar
my-profile edit pronouns they/them
my-profile edit location_city Lisboa
my-profile edit location_country Portugal
my-profile edit languages en,es,pt
```

For list fields (languages, departments, groups, domains):
  The value is split on commas: "en,es,pt" → ["en", "es", "pt"]

Privileged fields (readable/writable only by Guardian):
  inanna_notes — Guardian can add notes about a user
  (normal users cannot edit this field)

After updating, the profile grounding is refreshed:
  sync_profile_grounding(engine, profile_manager, user, token)

Response: "profile > [field] updated to [value]."

### Task 3 - "my-profile clear [field]" command

Clears a field back to its default (empty string or empty list).

```
my-profile clear pronouns
my-profile clear location_city
my-profile clear domains
```

Response: "profile > [field] cleared."

Protected fields (cannot be cleared):
  user_id, version, created_at, onboarding_completed

Response for protected fields:
  "profile > [field] cannot be cleared."

### Task 4 - "view-profile [display_name]" command

Privilege required: all (Guardian only)

Shows another user's full profile in the same format as my-profile,
prefixed with:
  "Profile for Alice (user_abc12345):"

If user not found:
  "view-profile > No user found: [name]"

### Task 5 - "profile" message type in index.html

Add a distinct profile message type for profile display:

```css
.msg-row.profile .msg-bubble {
    background: rgba(200, 150, 42, .05);
    border: 1px solid var(--gold1);
    border-left: 2px solid var(--gold3);
    font-family: var(--mono);
    font-size: 12px;
    line-height: 2;
    color: var(--ivory);
    white-space: pre-wrap;
}
.msg-row.profile .msg-label {
    color: var(--gold2);
}
```

The label: "profile"

In handleMsg():
```javascript
if (t === 'profile') { addMessage('profile', m.text); return; }
```

Server broadcasts profile output as:
  {"type": "profile", "text": "...formatted profile..."}

### Task 6 - Add "my-profile" and "view-profile" to capabilities

Update identity.py:
  CURRENT_PHASE = "Cycle 6 - Phase 6.3 - The Profile Command"

Update state.py: add my-profile, view-profile to STARTUP_COMMANDS.

### Task 7 - Tests

Update inanna/tests/test_profile.py:
  - format_profile_output() formats correctly for complete profile
  - format_profile_output() shows "—" for empty fields
  - parse_profile_edit_command() extracts field and value correctly
  - parse_profile_edit_command() handles list values (comma-split)
  - Protected fields cannot be cleared

Update test_identity.py: update CURRENT_PHASE assertion.
Update test_state.py: add my-profile, view-profile.
Update test_commands.py: add my-profile, view-profile.

---

## Permitted file changes

inanna/identity.py              <- MODIFY: update CURRENT_PHASE
inanna/main.py                  <- MODIFY: my-profile command,
                                           my-profile edit command,
                                           my-profile clear command,
                                           view-profile command
inanna/core/
  state.py                      <- MODIFY: add commands
inanna/ui/
  server.py                     <- MODIFY: same commands,
                                           broadcast as "profile" type
  static/index.html             <- MODIFY: profile message type CSS + handler
inanna/tests/
  test_profile.py               <- MODIFY: add format/parse tests
  test_identity.py              <- MODIFY: update phase assertion
  test_state.py                 <- MODIFY: add new commands
  test_commands.py              <- MODIFY: add new commands

---

## What You Are NOT Building

- No communication learning (Phase 6.4)
- No department/group management (Phase 6.5)
- No pronoun use in INANNA's language (Phase 6.6)
- No trust persistence backend (Phase 6.7)
- No reflective memory (Phase 6.8)
- No changes to console.html
- No profile export or download

---

## Definition of Done

- [ ] "my-profile" shows full profile as "profile" message type
- [ ] "my-profile edit [field] [value]" updates and refreshes grounding
- [ ] "my-profile clear [field]" clears non-protected fields
- [ ] "view-profile [name]" works for Guardian only
- [ ] profile message type renders distinctly in index.html
- [ ] List fields split on commas correctly
- [ ] Protected fields cannot be cleared
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed to origin/main immediately

---

## Handoff

Commit: cycle6-phase3-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE6_PHASE3_REPORT.md
Stop. Do not begin Phase 6.4 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-20*
*INANNA knows who you are.*
*Now you can see what she knows.*
*And you can correct her.*
*That is the difference between a profile and a dossier.*
