# INNER ORGAN · MEMORY
## The Archive — Long-Term Memory, Reflection, and Continuity

**Ring: Inner AI Organs**
**Grade: C+ (works for single user, not yet multi-user or civic scale)**
**Version: 1.0 · Date: 2026-04-24**

---

## Identity

**What it is:**
MEMORY is the continuity organ of INANNA NYX.
It preserves what matters across sessions — not everything,
but what the operator and governance decide should persist.

**What it does:**
- Stores approved reflections from sessions
- Maintains operator profiles across conversations
- Provides context to CROWN at session start
- Manages the boundary between session memory and persistent memory
- Records routing history for NAMMU learning

**What it must never do:**
- Store everything automatically (memory requires restraint)
- Promote private memory to communal memory without governance
- Allow memory to become a behavioral dossier
- Persist memory that the operator has not approved

**The name:**
MEMORY is not a database. It is selective continuity.
The difference matters: a database stores everything.
MEMORY stores what is worth remembering.

---

## Ring

**Inner AI Organs** — MEMORY gives INANNA continuity across time.
Without MEMORY, every session starts from zero.
With MEMORY, INANNA knows the operator, their preferences,
their ongoing projects, and their corrections.

---

## Correspondences

| Component | Location |
|---|---|
| Core memory class | `core/memory.py` → `Memory` |
| Reflective memory | `core/reflection.py` |
| Operator NAMMU profile | `core/nammu_profile.py` → `OperatorProfile` |
| User profile | `core/profile.py` → `UserProfile` |
| Session memory | `core/session.py` → session events |
| Routing memory | `core/nammu_memory.py` → routing_log.jsonl |
| Storage location | `data/realms/default/memory/` |
| NAMMU profile storage | `data/realms/default/nammu/operator_profiles/` |

**Called by:** `ui/server.py` (loads at session start), CROWN context building
**Calls:** Storage layer (JSON files)
**Reads:** memory JSONL files, operator profiles
**Writes:** memory JSONL, operator profiles, routing logs

---

## Mission

MEMORY exists because intelligence without continuity is shallow.

A system that forgets every session cannot serve a person deeply.
It cannot remember that INANNA NAMMU prefers short answers,
that "mtx" means Matxalen, that urgent emails are always the priority.

But memory without governance becomes surveillance.
MEMORY must be selective — storing what helps, not what profiles.

The Memory Promotion Law governs what can move:
- Private insight → stays private unless explicitly shared
- Session pattern → stays in session unless promoted
- Useful shorthand → promoted to NAMMU profile (explicit)
- Behavioral vulnerability → never promoted anywhere

---

## Current State

### What Works

**Reflective memory:**
- Proposals for memory updates generated from conversation
- Approved reflections stored in JSONL format
- Loaded at session start as context for CROWN

**NAMMU operator profile (active and growing):**
- Shorthands learned via `nammu-learn`
- Corrections recorded via `nammu-correct`
- Language patterns detected and stored
- Domain weights updated after every tool use
- Profile persists across sessions

**Session memory:**
- Current conversation stored in session events
- Available to CROWN for context

### What Is Missing

- Vector database for semantic memory retrieval
- Cross-session pattern recognition
- Communal memory with promotion law enforcement
- Memory expiry and cleanup policies
- Multi-user memory isolation verification
- Civic-scale memory architecture (departments, realms, communities)

---

## Memory Types (Design — not all implemented)

| Type | Scope | Governance | Status |
|---|---|---|---|
| Session memory | Current conversation | None (ephemeral) | Implemented |
| Private memory | This operator only | Operator consent | Partially implemented |
| Realm memory | This community | Realm governance | Not implemented |
| Communal memory | Promoted patterns | Collective governance | Not implemented |
| Forbidden memory | Never stored | Constitutional | Implemented (deletion) |

---

## Desired Function

**With vector database (Cycle 10+):**
- Semantic search across all approved memories
- "What did we decide about X?" returns relevant past decisions
- Memory relevance scoring per query

**With multi-user memory (Cycle 11+):**
- Each operator's private memory is fully isolated
- Realm memory shared within community, governed collectively
- Memory promotion law enforced — no automatic upward flow

---

## Evaluation

**Grade: C+**

The memory architecture is philosophically correct.
The NAMMU profile works and persists.
Reflective memory works for single-user scenarios.

Single most important gap:
**No semantic retrieval. Memory is chronological JSONL.**

If the operator asks "what did we decide about X six months ago?"
the system cannot answer. The memory exists but is not queryable.

Priority: integrate a lightweight vector store (SQLite with
vector extensions, or Chroma) for semantic memory retrieval.

---

*Organ Card version 1.0 · 2026-04-24*
