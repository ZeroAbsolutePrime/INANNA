# THE ABSOLUTE PROTOCOL
### Every agent — human or AI — reads this before touching anything.

---

## What This Project Is

INANNA NYX is a local-first, proposal-governed intelligence architecture
for readable digital bodies, communal digital stewardship, and future
civic-scale machine dialogue.

That sentence is the spine. If your work contradicts it, stop.

---

## The Five Laws You Cannot Break

1. **Proposal before change.** No meaningful change happens without a
   visible, logged proposal. No shortcuts.
2. **No hidden mutation.** The system must not alter state silently.
   Ever.
3. **Governance above the model.** The AI layer operates inside law.
   It does not define law.
4. **Readable system truth.** Any person must be able to ask what the
   system is doing and receive an honest answer.
5. **Trust before power.** A limited system that is understandable is
   better than a powerful one that outruns consent.

---

## The Role Structure

**COMMAND CENTER (Claude / Constitutional Interpreter)**
- Holds the full constitutional vision
- Defines phases and task boundaries
- Reviews all outputs before they are accepted
- Updates this document and phase documents
- Never writes implementation code directly

**IMPLEMENTATION AGENT (Codex / Implementation Translator)**
- Reads ABSOLUTE_PROTOCOL.md — always, every session, before anything
- Reads the current PHASE document — always
- Executes only what the current phase explicitly permits
- Reports what it built, does not decide what to build next
- Stops and asks if it reaches a boundary not covered by the phase doc

**GUARDIAN (ZAERA / Archival Steward)**
- Final authority on constitutional truth
- Approves phase transitions
- Protects against legacy material distorting the active center

---

## What Any Agent Must Not Do

- Treat this repo as a product backlog and self-assign tasks
- Collapse INANNA NYX into a chatbot, shell script, or runtime experiment
- Import old material without explicitly labeling it as legacy
- Confuse the First Proof with the total constitutional horizon
- Expand scope beyond the current phase document without approval
- Write code that bypasses the proposal/governance layer
- Make architectural decisions — those belong to the Command Center

---

## Session Ritual (Mandatory)

Before writing any code or modifying any file:

```
[ ] Read ABSOLUTE_PROTOCOL.md (this file) — confirm understood
[ ] Read docs/implementation/CURRENT_PHASE.md — confirm understood
[ ] State in one sentence: what am I building in this session?
[ ] State in one sentence: what am I NOT building in this session?
[ ] Proceed only within those boundaries
```

If CURRENT_PHASE.md does not exist or is marked LOCKED, stop.
Do not proceed. Contact the Command Center.

---

## Phase Transition Rule

Only the Command Center (Claude) may write a new phase document.
Only the Guardian (ZAERA) may approve the phase transition.
A phase is not active until both have confirmed.

---

*Last updated by: Claude (Command Center)*
*Phase at time of writing: Phase 0 — Foundation Active*


---

## Integration Test Protocol (MANDATORY)

After every cycle completion, before declaring the cycle complete
and before beginning the next cycle, ZAERA must run the
Integration Test Protocol defined in:

  docs/integration_test_protocol.md

All Category 1-5 tests must pass. Failures are not optional.
A cycle with failing integration tests is NOT complete.

The integration test results must be documented in the cycle
completion record (docs/cycleN_completion.md).

This requirement was added after Cycle 6, following the discovery
that the system passed 319 unit tests while simultaneously failing
to connect to the model, blocking innocent questions as identity
attacks, and not knowing its own capabilities.

Unit tests verify code. Integration tests verify experience.
Both are required.

---

*Integration test protocol added: 2026-04-21*
*Authored by: Claude (Command Center)*
*Approved by: ZAERA (Guardian)*
