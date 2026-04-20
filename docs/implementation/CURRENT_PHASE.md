# CURRENT PHASE: Cycle 6 - Phase 6.2 - The Onboarding Survey
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-20**
**Cycle: 6 - The Relational Memory**
**Replaces: Cycle 6 Phase 6.1 - The User Profile (COMPLETE)**

---

## What This Phase Is

Phase 6.1 created the profile — an empty vessel waiting to be filled.
Phase 6.2 is the first filling: the onboarding survey.

The first time an operator opens a session with INANNA,
she notices they have not yet been welcomed properly.
She pauses the normal conversation flow and asks five questions —
gently, conversationally, as though meeting someone for the first time.

Not a form. A meeting.

After the survey completes (or is skipped), it never repeats.
The answers live in the profile. INANNA uses them silently
to address the person as they wish to be addressed.

This phase also implements the first active use of the profile:
INANNA greets the user by their preferred_name after onboarding
and uses their pronouns correctly in the conversation.

---

## What You Are Building

### Task 1 - Onboarding detection in server.py and main.py

After the active session starts (user logged in, profile loaded),
check if onboarding is needed:

```python
def needs_onboarding(profile: UserProfile | None) -> bool:
    if profile is None:
        return False
    return not profile.onboarding_completed
```

If onboarding is needed, inject a special system message into
the conversation BEFORE the user's first input reaches CROWN:

```
{"type": "onboarding", "text": "...survey intro message..."}
```

This triggers the onboarding flow in the UI.

### Task 2 - Onboarding state machine in server.py

The onboarding survey is a 5-step conversational flow.
Track state in the server session:

```python
self.onboarding_active = False
self.onboarding_step = 0
self.onboarding_responses = {}
```

The five questions (asked one at a time, in order):

Step 1: "What would you like me to call you?"
  Field: preferred_name
  Skip phrase: "skip" | "no preference" | empty

Step 2: "What pronouns do you use? For example: she/her, he/him,
  they/them — or skip this if you prefer."
  Field: pronouns
  Skip phrase: "skip" | "prefer not" | empty

Step 3: "What brings you here? What are you working on?"
  Field: survey_responses["purpose"]
  Skip phrase: "skip"

Step 4: "Are there domains or topics you would like me to be
  especially thoughtful about?"
  Field: survey_responses["sensitive_domains"]
  Skip phrase: "skip" | "none"

Step 5: "Is there anything else you would like me to know
  about you that would help me serve you well?"
  Field: survey_responses["additional"]
  Skip phrase: "skip" | "nothing" | "no"

After Step 5 (or after the user types "skip all"):
  - Save all collected responses to the profile
  - Set profile.onboarding_completed = True
  - Set profile.onboarding_completed_at = utc_now()
  - Broadcast a warm completion message:
    "Thank you, [preferred_name or display_name]. I will remember
     what you have shared. You can update your profile at any time
     with the my-profile command. Let us begin."
  - Resume normal conversation flow

### Task 3 - Onboarding message interception

While onboarding_active is True, incoming user messages are
treated as survey responses, not conversation inputs.
They are NOT sent to NAMMU or CROWN.

The response to each survey answer is the next question.

If the user types "skip all" at any point:
  Complete onboarding immediately with whatever was collected.
  Mark as completed.

### Task 4 - "onboarding" message type in index.html

Add a distinct onboarding message type to the UI:

```css
.msg-row.onboarding .msg-bubble {
    background: rgba(120, 72, 176, .08);
    border: 1px solid rgba(120, 72, 176, .3);
    border-left: 3px solid var(--vio3);
    font-family: var(--serif);
    font-size: 14px;
    line-height: 2;
    color: var(--rose5);
}
.msg-row.onboarding .msg-label {
    color: var(--vio3);
    font-family: var(--serif);
}
```

The label text: "inanna ∴"

Onboarding messages feel like INANNA speaking warmly —
rose/pink text, violet border, Cinzel font.
Distinct from normal conversation but unmistakably INANNA.

### Task 5 - Onboarding skip button in UI

When an onboarding message arrives, optionally show
a subtle [ skip survey ] button beneath it:

```html
<div class="onboarding-skip">
  <button onclick="sendSkipOnboarding()">[ skip survey ]</button>
</div>
```

```javascript
function sendSkipOnboarding() {
  if (ws && ws.readyState === 1) {
    ws.send(JSON.stringify({type: 'input', text: 'skip all'}));
  }
}
```

This appears only for the first onboarding message,
not for each question.

### Task 6 - Profile update after onboarding

After onboarding completes, the profile is updated:

```python
if response_step1:
    profile_manager.update_field(user_id, 'preferred_name', response_step1)
if response_step2:
    profile_manager.update_field(user_id, 'pronouns', response_step2)
# survey_responses dict stored as JSON
profile_manager.update_field(user_id, 'survey_responses', collected)
profile_manager.update_field(user_id, 'onboarding_completed', True)
profile_manager.update_field(user_id, 'onboarding_completed_at', utc_now())
```

Immediately after saving, INANNA's grounding is refreshed
to include the new preferred_name:

```python
sync_profile_grounding(engine, profile_manager, active_user, active_token)
```

### Task 7 - INANNA uses preferred_name in completion message

The onboarding completion message uses the name the user provided:

```python
name = profile_manager.display_name_for(user_id, fallback=display_name)
completion_msg = (
    f"Thank you, {name}. I will remember what you have shared. "
    f"You can update your profile at any time with the my-profile command. "
    f"Let us begin."
)
```

### Task 8 - Update identity.py and state.py

CURRENT_PHASE = "Cycle 6 - Phase 6.2 - The Onboarding Survey"

### Task 9 - Tests

Update inanna/tests/test_profile.py:
  - needs_onboarding() returns True for incomplete profile
  - needs_onboarding() returns False for completed profile
  - needs_onboarding() returns False for None profile

Update test_identity.py: update CURRENT_PHASE assertion.

No new test file needed — onboarding logic is integration-level
and is tested via the existing profile tests + manual verification.

---

## Permitted file changes

inanna/identity.py              <- MODIFY: update CURRENT_PHASE
inanna/main.py                  <- MODIFY: onboarding detection,
                                           onboarding state machine,
                                           profile update on complete
inanna/ui/
  server.py                     <- MODIFY: onboarding detection,
                                           message interception,
                                           state machine,
                                           profile update on complete
  static/index.html             <- MODIFY: onboarding message type CSS,
                                           onboarding label,
                                           skip survey button
inanna/core/
  state.py                      <- MODIFY: update phase only
inanna/tests/
  test_profile.py               <- MODIFY: add needs_onboarding tests
  test_identity.py              <- MODIFY: update phase assertion

---

## What You Are NOT Building

- No profile commands (Phase 6.3)
- No communication learning (Phase 6.4)
- No department/group fields (Phase 6.5)
- No pronoun use in third-person language (Phase 6.6)
- Do not change console.html
- The Guardian (ZAERA) is NOT shown the onboarding survey —
  only new non-guardian users see it on first login.
  Guardian profile is created in Phase 6.1 but marked completed
  to skip the survey (Guardian configured the system).

---

## Definition of Done

- [ ] needs_onboarding() function exists and works correctly
- [ ] Onboarding detected on first login for non-guardian users
- [ ] Guardian profile marked onboarding_completed on creation
- [ ] Survey proceeds through 5 steps conversationally
- [ ] "skip all" exits survey immediately
- [ ] Profile updated with collected responses after survey
- [ ] preferred_name used in completion message
- [ ] grounding refreshed after onboarding completes
- [ ] Onboarding message type renders distinctly in index.html
- [ ] Skip survey button appears on first onboarding message
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed to origin/main immediately

---

## Handoff

Commit: cycle6-phase2-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE6_PHASE2_REPORT.md
Stop. Do not begin Phase 6.3 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-20*
*INANNA meets someone for the first time.*
*She asks who they are.*
*She listens.*
*She remembers.*
*Not because she was told to.*
*Because she cares.*
