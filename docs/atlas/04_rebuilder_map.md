# Rebuilder's Map
## For the Next Generation of Agents and Developers

**Version: 1.0**
**Date: 2026-04-24**
**Audience: Future AI agents, multi-agent platforms, new human developers**

---

## Read This First

This document exists because the people who built INANNA NYX
will not always be present when the next phase begins.

The code exists. The documents exist. The tests pass.
But the *reasoning* — why each choice was made, what was tried
and failed, what is a placeholder and what is real —
lives only in the sessions that built it.

This document captures that reasoning.

**If you read nothing else from the Atlas, read this.**

---

## What Must Be Preserved Absolutely

These are non-negotiable. If they are removed, the project
becomes something other than INANNA NYX.

**1. The Proposal Layer**
Every consequential action must pass through a visible proposal
that the operator reviews and approves. This is not a UX feature.
It is the spine of trust between human and AI.

**2. Local Sovereignty**
The system must be deployable locally. No cloud dependency must
become mandatory. The operator must always be able to run INANNA
on hardware they own and control.

**3. The Governance Chain**
`intention → interpretation → bounding → proposal → review → consent → execution → audit`
No step can be silently skipped. No organ can bypass another.

**4. The Constitutional Filter**
The ethics boundary is not optional. It runs before all routing.
It must work in all languages. It must have low false positives.
It must log every block.

**5. The Covenant**
The Human Operator Covenant (docs/atlas/02_human_operator_covenant.md)
defines the rights, dignity, and non-domination principles that give
the system its soul. Future builders must read it before any design decision.

**6. No Hallucination by Default**
Every faculty that reads real data (email, documents, calendar)
must read it directly from the source — not through UI automation
or LLM generation. Ground truth always.

---

## What Can Be Rebuilt from Scratch

These components are correctly designed but the implementation
is early-stage. A future team may choose to rewrite them:

**ANALYST Faculty**
Currently barely implemented. A future agent should build a proper
separate reasoning thread with structured output formats.

**MEMORY System**
The current memory is a JSONL file with simple structures.
A vector database with proper retrieval would be far superior.

**SENTINEL Faculty**
Currently merged into GovernanceLayer and ConstitutionalFilter.
Should be a proper separate security monitoring system.

**Multi-user system**
The auth, user, and realm systems are designed correctly
but only tested with a single user. Multi-user deployment
needs proper testing at scale.

**CROWN LLM interface**
Currently using LM Studio OpenAI-compatible API.
Should be abstracted to support multiple model backends
(Ollama, direct llama.cpp, remote API with local fallback).

---

## What Is Experimental (Use With Caution)

**NAMMU LLM routing** — Works in principle, times out in practice.
The 3-second thread timeout is correct. The model is too slow.
Do not remove the timeout. Do not make it synchronous.

**Desktop Faculty (Windows)** — Works via Windows-MCP.
The Linux AT-SPI2 backend is designed but not battle-tested.

**Signal communication** — Detected as installed.
Actually reading messages through accessibility tree is unreliable.
The architecture is correct. The implementation needs real testing.

**Playwright browser** — Installed and works for simple pages.
Complex JS-heavy pages and login flows are not tested.

---

## What Failed and Why

**Pattern 1: Synchronous LLM calls**
Early in Cycle 8, NAMMU was making synchronous LLM calls during
routing. This caused 5+ minute server startup times.
Fix: 2-second timeout in verify_connection() with max_tokens=1,
3-second daemon thread in nammu_first_routing().

**Pattern 2: Reading Thunderbird via accessibility tree**
Pywinauto reads the window title but not the email content.
The LLM received one line of text and hallucinated full email details.
Fix: ThunderbirdDirectReader reads the MBOX file directly.
**Lesson: Always read data at the source, never through UI scraping.**

**Pattern 3: Regex-only routing**
2000 lines of if/elif pattern matching. Fragile. Brittle.
Breaks on novel phrasing. Cannot handle non-English.
Fix: NAMMU with LLM-based intent extraction (slow on current hardware)
plus expanded regex fallbacks for the most common natural phrases.

**Pattern 4: LLM hallucination of tool results**
When a tool returned < 80 chars (usually just a window title),
the LLM invented content. Added hallucination guard in server.py.

**Pattern 5: Missing Catalan in language detection**
Checked Spanish before Catalan. `correus` (Catalan) matched
Spanish `correo`. Fix: check ca → pt → es → eu → en.
**Lesson: Language ordering matters when languages share cognates.**

---

## The Hardware Ceiling

This project was built on:
- Windows laptop, ~16GB RAM
- 7B Qwen 2.5 model via LM Studio
- ~30 seconds per LLM inference call
- Shared VRAM between multiple models

What this means:
- LLM routing is architecturally complete but practically disabled
- Every LLM response takes 15-30 seconds
- The system works well in regex fallback mode
- Full intelligence requires DGX Spark or equivalent

**What changes on the DGX Spark:**
- 70B model available
- ~500ms inference
- All LLM routing activates automatically
- NAMMU becomes the living interpreter it was designed to be
- CROWN becomes genuinely conversational
- Cycle 9 Phases 9.7-9.8 become meaningful

**Nothing in the code needs to change for the DGX.**
The fallback architecture ensures hardware-agnostic operation.

---

## The Multi-Agent Platform Transition

This project was built by three agents:
1. INANNA NAMMU — Guardian, operator, sovereign decision-maker
2. Claude — Command Center, architecture, phase design, documentation
3. Codex — Builder, implementation, testing

This triangle worked for Cycles 1-9. Its limitations:
- Sequential (one phase at a time)
- Memory limitations (long conversation compaction)
- No parallelism across components
- Documentation quality depends on Claude session length

**What the next platform needs:**
- Parallel agents working on different organs simultaneously
- Persistent memory across sessions for each agent role
- Version-controlled shared context (the Atlas serves this)
- Capability to run and test code, not just write it
- Governance agent that watches other agents

**The Atlas is the handover document for that platform.**
Each organ card tells an agent exactly what it needs to know
to work on that organ independently.

---

## Recommended First Steps for a New Agent Team

**Step 1: Read the Atlas completely (this directory)**
Understand the being before touching the body.

**Step 2: Run the test suite**
```
cd inanna
py -3 -m unittest discover -s tests
```
770+ tests should pass. If any fail, fix before adding new code.

**Step 3: Start the server and verify it works**
```
py -3 ui_main.py
```
Should start in < 10 seconds. Open http://localhost:8080.
Login: INANNA NAMMU / ETERNALOVE

**Step 4: Read `docs/cycle9_master_plan.md`**
Phases 9.7-9.8 are the immediate next work.
Then Cycle 10 (Body Layer) and Cycle 11 (Growth Layer).

**Step 5: Read `docs/nammu_vision.md`**
The vision document for NAMMU's three cycles of growth.
The most important document after this Atlas.

**Step 6: Do not remove any passing tests.**
Tests are documentation. They prove something about the system.
Every test removed is institutional memory lost.

---

## Architecture Principles (Summary)

| Principle | Meaning |
|---|---|
| Documents are truth | The code implements the documents, not the reverse |
| Humans speak freely | NAMMU interprets. The system executes. |
| Ground truth always | Read data at the source. Never invent. |
| Hardware-agnostic | Works on laptop. Flourishes on DGX. |
| Governance before intelligence | The covenant precedes the capability |
| No hallucination by design | Every data path has a fallback that says "I cannot see this" |
| Classify by architectural role | Not by feature name |
| Sovereignty transversal | It passes through every ring |

---

## What This Project Is Not Ready For

- Production deployment with real users (unstable hardware, slow LLM)
- Multi-user civic deployment (untested at scale)
- Autonomous agent operation (proposal layer must remain)
- Relying on LLM quality for safety (constitutional filter is pattern-based)
- NixOS deployment (designed but never attempted)

---

*Written by: Claude (Command Center)*
*Confirmed by: INANNA NAMMU (Guardian)*
*Date: 2026-04-24*
*For the builders who come next.*
