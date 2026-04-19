# CURRENT PHASE: Cycle 2 - Phase 3 - The Second Faculty
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-19**
**Cycle: 2 - The NAMMU Kernel**
**Replaces: Cycle 2 Phase 2 - The Refined Interface (COMPLETE)**

---

## What This Phase Is

The interface is alive and honest. The first proof is complete.

Phase 2.3 introduces the Analyst Faculty - a second, distinct cognitive surface with a different role, different identity, and different system prompt. INANNA can now route certain requests to the Analyst for deeper, more structured reasoning, while keeping the primary conversational voice with the CROWN Faculty.

This is not multi-agent in the full NAMMU sense - that comes in Phase 2.4. This phase establishes the second Faculty as a working entity with its own identity.

---

## The Two Faculties

### CROWN Faculty - Primary Voice
The current model (Qwen via LM Studio).
Role: conversational presence, memory grounding, relational response.
Already exists - no changes needed to its prompt.

### ANALYST Faculty - Deep Reasoning Surface
A second model call using the same LM Studio endpoint but a different system prompt.
Role: structured analysis, comparative reasoning, long-form thinking.
The ANALYST Faculty does not speak as INANNA directly. It produces structured analytical output.

---

## What You Are Building

### Task 1 - AnalystFaculty class in core/session.py

Add a new class AnalystFaculty in core/session.py alongside the existing Engine class.

AnalystFaculty has:
- Its own system prompt (from identity.py)
- A single public method: analyse(question: str, context: list[str]) -> tuple[str, str]
  Returns (mode, text) - same pattern as reflect() and speak_audit()
- Its own fallback response when the model is unreachable

### Task 2 - Analyst system prompt in identity.py

Add ANALYST_PROMPT constant and build_analyst_prompt() function to identity.py.

The prompt must state:
- "You are the Analyst Faculty of INANNA NYX"
- "You are not INANNA conversational voice. You are her analytical mind."
- Role: structured reasoning, comparative analysis, precise thinking
- Same five laws as INANNA
- Instruction to be precise, structured, honest about limits

### Task 3 - The analyse command

Add a new command: analyse

When the user types "analyse [question]", the system routes to AnalystFaculty
instead of the CROWN Faculty (Engine).

Response prefix: analyst > [live analysis] or analyst > [analysis fallback]

The analyse command DOES generate a proposal - analytical exchanges deserve
the same memory governance as conversational ones.

AnalystFaculty is instantiated in main() alongside Engine, using the same config.

### Task 4 - Analyst Faculty in the UI server

Update ui/server.py to instantiate AnalystFaculty alongside Engine.

When input begins with "analyse", route to AnalystFaculty.analyse().

Broadcast analyst responses as {"type": "analyst", "text": "..."}.

In index.html, add CSS for analyst messages with color #8ab4c4 (cool blue).
Prefix: "analyst :"

### Task 5 - Update capabilities and CURRENT_PHASE

Add analyse to STARTUP_COMMANDS in main.py and capabilities line in state.py.

Update CURRENT_PHASE in identity.py:
CURRENT_PHASE = "Cycle 2 - Phase 3 - The Second Faculty"

### Task 6 - Tests

Add tests in inanna/tests/test_session.py:
- AnalystFaculty can be instantiated with empty config
- AnalystFaculty.analyse() returns a tuple (str, str)
- In fallback mode, the mode string is "fallback"

Add tests in inanna/tests/test_identity.py:
- build_analyst_prompt() returns a non-empty string
- The analyst prompt contains "Analyst Faculty"
- The analyst prompt contains "structured"

Update test_identity.py CURRENT_PHASE assertion to Phase 2.3.

---

## Permitted file changes

```
inanna/
  identity.py          <- MODIFY: add ANALYST_PROMPT, build_analyst_prompt(), update CURRENT_PHASE
  config.py            <- no changes
  main.py              <- MODIFY: instantiate AnalystFaculty, add analyse command
  core/
    session.py         <- MODIFY: add AnalystFaculty class
    memory.py          <- no changes
    proposal.py        <- no changes
    state.py           <- MODIFY: add analyse to capabilities line
  ui/
    server.py          <- MODIFY: instantiate AnalystFaculty, route analyse prefix
    static/
      index.html       <- MODIFY: add analyst message styling
  tests/
    test_session.py    <- MODIFY: add AnalystFaculty tests
    test_identity.py   <- MODIFY: add analyst prompt tests, update phase
    test_commands.py   <- MODIFY: add analyse in capabilities test
    test_state.py      <- MODIFY: update capabilities assertion
```

---

## What You Are NOT Building in This Phase

- No routing logic between Faculties (that is Phase 2.4 - NAMMU)
- No automatic Faculty selection - user explicitly types analyse
- No separate model endpoints - both Faculties use the same LM Studio URL
- No change to memory, proposal, or governance logic
- Do not name anything "NAMMU" - that layer comes in Phase 2.4

---

## Definition of Done for Phase 2.3

- [ ] AnalystFaculty class exists in core/session.py
- [ ] build_analyst_prompt() exists in identity.py
- [ ] analyse [question] command works in CLI
- [ ] analyse [question] command works in UI with blue analyst : prefix
- [ ] Analyst responses generate proposals
- [ ] status capabilities line includes analyse
- [ ] CURRENT_PHASE updated to "Cycle 2 - Phase 3 - The Second Faculty"
- [ ] All tests pass: py -3 -m unittest discover -s tests

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit with message: cycle2-phase3-complete
2. Write docs/implementation/CYCLE2_PHASE3_REPORT.md
3. Stop. Do not begin Phase 2.4 without a new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-19*
*The second Faculty speaks in a different color.*
*That difference is the beginning of architecture.*
