# CURRENT PHASE: Phase 1 — The Living Loop
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-18**

---

## What Phase 1 Is

Phase 1 builds the smallest honest proof that INANNA NYX is alive:
a local, private, memory-aware dialogue companion that demonstrates
the proposal/governance loop in real operation.

This is NOT the full architecture.
This is ONE first manifestation — the smallest loop that proves
the laws work in living code.

---

## What You Are Building

A Python CLI application with four components:

### Component 1 — Session Engine
- Accepts user text input
- Sends it to a local or API-based language model
- Returns a response
- Logs the full exchange to a session file

### Component 2 — Memory Store
- Reads previous session logs on startup
- Extracts a bounded summary (max 10 lines) of prior context
- Injects that summary into the next session as context
- Memory is stored as plain .json files — no database yet

### Component 3 — Proposal Log
- Every time the system would make a change to memory or behavior,
  it generates a human-readable proposal entry
- Format: [PROPOSAL] {timestamp} | {what} | {why} | {status: pending}
- Status can only be changed by the user typing approve or reject

### Component 4 — Readable State Report
- On demand (user types status), the system prints:
  - Current session ID
  - How many memories are loaded
  - How many proposals are pending
  - What the system is and is not allowed to do right now

---

## Permitted File Locations

```
inanna/
  core/
    session.py
    memory.py
    proposal.py
    state.py
  data/
    sessions/
    memory/
    proposals/
  main.py
  requirements.txt
```

---

## What You Are NOT Building in This Phase

- No web interface, no Flask, no HTTP server
- No database — flat files only
- No user accounts or authentication
- No emotional analysis or psychological profiling
- No governance UI — text only
- No multi-user support
- No Docker, no deployment configuration
- Do not use ontology names (Oracle, NAMMU, Faculty) as class names

---

## Definition of Done for Phase 1

- [ ] python main.py starts a session with no errors
- [ ] User can have a multi-turn conversation
- [ ] Session is saved and loaded correctly on next run
- [ ] Memory summary appears in context on session start
- [ ] At least one proposal is generated and logged during a session
- [ ] status command returns honest readable system state
- [ ] All four components have basic unit tests that pass
- [ ] No code exists outside the permitted file locations above

---

## Handoff to Command Center

When done, Codex must:
1. Commit all work with message: phase-1-complete
2. Write docs/implementation/PHASE_1_REPORT.md with:
   - What was built
   - Decisions made
   - Unclear boundaries
   - Proposals for Phase 2

Then stop. Do not begin Phase 2 without a new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
