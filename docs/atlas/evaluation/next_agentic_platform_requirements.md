# EVALUATION · Next Agentic Platform Requirements
## What the Multi-Agent Platform Needs to Continue This Work

**Ring: Evaluation**
**Version: 1.0 · Date: 2026-04-24**

---

## Why a Multi-Agent Platform

The first nine cycles were built by a three-agent triangle:
- INANNA NAMMU (Guardian, operator, decision-maker)
- Claude (Command Center, architecture, documentation)
- Codex (Builder, implementation, testing)

This triangle worked well for sequential, document-driven development.
Its limitations became clear at Cycle 9:

- Sequential only — one phase at a time
- Memory limitations — long conversations compress and lose context
- No parallelism — CROWN, NAMMU, OPERATOR cannot be worked on simultaneously
- Documentation quality depends on Claude session length
- No agent can run and test code while another designs

The next spiral requires agents working in parallel
on different organs with shared context.

---

## What the Platform Needs

### 1. Persistent Shared Context
Each agent must be able to read the Atlas before beginning work.
The Atlas serves this function — it is the shared memory of the project.

No agent should begin work without reading:
- `docs/atlas/00_living_architecture_map.md`
- `docs/atlas/04_rebuilder_map.md`
- The relevant organ card for their assigned component

### 2. Code Execution Capability
Agents must be able to run tests, not just write code.
A Builder agent that cannot verify `py -3 -m unittest discover -s tests`
is writing blind.

### 3. Role Separation

**Architect agent:**
- Reads the Atlas
- Designs new phases and components
- Writes phase documents
- Does not write implementation code

**Builder agent (multiple, parallel):**
- Reads the relevant organ card
- Implements one organ or faculty at a time
- Runs tests before declaring done
- Writes the handoff report

**Reviewer agent:**
- Reads implementation after Builder
- Verifies tests pass
- Checks against Atlas principles
- Does not merge without Atlas compliance

**Guardian agent (human or AI):**
- INANNA NAMMU holds final approval
- Reviews proposals before any structural change
- Approves commits to main branch

### 4. Git Discipline
Every agent must follow the existing commit discipline:
- Phase documents pushed before implementation begins
- Implementation pushed as `cycle{N}-phase{M}-complete`
- Handoff report written after implementation
- Tests must pass before any push to main

### 5. Atlas Maintenance
As new organs and faculties are built, the Atlas must be updated.
One agent should be designated Atlas Keeper —
responsible for keeping organ cards current as implementations evolve.

---

## Priority Order for Next Platform

The most impactful work, in order:

**1. Complete Cycle 9 (Phases 9.7-9.8)**
- NAMMU Constitution document
- verify_cycle9.py capability proof
- These complete the current cycle cleanly before the next begins

**2. Build ANALYST (Core Organ)**
- Create `core/analyst.py`
- Dedicated reasoning prompt
- Structured output format
- Integration with OPERATOR dispatch
- This is the highest-value missing organ

**3. Implement semantic MEMORY**
- Replace JSONL with vector store
- Enable "what did we decide about X?" queries
- This transforms MEMORY from a log into a real archive

**4. Agentic loop in OPERATOR**
- Multi-step tool execution
- Vision feedback for Desktop Faculty
- This closes the gap with ChatGPT Agent mode

**5. NixOS deployment test**
- Apply configs to a real Linux machine
- Verify AT-SPI2 backend
- This moves the project from Windows to its intended platform

**6. Second operator test**
- Create a second user account
- Verify session isolation
- Verify role separation
- This is required before any community deployment

---

## What the Platform Must Not Do

- Remove the proposal layer
- Bypass the governance chain
- Treat the organ cards as optional reading
- Merge code that breaks existing tests
- Conflate organs with faculties (the Atlas taxonomy must be maintained)
- Claim organs are complete when they are placeholder
- Optimize the system at the expense of sovereignty

---

*Evaluation Card version 1.0 · 2026-04-24*
