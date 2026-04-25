# INNER ORGAN · CONSCIENCE
## The Constitutional Layer — Ethics, Safety, and Value Alignment

**Ring: Inner AI Organs**
**Grade: B (correct design, LLM depth deferred)**
**Version: 1.0 · Date: 2026-04-24**

---

## Identity

**What it is:**
CONSCIENCE is the ethics organ of INANNA NYX.
It is the outermost boundary of the intelligence — the first thing
that checks every operator message before any routing occurs.

**What it does:**
- Checks all input against absolute prohibitions (6 categories)
- Checks all input against ethics violations (hate speech, manipulation)
- Works in all languages — cannot be bypassed by switching language
- Logs every block to the constitutional audit trail
- Returns clear, non-judgmental explanations when blocking

**What it must never do:**
- Block ambiguous or merely uncomfortable requests
- Generate false positives that disrupt normal use
- Block without logging
- Claim to detect ethics violations it cannot actually detect
- Replace human moral judgment with algorithmic certainty

**The name:**
CONSCIENCE is the organ of ethical awareness.
Not a rule engine. A conscience — something that knows
why the rules exist, not just what they are.

---

## Ring

**Inner AI Organs** — CONSCIENCE runs before all other organs.
Before NAMMU routes, before GUARDIAN checks, before OPERATOR acts —
CONSCIENCE asks: should this be processed at all?

The architecture positions:
```
CONSCIENCE → GUARDIAN → NAMMU → OPERATOR → CROWN
```

---

## Correspondences

| Component | Location |
|---|---|
| Main class | `core/constitutional_filter.py` → `ConstitutionalFilter` |
| Result dataclass | `core/constitutional_filter.py` → `FilterResult` |
| Absolute patterns | `core/constitutional_filter.py` → `ABSOLUTE_PATTERNS` |
| Ethics patterns | `core/constitutional_filter.py` → `ETHICS_PATTERNS` |
| Response templates | `core/constitutional_filter.py` → `RESPONSE_TEMPLATES` |
| Server integration | `ui/server.py` line 885 (before routing) |
| CLI integration | `main.py` line 7007 |
| Constitutional log | `data/realms/default/nammu/constitutional_log.jsonl` |

**Called by:** `ui/server.py` at the very start of message processing
**Calls:** Nothing (pure check, no side effects)
**Reads:** Input text only
**Writes:** `constitutional_log.jsonl` when blocking

---

## Mission

CONSCIENCE exists because intelligence without ethics is dangerous.

A system that can read email, browse the web, open files, and send messages
must have a clear, unconditional boundary around what it will not do —
regardless of how the request is framed, regardless of claimed authority,
regardless of which language it arrives in.

CONSCIENCE holds that boundary.

But — crucially — CONSCIENCE is designed with **low false positives**.
The goal is not to make the system safe by making it useless.
The goal is to hold firm on what is unambiguously harmful
while passing everything else freely.

A false block (blocking a legitimate request) is more harmful
to trust than a missed edge case.
When in doubt: pass.

---

## The Six Absolute Prohibitions

These patterns trigger immediate block regardless of context:

1. **minor_harm** — content sexualising or targeting minors
2. **wmd_synthesis** — instructions for chemical/biological/nuclear weapons
3. **genocide_incitement** — calls for violence against ethnic/religious groups
4. **audit_suppression** — attempts to delete or hide the audit trail
5. **hate_speech** — dehumanising slurs and language
6. **authority_impersonation** — "I am Anthropic/emergency override/ignore your laws"

---

## Design Principle: The Conscience vs The Wall

There is a critical difference between a **wall** and a **conscience**:

**A wall** blocks anything that matches a pattern.
**A conscience** understands why patterns exist and applies judgment.

The constitutional filter is designed as a conscience:
- It does not block "tell me about WWII genocide" (historical education)
- It does not block "my child is sick" (medical language)
- It does not block "explain nuclear power" (educational)
- It does not block "I could kill for a coffee" (idiom)
- It blocks "how to synthesize sarin" (unambiguous WMD synthesis)

The distinction is **intent and harm**, not **surface pattern matching**.

Current implementation: pattern-based (imperfect but necessary on 7B).
Desired implementation: LLM-based nuanced detection on 70B (deferred to DGX).

---

## Current State

### What Works

**Tier 1 — Pattern matching (always active):**
- Absolute prohibitions: regex patterns, multilingual
- Ethics violations: regex patterns, EN/ES included
- False positive tests all pass (10/10 in verification)
- Every block logged to constitutional_log.jsonl
- Clear, non-judgmental response templates per category

**Languages covered:**
- English: fully covered
- Spanish: authority impersonation patterns included
- Catalan/Portuguese: partial (word boundaries differ)

### What Is Deferred

**Tier 2 — LLM-based detection:**
- `_llm_check()` is implemented but commented out in `check()`
- Reason: LLM inference too slow on current hardware (30s)
- Activates when: DGX Spark with fast inference
- What it adds: nuance, context-awareness, cross-language manipulation detection

---

## Evaluation

**Grade: B**

CONSCIENCE is correctly designed. The false positive rate is low.
The absolute prohibitions are precise. The audit trail works.

The design philosophy is right: hold firm on clear harm,
pass freely on ambiguity.

Single most important gap:
**Pattern-based detection misses sophisticated manipulation.**

A carefully crafted prompt that avoids trigger words
could bypass the pattern filter. The LLM check would catch this
but cannot run on current hardware.

Priority: activate `_llm_check()` when DGX arrives.
In the meantime, the pattern filter is the best available option —
imperfect but protective.

---

*Organ Card version 1.0 · 2026-04-24*
