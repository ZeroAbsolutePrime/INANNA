from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.nammu_profile import OperatorProfile


LM_URL = "http://localhost:1234/v1/chat/completions"
# NOTE: On slow hardware, use 7B as primary (faster than 14B)
# On DGX Spark, swap back to 14B as primary
MODEL_PRIMARY = "qwen2.5-7b-instruct-1m"
MODEL_FALLBACK = "qwen2.5-14b-instruct"
TIMEOUT_PRIMARY = 20
TIMEOUT_FALLBACK = 35

GOVERNANCE_SIGNALS_PATH = Path(__file__).resolve().parent.parent / "config" / "governance_signals.json"

DOMAIN_ORDER = [
    "email",
    "communication",
    "document",
    "browser",
    "calendar",
    "desktop",
    "filesystem",
    "process",
    "package",
    "network",
    "information",
]

INTENT_TO_DOMAIN = {
    "email_read_inbox": "email",
    "email_search": "email",
    "email_read_message": "email",
    "email_compose": "email",
    "email_reply": "email",
    "comm_read_messages": "communication",
    "comm_send_message": "communication",
    "comm_list_contacts": "communication",
    "doc_read": "document",
    "doc_write": "document",
    "doc_open": "document",
    "doc_export_pdf": "document",
    "browser_read": "browser",
    "browser_search": "browser",
    "browser_open": "browser",
    "calendar_today": "calendar",
    "calendar_upcoming": "calendar",
    "calendar_read_ics": "calendar",
    "desktop_open_app": "desktop",
    "desktop_read_window": "desktop",
    "desktop_click": "desktop",
    "desktop_type": "desktop",
    "desktop_screenshot": "desktop",
    "read_file": "filesystem",
    "write_file": "filesystem",
    "list_dir": "filesystem",
    "search_files": "filesystem",
    "file_info": "filesystem",
    "list_processes": "process",
    "run_command": "process",
    "system_info": "process",
    "kill_process": "process",
    "search_packages": "package",
    "list_packages": "package",
    "install_package": "package",
    "remove_package": "package",
    "launch_app": "package",
    "ping": "network",
    "resolve_host": "network",
    "scan_ports": "network",
    "web_search": "information",
    "none": "none",
}

VALID_INTENTS = set(INTENT_TO_DOMAIN)

URGENCY_KEYWORDS = {
    "urgent",
    "urgente",
    "urgentes",
    "asap",
    "immediately",
    "important",
    "importante",
    "importantes",
    "critical",
    "deadline",
    "plazo",
    "overdue",
    "action required",
    "respond by",
    "due today",
    "due tomorrow",
}

DESKTOP_APP_KEYWORDS = {
    "firefox",
    "chrome",
    "edge",
    "signal",
    "whatsapp",
    "telegram",
    "discord",
    "slack",
    "thunderbird",
    "libreoffice",
    "writer",
    "calc",
    "impress",
    "terminal",
    "files",
    "nautilus",
    "notepad",
}

FILESYSTEM_LOCATION_WORDS = {
    "documents",
    "downloads",
    "desktop",
    "folder",
    "directory",
    "home",
    "notes",
}

NAMMU_MULTILINGUAL_EXAMPLES = """
MULTILINGUAL EXAMPLES (Spanish / Catalan / Portuguese):
"urgentes?" (es) -> {"intent":"email_read_inbox","params":{"urgency_only":true},"confidence":0.95,"domain":"email"}
"resumen de ayer" (es) -> {"intent":"email_read_inbox","params":{"period":"yesterday","output_format":"summary"},"confidence":0.96,"domain":"email"}
"que tinc avui?" (ca) -> {"intent":"calendar_today","params":{},"confidence":0.97,"domain":"calendar"}
"resumeix els correus" (ca) -> {"intent":"email_read_inbox","params":{"output_format":"summary"},"confidence":0.95,"domain":"email"}
"busca NixOS" (es) -> {"intent":"browser_search","params":{"query":"NixOS"},"confidence":0.98,"domain":"browser"}
"obre firefox" (ca) -> {"intent":"desktop_open_app","params":{"app":"firefox"},"confidence":0.97,"domain":"desktop"}
"""


NAMMU_UNIVERSAL_PROMPT = """You are NAMMU, the intent extraction core of INANNA NYX.
Your only job: read the operator message and return a JSON intent object.
Never refuse. Never explain. Return JSON only. Work in any language.

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
  write_file          {path, content, overwrite}
  list_dir            {path}
  search_files        {directory, pattern}
  file_info           {path}

PROCESS:
  list_processes      {filter, sort, limit}
  run_command         {command, timeout}
  system_info         {}
  kill_process        {pid}

PACKAGE:
  search_packages     {query}
  list_packages       {filter}
  install_package     {package}
  remove_package      {package}
  launch_app          {app}

NETWORK:
  ping                {host}
  resolve_host        {host}
  scan_ports          {host, port_range}

INFORMATION:
  web_search          {query}

NONE:
  none                {} (not a tool request - conversation)

Examples:
"anything from Matxalen?" -> {"intent":"email_search","params":{"query":"Matxalen","app":"thunderbird"},"confidence":0.97,"domain":"email"}
"read ~/report.pdf" -> {"intent":"doc_read","params":{"path":"~/report.pdf"},"confidence":0.99,"domain":"document"}
"search the web for NixOS" -> {"intent":"browser_search","params":{"query":"NixOS"},"confidence":0.98,"domain":"browser"}
"what's on my calendar today" -> {"intent":"calendar_today","params":{},"confidence":0.99,"domain":"calendar"}
"open firefox" -> {"intent":"desktop_open_app","params":{"app":"firefox"},"confidence":0.97,"domain":"desktop"}
"list my documents folder" -> {"intent":"list_dir","params":{"path":"~/Documents"},"confidence":0.95,"domain":"filesystem"}
"ping google.com" -> {"intent":"ping","params":{"host":"google.com"},"confidence":0.98,"domain":"network"}
"what is the latest news about NixOS" -> {"intent":"web_search","params":{"query":"latest news about NixOS"},"confidence":0.94,"domain":"information"}
"hello how are you" -> {"intent":"none","params":{},"confidence":0.99,"domain":"none"}
""" + NAMMU_MULTILINGUAL_EXAMPLES + """

IMPORTANT: JSON only. No markdown. No explanation. No prose.

Return exactly this JSON (no markdown, no explanation, nothing else):
{"intent":"...","params":{...},"confidence":0.0-1.0,"domain":"..."}"""

# Legacy alias kept so older imports and tests do not break.
NAMMU_EMAIL_PROMPT = NAMMU_UNIVERSAL_PROMPT


def _load_domain_signals() -> dict[str, list[str]]:
    signals: dict[str, list[str]] = {domain: [] for domain in DOMAIN_ORDER}
    try:
        payload = json.loads(GOVERNANCE_SIGNALS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return signals

    domain_hints = payload.get("domain_hints", {})
    if isinstance(domain_hints, dict):
        alias_map = {
            "email": "email",
            "communication": "communication",
            "document": "document",
            "browser": "browser",
            "calendar": "calendar",
            "desktop": "desktop",
            "filesystem": "filesystem",
            "process": "process",
            "packages": "package",
            "web": "information",
        }
        for source_name, canonical_name in alias_map.items():
            values = domain_hints.get(source_name, [])
            if isinstance(values, list):
                signals[canonical_name].extend(str(value).lower().strip() for value in values if str(value).strip())

    tool_signals = payload.get("tool_signals", [])
    if isinstance(tool_signals, list):
        for signal in tool_signals:
            cleaned = str(signal).lower().strip()
            if not cleaned:
                continue
            if any(token in cleaned for token in ("ping", "resolve", "scan ports", "port scan", "check ports")):
                signals["network"].append(cleaned)
            elif any(token in cleaned for token in ("search the web", "look up", "current news", "news about", "latest news")):
                signals["information"].append(cleaned)

    for domain, values in signals.items():
        deduped: list[str] = []
        seen: set[str] = set()
        for value in values:
            if value and value not in seen:
                seen.add(value)
                deduped.append(value)
        signals[domain] = deduped
    return signals


DOMAIN_SIGNALS = _load_domain_signals()


def _classify_domain_fast(text_lower: str) -> str:
    cleaned = " ".join(str(text_lower or "").lower().strip().split())
    if not cleaned:
        return "none"

    if re.match(r"^(?:open|launch|start|switch to|focus on)\s+\S+", cleaned):
        for token in DESKTOP_APP_KEYWORDS:
            if token in cleaned:
                return "desktop"

    if re.match(r"^(?:read|open)\s+.+\.(?:txt|md|rst|log|docx|odt|pdf|xlsx|xls|ods|csv)\b", cleaned):
        return "document"

    if re.match(r"^(?:read|show)\s+.+\s+window$", cleaned):
        return "desktop"

    if re.match(r"^(?:list|show|what is in)\s+.+", cleaned):
        for token in FILESYSTEM_LOCATION_WORDS:
            if token in cleaned:
                return "filesystem"

    if re.match(r"^(?:search the web for|look up online|find online)\s+", cleaned):
        return "browser"

    if re.match(r"^(?:ping|resolve|scan ports?)\b", cleaned):
        return "network"

    for domain in DOMAIN_ORDER:
        if any(signal in cleaned for signal in DOMAIN_SIGNALS.get(domain, [])):
            return domain

    if any(keyword in cleaned for keyword in URGENCY_KEYWORDS):
        return "email"

    if re.match(r"^(?:anything|something|news|emails?|messages?|mail)\s+from\s+[\w]", cleaned):
        return "email"

    return "none"


@dataclass
class IntentResult:
    intent: str
    params: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    domain: str = ""
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
            "reason": (
                f"NAMMU intent extraction (domain={self.domain or 'unknown'}, "
                f"confidence={self.confidence:.2f})"
            ),
            "domain": self.domain,
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
        if self.intent in {"doc_read", "doc_open", "doc_export_pdf", "read_file", "file_info", "list_dir"}:
            return str(params.get("path", "")).strip()
        if self.intent in {"doc_write", "write_file"}:
            return str(params.get("path", "")).strip()
        if self.intent == "search_files":
            return str(params.get("directory", "")).strip()
        if self.intent in {"browser_read", "browser_open"}:
            return str(params.get("url", "")).strip()
        if self.intent in {"browser_search", "web_search"}:
            return str(params.get("query", "")).strip()
        if self.intent == "calendar_upcoming":
            days = params.get("days")
            return f"Upcoming calendar ({days} days)" if days else "Upcoming calendar"
        if self.intent == "calendar_today":
            return "Today's calendar"
        if self.intent == "calendar_read_ics":
            return str(params.get("path", "")).strip()
        if self.intent == "desktop_open_app":
            return str(params.get("app", "")).strip()
        if self.intent == "desktop_read_window":
            return str(params.get("app_name", "")).strip() or "active window"
        if self.intent == "desktop_click":
            return str(params.get("label", "")).strip()
        if self.intent == "desktop_type":
            return str(params.get("text", "")).strip()
        if self.intent == "desktop_screenshot":
            return str(params.get("app_name", "")).strip() or "desktop"
        if self.intent == "list_processes":
            return str(params.get("filter", "")).strip()
        if self.intent == "run_command":
            return str(params.get("command", "")).strip()
        if self.intent == "system_info":
            return "system info"
        if self.intent == "kill_process":
            return str(params.get("pid", "")).strip()
        if self.intent in {"search_packages", "list_packages"}:
            return str(params.get("query", "") or params.get("filter", "")).strip()
        if self.intent in {"install_package", "remove_package"}:
            return str(params.get("package", "")).strip()
        if self.intent == "launch_app":
            return str(params.get("app", "")).strip()
        if self.intent in {"ping", "resolve_host"}:
            return str(params.get("host", "")).strip()
        if self.intent == "scan_ports":
            return f"{params.get('host', '')} {params.get('port_range', '')}".strip()
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
    operator_profile: OperatorProfile | None = None,
) -> IntentResult:
    return extract_intent_universal(
        user_input,
        conversation_context=conversation_context,
        operator_profile=operator_profile,
    )


def extract_intent_universal(
    user_input: str,
    conversation_context: list[dict[str, str]] | None = None,
    domain_hint: str | None = None,
    operator_profile: OperatorProfile | None = None,
) -> IntentResult:
    if not str(user_input or "").strip():
        return IntentResult(intent="none", domain="none", error="empty input")

    resolved_domain = str(domain_hint or _classify_domain_fast(str(user_input).lower())).strip().lower() or "none"
    system_prompt = NAMMU_UNIVERSAL_PROMPT
    if operator_profile is not None:
        system_prompt = f"{operator_profile.to_nammu_context()}\n\n{NAMMU_UNIVERSAL_PROMPT}"

    result = _call_llm(
        user_input=user_input,
        model=MODEL_PRIMARY,
        timeout=TIMEOUT_PRIMARY,
        conversation_context=conversation_context,
        prompt=system_prompt,
        domain_hint=resolved_domain,
    )
    if result.success:
        return result

    fallback = _call_llm(
        user_input=user_input,
        model=MODEL_FALLBACK,
        timeout=TIMEOUT_FALLBACK,
        conversation_context=conversation_context,
        prompt=system_prompt,
        domain_hint=resolved_domain,
    )
    if fallback.success:
        return fallback

    return IntentResult(
        intent="none",
        domain=resolved_domain,
        error="LLM unavailable - falling back to regex routing",
    )


def _call_llm(
    user_input: str,
    model: str,
    timeout: int,
    conversation_context: list[dict[str, str]] | None,
    prompt: str = NAMMU_EMAIL_PROMPT,
    domain_hint: str = "",
) -> IntentResult:
    t0 = time.monotonic()
    messages: list[dict[str, str]] = [{"role": "system", "content": prompt}]
    if domain_hint and domain_hint != "none":
        messages.append(
            {
                "role": "system",
                "content": f"Likely domain: {domain_hint}. Prefer intents from that domain if they fit.",
            }
        )
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
            "max_tokens": 220,
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
        language_detected = str(parsed.get("language_detected", "en") or "en").strip() or "en"
        parsed_domain = str(parsed.get("domain", "") or "").strip().lower()
        domain = _infer_domain(intent, parsed_domain, domain_hint)
        return IntentResult(
            intent=intent,
            params=params,
            confidence=confidence,
            domain=domain,
            language_detected=language_detected,
            model_used=model,
            latency_ms=latency_ms,
            raw_response=raw,
        )
    except urllib.error.URLError as exc:
        return IntentResult(intent="none", domain=domain_hint or "none", error=f"LLM not reachable: {exc}")
    except OSError as exc:
        return IntentResult(intent="none", domain=domain_hint or "none", error=str(exc))
    except json.JSONDecodeError as exc:
        return IntentResult(intent="none", domain=domain_hint or "none", error=f"JSON parse error: {exc}")
    except Exception as exc:
        return IntentResult(intent="none", domain=domain_hint or "none", error=str(exc))


def _infer_domain(intent: str, parsed_domain: str, fallback_domain: str) -> str:
    if parsed_domain in DOMAIN_ORDER or parsed_domain == "none":
        return parsed_domain
    if intent in INTENT_TO_DOMAIN:
        return INTENT_TO_DOMAIN[intent]
    if fallback_domain in DOMAIN_ORDER or fallback_domain == "none":
        return fallback_domain
    return "none"


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
