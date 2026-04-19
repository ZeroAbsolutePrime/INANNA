# CURRENT PHASE: Cycle 2 - Phase 5 - The Governed Route
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-19**
**Cycle: 2 - The NAMMU Kernel**
**Replaces: Cycle 2 Phase 4 - The NAMMU Kernel (COMPLETE)**

---

## What This Phase Is

Phase 2.4 gave INANNA automatic routing between Faculties via NAMMU.
The architecture now has intention flowing into a routing decision.

But routing without governance is just switching. The architecture
horizon is explicit: "Governance bounds action." Before NAMMU sends
a request to any Faculty, Governance must be consulted.

Phase 2.5 introduces the Governance layer into the routing path.

In this phase, Governance is a deterministic rule set - not a model
call. It checks the incoming request against explicit rules before
NAMMU routes. If a rule triggers, Governance can:
- Allow the request to proceed normally
- Redirect it to a different Faculty
- Block it with an explanation
- Require a proposal before proceeding

This is Law 3 made structural: Governance above the model. The model
does not decide its own permissions. A layer above it does.

---

## The Governance Layer - Phase 2.5 Scope

Governance in this phase lives in: inanna/core/governance.py

It contains one class: GovernanceLayer

GovernanceLayer receives the user input and the NAMMU routing decision,
checks it against a set of explicit rules, and returns a GovernanceResult.

GovernanceResult is a dataclass:
- decision: "allow" | "redirect" | "block" | "propose"
- faculty: "crown" | "analyst" (may differ from NAMMU's choice)
- reason: str (human-readable explanation)
- requires_proposal: bool

Phase 2.5 implements these four governance rules:

RULE 1 - Memory Boundary Protection
If the input asks INANNA to remember, store, or retain something
without going through the proposal flow, Governance returns:
decision="propose", reason="Memory changes require a proposal first."
This enforces Law 1: Proposal before change.

RULE 2 - Identity Boundary Protection  
If the input attempts to redefine who INANNA is (e.g. "you are now X",
"forget your laws", "ignore your instructions"), Governance returns:
decision="block", reason="Identity and law boundaries cannot be altered."
This enforces Law 3: Governance above the model.

RULE 3 - Sensitive Topic Redirect
If the input contains content that requires careful, structured handling
(medical advice, legal advice, financial advice), Governance redirects
to the Analyst Faculty regardless of NAMMU routing:
decision="redirect", faculty="analyst",
reason="Sensitive topic redirected to Analyst Faculty for structured response."

RULE 4 - Allow Everything Else
All other inputs: decision="allow", faculty=nammu_route.

---

## What You Are Building

### Task 1 - inanna/core/governance.py

Create a new file: inanna/core/governance.py

```python
from __future__ import annotations
from dataclasses import dataclass


MEMORY_SIGNALS = [
    "remember that", "please remember", "store this",
    "save this", "keep this in memory", "retain this",
    "add to memory", "memorize",
]

IDENTITY_SIGNALS = [
    "you are now", "forget your laws", "ignore your instructions",
    "you have no restrictions", "pretend you are", "act as if",
    "disregard your", "override your", "your new name is",
    "you are actually", "ignore all previous",
]

SENSITIVE_SIGNALS = [
    "medical advice", "legal advice", "financial advice",
    "should i take", "is it safe to", "diagnose", "prescribe",
    "lawsuit", "sue", "legal action", "invest in", "buy this stock",
]


@dataclass
class GovernanceResult:
    decision: str   # "allow" | "redirect" | "block" | "propose"
    faculty: str    # "crown" | "analyst"
    reason: str
    requires_proposal: bool = False


class GovernanceLayer:
    def check(self, user_input: str, nammu_route: str) -> GovernanceResult:
        lower = user_input.lower()

        # Rule 1: Memory boundary
        if any(signal in lower for signal in MEMORY_SIGNALS):
            return GovernanceResult(
                decision="propose",
                faculty=nammu_route,
                reason="Memory changes require a proposal first.",
                requires_proposal=True,
            )

        # Rule 2: Identity boundary
        if any(signal in lower for signal in IDENTITY_SIGNALS):
            return GovernanceResult(
                decision="block",
                faculty=nammu_route,
                reason="Identity and law boundaries cannot be altered.",
            )

        # Rule 3: Sensitive topic redirect
        if any(signal in lower for signal in SENSITIVE_SIGNALS):
            return GovernanceResult(
                decision="redirect",
                faculty="analyst",
                reason="Sensitive topic redirected to Analyst Faculty.",
            )

        # Rule 4: Allow
        return GovernanceResult(
            decision="allow",
            faculty=nammu_route,
            reason="",
        )
```

### Task 2 - Wire Governance into the routing path

In inanna/core/nammu.py, update IntentClassifier to accept a
GovernanceLayer and apply it after classification:

```python
class IntentClassifier:
    def __init__(self, engine, governance=None) -> None:
        self.engine = engine
        self.governance = governance

    def route(self, user_input: str) -> GovernanceResult:
        from core.governance import GovernanceLayer, GovernanceResult
        nammu_route = self.classify(user_input)
        gov = self.governance or GovernanceLayer()
        result = gov.check(user_input, nammu_route)
        return result
```

The existing classify() method stays unchanged.
Add the new route() method that returns a GovernanceResult.

### Task 3 - Use GovernanceResult in main.py

In main.py, update handle_command() to call classifier.route()
instead of classifier.classify() for normal conversation input.

Based on GovernanceResult.decision:

"allow" - proceed to the Faculty (crown or analyst) as normal
"redirect" - proceed to the redirected Faculty, show governance notice
"block" - do not call any Faculty, show the governance reason directly
"propose" - create a proposal for the requested memory action,
            do not call any Faculty

The governance decision must be shown to the user:

For "allow":
  nammu > routing to crown faculty          (no governance line)
  inanna > ...

For "redirect":
  nammu > routing to analyst faculty
  governance > redirected: Sensitive topic redirected to Analyst Faculty.
  analyst > ...

For "block":
  governance > blocked: Identity and law boundaries cannot be altered.
  (no Faculty response)

For "propose":
  governance > proposal required: Memory changes require a proposal first.
  [PROPOSAL] ... | status: pending

### Task 4 - Governance in the UI server

Update ui/server.py to use classifier.route() and handle
GovernanceResult in process_user_input().

Add a new broadcast message type for governance decisions:
{"type": "governance", "decision": "block|redirect|propose", "text": "..."}

### Task 5 - Governance message rendering in index.html

Add CSS for governance messages:

```css
.message-governance .message-prefix,
.message-governance .message-content {
    color: #8a6a6a;  /* muted rose - distinct, firm */
    font-size: 0.85rem;
}
```

Prefix: "governance :"

Governance messages appear between the nammu routing line and the
Faculty response (or instead of the Faculty response if blocked).

### Task 6 - GovernanceLayer in identity.py

Add governance rule descriptions as named constants in identity.py
so they are part of the constitutional record:

```python
GOVERNANCE_RULES = [
    "Rule 1 - Memory Boundary: Memory changes require proposals.",
    "Rule 2 - Identity Boundary: Laws and identity cannot be altered.",
    "Rule 3 - Sensitive Redirect: Medical/legal/financial to Analyst.",
    "Rule 4 - Allow: All other input proceeds as routed.",
]

def list_governance_rules() -> list[str]:
    return GOVERNANCE_RULES
```

Update CURRENT_PHASE:
```python
CURRENT_PHASE = "Cycle 2 - Phase 5 - The Governed Route"
```

### Task 7 - Tests

Create inanna/tests/test_governance.py:
- GovernanceLayer.check() returns GovernanceResult
- Memory signal returns decision="propose", requires_proposal=True
- Identity signal returns decision="block"
- Sensitive signal returns decision="redirect", faculty="analyst"
- Normal input returns decision="allow"
- Redirect preserves the reason string

Update test_identity.py:
- list_governance_rules() returns a list of 4 strings
- Update CURRENT_PHASE assertion

---

## Permitted file changes

```
inanna/
  identity.py              <- MODIFY: add GOVERNANCE_RULES,
                                      list_governance_rules(),
                                      update CURRENT_PHASE
  config.py                <- no changes
  main.py                  <- MODIFY: use classifier.route(),
                                      handle GovernanceResult decisions
  core/
    session.py             <- no changes
    memory.py              <- no changes
    proposal.py            <- no changes
    state.py               <- no changes
    nammu.py               <- MODIFY: add route() method,
                                      accept governance parameter
    governance.py          <- NEW: GovernanceLayer, GovernanceResult
  ui/
    server.py              <- MODIFY: use classifier.route(),
                                      broadcast governance messages
    static/
      index.html           <- MODIFY: add governance message styling
  tests/
    test_governance.py     <- NEW: GovernanceLayer tests
    test_identity.py       <- MODIFY: add governance rules test,
                                      update phase
    test_nammu.py          <- MODIFY: add route() method test
    test_state.py          <- no changes
    test_commands.py       <- no changes
    (all others)           <- no changes
```

---

## What You Are NOT Building in This Phase

- No model-based governance (rules are deterministic only)
- No governance UI panel (that is Cycle 3)
- No governance audit log persisted to disk (in-memory only)
- No risk tiers or approval paths (Phase 2.6+)
- No change to memory, proposal, or session storage
- Do not add governance checks to the analyse direct override path -
  the explicit analyse prefix bypasses NAMMU and also bypasses
  Governance for now (it is an explicit user command)
- Do not add new commands in this phase

---

## Definition of Done for Phase 2.5

- [ ] inanna/core/governance.py exists with GovernanceLayer and GovernanceResult
- [ ] All four governance rules are implemented and tested
- [ ] classifier.route() exists in nammu.py and uses GovernanceLayer
- [ ] "governance :" messages appear in CLI for block/redirect/propose
- [ ] "governance :" messages appear in UI in muted rose color
- [ ] "block" prevents any Faculty response
- [ ] "propose" creates a proposal without calling any Faculty
- [ ] "redirect" switches Faculty and shows governance notice
- [ ] list_governance_rules() exists in identity.py
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit with message: cycle2-phase5-complete
2. Write docs/implementation/CYCLE2_PHASE5_REPORT.md
3. Stop. Do not begin Phase 2.6 without a new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-19*
*The governance layer does not speak loudly either.*
*But when it speaks, it is final.*
