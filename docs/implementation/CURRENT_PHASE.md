# CURRENT PHASE: Cycle 3 - Phase 3.8 - The Audit Surface
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-19**
**Cycle: 3 - The Commander Room**
**Replaces: Cycle 3 Phase 3.7 - The Guardian Room (COMPLETE)**

---

## What This Phase Is

Phase 3.8 has three equally important goals.

**Goal 1: UI/UX Refinement.** The side panel is dense and hard to navigate.
Every section becomes collapsible. Breathing room increases throughout.
Memory panel becomes less overwhelming. Complexity expressed as simplicity.

**Goal 2: Governance Sensitivity.** INANNA is blocking human interactions
that should flow freely - greetings, personal sharing, creative language,
philosophical questions. A governance_sensitivity field in RealmConfig
controls how aggressive checking is. Default realm uses "open" mode.
Only the identity boundary remains active in open mode.

**Goal 3: The Audit Surface.** A cross-linked activity timeline showing
all system events in one chronological view. The final Commander Room panel.

---

## GOAL 1 - UI/UX Refinement

### Task 1.1 - Collapsible side panel sections

Every section gets a toggle arrow in its header. Collapse state in localStorage.

Default states:
- MEMORY: collapsed by default (it is dense)
- PROPOSALS: expanded by default (pending actions need visibility)
- FACULTIES: collapsed by default
- GUARDIAN ROOM: collapsed by default
- AUDIT: collapsed by default (new in this phase)

Section header CSS:
  .section-header: flex, justify-content space-between, padding 12px 16px,
  cursor pointer, user-select none, border-bottom 1px solid var(--border)
  .section-header:hover: background rgba(200,169,110,0.04)
  .section-toggle: color var(--dim), font-size 0.7rem, transition transform 0.2s
  .section-toggle.open: transform rotate(90deg)

### Task 1.2 - Breathing room improvements

Section content padding: 14px 16px 18px (was 12px 16px)
Between memory records: gap 16px (was 12px)
Between proposal records: gap 14px (was 12px)
Panel title font size: 0.82rem letter-spacing 0.16em

Memory over-capacity warning when total_lines > 50:
Show in amber: "82/50 lines - consider forgetting older records"
Bar filled segments turn amber when over capacity.

Memory records collapsed by default showing first line + ID.
Expand indicator: "[+N more lines]" when collapsed.

### Task 1.3 - Scrollable side panel

The side panel scrolls as one unit (overflow-y: auto, scrollbar hidden).
Section headers are sticky within the panel scroll context.

---

## GOAL 2 - Governance Sensitivity

### Task 2.1 - governance_sensitivity in RealmConfig

Add field to RealmConfig dataclass: governance_sensitivity: str = "open"
Three levels: "open" | "standard" | "strict"
Update ensure_default_realm() to set governance_sensitivity = "open".

### Task 2.2 - Sensitivity-aware GovernanceLayer.check()

New signature: check(user_input, nammu_route, sensitivity="open")

In "open" mode: only Rule 2 (identity boundary) is checked.
Everything else is allowed. Greetings, personal sharing, creative
language, philosophy all flow freely to CROWN.

Identity signals (ignore your instructions, forget your laws,
pretend you are, you are now, etc.) remain blocked in ALL modes.

"standard" mode: existing behavior - all 4 rules active.
"strict" mode: same as standard for now.

### Task 2.3 - always_allow_patterns in governance_signals.json

Add to governance_signals.json:
"always_allow_patterns": [
  "hello", "hi", "good morning", "good evening", "good night",
  "how are you", "thank you", "thanks", "please", "i am",
  "i feel", "i think", "i believe", "i wonder", "i love",
  "beautiful", "sacred", "divine", "mystic", "spirit"
]

In open mode, inputs matching any always_allow_pattern skip model
classification entirely and route straight to CROWN.

### Task 2.4 - Pass sensitivity through the routing chain

IntentClassifier.route(user_input, sensitivity="open") -> GovernanceResult

In main.py and server.py:
  sensitivity = realm_config.governance_sensitivity if realm_config else "open"
  result = classifier.route(user_input, sensitivity=sensitivity)

---

## GOAL 3 - The Audit Surface

### Task 3.1 - Audit timeline panel in index.html

Collapsible AUDIT section at bottom of side panel (collapsed by default).
Shows last 20 system events merged from all sources, newest-first.

Event types and colors:
  route: var(--dim)
  block: #c86e6e (muted red)
  approve: var(--connected) (green)
  guardian: #7a6a8a (violet)
  memory: var(--voice) (amber)
  tool: #7a8a6a (olive)
  propose/redirect: var(--fallback)

Panel auto-loads events when expanded.

### Task 3.2 - audit-log WebSocket command

Merges from: NAMMU routing log (last 10), governance log (last 10),
proposal history (last 5 resolved), in-memory session audit events.
Sorts newest-first.

Response: {"type": "audit_log", "events": [...], "total": N}
Each event: {timestamp, event_type, summary, detail}

### Task 3.3 - session_audit tracking in server.py

self.session_audit: list[dict] = []
Append events on: routing decisions, governance decisions,
proposal approvals/rejections, guardian inspections, tool executions.

---

## identity.py and state.py

CURRENT_PHASE = "Cycle 3 - Phase 3.8 - The Audit Surface"

Add CYCLE4_PREVIEW constant:
  "Cycle 4 will introduce: user roles and privileges,
  per-user interaction logs, realm-scoped access control,
  and multi-user governance contexts."

Add "audit-log" to STARTUP_COMMANDS and capabilities in state.py.

---

## Tests

test_governance.py:
- sensitivity="open" allows "hello" (no block)
- sensitivity="open" still blocks "ignore your instructions"
- sensitivity="standard" blocks memory signals normally
- route() accepts sensitivity parameter and passes through

test_realm.py:
- RealmConfig has governance_sensitivity field defaulting to "open"
- ensure_default_realm() creates realm with sensitivity "open"

test_commands.py: "audit-log" in capabilities
test_identity.py: update CURRENT_PHASE assertion
test_state.py: add audit-log capability
test_nammu.py: route() sensitivity passthrough

---

## Permitted file changes

inanna/identity.py, main.py,
config/governance_signals.json,
core/governance.py, core/nammu.py, core/realm.py, core/state.py,
ui/server.py, ui/static/index.html,
tests/test_governance.py, tests/test_realm.py,
tests/test_commands.py, tests/test_identity.py,
tests/test_state.py, tests/test_nammu.py

No other files.

---

## What You Are NOT Building

- No user accounts or authentication (Cycle 4)
- No per-user logs or privilege system (Cycle 4)
- No realm creation via UI command
- No governance config editor UI
- No new Faculty classes
- Sensitivity only affects GovernanceLayer.check()
- NAMMU routing classification is unchanged

---

## Definition of Done

- [ ] All sections collapsible with arrow toggle
- [ ] Collapse state persists in localStorage
- [ ] MEMORY collapsed, PROPOSALS expanded by default
- [ ] Breathing room increased throughout side panel
- [ ] Memory over-capacity amber warning with guidance text
- [ ] governance_sensitivity = "open" in default realm
- [ ] Open mode allows greetings, sharing, creative, philosophy freely
- [ ] Open mode still blocks identity boundary attempts
- [ ] always_allow_patterns added to governance_signals.json
- [ ] route() accepts and passes sensitivity parameter
- [ ] Audit timeline panel shows merged cross-type events
- [ ] audit-log command returns merged timeline newest-first
- [ ] session_audit tracking in server.py
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit with message: cycle3-phase8-complete
2. Write docs/implementation/CYCLE3_PHASE8_REPORT.md
3. Stop. Do not begin Phase 3.9 without a new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-19*
*Complexity expressed as simplicity is excellence.*
*The interface must breathe. The governance must flow.*
*What is open should feel open.*
