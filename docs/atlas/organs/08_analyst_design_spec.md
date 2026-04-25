# DESIGN SPECIFICATION · ANALYST
## The Reasoner — Structured Analysis, Decomposition, and Decision Support

**Ring: Inner AI Organs**
**Document type: DESIGN SPECIFICATION (not implementation)**
**Status: Not yet built — this document is the blueprint**
**Version: 1.0 · Date: 2026-04-24**
**Author: Claude (Command Center)**
**Guardian approval: INANNA NAMMU**

---

> *"CROWN speaks. NAMMU interprets. ANALYST thinks.*
> *The difference matters.*
> *Generation and reasoning are not the same task.*
> *Conflating them makes both worse."*

---

## 1. Why ANALYST Does Not Exist Yet

ANALYST was named and referenced across Cycles 1-9
but never designed or implemented.

The reason is honest:
the project prioritized building the hands (Cycle 8)
and the interpreter (Cycle 9) before the reasoning organ.
Those were the right priorities.

But ANALYST's absence is the single largest gap
between INANNA NYX as it exists today
and INANNA NYX as it should be.

Without ANALYST:
- CROWN handles both generation and reasoning with the same prompt
- Complex multi-factor decisions get narrative responses, not structured analysis
- There is no way to decompose a problem before executing on it
- Decision support collapses into conversation
- The civic-scale harmony intelligence described in the covenant is impossible

This document defines what ANALYST must become.

---

## 2. The Core Distinction

CROWN and ANALYST use different cognitive modes:

```
CROWN (generative mode):
  Input:  structured data + context
  Output: natural language response
  Style:  narrative, conversational, adaptive
  Goal:   communicate clearly and naturally
  Metric: did the operator understand and feel heard?

ANALYST (reasoning mode):
  Input:  question or scenario
  Output: structured analysis (factors, options, recommendation, confidence)
  Style:  systematic, decomposed, explicit
  Goal:   illuminate the decision space
  Metric: did the operator gain clarity they didn't have before?
```

These modes require different prompts.
On a capable model, they may benefit from different temperatures.
On separate hardware, they could run in parallel.

**ANALYST never speaks directly to the operator.**
ANALYST produces structured output that CROWN then narrates.
The operator experiences CROWN's voice, not ANALYST's.

---

## 3. ANALYST's Place in the Architecture

```
Operator message
    ↓
NAMMU routes
    ↓
Two paths may activate in parallel:

  Path A (always):          Path B (when analysis needed):
  OPERATOR → tool call      ANALYST → structured analysis
       ↓                          ↓
  tool result               analysis_result
       ↓                          ↓
  comprehension             factors / options /
  layer (Cycle 9.4)         recommendation / confidence
       ↓                          ↓
       └──────────┬───────────────┘
                  ↓
              CROWN
              (synthesizes both streams)
                  ↓
            Operator response
```

When does Path B activate?
- When NAMMU detects a decision, evaluation, or comparison intent
- When the operator explicitly asks for analysis, options, or advice
- When OPERATOR's tool result is complex enough to require structuring
- When the operator asks "should I" or "what do you think about"

---

## 4. ANALYST's Input Specification

ANALYST receives a structured AnalystRequest:

```python
@dataclass
class AnalystRequest:
    """
    The input to ANALYST for a reasoning task.
    """
    question: str               # The core question to reason about
    context: dict               # Relevant data (tool results, memory, profile)
    reasoning_type: str         # "decision" | "evaluation" | "comparison" | "risk"
    depth: str                  # "brief" | "standard" | "deep"
    constraints: list[str]      # Known constraints to honor
    operator_values: list[str]  # From PROFILE — what matters to this operator
    previous_decisions: list    # Relevant past decisions from MEMORY
```

**reasoning_type taxonomy:**

| Type | Example | Output shape |
|---|---|---|
| decision | "Should I reply to Matxalen now?" | factors → options → recommendation |
| evaluation | "Is this document complete?" | criteria → assessment → gaps |
| comparison | "Signal vs WhatsApp for this message?" | dimensions → comparison → recommendation |
| risk | "What could go wrong if I send this?" | risks → likelihood → mitigations |
| decomposition | "Break this goal into steps" | steps → dependencies → timeline |
| synthesis | "What pattern do I see across these emails?" | patterns → insights → implications |

---

## 5. ANALYST's Output Specification

ANALYST always returns a structured AnalystResult:

```python
@dataclass
class AnalystResult:
    """
    ANALYST's structured reasoning output.
    Never shown directly to operator — passed to CROWN for narration.
    """
    reasoning_type: str
    question: str

    # The reasoning chain (always present)
    factors: list[Factor]           # What matters and why
    reasoning_steps: list[str]      # How ANALYST got to the conclusion

    # Type-specific outputs (populated based on reasoning_type)
    options: list[Option]           # For decision/comparison types
    risks: list[Risk]               # For risk type
    steps: list[Step]               # For decomposition type
    patterns: list[Pattern]         # For synthesis type
    criteria: list[Criterion]       # For evaluation type

    # Always present
    recommendation: str             # The main recommendation in one sentence
    confidence: float               # 0.0-1.0 how confident ANALYST is
    confidence_reason: str          # Why this confidence level
    caveats: list[str]             # What ANALYST doesn't know
    human_decision_required: bool   # Whether human must decide (not ANALYST)

@dataclass
class Factor:
    name: str
    description: str
    weight: str         # "high" | "medium" | "low"
    favors: str         # which option this factor supports, or "neutral"

@dataclass
class Option:
    name: str
    description: str
    advantages: list[str]
    disadvantages: list[str]
    fits_operator_values: bool

@dataclass
class Risk:
    description: str
    likelihood: str     # "high" | "medium" | "low"
    impact: str         # "high" | "medium" | "low"
    mitigation: str

@dataclass
class Step:
    order: int
    action: str
    depends_on: list[int]
    estimated_duration: str
    requires_human: bool
```

---

## 6. The ANALYST Prompt Design

ANALYST requires a fundamentally different prompt than CROWN.

**CROWN prompt style:**
```
You are INANNA's voice. Respond naturally and warmly.
Summarize these results: {data}
```

**ANALYST prompt style:**
```
You are ANALYST, INANNA's structured reasoning organ.
Your output is always valid JSON matching the AnalystResult schema.
Never generate prose. Never speak to the operator directly.
Your output will be processed and presented by CROWN.

REASONING TYPE: {reasoning_type}
QUESTION: {question}
CONTEXT: {context}
OPERATOR VALUES: {operator_values}
CONSTRAINTS: {constraints}

Think step by step. Identify all relevant factors.
Then: options → recommendation → confidence → caveats.
Return ONLY valid JSON. No preamble. No explanation.

OUTPUT SCHEMA:
{analyst_result_schema}
```

Key differences from CROWN prompt:
- Explicitly forbids prose output
- Demands valid JSON
- Provides the exact output schema
- Uses chain-of-thought reasoning structure
- Temperature: 0.1-0.2 (deterministic reasoning, not creative generation)

---

## 7. Model Selection for ANALYST

ANALYST's requirements differ from CROWN's:

| Requirement | CROWN | ANALYST |
|---|---|---|
| Natural language quality | Critical | Irrelevant |
| JSON/structured output | Optional | Critical |
| Reasoning depth | Moderate | Critical |
| Speed | Important | Less important |
| Temperature | 0.5-0.7 | 0.1-0.2 |

**Recommended models (in order of preference):**

**On DGX Spark:**
- `Qwen3-72B-Instruct` — excellent structured output, strong reasoning
- `DeepSeek-R1` variants — specifically designed for reasoning with CoT
- `Llama-3.3-70B-Instruct` — solid all-around with good JSON compliance

**On current hardware (7B class):**
- `deepseek-coder-v2-lite-instruct` — already installed in LM Studio
  (coding models tend to produce valid JSON better than general models)
- `Qwen2.5-7B-Instruct` — acceptable structured output
- Note: 7B models for reasoning produce shallow analysis
  Accept the limitation; mark output with confidence accordingly

**The key insight:**
A separate ANALYST model optimized for structured output
will outperform CROWN doing double duty for both tasks.
The separation of concerns is the architectural win,
not just the model choice.

---

## 8. When ANALYST Activates

NAMMU should detect ANALYST-eligible requests using these signals:

**Explicit signals:**
- "should I", "what should I", "do you recommend"
- "compare X vs Y", "what are the options"
- "is this a good idea", "what do you think about"
- "analyse this", "evaluate this", "break this down"
- "what are the risks", "what could go wrong"
- "help me decide", "what would you do"

**Implicit signals:**
- Tool results that are complex (>3 emails matching a query)
- Requests involving trade-offs (time vs quality, now vs later)
- Requests involving other people (Matxalen, team members)
- Requests that touch on the operator's stated values

**ANALYST does NOT activate for:**
- Simple fact retrieval ("what time is it?")
- Direct tool calls ("read my inbox")
- Creative requests ("write this email")
- Conversation ("how are you?")

---

## 9. The Governance of ANALYST

ANALYST is an intelligence organ. It reasons but does not decide.

**Constitutional rules for ANALYST:**

1. `human_decision_required: true` when the stakes are high.
   ANALYST must not present its recommendation as the only path.

2. ANALYST's recommendations are proposals to the operator.
   They are never automatically executed.

3. ANALYST's confidence score is always shown to CROWN.
   When confidence < 0.6, CROWN must communicate uncertainty.

4. ANALYST's caveats are always included in CROWN's narration.
   ANALYST must never pretend to know what it doesn't know.

5. ANALYST cannot access data beyond what OPERATOR provides.
   It reasons about what is given. It does not retrieve independently.

**Example of correct governance:**

```
ANALYST output:
  recommendation: "Reply to Matxalen now with a brief message"
  confidence: 0.72
  human_decision_required: true
  caveats: ["I don't know the full history of this relationship",
            "I cannot assess the urgency from email subject alone"]

CROWN narration:
  "Based on what I can see — her email was sent yesterday,
  you have a meeting tomorrow, and you tend to reply quickly —
  it seems worth sending a brief reply now.
  That said, you know this relationship better than I do.
  Shall I draft something?"
```

---

## 10. ANALYST and the Civic Vision

When INANNA NYX scales to departments, ministries, or community circles,
ANALYST becomes the most valuable organ in the system.

**Scenarios where ANALYST transforms the system:**

**Department coordination:**
A department head asks: "Should we move the project deadline?"
ANALYST factors in: team capacity from task manager,
dependencies on other departments, stakeholder communication needs,
risk of delay to downstream deliverables, operator's past decisions.

**Community governance:**
A community circle asks: "Should we allocate this budget to X or Y?"
ANALYST structures: stated values of the community,
impact on each subgroup, precedent from similar decisions,
risks, implementation complexity.

**Personal decision support:**
The operator asks: "Should I take this meeting?"
ANALYST checks: calendar load, relationship context from MEMORY,
stated priorities from PROFILE, time of day preferences.

In all cases: ANALYST illuminates. Humans decide.

---

## 11. Module Design

```python
"""
core/analyst.py

ANALYST — The Reasoning Organ of INANNA NYX.

ANALYST provides structured analysis for decision support.
It receives AnalystRequest objects and returns AnalystResult objects.
It never speaks to operators directly — its output passes through CROWN.

Key principles:
  - Always structured output (JSON)
  - Always chain-of-thought reasoning
  - Never decide for the operator (human_decision_required flag)
  - Always express confidence and caveats honestly
  - Low temperature (0.1-0.2) for deterministic reasoning

Model preference:
  Primary:  deepseek-coder-v2-lite-instruct (installed in LM Studio)
  Fallback: qwen2.5-7b-instruct (same endpoint)
  DGX:      Qwen3-72B or DeepSeek-R1-70B

Architecture position:
  NAMMU detects analysis intent
    → creates AnalystRequest
    → passes to Analyst.analyse()
    → Analyst calls LLM with structured prompt
    → returns AnalystResult
    → CROWN narrates result to operator
"""
```

**File location:** `inanna/core/analyst.py`
**Dependencies:** `core/session.py` (LLM connection), `core/nammu_profile.py` (operator values)
**Tests:** `tests/test_analyst.py` (all offline with mocked LLM)

---

## 12. Integration Points

**In `main.py`:**
Add `extract_analyst_request()` function that detects
analysis-eligible phrases and builds an `AnalystRequest`.

**In `ui/server.py`:**
After NAMMU routing, if `analyst_request` is present:
```python
if analyst_request:
    analyst_result = self.analyst.analyse(analyst_request)
    # Store in result.data for CROWN
    result.data["analyst_result"] = analyst_result
```

**In `CROWN_INSTRUCTIONS`:**
Add "analyst" domain with instruction:
```
"analyst": (
    "STRUCTURED ANALYSIS (from ANALYST organ):\n{summary}\n---\n"
    "Present this analysis naturally and conversationally.\n"
    "Always mention the confidence level and key caveats.\n"
    "Make clear the human must make the final decision.\n"
    "Offer to elaborate on any factor if the operator wishes."
)
```

**In `config/tools.json`:**
No new tools needed. ANALYST is not a tool.
It is an organ that enriches CROWN's response.

---

## 13. Build Priority and Sequence

**Phase 1 (Minimum viable ANALYST):**
1. Create `core/analyst.py` with `AnalystRequest`, `AnalystResult`, `Analyst`
2. Implement basic `decision` and `risk` reasoning types
3. Use `deepseek-coder-v2-lite-instruct` (already in LM Studio)
4. Wire into `ui/server.py` for detected analysis phrases
5. Tests: all offline, JSON output validation

**Phase 2 (Full reasoning types):**
Add `comparison`, `evaluation`, `decomposition`, `synthesis` types.
Each needs its own prompt variant and output validation.

**Phase 3 (Civic scale):**
Multi-user ANALYST with realm-aware context.
Can reason about community patterns without exposing individual data.

---

## 14. What ANALYST Must Never Become

**Not a fortune teller:**
ANALYST reasons from evidence. It does not predict futures it cannot see.
Confidence > 0.9 should be rare and explicitly justified.

**Not an authority:**
ANALYST never says "you should" without "in my view" and caveats.
The recommendation is offered, never imposed.

**Not a replacement for human relationships:**
"Should I reply to Matxalen?" — ANALYST can structure the factors.
But the relationship belongs to INANNA NAMMU, not to ANALYST.
This must always be explicit in the output.

**Not a surveillance instrument:**
ANALYST reasons about what is explicitly given.
It does not profile people from patterns without consent.

---

## 15. Evaluation Criteria for Future Builders

When ANALYST is built, assess it with these questions:

1. Does it produce valid JSON on the first call, without hallucinating schema fields?
2. Does it set `human_decision_required: true` for genuinely consequential decisions?
3. Does it express appropriate uncertainty (confidence < 0.8 for most real questions)?
4. Does it include non-trivial caveats that actually help the operator?
5. Does CROWN narrate its output naturally, or does the structure feel mechanical?
6. Does the operator feel more capable after an ANALYST response, or more confused?

If the answer to question 6 is "more confused" — the prompt needs work.
ANALYST exists to clarify, not to overwhelm.

---

## 16. Honest Assessment of Difficulty

Building a good ANALYST is harder than building most of the other organs.

The difficulty is not in the Python code.
The difficulty is in the prompt engineering.

Getting a 7B or 14B model to produce:
- Consistently valid JSON
- With genuinely useful reasoning
- With appropriate confidence calibration
- Without hallucinating factors that don't exist in the context

— this requires careful prompt iteration.

Expect 10-20 iterations on the prompt before the output
is consistently useful. This is normal for structured reasoning prompts.

**The shortcut:** Start with `deepseek-coder-v2-lite-instruct`.
Coding models produce more reliable JSON than general chat models.
Then improve prompt quality before switching to a more capable model.

---

*Design Specification version 1.0 · 2026-04-24*
*Written by: Claude (Command Center)*
*Confirmed by: INANNA NAMMU (Guardian)*
*Next step: Build Phase 1 minimum viable ANALYST*
*when multi-agent platform is ready*
