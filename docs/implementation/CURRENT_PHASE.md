# CURRENT PHASE: Phase 2 — The Real Voice
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-18**
**Replaces: Phase 1 — The Living Loop (COMPLETE)**

---

## What Phase 2 Is

Phase 1 proved the governance loop works. The session runs, proposals are
generated, memory is written only after explicit approval. The laws are
alive in code.

Phase 2 gives INANNA a real voice by wiring the Engine to a local model
running in LM Studio, and resolves the four open questions Codex raised
in PHASE_1_REPORT.md.

Phase 2 does NOT expand the architecture. It deepens what already exists.

---

## The Four Open Questions — Now Answered

### Q1: Model provider
**Answer:** LM Studio running locally.
The Engine connects to LM Studio's OpenAI-compatible endpoint at:
`http://localhost:1234/v1`
This is configured via environment variable INANNA_MODEL_URL.
INANNA_MODEL_NAME must be set to the exact model name shown in LM Studio.
INANNA_API_KEY is not required for LM Studio but must be supported as optional.

### Q2: Which proposal does approve/reject target?
**Answer:** The oldest pending proposal, exactly as Codex implemented.
This is now explicit policy, not a guess. Document it in a comment.
No change to the current behavior — just make the policy named and visible.

### Q3: Should approved memory replace or coexist with raw session context?
**Answer:** Approved memory takes priority and loads first.
Raw session lines supplement only if the approved memory fills fewer than
the max_lines limit. This is already how Codex implemented it.
Again — no code change needed, just make the policy explicit in a comment.

### Q4: Where do tests live?
**Answer:** Tests stay inside component modules for Phase 2.
A dedicated test directory is a Phase 3 concern when complexity justifies it.

---

## What You Are Building

### Task 1 — LM Studio connection verification
Add a startup check: when the app launches, if INANNA_MODEL_URL is set,
attempt a minimal test call to the model before entering the conversation loop.
If the call fails, print a clear warning and continue in fallback mode.
Do not crash. Do not block the session from starting.

The check must print one of these two messages on startup:
- `Model connected: {model_name} at {url}`
- `Model unreachable — fallback mode active. Set INANNA_MODEL_URL to connect.`

### Task 2 — Configuration surface
Create one new file: `inanna/config.py`
This file reads the three environment variables and exposes them as a
named Config object. main.py imports Config instead of reading os.getenv
directly. This is the only new file permitted in Phase 2.

```
inanna/
  config.py         <- NEW: reads env vars, exposes Config object
  core/
    session.py      <- MODIFY: add explicit policy comment on oldest-first
    memory.py       <- MODIFY: add explicit policy comment on memory priority
    proposal.py     <- no changes needed
    state.py        <- no changes needed
  main.py           <- MODIFY: import Config, add startup connection check
  requirements.txt  <- MODIFY: verify all deps are listed correctly
```

### Task 3 — .env support
Add python-dotenv to requirements.txt.
At the top of main.py, load a .env file from the inanna/ directory if present.
This allows the model URL and name to be set without exporting shell variables.
Add a .env.example file showing the three variables with placeholder values.
Add .env to .gitignore if not already present.

### Task 4 — Startup context display improvement
Currently startup context prints as a raw list. Change the display so it
prints with a clear header and numbered lines, like:

```
Prior context (3 lines):
  1. user: hello
  2. assistant: welcome back
  3. user: tell me more
```

This is a display-only change. No logic changes in memory.py.

---

## What You Are NOT Building in This Phase

- No new core components beyond config.py
- No web interface, no API server
- No new data storage formats — flat files only
- No change to the proposal or memory logic
- No multi-user support
- No Docker or deployment configuration
- No streaming responses
- No conversation history trimming or summarization
- Do not rename any existing files or classes
- Do not change the data/ directory structure

---

## LM Studio Setup Reference

LM Studio exposes an OpenAI-compatible API at:
`http://localhost:1234/v1`

The .env file should contain:
```
INANNA_MODEL_URL=http://localhost:1234/v1
INANNA_MODEL_NAME=<exact model name from LM Studio>
INANNA_API_KEY=
```

The Engine in session.py already supports this endpoint format.
No changes to the Engine's HTTP logic are needed.

---

## Definition of Done for Phase 2

- [ ] config.py exists and is imported by main.py
- [ ] .env.example exists with the three variables shown
- [ ] .env is in .gitignore
- [ ] Startup prints model connection status before the conversation begins
- [ ] When INANNA_MODEL_URL and INANNA_MODEL_NAME are set and LM Studio
      is running, the assistant responds with real model output
- [ ] When model is unreachable, fallback mode activates gracefully
- [ ] Startup context displays with numbered lines and header
- [ ] Policy comments are present in session.py and memory.py
- [ ] All existing unit tests still pass
- [ ] No code exists outside the permitted file locations above

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit all work with message: `phase-2-complete`
2. Write `docs/implementation/PHASE_2_REPORT.md` containing:
   - What was built
   - Any decisions made during implementation
   - Any boundaries that felt unclear
   - Any proposals for Phase 3

Then stop. Do not begin Phase 3 without a new CURRENT_PHASE.md
from the Command Center.

---

*Written by: Claude (Command Center)*
*Phase 1 reviewed and approved: 2026-04-18*
