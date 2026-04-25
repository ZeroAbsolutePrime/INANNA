# INNER ORGAN · PROFILE
## The Mirror — User Preferences, Personalization, and Identity

**Ring: Inner AI Organs**
**Grade: B- (basic and functional, deeper layers missing)**
**Version: 1.0 · Date: 2026-04-24**

---

## Identity

**What it is:**
PROFILE is the mirror organ of INANNA NYX.
It holds what the system knows about the operator —
their preferences, communication style, role, and context —
so the system can serve them as a singular person, not a generic user.

**What it does:**
- Stores operator preferences (language, style, length, formality)
- Holds the NAMMU operator profile (shorthands, corrections, domain weights)
- Provides personalization context to CROWN and NAMMU
- Manages the onboarding process for new operators
- Tracks trusted tools and persistent permissions

**What it must never do:**
- Become a behavioral dossier built without consent
- Share one operator's profile with another
- Store information the operator has not approved
- Be used for manipulation or hidden optimization

**The name:**
PROFILE is a mirror — it reflects the person back to the system
so the system can serve them more precisely.
A mirror shows truly. It does not distort or enhance.

---

## Ring

**Inner AI Organs** — PROFILE is the personalization layer.
It sits between the human covenant and the intelligence organs,
ensuring that all organs operate with knowledge of who they serve.

---

## Correspondences

| Component | Location |
|---|---|
| UserProfile class | `core/profile.py` → `UserProfile` |
| NAMMU operator profile | `core/nammu_profile.py` → `OperatorProfile` |
| User data storage | `data/users/{user_id}.json` |
| NAMMU profile storage | `data/realms/default/nammu/operator_profiles/{user_id}.json` |
| Profile commands | `ui/server.py` → `my-profile`, `my-profile edit` |
| Profile formatting | `core/profile.py` → `format_profile_output()` |
| Profile enrichment | `ui/server.py` → startup context |

**Called by:** Session startup, CROWN context building, NAMMU enrichment
**Calls:** Storage layer (JSON files)
**Reads:** User profile JSON, NAMMU operator profile JSON
**Writes:** User profile JSON, NAMMU operator profile JSON

---

## Mission

PROFILE exists because generic service is poor service.

An operator who prefers short answers should not receive essays.
An operator who writes in Catalan should not receive English responses.
An operator who has taught NAMMU "mtx = Matxalen" should never
need to explain it again.

PROFILE holds this knowledge — not to model the operator for extraction,
but to serve them with increasing precision over time.

The distinction that governs everything:
**PROFILE exists to serve the operator, not to profile them.**

---

## Current State

### What Works

**UserProfile fields (stored in data/users/):**
- `preferred_name`: how to address the operator
- `pronouns`: for respectful address
- `languages`: primary languages
- `communication_style`: direct/indirect/etc.
- `preferred_length`: short/medium/long
- `formality`: formal/warm/casual
- `domains`: areas of focus
- `recurring_topics`: what they often discuss
- `named_projects`: active projects

**Profile commands:**
- `my-profile`: display current profile
- `my-profile edit [field] [value]`: update a field
- `my-profile clear [field]`: remove a field

**NAMMU operator profile (actively used):**
- Shorthand lexicon (mtx = Matxalen)
- Language patterns
- Domain weights
- Correction history
- Grows with every session

### What Is Limited

- Most UserProfile fields are empty for INANNA NAMMU
- Onboarding process does not fully populate the profile
- CROWN does not yet adapt tone based on detected language

### What Is Missing

- Accessibility needs (screen reader, font size preferences, etc.)
- Emotional rhythm tracking (morning vs evening style differences)
- Explicit consent boundaries in the profile
- Profile completeness indicator and guided completion
- Role-specific profile sections (guardian vs operator vs user)

---

## Desired Function

A complete PROFILE organ would:
- Adapt CROWN's tone dynamically when NAMMU detects language switch
- Track emotional rhythm and adjust response depth accordingly
- Hold explicit consent boundaries ("never summarize calendar for third parties")
- Provide profile completeness suggestions during onboarding
- Support accessibility configuration (response format, verbosity, etc.)

---

## Evaluation

**Grade: B-**

PROFILE exists and works. The NAMMU operator profile is the
most active part — it grows with every session and genuinely
improves NAMMU's accuracy over time.

The UserProfile fields are mostly defined but empty.
They were designed carefully but the onboarding process
does not guide operators to fill them.

Single most important gap:
**CROWN does not use the profile to adapt its voice.**

The profile says "preferred_length: short" but CROWN
still generates long responses when the model wants to.
The profile needs to be enforced in the CROWN instruction.

Priority: enforce `preferred_length` and `formality` in
CROWN_INSTRUCTIONS on every turn.

---

*Organ Card version 1.0 · 2026-04-24*
