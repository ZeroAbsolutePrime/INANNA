from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any


LM_URL = "http://localhost:1234/v1/chat/completions"
MODEL_PRIMARY = "qwen2.5-14b-instruct"
MODEL_FALLBACK = "qwen2.5-7b-instruct-1m"
TIMEOUT_PRIMARY = 8
TIMEOUT_FALLBACK = 5

NAMMU_EMAIL_PROMPT = """You are NAMMU, the intent extraction core of INANNA NYX.
Your only job: read the operator message and return a JSON intent object.
Never refuse. Never explain. Return JSON only.
Work in any language - the operator may write in English, Spanish, Catalan, or others.

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

VALID_INTENTS = {
    "email_read_inbox",
    "email_search",
    "email_read_message",
    "email_compose",
    "email_reply",
    "comm_read_messages",
    "comm_send_message",
    "comm_list_contacts",
    "none",
}

URGENCY_KEYWORDS = {
    "urgent",
    "urgente",
    "asap",
    "immediately",
    "important",
    "importante",
    "critical",
    "deadline",
    "plazo",
    "overdue",
    "action required",
    "respond by",
    "due today",
    "due tomorrow",
}


@dataclass
class IntentResult:
    intent: str
    params: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    language_detected: str = "en"
    model_used: str = ""
    latency_ms: float = 0.0
    raw_response: str = ""
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.intent != "none" and self.error is None

    def to_tool_request(self) -> dict[str, Any] | None:
        if not self.success:
            return None
        return {
            "tool": self.intent,
            "params": dict(self.params),
            "query": self._build_query(),
            "reason": f"NAMMU intent extraction (confidence={self.confidence:.2f})",
        }

    def _build_query(self) -> str:
        params = self.params
        if self.intent == "email_read_inbox":
            parts = ["Read inbox"]
            if params.get("period"):
                parts.append(str(params["period"]))
            if params.get("max_emails"):
                parts.append(f"last {params['max_emails']}")
            if params.get("urgency_only"):
                parts.append("urgent only")
            return " - ".join(parts)
        if self.intent == "email_search":
            return f"Search emails for: {params.get('query', '')}"
        if self.intent == "email_read_message":
            return f"Read email from: {params.get('subject_or_sender', '')}"
        if self.intent == "email_compose":
            return f"Compose email to: {params.get('to', '')}"
        if self.intent == "email_reply":
            return f"Reply to: {params.get('subject_or_sender', '')}"
        if self.intent == "comm_read_messages":
            return f"Read {params.get('app', '')} messages"
        if self.intent == "comm_send_message":
            return f"Send {params.get('app', '')} message to {params.get('contact', '')}"
        if self.intent == "comm_list_contacts":
            return f"List {params.get('app', '')} contacts"
        return self.intent


@dataclass
class EmailComprehension:
    total: int = 0
    unread: int = 0
    urgent: list[dict[str, Any]] = field(default_factory=list)
    by_contact: dict[str, dict[str, Any]] = field(default_factory=dict)
    summaries: list[dict[str, Any]] = field(default_factory=list)
    suggested_actions: list[str] = field(default_factory=list)
    period: str = ""

    def to_crown_context(self) -> str:
        lines = [
            f"INBOX COMPREHENSION ({self.period or 'recent'}):",
            f"Total: {self.total} emails, {self.unread} unread",
        ]
        if self.urgent:
            lines.append("URGENT:")
            for item in self.urgent:
                lines.append(f"  - {item.get('from', '?')}: {item.get('reason', '?')}")
        if self.summaries:
            lines.append("SUMMARIES:")
            for item in self.summaries[:8]:
                lines.append(f"  - {item.get('from', '?')}: {item.get('one_line', '?')}")
        if self.suggested_actions:
            lines.append("SUGGESTED ACTIONS:")
            for action in self.suggested_actions[:3]:
                lines.append(f"  - {action}")
        return "\n".join(lines)


def extract_intent(
    user_input: str,
    conversation_context: list[dict[str, str]] | None = None,
) -> IntentResult:
    if not str(user_input or "").strip():
        return IntentResult(intent="none", error="empty input")

    result = _call_llm(
        user_input=user_input,
        model=MODEL_PRIMARY,
        timeout=TIMEOUT_PRIMARY,
        conversation_context=conversation_context,
    )
    if result.success:
        return result

    fallback = _call_llm(
        user_input=user_input,
        model=MODEL_FALLBACK,
        timeout=TIMEOUT_FALLBACK,
        conversation_context=conversation_context,
    )
    if fallback.success:
        return fallback

    return IntentResult(
        intent="none",
        error="LLM unavailable - falling back to regex routing",
    )


def _call_llm(
    user_input: str,
    model: str,
    timeout: int,
    conversation_context: list[dict[str, str]] | None,
) -> IntentResult:
    t0 = time.monotonic()
    messages: list[dict[str, str]] = [{"role": "system", "content": NAMMU_EMAIL_PROMPT}]
    if conversation_context:
        for turn in conversation_context[-2:]:
            role = str(turn.get("role", "")).strip()
            content = str(turn.get("content", "")).strip()
            if role and content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": str(user_input)})

    payload = json.dumps(
        {
            "model": model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 150,
        }
    ).encode("utf-8")

    try:
        request = urllib.request.Request(
            LM_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        latency_ms = (time.monotonic() - t0) * 1000.0
        raw = str(data["choices"][0]["message"]["content"]).strip()
        raw = _strip_code_fences(raw)
        parsed = json.loads(raw)
        intent = str(parsed.get("intent", "none")).strip()
        if intent not in VALID_INTENTS:
            intent = "none"
        params = parsed.get("params", {})
        if not isinstance(params, dict):
            params = {}
        confidence = float(parsed.get("confidence", 0.0) or 0.0)
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
    except json.JSONDecodeError as exc:
        return IntentResult(intent="none", error=f"JSON parse error: {exc}")
    except Exception as exc:
        return IntentResult(intent="none", error=str(exc))


def build_comprehension(
    emails: list[Any],
    period: str = "",
    urgency_filter: bool = False,
) -> EmailComprehension:
    del urgency_filter
    comprehension = EmailComprehension(
        total=len(emails),
        unread=sum(1 for email in emails if getattr(email, "unread", False)),
        period=period,
    )
    grouped: dict[str, list[dict[str, str]]] = {}

    for email in emails:
        sender = str(getattr(email, "sender", "") or "")
        subject = str(getattr(email, "subject", "") or "")
        preview = str(getattr(email, "preview", "") or "")
        contact = sender.split("<")[0].strip() or sender[:30] or "Unknown"
        grouped.setdefault(contact, []).append(
            {
                "subject": subject,
                "preview": preview[:100],
            }
        )

        lowered_subject = subject.lower()
        lowered_preview = preview.lower()
        if any(keyword in lowered_subject or keyword in lowered_preview for keyword in URGENCY_KEYWORDS):
            comprehension.urgent.append(
                {
                    "from": contact,
                    "subject": subject,
                    "reason": "urgency keyword detected in subject/body",
                }
            )

        comprehension.summaries.append(
            {
                "from": contact,
                "subject": subject,
                "one_line": subject[:80] if subject else "(no subject)",
            }
        )

    for contact, items in grouped.items():
        comprehension.by_contact[contact] = {
            "count": len(items),
            "latest": items[-1]["subject"][:60] if items else "",
        }

    for urgent in comprehension.urgent[:2]:
        comprehension.suggested_actions.append(f"Reply to {urgent['from']} (flagged urgent)")
    if comprehension.unread > 0:
        comprehension.suggested_actions.append(f"Review {comprehension.unread} unread email(s)")

    return comprehension


def _strip_code_fences(raw: str) -> str:
    text = str(raw or "").strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    if lines and lines[0].strip().lower() == "json":
        lines = lines[1:]
    return "\n".join(lines).strip()
