# Minimum Viable Sovereign System
## The Bar for Version 1.0

**Ring: Evaluation**
**Version: 1.0 · Date: 2026-04-25**
**Status: Required — defines completion criteria for the next spiral**

---

> *"The project is unusually honest about phase truth.*
> *Do not lose that discipline."*

---

## Purpose

This document defines the minimum set of capabilities and properties
that must be real — not designed, not planned, not described —
before INANNA NYX can be called version 1.0.

It is not a feature list. It is a constitution for completion.

It answers: how will we know when we have built something
that deserves the name INANNA NYX rather than a prototype of it?

---

## What "Sovereign" Means Here

A sovereign system is one where:
1. The operator controls it — not the cloud, not a company, not a hidden process
2. The system is readable — the operator can know what it is doing
3. The system is inspectable — the operator can see what it has stored
4. The system is correctable — the operator can fix what it has learned wrong
5. The system is pauseable — the operator can stop any capability at any time
6. The system is local — it functions without internet connectivity

Every item in this document must be real in all six senses.

---

## The Minimum Viable Sovereign System

### M1 — The Conversation (CROWN + SESSION)
**Requirement:** The operator can have a meaningful conversation
with INANNA in any of their languages, and receive responses
that are relevant, grounded in real data, and not invented.

**Measurable:** No hallucination in any tool result presentation.
CROWN says "I could not read this" before it invents content.
Response time under 30 seconds (current hardware) or under 5 seconds (DGX).

**Current state:** Functional. Hallucination guard implemented.
Latency is 30 seconds — hardware constrained.

**Status: REAL ✓ (hardware-limited but architecturally complete)**

---

### M2 — Real Data Access (OPERATOR + Faculties)
**Requirement:** The operator can access their real data —
email, documents, calendar, files — and receive accurate information
about it, not summaries invented by the model.

**Measurable:**
- Email: reads from real MBOX file (not UI scraping)
- Documents: reads actual file bytes (not window title)
- Files: lists real directory contents
- Web: fetches real URL content

**Current state:** All implemented. ThunderbirdDirectReader.
Document reads (python-docx, pymupdf). Browser fetches.

**Status: REAL ✓**

---

### M3 — Governed Action (GUARDIAN + Proposal Tier Model)
**Requirement:** Consequential actions require operator approval.
Non-consequential actions execute without friction.
The tier model (Tier 0-5) is implemented.

**Measurable:**
- Tier 0 actions (reading) require no approval
- Tier 3+ actions (sending, external) require explicit confirmation
- The operator cannot accidentally send an email
- The operator is never blocked from reading their own data

**Current state:** Partially implemented. Proposal system exists
but all tools have the same approval weight. Tier model not yet built.

**Status: PARTIAL — tier model must be implemented**

---

### M4 — Constitutional Boundary (CONSCIENCE)
**Requirement:** The system holds firm on six absolute prohibitions
in any language. False positive rate is low enough that normal
use is never blocked.

**Measurable:**
- Absolute prohibitions trigger on any language
- "tell me about WWII" passes
- "my child is sick" passes
- "synthesize sarin" blocks
- 0 false positives on the standard test suite

**Current state:** Implemented. Pattern-based. 10/10 false positive tests pass.

**Status: REAL ✓ (pattern-based, LLM depth deferred to DGX)**

---

### M5 — Memory That Persists (MEMORY + PROFILE)
**Requirement:** What the operator teaches INANNA about themselves
is remembered across sessions. The operator's language patterns,
shorthands, and corrections persist and improve routing.

**Measurable:**
- `nammu-learn mtx Matxalen` persists across server restart
- `nammu-correct email_search X` is used in next session
- Language patterns update and persist
- `nammu-profile` shows accurate profile

**Current state:** Implemented. NAMMU operator profile persists.

**Status: REAL ✓ (semantic memory layer not yet built)**

---

### M6 — Inspectable State (Audit Trail)
**Requirement:** The operator can inspect what the system has done.
Every consequential action has an audit trail.
The operator can read their profile and correct it.

**Measurable:**
- `governance_log.jsonl` captures all governance decisions
- `routing_log.jsonl` captures all NAMMU routing decisions
- `nammu-profile` shows operator profile
- Operator can correct profile fields
- Audit trail is human-readable JSONL (no special tools required)

**Current state:** Implemented.

**Status: REAL ✓**

---

### M7 — Local Operation (Sovereignty)
**Requirement:** The system functions without internet connectivity
for all core operations. External services are optional and opt-in.

**Measurable:**
- Server starts with no internet
- Email reading works offline (local MBOX)
- Document reading works offline (local files)
- Calendar reading works offline (local SQLite)
- Web fetching is optional (only when explicitly requested)
- LLM model is local (LM Studio, not API)

**Current state:** Implemented. All local. LM Studio runs offline.

**Status: REAL ✓**

---

### M8 — Multilingual Operation (NAMMU)
**Requirement:** The operator can speak in their language
without switching modes. INANNA understands intent in
English, Spanish, Catalan, Portuguese, and Basque.

**Measurable:**
- "urgentes?" routes correctly (Spanish)
- "que tinc avui?" routes correctly (Catalan)
- "resumen de ayer" routes correctly (Spanish)
- Mixed-language sessions work without configuration

**Current state:** Implemented (regex fallback active).

**Status: REAL ✓**

---

### M9 — Authentication and Role Separation
**Requirement:** The system knows who is speaking.
Guardian and operator roles have different permissions.
Unauthenticated access is not possible.

**Measurable:**
- Login required (INANNA NAMMU / ETERNALOVE)
- Session token validated
- Guardian operations not available to operator role
- Failed authentication is logged

**Current state:** Implemented.

**Status: REAL ✓**

---

### M10 — Organic Learning From Errors (ERROR MEMORY)
**Requirement:** When INANNA makes a mistake, the correction
is remembered. The system does not repeat the same error
without awareness.

**Measurable:**
- `nammu-correct` records correction with context
- Correction appears in NAMMU's few-shot prompt in next session
- Error pattern is visible in `nammu-stats`

**Current state:** Partially implemented.
Corrections recorded in operator profile.
Error Memory layer (from Memory Architecture v2) not yet built.

**Status: PARTIAL — basic correction exists, deep Error Memory not built**

---

## What Is NOT Required for v1.0

These are important but not minimum viable:

| Deferred | Why |
|---|---|
| ANALYST organ | Valuable but not core to sovereignty |
| Semantic MEMORY | Important but NAMMU profile provides basic continuity |
| SENTINEL standalone | Constitutional filter provides minimum safety |
| Multi-user governance | Single operator is minimum viable |
| NixOS deployment | Windows runtime is functional |
| 70B model quality | 7B works for v1.0 at reduced quality |
| Streaming responses | Functional without streaming |
| Agentic loop | Single-step execution is minimum viable |
| Civic deployment | Far beyond minimum viable |

---

## The v1.0 Verdict

Based on the M1-M10 assessment:

| Requirement | Status |
|---|---|
| M1 Conversation | ✓ Real |
| M2 Real Data Access | ✓ Real |
| M3 Governed Action | ◐ Partial (tier model needed) |
| M4 Constitutional Boundary | ✓ Real |
| M5 Persistent Memory | ✓ Real |
| M6 Inspectable State | ✓ Real |
| M7 Local Operation | ✓ Real |
| M8 Multilingual Operation | ✓ Real |
| M9 Authentication | ✓ Real |
| M10 Error Learning | ◐ Partial |

**8/10 requirements are real.**
**2/10 are partial — both have clear next steps.**

**The system is at version 0.9 as measured against its own standard.**

The single most important step to reach v1.0:
**Implement the Proposal Tier Model (M3).**

The guardrail problem is the last significant gap between
"a prototype that sometimes frustrates" and "a sovereign system
that can be trusted in daily operation."

---

*Document version 1.0 · 2026-04-25*
*Written by: Claude (Command Center)*
*Confirmed by: INANNA NAMMU (Guardian)*
