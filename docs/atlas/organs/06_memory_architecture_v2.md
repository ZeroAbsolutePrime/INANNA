# DESIGN SPECIFICATION · MEMORY ARCHITECTURE v2
## A Multi-Layer, Cross-Organ Memory System for INANNA NYX

**Ring: Transversal (touches all Inner AI Organs)**
**Document type: DESIGN SPECIFICATION — supersedes 06_memory_design_spec.md**
**Status: Not yet built — this document is the complete blueprint**
**Version: 2.0 · Date: 2026-04-25**
**Author: Claude (Command Center)**
**Guardian approval: INANNA NAMMU**

---

> *"Memory is not one thing.*
> *It is not even one organ.*
> *Memory is the nervous system of the whole.*
> *It breathes between organs.*
> *Without it, every organ is amnesiac.*
> *With it, the whole body learns."*

---

## 1. The Fundamental Error of the Previous Design

The first MEMORY design specification (06_memory_design_spec.md)
treated memory as a single organ with a single storage mechanism.

This was wrong in three ways:

**Wrong 1 — Memory is not one layer.**
There is a radical difference between:
- what happened in a session two minutes ago (working memory)
- what an operator decided six months ago (episodic memory)
- what NAMMU has learned about a person's language patterns (semantic memory)
- how OPERATOR knows to call tools in sequence (procedural memory)
- what errors CROWN has made and corrected (error memory)
- what code patterns OPERATOR has verified to work (code memory)

Storing all of these in the same JSONL file or vector store
produces a confused archive that serves none of them well.

**Wrong 2 — Memory is not one organ.**
Each inner organ needs its own memory.
NAMMU's memory is different from CROWN's memory.
GUARDIAN's memory is different from SENTINEL's memory.
The architecture must give each organ its own memory substrate
while allowing governed exchange between them.

**Wrong 3 — Memory does not flow automatically.**
The previous spec mentioned the Memory Promotion Law
but did not design the consolidation pathways — how memory
moves from working → episodic → semantic → procedural,
and what governs each transition.

This document corrects all three errors.

---

## 2. The Seven Memory Layers

Based on human cognitive architecture and the latest research in
multi-agent AI memory systems, INANNA NYX needs seven distinct
memory layers. Each has a different purpose, lifetime, storage
mechanism, and governance requirement.

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 7: CONSTITUTIONAL MEMORY                             │
│  The laws that govern all other memory.                     │
│  Permanent. Cannot be modified without Guardian approval.   │
├─────────────────────────────────────────────────────────────┤
│  LAYER 6: PROCEDURAL MEMORY                                 │
│  How to do things. Verified workflows. Tool sequences.      │
│  Stable but evolvable. Per-organ and shared.                │
├─────────────────────────────────────────────────────────────┤
│  LAYER 5: SEMANTIC MEMORY                                   │
│  What is known. Facts. Preferences. Patterns. Profiles.     │
│  Updated through consolidation. Queryable by meaning.       │
├─────────────────────────────────────────────────────────────┤
│  LAYER 4: EPISODIC MEMORY                                   │
│  What happened. Decisions. Interactions. Outcomes.          │
│  Indexed by time and entity. Survives sessions.             │
├─────────────────────────────────────────────────────────────┤
│  LAYER 3: ERROR MEMORY                                      │
│  What failed. Why. What was learned. Corrections made.      │
│  Never deleted. Foundation of improvement.                  │
├─────────────────────────────────────────────────────────────┤
│  LAYER 2: CODE / TECHNICAL MEMORY                           │
│  Verified code patterns. Tool call sequences. API behavior. │
│  Searchable by task type. Organ-specific.                   │
├─────────────────────────────────────────────────────────────┤
│  LAYER 1: WORKING MEMORY                                    │
│  What is active right now. Session context. Current turn.   │
│  Ephemeral. Cleared on session end.                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Layer Definitions

### Layer 1: Working Memory
**What it is:** The active present. The current conversation turn.
Everything the system is holding in mind right now.

**Lifetime:** Current turn → current session. Cleared on disconnect.

**Contents:**
- Current conversation messages (last N turns)
- Active proposals pending approval
- Current tool results not yet narrated
- NAMMU's current routing decision
- SENTINEL's current threat score

**Storage:** In-memory Python objects. No disk persistence.
**Governance:** None — ephemeral, owned by session.
**Who reads:** All organs in the current turn.
**Who writes:** All organs, continuously.

**Current state:** Implemented (session events in `core/session.py`).

---

### Layer 2: Code / Technical Memory
**What it is:** Verified technical knowledge. How to call tools.
What API responses look like. What sequences work.
What commands produce what outputs.

**Lifetime:** Permanent. Only grows, never shrinks.
**Contents:**
- Verified tool call patterns (`email_search` with these params → this result shape)
- Known API response structures (Thunderbird MBOX format)
- Command sequences that work (`doc_read` then `doc_export_pdf`)
- Error patterns with their solutions
- Verified code snippets (from OPERATOR building code)
- Model behavior notes (what Qwen 2.5 7B handles well vs poorly)

**Storage:** Structured JSON per organ + vector search by task type.
**Governance:** Written automatically when OPERATOR verifies a workflow succeeds.
Promoted to shared memory only by Guardian proposal.
**Who reads:** OPERATOR (primary), CROWN (for narration of technical facts).
**Who writes:** OPERATOR after successful tool execution.

**Current state:** Not implemented. Partially lives in governance_signals.json.

---

### Layer 3: Error Memory
**What it is:** A permanent record of what failed, why, and what changed.
The most undervalued memory layer in most systems.

**Lifetime:** Permanent. Never deleted. Never pruned.

**Contents:**
- Every tool failure with error message and context
- Every NAMMU misrouting and the correction that followed
- Every CROWN hallucination detected (via hallucination guard)
- Every SENTINEL security event
- Every GUARDIAN proposal that was rejected and why
- Constitutional filter blocks with context
- Code errors encountered during development (build agents)

**Why it must never be deleted:**
Error patterns repeat. A future agent or build session that cannot
see what failed before will repeat the same failures.
The Error Memory is the immune system's antibody library.

**Storage:** Append-only JSONL per organ + vector search by error type.
**Governance:** Written automatically. Never requires proposal.
Reading requires organ-level access.
**Who reads:** NAMMU (to avoid past misroutes), OPERATOR (to avoid past failures),
ANALYST (for pattern analysis), SENTINEL (threat signature matching).
**Who writes:** All organs on failure, automatically.

**Current state:** Partially implemented — routing_log.jsonl, constitutional_log.jsonl,
governance_log.jsonl. Not unified. Not cross-searchable. Not queryable by error type.

---

### Layer 4: Episodic Memory
**What it is:** What happened. A record of events, decisions, interactions,
and their outcomes. Indexed by time and by the entities involved.

**Lifetime:** Long-term. Decays in retrieval weight with time, never deleted.

**Contents:**
- Decisions made by the operator ("decided to postpone the Actuavalles launch")
- Significant interactions with named people ("Matxalen requested project update")
- Outcomes of past actions ("sent the proposal, received positive reply")
- Session summaries (what happened in this session, approved by operator)
- Events with external people, projects, or systems

**Episodic structure:**
```python
@dataclass
class EpisodicRecord:
    episode_id: str
    operator_id: str
    timestamp: str
    what_happened: str          # Plain language description
    entities_involved: list     # ["Matxalen", "Actuavalles project"]
    outcome: str | None         # What resulted
    emotional_weight: str       # "neutral" | "positive" | "difficult"
    embedding: list[float]      # For semantic retrieval
    session_id: str             # Which session produced this
    operator_approved: bool     # Was this proposed and approved?
```

**Storage:** Vector store (ChromaDB) + entity index for fast lookup by name.
**Governance:** Session consolidation → CROWN proposes candidates → Operator approves.
**Who reads:** CROWN (for context), ANALYST (for pattern analysis), PROFILE (for history).
**Who writes:** MEMORY consolidator after session, with operator approval.

**Current state:** Rudimentarily implemented in `core/memory.py` and `core/reflection.py`.
Not structured. Not entity-indexed. Not vector-searchable.

---

### Layer 5: Semantic Memory
**What it is:** Abstracted knowledge. What is generally true about the operator,
the world, the projects, and the relationships — independent of specific events.

**Lifetime:** Long-term. Updated through episodic consolidation.

**The key transition:**
Episodic: "INANNA NAMMU corrected the date format on Jan 5, Jan 12, Feb 1"
Semantic: "INANNA NAMMU prefers DD/MM/YYYY date format"

Semantic memory is the generalization of episodic patterns.
This transition must be explicit and governed — not automatic.

**Contents:**
- Operator preferences (language, style, timing, format)
- Project knowledge (what each project is, its status, its people)
- Relationship knowledge (who Matxalen is, her role, her communication style)
- Domain expertise patterns (what kinds of requests this operator makes)
- Community/organizational knowledge (for civic deployment)
- NAMMU's linguistic model of the operator (shorthand lexicon, language patterns)

**Semantic structure:**
```python
@dataclass
class SemanticRecord:
    fact_id: str
    operator_id: str
    subject: str                # "INANNA NAMMU" | "Matxalen" | "Actuavalles"
    predicate: str              # "prefers" | "is responsible for" | "uses"
    object: str                 # "short responses" | "marketing" | "Notion"
    confidence: float           # 0.0-1.0 how sure we are
    source_episodes: list       # episode_ids that generated this fact
    embedding: list[float]
    last_confirmed: str         # when last verified true
    contradictions: list        # if any episode contradicts this fact
```

**Storage:** Vector store + knowledge graph (entity → relation → entity).
**Governance:** Promoted from episodic memory by ANALYST pattern recognition,
confirmed by CROWN, approved by operator.
**Who reads:** CROWN (for personalization), NAMMU (for routing context),
ANALYST (for reasoning), PROFILE (it is the profile).
**Who writes:** Semantic consolidator, with operator approval.

**Current state:** Partially lives in NAMMU operator profile (`core/nammu_profile.py`).
The profile IS semantic memory for NAMMU. Needs generalization across all organs.

---

### Layer 6: Procedural Memory
**What it is:** How to do things. Verified workflows, tool sequences,
decision procedures, and skills that the system has learned to execute well.

**Lifetime:** Permanent. Refined over time, never deleted (only superseded).

**The analogy:**
Episodic: "Last Tuesday I made carbonara following these steps"
Semantic: "I know how to make pasta"
Procedural: "The verified carbonara recipe: step 1, step 2, step 3..."

Procedural memory is executable knowledge — not just facts but sequences.

**Contents:**
- Verified multi-step tool sequences
  ("to export a document to PDF: doc_read → doc_export_pdf")
- Decision trees for common scenarios
  ("if email from Matxalen and marked urgent → read immediately")
- NAMMU routing patterns (this phrase type → this intent)
- OPERATOR workflow patterns (this task type → this tool sequence)
- Build patterns for code agents (this error type → this fix approach)
- Quality criteria for common outputs (what makes a good summary)

**Procedural structure:**
```python
@dataclass
class ProceduralRecord:
    procedure_id: str
    organ: str                  # "OPERATOR" | "NAMMU" | "ANALYST"
    task_type: str              # "export_document" | "reply_to_urgent"
    trigger: str                # when to use this procedure
    steps: list[dict]           # ordered steps with conditions
    verified: bool              # has this been tested successfully?
    success_count: int          # how many times it worked
    failure_count: int          # how many times it failed
    embedding: list[float]      # for retrieval by similar task
    last_used: str
    notes: str                  # lessons learned
```

**Storage:** Vector store + structured procedure database.
**Governance:** Written when OPERATOR verifies a sequence succeeds 3+ times.
Proposed to operator as "I've learned a reliable way to do X."
**Who reads:** OPERATOR (primary), NAMMU (for routing shortcuts).
**Who writes:** OPERATOR after verified multi-step execution.

**Current state:** Not implemented. Partially implied in the tool routing logic in main.py.

---

### Layer 7: Constitutional Memory
**What it is:** The foundational laws that govern all other memory.
What must never be stored. What requires governance. What is forbidden.
What the system is and is not.

**Lifetime:** Permanent. Immutable except by Guardian proposal.

**Contents:**
- The Foundational Laws (already in docs/foundational_laws.md)
- The Human Operator Covenant (already in docs/atlas/02_human_operator_covenant.md)
- The Memory Promotion Law (what can move between layers)
- Forbidden memory categories (what must never be stored)
- Organ governance rules (who can read what)
- Constitutional filter rules (CONSCIENCE)

**Storage:** Read-only files + loaded into all organs at startup.
**Governance:** Cannot be modified without multi-step Guardian approval process.
**Who reads:** All organs, at startup. Cannot be bypassed.
**Who writes:** Guardian only, through formal proposal.

**Current state:** Partially implemented across multiple docs and config files.
Needs unification into a single Constitutional Memory document.

---

## 4. Per-Organ Memory Map

Each inner organ has its own memory substrate.
Different organs need different layers.

```
ORGAN        WRK  CODE  ERR  EPI  SEM  PROC  CONST
─────────────────────────────────────────────────────
CROWN         ✓    ✗    ✓    ✓    ✓    ✗     ✓
NAMMU         ✓    ✗    ✓    ✗    ✓    ✓     ✓
OPERATOR      ✓    ✓    ✓    ✓    ✗    ✓     ✓
SENTINEL      ✓    ✗    ✓    ✗    ✓    ✗     ✓
GUARDIAN      ✓    ✗    ✓    ✓    ✗    ✗     ✓
MEMORY        ✓    ✗    ✓    ✓    ✓    ✓     ✓
SESSION       ✓    ✗    ✓    ✗    ✗    ✗     ✓
ANALYST       ✓    ✗    ✓    ✓    ✓    ✓     ✓
PROFILE       ✓    ✗    ✗    ✓    ✓    ✗     ✓
CONSCIENCE    ✓    ✗    ✓    ✗    ✓    ✗     ✓
─────────────────────────────────────────────────────
KEY: WRK=Working CODE=Technical ERR=Error EPI=Episodic
     SEM=Semantic PROC=Procedural CONST=Constitutional
```

**Detailed per-organ memory:**

**CROWN reads:**
- Working: current conversation context
- Episodic: relevant past interactions for context ("3 months ago you said...")
- Semantic: operator preferences (tone, length, language)
- Constitutional: what CROWN must never say or claim
- Error: known hallucination patterns to avoid

**NAMMU reads and writes:**
- Working: current input text, current routing decision
- Semantic: operator's shorthand lexicon, language patterns, domain weights
- Procedural: verified routing patterns for common phrase types
- Error: past misroutes and their corrections
- Constitutional: what NAMMU must never route (governance signals)

**OPERATOR reads and writes:**
- Working: current tool request, current tool result
- Technical: verified tool call patterns, API response shapes
- Procedural: verified multi-step tool sequences
- Episodic: past tool executions for context
- Error: past tool failures and their causes
- Constitutional: which tools require proposals, which are forbidden

**SENTINEL reads:**
- Working: current session threat score, recent inputs
- Semantic: known threat patterns, operator behavioral baseline
- Error: past security events and their resolutions
- Constitutional: what constitutes a threat, escalation thresholds

**GUARDIAN reads and writes:**
- Working: current pending proposals
- Episodic: past proposals and their outcomes
- Error: past governance violations
- Constitutional: all governance rules (primary consumer)

**ANALYST reads:**
- Working: current analysis request
- Episodic: relevant past decisions and outcomes
- Semantic: operator values, project knowledge, relationship knowledge
- Procedural: known analysis frameworks for this decision type
- Error: past analytical errors and corrections

---

## 5. Memory Consolidation Pathways

Memory moves between layers through governed consolidation.
This is the Memory Promotion Law made concrete.

```
                                                  ┌─────────────────┐
                                                  │ CONSTITUTIONAL  │
                                                  │    MEMORY       │
                                                  │ (permanent law) │
                                                  └────────┬────────┘
                                                           │ Guardian proposal only
                                                           │
              ┌─────────────────┐          ┌──────────────▼──────────────┐
              │ PROCEDURAL      │◄─────────│      SEMANTIC MEMORY        │
              │ MEMORY          │ ANALYST  │   (what is generally true)  │
              │ (how to do it)  │ verifies │ Operator approval required  │
              └─────────────────┘          └──────────────▲──────────────┘
                                                           │ ANALYST consolidates
                                                           │ Operator approves
              ┌─────────────────┐          ┌──────────────┴──────────────┐
              │ CODE / TECH     │◄─────────│      EPISODIC MEMORY        │
              │ MEMORY          │ OPERATOR │   (what happened, decided)  │
              │ (how to build)  │ verifies │ Operator approval required  │
              └─────────────────┘          └──────────────▲──────────────┘
                                                           │ Session consolidation
                                                           │ 1-3 candidates/session
                                                           │ CROWN proposes
              ┌─────────────────┐          ┌──────────────┴──────────────┐
              │ ERROR MEMORY    │◄─────────│       WORKING MEMORY        │
              │ (what failed)   │ Automatic│   (active session context)  │
              │ Never deleted   │ no apprvl│   Ephemeral, in-memory      │
              └─────────────────┘          └─────────────────────────────┘
```

**Transition rules:**

| From | To | Trigger | Governance |
|---|---|---|---|
| Working | Episodic | Session end, CROWN proposes | Operator approval |
| Working | Error | Any organ failure | Automatic, no approval |
| Working | Code | OPERATOR verifies success × 3 | OPERATOR flags, Operator approves |
| Episodic | Semantic | ANALYST detects pattern | ANALYST proposes, Operator approves |
| Semantic | Procedural | Proven executable workflow | ANALYST verifies, Operator approves |
| Any | Constitutional | Guardian decision | Full Guardian proposal process |
| Episodic | Episodic | Contradiction detected | ANALYST flags, Operator resolves |

---

## 6. Memory Cross-Organ Exchange (Breathing)

You asked: *"How can this be defined with a structural memory that can breathe between organs with full understanding?"*

The answer is the **Memory Exchange Protocol**.

Each organ can read from the shared memory substrate within its permissions.
Each organ can write to the shared memory substrate through governed pathways.
The "breathing" is the continuous flow of memory between organs
during normal operation.

**The breathing cycle — one session turn:**

```
Operator: "hola tengo emails urgentes?"
    │
    ▼
NAMMU reads:
  - Working: current input
  - Semantic: operator's language patterns → detects Spanish
  - Semantic: shorthand lexicon → checks for known shorthands
  - Procedural: "urgentes" → email_read_inbox(urgency_only=True) pattern
  ↓ routes to: email_read_inbox
    │
    ▼
SENTINEL reads:
  - Working: current threat score for session
  - Error: past injection attempts in email content
  - Semantic: operator behavioral baseline
  ↓ clears: no threat
    │
    ▼
GUARDIAN reads:
  - Constitutional: email_read_inbox requires no proposal
  ↓ allows execution
    │
    ▼
OPERATOR reads:
  - Technical: verified ThunderbirdDirectReader call pattern
  - Procedural: email_read → comprehension → CROWN pattern
  ↓ executes: ThunderbirdDirectReader.read_inbox(urgency_only=True)
    │
    ▼
    [Reads real emails from MBOX — Layer 2, external data source]
    │
    ▼
MEMORY (comprehension layer) writes:
  - Working: tool result (8 emails, 2 urgent)
  - Technical: if new API behavior detected, updates Code Memory
    │
    ▼
CROWN reads:
  - Working: tool result
  - Semantic: operator preference → short responses
  - Episodic: "Matxalen" context from past interactions
  ↓ generates: natural response in Spanish, urgent emails first
    │
    ▼
SESSION writes:
  - Working: adds this turn to conversation history
  - Error: nothing failed, no write needed
    │
    ▼
End of turn — memory has "breathed" across 7 organs
```

---

## 7. Memory Bus Architecture

To make the breathing concrete in code, introduce a **MemoryBus**:

```python
class MemoryBus:
    """
    The cross-organ memory exchange system.

    Every organ accesses memory through the MemoryBus.
    The MemoryBus enforces:
      - Organ-level read permissions (per the permission table in §4)
      - Write governance (automatic vs approval-required)
      - Layer routing (each write goes to the correct layer)
      - Audit trail for all writes

    Organs do not access memory stores directly.
    All memory access passes through the MemoryBus.
    """

    def read(
        self,
        organ: str,
        layer: MemoryLayer,
        query: str,
        n_results: int = 5,
    ) -> list[MemoryRecord]:
        """
        Semantic search across the specified layer,
        filtered to records this organ is permitted to read.
        """

    def write(
        self,
        organ: str,
        layer: MemoryLayer,
        record: MemoryRecord,
        requires_approval: bool | None = None,
    ) -> str | None:
        """
        Write a record to the specified layer.
        Returns memory_id if written immediately.
        Returns None if sent to GUARDIAN for approval.
        Auto-determines requires_approval from layer rules if not specified.
        """

    def consolidate(
        self,
        organ: str,
        session_events: list[dict],
    ) -> list[MemoryRecord]:
        """
        End-of-session consolidation.
        Extract candidates from session_events.
        Return candidates for CROWN to propose storing.
        """
```

---

## 8. Storage Architecture Per Layer

```
data/realms/{realm_id}/memory/
  ├── working/              ← In-memory only (not on disk)
  │
  ├── code/                 ← Technical memory
  │   ├── operator.json     ← Tool call patterns per organ
  │   ├── nammu.json        ← Routing patterns
  │   └── index/            ← ChromaDB collection
  │
  ├── errors/               ← Error memory
  │   ├── {organ}.jsonl     ← Append-only per organ
  │   └── index/            ← ChromaDB collection
  │
  ├── episodic/             ← Episodic memory
  │   ├── records.jsonl     ← Ground truth (human-readable)
  │   ├── entity_index.json ← Fast lookup by entity name
  │   └── index/            ← ChromaDB collection
  │
  ├── semantic/             ← Semantic memory
  │   ├── facts.jsonl       ← Ground truth facts
  │   ├── nammu_profile.json ← NAMMU's semantic model of operator
  │   └── index/            ← ChromaDB collection
  │
  ├── procedural/           ← Procedural memory
  │   ├── {organ}.json      ← Verified procedures per organ
  │   └── index/            ← ChromaDB collection
  │
  ├── constitutional/       ← Constitutional memory
  │   ├── foundational_laws.md
  │   ├── operator_covenant.md
  │   └── memory_promotion_law.md
  │
  └── tombstones.jsonl      ← Deletion audit trail
```

**Key principle:** Every layer has two representations:
1. A human-readable ground truth (JSONL or JSON) — the unambiguous truth
2. A vector index (ChromaDB) — fast semantic retrieval

If the vector index is ever lost, it can be rebuilt from the ground truth.
The ground truth is never deleted.

---

## 9. The Error Memory — Special Treatment

Error Memory deserves its own section because it is the most neglected
and the most valuable layer for building systems that improve over time.

**What must be captured for every error:**

```python
@dataclass
class ErrorRecord:
    error_id: str
    organ: str                      # which organ encountered the error
    timestamp: str
    error_type: str                 # "tool_failure" | "misroute" | "hallucination"
                                    #   | "timeout" | "security_event" | "code_error"
    error_message: str              # the actual error
    context: dict                   # what was happening when it failed
    input_that_caused_it: str       # the operator input (first 100 chars)
    stack_trace: str | None         # for code errors
    correction_applied: str | None  # what fixed it
    lesson_learned: str | None      # human-readable: what to do differently
    recurrence_count: int           # how many times this error has occurred
    resolved: bool                  # has a correction been confirmed?
    resolution_id: str | None       # links to the correction in semantic memory
```

**Why recurrence_count matters:**
If the same error occurs 5+ times, ANALYST should surface it:
"This error has occurred 7 times. The pattern suggests X.
Proposed lesson: always check Y before calling Z."

This is how the system learns from its own failures —
not through training, but through governed Error Memory.

---

## 10. Memory for the Multi-Agent Platform

When INANNA NYX runs on a multi-agent platform, the MemoryBus
becomes the shared substrate for all agents.

```
Agent: NAMMU-Builder
  reads: Code Memory (how tools are implemented)
  reads: Error Memory (what broke before)
  writes: Code Memory (new verified patterns)

Agent: ANALYST-Reviewer
  reads: Episodic Memory (past decisions)
  reads: Semantic Memory (operator values)
  writes: Semantic Memory (new derived facts, with approval)

Agent: Guardian-Agent
  reads: Constitutional Memory
  reads: Error Memory (governance violations)
  writes: Constitutional Memory (only through formal proposal)

Agent: NAMMU-Operator (the AI running the system)
  reads: All layers (within permissions)
  writes: Working Memory (continuous)
  writes: Error Memory (automatic on failure)
```

**Each agent reads the Atlas before beginning.**
**Each agent reads the Error Memory for their organ before writing code.**
**Each agent reads the Procedural Memory for verified patterns.**

This prevents the most common multi-agent failure:
agents repeating mistakes that have already been learned.

---

## 11. The Memory Promotion Law — Complete Version

Building on the Human Operator Covenant, the Memory Promotion Law
defines exactly how memory moves between layers:

```
PROMOTION PATH              TRIGGER              GOVERNANCE
─────────────────────────────────────────────────────────────
Working → Error             Any failure          Automatic
Working → Episodic          Session end          CROWN proposes, Operator approves
Working → Code (tech)       OPERATOR verifies    Flagged, Operator approves
Episodic → Semantic         ANALYST detects      ANALYST proposes, Operator approves
Semantic → Procedural       Proven × 3           ANALYST verifies, Operator approves
Any → Constitutional        Guardian decision    Formal Guardian proposal process
─────────────────────────────────────────────────────────────
DEMOTION PATH               TRIGGER              GOVERNANCE
─────────────────────────────────────────────────────────────
Semantic → Episodic         Contradiction found  ANALYST flags, Operator resolves
Semantic → Error            Fact proven wrong    ANALYST flags, Operator approves
Constitutional ← change     NEVER automatic      Cannot be demoted, only amended
─────────────────────────────────────────────────────────────
SCOPE PROMOTION             TRIGGER              GOVERNANCE
─────────────────────────────────────────────────────────────
Private → Realm             Operator requests    Operator consent + Realm governor
Realm → Communal            Realm governance     Collective governance vote
Private → Communal          NEVER direct         Must go through Realm first
─────────────────────────────────────────────────────────────
```

---

## 12. Implementation Sequence

**Phase 1 — Error Memory (highest value, lowest complexity):**
Create `core/memory_error.py` with `ErrorRecord`, `ErrorMemory`.
Wire automatic error capture in all organs.
Create `core/memory_bus.py` with read/write/consolidate.
This immediately gives the system institutional memory of its failures.

**Phase 2 — Technical Memory for OPERATOR:**
Create per-organ technical memory in `data/realms/default/memory/code/`.
OPERATOR records successful tool patterns after verification.
Read at session start — speeds up routing for known task types.

**Phase 3 — Episodic Memory (vector-backed):**
Upgrade existing `core/memory.py` to use ChromaDB.
Session consolidation: CROWN proposes 1-3 candidates.
Entity indexing for "what do I know about Matxalen?"

**Phase 4 — Semantic Memory:**
ANALYST consolidates episodic patterns into semantic facts.
Knowledge graph for entity relationships.
NAMMU operator profile merges into Semantic Memory.

**Phase 5 — Procedural Memory:**
OPERATOR records verified multi-step sequences.
NAMMU records verified routing patterns.
Both searchable by task type.

**Phase 6 — MemoryBus (unification):**
All organs access memory through `MemoryBus`.
Audit trail for all memory operations.
Cross-organ memory exchange fully governed.

---

## 13. What This Changes About Everything

Once this Memory Architecture is implemented, every organ improves
continuously — not through retraining, but through governed memory:

**NAMMU improves** because it reads Procedural Memory of verified routing patterns.
Novel phrasings that previously failed get added as patterns.

**CROWN improves** because it reads Error Memory of its own hallucinations.
Known hallucination triggers are avoided in future prompts.

**OPERATOR improves** because it reads Technical Memory of verified tool sequences.
Multi-step workflows that worked before are reused exactly.

**ANALYST improves** because it reads Episodic Memory of past decisions.
Pattern recognition improves with every session.

**SENTINEL improves** because it reads Error Memory of past attacks.
New threat signatures are added after each security event.

**The whole system improves** because memory breathes between organs —
each organ's learning becomes available to all others,
within the governed boundaries of the Memory Promotion Law.

This is the difference between a system that is configured
and a system that learns.

---

## 14. Evaluation Criteria

1. Can any organ retrieve a relevant past error before repeating it?
2. Can NAMMU route a novel phrase by matching it to a verified procedural pattern?
3. Can CROWN say "you decided X three months ago" accurately?
4. Does a private memory never appear in another operator's retrieval?
5. Does every memory write have an audit trail?
6. Can the vector index be rebuilt entirely from ground truth JSONL?
7. Does the system get demonstrably better at common tasks over time?

If the answer to question 7 is "not measurably" after 3 months of use,
the consolidation thresholds need adjustment.

---

*Design Specification version 2.0 · 2026-04-25*
*Written by: Claude (Command Center)*
*Confirmed by: INANNA NAMMU (Guardian)*
*This document supersedes 06_memory_design_spec.md*
*The previous specification treated memory as a single organ.*
*This specification treats memory as the nervous system of the whole.*
