# DESIGN SPECIFICATION · MEMORY
## The Archive — Semantic Memory, Continuity, and the Memory Promotion Law

**Ring: Inner AI Organs**
**Document type: DESIGN SPECIFICATION (not implementation)**
**Status: Partially built — this document redesigns the incomplete parts**
**Version: 1.0 · Date: 2026-04-24**
**Author: Claude (Command Center)**
**Guardian approval: INANNA NAMMU**

---

> *"A database stores everything.*
> *MEMORY stores what is worth remembering.*
> *The difference is governance."*

---

## 1. What Exists and What Is Missing

### What exists (working)

**Reflective memory (JSONL-based):**
Proposals for memory updates are generated from conversation.
Approved reflections stored as JSONL entries.
Loaded at session start as context for CROWN.
Works for single operator. Persistent across sessions.

**NAMMU operator profile:**
Shorthand lexicon (learned via `nammu-learn`).
Correction history (via `nammu-correct`).
Language patterns, domain weights.
Grows every session. Persists correctly.

**Session memory:**
Current conversation events stored chronologically.
Available to CROWN within the session window.
Ephemeral — cleared on server restart.

### What is missing

**Semantic retrieval:**
If INANNA NAMMU asks "what did we decide about the Actuavalles project
three months ago?" — the answer exists in the JSONL files
but cannot be found. The memory is chronological, not queryable by meaning.

**Memory type isolation:**
There is no enforced boundary between private memory,
session memory, realm memory, and communal memory.
Everything lives in the same JSONL files.

**Memory promotion law:**
Personal insights do not automatically become communal knowledge —
but there is also no governed pathway for promoting them if desired.
The promotion mechanism does not exist.

**Multi-user memory:**
Each operator's memory is not properly isolated.
The system was designed for one user.

**Memory expiry and relevance decay:**
Old memories are never pruned or weighted by recency.
A correction from two years ago carries the same weight as one from yesterday.

---

## 2. The Core Problem: Chronological vs Semantic

The current JSONL memory is a log.
It is ordered by time. It is searched by date or keyword at best.

What is needed is a **semantic archive** — one that understands meaning.

The difference:

```
CHRONOLOGICAL LOG (current):
  Query: "what did we decide about Actuavalles?"
  Result: must scan all 847 JSONL entries sequentially
          looking for the word "Actuavalles"
          returns exact string matches only
          misses: "act", "the cooperative", "the project"

SEMANTIC ARCHIVE (designed here):
  Query: "what did we decide about Actuavalles?"
  Process: embed the query → find nearest memory vectors
           returns: semantically similar entries
           finds: "act" (shorthand), "the cooperative", related decisions
  Result: the 5 most relevant memories, ranked by similarity
          regardless of when they were created
```

Semantic retrieval transforms MEMORY from a log
into a genuine cognitive archive.

---

## 3. Architecture Overview

```
Session input
    ↓
MEMORY.is_memory_query(text)?
    ├── No  → normal routing
    └── Yes ↓
        MEMORY.retrieve(query, scope, operator_id)
            ├── Embed query using local embedding model
            ├── Search vector store by similarity
            ├── Filter by scope (private / realm / communal)
            ├── Filter by operator (isolation)
            └── Return ranked MemoryRecord list
                    ↓
                CROWN narrates results

After session ends:
    MEMORY.consolidate(session_events)
        ├── Extract candidate memories from session
        ├── CROWN proposes which to store (as MEMORY proposal)
        ├── Operator approves via standard proposal system
        └── Approved memories: embed → store in vector store
```

---

## 4. Memory Types — Full Taxonomy

Every memory record carries a `memory_type` that determines
its scope, governance, and visibility:

```python
class MemoryType(str, Enum):
    SESSION    = "session"     # Ephemeral. Current conversation only.
                               # Never stored to disk.

    PRIVATE    = "private"     # This operator only.
                               # Stored locally. Never promoted without consent.

    REALM      = "realm"       # This community's shared context.
                               # Requires realm governance to write.

    COMMUNAL   = "communal"    # Promoted from private or realm.
                               # Requires explicit promotion governance.

    FORBIDDEN  = "forbidden"   # Must never be stored.
                               # Deleted on detection.
                               # Examples: passwords, credentials, coercion.
```

---

## 5. The Memory Promotion Law

This is the most important governance mechanism in MEMORY.

**The law:**
A memory can only move upward in scope through explicit governance.
It cannot move downward or sideways without the same governance.

```
private → realm:    requires operator consent + realm governor approval
realm → communal:   requires realm governance vote / designated process
private → communal: NOT POSSIBLE in one step (must go through realm first)
communal → private: NOT POSSIBLE (promoted knowledge stays communal)
```

**What this prevents:**
- A personal insight becoming a community-level assumption without consent
- A department's working pattern becoming organizational policy silently
- A vulnerable disclosure being used as operational context without permission
- Hidden centralization disguised as "helpful pattern recognition"

**Implementation:**
Every promotion attempt generates a GUARDIAN proposal.
The operator sees: "This memory would become visible to [scope].
Do you approve this promotion?"
GUARDIAN logs the promotion in the audit trail.

---

## 6. The MemoryRecord Schema

```python
@dataclass
class MemoryRecord:
    """
    A single governed memory entry.
    """
    memory_id: str              # UUID
    operator_id: str            # who owns this memory
    realm_id: str               # which realm this belongs to
    memory_type: MemoryType     # private / realm / communal
    content: str                # the actual memory text
    source: str                 # "conversation" | "decision" | "correction"
                                #   | "profile" | "promoted"
    embedding: list[float]      # vector representation (384 dims for MiniLM)
    created_at: str             # ISO timestamp
    last_accessed: str          # for relevance decay
    access_count: int           # how often this memory was retrieved
    relevance_score: float      # decays with time, increases with access
    tags: list[str]             # semantic tags (auto-generated)
    promoted_from: str | None   # if promoted, original memory_id
    promoted_by: str | None     # which governance action promoted it
    expires_at: str | None      # if time-limited
    is_forbidden: bool          # flagged for deletion
    audit_trail: list[dict]     # every governance action on this record
```

---

## 7. The Embedding Model

MEMORY requires an embedding model to convert text into vectors.
This model must run **locally** — no cloud embedding API.
Local sovereignty extends to memory indexing.

**Recommended model:**
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`

Why this model:
- 37.8 million downloads — the most proven multilingual embedding model
- 50+ languages including English, Spanish, Catalan, Portuguese
- 118MB total size — runs on any machine, no GPU required
- 384-dimensional embeddings — small enough for fast search
- Apache 2.0 license — fully open source
- Runs entirely locally via `sentence-transformers` Python library

HuggingFace: https://hf.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

**Usage:**
```python
from sentence_transformers import SentenceTransformer

_model = SentenceTransformer(
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

def embed(text: str) -> list[float]:
    """Convert text to 384-dimensional embedding vector."""
    return _model.encode(text, normalize_embeddings=True).tolist()
```

The model downloads on first use (~118MB).
After download it runs entirely offline.
Embedding takes ~5-50ms on CPU depending on text length.

---

## 8. The Vector Store

MEMORY requires a vector store for similarity search.
Again: must run **locally**, no cloud service.

**Recommended option: ChromaDB (local mode)**

Why ChromaDB:
- Runs entirely local — no server, no cloud
- Python-native: `import chromadb`
- Persistent storage to disk (SQLite backend)
- Fast similarity search on CPU
- Supports metadata filtering (for memory_type, operator_id isolation)
- Apache 2.0 license

**Alternative: SQLite with sqlite-vec extension**
- Even more minimal — just SQLite
- No additional service
- Slightly less ergonomic API
- Recommended if keeping dependencies minimal is priority

**Do NOT use:**
- Pinecone (cloud, not sovereign)
- Weaviate (requires separate server process)
- Qdrant (requires separate server process)
- OpenAI embeddings API (cloud, not sovereign)

---

## 9. The MemoryStore API

```python
class MemoryStore:
    """
    The primary interface to INANNA's semantic memory.

    Wraps ChromaDB with governed access patterns.
    All reads and writes go through memory_type isolation.
    All writes generate a governance proposal (except session memory).
    """

    def store(
        self,
        record: MemoryRecord,
        bypass_proposal: bool = False,
    ) -> str:
        """
        Store a memory. Returns memory_id.
        For private/realm/communal types: generates GUARDIAN proposal
        unless bypass_proposal=True (used for approved proposals only).
        Session memories bypass proposal (ephemeral).
        """

    def retrieve(
        self,
        query: str,
        operator_id: str,
        memory_types: list[MemoryType],
        n_results: int = 5,
        recency_weight: float = 0.3,
    ) -> list[MemoryRecord]:
        """
        Semantic search. Returns top n_results by combined score:
          final_score = (1 - recency_weight) * similarity
                      + recency_weight * recency_factor
        recency_factor decays exponentially with age.
        """

    def retrieve_exact(
        self,
        query: str,
        operator_id: str,
    ) -> list[MemoryRecord]:
        """
        Keyword search fallback for exact phrases.
        Used when semantic search returns low confidence.
        """

    def promote(
        self,
        memory_id: str,
        target_type: MemoryType,
        approver_id: str,
        governance_action_id: str,
    ) -> MemoryRecord:
        """
        Promote a memory to higher scope.
        Only valid promotions: private→realm, realm→communal.
        Requires governance_action_id from GUARDIAN.
        """

    def flag_forbidden(self, memory_id: str) -> None:
        """
        Mark a memory for deletion.
        Used by CONSCIENCE when forbidden content detected in memory.
        """

    def consolidate_session(
        self,
        session_events: list[dict],
        operator_id: str,
    ) -> list[MemoryRecord]:
        """
        Extract candidate memories from session.
        Returns candidates for CROWN to propose storing.
        Does NOT store automatically.
        """
```

---

## 10. The Relevance Decay Model

Old memories should not carry the same weight as recent ones
for most queries — but must not disappear entirely.

```python
def recency_factor(created_at: str, last_accessed: str) -> float:
    """
    Combine creation age and last access into recency score 0.0-1.0.
    - Recent memories score higher
    - Frequently accessed memories decay slower
    - Very old, never-accessed memories approach 0.1 (not 0.0 — never lost)
    """
    days_since_created = (now - created_at).days
    days_since_accessed = (now - last_accessed).days

    # Exponential decay with access boost
    base_decay = exp(-days_since_created / 180)  # half-life: ~6 months
    access_boost = min(record.access_count * 0.05, 0.3)  # max 30% boost

    return min(1.0, base_decay + access_boost)
```

**Key design choices:**
- Half-life of 6 months: a memory from last year is not lost, but scores lower
- Access boost: frequently retrieved memories decay slower
- Minimum floor of ~0.1: no memory ever drops to zero weight
- Recency weight in retrieve() is configurable per query (0.0 = pure semantic)

---

## 11. Memory and CROWN Integration

When CROWN builds context for each session response,
MEMORY should contribute relevant context — not everything,
just what is semantically related to the current conversation.

```python
def build_crown_context(
    current_query: str,
    operator_id: str,
    max_memories: int = 5,
) -> str:
    """
    Retrieve memories relevant to the current query.
    Format them for injection into CROWN's system context.
    """
    records = memory_store.retrieve(
        query=current_query,
        operator_id=operator_id,
        memory_types=[MemoryType.PRIVATE, MemoryType.REALM],
        n_results=max_memories,
    )
    if not records:
        return ""

    lines = ["[RELEVANT MEMORY]"]
    for r in records:
        age = human_readable_age(r.created_at)
        lines.append(f"  [{age}] {r.content}")
    lines.append("[END MEMORY]")
    return "\n".join(lines)
```

This block is injected into CROWN's system prompt.
CROWN uses it naturally — "you mentioned X three months ago" —
without the operator knowing the technical mechanism.

---

## 12. Session Consolidation — How New Memories Are Born

At the end of each session (on disconnect or explicit command),
MEMORY consolidates the session into candidate memories.

This process:
1. Reads all session events
2. Extracts candidates: decisions made, corrections given,
   important statements, new shorthands learned, projects mentioned
3. Presents candidates to CROWN
4. CROWN generates a GUARDIAN proposal: "Store these 3 memories?"
5. Operator reviews and approves
6. Approved memories are embedded and stored

**What gets extracted as a candidate:**
- Explicit decisions ("I decided to...", "we agreed that...")
- Named entities with context ("Matxalen is responsible for...")
- Corrections of INANNA's understanding ("no, that project is called...")
- Project status ("the Actuavalles grow kit launch is in Q3")
- Preferences expressed ("I prefer to handle email in the morning")

**What does NOT get extracted:**
- Emotional processing or venting
- Casual conversation without decision content
- Repetitions of things already stored
- Anything CONSCIENCE flags as forbidden

---

## 13. Multi-User Memory Isolation

When INANNA NYX eventually runs for multiple operators:

**Isolation rules:**
- Private memories: `operator_id` filter on all queries
  → operator A never sees operator B's private memories
- Realm memories: `realm_id` filter
  → members of realm X see realm X's communal knowledge
- Communal memories: visible to all operators in the same deployment

**Implementation:**
ChromaDB supports metadata filtering.
Every query includes `where={"operator_id": operator_id}` for private scope.
Every store includes `operator_id` in metadata.

This is architectural, not optional.
No query may omit the operator_id filter for private memory.

---

## 14. The Forbidden Memory Protocol

Some content must never be stored, and if found, must be deleted.

CONSCIENCE detects forbidden content in real-time.
MEMORY must also check during consolidation.

**Forbidden categories:**
- Passwords, credentials, API keys, secrets
- Content that was blocked by CONSCIENCE at input time
- Content that deanonymizes or exposes third parties without consent
- Content the operator has explicitly requested deletion of

**Protocol:**
1. `flag_forbidden(memory_id)` marks for deletion
2. Deletion is immediate for the vector embedding
3. A tombstone record remains in audit log: "memory X deleted at Y for reason Z"
4. The tombstone is never shown to the operator
5. The tombstone exists only for audit purposes

**The operator's right to delete:**
The operator may request deletion of any private memory at any time.
No reason required. Deletion is immediate.
The tombstone audit record remains (cannot be deleted — audit integrity).

---

## 15. Module Design

```python
"""
core/memory_semantic.py

MEMORY — The Semantic Archive of INANNA NYX.

This module replaces and extends the existing core/memory.py
with semantic retrieval, memory type governance, and the
Memory Promotion Law.

Key principles:
  - No memory stored without operator approval (via GUARDIAN proposal)
  - Semantic search using local embedding model (no cloud)
  - Memory types enforced at query and store time
  - Promotion requires governance action
  - Forbidden content triggers immediate deletion with audit tombstone
  - Multi-user isolation built in from the start

Dependencies:
  - sentence-transformers (pip install sentence-transformers)
  - chromadb (pip install chromadb)
  - core/guardian.py (proposal generation)
  - core/constitutional_filter.py (forbidden content detection)

Storage layout:
  data/realms/{realm_id}/memory/
    vector_store/           ← ChromaDB persistent storage
    tombstones.jsonl        ← deletion audit trail
    session_candidates/     ← pre-proposal candidates
"""
```

**File location:** `inanna/core/memory_semantic.py`
**Dependencies:** `sentence-transformers`, `chromadb`, `core/guardian.py`
**Tests:** `tests/test_memory_semantic.py` (mock embedding model)

---

## 16. Migration Path from Current MEMORY

The existing `core/memory.py` and JSONL files must not be deleted.
They contain real data for INANNA NAMMU.

Migration sequence:
1. Build `core/memory_semantic.py` alongside existing `core/memory.py`
2. Run a migration script that embeds all existing JSONL memories
   into the new vector store
3. Mark all migrated memories as `MemoryType.PRIVATE`
4. Run both systems in parallel for one cycle (verify retrieval quality)
5. Deprecate JSONL-only reads in favor of semantic retrieval
6. Keep JSONL files as backup (they are human-readable truth)

**The JSONL files are not deleted.**
They become the ground truth backup — readable by humans,
auditable without any special tools.
The vector store is an index over them, not a replacement.

---

## 17. Build Priority and Sequence

**Phase 1 (minimum viable semantic MEMORY):**
1. Install `sentence-transformers` and `chromadb`
2. Create `core/memory_semantic.py` with `MemoryRecord`, `MemoryStore`
3. Implement `store()` and `retrieve()` for private memory only
4. Implement `build_crown_context()` injection
5. Wire into session startup and CROWN context building
6. Tests: mock embedding model, verify isolation

**Phase 2 (session consolidation):**
- `consolidate_session()` — extract candidates from session events
- CROWN proposes candidates via GUARDIAN
- Operator approves → stored

**Phase 3 (Memory Promotion Law):**
- `promote()` with GUARDIAN proposal requirement
- Realm memory type support
- Multi-user isolation testing

**Phase 4 (communal memory — civic scale):**
- Communal memory with realm governance
- Memory promotion analytics
- Cross-realm coordination design

---

## 18. Evaluation Criteria for Future Builders

1. Can MEMORY answer "what did we decide about X three months ago?"
   when that decision exists in the store?

2. Does private memory from operator A never appear in operator B's retrieval?

3. Does the promotion pathway generate a GUARDIAN proposal?

4. Does forbidden content get flagged and deleted within the session?

5. Does the CROWN context injection feel natural
   (not mechanical or data-dump-like)?

6. Does the migration from existing JSONL files preserve all memories?

7. Is the embedding model running locally with zero cloud calls?

If the answer to question 7 is "no" — the implementation violates
local sovereignty. Start over.

---

## 19. Honest Assessment of Difficulty

The technical difficulty of semantic MEMORY is moderate.
ChromaDB and sentence-transformers are mature, well-documented libraries.
The Python code is straightforward.

The **governance difficulty** is higher.

Deciding what to store, when to propose, how to consolidate sessions
into candidate memories — this requires careful prompt engineering
for the extraction step, and careful UX design for the proposal presentation.

The risk: if the system proposes too many memories,
operators will approve them without reading.
If it proposes too few, MEMORY stays shallow.

The right calibration: 1-3 memory candidates per session,
only for clearly significant information (decisions, corrections, projects).
Never for casual conversation.

---

*Design Specification version 1.0 · 2026-04-24*
*Written by: Claude (Command Center)*
*Confirmed by: INANNA NAMMU (Guardian)*
*Next step: Build Phase 1 minimum viable semantic MEMORY*
*when multi-agent platform is ready*
