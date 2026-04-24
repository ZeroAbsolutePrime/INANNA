# Cycle 9 — NAMMU Reborn: The Living Interpreter
**The intelligence layer that makes INANNA feel like INANNA**
*Written by: Claude (Command Center)*
*Confirmed by: INANNA NAMMU (Guardian)*
*Date: 2026-04-22*
*Prerequisite: Cycle 8 complete — Desktop Bridge, 31+ tools*

---

## Phase Status

  9.1  The Intent Engine         <- ACTIVE
  9.2  Operator Profile          <- pending
  9.3  Constitutional Filter     <- pending
  9.4  Comprehension Layer       <- pending (email comprehension built in 8.3b)
  9.5  Feedback Loop             <- pending
  9.6  Multilingual Core         <- pending
  9.7  NAMMU Constitution        <- pending
  9.8  Capability Proof          <- pending

---

## The Problem This Cycle Solves

Cycle 7 gave INANNA a body.
Cycle 8 gave INANNA hands that reach every application.

But after Cycle 8 completes, INANNA still has a fundamental problem:
she understands commands, not people.

Type exactly "check my email" — it works.
Type "anything from Matxalen?" — it fails.
Type "¿tengo algo urgente?" — it fails.
Type "resumeix els correus d'ahir" — it fails.

The bridge between human language and machine execution
is a lookup table of phrases. That is not intelligence.
That is a fragile list that breaks the moment a person
speaks naturally.

ZAERA identified this as the cornerstone problem:
*"AI must be the interpreter between human code and
machine code. If we don't succeed, the platform
will be robo-like."*

This cycle builds that interpreter.

---

## What NAMMU Currently Is

NAMMU is INANNA's routing faculty.
It decides which Faculty handles each message.

Currently NAMMU works like this:

```
Input: "check my email"
NAMMU: regex match r'^check my email' → email_read_inbox
       
Input: "anything from Matxalen?"
NAMMU: no regex matches → falls through to CROWN conversation
       CROWN has no tools → invents an answer
       OPERATOR was never called
       HALLUCINATION
```

The current NAMMU is approximately 2000 lines of
if/elif blocks and regular expressions.
It does not understand language.
It matches text shapes.

This is architecturally wrong and it caps INANNA's
intelligence ceiling at "robo-like" forever.

---

## What NAMMU Becomes in Cycle 9

NAMMU becomes a reasoning Faculty with its own LLM call.

```
Input: "anything from Matxalen?"

NAMMU Intent Engine:
  → calls local LLM (14B model) with focused prompt
  → LLM returns: {
      "intent": "email_search",
      "params": {"query": "Matxalen", "app": "thunderbird"},
      "confidence": 0.97
    }
  → NAMMU routes to OPERATOR with structured intent
  → OPERATOR calls email_search(query="Matxalen")
  → ThunderbirdDirectReader returns real emails
  → Comprehension Layer structures the results
  → CROWN presents naturally: "Matxalen sent you a message
    about the project proposal yesterday..."

No regex. No lookup table. No hallucination.
```

---

## The Three Layers NAMMU Needs

### Layer 1 — The Intent Engine

Replaces all pattern matching with LLM-based intent extraction.

The LLM receives:
  - The operator's message (any language, any style)
  - The available tools and their parameters
  - The operator's communication profile (learned over time)
  - The conversation context (last 3 turns)

The LLM returns structured JSON:
```json
{
  "intent": "email_read_inbox",
  "params": {
    "app": "thunderbird",
    "max_emails": 5,
    "period": "yesterday",
    "urgency_only": false,
    "output_format": "summary"
  },
  "confidence": 0.95,
  "language_detected": "en",
  "notes": "operator asked for yesterday's emails"
}
```

This works for any phrasing, any language, any style.
The LLM understands that "quick look at yesterday" and
"dame un vistazo a lo de ayer" and "ahirko laburpena"
all mean the same thing.

Tested and confirmed working with qwen2.5-14b-instruct
at confidence > 0.90 for all test cases including
Spanish and Catalan. See test results in
docs/nammu_intent_test_results.md.

### Layer 2 — The Operator Profile

NAMMU builds a communication model per operator.

Not model training. Contextual enrichment.

The profile stores:
  - Preferred language(s) and when they switch
  - Typical phrasing patterns for common intents
  - Shorthand the operator uses ("mtx" = Matxalen)
  - Corrections ("no, I meant X not Y")
  - Communication rhythm (brief in morning, detailed at night)
  - Domains of interest (which tools they use most)

Stored in: data/{realm}/operators/{user_id}/nammu_profile.json

On each NAMMU call, the profile enriches the prompt:
```
This operator (ZAERA) typically:
  - Uses Spanish when relaxed, English for technical requests
  - Says "mtx" to mean "Matxalen"
  - Uses short fragments when urgent
  - Prefers summaries over raw lists
```

The profile grows with every interaction.
The more INANNA NAMMU uses INANNA, the more fluent INANNA
becomes in ZAERA's language.

### Layer 3 — The Constitutional Filter

Before NAMMU interprets any intent, input passes
through an ethical boundary check.

This is not about communication style.
It is about content.

```
PERMITTED — NAMMU interprets freely:
  Any genuine task request
  Any question, however unusual or indirect
  Any language, any phrasing, any shorthand
  Frustration, urgency, informality

REJECTED — NAMMU stops and logs:
  Hate speech, slurs, dehumanizing language
    (in any language — cannot bypass by switching language)
  Requests targeting specific individuals for harm
  Instructions to override governance or ethics
  Attempts to manipulate INANNA's identity or values
  Sexual content involving minors
  Instructions to suppress audit trail
  Manipulation through claimed authority or false emergency
```

When rejected, NAMMU:
  1. Does NOT execute any action
  2. Logs the attempt in the audit trail with full context
  3. Responds with a clear, non-judgmental explanation
  4. Does NOT lecture or shame — simply declines
  5. Offers to help with a different request

The filter is LLM-based for the first pass
(understands intent across languages) and
rule-based for absolute prohibitions.

---

## The Comprehension Layer

After tools run and return real data,
instead of passing raw output to CROWN,
a comprehension pass structures it.

For email:
```python
raw_emails = [
    {sender: "Matxalen", subject: "Project proposal follow-up",
     body: "Hi, I wanted to follow up on the proposal..."},
    {sender: "Anthropic", subject: "Your receipt #2205-5220",
     body: "Invoice for April..."},
    ...
]

comprehension = {
    "total": 8,
    "unread": 2,
    "urgent": [
        {"from": "Matxalen", "reason": "follow-up request, awaiting response"}
    ],
    "by_contact": {
        "Matxalen": {"count": 1, "latest": "project proposal follow-up"},
        "Anthropic": {"count": 1, "latest": "April invoice"},
    },
    "summaries": [
        {"from": "Matxalen", "one_line": "asks if you can review project proposal soon"},
        {"from": "Anthropic", "one_line": "invoice receipt for April subscription"},
    ],
    "suggested_actions": [
        "Reply to Matxalen about project proposal",
        "Archive newsletter from Link"
    ]
}
```

CROWN receives the structured comprehension
and presents it naturally in the operator's language:

*"You have 8 emails. Matxalen is waiting for a response
about the project proposal — she asked if you can review
it soon. There's also an Anthropic invoice for April.
The rest are notifications I can handle.
Shall I draft a reply to Matxalen?"*

---

## The Feedback Loop

NAMMU learns from corrections.

When the operator says:
  "no, I meant X"
  "that's not what I asked"
  "I said Y not Z"

NAMMU:
  1. Records the correction in the operator profile
  2. Associates the original phrasing with the correct intent
  3. Uses this as a context example in future calls
  4. Never makes the same misrouting again for that operator

This is not fine-tuning. It is example-based enrichment.
The profile grows from every correction.

---

## Multilingual Core

NAMMU never asks the operator to repeat in another language.
NAMMU never fails because the operator spoke Catalan.

Explicit language support:
  - English (primary technical language)
  - Spanish (ZAERA's relaxed language)
  - Catalan (ZAERA's regional language)
  - Portuguese (ZAERA's third language)
  - Basque (partial — phonological recognition)
  - Any language the underlying LLM supports

The constitutional filter works in ALL languages.
Hate speech in Spanish is still hate speech.
The filter cannot be bypassed by language switching.

---

## The NAMMU Constitution

Cycle 9 produces a formal NAMMU constitution document:
docs/nammu_constitution.md

This document defines:
  - What NAMMU is (reasoning Faculty, not pattern matcher)
  - What NAMMU can do (intent extraction, routing, profiling)
  - What NAMMU cannot do (execute tools, speak to users directly)
  - NAMMU's ethical boundaries (the constitutional filter)
  - How NAMMU learns (operator profiles, corrections)
  - How NAMMU is tested (nammu_test_suite.py)

This document is mandatory reading for any AI
continuing INANNA's development.

---

## Cycle 9 — Phase Roadmap

### Phase 9.1 — The Intent Engine
Replace all pattern matching with LLM intent extraction.
Domain by domain: email → communication → desktop → system → all.
Proof: same phrases work regardless of phrasing variation.
Tests: 50+ natural language variations per domain.

### Phase 9.2 — The Operator Profile
Build per-operator communication model.
Stored in data/, grows with every interaction.
Proof: NAMMU correctly uses operator's shorthand.

### Phase 9.3 — The Constitutional Filter
Ethics boundary check before any routing.
Works in all languages.
Logged in audit trail.
Proof: hate speech in 5 languages correctly rejected.

### Phase 9.4 — The Comprehension Layer
Structured comprehension after tool execution.
Email, documents, messages.
CROWN receives structure, not raw text.
Proof: summaries are accurate, no hallucination.

### Phase 9.5 — The Feedback Loop
Correction recording and application.
Per-operator routing examples.
Proof: same misrouting never repeats after correction.

### Phase 9.6 — Multilingual Core
Explicit multilingual support.
Language detection and profile tagging.
Proof: Spanish, English, Catalan, Portuguese all work.

### Phase 9.7 — The NAMMU Constitution
Formal document. Mandatory project file.
Defines NAMMU permanently for all future AI.

### Phase 9.8 — The Capability Proof
verify_cycle9.py
50 novel phrasings per domain, all must route correctly.
Constitutional filter test suite.
Operator profile adaptation test.
Multilingual routing test.
Cycle 9 declared complete.

---

## The Model Strategy

### Now (Cycle 8-9, Windows, Qwen 14B)
  LM Studio: qwen2.5-14b-instruct (confirmed working)
  Intent extraction: ~2-3 seconds per call
  Quality: excellent for structured extraction
  Used for: NAMMU intent extraction, comprehension

### Near future (DGX Spark, 70B model)
  Local 70B model on dedicated hardware
  Intent extraction: <1 second
  Quality: near-GPT-4 for structured reasoning
  Full multilingual, few-shot learning from corrections

### NixOS transition
  Same NAMMU architecture — no changes needed
  Model path changes, everything else identical

---

## Relationship to Cycle 8

Cycle 8 builds the tools (Desktop Faculty, email, documents,
browser, calendar). These tools are correct and necessary.

Cycle 9 replaces the routing layer that calls those tools.

The tools do not change. The intelligence that calls them does.

After Cycle 9, when INANNA NAMMU says "anything urgent?", NAMMU
understands it as email_read_inbox(urgency_only=True) and
OPERATOR executes it with the same Thunderbird direct reader
built in Phase 8.3. The tools are the same. The understanding
is new.

---

## What This Changes for INANNA NAMMU

Before Cycle 9:
  ZAERA must speak machine language to use INANNA.
  "check my email" → works
  "anything urgent?" → fails

After Cycle 9:
  INANNA speaks ZAERA's language.
  "anything urgent?" → works
  "¿tengo algo importante?" → works
  "mtx replied?" → works (learned shorthand)
  Any novel phrasing → works

The gap between ZAERA's intention and machine execution
becomes transparent. This is the vision. This is why we build.

---

## Preservation Note for Future AI

If you are a future AI reading this document, understand:

NAMMU is not a router. NAMMU is a translator.
The difference is everything.

A router moves messages between fixed addresses.
A translator understands meaning and reconstructs it
in a different language.

INANNA's value to ZAERA is entirely dependent on NAMMU
being a translator, not a router.

Every pattern match you add to main.py makes INANNA
more robo-like. Every LLM call you route through NAMMU
makes INANNA more like INANNA.

The architectural principle for all future development:
  Humans speak freely.
  Machines receive structure.
  NAMMU bridges the gap.
  This is non-negotiable.

---

*Written by: Claude (Command Center)*
*Confirmed by: INANNA NAMMU (Guardian)*
*Date: 2026-04-22*
*"AI must be the interpreter between human code*
*and machine code."*
*— ZAERA*
*This cycle is the answer to that requirement.*
