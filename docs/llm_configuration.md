# LLM Configuration — INANNA NYX
**The intelligence substrate of the platform**
*Written by: Claude (Command Center)*
*Confirmed by: ZAERA (Guardian)*
*Date: 2026-04-20*
*This document must be updated whenever a model is added, changed, or removed.*

---

## Active Model Configuration

INANNA NYX runs on a local LM Studio server at http://localhost:1234/v1
using the OpenAI-compatible REST API.

The server hosts multiple models simultaneously, each serving a specific
Faculty with its own charter, governance rules, and purpose.

---

## Model Registry

### Model 1 — qwen2.5-7b-instruct-1m
**Provider:** Qwen / Alibaba Cloud
**Format:** GGUF (quantized for local inference)
**Size:** ~4.68 GB
**Context window:** 1M tokens
**API identifier:** qwen2.5-7b-instruct-1m
**LM Studio source:** bartowski/Qwen2.5-7B-Instruct-GGUF

**Serves these Faculties:**
- CROWN — Primary conversational voice
- ANALYST — Structured reasoning and analysis
- OPERATOR — Bounded tool execution
- GUARDIAN — System observation

**Why this model for these Faculties:**
Qwen2.5-7B-Instruct-1M provides an exceptional context window (1 million tokens)
that allows CROWN to ground every response in the full history of approved memory
without truncation. For conversational and analytical tasks it is fast, warm,
and contextually rich. The 1M context is the defining capability here.

---

### Model 2 — qwen2.5-14b-instruct
**Provider:** Qwen / Alibaba Cloud
**Format:** GGUF Q3_K_S quantization
**Size:** 6.66 GB
**API identifier:** qwen2.5-14b-instruct
**LM Studio source:** bartowski/Qwen2.5-14B-Instruct-GGUF

**Serves these Faculties:**
- SENTINEL — Cybersecurity analysis, threat assessment, vulnerability reasoning

**Why this model for SENTINEL:**
Security domain reasoning demands more depth than a 7B model provides.
Qwen2.5-14B has nearly double the parameters, enabling deeper threat modeling,
more accurate CVE reasoning, better understanding of network security concepts,
and more nuanced risk assessment. The Q3_K_S quantization keeps the file size
manageable while preserving the reasoning quality advantage over the 7B.

SENTINEL's governance rules (passive analysis only, no working exploits,
responsible disclosure emphasis) are enforced at the system prompt level
regardless of which model is used. The 14B model is more capable of
following these nuanced instructions consistently.

---

### Model 3 — text-embedding-nomic-embed-text-v1.5
**Provider:** Nomic AI
**Format:** GGUF (embedding model)
**API identifier:** text-embedding-nomic-embed-text-v1.5

**Current use:** Loaded and available in LM Studio.
**Planned use:** Semantic memory search in Cycle 6 (Relational Memory layer).
When INANNA needs to find semantically relevant memories or profile entries,
this embedding model will power vector similarity search over the UserProfile
and session memory stores.

---

## Faculty → Model Mapping

```
CROWN     qwen2.5-7b-instruct-1m    general       active
ANALYST   qwen2.5-7b-instruct-1m    reasoning     active
OPERATOR  qwen2.5-7b-instruct-1m    tools         active
GUARDIAN  qwen2.5-7b-instruct-1m    governance    active
SENTINEL  qwen2.5-14b-instruct      security      active
```

All model assignments are configured in:
  inanna/config/faculties.json

The model_url and model_name fields in each Faculty entry determine
which model serves that Faculty. Changing the model requires only
updating faculties.json — no Python code changes needed.

---

## LM Studio Configuration

Server endpoint: http://localhost:1234/v1
Protocol: OpenAI-compatible REST API
Parallel slots: 4 per model
Idle TTL: 60 minutes (auto-evict inactive model from VRAM)

Both models are loaded simultaneously. LM Studio routes requests
to the correct model based on the model_name parameter in each API call.

---

## Future Model Roadmap

As specialized models mature and become available as GGUF:

| Faculty (planned) | Preferred model type | Phase |
|---|---|---|
| PYTHIA (research) | Large reasoning model (32B+) | Cycle 6 |
| AESCULAPIUS (clinical) | Medical-fine-tuned model | Cycle 6 |
| Semantic memory search | Nomic Embed (already loaded) | Cycle 6 |
| SENTINEL upgrade | Security-fine-tuned model when available | Future |

The Faculty architecture is model-agnostic by design. Every model change
is a one-line update to faculties.json. The governance layer works
identically regardless of which model serves each Faculty.

---

## The Principle

INANNA is not one intelligence. She is an orchestra.

Each Faculty is a distinct voice with its own purpose, charter,
and governance rules. The model beneath each Faculty is the instrument
that voice plays on. The instrument matters — a security analysis
deserves a deeper, more capable instrument than casual conversation.

But the identity of each Faculty is in its charter, not its model.
SENTINEL is SENTINEL because of what it will and will not do.
The 14B model makes it more capable of being SENTINEL well.

---

*This document must be updated whenever:*
*- A new model is loaded in LM Studio*
*- A Faculty's model assignment changes*
*- A new Faculty is added to faculties.json*
*- The embedding model is put into active use*
*Written by: Claude (Command Center)*
*Date: 2026-04-20*
