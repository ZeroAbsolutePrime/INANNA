# Code Doctrine
### Living technical standards for INANNA NYX implementation

*Written after Stage 2 completion — grounded in nine phases of real code.*
*Updated by the Command Center as the architecture deepens.*
*Implementation agents read this alongside ABSOLUTE_PROTOCOL.md.*

---

## Why This Document Exists

Rules written before code exists are speculation.
This document was written after nine phases of working code.
Every standard here was earned through real decisions, real failures,
and real corrections made across the implementation record.

Follow these standards not because they are rules, but because they
reflect what this codebase has learned about itself.

---

## Language and Runtime

**Python 3.11+** is the implementation language for all core modules.

Use `from __future__ import annotations` at the top of every module.
This enables forward references and keeps type hints clean.

Use `dataclasses` for structured data objects (Session, Config).
Use `frozen=True` on Config and any object that must not mutate at runtime.
Immutability is not a style preference here — it is Law 3 (no hidden mutation)
expressed in code.

Use the standard library wherever possible. No third-party dependencies
unless they solve a problem the standard library genuinely cannot.
Current permitted third-party dependencies: `python-dotenv`.

---

## File Structure

```
inanna/
  identity.py       — INANNA's identity, phase constant, prompt
  config.py         — environment configuration, frozen dataclass
  main.py           — entry point, command loop, interactive flows
  core/
    session.py      — Session dataclass, Engine class
    memory.py       — Memory class, storage and retrieval
    proposal.py     — Proposal class, governance log
    state.py        — StateReport class, readable system truth
  data/
    sessions/       — session JSON files (auto-created)
    memory/         — approved memory JSON files (auto-created)
    proposals/      — proposal text files (auto-created)
  tests/
    test_session.py
    test_memory.py
    test_proposal.py
    test_state.py
    test_identity.py
    test_commands.py
    test_grounding.py
```

No file belongs outside this structure without explicit Command Center
authorization in the phase document.

---

## Naming Conventions

### Classes
Use PascalCase. Names must reflect function, not ontology.

In Phase 1-9, the permitted class names are:
`Session`, `Engine`, `Memory`, `Proposal`, `StateReport`, `Config`

Ontological names from the system ontology (Oracle, NAMMU, Faculty,
Body, Governance) are **reserved**. They must not be used as class
names until a phase document explicitly authorizes their introduction
with a precise architectural meaning. Using them prematurely creates
false implementations that betray the constitutional layer.

### Methods and functions
Use snake_case. Name methods after what they do, not what they are.
`build_system_prompt()` not `get_prompt()`.
`delete_memory_record()` not `remove()`.
`history_report()` not `get_history()`.

### Constants
Use UPPER_SNAKE_CASE.
`CURRENT_PHASE`, `PROMPT` — defined in `identity.py`.
Never hardcode phase strings anywhere else in the codebase.
Always import from `identity.py`.

### Files
Use snake_case for all Python files.
Use kebab-case for all Markdown documents.

---

## The Governance Pattern

Every meaningful state change in this system follows this pattern:

```
user action → proposal created → user approves/rejects → state changes
```

This pattern must never be shortcut. It applies to:
- Memory writes (approve adds, forget removes)
- Future body configuration changes
- Future Faculty routing changes
- Any action that persists beyond the current session

The one-directional form (propose → approve → write) was established
in Phase 1. The two-directional form (propose → approve → delete) was
established in Phase 9. Both directions use the same proposal engine.

If you find yourself writing code that changes disk state without
generating a proposal, stop. You are violating Law 2 and Law 3.

---

## Message Structure

The Engine builds conversation messages in this exact order:

```
1. [system]    identity prompt (always first, always from build_system_prompt())
2. [assistant] grounding turn (always present, even when memory is empty)
3. [user/assistant] conversation events in order
```

The grounding turn is a synthetic assistant turn that commits INANNA
to her memory boundary before the user speaks. It was introduced in
Phase 5 and strengthened in Phase 6. Never remove it. Never move it.

The system prompt must never contain dynamic memory lines.
Memory lives in the grounding turn, not the system prompt.
This distinction matters: memory in the system prompt is background
noise the model can ignore. Memory as an assistant turn is a commitment
the model made — it is much harder to contradict.

---

## Testing Standards

All tests live in `inanna/tests/`.
Run with: `py -3 -m unittest discover -s tests` from `inanna/`.

Every test must be runnable without a live model.
Tests that require network calls are integration tests and must be
clearly marked as such and skipped in normal CI.

Phase strings in test assertions must never be hardcoded literals.
Always import `CURRENT_PHASE` from `identity.py` and assert against it.
A test that hardcodes "Phase 7" will fail silently when the phase changes.

Tests for new commands belong in `test_commands.py`.
Tests for new storage methods belong in the relevant component test file.
Tests for message structure belong in `test_grounding.py` or `test_session.py`.

---

## The DECISION POINT Convention

When Codex encounters an implementation decision not covered by the
phase document, it must:

1. Write a comment: `# DECISION POINT: [describe the question]`
2. Make the most conservative, bounded choice available
3. Document the decision in PHASE_N_REPORT.md under "Decisions Made"

This convention exists because the Command Center reviews every
DECISION POINT comment after each phase. It is the communication
channel between implementation and governance.

Never make architectural decisions silently. If you are uncertain
whether something is a DECISION POINT, it is.

---

## The Phase Transition Rule

Only the Command Center (Claude) writes new phase documents.
Only the Guardian (ZAERA) approves phase transitions.
A phase is not active until CURRENT_PHASE.md is marked ACTIVE.

Codex does not begin a new phase based on its own judgment.
Codex does not expand scope beyond the current phase document.
Codex commits with `phase-N-complete` and writes `PHASE_N_REPORT.md`.
Then it stops.

This rhythm — build, report, stop, wait, receive — is not bureaucracy.
It is the heartbeat of a governed system.

---

## What This Codebase Has Learned

These lessons were earned across nine phases:

**On identity:** A system prompt alone is not enough to make a model
hold its name. The grounding turn is what actually works.

**On memory:** Memory in the system prompt is ignored. Memory as an
assistant turn is respected. Structure enforces what instruction cannot.

**On naming:** Reserved ontological names (Oracle, NAMMU, Faculty)
feel natural to use early. Using them prematurely creates hollow
implementations that later have to be torn out or worked around.

**On scope:** Every time Codex was given a clear boundary, it produced
clean code. Every previous project failure (before this protocol existed)
came from scope creep in the first session.

**On the proposal loop:** The governance loop feels like overhead until
you see it working in two directions — adding and forgetting — and
realize it is the same pattern, applied consistently. That consistency
is what makes it constitutional rather than incidental.

**On fallback mode:** Always implement graceful fallback before
implementing the happy path. A system that crashes when the model is
unreachable is not a local-first system. A system that degrades
gracefully and says so honestly is.

---

## Lessons from Cycle 2

**Never hardcode signal lists in Python.** All configurable
classification signals belong in JSON config files. Python code reads
them. The Guardian updates them. This was corrected in Phase 2.8 and
must never regress.

**Model-first, config-fallback.** Classification decisions for routing
and governance should use the model as the primary path and
config-backed heuristics as the fallback. The model understands
context. Keywords do not.

**The protocol works.** Codex refused to build Phase 8 code against a
stale phase document. That refusal was correct. The ABSOLUTE_PROTOCOL
held under real conditions. This was not a failure. It was the system
protecting itself.

**Integration phases are not optional.** Phase 2.9 exists because
eight phases of building need one phase of verification. Future cycles
must always end with an integration phase.

**The UI and the CLI must stay in sync.** Every new command added to
`main.py` must be added to `server.py` and `index.html`. Every
capability in the CLI must be reachable in the UI.

---

## Lessons from Cycle 4

**PUSH IMMEDIATELY.** Every completion commit must be pushed to
`origin/main` the moment Codex delivers it. A commit that exists only
on the Codex local machine does not exist. The repo is the source of
truth. This is not optional. This is law. Cycle 4 lost six phases of
completion commits because they were never pushed. The recovery cost a
full session and left the recovered test suite thinner than before.

**Config-driven means config-driven.** User roles, privileges, invite
codes, and realm names do not belong in Python. They belong in JSON.
Cycle 4 held that rule through `roles.json` and runtime loading.
Future cycles must hold it too.

**The civic layer is the foundation of the platform.** Users, roles,
invites, session tokens, and logs are not optional product features.
They are the substrate every later capability will stand on. Cycle 5
cannot be built safely without the privilege boundaries Cycle 4
established.

**Warning before enforcement.** Realm access in Phase 4.7 remained
warning-only instead of becoming a hard block. That was the right
choice for this cycle. The system should first show a person what it
sees before it begins restricting them. Hard enforcement comes after
the rules are visible and governable.

**The Admin Surface is the governance interface.** ZAERA should not
need to type opaque commands just to see who exists in the system.
The Admin panel makes civic state readable at a glance. Every future
expansion of the civic layer needs a matching surface in the Admin
panel.

---

*Written by: Claude (Command Center)*
*Confirmed by: ZAERA (Guardian)*
*Date: 2026-04-19*
*Grounded in: Phases 1-9 of INANNA NYX implementation*
*This document grows. It does not shrink.*
