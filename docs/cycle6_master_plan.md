# Cycle 6 Master Plan — The Relational Memory
**The platform learns who it serves**
*Written by: Claude (Command Center)*
*Confirmed by: ZAERA (Guardian)*
*Date: 2026-04-20*
*Prerequisite: Cycle 5 complete — verify_cycle5.py passed 90 checks*

---

## What Cycle 6 Builds

Cycles 1-5 built the governed intelligence and its operational surface.
INANNA can think, route, govern, remember, operate tools,
monitor processes, and orchestrate multiple Faculties.

Cycle 6 builds the layer that makes INANNA a companion, not just a tool.

**The Relational Memory** — INANNA learns who she is speaking with.
Not by surveillance, but by genuine understanding.
Each person has a profile that deepens with every interaction.
INANNA addresses people by their chosen name and pronouns.
She knows which department they belong to, what interests them,
how they prefer to communicate, what they trust and what they hesitate on.

When a new person arrives, INANNA meets them properly —
a gentle onboarding conversation that asks who they are
and what they need, so she can serve them well from the first exchange.

When something happens in a department's realm, the right people
are notified. Not everyone. The right ones.

This is the foundation of INANNA as a platform for communities,
not just a personal assistant for one person.

---

## The Nine Phases of Cycle 6

| Phase | Name | What it builds |
|---|---|---|
| 6.1 | The User Profile | UserProfile dataclass, profile.json storage, CRUD |
| 6.2 | The Onboarding Survey | First-session conversation-style survey |
| 6.3 | The Profile Command | my-profile, view-profile, edit-profile commands |
| 6.4 | The Communication Learner | INANNA observes style, updates profile silently |
| 6.5 | The Organizational Layer | Departments, groups, notification scope |
| 6.6 | The Identity Layer | Pronouns, preferred name, location in INANNA's language |
| 6.7 | The Trust Persistence | session-trust → persistent-trust for governance patterns |
| 6.8 | The Reflective Memory | INANNA self-observation, proposal-governed self-knowledge |
| 6.9 | The Relational Proof | verify_cycle6.py, Cycle 6 Completion Record |

---

## Phase 6.1 — The User Profile

**What it builds:**
- `UserProfile` dataclass in `core/profile.py`
- Profile stored at `inanna/data/profiles/{user_id}.json`
- `ProfileManager` class with create, read, update, delete
- `ensure_profile_exists()` — creates empty profile on first use
- Profile fields (all optional, grow over time):
  identity: preferred_name, pronouns, gender, sex, languages, timezone, location
  organizational: departments, groups, notification_scope
  communication: style, preferred_length, formality, observed_patterns
  interests: domains, recurring_topics, named_projects
  trust_patterns: session_trusted_tools, persistent_trusted_tools
  onboarding: completed, completed_at, survey_responses
  inanna_notes: [] (INANNA's observations, proposal-governed)

Full schema: see docs/memory_architecture.md

---

## Phase 6.2 — The Onboarding Survey

**What it builds:**
The first time an operator opens a session, INANNA asks five questions
in conversational style — not as a form, as a meeting.

Questions:
1. What would you like me to call you?
2. What pronouns do you use?
3. What brings you here — what are you working on?
4. Are there domains you'd like me to be especially thoughtful about?
5. Is there anything you'd like me to know that would help me serve you well?

Each answer is stored in profile.onboarding.survey_responses.
After the survey: profile.onboarding.completed = true.
The survey never repeats. It can be revisited via my-profile.

---

## Phase 6.3 — The Profile Command

**What it builds:**
- `my-profile` — show your own profile
- `my-profile edit [field] [value]` — update a field
- `view-profile [user]` — Guardian sees any user's profile
- Profile displayed beautifully in the conversation, not as raw JSON

---

## Phase 6.4 — The Communication Learner

**What it builds:**
After every session, INANNA observes:
- Message length preference (short/medium/long)
- Formality level (casual/professional/mixed)
- Language patterns (technical/poetic/direct)
- Recurring topics (what comes up again and again)

Observations stored silently in profile.communication and
profile.interests. No proposal needed — these are observations,
not stored memories. The user can clear them via my-profile.

---

## Phase 6.5 — The Organizational Layer

**What it builds:**
- `departments` field in UserProfile — which departments the user belongs to
- `groups` field — which groups (e.g. "core-team", "facilitators")
- Notification routing: when a realm event occurs, notify users
  whose departments/groups match the realm's notification scope
- `notify-department [dept] [message]` command (Guardian only)
- Departments visible in Admin Surface

---

## Phase 6.6 — The Identity Layer

**What it builds:**
INANNA uses profile data in her language:
- Addresses users by preferred_name (not display_name) when set
- Uses correct pronouns when referring to a user in third person
- Formats times in the user's timezone when set
- Responds in the user's preferred language when set
  (requires multi-language system prompt — future work)

The identity fields:
- pronouns: stored, used silently, never displayed without consent
- preferred_name: used in INANNA's greetings and references
- location: used for location-aware responses

---

## Phase 6.7 — The Trust Persistence

**What it builds:**
The organic governance suggestion (already in the UI) gains a backend:
When a Guardian approves a tool N times and confirms "yes, trust this",
the tool is added to profile.trust_patterns.persistent_trusted_tools.

Persistent trusted tools bypass the proposal governance for that user.
The Guardian can revoke trust via `my-profile edit trust remove [tool]`.
This is the governance pattern ZAERA named: seeking the flow.

---

## Phase 6.8 — The Reflective Memory

**What it builds:**
INANNA can propose additions to her own self-knowledge.
When she notices a pattern in herself — a tendency, a strength,
a moment of misalignment corrected — she proposes:
"I notice [observation]. Shall I add this to my self-knowledge?"

Stored at: inanna/data/self/reflection.jsonl
Proposal-governed. Guardian approves or declines.
Readable via: `inanna-reflection` command (Guardian only).

---

## Phase 6.9 — The Relational Proof

verify_cycle6.py with 40+ checks covering all 8 phases.
Cycle 6 Completion Record.
Code Doctrine: Lessons from Cycle 6.

---

## The Evolutionary Contract (from memory_architecture.md)

Every new platform dimension added in future cycles
must extend the UserProfile schema.

Examples already named:
- Add "projects" feature → profile.organizational.projects
- Add "availability" feature → profile.organizational.availability
- Add "specializations" → profile.interests.specializations

The contract is alive. The profile grows with the platform.

---

## Current Position

```
Stage 4  [COMPLETE]  Cycle 4 — The Civic Layer
Stage 4  [COMPLETE]  Cycle 5 — The Operator Console
Stage 5  [ACTIVE]    Cycle 6 — The Relational Memory  ← here
Stage 5  [HORIZON]   Cycle 7 — INANNA NYXOS
```

We are here: beginning Cycle 6, Phase 6.1.

---

*Written by: Claude (Command Center)*
*Confirmed by: ZAERA (Guardian)*
*Date: 2026-04-20*
*The platform knows what it can do.*
*Now it begins to know who it serves.*
