# CURRENT PHASE: Cycle 2 - Phase 4 - The NAMMU Kernel
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-19**
**Cycle: 2 - The NAMMU Kernel**
**Replaces: Cycle 2 Phase 3 - The Second Faculty (COMPLETE)**

---

## What This Phase Is

Phase 2.3 gave INANNA two Faculties. The user chooses which one to invoke
by prefixing their input with "analyse". That is explicit routing - the
human decides.

Phase 2.4 introduces NAMMU - the first layer of governed automatic routing.

NAMMU is the mediation field where operator intention, Oracle interpretation,
body truth, governance constraints, and possible action are brought into
governed relation. It is not merely routing. It is the field where intention
becomes structured possibility.

In Phase 2.4, NAMMU takes one concrete, bounded form: an IntentClassifier
that reads the user's input and decides whether to route it to the CROWN
Faculty (conversational, relational) or the ANALYST Faculty (structured,
analytical). This decision is made transparently - NAMMU logs its routing
decision before the Faculty responds, so the user always knows which Faculty
is speaking and why.

This is NAMMU's first breath. It will deepen in future phases.

---

## The NAMMU Layer - Phase 2.4 Scope

NAMMU in this phase is a single Python module: inanna/core/nammu.py

It contains one class: IntentClassifier

IntentClassifier reads the user's message and returns one of two routing
decisions: "crown" or "analyst"

It does this by asking the model itself - a lightweight classification
call that precedes the actual Faculty response. This is governed routing:
the classification is logged, visible, and auditable.

---

## What You Are Building

### Task 1 - inanna/core/nammu.py

Create a new file: inanna/core/nammu.py

```python
from __future__ import annotations
from identity import build_system_prompt

CLASSIFICATION_PROMPT = """You are the NAMMU routing layer of INANNA NYX.
Your only task is to classify the user intention as one of two routes:

CROWN - for: conversational exchanges, personal sharing, emotional content,
        questions about INANNA herself, memory and identity topics,
        reflective or relational requests

ANALYST - for: requests for structured analysis, comparative reasoning,
          technical questions, "why does X work", "explain the relationship
          between X and Y", requests for breakdown or examination

Reply with exactly one word: either CROWN or ANALYST.
Nothing else. No explanation. Just the routing decision."""


class IntentClassifier:
    def __init__(self, engine) -> None:
        self.engine = engine

    def classify(self, user_input: str) -> str:
        messages = [
            {"role": "system", "content": CLASSIFICATION_PROMPT},
            {"role": "user", "content": user_input},
        ]
        if not self.engine._connected:
            return self._heuristic_classify(user_input)
        try:
            result = self.engine._call_openai_compatible(messages)
            route = result.strip().upper()
            if "ANALYST" in route:
                return "analyst"
            return "crown"
        except Exception:
            return self._heuristic_classify(user_input)

    def _heuristic_classify(self, text: str) -> str:
        analyst_signals = [
            "analyse", "analyze", "explain", "why does", "how does",
            "what is the relationship", "compare", "examine", "breakdown",
            "structured", "reasoning", "implications", "technical",
        ]
        lower = text.lower()
        if any(signal in lower for signal in analyst_signals):
            return "analyst"
        return "crown"
```

### Task 2 - Auto-routing in main.py

Update handle_command() in main.py so that normal conversation input
(not a recognized command) is first passed through IntentClassifier.

When NAMMU routes to "analyst", the input is handled by AnalystFaculty.
When NAMMU routes to "crown", the input is handled by Engine as before.

The routing decision must be shown to the user BEFORE the response:

```
nammu > routing to analyst faculty
analyst > [live analysis] ...

nammu > routing to crown faculty
inanna > Hello, ZAERA...
```

The explicit "analyse" prefix command from Phase 2.3 must still work
as a direct override that bypasses NAMMU classification entirely.

IntentClassifier is instantiated in main() alongside Engine and AnalystFaculty.

### Task 3 - NAMMU routing in the UI server

Update InterfaceServer in ui/server.py to instantiate IntentClassifier.

In process_user_input(), before routing to Engine or AnalystFaculty,
call classifier.classify(text).

Broadcast the routing decision as a new message type:
{"type": "nammu", "route": "crown", "text": "routing to crown faculty"}
or
{"type": "nammu", "route": "analyst", "text": "routing to analyst faculty"}

This message appears in the conversation panel BEFORE the Faculty response.

### Task 4 - NAMMU message rendering in index.html

Add CSS for nammu routing messages:

```css
.message-nammu .message-prefix,
.message-nammu .message-content {
    color: #6a8a7a;  /* muted sage green - distinct, subtle */
    font-size: 0.82rem;
    letter-spacing: 0.06em;
}
```

Prefix: "nammu :"
The routing message is small and subtle - it is system infrastructure,
not conversation. It should be visually present but not dominant.

### Task 5 - NAMMU audit in history

Update Proposal.history_report() or add a new NAMMU log alongside proposals.

Actually: keep it simple for this phase. Add a routing_log list to
InterfaceServer that records each routing decision:
{"timestamp": ..., "input_preview": first 60 chars, "route": "crown|analyst"}

Expose this via a new command: "routing-log"

When user types "routing-log", show:
```
NAMMU Routing Log (N decisions):
  [crown]   2026-04-19T07:25:08 | Hello, I am ZAERA...
  [analyst] 2026-04-19T07:25:44 | What makes a governance...
```

Add "routing-log" to STARTUP_COMMANDS and capabilities.

### Task 6 - Update identity.py

Add the NAMMU classification prompt as a named constant:

```python
NAMMU_CLASSIFICATION_PROMPT = """..."""  # same text as in nammu.py

def build_nammu_prompt() -> str:
    return NAMMU_CLASSIFICATION_PROMPT
```

Update CURRENT_PHASE:
```python
CURRENT_PHASE = "Cycle 2 - Phase 4 - The NAMMU Kernel"
```

### Task 7 - Tests

Add inanna/tests/test_nammu.py:
- IntentClassifier.classify() returns "crown" or "analyst"
- Heuristic classify returns "analyst" for "analyse this"
- Heuristic classify returns "analyst" for "explain why"
- Heuristic classify returns "crown" for "hello"
- Heuristic classify returns "crown" for "I am ZAERA"

Update test_identity.py:
- Add test for build_nammu_prompt() non-empty
- Update CURRENT_PHASE assertion

---

## Permitted file changes

```
inanna/
  identity.py              <- MODIFY: add NAMMU_CLASSIFICATION_PROMPT,
                                      build_nammu_prompt(), update CURRENT_PHASE
  config.py                <- no changes
  main.py                  <- MODIFY: instantiate IntentClassifier, auto-route
                                      in handle_command(), add routing-log command
  core/
    session.py             <- no changes
    memory.py              <- no changes
    proposal.py            <- no changes
    state.py               <- MODIFY: add routing-log to capabilities line
    nammu.py               <- NEW: IntentClassifier class
  ui/
    server.py              <- MODIFY: instantiate IntentClassifier, broadcast
                                      nammu routing message, routing_log list,
                                      handle routing-log command
    static/
      index.html           <- MODIFY: add nammu message styling and rendering
  tests/
    test_nammu.py          <- NEW: IntentClassifier tests
    test_identity.py       <- MODIFY: add nammu prompt test, update phase
    test_state.py          <- MODIFY: update capabilities assertion
    test_commands.py       <- MODIFY: add routing-log in capabilities test
    (all others)           <- no changes
```

---

## What You Are NOT Building in This Phase

- No multi-step NAMMU mediation (that is Phase 2.5+)
- No governance tier checking in NAMMU (Phase 2.6)
- No NAMMU memory layer (Phase 2.7)
- No persistent routing log across sessions (flat in-memory only for now)
- No Faculty chaining or sequential routing
- No change to proposal, memory, or session storage logic
- The explicit "analyse" prefix must remain as a direct override

---

## Definition of Done for Phase 2.4

- [ ] inanna/core/nammu.py exists with IntentClassifier
- [ ] Normal conversation is auto-routed by NAMMU
- [ ] "nammu : routing to X faculty" appears before each response
- [ ] "analyse" prefix still works as direct override
- [ ] "routing-log" command shows NAMMU decision history
- [ ] UI shows nammu messages in muted sage green
- [ ] build_nammu_prompt() exists in identity.py
- [ ] CURRENT_PHASE updated to "Cycle 2 - Phase 4 - The NAMMU Kernel"
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] test_nammu.py exists with heuristic tests

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit with message: cycle2-phase4-complete
2. Write docs/implementation/CYCLE2_PHASE4_REPORT.md
3. Stop. Do not begin Phase 2.5 without a new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-19*
*NAMMU does not speak loudly. It routes faithfully.*
*Its presence is felt in the small green line before every response.*
