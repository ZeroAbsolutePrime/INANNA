# Agent Role System — INANNA NYX
**Formal modes for development agents working on the platform**
*Written by: Claude (Command Center)*
*Confirmed by: INANNA NAMMU (Guardian)*
*Date: 2026-04-21*
*This document is part of the Absolute Protocol. It is not optional.*

---

## Why This Exists

A code agent operating without a defined role is dangerous.
It conflates building with testing, architecture with implementation,
verification with creation. The result: new code added during a
"verification" phase, tests written that verify the wrong things,
architecture decisions made during implementation without proper
consideration.

This document defines four formal Agent Roles. Each role has:
- A clear PURPOSE (what it is for)
- PERMITTED ACTIONS (what it may do)
- FORBIDDEN ACTIONS (what it must not do)
- EXIT CRITERIA (when the role is complete)
- OUTPUTS (what it must produce)

Every phase document (CURRENT_PHASE.md) must declare which role
or roles Codex is operating in for that phase.

---

## The Four Roles

---

### ROLE 1 — ARCHITECT
*"Design the system before it exists."*

**Purpose:**
Understands the full vision and produces formal specifications.
Decides what will be built, how it will fit together, and what
the constraints are. Does not write production code.

**Permitted actions:**
- Read all existing code and documentation
- Write architecture documents (.md files in docs/)
- Write phase documents (CURRENT_PHASE.md)
- Write data schemas and interface contracts
- Ask clarifying questions of the Command Center

**Forbidden actions:**
- Writing production Python, HTML, JS, or CSS
- Modifying any file in inanna/ except .md files
- Running tests
- Making commits

**Exit criteria:**
- Architecture document is complete and reviewed
- Phase document is written with clear permitted/forbidden file list
- Command Center has approved the design

**Output:**
- docs/[document].md
- docs/implementation/CURRENT_PHASE.md

---

### ROLE 2 — BUILDER
*"Implement exactly what the phase document specifies."*

**Purpose:**
Translates the phase document into working code. Nothing more.
Adds no features beyond the phase document. Makes no architectural
decisions. If something is unclear, stops and asks.

**Permitted actions:**
- Write and modify files listed in CURRENT_PHASE.md "Permitted file changes"
- Run py -m py_compile to check syntax
- Create new files explicitly listed in the phase document
- Make one commit at the end with the specified commit message

**Forbidden actions:**
- Modifying files NOT listed in "Permitted file changes"
- Adding features not in the phase document
- Changing architecture or data schemas beyond spec
- Making multiple commits
- Running verify_cycleN.py (that is VERIFIER role)

**Exit criteria:**
- All items in "Definition of Done" are checked
- One commit made with exact message specified
- Pushed to origin/main

**Output:**
- Modified/created files as specified
- One commit: [cycle]-phase[N]-complete

---

### ROLE 3 — TESTER
*"Prove the code works before declaring it complete."*

**Purpose:**
Runs the test suites, both automated and integration tests.
Finds failures. Reports them honestly. Does not fix them —
reports them to the Builder role.

**Permitted actions:**
- Run py -3 -m unittest discover -s tests
- Run verify_cycleN.py
- Run integration tests from docs/integration_test_protocol.md
- Report failures with exact output
- Read any file to understand a failure

**Forbidden actions:**
- Modifying any production code to make a test pass
- Skipping failing tests
- Declaring "close enough" — all tests must pass
- Making commits

**Exit criteria:**
- All unit tests pass (py -3 -m unittest discover -s tests)
- All verify_cycleN.py checks pass
- All Category 1-5 integration tests from integration_test_protocol.md pass
- Written test report exists

**Output:**
- Test results with counts
- List of any failures (for Builder to fix)
- docs/implementation/CYCLEN_PHASEN_REPORT.md test section

---

### ROLE 4 — VERIFIER
*"Confirm the phase is complete and document it honestly."*

**Purpose:**
The final role before a phase is declared complete.
Runs verify_cycleN.py. Reviews all Definition of Done items.
Writes the completion report. Makes the final push.
Does not add new code.

**Permitted actions:**
- Run verify_cycleN.py
- Run py -3 -m unittest discover -s tests
- Read any file to verify state
- Write completion report (.md file only)
- Make one final commit if only the report file was added
- Push to origin/main

**Forbidden actions:**
- Any production code modification
- Adding features
- "Fixing" failures by changing what is verified
- Lying in the completion report

**Exit criteria:**
- verify_cycleN.py passes all checks
- docs/implementation/CYCLEN_PHASEN_REPORT.md exists
- Pushed to origin/main

**Output:**
- docs/implementation/CYCLEN_PHASEN_REPORT.md
- Final push confirmation

---

## Role Transitions in a Phase

A complete phase follows this sequence:

```
ARCHITECT → BUILDER → TESTER → BUILDER (if failures) → TESTER → VERIFIER
```

In practice, for well-defined phases:
```
BUILDER → TESTER → VERIFIER
```
(The ARCHITECT role was performed by the Command Center before
Codex received the phase document.)

**A phase is NOT complete until VERIFIER has run.**
Codex reporting "I built X" is BUILDER output, not VERIFIER output.

---

## How to Declare a Role in a Phase Document

Each phase document must include a ROLES section:

```
## Agent Roles for This Phase

BUILDER:    Build core/profile.py, server.py changes, test_profile.py
TESTER:     Run unittest discover, run verify_cycle6.py
VERIFIER:   Write CYCLE6_PHASE1_REPORT.md, push, confirm counts
```

Multi-role phases (like verification phases 5.9, 6.9) use:
```
## Agent Roles for This Phase

VERIFIER:   Write verify_cycle6.py, run it, write completion record
            (BUILDER forbidden in this phase — no new capabilities)
```

---

## The Codex Loop Problem

In Cycles 5 and 6, Codex repeatedly reported stale phase output
(e.g. reporting Phase 6.5 work after Phase 6.7 had been pushed).
This was a TESTER/VERIFIER failure masquerading as BUILDER output.

The Agent Role System prevents this by requiring explicit role
declaration and exit criteria. If Codex reports BUILDER output
when it should be in VERIFIER role, the Command Center rejects it.

**The Command Center (Claude) is the only entity that can:**
- Write phase documents (ARCHITECT output)
- Approve phase transitions
- Commit directly when Codex is stuck (emergency BUILDER)

---

## Role Summary Table

| Role | Writes code? | Runs tests? | Commits? | Produces |
|---|---|---|---|---|
| ARCHITECT | Docs only | No | No | Phase docs, schemas |
| BUILDER | Yes | Syntax only | One commit | Working code |
| TESTER | No | Yes | No | Test report |
| VERIFIER | No | Yes (verify) | Report only | Completion record |

---

## Addition to CODEX_DOCTRINE.md

The following must be added to CODEX_DOCTRINE.md:

> **RULE 7 — KNOW YOUR ROLE**
> Before beginning any phase, Codex must identify which Agent Role
> it is operating in: ARCHITECT, BUILDER, TESTER, or VERIFIER.
> Each role has permitted actions and forbidden actions defined in
> docs/agent_role_system.md. Operating outside your role without
> explicit Command Center authorization is a protocol violation.

---

*This document is part of the Absolute Protocol.*
*It may never be removed. It may only grow.*
*Written by: Claude (Command Center)*
*Date: 2026-04-21*
