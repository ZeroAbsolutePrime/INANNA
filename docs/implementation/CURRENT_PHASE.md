# CURRENT PHASE: Cycle 9 - Phase 9.1 - The Intent Engine
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-22**
**Cycle: 9 - NAMMU Reborn: The Living Interpreter**

---

## MANDATORY READING — in this exact order

1. docs/nammu_vision.md              ← ESSENTIAL — read every word
2. docs/cycle9_master_plan.md
3. docs/platform_architecture.md
4. docs/cycle8_complete.md
5. docs/implementation/CURRENT_PHASE.md (this file)
6. CODEX_DOCTRINE.md
7. ABSOLUTE_PROTOCOL.md

**If you read nothing else: read docs/nammu_vision.md first.**
It defines what NAMMU is, what it must become, and why.
Every line of code in this cycle serves that vision.

---

## The Transition: Cycle 8 → Cycle 9

Cycle 8 built the tools. 41 tools. 11 categories.
Email, documents, browser, calendar, desktop.
The hands exist. The faculties exist.

Cycle 9 builds the intelligence that calls them.

Before Cycle 9:
  User: "anything from Matxalen?"
  NAMMU: regex tries to match → falls through → web_search
  Result: WRONG

After Cycle 9 Phase 9.1:
  User: "anything from Matxalen?"
  NAMMU: LLM extracts intent → email_search(query="Matxalen")
  Result: CORRECT — every time, any phrasing, any language

The core principle (from nammu_vision.md):
  Humans speak freely.
  Machines receive structure.
  NAMMU bridges the gap.
  LLM, not regex.

---

## Hardware Reality

Current machine: Windows laptop, Qwen 2.5 7B via LM Studio
LLM inference: ~30 seconds per call
Status: too slow for synchronous routing

DGX Spark (when it arrives): 70B model, ~500ms inference
Status: full NAMMU intelligence activates

This phase builds the correct architecture for both.
On current hardware: LLM runs in background thread, 3s timeout,
regex fallback if slow (already in place from Phase 8.3b/c).
On DGX: LLM responds in time, full intelligence.

The code written now works perfectly on DGX without changes.
The fallback ensures it works on current hardware too.
This is the principle: build for the DGX, run gracefully now.

---

## What Phase 9.1 Builds

Phase 9.1 replaces all regex pattern matching in the routing
layer with LLM-based intent extraction, domain by domain.

### The Scope

Phase 8.3b built NAMMU intent extraction for email and
communication only. Phase 9.1 extends it to ALL domains:
  - email / communication   (already done — enhance)
  - document                (new)
  - browser                 (new)
  - calendar                (new)
  - desktop                 (new)
  - filesystem              (new)
  - process / system        (new)

### The Architecture

```
User input
    ↓
NAMMU IntentEngine.extract(text, context)
    ↓  [3s thread timeout]
    ↓  [primary: qwen2.5-7b, timeout 20s]
    ↓  [fallback: regex if LLM slow]
IntentResult {
  intent: "email_search",
  params: {query: "Matxalen", app: "thunderbird"},
  confidence: 0.97,
  domain: "email",
  language: "en"
}
    ↓
OPERATOR executes tool
    ↓
CROWN presents result
```

---

## What You Are Building

### Task 1 — Expand nammu_intent.py to cover all domains

The existing nammu_intent.py covers email and communication.
Extend it to cover all 11 tool categories.

Create a unified NAMMU_UNIVERSAL_PROMPT that covers all domains:

```python
NAMMU_UNIVERSAL_PROMPT = """You are NAMMU, the intent extraction
core of INANNA NYX. Your only job: read the operator message and
return a JSON intent object. Never refuse. Never explain.
Return JSON only. Work in any language.

Available intents by domain:

EMAIL:
  email_read_inbox    {app, max_emails, period, urgency_only, output_format}
  email_search        {query, app, period}
  email_read_message  {subject_or_sender, app}
  email_compose       {to, subject, body, app}
  email_reply         {subject_or_sender, body, app}

COMMUNICATION:
  comm_read_messages  {app}
  comm_send_message   {app, contact, message}
  comm_list_contacts  {app}

DOCUMENT:
  doc_read            {path}
  doc_write           {path, content, title, format}
  doc_open            {path}
  doc_export_pdf      {path, output_dir}

BROWSER:
  browser_read        {url, js}
  browser_search      {query}
  browser_open        {url, browser}

CALENDAR:
  calendar_today      {}
  calendar_upcoming   {days}
  calendar_read_ics   {path}

DESKTOP:
  desktop_open_app    {app}
  desktop_read_window {app_name, max_depth}
  desktop_click       {label, app_name}
  desktop_type        {text, submit}
  desktop_screenshot  {app_name}

FILESYSTEM:
  read_file           {path}
  write_file          {path, content}
  list_dir            {path, pattern}
  search_files        {path, pattern}
  file_info           {path}

PROCESS:
  list_processes      {filter}
  run_command         {command, working_dir}
  system_info         {}
  kill_process        {pid, name}

NETWORK:
  ping                {host}
  resolve_host        {host}
  scan_ports          {host, ports}

INFORMATION:
  web_search          {query}

NONE:
  none                {} (not a tool request — conversation)

Return exactly:
{"intent":"...","params":{...},"confidence":0.0-1.0,"domain":"..."}
IMPORTANT: JSON only. No markdown. No explanation. No prose.

Examples:
"anything from Matxalen?" → {"intent":"email_search","params":{"query":"Matxalen","app":"thunderbird"},"confidence":0.97,"domain":"email"}
"read ~/report.pdf" → {"intent":"doc_read","params":{"path":"~/report.pdf"},"confidence":0.99,"domain":"document"}
"search the web for NixOS" → {"intent":"browser_search","params":{"query":"NixOS"},"confidence":0.98,"domain":"browser"}
"what's on my calendar today" → {"intent":"calendar_today","params":{},"confidence":0.99,"domain":"calendar"}
"open firefox" → {"intent":"desktop_open_app","params":{"app":"firefox"},"confidence":0.97,"domain":"desktop"}
"list my documents folder" → {"intent":"list_dir","params":{"path":"~/Documents"},"confidence":0.95,"domain":"filesystem"}
"hello how are you" → {"intent":"none","params":{},"confidence":0.99,"domain":"none"}"""
```

Key changes to nammu_intent.py:
  - Add NAMMU_UNIVERSAL_PROMPT alongside NAMMU_EMAIL_PROMPT
  - Extend IntentResult: add `domain` field
  - Extend extract_intent() to use universal prompt for non-email
  - Add domain detection: classify input domain before LLM call
    (fast heuristic — avoids LLM call for clearly-domain inputs)
  - Update _has_email_comm_signal → _classify_domain(text)

### Task 2 — Replace domain-specific routing in main.py

Currently main.py has separate extract_*_tool_request()
functions per domain, all using regex patterns.

Phase 9.1 adds a NAMMU-first pre-routing pass:

```python
def nammu_first_routing(
    text: str,
    conversation_context: list | None = None,
) -> dict | None:
    """
    Try NAMMU LLM intent extraction first.
    Returns tool_request dict if confident, None to fall through to regex.
    Runs in 3s background thread — never blocks routing.
    """
    domain = _classify_domain_fast(text.lower())
    if domain == "none":
        return None   # Pure conversation — skip LLM entirely

    import threading
    result_box = [None]
    def _run():
        result_box[0] = extract_intent_universal(text, conversation_context)
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=3.0)

    r = result_box[0]
    if r and r.success and r.confidence >= 0.75:
        return r.to_tool_request()
    return None   # Fall through to existing regex routing
```

Add `_classify_domain_fast(text_lower)`:
```python
def _classify_domain_fast(text: str) -> str:
    """Fast domain classification without LLM.
    Returns domain name or 'none'."""
    # Check each domain's signal words
    if any(w in text for w in EMAIL_SIGNALS):     return "email"
    if any(w in text for w in COMM_SIGNALS):      return "communication"
    if any(w in text for w in DOC_SIGNALS):       return "document"
    if any(w in text for w in BROWSER_SIGNALS):   return "browser"
    if any(w in text for w in CAL_SIGNALS):       return "calendar"
    if any(w in text for w in DESKTOP_SIGNALS):   return "desktop"
    if any(w in text for w in FS_SIGNALS):        return "filesystem"
    if any(w in text for w in PROC_SIGNALS):      return "process"
    if any(w in text for w in NET_SIGNALS):       return "network"
    if any(w in text for w in INFO_SIGNALS):      return "information"
    return "none"
```

Signal word lists use the existing governance_signals.json
entries. No duplication — read from the same source.

### Task 3 — Wire nammu_first_routing into the dispatch chain

In main.py _run_routed_turn() or equivalent dispatch:

```python
# NAMMU-first: try LLM intent extraction
# Falls through gracefully if LLM is slow or unavailable
tool_request = nammu_first_routing(text, conversation_context)

if tool_request:
    # NAMMU succeeded — execute directly
    result = execute_tool_request(tool_request)
    return build_tool_response(result)

# Fall through to domain-specific regex routing
# (existing extract_email_tool_request, etc.)
tool_request = (
    extract_email_tool_request(text, ...) or
    extract_document_tool_request(text, ...) or
    extract_browser_tool_request(text, ...) or
    ...
)
```

### Task 4 — Extend IntentResult with domain field

In nammu_intent.py:
```python
@dataclass
class IntentResult:
    intent: str
    params: dict = field(default_factory=dict)
    confidence: float = 0.0
    domain: str = ""           # ← NEW
    language_detected: str = "en"
    model_used: str = ""
    latency_ms: float = 0.0
    raw_response: str = ""
    error: Optional[str] = None
```

### Task 5 — Update help_system.py

Add a section to the help panel explaining natural language:

```
  NATURAL LANGUAGE (speak freely)
    INANNA understands your intent regardless of phrasing.
    You do not need exact commands. Examples:

    "anything from Matxalen?"        finds her emails
    "¿tengo algo urgente?"           checks urgent emails (Spanish)
    "resumeix els correus d'ahir"    yesterday's emails (Catalan)
    "read ~/proposal.pdf"            reads a document
    "search the web for NixOS"       web search
    "what's on my calendar?"         today's events
    "open firefox"                   opens Firefox
    "list my downloads"              filesystem listing

    On fast hardware: NAMMU uses full LLM understanding.
    On slow hardware: NAMMU uses intelligent regex fallback.
    Both produce correct results. Speed differs.
```

### Task 6 — Update identity.py

CURRENT_PHASE = "Cycle 9 - Phase 9.1 - The Intent Engine"

### Task 7 — Update docs/cycle9_master_plan.md

Add a status section at the top:
```
## Phase Status
  9.1  The Intent Engine    ← ACTIVE
  9.2  Operator Profile     ← pending
  9.3  Constitutional Filter ← pending
  9.4  Comprehension Layer  ← pending (email comprehension built in 8.3b)
  9.5  Feedback Loop        ← pending
  9.6  Multilingual Core    ← pending
  9.7  NAMMU Constitution   ← pending
  9.8  Capability Proof     ← pending
```

### Task 8 — Tests

Create inanna/tests/test_intent_engine.py (25 tests):

All tests mock the LLM call — no actual LLM calls in tests.

  - IntentResult has domain field with default ""
  - extract_intent_universal called with universal prompt
  - _classify_domain_fast("check my email") returns "email"
  - _classify_domain_fast("read ~/report.pdf") returns "document"
  - _classify_domain_fast("search the web for X") returns "browser"
  - _classify_domain_fast("what's on my calendar") returns "calendar"
  - _classify_domain_fast("open firefox") returns "desktop"
  - _classify_domain_fast("list my documents") returns "filesystem"
  - _classify_domain_fast("hello how are you") returns "none"
  - _classify_domain_fast("urgentes?") returns "email"
  - _classify_domain_fast("ping google.com") returns "network"
  - nammu_first_routing returns None when domain is "none"
    (mock _classify_domain_fast to return "none")
  - nammu_first_routing returns None when LLM times out
    (mock extract_intent_universal to block > 3s)
  - nammu_first_routing returns tool_request when LLM fast + confident
    (mock to return IntentResult(intent="email_search", confidence=0.97))
  - nammu_first_routing returns None when confidence < 0.75
    (mock to return IntentResult(intent="email_search", confidence=0.50))
  - NAMMU_UNIVERSAL_PROMPT contains all 11 domain names
  - NAMMU_UNIVERSAL_PROMPT contains example JSON outputs
  - IntentResult.to_tool_request includes domain in output
  - Email routing still works when NAMMU returns None (regex fallback)
    "anything from Matxalen?" → email_search via regex
  - Document routing: "read ~/report.pdf" → doc_read via regex fallback
  - Browser routing: "fetch https://example.com" → browser_read
  - Calendar routing: "what do I have today" → calendar_today
  - Full test suite still passes (≥621 tests)
  - Phase identity: CURRENT_PHASE contains "9.1"

Update test_identity.py, test_nammu_intent.py.

---

## Signal Word Lists

Read from governance_signals.json. Do NOT hardcode separately.
These must stay in sync with the governance config.
Load them at module import time:

```python
import json
from pathlib import Path

def _load_signals() -> dict[str, list[str]]:
    path = Path(__file__).parent.parent / "config" / "governance_signals.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

_DOMAIN_SIGNALS = _load_signals()

def _classify_domain_fast(text_lower: str) -> str:
    for domain, signals in _DOMAIN_SIGNALS.items():
        if any(s in text_lower for s in signals):
            return domain
    return "none"
```

---

## Permitted file changes

inanna/core/nammu_intent.py            <- MODIFY: universal prompt,
                                           domain field, new functions
inanna/main.py                         <- MODIFY: nammu_first_routing,
                                           _classify_domain_fast, wiring
inanna/core/help_system.py             <- MODIFY: natural language section
inanna/identity.py                     <- MODIFY: CURRENT_PHASE
inanna/tests/test_intent_engine.py     <- NEW
inanna/tests/test_nammu_intent.py      <- MODIFY: domain field tests
inanna/tests/test_identity.py          <- MODIFY
docs/cycle9_master_plan.md             <- MODIFY: phase status

---

## What You Are NOT Building

- No operator profile storage (Phase 9.2)
- No constitutional filter (Phase 9.3)
- No per-operator learning (Phase 9.2)
- No changes to workflow files (email_workflows, etc.)
- No changes to tools.json
- No changes to NixOS configs

---

## Critical Constraints

1. NEVER block the main routing path waiting for LLM
   All LLM calls MUST be in daemon threads with max 3s join timeout

2. NEVER remove existing regex routing
   nammu_first_routing is ADDITIVE — it runs before regex
   If it returns None, regex runs as before
   The system must work identically on slow hardware

3. NEVER call the LLM for pure conversation
   _classify_domain_fast("hello") returns "none"
   nammu_first_routing returns None immediately
   CROWN handles the conversation — no LLM routing call

4. Confidence threshold: 0.75
   Below this: fall through to regex even if LLM responded
   The regex is often more reliable for ambiguous inputs

---

## Definition of Done

- [ ] NAMMU_UNIVERSAL_PROMPT covers all 11 domains with examples
- [ ] _classify_domain_fast() reads from governance_signals.json
- [ ] nammu_first_routing() runs in 3s thread, returns None on timeout
- [ ] IntentResult has domain field
- [ ] nammu_first_routing wired before regex in dispatch chain
- [ ] help_system.py updated with natural language section
- [ ] CURRENT_PHASE = "Cycle 9 - Phase 9.1 - The Intent Engine"
- [ ] All tests pass: py -3 -m unittest discover -s tests (≥621)
- [ ] Pushed as cycle9-phase1-complete

---

## Handoff

Commit: cycle9-phase1-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE9_PHASE1_REPORT.md

The report MUST include:
  - Confirmation NAMMU_UNIVERSAL_PROMPT covers all 11 domains
  - Test of nammu_first_routing with mocked 97% confidence result
  - Confirmation fallback still works when LLM returns None
  - Whether the 3s thread timeout was tested

Stop. Do not begin Phase 9.2 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-22*
*Cycle 8 gave INANNA hands.*
*Cycle 9 gives INANNA understanding.*
*Phase 9.1 is the first word*
*in NAMMU's language.*
*The regex falls silent.*
*The LLM speaks.*
*Any phrasing. Any language. Any style.*
*Humans speak freely.*
*Machines receive structure.*
*NAMMU bridges the gap.*
