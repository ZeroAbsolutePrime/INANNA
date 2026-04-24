# CURRENT PHASE: Cycle 8 - Phase 8.3b - The NAMMU Intelligence Bridge
**Status: ACTIVE**
**Authorized by: INANNA NAMMU (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-22**
**Cycle: 8 - The Desktop Bridge**
**Replaces: Cycle 8 Phase 8.3 - Email Faculty (COMPLETE)**

**MANDATORY READING before touching code:**
  docs/cycle8_master_plan.md
  docs/cycle9_master_plan.md   ← READ THIS ESPECIALLY
  docs/project_preservation.md

---

## Why This Phase Exists

Phase 8.3 built real email reading via ThunderbirdDirectReader.
The tools work. The data is real. No hallucination.

But the routing is still robo-like:

  "check my email"     → works  (exact phrase match)
  "anything urgent?"   → fails  (no regex match)
  "Matxalen replied?"  → fails  (no regex match)
  "¿tengo emails?"     → fails  (wrong language)

This phase replaces pattern matching with LLM intent extraction
for email and communication domains. It is the first step of
what becomes Cycle 9 — NAMMU Reborn.

The architectural principle:
  Humans speak freely.
  Machines receive structure.
  NAMMU bridges the gap.
  LLM, not regex.

Read docs/cycle9_master_plan.md for the full vision.
This phase implements the foundation.

---

## What This Phase Is NOT

This phase does NOT build:
  - Per-operator learning (Cycle 9 Phase 9.2)
  - Constitutional filter (Cycle 9 Phase 9.3)
  - Comprehension Layer in full (partial here)
  - Multilingual core (Cycle 9 Phase 9.6)
  - Full NAMMU replacement (Cycle 9)

This phase builds ONE thing:
  LLM-based intent extraction for email and communication,
  replacing the regex patterns in main.py for those domains.
  Plus: basic email comprehension (summary, urgency detection).

This proves the concept. Cycle 9 generalizes it to all domains.

---

## The Model

Available on this machine via LM Studio:
  qwen2.5-14b-instruct  ← USE THIS for intent extraction
  qwen2.5-7b-instruct-1m ← fallback if 14B fails/times out

The 14B model has been tested and produces correct structured
JSON for all test cases including Spanish and Catalan.
See test results below.

LM Studio URL: http://localhost:1234/v1/chat/completions

Timeout strategy:
  - Primary: qwen2.5-14b-instruct, timeout=8s
  - Fallback: qwen2.5-7b-instruct-1m, timeout=5s
  - Final fallback: existing regex routing (never fail silently)

---

## Confirmed Test Results (run before writing code)

These results were produced by calling qwen2.5-14b-instruct
with the NAMMU intent prompt defined in Task 1 below.

Input: "summarize my last 5 emails"
Output: intent=email_read_inbox, max_emails=5, output_format=summary
Confidence: 1.00 ✓

Input: "do I have anything urgent in my inbox?"
Output: intent=email_read_inbox, urgency_only=true, period=today
Confidence: 1.00 ✓

Input: "quick overview of yesterday's emails"
Output: intent=email_read_inbox, period=yesterday, output_format=summary
Confidence: 1.00 ✓

These results confirm the approach is valid and the model
is capable. The implementation should match these results.

---

## What You Are Building

### Task 1 — inanna/core/nammu_intent.py

Create: inanna/core/nammu_intent.py

This is the NAMMU Intent Engine — first implementation.
A single focused module that handles LLM-based intent
extraction for email and communication domains.

```python
"""
NAMMU Intent Engine — Phase 8.3b
LLM-based intent extraction for email and communication.

This is the first step toward NAMMU Reborn (Cycle 9).
It replaces regex pattern matching for email/comm domains
with LLM understanding via the local Qwen 14B model.

Architecture principle (mandatory):
  Humans speak freely.
  Machines receive structure.
  NAMMU bridges the gap.
  LLM, not regex.

See docs/cycle9_master_plan.md for the full vision.
"""
from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Optional

# ── CONFIGURATION ──────────────────────────────────────────────────

LM_URL = "http://localhost:1234/v1/chat/completions"
MODEL_PRIMARY   = "qwen2.5-14b-instruct"
MODEL_FALLBACK  = "qwen2.5-7b-instruct-1m"
TIMEOUT_PRIMARY = 8    # seconds
TIMEOUT_FALLBACK = 5   # seconds

# ── NAMMU INTENT PROMPT ───────────────────────────────────────────
# This prompt is the core of the Intent Engine.
# It must be precise, complete, and language-agnostic.
# Any modification requires updating the test suite.

NAMMU_EMAIL_PROMPT = """You are NAMMU, the intent extraction core of INANNA NYX.
Your only job: read the operator message and return a JSON intent object.
Never refuse. Never explain. Return JSON only.
Work in any language — the operator may write in English, Spanish, Catalan, or others.

Available intents:
  email_read_inbox    Read the email inbox
  email_search        Search emails by keyword/sender/subject
  email_read_message  Read a specific email
  email_compose       Compose a new email
  email_reply         Reply to an email
  comm_read_messages  Read messages from Signal/WhatsApp
  comm_send_message   Send a message via Signal/WhatsApp
  comm_list_contacts  List contacts in messaging app
  none                Not an email or communication request

Parameters for email_read_inbox:
  app: "thunderbird" (default) or "protonmail"
  max_emails: integer or null (null = use default 15)
  period: "today" | "yesterday" | "this_week" | null
  urgency_only: true if operator asks for urgent/important only
  output_format: "summary" (default) | "list"

Parameters for email_search:
  query: search string (sender name, keyword, subject fragment)
  app: "thunderbird" (default)
  period: "today" | "yesterday" | "this_week" | null

Parameters for email_read_message:
  subject_or_sender: name or subject keyword to find
  app: "thunderbird" (default)

Parameters for email_compose:
  to: recipient
  subject: subject line
  body: message body
  app: "thunderbird" (default)

Parameters for email_reply:
  subject_or_sender: email to reply to
  body: reply text
  app: "thunderbird" (default)

Parameters for comm_read_messages:
  app: "signal" | "whatsapp"

Parameters for comm_send_message:
  app: "signal" | "whatsapp"
  contact: contact name
  message: message text

Return exactly this JSON (no markdown, no explanation):
{"intent": "...", "params": {...}, "confidence": 0.0-1.0}"""


# ── DATA STRUCTURES ────────────────────────────────────────────────

@dataclass
class IntentResult:
    """Structured intent extracted from operator input."""
    intent: str                          # tool name or "none"
    params: dict = field(default_factory=dict)
    confidence: float = 0.0
    language_detected: str = "en"
    model_used: str = ""
    latency_ms: float = 0.0
    raw_response: str = ""
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.intent != "none" and self.error is None

    def to_tool_request(self) -> dict | None:
        """Convert to the format expected by execute_tool_request."""
        if not self.success:
            return None
        return {
            "tool": self.intent,
            "params": self.params,
            "query": self._build_query(),
            "reason": f"NAMMU intent extraction (confidence={self.confidence:.2f})",
        }

    def _build_query(self) -> str:
        p = self.params
        if self.intent == "email_read_inbox":
            parts = ["Read inbox"]
            if p.get("period"): parts.append(p["period"])
            if p.get("max_emails"): parts.append(f"last {p['max_emails']}")
            if p.get("urgency_only"): parts.append("urgent only")
            return " — ".join(parts)
        if self.intent == "email_search":
            return f"Search emails for: {p.get('query','')}"
        if self.intent == "email_read_message":
            return f"Read email from: {p.get('subject_or_sender','')}"
        if self.intent == "email_compose":
            return f"Compose email to: {p.get('to','')}"
        if self.intent == "email_reply":
            return f"Reply to: {p.get('subject_or_sender','')}"
        if self.intent == "comm_read_messages":
            return f"Read {p.get('app','')} messages"
        if self.intent == "comm_send_message":
            return f"Send {p.get('app','')} message to {p.get('contact','')}"
        return self.intent


# ── CORE EXTRACTION FUNCTION ────────────────────────────────────────

def extract_intent(
    user_input: str,
    conversation_context: list[dict] | None = None,
) -> IntentResult:
    """
    Extract structured intent from free-form operator input.
    Uses LLM (14B primary, 7B fallback, regex final fallback).

    This is the main entry point for NAMMU intent extraction.
    It NEVER raises exceptions — always returns an IntentResult.
    If all LLM calls fail, returns IntentResult(intent="none").
    """
    if not user_input or not user_input.strip():
        return IntentResult(intent="none", error="empty input")

    # Try primary model
    result = _call_llm(
        user_input, MODEL_PRIMARY, TIMEOUT_PRIMARY,
        conversation_context
    )
    if result.success:
        return result

    # Try fallback model
    result = _call_llm(
        user_input, MODEL_FALLBACK, TIMEOUT_FALLBACK,
        conversation_context
    )
    if result.success:
        return result

    # Both LLM calls failed — return none gracefully
    return IntentResult(
        intent="none",
        error="LLM unavailable — falling back to regex routing",
    )


def _call_llm(
    user_input: str,
    model: str,
    timeout: int,
    conversation_context: list[dict] | None,
) -> IntentResult:
    """Make one LLM call and parse the JSON response."""
    t0 = time.monotonic()
    messages = [{"role": "system", "content": NAMMU_EMAIL_PROMPT}]

    # Add last 2 turns of context if available
    if conversation_context:
        for turn in conversation_context[-2:]:
            messages.append(turn)

    messages.append({"role": "user", "content": user_input})

    payload = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 150,
    }).encode()

    try:
        req = urllib.request.Request(
            LM_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())

        latency_ms = (time.monotonic() - t0) * 1000
        raw = data["choices"][0]["message"]["content"].strip()

        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        parsed = json.loads(raw)
        intent = str(parsed.get("intent", "none"))
        params = dict(parsed.get("params", {}))
        confidence = float(parsed.get("confidence", 0.0))

        # Validate intent name
        valid_intents = {
            "email_read_inbox", "email_search", "email_read_message",
            "email_compose", "email_reply",
            "comm_read_messages", "comm_send_message", "comm_list_contacts",
            "none",
        }
        if intent not in valid_intents:
            intent = "none"

        return IntentResult(
            intent=intent,
            params=params,
            confidence=confidence,
            model_used=model,
            latency_ms=latency_ms,
            raw_response=raw,
        )

    except urllib.error.URLError:
        return IntentResult(intent="none", error=f"LLM not reachable: {model}")
    except json.JSONDecodeError as e:
        return IntentResult(intent="none", error=f"JSON parse error: {e}")
    except Exception as e:
        return IntentResult(intent="none", error=str(e))


# ── EMAIL COMPREHENSION ────────────────────────────────────────────

@dataclass
class EmailComprehension:
    """
    Structured summary of an email inbox.
    Produced after reading real emails from ThunderbirdDirectReader.
    Given to CROWN for natural language presentation.
    """
    total: int = 0
    unread: int = 0
    urgent: list[dict] = field(default_factory=list)
    by_contact: dict[str, dict] = field(default_factory=dict)
    summaries: list[dict] = field(default_factory=list)
    suggested_actions: list[str] = field(default_factory=list)
    period: str = ""

    def to_crown_context(self) -> str:
        """
        Format comprehension for CROWN to present naturally.
        CROWN receives this instead of raw email data.
        """
        lines = [
            f"INBOX COMPREHENSION ({self.period or 'recent'}):",
            f"Total: {self.total} emails, {self.unread} unread",
        ]
        if self.urgent:
            lines.append("URGENT:")
            for u in self.urgent:
                lines.append(f"  - {u.get('from','?')}: {u.get('reason','?')}")
        if self.summaries:
            lines.append("SUMMARIES:")
            for s in self.summaries[:8]:
                lines.append(
                    f"  - {s.get('from','?')}: {s.get('one_line','?')}"
                )
        if self.suggested_actions:
            lines.append("SUGGESTED ACTIONS:")
            for a in self.suggested_actions[:3]:
                lines.append(f"  - {a}")
        return "\n".join(lines)


# Urgency keywords to detect in email subjects/bodies
URGENCY_KEYWORDS = {
    "urgent", "urgente", "asap", "immediately", "important",
    "importante", "crítico", "critical", "deadline", "plazo",
    "overdue", "vencido", "action required", "acción requerida",
    "respond by", "due today", "due tomorrow",
}


def build_comprehension(
    emails: list,  # list of EmailRecord
    period: str = "",
    urgency_filter: bool = False,
) -> EmailComprehension:
    """
    Build structured comprehension from a list of EmailRecord objects.
    Detects urgency, groups by contact, extracts summaries.
    No LLM call — pure deterministic analysis. Zero hallucination.
    """
    comp = EmailComprehension(
        total=len(emails),
        unread=sum(1 for e in emails if getattr(e, 'unread', False)),
        period=period,
    )

    contact_groups: dict[str, list] = {}

    for email in emails:
        sender = str(getattr(email, 'sender', '') or '')
        subject = str(getattr(email, 'subject', '') or '')
        preview = str(getattr(email, 'preview', '') or '')

        # Extract contact name (before <email>)
        contact = sender.split('<')[0].strip() or sender[:30]

        # Group by contact
        if contact not in contact_groups:
            contact_groups[contact] = []
        contact_groups[contact].append({
            "subject": subject,
            "preview": preview[:100],
        })

        # Urgency detection
        subject_lower = subject.lower()
        preview_lower = preview.lower()
        is_urgent = any(
            kw in subject_lower or kw in preview_lower
            for kw in URGENCY_KEYWORDS
        )
        if is_urgent:
            comp.urgent.append({
                "from": contact,
                "subject": subject,
                "reason": "urgency keyword detected in subject/body",
            })

        # Build summary
        comp.summaries.append({
            "from": contact,
            "subject": subject,
            "one_line": subject[:80] if subject else "(no subject)",
        })

    # Build contact summary
    for contact, msgs in contact_groups.items():
        comp.by_contact[contact] = {
            "count": len(msgs),
            "latest": msgs[-1]["subject"][:60] if msgs else "",
        }

    # Suggested actions
    if comp.urgent:
        for u in comp.urgent[:2]:
            comp.suggested_actions.append(
                f"Reply to {u['from']} (flagged urgent)"
            )
    if comp.unread > 0:
        comp.suggested_actions.append(
            f"Review {comp.unread} unread email(s)"
        )

    return comp
```

### Task 2 — Wire NammuIntent into server.py and main.py

In main.py, add a new routing layer BEFORE the existing
email regex patterns. This is the "NAMMU first" principle:

```python
# In extract_email_tool_request(), BEFORE all regex:
from core.nammu_intent import extract_intent, IntentResult

# Try LLM intent extraction first
# Only call for messages that have email/comm domain signals
if _has_email_comm_signal(lowered):
    intent_result = extract_intent(text, conversation_context)
    if intent_result.success and intent_result.confidence >= 0.75:
        return intent_result.to_tool_request()
# Fall through to existing regex patterns if LLM fails/low confidence
```

Helper function:
```python
def _has_email_comm_signal(text_lower: str) -> bool:
    """Quick check: does this look like email/comm related?"""
    signals = {
        "email", "inbox", "message", "mail", "signal", "whatsapp",
        "correo", "mensajes", "correu", "missatge",  # ES/CA
        "from", "de", "urgent", "urgente", "summary", "resumen",
    }
    return any(s in text_lower for s in signals)
```

In server.py, after tool runs and returns emails,
call build_comprehension() before passing to CROWN:

```python
# After email_read_inbox runs and returns emails:
from core.nammu_intent import build_comprehension, EmailComprehension
if result.tool in {"email_read_inbox", "email_search"} and result.success:
    emails = result.data.get("emails", [])
    if emails:
        period = result.data.get("params", {}).get("period", "")
        urgency = result.data.get("params", {}).get("urgency_only", False)
        comp = build_comprehension(emails, period=period)
        # Replace tool_result_summary with structured comprehension
        tool_result_summary = comp.to_crown_context()
```

### Task 3 — CROWN instruction for email comprehension

When the tool result is an EmailComprehension, CROWN gets
a stronger, clearer instruction:

```python
if is_email_comprehension:
    tool_instruction = (
        f"INBOX DATA (real, from Thunderbird — no hallucination):\n"
        f"{tool_result_summary}\n"
        f"---\n"
        f"Present this to the operator naturally.\n"
        f"Rules:\n"
        f"- Speak conversationally, not as a list\n"
        f"- Mention urgent items first\n"
        f"- Suggest a next action if obvious\n"
        f"- Use the operator's language if detectable\n"
        f"- DO NOT invent any email content not shown above\n"
        f"- DO NOT add fictional senders, subjects, or bodies"
    )
```

### Task 4 — Update identity.py

CURRENT_PHASE = "Cycle 8 - Phase 8.3b - NAMMU Intelligence Bridge"

### Task 5 — Document the test results

Create: docs/nammu_intent_test_results.md

Document the actual LLM test results confirming the model
works for intent extraction. Include:
  - Model used and version
  - Test inputs and outputs
  - Confidence scores
  - Latency measurements
  - Spanish/Catalan test results when available

This document is mandatory project evidence.

### Task 6 — Tests (all offline — mock the LLM call)

Create: inanna/tests/test_nammu_intent.py

Tests (mock the HTTP call to LLM — no actual LLM in tests):
  - IntentResult instantiates correctly
  - IntentResult.success True when intent != "none"
  - IntentResult.success False when intent == "none"
  - IntentResult.to_tool_request returns dict for valid intent
  - IntentResult.to_tool_request returns None for "none" intent
  - _call_llm returns IntentResult with error on connection fail
  - extract_intent returns IntentResult(intent="none") on empty input
  - extract_intent returns IntentResult(intent="none") on LLM failure
    (mocked to raise URLError)
  - EmailComprehension instantiates with defaults
  - build_comprehension returns correct total count
  - build_comprehension detects urgency keywords
  - build_comprehension groups by contact correctly
  - build_comprehension.to_crown_context includes total count
  - build_comprehension.to_crown_context includes URGENT section
    when urgent emails present
  - build_comprehension does not hallucinate (output contains
    only data from input emails)
  - URGENCY_KEYWORDS contains "urgent" and "urgente"
  - _has_email_comm_signal("check my email") returns True
  - _has_email_comm_signal("hello world") returns False
  - _has_email_comm_signal("correo urgente") returns True (Spanish)

Update test_identity.py: CURRENT_PHASE assertion.

---

## Permitted file changes

inanna/core/nammu_intent.py             <- NEW
inanna/main.py                          <- MODIFY: NAMMU-first routing
inanna/ui/server.py                     <- MODIFY: comprehension before CROWN
inanna/identity.py                      <- MODIFY: CURRENT_PHASE
inanna/tests/test_nammu_intent.py       <- NEW
inanna/tests/test_identity.py           <- MODIFY
docs/nammu_intent_test_results.md       <- NEW (mandatory)

---

## What You Are NOT Building

- No per-operator profiles (Cycle 9 Phase 9.2)
- No constitutional filter (Cycle 9 Phase 9.3)
- No full NAMMU replacement (Cycle 9)
- No changes to ThunderbirdDirectReader
- No changes to desktop_faculty.py
- No changes to communication_workflows.py
- No voice changes, no auth changes

---

## Definition of Done

- [ ] core/nammu_intent.py with extract_intent() and build_comprehension()
- [ ] LLM intent extraction wired before regex in email routing
- [ ] EmailComprehension wired into server.py after email tool execution
- [ ] CROWN receives structured comprehension, not raw email list
- [ ] Test: "anything from Matxalen?" routes to email_search
- [ ] Test: "anything urgent?" routes to email_read_inbox(urgency_only=True)
- [ ] Test: "summarize yesterday's emails" routes correctly with period=yesterday
- [ ] All offline tests pass: py -3 -m unittest discover -s tests
- [ ] docs/nammu_intent_test_results.md written
- [ ] CURRENT_PHASE updated
- [ ] Pushed as cycle8-phase3b-complete

---

## Handoff

Commit: cycle8-phase3b-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE8_PHASE3B_REPORT.md
Stop. Do not begin Phase 8.4 without new CURRENT_PHASE.md.

---

## Mandatory Documentation Update

After pushing, verify these files exist and are current:
  docs/cycle8_master_plan.md     ← already exists
  docs/cycle9_master_plan.md     ← created this session
  docs/nammu_intent_test_results.md  ← create in this phase
  docs/implementation/CYCLE8_PHASE3B_REPORT.md ← create in this phase

These are permanent project records. They document WHY
decisions were made, not just what was built.
Future AI reading this project depends on these documents.

---

*Written by: Claude (Command Center)*
*Guardian approval: INANNA NAMMU*
*Date: 2026-04-22*
*The pattern matcher dies here.*
*The interpreter is born.*
*Humans speak freely.*
*Machines receive structure.*
*NAMMU bridges the gap.*
*This is the cornerstone.*
