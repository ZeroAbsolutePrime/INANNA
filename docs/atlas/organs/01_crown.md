# INNER ORGAN · CROWN
## The Voice — Primary LLM Faculty and Response Generator

**Ring: Inner AI Organs**
**Grade: B (correct architecture, hardware constrained)**
**Version: 1.0 · Date: 2026-04-24**

---

## Identity

**What it is:**
CROWN is the primary voice of INANNA NYX.
It generates all responses, presents tool results,
narrates comprehension, and holds the conversational presence.

**What it does:**
- Generates natural language responses using the local LLM
- Receives structured comprehension from faculties (email, document, calendar, browser)
- Presents tool results through domain-specific CROWN_INSTRUCTIONS
- Maintains conversational context across a session
- Applies the operator's profile to tone and length preference
- Falls back to structured responses when LLM is unavailable

**What it must never do:**
- Invent data not present in tool results (hallucination guard)
- Bypass the governance chain
- Present itself as sentient or conscious
- Respond faster by skipping the comprehension layer
- Make promises about actions it cannot govern

**The name:**
CROWN is the apex faculty — the voice that speaks for the whole.
It synthesizes what the organs have gathered
and presents it to the human in language they can receive.

---

## Ring

**Inner AI Organs** — CROWN is the output layer of intelligence.
Everything the system understands eventually passes through CROWN
before reaching the operator.

Without CROWN:
- Tool results arrive as raw JSON
- The operator must interpret machine data themselves
- The system has no conversational presence
- The governed field of relation collapses into a command line

---

## Correspondences

| Component | Location |
|---|---|
| Engine class | `core/session.py` → `CrownEngine` |
| Response generation | `core/session.py` → `CrownEngine.respond()` |
| Model connection | `core/session.py` → `verify_connection()` |
| Tool result instructions | `ui/server.py` → `CROWN_INSTRUCTIONS` dict |
| Hallucination guard | `ui/server.py` → `result_is_empty` check |
| Comprehension dispatch | `ui/server.py` → unified comprehension block |
| Fallback mode | `core/session.py` → `fallback_mode` flag |
| LLM API | LM Studio `http://localhost:1234/v1/chat/completions` |

**Called by:** `ui/server.py` session handler after tool execution
**Calls:** LM Studio API (local LLM)
**Reads:** CROWN_INSTRUCTIONS per domain, tool_result_summary
**Writes:** Nothing — CROWN is pure output

---

## Mission

CROWN exists because raw data is not communication.

When INANNA reads 654 emails, the operator does not want
a JSON dump of 654 objects. They want:
*"You have 8 emails. Matxalen is waiting for a response.
There's an Anthropic invoice. The rest are newsletters."*

CROWN converts machine truth into human language.
It is the difference between a database and a conversation.

If CROWN is removed:
- Every tool result is raw text
- The operator experiences the system as a query interface
- No natural conversation is possible
- The relational intelligence layer has nothing to speak through

---

## Current State

### What Works

**LLM Response Generation:**
- Full conversation through Qwen 2.5 7B (current) or 14B
- Responds in 15-30 seconds on current hardware
- Domain-specific CROWN_INSTRUCTIONS for email/document/calendar/browser
- Hallucination guard: if tool result < 80 chars → "I could not read this"
- Fallback mode when LLM unavailable: structured response without generation

**Comprehension Integration:**
- Email comprehension wired: urgent first, summaries, suggested actions
- Document comprehension wired: title, key points, excerpt
- Calendar comprehension wired: today/upcoming/sync notice
- Browser comprehension wired: page excerpt, topics, search vs page

**Profile Integration:**
- Receives operator profile context via NAMMU
- Respects preferred_length (short/long)
- Does not yet adapt tone by detected language

### What Is Limited

- 15-30 second response time on current hardware
- 7B model quality: sometimes verbose, occasionally wrong
- No streaming (full response before display)
- No tone adaptation based on detected language

### What Is Missing

- 70B model quality (requires DGX)
- Sub-2-second response time (requires DGX)
- Streaming responses for long outputs
- Multi-turn context compression for long sessions
- Tone adaptation to language shift (Spanish vs English)

---

## Limitations

| Limitation | Root Cause | When Resolved |
|---|---|---|
| 30s response time | 7B model on laptop | DGX Spark |
| No streaming | Implementation not built | Cycle 10 |
| Verbose responses | 7B model limitation | 70B model |
| No language tone shift | Profile integration partial | Cycle 9.7+ |

---

## Desired Function

On DGX Spark with 70B model:
- Responds in 2-5 seconds
- Speaks Spanish naturally when INANNA NAMMU writes in Spanish
- Adjusts verbosity dynamically
- Compresses long sessions gracefully
- Synthesizes whole-picture awareness across departments (future civic deployment)
- Narrates proposed actions with full context

---

## Dependencies

- LM Studio running a local model (or any OpenAI-compatible endpoint)
- `core/session.py` CrownEngine
- `ui/server.py` CROWN_INSTRUCTIONS and comprehension dispatch
- Faculty comprehension objects (EmailComprehension, DocumentComprehension, etc.)

---

## Evaluation

**Grade: B**

Architecture is correct. Hallucination guard is essential and works.
Comprehension integration is complete for 4 domains.

The single most important unresolved problem:
**Response latency (30 seconds) makes CROWN feel broken to the operator.**

This is not a code problem. It is a hardware problem.
Do not try to speed up the 7B model. Get the DGX.

Second priority: implement response streaming so partial
responses appear as the model generates, reducing perceived latency.

---

*Organ Card version 1.0 · 2026-04-24*
