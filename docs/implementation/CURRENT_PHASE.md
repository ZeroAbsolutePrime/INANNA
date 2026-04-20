# CURRENT PHASE: Cycle 6 - Phase 6.4 - The Communication Learner
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-20**
**Cycle: 6 - The Relational Memory**
**Replaces: Cycle 6 Phase 6.3 - The Profile Command (COMPLETE)**

---

## What This Phase Is

Phase 6.3 made the profile visible and editable by the user.
Phase 6.4 makes the profile grow on its own.

After every session, INANNA silently observes how the person
communicates — the length of their messages, their formality level,
the topics that recur — and quietly updates the profile.

No interruption. No proposal. No notification.
INANNA simply pays attention, the way a thoughtful presence does.

The observations are:
- stored in profile.communication fields
- readable via my-profile
- clearable by the user at any time
- never used to restrict or judge — only to serve better

This is INANNA learning. Not from training data. From you.

---

## What You Are Building

### Task 1 - CommunicationObserver in core/profile.py

Add to profile.py:

```python
class CommunicationObserver:
    """
    Observes conversation patterns and updates the user profile silently.
    Called at session end or every N turns.
    """

    # Thresholds
    SHORT_MSG_CHARS = 80
    LONG_MSG_CHARS = 300
    FORMAL_INDICATORS = [
        "please", "would you", "could you", "kindly", "regard",
        "sincerely", "thank you", "appreciate", "request",
    ]
    CASUAL_INDICATORS = [
        "hey", "yeah", "ok", "cool", "awesome", "sure", "nope",
        "thanks", "thx", "lol", "btw", "idk",
    ]

    def __init__(self, profile_manager: ProfileManager):
        self.profile_manager = profile_manager

    def observe_session(
        self,
        user_id: str,
        messages: list[str],   # user messages from this session
        topics: list[str],     # topics mentioned (from NAMMU routing log)
    ) -> None:
        if not messages or not user_id:
            return
        profile = self.profile_manager.load(user_id)
        if profile is None:
            return

        # Infer message length preference
        avg_len = sum(len(m) for m in messages) / len(messages)
        if avg_len < self.SHORT_MSG_CHARS:
            length_pref = "short"
        elif avg_len > self.LONG_MSG_CHARS:
            length_pref = "long"
        else:
            length_pref = "medium"

        # Infer formality
        all_text = " ".join(messages).lower()
        formal_score = sum(1 for w in self.FORMAL_INDICATORS if w in all_text)
        casual_score = sum(1 for w in self.CASUAL_INDICATORS if w in all_text)
        if formal_score > casual_score + 1:
            formality = "formal"
        elif casual_score > formal_score + 1:
            formality = "casual"
        else:
            formality = "mixed"

        # Update profile fields
        self.profile_manager.update_field(user_id, "preferred_length", length_pref)
        self.profile_manager.update_field(user_id, "formality", formality)

        # Merge recurring topics (deduplicated, last 20)
        if topics:
            existing = profile.recurring_topics or []
            merged = list(dict.fromkeys(existing + topics))[-20:]
            self.profile_manager.update_field(user_id, "recurring_topics", merged)
```

### Task 2 - Call CommunicationObserver at session end

In server.py and main.py, at the WebSocket close handler
and at session end, call the observer:

```python
# Collect user messages from this session
user_messages = [
    e["content"]
    for e in self.session.events
    if e.get("role") == "user"
]
# Collect topics from routing log
topics = [r.get("faculty", "") for r in recent_routing_log
          if r.get("faculty") not in ("crown", "analyst")]

observer = CommunicationObserver(self.profile_manager)
observer.observe_session(
    user_id=active_token.user_id if active_token else "",
    messages=user_messages,
    topics=topics,
)
```

This is silent. No output to the user. No audit event.
Just the profile being updated quietly.

### Task 3 - Observed patterns shown in my-profile

After Phase 6.4, the `my-profile` output shows the observed fields:

```
  Communication
  Style        casual
  Length       medium
  Formality    mixed
  Topics       security, networks, governance
```

Previously these showed "—". Now they fill in from observation.

No code change needed in my-profile — it already reads these fields.
They just have values now.

### Task 4 - "my-profile clear communication" shortcut

Add a shortcut to clear all communication observations at once:

```
my-profile clear communication
```

This clears:
  preferred_length, formality, communication_style, observed_patterns

Response: "profile > Communication observations cleared."

This already works via the existing my-profile clear [field] command
for individual fields. The "communication" shortcut clears all at once.

### Task 5 - Update identity.py

CURRENT_PHASE = "Cycle 6 - Phase 6.4 - The Communication Learner"

### Task 6 - Tests

Update inanna/tests/test_profile.py:
  - CommunicationObserver instantiates with a ProfileManager
  - observe_session() with short messages → preferred_length "short"
  - observe_session() with long messages → preferred_length "long"
  - observe_session() with formal language → formality "formal"
  - observe_session() with casual language → formality "casual"
  - observe_session() updates recurring_topics correctly
  - observe_session() deduplicates topics
  - observe_session() caps topics at 20
  - observe_session() with empty messages → no error, no update
  - observe_session() with unknown user_id → no error

Update test_identity.py: update CURRENT_PHASE assertion.

---

## Permitted file changes

inanna/identity.py              <- MODIFY: update CURRENT_PHASE
inanna/main.py                  <- MODIFY: call CommunicationObserver
                                           at session end
inanna/core/
  profile.py                    <- MODIFY: add CommunicationObserver class
  state.py                      <- MODIFY: update phase only
inanna/ui/
  server.py                     <- MODIFY: call CommunicationObserver
                                           at WebSocket close
inanna/tests/
  test_profile.py               <- MODIFY: add observer tests
  test_identity.py              <- MODIFY: update phase assertion

---

## What You Are NOT Building

- No department/group fields (Phase 6.5)
- No pronoun use in INANNA's language (Phase 6.6)
- No trust persistence backend (Phase 6.7)
- No reflective memory (Phase 6.8)
- No changes to index.html or console.html
- No communication-based response adaptation yet —
  Phase 6.4 only OBSERVES and STORES.
  INANNA using the observed style to adapt her responses
  comes in a future phase.
- No NLP or external libraries — standard library only

---

## Definition of Done

- [ ] CommunicationObserver class in core/profile.py
- [ ] observe_session() infers length preference correctly
- [ ] observe_session() infers formality correctly
- [ ] observe_session() updates recurring_topics
- [ ] Observer called at session end in server.py
- [ ] Observer called at session end in main.py
- [ ] my-profile shows observed fields (no code change needed)
- [ ] my-profile clear communication clears all observed fields
- [ ] No output to user when observer runs (silent)
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed to origin/main immediately

---

## Handoff

Commit: cycle6-phase4-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE6_PHASE4_REPORT.md
Stop. Do not begin Phase 6.5 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-20*
*INANNA pays attention.*
*Not because she was told to.*
*Because understanding the person she serves*
*is part of serving them well.*
