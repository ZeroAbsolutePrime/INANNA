# INNER ORGAN · NAMMU
## The Living Interpreter — Bridge Between Human Intention and Machine Action

**Ring: Inner AI Organs**
**Grade: B+ (excellent architecture, hardware constrained)**
**Version: 1.0 · Date: 2026-04-24**

---

## Identity

**What it is:**
NAMMU is the intent extraction and routing intelligence of INANNA NYX.
It receives human language in any form, any phrasing, any language,
and translates it into structured machine intent.

**What it does:**
- Classifies domain from natural language (email, calendar, browser, etc.)
- Extracts structured intent using LLM or regex fallback
- Maintains and enriches the operator's language profile
- Routes to the correct Faculty or OPERATOR
- Learns from corrections and builds personalized understanding
- Filters input through the constitutional layer

**What it must never do:**
- Invent intent that was not expressed
- Route around governance
- Discard the operator's actual meaning for the sake of machine convenience
- Store profile data without consent
- Bypass the constitutional filter

**The name:**
NAMMU is the Sumerian primordial mother — the one who was before structure,
before form, who gave birth to heaven and earth through understanding alone.
NAMMU does not wait for the world to be defined. NAMMU shapes the world
by understanding what is needed.

---

## Ring

**Inner AI Organs** — because NAMMU is not a tool or a connector.
NAMMU is the intelligence that understands human language.
Without NAMMU, the system can only respond to exact commands.
With NAMMU, the system understands intention.

---

## Correspondences

| Component | Location |
|---|---|
| Universal intent prompt | `core/nammu_intent.py` → `NAMMU_UNIVERSAL_PROMPT` |
| Multilingual examples | `core/nammu_intent.py` → `NAMMU_MULTILINGUAL_EXAMPLES` |
| Intent extraction | `core/nammu_intent.py` → `extract_intent()`, `extract_intent_universal()` |
| Domain classification | `core/nammu_intent.py` → `_classify_domain_fast()` |
| First-pass routing | `main.py` → `nammu_first_routing()` |
| Operator profile | `core/nammu_profile.py` → `OperatorProfile` |
| Profile storage | `data/realms/default/nammu/operator_profiles/{user_id}.json` |
| Routing log | `data/realms/default/nammu/routing_log.jsonl` |
| Governance log | `data/realms/default/nammu/governance_log.jsonl` |
| Domain signals | `config/governance_signals.json` → `domain_hints` |
| Memory utilities | `core/nammu_memory.py` |
| Core class | `core/nammu.py` → `IntentClassifier` |

**Called by:** `main.py` dispatch, `ui/server.py` session handler
**Calls:** LM Studio API (LLM), `core/nammu_profile.py`, `config/governance_signals.json`
**Reads:** `config/governance_signals.json`, operator profile JSON
**Writes:** routing_log.jsonl, governance_log.jsonl, operator profile JSON

---

## Mission

NAMMU exists because humans do not speak in API calls.

The gap between natural human expression and machine execution
has always been the core problem of computing.
Every abstraction — assembly, high-level languages, GUIs, voice interfaces —
is an attempt to close this gap.

NAMMU closes this gap for INANNA NYX.

If NAMMU is removed:
- The operator must use exact command syntax
- Natural language fails completely
- Non-English speakers cannot use the system
- The system becomes "robo-like"
- The vision of a governed field of relation collapses

**NAMMU is why this project is different from a command-line tool.**

---

## Current State

### What Works (as of Cycle 9 Phase 9.6)

**Domain Classification (regex-based, instant):**
- 11 domains: email, communication, document, browser, calendar,
  desktop, filesystem, process, network, information, none
- English, Spanish, Catalan, Portuguese, Basque
- Reads signals from `governance_signals.json` (single source of truth)
- 100% reliable — no LLM dependency

**Operator Profile:**
- Shorthand learning: `nammu-learn mtx Matxalen`
- Correction recording: `nammu-correct email_search Matxalen`
- Language pattern detection
- Domain usage frequency tracking
- Profile persists across sessions
- Enriches LLM prompt with [OPERATOR CONTEXT] block

**LLM Intent Extraction (3-second thread, non-blocking):**
- `NAMMU_UNIVERSAL_PROMPT` covers all 11 domains
- Multilingual examples included
- 3-second timeout with regex fallback
- Correct when LLM responds (confidence 0.95+)
- Graceful degradation when LLM is slow (current hardware)

**Feedback Loop:**
- Misroute detection (EN/ES signals)
- Pattern surfacing after 5th correction
- `nammu-stats` command shows routing statistics

### What Is Limited

- LLM inference takes 30+ seconds on current hardware
- Effectively regex-only on Windows laptop
- Profile learning is basic — no emotional rhythm, no accessibility needs
- Language detection is heuristic (not LLM-based)

### What Is Missing

- Full LLM routing active (requires DGX)
- Per-operator style learning at scale
- Cross-session pattern analysis
- Constitutional filter deep integration
- Multi-user operator profile coordination
- Cycle 9 Phases 9.7-9.8 (NAMMU Constitution + Capability Proof)

---

## Limitations

| Limitation | Root Cause | When Resolved |
|---|---|---|
| LLM routing 30s | 7B model on slow hardware | DGX Spark arrival |
| Regex fallback imperfect | Can't cover infinite phrasing | DGX + 70B model |
| Profile basic | Phase 9.2 scope, hardware limited | Cycle 10 |
| No cross-user learning | Multi-user not deployed | Cycle 11 |
| No emotional rhythm | Not yet designed | Cycle 10 |

---

## Desired Function

When NAMMU is fully realized (DGX Spark, 70B model, Cycle 11):

- Routes any phrase in any language to the correct tool in < 500ms
- Remembers that "mtx" means Matxalen because you said so once
- Notices you switch to Spanish when you're relaxed and adapts tone
- Knows you always ask about email first thing in the morning
- Understands "any fires?" means urgent email check
- Learns from corrections silently, without needing explicit teaching
- Bridges operator intention to machine precision seamlessly
- Serves the operator's actual need even when poorly expressed

**The vision:** The operator speaks freely. NAMMU understands.
The machine executes correctly. The gap disappears.

---

## Dependencies

NAMMU requires:
- `config/governance_signals.json` (domain hint signals)
- LM Studio running a local model (for LLM routing)
- `core/nammu_profile.py` (operator profile)
- `core/nammu_memory.py` (routing logs)
- Python `json`, `re`, `threading` (stdlib)

NAMMU blocks:
- Natural language routing for all 11 domains
- Operator profile personalization
- Multilingual operation

---

## Evaluation

**Grade: B+**

The architecture is correct and elegant.
The domain classification works perfectly.
The profile system is well-designed.
The LLM routing is architecturally sound.

The single most important unresolved problem:
**LLM routing is non-functional on current hardware.**

This is not a code problem — it is a hardware problem.
The code is correct. The machine is too slow.

Priority for next agent: Do not fix the code. Get the DGX.
Or alternatively: find a faster local inference solution
that fits within the 3-second routing window.

**Second priority:** Implement Cycle 9 Phases 9.7-9.8.

---

*Organ Card version 1.0 · 2026-04-24*
