# CURRENT PHASE: Cycle 5 - Phase 5.8 - The Orchestration Layer
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-20**
**Cycle: 5 - The Operator Console**
**Replaces: Cycle 5 Phase 5.7 - The Domain Faculty (COMPLETE)**

---

## What This Phase Is

Phase 5.7 gave INANNA a second voice: SENTINEL.
Phase 5.8 teaches two voices to work together.

Orchestration is the ability to route a complex task through multiple
Faculties in sequence, passing results from one to the next, and
synthesizing a final response that reflects the combined intelligence.

Example:
  "Analyze the security of this Python code and explain the risks in simple terms."
  → SENTINEL analyzes the code for vulnerabilities (security domain)
  → CROWN synthesizes the findings into clear, human language (general domain)
  → The user receives one coherent response

This is not two separate messages. It is one governed orchestration:
  propose → approve → SENTINEL → CROWN → respond

The governed MCP principle applies:
  discover → propose → approve → execute → result → audit

---

## What You Are Building

### Task 1 - OrchestrationEngine in core/orchestration.py

Create: inanna/core/orchestration.py

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

@dataclass
class OrchestrationStep:
    faculty: str
    purpose: str        # "analyze" | "synthesize" | "verify" | "summarize"
    input_from: str     # "user" | previous faculty name
    output_to: str      # next faculty name | "user"

@dataclass
class OrchestrationPlan:
    steps: list[OrchestrationStep]
    trigger_pattern: str   # what input pattern triggers this plan
    requires_approval: bool = True

class OrchestrationEngine:
    def __init__(self, faculties_path: Path):
        self.faculties_path = faculties_path
        self._plans = self._load_plans()

    def _load_plans(self) -> list[OrchestrationPlan]:
        # Built-in plans — later phases can load from config
        return [
            OrchestrationPlan(
                trigger_pattern="security.*explain|analyze.*security.*simple|"
                                "vulnerabilit.*plain|security.*non.*technical",
                steps=[
                    OrchestrationStep("sentinel", "analyze", "user", "crown"),
                    OrchestrationStep("crown", "synthesize", "sentinel", "user"),
                ],
                requires_approval=True,
            ),
        ]

    def detect_orchestration(self, user_input: str) -> OrchestrationPlan | None:
        import re
        for plan in self._plans:
            if re.search(plan.trigger_pattern, user_input, re.IGNORECASE):
                return plan
        return None

    def format_synthesis_prompt(
        self,
        user_input: str,
        previous_output: str,
        step: OrchestrationStep,
    ) -> str:
        if step.purpose == "synthesize":
            return (
                f"The user asked: {user_input}\n\n"
                f"The {step.input_from.upper()} Faculty analyzed this and found:\n"
                f"{previous_output}\n\n"
                f"Please synthesize these findings into a clear, accessible response "
                f"for the user. Preserve the important insights while making them "
                f"understandable. Do not add information not present in the analysis."
            )
        return user_input
```

### Task 2 - Orchestration proposal type

When an orchestration is detected, generate a special proposal:

```
[ORCHESTRATION PROPOSAL] 2026-04-20T... |
Multi-Faculty task: SENTINEL → CROWN |
SENTINEL will analyze, CROWN will synthesize. |
status: pending
```

This gives the operator visibility into what is about to happen
before it happens. One proposal covers the full orchestration chain.

After approval, both Faculty calls execute without additional proposals.

### Task 3 - Orchestration execution in server.py and main.py

In the conversation handling flow, after NAMMU classification,
check for orchestration before routing:

```python
# In handle_conversation_turn():

# 1. Check orchestration first
plan = orchestration_engine.detect_orchestration(text)
if plan:
    # Generate orchestration proposal
    # After approval: execute chain
    first_output = run_faculty(plan.steps[0].faculty, text, grounding)
    for step in plan.steps[1:]:
        synthesized_input = orchestration_engine.format_synthesis_prompt(
            text, first_output, step
        )
        final_output = run_faculty(step.faculty, synthesized_input, grounding)
    broadcast as: {"type": "orchestration", "steps": [...], "text": final_output}
    return

# 2. Otherwise: normal NAMMU routing
```

### Task 4 - Orchestration message type in index.html

Add "orchestration" message type — rendered with a distinct visual:
A subtle header showing the chain that produced the response:

```css
.msg-row.orchestration .msg-bubble {
    background: rgba(120, 72, 176, .06);
    border: 1px solid rgba(120, 72, 176, .25);
    border-left: 2px solid var(--vio3);
    font-size: 13px;
    color: var(--rose5);  /* same as INANNA */
    line-height: 2;
    font-family: var(--serif);
}
.msg-chain-header {
    font-size: 8px;
    letter-spacing: 3px;
    color: var(--vio3);
    margin-bottom: 10px;
    padding-bottom: 6px;
    border-bottom: 1px solid rgba(120, 72, 176, .2);
}
```

The chain header shows: `𒊩 SENTINEL → CROWN · orchestrated response`

### Task 5 - Orchestration audit trail

Each orchestration execution appends to the audit surface:
```
orchestration: SENTINEL→CROWN | input: "..." | steps: 2 | approved: proposal-xxx
```

### Task 6 - Orchestration visible in Console

The Operator Console activity feed shows orchestration events distinctly.
The Faculties panel shows call counts for both SENTINEL and CROWN
after an orchestration run.

### Task 7 - Update identity.py and state.py

CURRENT_PHASE = "Cycle 5 - Phase 5.8 - The Orchestration Layer"
No new commands in this phase.

### Task 8 - Tests

Create inanna/tests/test_orchestration.py:
  - OrchestrationEngine can be instantiated
  - detect_orchestration() returns a plan for "analyze security and explain simply"
  - detect_orchestration() returns None for unrelated input
  - format_synthesis_prompt() includes previous output
  - format_synthesis_prompt() includes user input
  - OrchestrationPlan has correct step count
  - OrchestrationStep has faculty, purpose, input_from, output_to

Update test_identity.py: update CURRENT_PHASE assertion.

---

## Permitted file changes

inanna/identity.py
inanna/main.py                  <- orchestration detection and execution
inanna/core/
  orchestration.py              <- NEW
  state.py                      <- update phase only
inanna/ui/
  server.py                     <- orchestration detection and execution,
                                   broadcast as "orchestration" type,
                                   audit trail
  static/index.html             <- add orchestration message type CSS + handler
inanna/tests/
  test_orchestration.py         <- NEW
  test_identity.py              <- update phase assertion

---

## What You Are NOT Building

- No dynamic orchestration plan loading from config (plans are built-in)
- No more than 2 steps in a chain (SENTINEL → CROWN only)
- No parallel Faculty execution (sequential only)
- No orchestration for non-security inputs in Phase 5.8
- No changes to console.html beyond activity feed
- Do not modify faculties.json or tools.json

---

## Definition of Done

- [ ] core/orchestration.py with OrchestrationEngine
- [ ] detect_orchestration() recognizes security+explain patterns
- [ ] Orchestration proposal generated before chain executes
- [ ] SENTINEL → CROWN chain executes on approval
- [ ] Final response broadcast as "orchestration" type
- [ ] index.html renders orchestration messages with chain header
- [ ] Audit trail entry for each orchestration
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed to origin/main immediately

---

## Handoff

Commit: cycle5-phase8-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE5_PHASE8_REPORT.md
Stop. Do not begin Phase 5.9 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-20*
*Two voices. One response.*
*The orchestra begins to play as one.*
