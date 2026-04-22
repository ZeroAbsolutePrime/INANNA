from __future__ import annotations

import json
import os
import re
import threading
import time
from dataclasses import MISSING, asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv

from config import Config
from core.body import BodyInspector, BodyReport
from core.browser_workflows import (
    BrowserActionResult,
    BrowserComprehension,
    BrowserWorkflows,
    PageRecord,
)
from core.calendar_workflows import (
    CalendarComprehension,
    CalendarResult,
    CalendarWorkflows,
)
from core.communication_workflows import CommunicationWorkflows, WorkflowResult, normalize_app_name
from core.constitutional_filter import ConstitutionalFilter
from core.desktop_faculty import DesktopFaculty, DesktopResult, is_consequential_label
from core.document_workflows import (
    DocumentComprehension,
    DocumentRecord,
    DocumentWorkflows,
    DocumentWriteResult,
)
from core.email_workflows import (
    DEFAULT_EMAIL_CLIENT,
    EMAIL_APP_PATTERNS,
    EMAIL_APP_WINGET_IDS,
    EmailRecord,
    EmailWorkflowResult,
    EmailWorkflows,
    normalize_email_app,
)
from core.faculty_monitor import FacultyMonitor
from core.filesystem_faculty import FileInfo, FileSystemFaculty, FileSystemResult
from core.governance import GovernanceLayer
from core.guardian import GuardianFaculty
from core.memory import Memory
from core.nammu_intent import (
    INTENT_TO_DOMAIN,
    _classify_domain_fast,
    extract_intent,
    extract_intent_universal,
)
from core.nammu_profile import (
    OperatorProfile,
    RoutingCorrection,
    analyse_routing_log,
    build_profile_from_user_profile,
    load_operator_profile,
    save_operator_profile,
)
from core.nammu import IntentClassifier
from core.nammu_memory import (
    ROUTING_LOG_FILE,
    append_governance_event,
    append_routing_event,
    load_governance_history,
    load_routing_history,
)
from core.orchestration import OrchestrationEngine, OrchestrationPlan
from core.operator import OperatorFaculty, ToolResult
from core.package_faculty import (
    PackageFaculty,
    PackageRecord as FacultyPackageRecord,
    PackageResult as FacultyPackageResult,
)
from core.software_registry import SoftwareRegistry
from core.profile import (
    CommunicationObserver,
    NotificationStore,
    ProfileManager,
    UserProfile,
    utc_now,
)
from core.process_faculty import (
    ProcessFaculty,
    ProcessRecord as FacultyProcessRecord,
    ProcessResult as FacultyProcessResult,
    SystemInfo as FacultySystemInfo,
)
from core.process_monitor import ProcessMonitor
from core.proposal import Proposal
from core.realm import DEFAULT_REALM, RealmConfig, RealmManager
from core.reflection import ReflectionEntry, ReflectiveMemory
from core.session import AnalystFaculty, Engine, Session
from core.session_token import SessionToken, TokenStore
from core.state import StateReport
from core.user import (
    InviteRecord,
    UserManager,
    UserRecord,
    can_access_realm,
    check_privilege,
    ensure_guardian_exists,
)
from core.user_log import UserLog
from identity import phase_banner


APP_ROOT = Path(__file__).resolve().parent
load_dotenv(APP_ROOT / ".env")

DATA_ROOT = APP_ROOT / "data"
FACULTIES_CONFIG_PATH = APP_ROOT / "config" / "faculties.json"
ROLES_CONFIG_PATH = APP_ROOT / "config" / "roles.json"
USER_LOG_DIR = DATA_ROOT / "user_logs"
PROFILES_DIR = DATA_ROOT / "profiles"
SESSION_DIR = DATA_ROOT / "sessions"
MEMORY_DIR = DATA_ROOT / "memory"
PROPOSAL_DIR = DATA_ROOT / "proposals"
NAMMU_DIR = DATA_ROOT / "nammu"
SELF_DIR = DATA_ROOT / "self"
STARTUP_COMMANDS = (
    "users",
    "create-user",
    "login",
    "logout",
    "whoami",
    "my-profile",
    "view-profile",
    "inanna-reflect",
    "my-trust",
    "my-departments",
    "assign-department",
    "unassign-department",
    "assign-group",
    "unassign-group",
    "notify-department",
    "governance-trust",
    "governance-revoke",
    "reflect",
    "analyse",
    "audit",
    "guardian",
    "faculties",
    "realms",
    "create-realm",
    "realm-context",
    "switch-user",
    "assign-realm",
    "unassign-realm",
    "my-log",
    "user-log",
    "invite",
    "join",
    "invites",
    "admin-surface",
    "tool-registry",
    "faculty-registry",
    "network-status",
    "process-status",
    "history",
    "proposal-history",
    "routing-log",
    "nammu-log",
    "memory-log",
    "body",
    "status",
    "diagnostics",
    "guardian-dismiss",
    "guardian-clear-events",
    "approve",
    "reject",
    "forget",
    "exit",
    "help",
    "software",
)
AUTO_MEMORY_TURN_THRESHOLD = 20

# Help system
from core.help_system import build_help_response  # noqa: E402
REFLECT_PATTERN = re.compile(
    r"\[REFLECT:\s*(.+?)\s*\|\s*context:\s*(.+?)\s*\]",
    re.DOTALL,
)
SENTINEL_STUB_RESPONSE = (
    "SENTINEL Faculty is registered but not yet deployed. Activate it in the Faculty Registry."
)
SENTINEL_FALLBACK_PREFIX = "[sentinel fallback]"
ONBOARDING_SKIP_ALL = "skip all"
ONBOARDING_STEPS: tuple[dict[str, Any], ...] = (
    {
        "field": "preferred_name",
        "prompt": "What would you like me to call you?",
        "skip_phrases": {"", "skip", "no preference"},
    },
    {
        "field": "pronouns",
        "prompt": (
            "What pronouns do you use? For example: she/her, he/him, "
            "they/them - or skip this if you prefer."
        ),
        "skip_phrases": {"", "skip", "prefer not"},
    },
    {
        "field": "purpose",
        "prompt": "What brings you here? What are you working on?",
        "skip_phrases": {"skip"},
    },
    {
        "field": "sensitive_domains",
        "prompt": (
            "Are there domains or topics you would like me to be especially "
            "thoughtful about?"
        ),
        "skip_phrases": {"skip", "none"},
    },
    {
        "field": "additional",
        "prompt": (
            "Is there anything else you would like me to know about you "
            "that would help me serve you well?"
        ),
        "skip_phrases": {"skip", "nothing", "no"},
    },
)
PROFILE_EMPTY_VALUE = "\u2014"
PROFILE_GUARDIAN_ONLY_FIELDS = {"inanna_notes"}
PROFILE_PROTECTED_CLEAR_FIELDS = {
    "user_id",
    "version",
    "created_at",
    "last_updated",
    "onboarding_completed",
}
PROFILE_READ_ONLY_FIELDS = {
    "user_id",
    "version",
    "created_at",
    "last_updated",
}
PROFILE_COMMUNICATION_CLEAR_FIELDS = (
    "preferred_length",
    "formality",
    "communication_style",
    "observed_patterns",
)
FILESYSTEM_SIGNAL_PATH = APP_ROOT / "config" / "governance_signals.json"
FILESYSTEM_TOOL_NAMES = {
    "read_file",
    "list_dir",
    "file_info",
    "search_files",
    "write_file",
}
FILESYSTEM_HINT_FALLBACKS = (
    "read file",
    "open file",
    "show file",
    "list directory",
    "list folder",
    "what files",
    "search files",
    "find files",
    "file size",
    "file info",
    "write file",
    "save file",
    "create file",
    "what is in",
    "show me",
)
FILESYSTEM_PATTERN_ALIASES = {
    "python": "*.py",
    "python code": "*.py",
    "py": "*.py",
    ".py": "*.py",
    "text": "*.txt",
    "txt": "*.txt",
    ".txt": "*.txt",
    "markdown": "*.md",
    "md": "*.md",
    ".md": "*.md",
    "json": "*.json",
    ".json": "*.json",
    "csv": "*.csv",
    ".csv": "*.csv",
    "pdf": "*.pdf",
    ".pdf": "*.pdf",
}
PROCESS_TOOL_NAMES = {
    "list_processes",
    "system_info",
    "kill_process",
    "run_command",
}
PACKAGE_TOOL_NAMES = {
    "search_packages",
    "list_packages",
    "install_package",
    "remove_package",
    "launch_app",
}
DESKTOP_TOOL_NAMES = {
    "desktop_open_app",
    "desktop_read_window",
    "desktop_click",
    "desktop_type",
    "desktop_screenshot",
}
COMMUNICATION_TOOL_NAMES = {
    "comm_read_messages",
    "comm_send_message",
    "comm_list_contacts",
}
CALENDAR_TOOL_NAMES = {
    "calendar_today",
    "calendar_upcoming",
    "calendar_read_ics",
}
EMAIL_TOOL_NAMES = {
    "email_read_inbox",
    "email_read_message",
    "email_search",
    "email_compose",
    "email_reply",
}
BROWSER_TOOL_NAMES = {
    "browser_read",
    "browser_search",
    "browser_open",
}
DOCUMENT_TOOL_NAMES = {
    "doc_read",
    "doc_write",
    "doc_open",
    "doc_export_pdf",
}
PROCESS_HINT_FALLBACKS = (
    "process",
    "processes",
    "running",
    "memory usage",
    "cpu usage",
    "system info",
    "system health",
    "uptime",
    "kill process",
    "terminate",
    "what is using",
    "ram",
    "disk space",
    "how is the system",
    "performance",
)
PACKAGE_HINT_FALLBACKS = (
    "install",
    "uninstall",
    "remove package",
    "search package",
    "list packages",
    "what is installed",
    "package manager",
    "nix-env",
    "apt",
    "brew",
    "winget",
    "software",
)
COMMUNICATION_HINT_FALLBACKS = (
    "send message",
    "send signal",
    "message to",
    "text to",
    "whatsapp",
    "signal message",
    "read messages",
    "check messages",
    "new messages",
    "reply to",
    "write to",
    "contact",
    "unread",
    "chat",
    "inbox",
)
EMAIL_HINT_FALLBACKS = (
    "check email",
    "read email",
    "inbox",
    "unread email",
    "new emails",
    "email from",
    "send email",
    "compose email",
    "write email",
    "reply to email",
    "reply to",
    "email to",
    "forward email",
    "search email",
    "find email",
    "thunderbird",
    "protonmail",
    "proton mail",
    "mail",
    "message from",
)
EMAIL_COMM_SIGNAL_FALLBACKS = {
    "email",
    "emails",
    "inbox",
    "mail",
    "message",
    "messages",
    "signal",
    "whatsapp",
    "correo",
    "mensajes",
    "correu",
    "missatge",
    "from",
    "de",
    "urgent",
    "urgente",
    "summary",
    "resumen",
}
DESKTOP_HINT_FALLBACKS = (
    "open app",
    "launch app",
    "start app",
    "open application",
    "read window",
    "what is in the",
    "what does",
    "show me the screen",
    "click",
    "press button",
    "tap",
    "select",
    "type",
    "enter text",
    "fill in",
    "screenshot",
    "capture screen",
    "switch to",
    "focus on",
)
DOCUMENT_HINT_FALLBACKS = (
    "read document",
    "open document",
    "read pdf",
    "read docx",
    "read odt",
    "summarize document",
    "summarize pdf",
    "what does the document say",
    "what is in the file",
    "write a document",
    "create a document",
    "write a report",
    "create a report",
    "write a letter",
    "open in libreoffice",
    "export to pdf",
    "save as pdf",
)
BROWSER_HINT_FALLBACKS = (
    "open url",
    "go to",
    "navigate to",
    "visit",
    "read the page",
    "what does the page say",
    "fetch",
    "browse to",
    "open website",
    "open site",
    "search the web",
    "look up online",
    "find online",
    "what is on",
    "read the website",
    "open firefox",
    "open chrome",
    "open edge",
    "open in browser",
    "show me the website",
)
CALENDAR_HINT_FALLBACKS = (
    "calendar",
    "events",
    "schedule",
    "agenda",
    "what do i have today",
    "what is today",
    "today's events",
    "this week",
    "next week",
    "upcoming",
    "appointments",
    "do i have anything",
    "what is scheduled",
    "show me my calendar",
    "my schedule",
    "read ics",
    "open ics",
    "ics file",
)
PACKAGE_SEARCH_TERMS = (
    "app",
    "application",
    "browser",
    "client",
    "compiler",
    "editor",
    "ide",
    "package",
    "packages",
    "player",
    "software",
    "terminal",
    "tool",
    "tools",
)


def get_active_realm_name() -> str:
    realm_name = os.getenv("INANNA_REALM", DEFAULT_REALM).strip()
    return realm_name or DEFAULT_REALM


def load_filesystem_domain_hints(
    signals_path: Path = FILESYSTEM_SIGNAL_PATH,
) -> list[str]:
    try:
        payload = json.loads(signals_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return list(FILESYSTEM_HINT_FALLBACKS)

    domain_hints = payload.get("domain_hints", {})
    if not isinstance(domain_hints, dict):
        return list(FILESYSTEM_HINT_FALLBACKS)
    hints = domain_hints.get("filesystem", [])
    if not isinstance(hints, list):
        return list(FILESYSTEM_HINT_FALLBACKS)

    cleaned = [str(item).strip().lower() for item in hints if str(item).strip()]
    return cleaned or list(FILESYSTEM_HINT_FALLBACKS)


def load_process_domain_hints(
    signals_path: Path = FILESYSTEM_SIGNAL_PATH,
) -> list[str]:
    try:
        payload = json.loads(signals_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return list(PROCESS_HINT_FALLBACKS)

    domain_hints = payload.get("domain_hints", {})
    if not isinstance(domain_hints, dict):
        return list(PROCESS_HINT_FALLBACKS)
    hints = domain_hints.get("process", [])
    if not isinstance(hints, list):
        return list(PROCESS_HINT_FALLBACKS)

    cleaned = [str(item).strip().lower() for item in hints if str(item).strip()]
    return cleaned or list(PROCESS_HINT_FALLBACKS)


def load_package_domain_hints(
    signals_path: Path = FILESYSTEM_SIGNAL_PATH,
) -> list[str]:
    try:
        payload = json.loads(signals_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return list(PACKAGE_HINT_FALLBACKS)

    domain_hints = payload.get("domain_hints", {})
    if not isinstance(domain_hints, dict):
        return list(PACKAGE_HINT_FALLBACKS)
    hints = domain_hints.get("packages", [])
    if not isinstance(hints, list):
        return list(PACKAGE_HINT_FALLBACKS)

    cleaned = [str(item).strip().lower() for item in hints if str(item).strip()]
    return cleaned or list(PACKAGE_HINT_FALLBACKS)


def load_communication_domain_hints(
    signals_path: Path = FILESYSTEM_SIGNAL_PATH,
) -> list[str]:
    try:
        payload = json.loads(signals_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return list(COMMUNICATION_HINT_FALLBACKS)

    domain_hints = payload.get("domain_hints", {})
    if not isinstance(domain_hints, dict):
        return list(COMMUNICATION_HINT_FALLBACKS)
    hints = domain_hints.get("communication", [])
    if not isinstance(hints, list):
        return list(COMMUNICATION_HINT_FALLBACKS)

    cleaned = [str(item).strip().lower() for item in hints if str(item).strip()]
    return cleaned or list(COMMUNICATION_HINT_FALLBACKS)


def load_email_domain_hints(
    signals_path: Path = FILESYSTEM_SIGNAL_PATH,
) -> list[str]:
    try:
        payload = json.loads(signals_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return list(EMAIL_HINT_FALLBACKS)

    domain_hints = payload.get("domain_hints", {})
    if not isinstance(domain_hints, dict):
        return list(EMAIL_HINT_FALLBACKS)
    hints = domain_hints.get("email", [])
    if not isinstance(hints, list):
        return list(EMAIL_HINT_FALLBACKS)

    cleaned = [str(item).strip().lower() for item in hints if str(item).strip()]
    return cleaned or list(EMAIL_HINT_FALLBACKS)


def load_desktop_domain_hints(
    signals_path: Path = FILESYSTEM_SIGNAL_PATH,
) -> list[str]:
    try:
        payload = json.loads(signals_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return list(DESKTOP_HINT_FALLBACKS)

    domain_hints = payload.get("domain_hints", {})
    if not isinstance(domain_hints, dict):
        return list(DESKTOP_HINT_FALLBACKS)
    hints = domain_hints.get("desktop", [])
    if not isinstance(hints, list):
        return list(DESKTOP_HINT_FALLBACKS)

    cleaned = [str(item).strip().lower() for item in hints if str(item).strip()]
    return cleaned or list(DESKTOP_HINT_FALLBACKS)


def load_document_domain_hints(
    signals_path: Path = FILESYSTEM_SIGNAL_PATH,
) -> list[str]:
    try:
        payload = json.loads(signals_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return list(DOCUMENT_HINT_FALLBACKS)

    domain_hints = payload.get("domain_hints", {})
    if not isinstance(domain_hints, dict):
        return list(DOCUMENT_HINT_FALLBACKS)
    hints = domain_hints.get("document", [])
    if not isinstance(hints, list):
        return list(DOCUMENT_HINT_FALLBACKS)

    cleaned = [str(item).strip().lower() for item in hints if str(item).strip()]
    return cleaned or list(DOCUMENT_HINT_FALLBACKS)


def load_browser_domain_hints(
    signals_path: Path = FILESYSTEM_SIGNAL_PATH,
) -> list[str]:
    try:
        payload = json.loads(signals_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return list(BROWSER_HINT_FALLBACKS)

    domain_hints = payload.get("domain_hints", {})
    if not isinstance(domain_hints, dict):
        return list(BROWSER_HINT_FALLBACKS)
    hints = domain_hints.get("browser", [])
    if not isinstance(hints, list):
        return list(BROWSER_HINT_FALLBACKS)

    cleaned = [str(item).strip().lower() for item in hints if str(item).strip()]
    return cleaned or list(BROWSER_HINT_FALLBACKS)


def load_calendar_domain_hints(
    signals_path: Path = FILESYSTEM_SIGNAL_PATH,
) -> list[str]:
    try:
        payload = json.loads(signals_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return list(CALENDAR_HINT_FALLBACKS)

    domain_hints = payload.get("domain_hints", {})
    if not isinstance(domain_hints, dict):
        return list(CALENDAR_HINT_FALLBACKS)
    hints = domain_hints.get("calendar", [])
    if not isinstance(hints, list):
        return list(CALENDAR_HINT_FALLBACKS)

    cleaned = [str(item).strip().lower() for item in hints if str(item).strip()]
    return cleaned or list(CALENDAR_HINT_FALLBACKS)


def normalize_request_fragment(value: str) -> str:
    cleaned = str(value or "").strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {'"', "'"}:
        cleaned = cleaned[1:-1].strip()
    return cleaned.rstrip(".,;:!?")


def normalize_filesystem_path(value: str) -> str:
    cleaned = normalize_request_fragment(value)
    lowered = cleaned.lower()
    for prefix in ("the ",):
        if lowered.startswith(prefix):
            cleaned = cleaned[len(prefix) :].strip()
            lowered = cleaned.lower()
    for suffix in (" folder", " directory"):
        if lowered.endswith(suffix):
            cleaned = cleaned[: -len(suffix)].strip()
            lowered = cleaned.lower()
    if lowered in {"home", "home directory", "my home"}:
        return str(Path.home())
    if lowered.startswith("my "):
        remainder = cleaned[3:].strip()
        special = {
            "documents": Path.home() / "Documents",
            "downloads": Path.home() / "Downloads",
            "desktop": Path.home() / "Desktop",
            "pictures": Path.home() / "Pictures",
            "music": Path.home() / "Music",
            "videos": Path.home() / "Videos",
        }
        return str(special.get(remainder.lower(), Path.home() / remainder))
    return cleaned


def normalize_document_path(value: str) -> str:
    cleaned = normalize_request_fragment(value)
    lowered = cleaned.lower()
    for prefix in ("the document ", "document ", "the file ", "file ", "the pdf ", "pdf "):
        if lowered.startswith(prefix):
            cleaned = cleaned[len(prefix) :].strip()
            lowered = cleaned.lower()
    for suffix in (" in libreoffice", " with libreoffice", " to pdf", " as pdf"):
        if lowered.endswith(suffix):
            cleaned = cleaned[: -len(suffix)].strip()
            lowered = cleaned.lower()
    return cleaned.strip().strip('"')


def normalize_url_fragment(value: str) -> str:
    cleaned = normalize_request_fragment(value).strip()
    cleaned = cleaned.strip("<>[]()")
    return cleaned


def normalize_search_pattern(value: str) -> str:
    cleaned = normalize_request_fragment(value)
    lowered = cleaned.lower()
    if lowered.endswith(" files"):
        cleaned = cleaned[:-6].strip()
        lowered = cleaned.lower()
    alias = FILESYSTEM_PATTERN_ALIASES.get(lowered)
    if alias:
        return alias
    if cleaned.startswith("."):
        return f"*{cleaned}"
    return cleaned or "*"


def build_tool_request_query(tool_name: str, params: dict[str, Any]) -> str:
    if tool_name == "search_files":
        directory = str(params.get("directory", "")).strip()
        pattern = str(params.get("pattern", "")).strip()
        return f"{directory} | {pattern}".strip(" |")
    if tool_name == "list_processes":
        return str(params.get("filter", "")).strip() or "all"
    if tool_name == "system_info":
        return "system"
    if tool_name == "kill_process":
        return str(params.get("pid", "")).strip()
    if tool_name == "run_command":
        return str(params.get("command", "")).strip()
    if tool_name == "list_packages":
        return str(params.get("filter", "")).strip() or "installed"
    if tool_name in {"search_packages", "install_package", "remove_package"}:
        return str(params.get("package", "") or params.get("query", "")).strip()
    if tool_name == "desktop_open_app":
        return str(params.get("app", "")).strip()
    if tool_name == "desktop_read_window":
        return str(params.get("app_name", "")).strip() or "active window"
    if tool_name == "desktop_click":
        return str(params.get("label", "")).strip()
    if tool_name == "desktop_type":
        return str(params.get("text", "")).strip()
    if tool_name == "desktop_screenshot":
        return str(params.get("app_name", "")).strip() or "desktop"
    if tool_name in FILESYSTEM_TOOL_NAMES:
        return str(params.get("path", "")).strip()
    return str(params.get("query", "")).strip()


def extract_filesystem_tool_request(
    text: str,
    hints: list[str] | None = None,
) -> dict[str, Any] | None:
    normalized = str(text or "").strip()
    lowered = normalized.lower()
    active_hints = hints or load_filesystem_domain_hints()
    hint_match = any(hint in lowered for hint in active_hints)
    if not hint_match and not re.match(r"^(read|open|list|find|search|write|save|create|what is in)\b", lowered):
        return None

    write_match = re.match(
        r"^(?P<verb>overwrite|write|save|create)\s+(?:a\s+)?file(?:\s+called)?\s+(?P<path>.+?)\s+(?:with|containing)\s+(?P<content>.+)$",
        normalized,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if write_match:
        params = {
            "path": normalize_filesystem_path(write_match.group("path")),
            "content": normalize_request_fragment(write_match.group("content")),
            "overwrite": write_match.group("verb").strip().lower() == "overwrite",
        }
        return {
            "tool": "write_file",
            "params": params,
            "query": build_tool_request_query("write_file", params),
            "reason": "File write operations require governed tool use.",
        }

    search_match = re.match(
        r"^(?:find|search(?:\s+for)?)\s+(?:all\s+)?(?P<pattern>.+?)\s+files?\s+(?:in|under)\s+(?P<directory>.+)$",
        normalized,
        flags=re.IGNORECASE,
    )
    if search_match:
        params = {
            "directory": normalize_filesystem_path(search_match.group("directory")),
            "pattern": normalize_search_pattern(search_match.group("pattern")),
        }
        return {
            "tool": "search_files",
            "params": params,
            "query": build_tool_request_query("search_files", params),
            "reason": "File search routed to OPERATOR tool use.",
        }

    info_match = re.match(
        r"^(?:what is|show)(?:\s+me)?(?:\s+the)?\s+(?:size|file info|info|metadata)\s+(?:of|for)?\s+(?P<path>.+)$",
        normalized,
        flags=re.IGNORECASE,
    )
    if info_match:
        params = {"path": normalize_filesystem_path(info_match.group("path"))}
        return {
            "tool": "file_info",
            "params": params,
            "query": build_tool_request_query("file_info", params),
            "reason": "File metadata routed to OPERATOR tool use.",
        }

    read_match = re.match(
        r"^(?:read|open|show)(?:\s+me)?(?:\s+the)?\s+file(?:\s+at)?\s+(?P<path>.+)$",
        normalized,
        flags=re.IGNORECASE,
    )
    if read_match:
        params = {"path": normalize_filesystem_path(read_match.group("path"))}
        return {
            "tool": "read_file",
            "params": params,
            "query": build_tool_request_query("read_file", params),
            "reason": "File read routed to OPERATOR tool use.",
        }

    list_match = re.match(
        r"^(?:list|show)(?:\s+me)?(?:\s+the)?\s+(?:files?|contents?)\s+(?:in|of)\s+(?P<path>.+)$",
        normalized,
        flags=re.IGNORECASE,
    )
    if list_match:
        params = {"path": normalize_filesystem_path(list_match.group("path"))}
        return {
            "tool": "list_dir",
            "params": params,
            "query": build_tool_request_query("list_dir", params),
            "reason": "Directory listing routed to OPERATOR tool use.",
        }

    if lowered.startswith("what is in "):
        params = {"path": normalize_filesystem_path(normalized[len("what is in ") :])}
        return {
            "tool": "list_dir",
            "params": params,
            "query": build_tool_request_query("list_dir", params),
            "reason": "Directory listing routed to OPERATOR tool use.",
        }

    if lowered.startswith("list "):
        params = {"path": normalize_filesystem_path(normalized[len("list ") :])}
        return {
            "tool": "list_dir",
            "params": params,
            "query": build_tool_request_query("list_dir", params),
            "reason": "Directory listing routed to OPERATOR tool use.",
        }

    return None


def filesystem_request_requires_proposal(
    filesystem_request: dict[str, Any],
    filesystem_faculty: FileSystemFaculty,
) -> bool:
    tool_name = str(filesystem_request.get("tool", "")).strip().lower()
    params = filesystem_request.get("params", {})
    if not isinstance(params, dict):
        params = {}
    if tool_name == "write_file":
        return True
    if tool_name == "read_file":
        path = normalize_filesystem_path(str(params.get("path", "")))
        if not path:
            return True
        return not filesystem_faculty.is_safe_read(Path(path).expanduser())
    return False


def detect_filesystem_tool_action(
    text: str,
    filesystem_faculty: FileSystemFaculty,
    profile_manager: ProfileManager | None = None,
    current_user: UserRecord | None = None,
    active_token: SessionToken | None = None,
) -> dict[str, Any] | None:
    request = extract_filesystem_tool_request(text)
    if request is None:
        return None
    requires_proposal = filesystem_request_requires_proposal(request, filesystem_faculty)
    persistent_trusted_tools: list[str] = []
    if profile_manager is not None and current_user is not None and active_token is not None:
        profile = profile_manager.load(current_user.user_id)
        if profile is not None:
            persistent_trusted_tools = normalize_trusted_tools(profile.persistent_trusted_tools)
    return {
        **request,
        "requires_proposal": requires_proposal,
        "persistent_trusted_tools": persistent_trusted_tools,
    }


def _looks_like_document_path(value: str) -> bool:
    cleaned = normalize_document_path(value)
    if not cleaned:
        return False
    suffix = Path(cleaned).suffix.lower()
    return suffix in {
        ".txt",
        ".md",
        ".rst",
        ".log",
        ".docx",
        ".odt",
        ".pdf",
        ".xlsx",
        ".xls",
        ".ods",
        ".csv",
    }


def extract_document_tool_request(
    text: str,
    hints: list[str] | None = None,
) -> dict[str, Any] | None:
    normalized = str(text or "").strip()
    lowered = normalized.lower()
    if (
        lowered.startswith("read file")
        or lowered.startswith("read the file")
        or lowered.startswith("show file")
        or lowered.startswith("show the file")
        or lowered.startswith("open file at")
        or lowered.startswith("open the file at")
    ):
        return None
    active_hints = hints or load_document_domain_hints()
    hint_match = any(hint in lowered for hint in active_hints)

    open_lo_match = re.match(
        r"^(?:open)(?:\s+the)?(?:\s+document|\s+file)?\s+(?P<path>.+?)\s+(?:in|with)\s+libreoffice$",
        normalized,
        flags=re.IGNORECASE,
    )
    if open_lo_match:
        path = normalize_document_path(open_lo_match.group("path"))
        if _looks_like_document_path(path):
            return {
                "tool": "doc_open",
                "params": {"path": path},
                "query": path,
                "reason": "LibreOffice document open routed to Document Faculty.",
            }

    export_match = re.match(
        r"^(?:export|save)\s+(?P<path>.+?)\s+(?:to|as)\s+pdf(?:\s+in\s+(?P<output_dir>.+))?$",
        normalized,
        flags=re.IGNORECASE,
    )
    if export_match:
        path = normalize_document_path(export_match.group("path"))
        if _looks_like_document_path(path):
            params: dict[str, str] = {"path": path}
            output_dir = normalize_request_fragment(export_match.group("output_dir") or "")
            if output_dir:
                params["output_dir"] = output_dir
            return {
                "tool": "doc_export_pdf",
                "params": params,
                "query": path,
                "reason": "Document PDF export routed to Document Faculty.",
            }

    read_match = re.match(
        r"^(?:read|open|summarize|explain)(?:\s+the)?(?:\s+document|\s+file|\s+pdf)?\s+(?P<path>.+)$",
        normalized,
        flags=re.IGNORECASE,
    )
    if read_match:
        path = normalize_document_path(read_match.group("path"))
        if _looks_like_document_path(path):
            return {
                "tool": "doc_read",
                "params": {"path": path},
                "query": path,
                "reason": "Document read routed to Document Faculty.",
            }

    write_match = re.match(
        r"^(?:write|create)(?:\s+a)?(?:\s+new)?\s+(?:document|report|letter|note)(?:\s+at|\s+to|\s+called|\s+named)?\s+(?P<path>\"[^\"]+\"|\\S+)\s*(?:with|saying|containing)?\s*(?P<content>.*)$",
        normalized,
        flags=re.IGNORECASE,
    )
    if write_match:
        path = normalize_document_path(write_match.group("path"))
        if path:
            suffix = Path(path).suffix.lower()
            format_name = suffix.lstrip(".") if suffix else "txt"
            return {
                "tool": "doc_write",
                "params": {
                    "path": path,
                    "content": normalize_request_fragment(write_match.group("content") or ""),
                    "format": format_name,
                },
                "query": path,
                "reason": "Document creation routed to Document Faculty.",
            }

    if hint_match and _looks_like_document_path(normalized):
        path = normalize_document_path(normalized)
        return {
            "tool": "doc_read",
            "params": {"path": path},
            "query": path,
            "reason": "Document read routed to Document Faculty.",
        }

    return None


def document_request_requires_proposal(document_request: dict[str, Any]) -> bool:
    tool_name = str(document_request.get("tool", "")).strip().lower()
    return tool_name != "doc_read"


def detect_document_tool_action(
    text: str,
    document_workflows: DocumentWorkflows | None = None,
) -> dict[str, Any] | None:
    del document_workflows
    request = extract_document_tool_request(text)
    if request is None:
        return None
    return {
        **request,
        "requires_proposal": document_request_requires_proposal(request),
    }


def extract_calendar_tool_request(
    text: str,
    hints: list[str] | None = None,
) -> dict[str, Any] | None:
    normalized = str(text or "").strip()
    lowered = normalized.lower()
    active_hints = hints or load_calendar_domain_hints()
    hint_match = any(hint in lowered for hint in active_hints)

    ics_match = re.match(
        r"^(?:read|open|parse)(?:\s+the)?\s+ics(?:\s+file)?(?:\s+at)?\s+(?P<path>.+)$",
        normalized,
        flags=re.IGNORECASE,
    )
    if ics_match:
        path = normalize_document_path(ics_match.group("path"))
        return {
            "tool": "calendar_read_ics",
            "params": {"path": path},
            "query": path,
            "reason": "ICS calendar file routed to Calendar Faculty.",
        }

    next_days_match = re.match(
        r"^(?:show|what are|read)?(?:\s+my)?\s*(?:calendar|events|schedule|agenda)?\s*(?:for\s+)?next\s+(?P<days>\d+)\s+days?$",
        normalized,
        flags=re.IGNORECASE,
    )
    if next_days_match:
        days = max(1, int(next_days_match.group("days")))
        return {
            "tool": "calendar_upcoming",
            "params": {"days": days},
            "query": f"next {days} days",
            "reason": "Upcoming calendar events routed to Calendar Faculty.",
        }

    today_phrases = (
        "what do i have today",
        "show my calendar today",
        "show me my calendar today",
        "today's events",
        "todays events",
        "what is on my calendar today",
        "what is scheduled today",
        "what's on my calendar today",
        # Spanish
        "que tengo hoy",
        "agenda de hoy",
        "eventos de hoy",
        # Catalan
        "que tinc avui",
        "agenda d'avui",
        "events d'avui",
        # Portuguese
        "agenda de hoje",
        "o que tenho hoje",
    )
    if any(phrase in lowered for phrase in today_phrases):
        return {
            "tool": "calendar_today",
            "params": {},
            "query": "today",
            "reason": "Today's calendar events routed to Calendar Faculty.",
        }

    upcoming_phrases = (
        "upcoming events",
        "show my calendar",
        "show me my calendar",
        "my schedule",
        "my agenda",
        "what is scheduled",
        "do i have anything",
    )
    if "next week" in lowered:
        return {
            "tool": "calendar_upcoming",
            "params": {"days": 14},
            "query": "next 14 days",
            "reason": "Next-week calendar view routed to Calendar Faculty.",
        }
    if any(phrase in lowered for phrase in upcoming_phrases):
        return {
            "tool": "calendar_upcoming",
            "params": {"days": 7},
            "query": "next 7 days",
            "reason": "Upcoming calendar events routed to Calendar Faculty.",
        }

    if hint_match and "today" in lowered:
        return {
            "tool": "calendar_today",
            "params": {},
            "query": "today",
            "reason": "Today's calendar events routed to Calendar Faculty.",
        }
    if hint_match:
        return {
            "tool": "calendar_upcoming",
            "params": {"days": 7},
            "query": "next 7 days",
            "reason": "Upcoming calendar events routed to Calendar Faculty.",
        }
    return None


def detect_calendar_tool_action(
    text: str,
    calendar_workflows: CalendarWorkflows | None = None,
) -> dict[str, Any] | None:
    del calendar_workflows
    request = extract_calendar_tool_request(text)
    if request is None:
        return None
    return {
        **request,
        "requires_proposal": False,
    }


def extract_browser_tool_request(
    text: str,
    hints: list[str] | None = None,
) -> dict[str, Any] | None:
    normalized = str(text or "").strip()
    lowered = normalized.lower()
    active_hints = hints or load_browser_domain_hints()
    hint_match = any(hint in lowered for hint in active_hints)

    open_match = re.match(
        r"^(?:open|go to|navigate to|visit|browse to)\s+(?P<url>\S+)(?:\s+in\s+(?P<browser>firefox|chrome|edge))?$",
        normalized,
        flags=re.IGNORECASE,
    )
    if open_match:
        params = {
            "url": normalize_url_fragment(open_match.group("url")),
            "browser": normalize_request_fragment(open_match.group("browser") or "firefox").lower(),
        }
        return {
            "tool": "browser_open",
            "params": params,
            "query": params["url"],
            "reason": "Visible browser navigation requires governed tool use.",
        }

    read_match = re.match(
        r"^(?:read|fetch)(?:\s+the)?(?:\s+page|\s+website|\s+site)?(?:\s+at)?\s+(?P<url>\S+)(?:\s+with\s+js)?$",
        normalized,
        flags=re.IGNORECASE,
    )
    if read_match:
        url = normalize_url_fragment(read_match.group("url"))
        params = {"url": url, "js": bool(re.search(r"\bwith\s+js\b", lowered))}
        return {
            "tool": "browser_read",
            "params": params,
            "query": url,
            "reason": "Browser page reading routed to Browser Faculty.",
        }

    search_match = re.match(
        r"^(?:search the web for|look up|look up online|find online)\s+(?P<query>.+)$",
        normalized,
        flags=re.IGNORECASE,
    )
    if search_match:
        query = normalize_request_fragment(search_match.group("query"))
        return {
            "tool": "browser_search",
            "params": {"query": query},
            "query": query,
            "reason": "Browser web search routed to Browser Faculty.",
        }

    if hint_match and re.match(r"^(?:what is|who is|where is|when is|why is|how is)\s+.+\?$", normalized, flags=re.IGNORECASE):
        query = normalize_request_fragment(normalized)
        return {
            "tool": "browser_search",
            "params": {"query": query},
            "query": query,
            "reason": "Browser web search routed to Browser Faculty.",
        }

    return None


def browser_request_requires_proposal(browser_request: dict[str, Any]) -> bool:
    tool_name = str(browser_request.get("tool", "")).strip().lower()
    return tool_name == "browser_open"


def detect_browser_tool_action(
    text: str,
    browser_workflows: BrowserWorkflows | None = None,
) -> dict[str, Any] | None:
    del browser_workflows
    request = extract_browser_tool_request(text)
    if request is None:
        return None
    return {
        **request,
        "requires_proposal": browser_request_requires_proposal(request),
    }


def extract_process_tool_request(
    text: str,
    hints: list[str] | None = None,
) -> dict[str, Any] | None:
    normalized = str(text or "").strip()
    lowered = normalized.lower()
    active_hints = hints or load_process_domain_hints()
    hint_match = any(hint in lowered for hint in active_hints)
    if not hint_match and not re.match(r"^(show|list|kill|terminate|run|what is using|how is the system)\b", lowered):
        return None

    run_match = re.match(
        r"^(?:run(?:\s+command)?|execute(?:\s+command)?)\s+(?P<command>.+)$",
        normalized,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if run_match:
        params = {
            "command": normalize_request_fragment(run_match.group("command")),
            "timeout": 30,
        }
        return {
            "tool": "run_command",
            "params": params,
            "query": build_tool_request_query("run_command", params),
            "reason": "Shell command execution requires governed tool use.",
        }

    kill_match = re.match(
        r"^(?:kill|terminate)(?:\s+the)?(?:\s+process)?(?:\s+pid)?\s+(?P<pid>\d+)\b",
        normalized,
        flags=re.IGNORECASE,
    )
    if kill_match:
        params = {"pid": int(kill_match.group("pid"))}
        return {
            "tool": "kill_process",
            "params": params,
            "query": build_tool_request_query("kill_process", params),
            "reason": "Process termination requires governed tool use.",
        }

    if any(
        phrase in lowered
        for phrase in (
            "how is the system",
            "system info",
            "system health",
            "uptime",
            "disk space",
            "performance",
        )
    ):
        params: dict[str, Any] = {}
        return {
            "tool": "system_info",
            "params": params,
            "query": build_tool_request_query("system_info", params),
            "reason": "System inspection routed to OPERATOR tool use.",
        }

    if "what is using" in lowered and ("memory" in lowered or "ram" in lowered):
        params = {"filter": "", "sort": "memory", "limit": 20}
        return {
            "tool": "list_processes",
            "params": params,
            "query": build_tool_request_query("list_processes", params),
            "reason": "Process inspection routed to OPERATOR tool use.",
        }

    if "what is using" in lowered and "cpu" in lowered:
        params = {"filter": "", "sort": "cpu", "limit": 20}
        return {
            "tool": "list_processes",
            "params": params,
            "query": build_tool_request_query("list_processes", params),
            "reason": "Process inspection routed to OPERATOR tool use.",
        }

    list_match = re.match(
        r"^(?:show|list)(?:\s+me)?(?:\s+all)?\s+(?P<filter>.+?)\s+process(?:es)?$",
        normalized,
        flags=re.IGNORECASE,
    )
    if list_match:
        params = {
            "filter": normalize_request_fragment(list_match.group("filter")),
            "sort": "memory",
            "limit": 20,
        }
        return {
            "tool": "list_processes",
            "params": params,
            "query": build_tool_request_query("list_processes", params),
            "reason": "Process inspection routed to OPERATOR tool use.",
        }

    if lowered in {"list processes", "show processes", "show me processes"}:
        params = {"filter": "", "sort": "memory", "limit": 20}
        return {
            "tool": "list_processes",
            "params": params,
            "query": build_tool_request_query("list_processes", params),
            "reason": "Process inspection routed to OPERATOR tool use.",
        }

    return None


def process_request_requires_proposal(process_request: dict[str, Any]) -> bool:
    tool_name = str(process_request.get("tool", "")).strip().lower()
    return tool_name in {"kill_process", "run_command"}


def detect_process_tool_action(
    text: str,
    process_faculty: ProcessFaculty | None = None,
) -> dict[str, Any] | None:
    del process_faculty
    request = extract_process_tool_request(text)
    if request is None:
        return None
    return {
        **request,
        "requires_proposal": process_request_requires_proposal(request),
    }


def _strip_common_request_prefixes(value: str) -> tuple[str, str]:
    normalized = str(value or "").strip()
    lowered = normalized.lower()
    pattern = r"^(?:inanna[,\s]+|hey inanna[,\s]+|please[,\s]+|can you[,\s]+)"
    normalized_stripped = re.sub(pattern, "", normalized, flags=re.IGNORECASE).strip()
    lowered_stripped = re.sub(pattern, "", lowered, flags=re.IGNORECASE).strip()
    return normalized_stripped, lowered_stripped


def _looks_like_file_target(candidate: str) -> bool:
    cleaned = str(candidate or "").strip().lower()
    if not cleaned:
        return False
    if cleaned.startswith(("file ", "the file ", "~/", "/", ".\\", "..\\", "c:\\", "d:\\")):
        return True
    return any(
        cleaned.endswith(ext)
        for ext in (
            ".txt",
            ".md",
            ".json",
            ".py",
            ".csv",
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".png",
            ".jpg",
            ".jpeg",
        )
    )


def extract_desktop_tool_request(
    text: str,
    hints: list[str] | None = None,
) -> dict[str, Any] | None:
    normalized = str(text or "").strip()
    lowered = normalized.lower()
    normalized_stripped, lowered_stripped = _strip_common_request_prefixes(normalized)
    active_hints = hints or load_desktop_domain_hints()
    hint_match = any(hint in lowered for hint in active_hints)
    if not hint_match and not re.match(
        r"^(open|launch|start|switch to|focus on|read|show|what is in|what does|click|press|tap|select|type|enter|take|capture|screenshot)\b",
        lowered_stripped,
    ):
        return None

    screenshot_match = re.match(
        r"^(?:take|capture)(?:\s+(?:a|the))?\s+screenshot(?:\s+(?:of|for)\s+(?P<app>.+))?$",
        normalized_stripped,
        flags=re.IGNORECASE,
    )
    if screenshot_match or lowered_stripped in {
        "screenshot",
        "take a screenshot",
        "capture screen",
        "capture the screen",
    }:
        params = {
            "app_name": normalize_request_fragment(
                (screenshot_match.group("app") if screenshot_match else "") or ""
            ),
        }
        return {
            "tool": "desktop_screenshot",
            "params": params,
            "query": build_tool_request_query("desktop_screenshot", params),
            "reason": "Desktop observation routed to OPERATOR tool use.",
        }

    read_match = re.match(
        r"^(?:read|show)(?:\s+me)?(?:\s+the)?\s+(?P<app>.+?)\s+window$",
        normalized_stripped,
        flags=re.IGNORECASE,
    )
    if not read_match:
        read_match = re.match(
            r"^(?:what is in|what does)(?:\s+the)?\s+(?P<app>.+?)\s+window(?:\s+say)?$",
            normalized_stripped,
            flags=re.IGNORECASE,
        )
    if read_match:
        params = {
            "app_name": normalize_request_fragment(read_match.group("app")),
            "max_depth": 5,
        }
        return {
            "tool": "desktop_read_window",
            "params": params,
            "query": build_tool_request_query("desktop_read_window", params),
            "reason": "Desktop window reading routed to OPERATOR tool use.",
        }

    click_match = re.match(
        r"^(?:click|press|tap|select)(?:\s+the)?\s+(?P<label>.+?)(?:\s+(?:button|link|tab|icon))?(?:\s+(?:in|on)\s+(?P<app>.+))?$",
        normalized_stripped,
        flags=re.IGNORECASE,
    )
    if click_match:
        params = {
            "label": normalize_request_fragment(click_match.group("label")),
            "app_name": normalize_request_fragment(click_match.group("app") or ""),
        }
        return {
            "tool": "desktop_click",
            "params": params,
            "query": build_tool_request_query("desktop_click", params),
            "reason": "Desktop clicking routed to OPERATOR tool use.",
        }

    type_match = re.match(
        r"^(?:type|enter(?:\s+text)?)\s+(?P<text>.+?)(?:\s+and\s+(?P<submit>submit|send|press enter))?$",
        normalized_stripped,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if type_match:
        params = {
            "text": normalize_request_fragment(type_match.group("text")),
            "submit": bool(type_match.group("submit")),
        }
        return {
            "tool": "desktop_type",
            "params": params,
            "query": build_tool_request_query("desktop_type", params),
            "reason": "Desktop typing requires governed tool use.",
        }

    open_match = re.match(
        r"^(?:open|launch|start|switch to|focus on)(?:\s+(?:the|app|application))?\s+(?P<app>.+)$",
        normalized_stripped,
        flags=re.IGNORECASE,
    )
    if open_match:
        app = normalize_request_fragment(open_match.group("app"))
        if app.lower().endswith(" window") or _looks_like_file_target(app):
            return None
        params = {"app": app}
        return {
            "tool": "desktop_open_app",
            "params": params,
            "query": build_tool_request_query("desktop_open_app", params),
            "reason": "Desktop app launch requires governed tool use.",
        }

    return None


def desktop_request_requires_proposal(desktop_request: dict[str, Any]) -> bool:
    tool_name = str(desktop_request.get("tool", "")).strip().lower()
    params = desktop_request.get("params", {})
    if not isinstance(params, dict):
        params = {}
    if tool_name in {"desktop_open_app", "desktop_type"}:
        return True
    if tool_name == "desktop_click":
        return is_consequential_label(str(params.get("label", "")))
    return False


def communication_request_requires_proposal(
    communication_request: dict[str, Any],
) -> bool:
    return str(communication_request.get("tool", "")).strip().lower() == "comm_send_message"


def email_request_requires_proposal(email_request: dict[str, Any]) -> bool:
    return str(email_request.get("tool", "")).strip().lower() in {"email_compose", "email_reply"}


def display_communication_app_name(app: str) -> str:
    normalized = normalize_app_name(app)
    labels = {
        "signal": "Signal",
        "whatsapp": "WhatsApp",
        "telegram": "Telegram",
        "discord": "Discord",
        "slack": "Slack",
    }
    return labels.get(normalized, normalized.title() or "Communication App")


def display_email_app_name(app: str) -> str:
    normalized = normalize_email_app(app)
    labels = {
        "thunderbird": "Thunderbird",
        "protonmail": "Proton Mail",
        "evolution": "Evolution",
        "geary": "Geary",
    }
    return labels.get(normalized, normalized.title() or "Email Client")


def build_communication_send_query(app: str, contact: str, message: str) -> str:
    return (
        f'{display_communication_app_name(app)} -> {normalize_request_fragment(contact)}: '
        f'"{str(message or "").strip()}"'
    )


def build_email_compose_query(app: str, recipient: str, subject: str) -> str:
    return (
        f"{display_email_app_name(app)} -> {normalize_request_fragment(recipient)}"
        f' | "{normalize_request_fragment(subject)}"'
    )


def build_email_reply_query(app: str, subject_or_sender: str) -> str:
    return f"{display_email_app_name(app)} reply -> {normalize_request_fragment(subject_or_sender)}"


def extract_communication_tool_request(
    text: str,
    hints: list[str] | None = None,
    conversation_context: list[dict[str, str]] | None = None,
) -> dict[str, Any] | None:
    normalized = str(text or "").strip()
    lowered = normalized.lower()
    prefix_pattern = r"^(?:inanna[,\s]+|hey inanna[,\s]+|please[,\s]+|can you[,\s]+)"
    prefix_stripped = re.sub(prefix_pattern, "", lowered, flags=re.IGNORECASE).strip()
    normalized_stripped = re.sub(prefix_pattern, "", normalized, flags=re.IGNORECASE).strip()

    active_hints = hints or load_communication_domain_hints()
    app_pattern = r"signal(?: messenger)?|whatsapp|whats app|wa|telegram|tg"
    app_mentioned = re.search(app_pattern, prefix_stripped, flags=re.IGNORECASE) is not None
    hint_match = any(hint in lowered for hint in active_hints)
    if not app_mentioned and not hint_match:
        return None

    if _has_email_comm_signal(lowered):
        intent_result = _extract_intent_with_timeout(
            normalized,
            conversation_context=conversation_context,
        )
        if intent_result.success and intent_result.confidence >= 0.75:
            tool_request = intent_result.to_tool_request()
            if tool_request is not None and str(tool_request.get("tool", "")) in COMMUNICATION_TOOL_NAMES:
                return tool_request

    send_patterns = (
        re.match(
            rf"^(?:send|text)\s+(?:a\s+)?(?P<app>{app_pattern})\s+(?:message\s+)?to\s+(?P<contact>.+?)\s+(?:saying|that says)\s+(?P<message>.+)$",
            normalized_stripped,
            flags=re.IGNORECASE,
        ),
        re.match(
            rf"^(?:send|text)\s+(?:a\s+)?message\s+to\s+(?P<contact>.+?)\s+on\s+(?P<app>{app_pattern})\s*(?::|saying)\s*(?P<message>.+)$",
            normalized_stripped,
            flags=re.IGNORECASE,
        ),
        re.match(
            rf"^(?:message|text)\s+(?P<contact>.+?)\s+on\s+(?P<app>{app_pattern})\s*:\s*(?P<message>.+)$",
            normalized_stripped,
            flags=re.IGNORECASE,
        ),
    )
    for send_match in send_patterns:
        if send_match:
            app = normalize_app_name(send_match.group("app"))
            contact = normalize_request_fragment(send_match.group("contact"))
            message = str(send_match.group("message") or "").strip()
            params = {
                "app": app,
                "contact": contact,
                "message": message,
                "mode": "draft",
            }
            return {
                "tool": "comm_send_message",
                "params": params,
                "query": build_communication_send_query(app, contact, message),
                "reason": "Communication send requires a governed two-stage send flow.",
            }

    read_patterns = (
        re.match(
            rf"^(?:read|check|show)(?:\s+my)?\s+(?P<app>{app_pattern})(?:\s+(?:messages?|inbox|chat))?$",
            prefix_stripped,
            flags=re.IGNORECASE,
        ),
        re.match(
            rf"^(?:read|check|show)\s+(?:messages?|inbox|chat)(?:\s+on)?\s+(?P<app>{app_pattern})$",
            prefix_stripped,
            flags=re.IGNORECASE,
        ),
    )
    for read_match in read_patterns:
        if read_match:
            app = normalize_app_name(read_match.group("app"))
            params = {"app": app}
            return {
                "tool": "comm_read_messages",
                "params": params,
                "query": f"{display_communication_app_name(app)} messages",
                "reason": "Communication message reading routed to workflow execution.",
            }

    list_patterns = (
        re.match(
            rf"^(?:list|show)(?:\s+my)?\s+(?P<app>{app_pattern})\s+contacts$",
            prefix_stripped,
            flags=re.IGNORECASE,
        ),
        re.match(
            rf"^(?:list|show)\s+contacts(?:\s+in|\s+on)?\s+(?P<app>{app_pattern})$",
            prefix_stripped,
            flags=re.IGNORECASE,
        ),
    )
    for list_match in list_patterns:
        if list_match:
            app = normalize_app_name(list_match.group("app"))
            params = {"app": app}
            return {
                "tool": "comm_list_contacts",
                "params": params,
                "query": f"{display_communication_app_name(app)} contacts",
                "reason": "Communication contact inspection routed to workflow execution.",
            }

    return None


def detect_communication_tool_action(
    text: str,
    communication_workflows: CommunicationWorkflows | None = None,
    conversation_context: list[dict[str, str]] | None = None,
) -> dict[str, Any] | None:
    del communication_workflows
    request = extract_communication_tool_request(
        text,
        conversation_context=conversation_context,
    )
    if request is None:
        return None
    return {
        **request,
        "requires_proposal": communication_request_requires_proposal(request),
    }


def extract_email_tool_request(
    text: str,
    hints: list[str] | None = None,
    conversation_context: list[dict[str, str]] | None = None,
) -> dict[str, Any] | None:
    normalized = str(text or "").strip()
    lowered = normalized.lower()
    prefix_pattern = r"^(?:inanna[,\s]+|hey inanna[,\s]+|please[,\s]+|can you[,\s]+)"
    prefix_stripped = re.sub(prefix_pattern, "", lowered, flags=re.IGNORECASE).strip()
    normalized_stripped = re.sub(prefix_pattern, "", normalized, flags=re.IGNORECASE).strip()
    app_pattern = r"thunderbird|thunder bird|tb|protonmail|proton mail|proton"
    active_hints = hints or load_email_domain_hints()
    hint_match = any(hint in lowered for hint in active_hints)
    app_match = re.search(app_pattern, prefix_stripped, flags=re.IGNORECASE) is not None
    # Natural phrase guard — catch "anything from X?", "urgentes?", etc.
    # even when they don't contain explicit email keywords
    natural_match = bool(re.match(
        r"^(?:anything|something|news)\s+from\s+[\w]",
        prefix_stripped, re.IGNORECASE
    )) or bool(re.match(
        r"^(?:urgent|important|critical|urgentes?|importantes?)(?:\s+|\??$)",
        prefix_stripped, re.IGNORECASE
    )) or bool(re.match(
        r"^(?:hola\s+)?tengo\s+(?:emails?|correos?|mensajes)",
        prefix_stripped, re.IGNORECASE
    )) or bool(re.match(
        r"^resumen\s+(?:de|del|correos?|emails?)",
        prefix_stripped, re.IGNORECASE
    ))
    if not hint_match and not app_match and not natural_match:
        return None

    if _has_email_comm_signal(lowered):
        intent_result = _extract_intent_with_timeout(
            normalized,
            conversation_context=conversation_context,
        )
        if intent_result is not None and intent_result.success and intent_result.confidence >= 0.75:
            tool_request = intent_result.to_tool_request()
            if tool_request is not None and str(tool_request.get("tool", "")) in EMAIL_TOOL_NAMES:
                return tool_request

    # "anything from X?" / "something from X?" — natural email search
    anything_from_match = re.match(
        r"^(?:anything|something|news|emails?|messages?|mail)\s+from\s+(?P<sender>[\w\s\-.]+?)\s*\??$",
        prefix_stripped, flags=re.IGNORECASE,
    )
    if anything_from_match:
        sender = normalize_request_fragment(anything_from_match.group("sender"))
        app = DEFAULT_EMAIL_CLIENT
        params = {"query": sender, "app": app}
        return {
            "tool": "email_search",
            "params": params,
            "query": f"Search for emails from {sender}",
            "reason": "Natural language email search (regex fallback)",
        }

    # "check email from X" / "look for X email"
    check_from_match = re.match(
        r"^(?:check|look\s+for|find|show\s+me)\s+(?:email|mail|message)?\s*from\s+(?P<sender>[\w\s\-]+?)\??$",
        prefix_stripped, flags=re.IGNORECASE,
    )
    if check_from_match:
        sender = normalize_request_fragment(check_from_match.group("sender"))
        params = {"subject_or_sender": sender, "app": DEFAULT_EMAIL_CLIENT}
        return {
            "tool": "email_read_message",
            "params": params,
            "query": f"Read email from {sender}",
            "reason": "Natural language email read (regex fallback)",
        }

    # "urgent emails?" / "urgentes?" / "important emails?"
    urgent_match = re.match(
        r"^(?:urgent|important|critical|urgentes?|importantes?)(?:\s+(?:emails?|mail|messages?))?\s*\??$",
        prefix_stripped, flags=re.IGNORECASE,
    )
    if urgent_match:
        params = {"app": DEFAULT_EMAIL_CLIENT, "urgency_only": True, "output_format": "summary"}
        return {
            "tool": "email_read_inbox",
            "params": params,
            "query": "Read inbox — urgent only",
            "reason": "Urgency email filter (regex fallback)",
        }

    # "last N emails" / "N últimos emails"
    last_n_match = re.match(
        r"^(?:last|latest|recent|últimos?|recientes?)\s+(?P<n>\d+)\s+(?:emails?|mail|messages?)\??$",
        prefix_stripped, flags=re.IGNORECASE,
    )
    if last_n_match:
        n = int(last_n_match.group("n"))
        params = {"app": DEFAULT_EMAIL_CLIENT, "max_emails": n, "output_format": "list"}
        return {
            "tool": "email_read_inbox",
            "params": params,
            "query": f"Read last {n} emails",
            "reason": "Email count request (regex fallback)",
        }

    # Spanish/Catalan "tengo emails" / "resumen de ayer" → inbox
    if re.match(r"^(?:hola\s+)?tengo\s+(?:emails?|correos?|mensajes)", prefix_stripped, re.IGNORECASE):
        params = {"app": DEFAULT_EMAIL_CLIENT, "output_format": "list"}
        return {
            "tool": "email_read_inbox",
            "params": params,
            "query": "Read inbox",
            "reason": "Spanish/Catalan inbox request (regex fallback)",
        }

    if re.match(r"^resumen\s+(?:de|del)\s+", prefix_stripped, re.IGNORECASE):
        # "resumen de ayer" → read inbox with period=yesterday
        period = "yesterday" if "ayer" in prefix_stripped or "ahir" in prefix_stripped else ""
        params = {"app": DEFAULT_EMAIL_CLIENT, "output_format": "summary"}
        if period:
            params["period"] = period
        return {
            "tool": "email_read_inbox",
            "params": params,
            "query": f"Email summary {'yesterday' if period else 'recent'}",
            "reason": "Spanish/Catalan email summary (regex fallback)",
        }

        # "do I have emails from X" / "any emails from X" -> search
    have_emails_match = re.match(
        r"^(?:do\s+i\s+have|any|have\s+i\s+(?:got|received)?)\s+(?:any\s+)?(?:new\s+)?emails?\s+from\s+(?P<sender>.+?)(?:\s+in\s+(?P<app>.+))?$",
        prefix_stripped,
        flags=re.IGNORECASE,
    )
    if have_emails_match:
        sender = normalize_request_fragment(have_emails_match.group("sender"))
        app = normalize_email_app(have_emails_match.group("app") or DEFAULT_EMAIL_CLIENT)
        params = {"query": sender, "app": app}
        return {
            "tool": "email_search",
            "params": params,
            "query": f"Search {app} for emails from {sender}",
            "reason": "Email search routed to email faculty.",
        }

    compose_match = re.match(
        rf"^(?:send|write|compose)\s+(?:an?\s+)?email\s+to\s+(?P<to>[^\s].+?)(?:\s+about\s+(?P<subject>.+?))?\s+saying\s+(?P<body>.+?)(?:\s+on\s+(?P<app>{app_pattern}))?$",
        normalized_stripped,
        flags=re.IGNORECASE,
    )
    if compose_match:
        app = normalize_email_app(compose_match.group("app") or DEFAULT_EMAIL_CLIENT)
        recipient = normalize_request_fragment(compose_match.group("to"))
        subject = normalize_request_fragment(compose_match.group("subject"))
        body = str(compose_match.group("body") or "").strip()
        params = {
            "app": app,
            "to": recipient,
            "subject": subject,
            "body": body,
            "mode": "draft",
        }
        return {
            "tool": "email_compose",
            "params": params,
            "query": build_email_compose_query(app, recipient, subject),
            "reason": "Email composition requires a governed two-stage send flow.",
        }

    reply_match = re.match(
        rf"^(?:reply\s+to(?:\s+the)?\s+email\s+from|reply\s+to)\s+(?P<target>.+?)\s+saying\s+(?P<body>.+?)(?:\s+on\s+(?P<app>{app_pattern}))?$",
        normalized_stripped,
        flags=re.IGNORECASE,
    )
    if reply_match:
        app = normalize_email_app(reply_match.group("app") or DEFAULT_EMAIL_CLIENT)
        target = normalize_request_fragment(reply_match.group("target"))
        body = str(reply_match.group("body") or "").strip()
        params = {
            "app": app,
            "subject_or_sender": target,
            "body": body,
            "mode": "draft",
        }
        return {
            "tool": "email_reply",
            "params": params,
            "query": build_email_reply_query(app, target),
            "reason": "Email reply requires a governed two-stage send flow.",
        }

    read_inbox_patterns = (
        re.match(
            rf"^(?:check|read|show)(?:\s+my)?\s+(?:email|emails|inbox|mail)(?:\s+on\s+(?P<app>{app_pattern}))?$",
            prefix_stripped,
            flags=re.IGNORECASE,
        ),
        re.match(
            rf"^(?:check|read|show)\s+(?P<app>{app_pattern})\s+(?:email|emails|inbox|mail)$",
            prefix_stripped,
            flags=re.IGNORECASE,
        ),
    )
    for match in read_inbox_patterns:
        if match:
            app = normalize_email_app(match.groupdict().get("app", "") or DEFAULT_EMAIL_CLIENT)
            return {
                "tool": "email_read_inbox",
                "params": {"app": app, "max_emails": 10},
                "query": f"{display_email_app_name(app)} inbox",
                "reason": "Email inbox inspection routed to workflow execution.",
            }

    search_sender_match = re.match(
        rf"^(?:do i have any )?(?:emails?|mail)\s+from\s+(?P<query>.+?)(?:\s+on\s+(?P<app>{app_pattern}))?$",
        prefix_stripped,
        flags=re.IGNORECASE,
    )
    if search_sender_match:
        app = normalize_email_app(search_sender_match.group("app") or DEFAULT_EMAIL_CLIENT)
        query = normalize_request_fragment(search_sender_match.group("query"))
        return {
            "tool": "email_search",
            "params": {"query": query, "app": app},
            "query": f"{display_email_app_name(app)} search: {query}",
            "reason": "Email search routed to workflow execution.",
        }

    read_email_match = re.match(
        rf"^(?:read|open)\s+(?:the\s+)?email\s+from\s+(?P<target>.+?)(?:\s+on\s+(?P<app>{app_pattern}))?$",
        normalized_stripped,
        flags=re.IGNORECASE,
    )
    if read_email_match:
        app = normalize_email_app(read_email_match.group("app") or DEFAULT_EMAIL_CLIENT)
        target = normalize_request_fragment(read_email_match.group("target"))
        return {
            "tool": "email_read_message",
            "params": {"subject_or_sender": target, "app": app},
            "query": f"{display_email_app_name(app)} email: {target}",
            "reason": "Specific email reading routed to workflow execution.",
        }

    search_match = re.match(
        rf"^(?:search|find)\s+(?:my\s+)?(?:email|emails|mail)\s+for\s+(?P<query>.+?)(?:\s+on\s+(?P<app>{app_pattern}))?$",
        normalized_stripped,
        flags=re.IGNORECASE,
    )
    if search_match:
        app = normalize_email_app(search_match.group("app") or DEFAULT_EMAIL_CLIENT)
        query = normalize_request_fragment(search_match.group("query"))
        return {
            "tool": "email_search",
            "params": {"query": query, "app": app},
            "query": f"{display_email_app_name(app)} search: {query}",
            "reason": "Email search routed to workflow execution.",
        }

    return None


def detect_email_tool_action(
    text: str,
    email_workflows: EmailWorkflows | None = None,
    conversation_context: list[dict[str, str]] | None = None,
) -> dict[str, Any] | None:
    del email_workflows
    request = extract_email_tool_request(
        text,
        conversation_context=conversation_context,
    )
    if request is None:
        return None
    return {
        **request,
        "requires_proposal": email_request_requires_proposal(request),
    }


def _has_email_comm_signal(text_lower: str) -> bool:
    lowered = str(text_lower or "").lower()
    return any(signal in lowered for signal in EMAIL_COMM_SIGNAL_FALLBACKS)


def _extract_intent_with_timeout(
    user_input: str,
    conversation_context: list[dict[str, str]] | None = None,
    timeout_s: float = 3.0,
) -> IntentResult | None:
    holder: list[IntentResult | None] = [None]

    def _run_intent() -> None:
        holder[0] = extract_intent(
            user_input,
            conversation_context=conversation_context,
        )

    thread = threading.Thread(target=_run_intent, daemon=True)
    thread.start()
    thread.join(timeout=timeout_s)
    if thread.is_alive():
        return None
    return holder[0]


def nammu_first_routing(
    text: str,
    conversation_context: list[dict[str, str]] | None = None,
    operator_profile: OperatorProfile | None = None,
) -> dict[str, Any] | None:
    """Try NAMMU universal intent extraction first, then fall through to regex."""
    normalized = str(text or "").strip()
    domain = _classify_domain_fast(normalized.lower())
    if domain == "none":
        return None

    holder: list[IntentResult | None] = [None]

    def _run_universal_intent() -> None:
        holder[0] = extract_intent_universal(
            normalized,
            conversation_context=conversation_context,
            domain_hint=domain,
            operator_profile=operator_profile,
        )

    thread = threading.Thread(target=_run_universal_intent, daemon=True)
    thread.start()
    thread.join(timeout=3.0)
    if thread.is_alive():
        return None

    result = holder[0]
    if result is None or not result.success or result.confidence < 0.75:
        return None
    request = result.to_tool_request()
    if request is not None:
        request["_nammu_domain"] = result.domain
    return request


def ensure_nammu_profile_for_user(
    profile_manager: ProfileManager | None,
    nammu_dir: Path | None,
    user_id: str,
) -> OperatorProfile | None:
    if profile_manager is None or nammu_dir is None or not user_id:
        return None
    user_profile = profile_manager.ensure_profile_exists(user_id)
    nammu_profile = build_profile_from_user_profile(user_profile, nammu_dir)
    save_operator_profile(nammu_dir, nammu_profile)
    return nammu_profile


def parse_nammu_correction_params(param_str: str) -> dict[str, Any]:
    cleaned = str(param_str or "").strip()
    if not cleaned:
        return {}
    try:
        parsed = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        return {"query": cleaned}
    return parsed if isinstance(parsed, dict) else {"query": cleaned}


def build_nammu_correction_record_text(
    original_text: str,
    correct_intent: str,
    correct_params: dict[str, Any],
) -> str:
    example = RoutingCorrection(
        original_text=str(original_text or ""),
        correct_intent=str(correct_intent or ""),
        correct_params=dict(correct_params or {}),
    ).to_example_line()
    return example


def build_nammu_pattern_summary(
    routing_corrections: list[dict[str, Any]],
    session_correction_count: int,
) -> str | None:
    if session_correction_count <= 0 or session_correction_count % 5 != 0:
        return None
    recent = routing_corrections[-5:]
    if not recent:
        return None
    patterns = [
        f"  '{str(item.get('original_text', ''))[:30]}' -> {str(item.get('correct_intent', ''))}"
        for item in recent
    ]
    return "\n".join(
        [
            f"nammu > {session_correction_count} corrections this session",
            *patterns,
            "  These are saved and will improve future routing.",
        ]
    )


def resolve_tool_domain(tool_name: str) -> str:
    normalized = str(tool_name or "").strip().lower()
    return INTENT_TO_DOMAIN.get(normalized, "none")


def update_nammu_profile_after_tool(
    profile: OperatorProfile | None,
    nammu_dir: Path | None,
    text: str,
    tool_name: str,
) -> OperatorProfile | None:
    if profile is None or nammu_dir is None:
        return profile
    domain = resolve_tool_domain(tool_name)
    if domain == "none":
        return profile
    profile.record_routing(domain)
    profile.update_language_pattern(text, domain)
    save_operator_profile(nammu_dir, profile)
    return profile


def _nammu_request_requires_proposal(
    tool_request: dict[str, Any],
    filesystem_faculty: FileSystemFaculty,
) -> bool:
    tool_name = str(tool_request.get("tool", "")).strip().lower()
    if tool_name in EMAIL_TOOL_NAMES:
        return email_request_requires_proposal(tool_request)
    if tool_name in COMMUNICATION_TOOL_NAMES:
        return communication_request_requires_proposal(tool_request)
    if tool_name in DOCUMENT_TOOL_NAMES:
        return document_request_requires_proposal(tool_request)
    if tool_name in BROWSER_TOOL_NAMES:
        return browser_request_requires_proposal(tool_request)
    if tool_name in DESKTOP_TOOL_NAMES:
        return desktop_request_requires_proposal(tool_request)
    if tool_name in FILESYSTEM_TOOL_NAMES:
        return filesystem_request_requires_proposal(tool_request, filesystem_faculty)
    if tool_name in PROCESS_TOOL_NAMES:
        return process_request_requires_proposal(tool_request)
    if tool_name in PACKAGE_TOOL_NAMES:
        return package_request_requires_proposal(tool_request)
    if tool_name in CALENDAR_TOOL_NAMES:
        return False
    if tool_name in NETWORK_TOOL_NAMES or tool_name == "web_search":
        return True
    return False


def build_nammu_tool_action(
    tool_request: dict[str, Any] | None,
    filesystem_faculty: FileSystemFaculty,
) -> dict[str, Any] | None:
    if tool_request is None:
        return None
    return {
        **tool_request,
        "requires_proposal": _nammu_request_requires_proposal(tool_request, filesystem_faculty),
    }


def detect_desktop_tool_action(
    text: str,
    desktop_faculty: DesktopFaculty | None = None,
) -> dict[str, Any] | None:
    del desktop_faculty
    request = extract_desktop_tool_request(text)
    if request is None:
        return None
    return {
        **request,
        "requires_proposal": desktop_request_requires_proposal(request),
    }


def extract_package_tool_request(
    text: str,
    hints: list[str] | None = None,
) -> dict[str, Any] | None:
    normalized = str(text or "").strip()
    lowered = normalized.lower()

    # Strip common INANNA prefixes so "INANNA, install X" works
    prefix_stripped = re.sub(
        r"^(?:inanna[,\s]+|hey inanna[,\s]+|please[,\s]+|can you[,\s]+)",
        "",
        lowered,
        flags=re.IGNORECASE,
    ).strip()
    normalized_stripped = re.sub(
        r"^(?:inanna[,\s]+|hey inanna[,\s]+|please[,\s]+|can you[,\s]+)",
        "",
        normalized,
        flags=re.IGNORECASE,
    ).strip()

    active_hints = hints or load_package_domain_hints()
    hint_match = any(hint in lowered for hint in active_hints)
    search_term_match = any(term in lowered for term in PACKAGE_SEARCH_TERMS)

    if not hint_match and not search_term_match and not re.match(
        r"^(?:install|remove|uninstall|search|find|list|show|what packages|what software|what is installed|what do i have|installed|my software|my apps|launch|open|start|run)\b",
        prefix_stripped,
    ):
        return None

    # install / add package
    install_match = re.match(
        r"^(?:install|add)(?:\s+package)?\s+(?P<package>.+)$",
        normalized_stripped,
        flags=re.IGNORECASE,
    )
    if install_match:
        params = {"package": normalize_request_fragment(install_match.group("package"))}
        return {
            "tool": "install_package",
            "params": params,
            "query": build_tool_request_query("install_package", params),
            "reason": "Package installation requires governed tool use.",
        }

    # remove / uninstall package
    remove_match = re.match(
        r"^(?:remove|uninstall)(?:\s+package)?\s+(?P<package>.+)$",
        normalized_stripped,
        flags=re.IGNORECASE,
    )
    if remove_match:
        params = {"package": normalize_request_fragment(remove_match.group("package"))}
        return {
            "tool": "remove_package",
            "params": params,
            "query": build_tool_request_query("remove_package", params),
            "reason": "Package removal requires governed tool use.",
        }

    # search for a package / software
    search_pkg_match = re.match(
        r"^(?:search|find|look for|search for)(?:\s+a)?(?:\s+package)?(?:\s+for)?\s+(?P<query>.+)$",
        prefix_stripped,
        flags=re.IGNORECASE,
    )
    if search_pkg_match:
        query = search_pkg_match.group("query").strip()
        # If query looks like software/app context, use search_packages
        app_signals = [
            "editor", "browser", "player", "viewer", "client", "tool",
            "software", "program", "app", "application", "manager",
            "notepad", "firefox", "chrome", "vlc", "gimp", "code",
        ]
        if any(sig in query.lower() for sig in app_signals):
            params = {"query": query}
            return {
                "tool": "search_packages",
                "params": params,
                "query": build_tool_request_query("search_packages", params),
                "reason": "Package search routed to OPERATOR tool use.",
            }

    if prefix_stripped in {
        "what packages do i have installed",
        "what is installed",
        "what software is installed",
        "list packages",
        "show packages",
        "show me packages",
        "show installed",
        "list installed",
        "list installed software",
        "show installed software",
        "what do i have installed",
        "show me what is installed",
        "installed software",
        "installed apps",
        "my installed apps",
        "my software",
    }:
        params = {"filter": ""}
        return {
            "tool": "list_packages",
            "params": params,
            "query": build_tool_request_query("list_packages", params),
            "reason": "Installed package inspection routed to OPERATOR tool use.",
        }

    list_match = re.match(
        r"^(?:list|show)(?:\s+me)?(?:\s+the)?(?:\s+installed)?\s+(?:packages?|software|apps?|applications?|programs?)(?:\s+(?P<filter>.+))?$",
        prefix_stripped,
        flags=re.IGNORECASE,
    )
    if list_match:
        params = {"filter": normalize_request_fragment(list_match.group("filter") or "")}
        return {
            "tool": "list_packages",
            "params": params,
            "query": build_tool_request_query("list_packages", params),
            "reason": "Installed package inspection routed to OPERATOR tool use.",
        }

    search_match = re.match(
        r"^(?:search(?:\s+for)?|find)(?:\s+(?:a|an|package|packages|software|app|application))?\s+(?P<query>.+)$",
        normalized,
        flags=re.IGNORECASE,
    )
    if search_match:
        query = normalize_request_fragment(search_match.group("query"))
        query_lower = query.lower()
        if hint_match or any(term in query_lower for term in PACKAGE_SEARCH_TERMS):
            params = {"query": query, "package": query}
            return {
                "tool": "search_packages",
                "params": params,
                "query": build_tool_request_query("search_packages", params),
                "reason": "Package search routed to OPERATOR tool use.",
            }

    # launch / open application
    launch_match = re.match(
        r"^(?:launch|open|start|run)(?:\s+(?:app|application|program|software))?\s+(?P<app>.+)$",
        prefix_stripped,
        flags=re.IGNORECASE,
    )
    if launch_match:
        app = normalize_request_fragment(launch_match.group("app"))
        params = {"app": app}
        return {
            "tool": "launch_app",
            "params": params,
            "query": app,
            "reason": "Application launch routed to OPERATOR tool use.",
        }

    return None


def package_request_requires_proposal(package_request: dict[str, Any]) -> bool:
    tool_name = str(package_request.get("tool", "")).strip().lower()
    return tool_name in {"install_package", "remove_package", "launch_app"}


def detect_package_tool_action(
    text: str,
    package_faculty: PackageFaculty | None = None,
) -> dict[str, Any] | None:
    del package_faculty
    request = extract_package_tool_request(text)
    if request is None:
        return None
    return {
        **request,
        "requires_proposal": package_request_requires_proposal(request),
    }


def build_sentinel_stub_response() -> str:
    return SENTINEL_STUB_RESPONSE


def load_faculty_definition(
    faculties_path: Path,
    faculty_name: str,
) -> dict[str, Any]:
    try:
        fac_data = json.loads(faculties_path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    faculties = fac_data.get("faculties", {})
    if not isinstance(faculties, dict):
        return {}

    definition = faculties.get(faculty_name, {})
    return definition if isinstance(definition, dict) else {}


def build_sentinel_system_prompt(
    grounding: str | list[str | dict[str, str]] | None,
    faculties_path: Path,
    grounding_prefix: str = "",
) -> str:
    default_charter = (
        "I am SENTINEL. I analyze security posture. I reason about threats "
        "and vulnerabilities. I perform passive analysis only. Any offensive "
        "or active capability requires explicit Guardian proposal approval."
    )
    default_rules = [
        "Passive analysis only without explicit Guardian approval",
        "All offensive actions require Guardian proposal",
        "Never recommend exploiting a vulnerability without consent",
    ]

    try:
        sentinel_cfg = load_faculty_definition(faculties_path, "sentinel")
        charter = str(sentinel_cfg.get("charter_preview", "")).strip()
        gov_rules = [
            str(rule).strip()
            for rule in sentinel_cfg.get("governance_rules", [])
            if isinstance(rule, str) and str(rule).strip()
        ]
    except Exception:
        charter = ""
        gov_rules = []

    if not charter:
        charter = default_charter
    if not gov_rules:
        gov_rules = default_rules

    grounding_text = grounding.strip() if isinstance(grounding, str) else ""
    if grounding_text and grounding_prefix:
        grounding_text = f"{grounding_prefix}\n{grounding_text}"
    if not grounding_text:
        grounding_items = list(grounding or []) if isinstance(grounding, list) else []
        grounding_text = Engine(grounding_prefix=grounding_prefix)._build_grounding_turn(
            grounding_items
        )["content"]

    rules_text = "\n".join(f"- {rule}" for rule in gov_rules)
    return (
        "You are SENTINEL, the cybersecurity Faculty of INANNA NYX.\n\n"
        f"Charter: {charter}\n\n"
        "Your domain: network security, threat analysis, vulnerability assessment,\n"
        "risk reasoning, defensive security posture.\n\n"
        "Governance rules (enforced, not negotiable):\n"
        f"{rules_text}\n\n"
        "You reason carefully, cite known frameworks (MITRE ATT&CK, CVE, OWASP)\n"
        "where relevant, and always distinguish between what is known and what is\n"
        "inferred. You are honest about the limits of your knowledge.\n\n"
        f"{grounding_text}"
    ).strip()


def run_sentinel_response(
    user_input: str,
    grounding: str | list[str | dict[str, str]] | None,
    lm_url: str,
    model_name: str,
    faculties_path: Path,
    grounding_prefix: str = "",
) -> str:
    system_prompt = build_sentinel_system_prompt(
        grounding,
        faculties_path,
        grounding_prefix=grounding_prefix,
    )
    sentinel_cfg = load_faculty_definition(faculties_path, "sentinel")
    effective_lm_url = str(sentinel_cfg.get("model_url") or lm_url).strip()
    effective_model_name = str(sentinel_cfg.get("model_name") or model_name).strip()
    engine = Engine(
        model_url=effective_lm_url,
        model_name=effective_model_name,
        api_key=os.getenv("INANNA_API_KEY", "").strip(),
    )
    fallback = (
        f"{SENTINEL_FALLBACK_PREFIX} Model endpoint unavailable. "
        "I can still offer bounded defensive guidance: confirm scope, preserve logs, "
        "validate exposure, and pursue responsible disclosure or defensive action."
    )

    if not (engine.model_url and engine.model_name):
        return fallback

    try:
        return engine._call_openai_compatible(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input.strip()},
            ]
        )
    except Exception:
        return fallback


def sentinel_response_mode(response_text: str) -> str:
    return "fallback" if response_text.startswith(SENTINEL_FALLBACK_PREFIX) else "connected"


def realm_is_empty(realm_dirs: dict[str, Path]) -> bool:
    return all(not any(path.iterdir()) for path in realm_dirs.values())


def flat_data_contains_files(data_root: Path) -> bool:
    for key in ("sessions", "memory", "proposals", "nammu"):
        flat_dir = data_root / key
        if flat_dir.exists() and any(path.is_file() for path in flat_dir.iterdir()):
            return True
    return False


def migrate_flat_data_to_default_realm(
    data_root: Path,
    realm_dirs: dict[str, Path],
) -> int:
    migrated = 0
    for key in ("sessions", "memory", "proposals", "nammu"):
        flat_dir = data_root / key
        realm_dir = realm_dirs[key]
        realm_dir.mkdir(parents=True, exist_ok=True)
        if flat_dir.exists():
            for path in flat_dir.iterdir():
                if path.is_file():
                    destination = realm_dir / path.name
                    if not destination.exists():
                        path.rename(destination)
                        migrated += 1
    return migrated


def initialize_realm_context(
    data_root: Path,
) -> tuple[RealmManager, RealmConfig, dict[str, Path], int]:
    realm_manager = RealmManager(data_root)
    default_realm = realm_manager.ensure_default_realm()
    default_dirs = realm_manager.realm_data_dirs(default_realm.name)
    migrated = 0
    if realm_is_empty(default_dirs) and flat_data_contains_files(data_root):
        migrated = migrate_flat_data_to_default_realm(data_root, default_dirs)

    active_realm_name = get_active_realm_name()
    if not realm_manager.realm_exists(active_realm_name):
        realm_manager.create_realm(active_realm_name)

    active_realm = realm_manager.load_realm(active_realm_name)
    if active_realm is None:
        active_realm = realm_manager.ensure_default_realm()
        active_realm_name = active_realm.name

    realm_dirs = realm_manager.realm_data_dirs(active_realm_name)
    for path in realm_dirs.values():
        path.mkdir(parents=True, exist_ok=True)

    return realm_manager, active_realm, realm_dirs, migrated


def build_realms_report(
    realm_manager: RealmManager,
    active_realm_name: str,
) -> str:
    names = realm_manager.list_realms()
    lines = [f"realms > Available realms ({len(names)}):"]
    for name in names:
        config = realm_manager.load_realm(name)
        purpose = config.purpose if config and config.purpose else "No purpose set."
        lines.append(f"  [{name}]  {purpose}")
    lines.append(f"  Active: {active_realm_name}")
    return "\n".join(lines)


def count_records(directory: Path, pattern: str) -> int:
    return len(list(directory.glob(pattern)))


def load_current_realm(
    realm_manager: RealmManager | None,
    active_realm: RealmConfig | None,
) -> RealmConfig | None:
    if active_realm is None:
        return None
    if realm_manager is None:
        return active_realm
    loaded = realm_manager.load_realm(active_realm.name)
    return loaded or active_realm


def build_realm_context_report(
    realm: RealmConfig | None,
    session_dir: Path,
    memory_dir: Path,
    proposal_dir: Path,
) -> str:
    if realm is None:
        return (
            "Active realm: default\n"
            "Purpose: No purpose set.\n"
            "Governance context: No governance context set.\n"
            "Created: unknown\n"
            f"Memory records: {count_records(memory_dir, '*.json')}\n"
            f"Sessions: {count_records(session_dir, '*.json')}\n"
            f"Proposals: {count_records(proposal_dir, '*.txt')}"
        )

    return "\n".join(
        [
            f"Active realm: {realm.name}",
            f"Purpose: {realm.purpose or 'No purpose set.'}",
            (
                "Governance context: "
                + (realm.governance_context or "No governance context set.")
            ),
            f"Created: {realm.created_at}",
            f"Memory records: {count_records(memory_dir, '*.json')}",
            f"Sessions: {count_records(session_dir, '*.json')}",
            f"Proposals: {count_records(proposal_dir, '*.txt')}",
        ]
    )


def format_realm_proposal_line(record: dict) -> str:
    return (
        f"[REALM PROPOSAL] {record['timestamp']} | {record['what']} | "
        f"{record['why']} | status: {record['status']}"
    )


def format_assigned_realms(user_record: UserRecord | None) -> str:
    if user_record is None or not user_record.assigned_realms:
        return "(none)"
    return ", ".join(user_record.assigned_realms)


def build_realm_access_warning_lines(
    user_record: UserRecord | None,
    realm_name: str,
) -> list[str]:
    if user_record is None or can_access_realm(user_record, realm_name):
        return []
    return [
        f"access > {user_record.display_name} does not have access to realm {realm_name}.",
        f"access > Assigned realms: {format_assigned_realms(user_record)}.",
        f"access > Start with INANNA_REALM=default or use assign-realm.",
    ]


def parse_user_realm_command(command: str, command_name: str) -> tuple[str, str] | None:
    parts = command.split(maxsplit=2)
    if len(parts) != 3 or parts[0].lower() != command_name:
        return None
    return parts[1].strip(), parts[2].strip()


def create_realm_assignment_proposal(
    proposal: Proposal,
    display_name: str,
    user_id: str,
    realm_name: str,
    action: str,
) -> dict:
    verb = "Assign" if action == "assign_realm" else "Remove"
    created = proposal.create(
        what=f"{verb} realm {realm_name} {'to' if action == 'assign_realm' else 'from'} {display_name}",
        why="Realm access changes require visible approval before they take effect.",
        payload={
            "action": action,
            "user_id": user_id,
            "display_name": display_name,
            "realm_name": realm_name,
        },
    )
    return {**created, "line": format_realm_proposal_line(created)}


def refresh_session_state_user(
    session_state: dict[str, UserRecord | None] | None,
    user_manager: UserManager,
    user_id: str,
) -> None:
    if session_state is None:
        return
    refreshed = user_manager.get_user(user_id)
    if refreshed is None:
        return
    for key in ("active_user", "original_user", "guardian_user"):
        record = session_state.get(key)
        if record is not None and record.user_id == user_id:
            session_state[key] = refreshed


def memory_scope_user_id(
    active_user: UserRecord | None,
    user_manager: UserManager | None,
) -> str | None:
    if active_user is None:
        return None
    if user_manager is not None and user_manager.has_privilege(active_user.user_id, "all"):
        return None
    return active_user.user_id


def refresh_startup_context(
    startup_context: dict[str, Any],
    memory: Memory,
    active_user: UserRecord | None,
    user_manager: UserManager | None,
) -> None:
    payload = memory.load_startup_context(user_id=memory_scope_user_id(active_user, user_manager))
    startup_context.clear()
    startup_context.update(payload)


def profile_subject(
    active_user: UserRecord | None,
    active_token: SessionToken | None,
) -> tuple[str, str]:
    if active_user is not None:
        return active_user.user_id, active_user.display_name
    if active_token is not None:
        return active_token.user_id, active_token.display_name
    return "", ""


def build_grounding_prefix(
    profile_manager: ProfileManager | None,
    active_user: UserRecord | None,
    active_token: SessionToken | None,
) -> str:
    from core.profile import IdentityFormatter
    user_id, fallback = profile_subject(active_user, active_token)
    if not user_id:
        return ""
    if profile_manager is None:
        display_name = fallback.strip()
        return f"You are speaking with {display_name}." if display_name else ""
    formatter = IdentityFormatter(profile_manager)
    name = formatter.address(user_id, fallback=fallback).strip()
    if not name:
        return ""
    lines = [f"You are speaking with {name}."]
    pset = formatter.pronouns(user_id)
    subject = pset["subject"]
    possessive = pset["possessive"]
    # Only add pronoun line when explicitly set (not default they/them from empty)
    raw_pronouns = profile_manager.pronouns_for(user_id).strip()
    if raw_pronouns:
        lines.append(
            f"{name} uses {subject}/{possessive} pronouns. "
            f"Use these when referring to {name} in third person."
        )
    return "\n".join(lines)


def build_reflection_grounding(reflective_memory: ReflectiveMemory | None) -> str:
    if reflective_memory is None:
        return ""
    entries = reflective_memory.load_all()
    if not entries:
        return ""
    observations = [entry.observation.strip() for entry in entries[-5:] if entry.observation.strip()]
    if not observations:
        return ""
    return f"Your self-knowledge: {'; '.join(observations)}"


def sync_profile_grounding(
    engine: Engine | None,
    profile_manager: ProfileManager | None,
    active_user: UserRecord | None,
    active_token: SessionToken | None,
    reflective_memory: ReflectiveMemory | None = None,
) -> None:
    if engine is None:
        return
    if reflective_memory is None and profile_manager is not None:
        reflective_memory = ReflectiveMemory(profile_manager.profiles_dir.parent / "self")
    profile_grounding = build_grounding_prefix(
        profile_manager,
        active_user,
        active_token,
    )
    reflection_grounding = build_reflection_grounding(reflective_memory)
    engine.grounding_prefix = "\n".join(
        line
        for line in [profile_grounding, reflection_grounding]
        if line
    )


def build_profile_status_payload(
    profile_manager: ProfileManager | None,
    active_user: UserRecord | None,
    active_token: SessionToken | None,
) -> dict[str, Any]:
    user_id, _ = profile_subject(active_user, active_token)
    if not user_id or profile_manager is None:
        return {
            "exists": False,
            "preferred_name": "",
            "onboarding_completed": False,
            "departments": [],
            "pronouns": "",
        }

    profile = profile_manager.load(user_id)
    if profile is None:
        return {
            "exists": False,
            "preferred_name": "",
            "onboarding_completed": False,
            "departments": [],
            "pronouns": "",
        }

    return {
        "exists": True,
        "preferred_name": profile.preferred_name,
        "onboarding_completed": profile.onboarding_completed,
        "departments": list(profile.departments),
        "pronouns": profile.pronouns,
    }


def has_profile_field(field_name: str) -> bool:
    return field_name in UserProfile.__dataclass_fields__


def default_profile_field_value(field_name: str) -> Any:
    field = UserProfile.__dataclass_fields__.get(field_name)
    if field is None:
        raise KeyError(field_name)
    if field.default_factory is not MISSING:
        return field.default_factory()
    if field.default is not MISSING:
        return field.default
    return ""


def is_profile_list_field(field_name: str) -> bool:
    if not has_profile_field(field_name):
        return False
    return isinstance(default_profile_field_value(field_name), list)


def format_profile_value(value: Any) -> str:
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        return ", ".join(items) if items else PROFILE_EMPTY_VALUE
    text = str(value).strip() if value is not None else ""
    return text or PROFILE_EMPTY_VALUE


def format_profile_timestamp(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    try:
        return datetime.fromisoformat(text).strftime("%b %d %H:%M")
    except ValueError:
        return text


def format_profile_location(profile: UserProfile) -> str:
    parts = [
        profile.location_city.strip(),
        profile.location_region.strip(),
        profile.location_country.strip(),
    ]
    joined = ", ".join(part for part in parts if part)
    return joined or PROFILE_EMPTY_VALUE


def format_profile_onboarding(profile: UserProfile) -> str:
    if not profile.onboarding_completed:
        return "not completed"
    completed_at = format_profile_timestamp(profile.onboarding_completed_at)
    if completed_at:
        return f"completed {completed_at}"
    return "completed"


def format_profile_output(
    profile: UserProfile,
    display_name: str,
    heading: str = "Your profile",
    include_actions: bool = True,
) -> str:
    lines = [
        heading,
        "",
        f"  {'Name':<12} {format_profile_value(display_name)}",
        f"  {'Preferred':<12} {format_profile_value(profile.preferred_name)}",
        f"  {'Pronouns':<12} {format_profile_value(profile.pronouns)}",
        f"  {'Languages':<12} {format_profile_value(profile.languages)}",
        f"  {'Location':<12} {format_profile_location(profile)}",
        "",
        "  Organization",
        f"  {'Departments':<12} {format_profile_value(profile.departments)}",
        f"  {'Groups':<12} {format_profile_value(profile.groups)}",
        "",
        "  Communication",
        f"  {'Style':<12} {format_profile_value(profile.communication_style)}",
        f"  {'Length':<12} {format_profile_value(profile.preferred_length)}",
        f"  {'Formality':<12} {format_profile_value(profile.formality)}",
        f"  {'Patterns':<12} {format_profile_value(profile.observed_patterns)}",
        "",
        "  Interests",
        f"  {'Domains':<12} {format_profile_value(profile.domains)}",
        f"  {'Topics':<12} {format_profile_value(profile.recurring_topics)}",
        f"  {'Projects':<12} {format_profile_value(profile.named_projects)}",
        "",
        "  Trust",
        f"  {'Session':<12} {format_profile_value(profile.session_trusted_tools)}",
        f"  {'Persistent':<12} {format_profile_value(profile.persistent_trusted_tools)}",
        "",
        f"  {'Onboarding':<12} {format_profile_onboarding(profile)}",
    ]
    if include_actions:
        lines.extend(
            [
                "",
                'Type "my-profile edit [field] [value]" to update any field.',
                'Type "my-profile clear [field]" to remove a field.',
            ]
        )
    return "\n".join(lines)


# Human-friendly aliases for profile fields
# Allows natural language like "name", "pronouns", "city" instead of snake_case
PROFILE_FIELD_ALIASES: dict[str, str] = {
    # Name
    "name":              "preferred_name",
    "preferred":         "preferred_name",
    "preferred_name":    "preferred_name",
    "display_name":      "preferred_name",
    "call_me":           "preferred_name",
    # Pronouns & identity
    "pronouns":          "pronouns",
    "pronoun":           "pronouns",
    "gender":            "gender",
    "sex":               "sex",
    # Location
    "city":              "location_city",
    "location_city":     "location_city",
    "region":            "location_region",
    "location_region":   "location_region",
    "country":           "location_country",
    "location_country":  "location_country",
    # Languages
    "language":          "languages",
    "languages":         "languages",
    "lang":              "languages",
    # Timezone
    "timezone":          "timezone",
    "tz":                "timezone",
    "time_zone":         "timezone",
    # Communication
    "style":             "communication_style",
    "communication_style": "communication_style",
    "length":            "preferred_length",
    "preferred_length":  "preferred_length",
    "formality":         "formality",
    # Notification
    "notification":      "notification_scope",
    "notification_scope": "notification_scope",
    "notifications":     "notification_scope",
}


def resolve_profile_field(field_name: str) -> str:
    """Resolve a human-friendly field alias to the actual UserProfile field name."""
    return PROFILE_FIELD_ALIASES.get(field_name.lower().strip(), field_name.lower().strip())


def parse_profile_edit_command(command: str) -> tuple[str, str] | None:
    parts = command.strip().split(maxsplit=3)
    if len(parts) != 4:
        return None
    if parts[0].lower() != "my-profile" or parts[1].lower() != "edit":
        return None
    raw_field = parts[2].strip()
    value = parts[3].strip()
    if not raw_field or not value:
        return None
    # Resolve alias to actual field name
    field_name = resolve_profile_field(raw_field)
    return field_name, value


def parse_profile_clear_command(command: str) -> str | None:
    parts = command.strip().split(maxsplit=2)
    if len(parts) != 3:
        return None
    if parts[0].lower() != "my-profile" or parts[1].lower() != "clear":
        return None
    field_name = parts[2].strip()
    return field_name or None


def coerce_profile_field_value(field_name: str, value: str) -> Any:
    if is_profile_list_field(field_name):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value.strip()


def normalize_tool_name(value: str) -> str:
    return str(value or "").strip().lower()


def normalize_trusted_tools(values: list[str] | None) -> list[str]:
    normalized: list[str] = []
    for item in values or []:
        cleaned = normalize_tool_name(item)
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    return normalized


def grant_persistent_tool_trust(
    profile_manager: ProfileManager | None,
    operator: OperatorFaculty | None,
    user_id: str,
    tool_name: str,
) -> tuple[bool, bool, str]:
    normalized = normalize_tool_name(tool_name)
    if profile_manager is None or operator is None or not user_id or not normalized:
        return False, False, normalized
    if normalized not in operator.PERMITTED_TOOLS:
        return False, False, normalized
    profile = profile_manager.ensure_profile_exists(user_id)
    trusted_tools = normalize_trusted_tools(profile.persistent_trusted_tools)
    changed = normalized not in trusted_tools
    if changed:
        trusted_tools.append(normalized)
    if changed or trusted_tools != list(profile.persistent_trusted_tools or []):
        profile_manager.update_field(user_id, "persistent_trusted_tools", trusted_tools)
    return True, changed, normalized


def revoke_persistent_tool_trust(
    profile_manager: ProfileManager | None,
    user_id: str,
    tool_name: str,
) -> tuple[bool, bool, str]:
    normalized = normalize_tool_name(tool_name)
    if profile_manager is None or not user_id or not normalized:
        return False, False, normalized
    profile = profile_manager.ensure_profile_exists(user_id)
    trusted_tools = normalize_trusted_tools(profile.persistent_trusted_tools)
    removed = normalized in trusted_tools
    next_tools = [item for item in trusted_tools if item != normalized]
    if next_tools != list(profile.persistent_trusted_tools or []):
        profile_manager.update_field(user_id, "persistent_trusted_tools", next_tools)
    return True, removed, normalized


def build_trust_report(profile: UserProfile) -> str:
    return "\n".join(
        [
            "Your trust patterns:",
            "",
            f"  {'Session':<12} {format_profile_value(normalize_trusted_tools(profile.session_trusted_tools))}",
            f"  {'Persistent':<12} {format_profile_value(normalize_trusted_tools(profile.persistent_trusted_tools))}",
            "",
            'Type "governance-trust [tool]" to persistently trust a tool.',
            'Type "governance-revoke [tool]" to remove persistent trust.',
        ]
    )


def resolve_profile_subject(
    profile_manager: ProfileManager | None,
    active_user: UserRecord | None,
    active_token: SessionToken | None,
) -> tuple[str, str, UserProfile | None]:
    user_id, display_name = profile_subject(active_user, active_token)
    if not user_id or profile_manager is None:
        return user_id, display_name, None
    profile = profile_manager.ensure_profile_exists(user_id)
    return user_id, display_name, profile


def clear_communication_observations(
    profile_manager: ProfileManager | None,
    user_id: str,
) -> bool:
    if profile_manager is None or not user_id:
        return False
    for field_name in PROFILE_COMMUNICATION_CLEAR_FIELDS:
        profile_manager.update_field(
            user_id,
            field_name,
            default_profile_field_value(field_name),
        )
    return True


def normalize_org_value(value: str) -> str:
    return " ".join(value.strip().lower().split())


def assign_profile_membership(
    profile_manager: ProfileManager | None,
    user_id: str,
    field_name: str,
    value: str,
) -> tuple[bool, str]:
    if profile_manager is None or not user_id or field_name not in {"departments", "groups"}:
        return False, ""
    normalized = normalize_org_value(value)
    if not normalized:
        return False, ""
    profile = profile_manager.ensure_profile_exists(user_id)
    current_values: list[str] = []
    for item in getattr(profile, field_name, []) or []:
        cleaned = normalize_org_value(str(item))
        if cleaned and cleaned not in current_values:
            current_values.append(cleaned)
    if normalized not in current_values:
        current_values.append(normalized)
    if list(getattr(profile, field_name, [])) != current_values:
        profile_manager.update_field(user_id, field_name, current_values)
    return True, normalized


def unassign_profile_membership(
    profile_manager: ProfileManager | None,
    user_id: str,
    field_name: str,
    value: str,
) -> tuple[bool, bool, str]:
    if profile_manager is None or not user_id or field_name not in {"departments", "groups"}:
        return False, False, ""
    normalized = normalize_org_value(value)
    if not normalized:
        return False, False, ""
    profile = profile_manager.ensure_profile_exists(user_id)
    current_values: list[str] = []
    for item in getattr(profile, field_name, []) or []:
        cleaned = normalize_org_value(str(item))
        if cleaned and cleaned not in current_values:
            current_values.append(cleaned)
    removed = normalized in current_values
    next_values = [item for item in current_values if item != normalized]
    if list(getattr(profile, field_name, [])) != next_values:
        profile_manager.update_field(user_id, field_name, next_values)
    return True, removed, normalized


def notification_store_from_profile_manager(
    profile_manager: ProfileManager | None,
) -> NotificationStore | None:
    if profile_manager is None:
        return None
    return NotificationStore(profile_manager.profiles_dir.parent / "notifications")


def build_organizational_context_report(profile: UserProfile) -> str:
    return "\n".join(
        [
            "Your organizational context:",
            "",
            f"  {'Departments':<12} {format_profile_value(profile.departments)}",
            f"  {'Groups':<12} {format_profile_value(profile.groups)}",
            "",
            'Type "assign-department [dept]" to request assignment (Guardian approves).',
        ]
    )


def queue_department_notifications(
    notification_store: NotificationStore | None,
    user_manager: UserManager | None,
    profile_manager: ProfileManager | None,
    department: str,
    message: str,
    sender: str,
) -> tuple[int, str]:
    if notification_store is None or user_manager is None or profile_manager is None:
        return 0, ""
    normalized_department = normalize_org_value(department)
    message_text = message.strip()
    if not normalized_department or not message_text:
        return 0, normalized_department
    recipients = 0
    for record in user_manager.list_users():
        profile = profile_manager.load(record.user_id)
        if profile is None:
            continue
        departments = [
            normalize_org_value(str(item))
            for item in profile.departments
            if normalize_org_value(str(item))
        ]
        if normalized_department not in departments:
            continue
        notification_store.add(
            record.user_id,
            {
                "notification_id": f"notif-{uuid4().hex[:12]}",
                "from": sender,
                "department": normalized_department,
                "message": message_text,
                "created_at": utc_now(),
                "delivered": False,
            },
        )
        recipients += 1
    return recipients, normalized_department


def deliver_pending_notifications(
    notification_store: NotificationStore | None,
    user_id: str,
) -> list[str]:
    if notification_store is None or not user_id:
        return []
    lines: list[str] = []
    pending = notification_store.load_pending(user_id)
    for notification in pending:
        department = normalize_org_value(str(notification.get("department", ""))) or "department"
        message = str(notification.get("message", "")).strip()
        lines.append(f"\U0001F4E2 [{department} notification] {message}".strip())
        notification_id = str(notification.get("notification_id", "")).strip()
        if notification_id:
            notification_store.mark_delivered(user_id, notification_id)
    notification_store.clear_delivered(user_id)
    return lines


def collect_session_user_messages(session: Session) -> list[str]:
    messages: list[str] = []
    for event in session.events:
        if event.get("role") != "user":
            continue
        text = str(event.get("content", "")).strip()
        if text:
            messages.append(text)
    return messages


def collect_session_topics(routing_log: list[dict[str, str]] | None) -> list[str]:
    topics: list[str] = []
    for record in routing_log or []:
        topic = str(record.get("faculty") or record.get("route") or "").strip().lower()
        if topic and topic not in {"crown", "analyst"}:
            topics.append(topic)
    return topics


def observe_session_communication(
    profile_manager: ProfileManager | None,
    active_token: SessionToken | None,
    session: Session,
    routing_log: list[dict[str, str]] | None,
) -> None:
    if profile_manager is None or active_token is None:
        return
    observer = CommunicationObserver(profile_manager)
    observer.observe_session(
        user_id=active_token.user_id,
        messages=collect_session_user_messages(session),
        topics=collect_session_topics(routing_log),
    )


def needs_onboarding(profile: UserProfile | None) -> bool:
    if profile is None:
        return False
    return not profile.onboarding_completed


def ensure_guardian_profile_completed(
    profile_manager: ProfileManager | None,
    user_id: str,
) -> UserProfile | None:
    if profile_manager is None or not user_id:
        return None
    profile = profile_manager.ensure_profile_exists(user_id)
    if not profile.onboarding_completed:
        profile_manager.update_field(user_id, "onboarding_completed", True)
    if not profile.onboarding_completed_at:
        profile_manager.update_field(user_id, "onboarding_completed_at", utc_now())
    return profile_manager.load(user_id)


def reset_onboarding_state(state: dict[str, Any] | None) -> None:
    if state is None:
        return
    state["onboarding_active"] = False
    state["onboarding_step"] = 0
    state["onboarding_responses"] = {}


def activate_onboarding_state(state: dict[str, Any] | None) -> None:
    if state is None:
        return
    state["onboarding_active"] = True
    state["onboarding_step"] = 0
    state["onboarding_responses"] = {}


def build_onboarding_intro(display_name: str) -> str:
    name = display_name.strip() or "friend"
    return (
        f"Welcome, {name}. Before we begin, I would like to welcome you properly. "
        "I have five brief questions so I can serve you more thoughtfully. "
        "You may answer in your own words, say skip, or say skip all to leave the survey."
    )


def onboarding_question(step_index: int) -> str:
    bounded_index = max(0, min(step_index, len(ONBOARDING_STEPS) - 1))
    return str(ONBOARDING_STEPS[bounded_index]["prompt"])


def begin_onboarding_if_needed(
    state: dict[str, Any] | None,
    profile_manager: ProfileManager | None,
    active_user: UserRecord | None,
    active_token: SessionToken | None,
) -> list[str]:
    if state is None or profile_manager is None:
        return []
    user_id, display_name = profile_subject(active_user, active_token)
    if not user_id:
        reset_onboarding_state(state)
        return []
    if active_user is not None and active_user.role.strip().lower() == "guardian":
        reset_onboarding_state(state)
        return []
    profile = profile_manager.load(user_id)
    if not needs_onboarding(profile):
        reset_onboarding_state(state)
        return []
    activate_onboarding_state(state)
    return [build_onboarding_intro(display_name), onboarding_question(0)]


def _record_onboarding_response(
    responses: dict[str, Any],
    step_index: int,
    text: str,
) -> None:
    step = ONBOARDING_STEPS[step_index]
    cleaned = text.strip()
    lowered = cleaned.lower()
    if lowered in step["skip_phrases"] or not cleaned:
        return
    field = str(step["field"])
    if field in {"preferred_name", "pronouns"}:
        responses[field] = cleaned
        return
    survey_responses = dict(responses.get("survey_responses", {}))
    survey_responses[field] = cleaned
    responses["survey_responses"] = survey_responses


def complete_onboarding(
    *,
    profile_manager: ProfileManager | None,
    active_user: UserRecord | None,
    active_token: SessionToken | None,
    engine: Engine | None,
    responses: dict[str, Any] | None,
) -> str:
    user_id, display_name = profile_subject(active_user, active_token)
    if not user_id or profile_manager is None:
        return "Thank you. Let us begin."
    collected = dict(responses or {})
    preferred_name = str(collected.get("preferred_name", "")).strip()
    pronouns = str(collected.get("pronouns", "")).strip()
    survey_responses = dict(collected.get("survey_responses", {}))
    if preferred_name:
        profile_manager.update_field(user_id, "preferred_name", preferred_name)
    if pronouns:
        profile_manager.update_field(user_id, "pronouns", pronouns)
    profile_manager.update_field(user_id, "survey_responses", survey_responses)
    profile_manager.update_field(user_id, "onboarding_completed", True)
    profile_manager.update_field(user_id, "onboarding_completed_at", utc_now())
    sync_profile_grounding(engine, profile_manager, active_user, active_token, None)
    name = profile_manager.display_name_for(user_id, fallback=display_name)
    return (
        f"Thank you, {name}. I will remember what you have shared. "
        "You can update your profile at any time with the my-profile command. "
        "Let us begin."
    )


def handle_onboarding_response(
    *,
    state: dict[str, Any] | None,
    text: str,
    profile_manager: ProfileManager | None,
    active_user: UserRecord | None,
    active_token: SessionToken | None,
    engine: Engine | None,
) -> dict[str, Any]:
    if state is None or not state.get("onboarding_active"):
        return {"handled": False, "messages": [], "completed": False}

    cleaned = text.strip()
    responses = dict(state.get("onboarding_responses", {}))
    if cleaned.lower() == ONBOARDING_SKIP_ALL:
        completion = complete_onboarding(
            profile_manager=profile_manager,
            active_user=active_user,
            active_token=active_token,
            engine=engine,
            responses=responses,
        )
        reset_onboarding_state(state)
        return {"handled": True, "messages": [completion], "completed": True}

    step_index = int(state.get("onboarding_step", 0))
    bounded_index = max(0, min(step_index, len(ONBOARDING_STEPS) - 1))
    _record_onboarding_response(responses, bounded_index, cleaned)

    next_step = bounded_index + 1
    if next_step >= len(ONBOARDING_STEPS):
        completion = complete_onboarding(
            profile_manager=profile_manager,
            active_user=active_user,
            active_token=active_token,
            engine=engine,
            responses=responses,
        )
        reset_onboarding_state(state)
        return {"handled": True, "messages": [completion], "completed": True}

    state["onboarding_responses"] = responses
    state["onboarding_step"] = next_step
    return {
        "handled": True,
        "messages": [onboarding_question(next_step)],
        "completed": False,
    }


def token_preview(active_token: SessionToken | None) -> str:
    if active_token is None:
        return "none"
    return f"{active_token.token[:8]}..."


def append_audit_event(
    session_audit: list[dict[str, object]] | None,
    event_type: str,
    summary: str,
    details: dict[str, object] | None = None,
) -> None:
    if session_audit is None:
        return
    event: dict[str, object] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "summary": summary,
    }
    if details:
        event.update(details)
    session_audit.append(event)


def build_users_report(user_manager: UserManager) -> str:
    records = user_manager.list_users()
    lines = [f"Users ({len(records)} total):"]
    for record in records:
        realms = ", ".join(record.assigned_realms) or "(none)"
        lines.append(
            f"  [{record.role}]  {record.display_name:<15} {record.status:<8} realms: {realms}"
        )
    lines.append("(access control active in Phase 4.2)")
    return "\n".join(lines)


def format_realm_names(realms: list[str]) -> str:
    cleaned = [realm.strip() for realm in realms if realm.strip()]
    return ", ".join(cleaned) if cleaned else "(none)"


def has_admin_surface_access(
    user_manager: UserManager,
    active_user: UserRecord | None,
) -> bool:
    if active_user is None:
        return False
    return user_manager.has_privilege(active_user.user_id, "all") or user_manager.has_privilege(
        active_user.user_id,
        "invite_users",
    )


def admin_scope_realms(active_user: UserRecord | None) -> set[str]:
    if active_user is None:
        return set()
    return {realm.strip().lower() for realm in active_user.assigned_realms if realm.strip()}


def record_matches_admin_scope(
    assigned_realms: list[str],
    scope_realms: set[str],
) -> bool:
    if not scope_realms or "all" in scope_realms:
        return True
    target_realms = {realm.strip().lower() for realm in assigned_realms if realm.strip()}
    return "all" in target_realms or bool(target_realms & scope_realms)


def build_admin_surface_payload(
    user_manager: UserManager,
    user_log: UserLog,
    realm_manager: RealmManager,
    active_user: UserRecord | None,
    profile_manager: ProfileManager | None = None,
) -> dict[str, object]:
    scope_realms = admin_scope_realms(active_user)
    full_access = (
        active_user is None
        or "all" in scope_realms
        or user_manager.has_privilege(active_user.user_id, "all")
    )
    all_users = sorted(
        user_manager.list_users(),
        key=lambda record: (record.display_name.lower(), record.user_id),
    )
    visible_users: list[dict[str, object]] = []
    for record in all_users:
        if not full_access and not record_matches_admin_scope(record.assigned_realms, scope_realms):
            continue
        profile = profile_manager.load(record.user_id) if profile_manager is not None else None
        visible_users.append(
            {
                "user_id": record.user_id,
                "display_name": record.display_name,
                "role": record.role,
                "assigned_realms": list(record.assigned_realms),
                "departments": list(profile.departments) if profile is not None else [],
                "groups": list(profile.groups) if profile is not None else [],
                "status": record.status,
                "log_count": user_log.entry_count(record.user_id),
            }
        )
    visible_invites = [
        {
            "invite_code": invite.invite_code,
            "role": invite.role,
            "assigned_realms": list(invite.assigned_realms),
            "status": invite.status,
            "created_at": invite.created_at,
        }
        for invite in sorted(
            user_manager.list_invites(),
            key=lambda record: record.created_at,
            reverse=True,
        )
        if full_access or record_matches_admin_scope(invite.assigned_realms, scope_realms)
    ]
    visible_realms: list[dict[str, object]] = []
    for realm_name in realm_manager.list_realms():
        if not full_access and realm_name.strip().lower() not in scope_realms:
            continue
        config = realm_manager.load_realm(realm_name)
        if config is None:
            continue
        visible_realms.append(
            {
                "name": config.name,
                "purpose": config.purpose,
                "governance_sensitivity": config.governance_sensitivity,
                "user_count": sum(
                    1 for record in all_users if can_access_realm(record, config.name)
                ),
                "memory_count": count_records(
                    realm_manager.realm_data_dirs(config.name)["memory"],
                    "*.json",
                ),
            }
        )
    return {
        "users": visible_users,
        "invites": visible_invites,
        "realms": visible_realms,
        "total_users": len(visible_users),
        "total_invites": len(visible_invites),
        "total_realms": len(visible_realms),
    }


def build_admin_surface_report(admin_data: dict[str, object]) -> str:
    users = list(admin_data.get("users", []))
    invites = list(admin_data.get("invites", []))
    realms = list(admin_data.get("realms", []))
    total_users = int(admin_data.get("total_users", len(users)))
    total_invites = int(admin_data.get("total_invites", len(invites)))
    total_realms = int(admin_data.get("total_realms", len(realms)))
    lines = [
        f"admin-surface > Users: {total_users}  Invites: {total_invites}  Realms: {total_realms}",
        "",
        "USERS",
    ]
    if not users:
        lines.append("  No visible users.")
    else:
        for record in users:
            realms_text = format_realm_names(list(record.get("assigned_realms", [])))
            departments_text = format_realm_names(list(record.get("departments", [])))
            groups_text = format_realm_names(list(record.get("groups", [])))
            lines.append(
                "  "
                f"{record.get('display_name', '')} "
                f"[{record.get('role', '')}] "
                f"{record.get('status', '')} "
                f"realms: {realms_text} "
                f"departments: {departments_text} "
                f"groups: {groups_text} "
                f"log: {record.get('log_count', 0)}"
            )
    lines.extend(["", "INVITES"])
    if not invites:
        lines.append("  No visible invites.")
    else:
        for invite in invites:
            lines.append(
                "  "
                f"{invite.get('invite_code', '')} "
                f"{invite.get('role', '')}/{format_realm_names(list(invite.get('assigned_realms', [])))} "
                f"{invite.get('status', '')} "
                f"{invite.get('created_at', '')}"
            )
    lines.extend(["", "REALMS"])
    if not realms:
        lines.append("  No visible realms.")
    else:
        for realm in realms:
            purpose = str(realm.get("purpose", "")).strip() or "No purpose set."
            lines.append(
                "  "
                f"[{realm.get('name', '')}] "
                f"{purpose} "
                f"sensitivity: {realm.get('governance_sensitivity', 'open')} "
                f"users: {realm.get('user_count', 0)} "
                f"memory: {realm.get('memory_count', 0)}"
            )
    return "\n".join(lines)


def create_user_proposal(
    proposal: Proposal,
    display_name: str,
    role: str,
    realm_name: str,
    created_by: str,
) -> dict[str, object]:
    created = proposal.create(
        what=f"Create user: {display_name} with role {role}",
        why="User creation requires visible approval before it takes effect.",
        payload={
            "action": "create_user",
            "display_name": display_name,
            "role": role,
            "assigned_realms": [realm_name],
            "created_by": created_by,
        },
    )
    return {
        **created,
        "line": (
            f"[USER PROPOSAL] {created['timestamp']} | "
            f"Create user: {display_name} with role {role} | status: {created['status']}"
        ),
    }


def create_invite_proposal(
    proposal: Proposal,
    role: str,
    realm_name: str,
    created_by: str,
) -> dict[str, object]:
    created = proposal.create(
        what=f"Create invite: role={role} realm={realm_name}",
        why="Invites require visible approval before they are issued.",
        payload={
            "action": "create_invite",
            "role": role,
            "assigned_realms": [realm_name],
            "created_by": created_by,
        },
    )
    return {
        **created,
        "line": (
            f"[INVITE PROPOSAL] {created['timestamp']} | "
            f"Create invite: role={role} realm={realm_name} | status: {created['status']}"
        ),
    }


def create_realm_proposal(
    proposal: Proposal,
    realm_name: str,
    purpose: str,
    created_by: str,
) -> dict[str, object]:
    created = proposal.create(
        what=f"Create realm: {realm_name}",
        why="Realm creation requires visible approval before it takes effect.",
        payload={
            "action": "create_realm",
            "realm_name": realm_name,
            "purpose": purpose,
            "created_by": created_by,
        },
    )
    return {
        **created,
        "line": (
            f"[REALM PROPOSAL] {created['timestamp']} | "
            f"Create realm: {realm_name} | status: {created['status']}"
        ),
    }


def build_whoami_report(
    active_token: SessionToken | None,
    user_manager: UserManager | None,
) -> str:
    if active_token is None or user_manager is None:
        return 'whoami > No active session. Type "login [name]" to identify.'
    privileges = user_manager.get_role_privileges(active_token.role)
    lines = [f"whoami > {active_token.display_name} ({active_token.role})"]
    lines.append(f"whoami > user_id: {active_token.user_id}")
    lines.append(f"whoami > session token: {token_preview(active_token)} (active)")
    expires = datetime.fromisoformat(active_token.expires_at)
    lines.append(f"whoami > session expires: {expires.strftime('%b %d %H:%M')}")
    lines.append(f"whoami > privileges: {', '.join(privileges)}")
    if privileges == ["all"]:
        lines.append("whoami > can do: everything")
    return "\n".join(lines)


def format_user_log_report(
    heading: str,
    entries: list[dict],
) -> str:
    if not entries:
        return f"{heading} (0 entries):\n  No interaction log entries yet."
    lines = [f"{heading} ({len(entries)} entries):", ""]
    for entry in reversed(entries):
        timestamp = entry.get("timestamp", "")
        label = timestamp
        if timestamp:
            label = datetime.fromisoformat(timestamp).strftime("%b %d %H:%M")
        lines.append(f"  {label}  {entry.get('content', '')}")
        lines.append(f"    inanna > {entry.get('response_preview', '')}")
        lines.append("")
    return "\n".join(lines).rstrip()


def build_invites_report(
    invites: list[InviteRecord],
    active_user: UserRecord | None,
) -> str:
    if active_user is not None and active_user.role == "guardian":
        visible = invites
    elif active_user is not None:
        visible = [invite for invite in invites if invite.created_by == active_user.user_id]
    else:
        visible = []
    if not visible:
        return "Invites (0 total):\n  No invites recorded yet."
    lines = [f"Invites ({len(visible)} total):"]
    for invite in visible:
        realm_text = ",".join(invite.assigned_realms)
        if invite.status == "accepted":
            suffix = f"accepted by {invite.accepted_by}"
        elif invite.status == "expired":
            suffix = "expired"
        else:
            suffix = "pending"
        lines.append(
            f"  [{invite.status}]   {invite.invite_code}  {invite.role}/{realm_text}  {suffix}"
        )
    return "\n".join(lines)


def append_user_log_entry(
    user_log: UserLog | None,
    active_token: SessionToken | None,
    session_id: str,
    content: str,
    response_preview: str,
) -> None:
    if user_log is None or active_token is None:
        return
    user_log.append(
        user_id=active_token.user_id,
        session_id=session_id,
        role="user",
        content=content,
        response_preview=response_preview,
    )


def create_realm_context_proposal(
    proposal: Proposal,
    active_realm: RealmConfig,
    governance_context: str,
) -> dict:
    created = proposal.create(
        what=f"Update governance context for realm {active_realm.name}",
        why="Realm context changes require visible approval before they take effect.",
        payload={
            "action": "realm_context_update",
            "realm_name": active_realm.name,
            "governance_context": governance_context,
        },
    )
    return {**created, "line": format_realm_proposal_line(created)}


def startup_context_items(startup_context: dict) -> list[str | dict[str, str]]:
    return startup_context.get("summary_items", startup_context["summary_lines"])


def ensure_guardian_metrics(
    guardian_metrics: dict[str, int] | None,
) -> dict[str, int]:
    if guardian_metrics is None:
        guardian_metrics = {}
    guardian_metrics.setdefault("governance_blocks", 0)
    guardian_metrics.setdefault("tool_executions", 0)
    return guardian_metrics


def resolve_nammu_dir(session: Session, nammu_dir: Path | None = None) -> Path:
    if nammu_dir is not None:
        return nammu_dir
    return session.session_path.parent.parent / "nammu"


def ensure_directories() -> None:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    PROPOSAL_DIR.mkdir(parents=True, exist_ok=True)
    NAMMU_DIR.mkdir(parents=True, exist_ok=True)


def startup_commands_line() -> str:
    return f"Commands: {', '.join(STARTUP_COMMANDS)}"


def print_startup_context(summary_lines: list[str]) -> None:
    if not summary_lines:
        print("Prior context (0 lines):")
        print("  none yet.")
        return

    print(f"Prior context ({len(summary_lines)} lines):")
    for index, line in enumerate(summary_lines, start=1):
        print(f"  {index}. {line}")


def count_routing_log_lines(nammu_dir: Path) -> int:
    path = nammu_dir / ROUTING_LOG_FILE
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def inspect_body_report(
    config: Config,
    engine: Engine,
    session: Session,
    proposal: Proposal | None = None,
    memory_dir: Path | None = None,
    proposal_dir: Path | None = None,
    nammu_dir: Path | None = None,
    data_root: Path | None = None,
    realm_name: str = DEFAULT_REALM,
) -> BodyReport:
    resolved_memory_dir = memory_dir or MEMORY_DIR
    resolved_proposal_dir = proposal_dir or PROPOSAL_DIR
    resolved_nammu_dir = nammu_dir or NAMMU_DIR
    resolved_data_root = data_root or DATA_ROOT
    pending_count = (
        proposal.pending_count()
        if proposal is not None
        else count_records(resolved_proposal_dir, "*.txt")
    )

    return BodyInspector().inspect(
        session_id=session.session_id,
        session_started_at=session.started_at,
        realm=realm_name,
        model_url=config.model_url or "not set",
        model_name=config.model_name or "not set",
        model_mode=engine.mode,
        data_root=resolved_data_root,
        memory_record_count=count_records(resolved_memory_dir, "*.json"),
        pending_proposal_count=pending_count,
        routing_log_count=count_routing_log_lines(resolved_nammu_dir),
    )


def build_body_summary(report: BodyReport) -> dict[str, object]:
    return {
        "platform": report.platform,
        "python_version": report.python_version,
        "model_mode": report.model_mode,
        "session_uptime_seconds": report.session_uptime_seconds,
        "memory_used_pct": report.memory_used_pct,
        "disk_free_gb": report.disk_free_gb,
    }


def build_body_report(
    config: Config,
    engine: Engine,
    session: Session,
    proposal: Proposal | None = None,
    memory_dir: Path | None = None,
    proposal_dir: Path | None = None,
    nammu_dir: Path | None = None,
    data_root: Path | None = None,
    realm_name: str = DEFAULT_REALM,
) -> str:
    report = inspect_body_report(
        config=config,
        engine=engine,
        session=session,
        proposal=proposal,
        memory_dir=memory_dir,
        proposal_dir=proposal_dir,
        nammu_dir=nammu_dir,
        data_root=data_root,
        realm_name=realm_name,
    )
    return BodyInspector().format_report(report)


def build_diagnostics_report(
    config: Config,
    engine: Engine,
    session: Session,
    proposal: Proposal | None = None,
    memory_dir: Path | None = None,
    proposal_dir: Path | None = None,
    nammu_dir: Path | None = None,
    data_root: Path | None = None,
    realm_name: str = DEFAULT_REALM,
) -> str:
    return build_body_report(
        config=config,
        engine=engine,
        session=session,
        proposal=proposal,
        memory_dir=memory_dir,
        proposal_dir=proposal_dir,
        nammu_dir=nammu_dir,
        data_root=data_root,
        realm_name=realm_name,
    )


def build_history_report(report: dict) -> str:
    total = report["total"]
    if total == 0:
        return "Proposal history (0 total):\n  No proposals recorded yet."

    lines = [
        (
            "Proposal history "
            f"({total} total, {report['approved']} approved, "
            f"{report['rejected']} rejected, {report['pending']} pending):"
        ),
        "",
    ]

    entries: list[str] = []
    for record in report["records"]:
        label = f"[{record['status']}]"
        entries.append(
            "\n".join(
                [
                    f"  {label:<11}{record['proposal_id']} — {record['timestamp']}",
                    f"             {record['what']}",
                ]
            )
        )
    lines.append("\n\n".join(entries))
    return "\n".join(lines)


def build_memory_log_report(report: dict) -> str:
    total = report["total"]
    if total == 0:
        return "Memory log (0 records):\n  No approved memory records yet."

    lines = [f"Memory log ({total} records):", ""]
    entries: list[str] = []
    for record in report["records"]:
        entry_lines = [
            f"  [{record['memory_id']}] approved: {record['approved_at']}",
            f"    Session: {record['session_id']}",
            "    Lines:",
        ]
        for index, line in enumerate(record.get("summary_lines", []), start=1):
            entry_lines.append(f"      {index}. {line}")
        entries.append("\n".join(entry_lines))
    lines.append("\n\n".join(entries))
    return "\n".join(lines)


def build_proposal_history_payload(report: dict) -> dict[str, object]:
    records: list[dict[str, str]] = []
    for record in report["records"]:
        payload = {
            "proposal_id": record["proposal_id"],
            "timestamp": record["timestamp"],
            "what": record["what"],
            "status": record["status"],
        }
        if "resolved_at" in record:
            payload["resolved_at"] = record["resolved_at"]
        records.append(payload)

    return {
        "type": "proposal_history",
        "records": records,
        "total": report["total"],
        "approved": report["approved"],
        "rejected": report["rejected"],
        "pending": report["pending"],
    }


def build_routing_log_report(routing_log: list[dict[str, str]]) -> str:
    total = len(routing_log)
    if total == 0:
        return "NAMMU Routing Log (0 decisions):\n  No routing decisions recorded yet."

    lines = [f"NAMMU Routing Log ({total} decisions):"]
    for record in routing_log:
        label = f"[{record['route']}]"
        lines.append(
            f"  {label:<11}{record['timestamp']} | {record['input_preview']}"
        )
    return "\n".join(lines)


def build_nammu_log_report(nammu_dir: Path) -> str:
    routing_history = load_routing_history(nammu_dir)
    governance_history = load_governance_history(nammu_dir)
    lines = [
        (
            "NAMMU Memory "
            f"({len(routing_history)} routing, {len(governance_history)} governance):"
        ),
        "",
        "Routing history:",
    ]

    if not routing_history:
        lines.append("  No persisted routing history yet.")
    else:
        for record in routing_history:
            lines.append(
                f"  [{record.get('route', '?')}] {record.get('timestamp', '')} | "
                f"session {record.get('session_id', '?')} | {record.get('input_preview', '')}"
            )

    lines.extend(["", "Governance history:"])
    if not governance_history:
        lines.append("  No persisted governance history yet.")
    else:
        for record in governance_history:
            lines.append(
                f"  [{record.get('decision', '?')}] {record.get('timestamp', '')} | "
                f"session {record.get('session_id', '?')}"
            )
            lines.append(f"       {record.get('reason', '') or 'No reason recorded.'}")
            lines.append(f"       {record.get('input_preview', '')}")

    return "\n".join(lines)


def append_routing_decision(
    routing_log: list[dict[str, str]],
    session: Session,
    route: str,
    user_input: str,
    nammu_dir: Path | None = None,
) -> None:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_preview": user_input[:60],
        "route": route,
    }
    routing_log.append(record)
    append_routing_event(
        resolve_nammu_dir(session, nammu_dir),
        session.session_id,
        route,
        record["input_preview"],
    )


def append_governance_decision(
    session: Session,
    governance_result,
    user_input: str,
    nammu_dir: Path | None = None,
) -> None:
    if governance_result.suggests_tool:
        append_governance_event(
            resolve_nammu_dir(session, nammu_dir),
            session.session_id,
            "tool",
            "Current information requires governed tool use.",
            user_input[:60],
        )
        return

    if governance_result.decision != "allow":
        append_governance_event(
            resolve_nammu_dir(session, nammu_dir),
            session.session_id,
            governance_result.decision,
            governance_result.reason,
            user_input[:60],
        )


def create_memory_request_proposal(
    proposal: Proposal,
    session: Session,
    user_input: str,
    reason: str,
    user_id: str = "",
) -> dict:
    return proposal.create(
        what="Store a requested memory from direct user instruction",
        why=reason,
        payload={
            "session_id": session.session_id,
            "summary_lines": [f"user: {user_input}"],
            "user_id": user_id,
        },
    )


def extract_reflection_proposal(text: str) -> tuple[str | None, str | None]:
    match = REFLECT_PATTERN.search(str(text or ""))
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return None, None


def strip_reflection_markup(text: str) -> str:
    cleaned = REFLECT_PATTERN.sub("", str(text or "")).strip()
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


def create_reflection_proposal(
    proposal: Proposal,
    session: Session,
    entry: ReflectionEntry,
) -> dict[str, Any]:
    created = proposal.create(
        what="INANNA self-reflection",
        why="INANNA proposed a governed self-observation.",
        payload={
            "action": "reflection",
            "session_id": session.session_id,
            "entry": {
                "entry_id": entry.entry_id,
                "observation": entry.observation,
                "context": entry.context,
                "approved_at": entry.approved_at,
                "approved_by": entry.approved_by,
                "created_at": entry.created_at,
            },
        },
    )
    preview = entry.observation[:72]
    return {
        **created,
        "line": (
            f"[REFLECTION PROPOSAL] {created['timestamp']} | "
            f"{preview} | status: {created['status']}"
        ),
    }


def maybe_capture_reflection_proposal(
    response_text: str,
    proposal: Proposal | None,
    session: Session | None,
    reflective_memory: ReflectiveMemory | None,
) -> tuple[str, dict[str, Any] | None]:
    observation, context = extract_reflection_proposal(response_text)
    if observation is None or context is None:
        return str(response_text or "").strip(), None
    cleaned = strip_reflection_markup(response_text)
    if proposal is None or session is None or reflective_memory is None:
        return cleaned, None
    entry = reflective_memory.propose(observation, context)
    return cleaned, create_reflection_proposal(proposal, session, entry)


def reflection_entry_from_payload(payload: dict[str, Any]) -> ReflectionEntry | None:
    entry_payload = payload.get("entry", {})
    if not isinstance(entry_payload, dict):
        return None
    try:
        return ReflectionEntry(**entry_payload)
    except TypeError:
        return None


def build_auto_memory_events(
    session: Session,
    user_log: UserLog | None,
    active_token: SessionToken | None,
) -> list[dict[str, str]]:
    if user_log is None or active_token is None:
        return list(session.events)

    entries = [
        entry
        for entry in user_log.load(active_token.user_id, limit=200)
        if entry.get("session_id") == session.session_id
    ]
    if not entries:
        return list(session.events)

    events: list[dict[str, str]] = []
    for entry in entries[-20:]:
        content = str(entry.get("content", "")).strip()
        response = str(entry.get("response_preview", "")).strip()
        if content:
            events.append({"role": "user", "content": content})
        if response:
            role = "analyst" if content.lower().startswith("analyse") else "assistant"
            events.append({"role": role, "content": response})
    return events or list(session.events)


def maybe_auto_write_memory(
    *,
    memory: Memory,
    session: Session,
    active_realm_name: str,
    active_token: SessionToken | None,
    user_log: UserLog | None,
    turn_count: int,
    last_written_turn: int,
    reason: str,
    session_audit: list[dict[str, object]] | None = None,
) -> dict[str, object] | None:
    pending_turns = turn_count - last_written_turn
    if pending_turns <= 0:
        return None

    candidate = memory.build_candidate(
        session_id=session.session_id,
        events=build_auto_memory_events(session, user_log, active_token),
        user_id=active_token.user_id if active_token is not None else "",
    )
    summary_lines = list(candidate.get("summary_lines", []))
    if not summary_lines:
        return None

    approved_at = datetime.now(timezone.utc).isoformat()
    memory_id = (
        f"auto-memory-{session.session_id}-{reason.replace(' ', '-')}-{turn_count}-"
        f"{int(time.time() * 1000)}"
    )
    memory.write_memory(
        proposal_id=memory_id,
        session_id=session.session_id,
        summary_lines=summary_lines,
        approved_at=approved_at,
        realm_name=active_realm_name,
        user_id=active_token.user_id if active_token is not None else "",
    )
    append_audit_event(
        session_audit,
        "auto_memory",
        f"auto-memory: {pending_turns} turns written at {reason}",
        {
            "memory_id": memory_id,
            "turns_written": pending_turns,
            "reason": reason,
        },
    )
    return {
        "memory_id": memory_id,
        "turns_written": pending_turns,
        "approved_at": approved_at,
    }


def record_completed_turn(
    *,
    conversation_state: dict[str, int] | None,
    memory: Memory,
    session: Session,
    active_realm_name: str,
    active_token: SessionToken | None,
    user_log: UserLog | None,
    session_audit: list[dict[str, object]] | None = None,
) -> dict[str, object] | None:
    if conversation_state is None:
        return None
    turn_count = int(conversation_state.get("turn_count", 0)) + 1
    conversation_state["turn_count"] = turn_count
    conversation_state.setdefault("last_auto_memory_turn", 0)
    if turn_count % AUTO_MEMORY_TURN_THRESHOLD != 0:
        return None
    written = maybe_auto_write_memory(
        memory=memory,
        session=session,
        active_realm_name=active_realm_name,
        active_token=active_token,
        user_log=user_log,
        turn_count=turn_count,
        last_written_turn=int(conversation_state.get("last_auto_memory_turn", 0)),
        reason="threshold",
        session_audit=session_audit,
    )
    if written is not None:
        conversation_state["last_auto_memory_turn"] = turn_count
    return written


def finalize_auto_memory(
    *,
    conversation_state: dict[str, int] | None,
    memory: Memory,
    session: Session,
    active_realm_name: str,
    active_token: SessionToken | None,
    user_log: UserLog | None,
    reason: str = "session end",
    session_audit: list[dict[str, object]] | None = None,
) -> dict[str, object] | None:
    if conversation_state is None:
        return None
    conversation_state.setdefault("turn_count", 0)
    conversation_state.setdefault("last_auto_memory_turn", 0)
    written = maybe_auto_write_memory(
        memory=memory,
        session=session,
        active_realm_name=active_realm_name,
        active_token=active_token,
        user_log=user_log,
        turn_count=int(conversation_state["turn_count"]),
        last_written_turn=int(conversation_state["last_auto_memory_turn"]),
        reason=reason,
        session_audit=session_audit,
    )
    if written is not None:
        conversation_state["last_auto_memory_turn"] = int(conversation_state["turn_count"])
    return written


def build_process_status_payload(process_monitor: ProcessMonitor) -> dict[str, object]:
    processes = []
    for record in process_monitor.all_records():
        uptime = (
            process_monitor.format_uptime(record.uptime_seconds)
            if record.uptime_seconds > 0
            else ("0s" if record.name == "INANNA NYX Server" else "unknown")
        )
        processes.append(
            {
                "name": record.name,
                "pid": record.pid,
                "status": record.status,
                "uptime": uptime,
                "description": record.description,
                "endpoint": record.endpoint,
                "memory_mb": record.memory_mb,
                "cpu_percent": record.cpu_percent,
            }
        )
    return {"type": "process_status", "processes": processes}


def build_process_status_report(payload: dict[str, object]) -> str:
    lines = ["process-status > Live process view:"]
    for record in list(payload.get("processes", [])):
        lines.append(
            f"  [{record.get('status', 'unknown')}] {record.get('name', 'process')}"
        )
        lines.append(f"    {record.get('description', '')}")
        lines.append(
            f"    uptime: {record.get('uptime', 'unknown')}  "
            f"memory: {record.get('memory_mb', 'unknown')}  "
            f"cpu: {record.get('cpu_percent', 'unknown')}"
        )
    return "\n".join(lines)


def create_tool_use_proposal(
    proposal: Proposal,
    session: Session,
    user_input: str,
    tool: str,
    query: str,
    params: dict[str, Any] | None = None,
) -> dict:
    created = proposal.create(
        what=f"{tool} tool use",
        why="User requested information or connectivity that requires approved tool use.",
        payload={
            "action": "tool_use",
            "tool": tool,
            "query": query,
            "params": dict(params or {"query": query}),
            "original_input": user_input,
            "session_id": session.session_id,
        },
    )
    return {
        **created,
        "tool_line": (
            f"[TOOL PROPOSAL] {created['timestamp']} | "
            f"Use {tool} for: {query} | status: {created['status']}"
        ),
    }


def create_communication_send_proposal(
    proposal: Proposal,
    session: Session,
    user_input: str,
    app: str,
    contact: str,
    message: str,
    stage: str = "draft",
) -> dict[str, Any]:
    normalized_stage = "execute_send" if str(stage).strip().lower() in {
        "execute_send",
        "send",
        "confirm",
    } else "draft"
    app_label = display_communication_app_name(app)
    contact_label = normalize_request_fragment(contact) or "contact"
    message_text = str(message or "").strip()
    summary = (
        f"Send drafted message in {app_label} to {contact_label}"
        if normalized_stage == "execute_send"
        else f"Type draft message in {app_label} to {contact_label}"
    )
    prompt_text = (
        f'Send this message to {contact_label} on {app_label}?\n"{message_text}"'
        if normalized_stage == "execute_send"
        else f'Type this message as a draft in {app_label} to {contact_label}?\n"{message_text}"'
    )
    created = proposal.create(
        what=summary,
        why=(
            "Sending a communication draft is a consequential action and requires explicit approval."
            if normalized_stage == "execute_send"
            else "User requested a governed communication draft before any message is sent."
        ),
        payload={
            "action": "tool_use",
            "tool": "comm_send_message",
            "query": build_communication_send_query(app, contact_label, message_text),
            "params": {
                "app": normalize_app_name(app),
                "contact": contact_label,
                "message": message_text,
                "mode": normalized_stage,
            },
            "original_input": user_input,
            "session_id": session.session_id,
        },
    )
    tool_line = (
        f"[TOOL PROPOSAL] {created['timestamp']} | "
        f"{summary} | status: {created['status']}"
    )
    return {
        **created,
        "prompt_text": prompt_text,
        "tool_line": tool_line,
        "line": f"{prompt_text}\n{tool_line}",
    }


def create_email_send_proposal(
    proposal: Proposal,
    session: Session,
    user_input: str,
    app: str,
    *,
    recipient: str = "",
    subject: str = "",
    body: str = "",
    subject_or_sender: str = "",
    stage: str = "draft",
    workflow: str = "email_compose",
) -> dict[str, Any]:
    normalized_stage = "execute_send" if str(stage).strip().lower() in {
        "execute_send",
        "send",
        "confirm",
    } else "draft"
    app_label = display_email_app_name(app)
    cleaned_recipient = normalize_request_fragment(recipient)
    cleaned_subject = normalize_request_fragment(subject)
    cleaned_target = normalize_request_fragment(subject_or_sender)
    body_text = str(body or "").strip()
    is_reply = workflow == "email_reply"
    summary = (
        f"Send drafted email in {app_label}"
        if normalized_stage == "execute_send"
        else (
            f"Compose reply draft in {app_label} for {cleaned_target or 'selected email'}"
            if is_reply
            else f"Compose email draft in {app_label} to {cleaned_recipient or 'recipient'}"
        )
    )
    header_lines = []
    if cleaned_recipient:
        header_lines.append(f"To: {cleaned_recipient}")
    if cleaned_subject:
        header_lines.append(f"Subject: {cleaned_subject}")
    if cleaned_target and is_reply:
        header_lines.append(f"Reply target: {cleaned_target}")
    header_lines.append("---")
    header_lines.append(body_text)
    header_text = "\n".join(header_lines)
    prompt_text = (
        f"Send this email from {app_label}?\n{header_text}"
        if normalized_stage == "execute_send"
        else (
            f"Compose this reply draft in {app_label}?\n{header_text}"
            if is_reply
            else f"Compose this email draft in {app_label}?\n{header_text}"
        )
    )
    payload_params: dict[str, Any] = {
        "app": normalize_email_app(app),
        "mode": normalized_stage,
    }
    if is_reply:
        payload_params["subject_or_sender"] = cleaned_target
        payload_params["body"] = body_text
        tool_name = "email_reply"
        query = build_email_reply_query(app, cleaned_target)
    else:
        payload_params["to"] = cleaned_recipient
        payload_params["subject"] = cleaned_subject
        payload_params["body"] = body_text
        tool_name = "email_compose"
        query = build_email_compose_query(app, cleaned_recipient, cleaned_subject)
    created = proposal.create(
        what=summary,
        why=(
            "Sending an email is a consequential action and requires explicit approval."
            if normalized_stage == "execute_send"
            else "User requested a governed email draft before any email is sent."
        ),
        payload={
            "action": "tool_use",
            "tool": tool_name,
            "query": query,
            "params": payload_params,
            "original_input": user_input,
            "session_id": session.session_id,
        },
    )
    tool_line = (
        f"[TOOL PROPOSAL] {created['timestamp']} | "
        f"{summary} | status: {created['status']}"
    )
    return {
        **created,
        "prompt_text": prompt_text,
        "tool_line": tool_line,
        "line": f"{prompt_text}\n{tool_line}",
    }


def create_orchestration_proposal(
    proposal: Proposal,
    session: Session,
    user_input: str,
    plan: OrchestrationPlan,
) -> dict[str, Any]:
    created = proposal.create(
        what=f"Multi-Faculty task: {plan.chain_label()}",
        why="User requested a governed multi-Faculty orchestration.",
        payload={
            "action": "orchestration",
            "original_input": user_input,
            "session_id": session.session_id,
            "plan": plan.to_payload(),
        },
    )
    return {
        **created,
        "line": (
            f"[ORCHESTRATION PROPOSAL] {created['timestamp']} | "
            f"Multi-Faculty task: {plan.chain_label()} | "
            f"{plan.describe_steps()} | status: {created['status']}"
        ),
    }


def execute_orchestration_plan(
    *,
    plan: OrchestrationPlan,
    user_input: str,
    grounding: str | list[str | dict[str, str]] | None,
    config: Config,
    engine: Engine,
    orchestration_engine: OrchestrationEngine,
    faculty_monitor: FacultyMonitor | None = None,
    grounding_prefix: str = "",
) -> dict[str, Any]:
    if isinstance(grounding, list):
        grounding_items = list(grounding)
    elif isinstance(grounding, str) and grounding.strip():
        grounding_items = [grounding.strip()]
    else:
        grounding_items = []

    previous_output = user_input
    executed_steps: list[dict[str, str]] = []

    for step in plan.steps:
        step_input = user_input if step.input_from == "user" else previous_output
        if step.purpose == "synthesize":
            step_input = orchestration_engine.format_synthesis_prompt(
                user_input,
                previous_output,
                step,
            )

        if step.faculty == "sentinel":
            t0 = time.monotonic()
            step_output = run_sentinel_response(
                user_input=step_input,
                grounding=grounding_items,
                lm_url=config.model_url,
                model_name=config.model_name,
                faculties_path=FACULTIES_CONFIG_PATH,
                grounding_prefix=grounding_prefix,
            )
            mode = sentinel_response_mode(step_output)
            if faculty_monitor is not None:
                faculty_monitor.record_call(
                    "sentinel",
                    (time.monotonic() - t0) * 1000,
                    mode == "connected",
                )
                faculty_monitor.set_mode("sentinel", mode)
        elif step.faculty == "crown":
            t0 = time.monotonic()
            step_output = engine.respond(
                context_summary=grounding_items,
                conversation=[{"role": "user", "content": step_input}],
            )
            if faculty_monitor is not None:
                faculty_monitor.record_call("crown", (time.monotonic() - t0) * 1000, True)
        else:
            raise ValueError(f"Unsupported orchestration faculty: {step.faculty}")

        previous_output = step_output
        executed_steps.append(
            {
                "faculty": step.faculty,
                "purpose": step.purpose,
                "input_from": step.input_from,
                "output_to": step.output_to,
            }
        )

    return {
        "chain": plan.chain_label(),
        "steps": executed_steps,
        "text": previous_output,
    }


def complete_orchestration_resolution(
    *,
    resolved: dict[str, Any],
    decision: str,
    session: Session,
    memory: Memory,
    engine: Engine,
    config: Config,
    startup_context: dict[str, Any],
    orchestration_engine: OrchestrationEngine,
    active_token: SessionToken | None = None,
    user_log: UserLog | None = None,
    faculty_monitor: FacultyMonitor | None = None,
    session_audit: list[dict[str, object]] | None = None,
    active_realm_name: str = "",
    conversation_state: dict[str, int] | None = None,
    current_user: UserRecord | None = None,
    profile_manager: ProfileManager | None = None,
) -> dict[str, Any]:
    payload = resolved["payload"]
    original_input = str(payload.get("original_input", "")).strip()
    plan = OrchestrationPlan.from_payload(payload.get("plan", {}))
    compact_chain = plan.chain_label(separator="->")

    if decision != "approve":
        append_audit_event(
            session_audit,
            "orchestration",
            (
                f'orchestration rejected: {compact_chain} | input: "{original_input[:60]}" | '
                f"steps: {len(plan.steps)} | proposal: {resolved['proposal_id']}"
            ),
            {
                "proposal_id": resolved["proposal_id"],
                "chain": compact_chain,
                "steps": len(plan.steps),
                "input_preview": original_input[:60],
                "approved": False,
            },
        )
        return {
            "display_text": f"Rejected {resolved['proposal_id']}.",
            "response": None,
        }

    session.add_event("user", original_input)
    outcome = execute_orchestration_plan(
        plan=plan,
        user_input=original_input,
        grounding=startup_context_items(startup_context),
        config=config,
        engine=engine,
        orchestration_engine=orchestration_engine,
        faculty_monitor=faculty_monitor,
        grounding_prefix=build_grounding_prefix(
            profile_manager,
            current_user,
            active_token,
        ),
    )
    final_text = str(outcome["text"]).strip()
    session.add_event("assistant", final_text)
    append_user_log_entry(
        user_log,
        active_token,
        session.session_id,
        original_input,
        final_text,
    )
    append_audit_event(
        session_audit,
        "orchestration",
        (
            f'orchestration: {compact_chain} | input: "{original_input[:60]}" | '
            f"steps: {len(outcome['steps'])} | approved: {resolved['proposal_id']}"
        ),
        {
            "proposal_id": resolved["proposal_id"],
            "chain": compact_chain,
            "steps": len(outcome["steps"]),
            "input_preview": original_input[:60],
            "approved": True,
        },
    )
    record_completed_turn(
        conversation_state=conversation_state,
        memory=memory,
        session=session,
        active_realm_name=active_realm_name,
        active_token=active_token,
        user_log=user_log,
        session_audit=session_audit,
    )
    return {
        "display_text": f"orchestration > {outcome['chain']}\n{final_text}",
        "response": {
            "type": "orchestration",
            "chain": outcome["chain"],
            "steps": outcome["steps"],
            "text": final_text,
            "proposal_id": resolved["proposal_id"],
        },
    }


def serialize_file_info(info: FileInfo) -> dict[str, object]:
    return {
        "path": info.path,
        "name": info.name,
        "size_bytes": info.size_bytes,
        "size_human": info.size_human,
        "is_dir": info.is_dir,
        "is_file": info.is_file,
        "modified_at": info.modified_at,
        "created_at": info.created_at,
        "permissions": info.permissions,
        "extension": info.extension,
    }


def serialize_process_record(record: FacultyProcessRecord) -> dict[str, object]:
    return {
        "pid": record.pid,
        "name": record.name,
        "status": record.status,
        "cpu_percent": record.cpu_percent,
        "memory_mb": record.memory_mb,
        "memory_percent": record.memory_percent,
        "username": record.username,
        "started_at": record.started_at,
        "cmdline": record.cmdline,
    }


def serialize_package_record(record: FacultyPackageRecord) -> dict[str, object]:
    return {
        "name": record.name,
        "version": record.version,
        "description": record.description,
        "installed": record.installed,
    }


def serialize_system_info(info: FacultySystemInfo) -> dict[str, object]:
    return {
        "platform": info.platform,
        "hostname": info.hostname,
        "uptime_seconds": info.uptime_seconds,
        "uptime_human": info.uptime_human,
        "cpu_count": info.cpu_count,
        "cpu_percent": info.cpu_percent,
        "ram_total_gb": info.ram_total_gb,
        "ram_used_gb": info.ram_used_gb,
        "ram_percent": info.ram_percent,
        "disk_total_gb": info.disk_total_gb,
        "disk_used_gb": info.disk_used_gb,
        "disk_percent": info.disk_percent,
        "python_version": info.python_version,
    }


def build_filesystem_tool_result(
    tool_name: str,
    fs_result: FileSystemResult,
    filesystem_faculty: FileSystemFaculty,
) -> ToolResult:
    data: dict[str, Any] = {
        "formatted": filesystem_faculty.format_result(fs_result),
        "operation": fs_result.operation,
        "path": fs_result.path,
        "truncated": fs_result.truncated,
        "bytes_read": fs_result.bytes_read,
    }
    if fs_result.content is not None:
        data["content"] = fs_result.content
    if fs_result.info is not None:
        data["info"] = serialize_file_info(fs_result.info)
    if fs_result.entries:
        data["entries"] = [serialize_file_info(entry) for entry in fs_result.entries]
    return ToolResult(
        tool=tool_name,
        query=fs_result.path,
        success=fs_result.success,
        data=data,
        error=str(fs_result.error or ""),
    )


def build_process_tool_result(
    tool_name: str,
    process_result: FacultyProcessResult,
    process_faculty: ProcessFaculty,
) -> ToolResult:
    data: dict[str, Any] = {
        "formatted": process_faculty.format_result(process_result),
        "operation": process_result.operation,
        "count": process_result.count,
        "stdout": process_result.stdout,
        "stderr": process_result.stderr,
        "returncode": process_result.returncode,
    }
    if process_result.records:
        data["records"] = [serialize_process_record(record) for record in process_result.records]
    if process_result.system_info is not None:
        data["system_info"] = serialize_system_info(process_result.system_info)
    return ToolResult(
        tool=tool_name,
        query=process_result.query,
        success=process_result.success,
        data=data,
        error=str(process_result.error or ""),
    )


def build_package_tool_result(
    tool_name: str,
    package_result: FacultyPackageResult,
    package_faculty: PackageFaculty,
) -> ToolResult:
    data: dict[str, Any] = {
        "formatted": package_faculty.format_result(package_result),
        "operation": package_result.operation,
        "output": package_result.output,
        "package_manager": package_result.package_manager,
    }
    if package_result.records:
        data["records"] = [serialize_package_record(record) for record in package_result.records]
    return ToolResult(
        tool=tool_name,
        query=package_result.query,
        success=package_result.success,
        data=data,
        error=str(package_result.error or ""),
    )


def build_desktop_tool_result(
    tool_name: str,
    desktop_result: DesktopResult,
    desktop_faculty: DesktopFaculty,
) -> ToolResult:
    data: dict[str, Any] = {
        "formatted": desktop_faculty.format_result(desktop_result),
        "operation": desktop_result.tool,
        "output": desktop_result.output,
        "window_title": desktop_result.window_title,
        "screenshot_path": desktop_result.screenshot_path,
        "element_found": desktop_result.element_found,
        "consequential": desktop_result.consequential,
        "backend": desktop_faculty.backend_name,
    }
    return ToolResult(
        tool=tool_name,
        query=desktop_result.query,
        success=desktop_result.success,
        data=data,
        error=str(desktop_result.error or ""),
    )


def build_communication_tool_result(
    tool_name: str,
    workflow_result: WorkflowResult,
    communication_workflows: CommunicationWorkflows,
    *,
    query: str,
    contact: str = "",
    message: str = "",
    mode: str = "",
) -> ToolResult:
    data: dict[str, Any] = {
        "formatted": communication_workflows.format_result(workflow_result),
        "workflow": workflow_result.workflow,
        "app": workflow_result.app,
        "messages": [
            {
                "sender": record.sender,
                "content": record.content,
                "timestamp": record.timestamp,
                "unread": record.unread,
                "app": record.app,
            }
            for record in workflow_result.messages
        ],
        "output": workflow_result.output,
        "draft_visible": workflow_result.draft_visible,
        "steps_completed": list(workflow_result.steps_completed),
        "contact": contact,
        "message": message,
        "mode": mode,
    }
    return ToolResult(
        tool=tool_name,
        query=query,
        success=workflow_result.success,
        data=data,
        error=str(workflow_result.error or ""),
    )


def serialize_email_record(record: EmailRecord) -> dict[str, object]:
    return {
        "sender": record.sender,
        "subject": record.subject,
        "preview": record.preview,
        "date": record.date,
        "unread": record.unread,
        "app": record.app,
    }


def build_email_tool_result(
    tool_name: str,
    workflow_result: EmailWorkflowResult,
    email_workflows: EmailWorkflows,
    *,
    query: str,
    recipient: str = "",
    subject: str = "",
    body: str = "",
    subject_or_sender: str = "",
    mode: str = "",
    param_payload: dict[str, Any] | None = None,
) -> ToolResult:
    data: dict[str, Any] = {
        "formatted": email_workflows.format_result(workflow_result),
        "workflow": workflow_result.workflow,
        "app": workflow_result.app,
        "emails": [serialize_email_record(record) for record in workflow_result.emails],
        "output": workflow_result.output,
        "draft_visible": workflow_result.draft_visible,
        "steps_completed": list(workflow_result.steps_completed),
        "recipient": workflow_result.recipient or recipient,
        "subject": workflow_result.subject or subject,
        "body": body,
        "subject_or_sender": subject_or_sender,
        "mode": mode,
        "params": dict(param_payload or {}),
    }
    return ToolResult(
        tool=tool_name,
        query=query,
        success=workflow_result.success,
        data=data,
        error=str(workflow_result.error or ""),
    )


def run_filesystem_tool(
    filesystem_faculty: FileSystemFaculty,
    tool_name: str,
    params: dict[str, Any],
) -> ToolResult:
    if tool_name == "read_file":
        result = filesystem_faculty.read_file(str(params.get("path", "")))
    elif tool_name == "list_dir":
        result = filesystem_faculty.list_dir(str(params.get("path", "")))
    elif tool_name == "file_info":
        result = filesystem_faculty.file_info(str(params.get("path", "")))
    elif tool_name == "search_files":
        result = filesystem_faculty.search_files(
            str(params.get("directory", "")),
            str(params.get("pattern", "")),
        )
    elif tool_name == "write_file":
        result = filesystem_faculty.write_file(
            str(params.get("path", "")),
            str(params.get("content", "")),
            overwrite=bool(params.get("overwrite", False)),
        )
    else:
        result = FileSystemResult(
            success=False,
            operation=tool_name,
            path=str(params.get("path", "") or params.get("directory", "")),
            error=f"Unknown file system tool: {tool_name}",
        )
    return build_filesystem_tool_result(tool_name, result, filesystem_faculty)


def run_process_tool(
    process_faculty: ProcessFaculty,
    tool_name: str,
    params: dict[str, Any],
) -> ToolResult:
    if tool_name == "list_processes":
        result = process_faculty.list_processes(
            filter_name=str(params.get("filter", "")),
            sort_by=str(params.get("sort", "memory")),
            limit=int(params.get("limit", 20) or 20),
        )
    elif tool_name == "system_info":
        result = process_faculty.system_info()
    elif tool_name == "kill_process":
        result = process_faculty.kill_process(int(params.get("pid", 0) or 0))
    elif tool_name == "run_command":
        result = process_faculty.run_command(
            str(params.get("command", "")),
            timeout=int(params.get("timeout", 30) or 30),
        )
    else:
        result = FacultyProcessResult(
            success=False,
            operation=tool_name,
            query=str(params.get("filter", "") or params.get("command", "") or params.get("pid", "")),
            error=f"Unknown process tool: {tool_name}",
        )
    return build_process_tool_result(tool_name, result, process_faculty)


def parse_boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def run_desktop_tool(
    desktop_faculty: DesktopFaculty,
    tool_name: str,
    params: dict[str, Any],
) -> ToolResult:
    if tool_name == "desktop_open_app":
        result = desktop_faculty.open_app(str(params.get("app", "") or params.get("query", "")))
    elif tool_name == "desktop_read_window":
        try:
            max_depth = int(params.get("max_depth", 5) or 5)
        except (TypeError, ValueError):
            max_depth = 5
        result = desktop_faculty.read_window(
            str(params.get("app_name", "") or params.get("query", "")),
            max_depth,
        )
    elif tool_name == "desktop_click":
        result = desktop_faculty.click(
            str(params.get("label", "") or params.get("query", "")),
            str(params.get("app_name", "")),
        )
    elif tool_name == "desktop_type":
        result = desktop_faculty.type_text(
            str(params.get("text", "") or params.get("query", "")),
            parse_boolish(params.get("submit", False)),
        )
    elif tool_name == "desktop_screenshot":
        result = desktop_faculty.screenshot(
            str(params.get("app_name", "") or params.get("query", "")),
        )
    else:
        result = DesktopResult(False, tool_name, "", error=f"Unknown desktop tool: {tool_name}")
    return build_desktop_tool_result(tool_name, result, desktop_faculty)


def run_communication_tool(
    communication_workflows: CommunicationWorkflows,
    tool_name: str,
    params: dict[str, Any],
) -> ToolResult:
    app = normalize_app_name(str(params.get("app", "") or params.get("query", "")))
    contact = str(params.get("contact", "")).strip()
    message = str(params.get("message", "")).strip()
    mode = str(params.get("mode", "draft") or "draft").strip().lower()

    if tool_name == "comm_read_messages":
        result = communication_workflows.read_messages(app)
        query = f"{display_communication_app_name(app)} messages"
    elif tool_name == "comm_list_contacts":
        result = communication_workflows.list_contacts(app)
        query = f"{display_communication_app_name(app)} contacts"
    elif tool_name == "comm_send_message":
        query = build_communication_send_query(app, contact, message)
        if mode == "execute_send":
            result = communication_workflows.execute_send(app)
        else:
            result = communication_workflows.send_message(app, contact, message)
    else:
        result = WorkflowResult(
            success=False,
            workflow=tool_name,
            app=app,
            error=f"Unknown communication tool: {tool_name}",
        )
        query = build_communication_send_query(app, contact, message) if contact or message else app

    return build_communication_tool_result(
        tool_name,
        result,
        communication_workflows,
        query=query,
        contact=contact,
        message=message,
        mode=mode,
    )


def run_email_tool(
    email_workflows: EmailWorkflows,
    tool_name: str,
    params: dict[str, Any],
) -> ToolResult:
    app = normalize_email_app(str(params.get("app", "") or DEFAULT_EMAIL_CLIENT))
    mode = str(params.get("mode", "draft") or "draft").strip().lower()
    if tool_name == "email_read_inbox":
        max_emails = int(params.get("max_emails", 10) or 10)
        result = email_workflows.read_inbox(app, max_emails=max_emails)
        query = f"{display_email_app_name(app)} inbox"
        return build_email_tool_result(
            tool_name,
            result,
            email_workflows,
            query=query,
            mode=mode,
            param_payload=dict(params),
        )

    if tool_name == "email_read_message":
        subject_or_sender = str(params.get("subject_or_sender", "") or params.get("query", "")).strip()
        result = email_workflows.read_email(subject_or_sender, app)
        query = f"{display_email_app_name(app)} email: {subject_or_sender}"
        return build_email_tool_result(
            tool_name,
            result,
            email_workflows,
            query=query,
            subject_or_sender=subject_or_sender,
            mode=mode,
            param_payload=dict(params),
        )

    if tool_name == "email_search":
        search_query = str(params.get("query", "")).strip()
        result = email_workflows.search_emails(search_query, app)
        query = f"{display_email_app_name(app)} search: {search_query}"
        return build_email_tool_result(
            tool_name,
            result,
            email_workflows,
            query=query,
            mode=mode,
            param_payload=dict(params),
        )

    if tool_name == "email_compose":
        recipient = str(params.get("to", "")).strip()
        subject = str(params.get("subject", "")).strip()
        body = str(params.get("body", "")).strip()
        query = build_email_compose_query(app, recipient, subject)
        if mode == "execute_send":
            result = email_workflows.execute_send(app)
        else:
            result = email_workflows.compose_draft(app=app, to=recipient, subject=subject, body=body)
        return build_email_tool_result(
            tool_name,
            result,
            email_workflows,
            query=query,
            recipient=recipient,
            subject=subject,
            body=body,
            mode=mode,
            param_payload=dict(params),
        )

    if tool_name == "email_reply":
        subject_or_sender = str(params.get("subject_or_sender", "")).strip()
        body = str(params.get("body", "")).strip()
        query = build_email_reply_query(app, subject_or_sender)
        if mode == "execute_send":
            result = email_workflows.execute_send(app)
        else:
            result = email_workflows.reply_draft(
                app=app,
                subject_or_sender=subject_or_sender,
                body=body,
            )
        return build_email_tool_result(
            tool_name,
            result,
            email_workflows,
            query=query,
            body=body,
            subject_or_sender=subject_or_sender,
            mode=mode,
            param_payload=dict(params),
        )

    result = EmailWorkflowResult(
        success=False,
        workflow=tool_name,
        app=app,
        error=f"Unknown email tool: {tool_name}",
    )
    return build_email_tool_result(
        tool_name,
        result,
        email_workflows,
        query=app,
        mode=mode,
        param_payload=dict(params),
    )


def run_package_tool(
    package_faculty: PackageFaculty,
    tool_name: str,
    params: dict[str, Any],
    software_registry: SoftwareRegistry | None = None,
) -> ToolResult:
    if tool_name == "search_packages":
        result = package_faculty.search(str(params.get("query", "") or params.get("package", "")))
    elif tool_name == "list_packages":
        result = package_faculty.list_installed(str(params.get("filter", "")))
    elif tool_name == "install_package":
        pkg_name = str(params.get("package", "") or params.get("query", ""))
        # Deduplication: check if already installed before proceeding
        if software_registry is not None:
            existing = software_registry.is_installed(pkg_name)
            if existing:
                # Return a special result indicating already installed
                from core.package_faculty import PackageResult as FPR
                already = FPR(
                    success=True,
                    operation="already_installed",
                    query=pkg_name,
                    output=f"{existing.name} (version {existing.version}) is already installed.",
                    package_manager=package_faculty.pm,
                )
                return build_package_tool_result(tool_name, already, package_faculty)
        result = package_faculty.install(pkg_name)
    elif tool_name == "remove_package":
        result = package_faculty.remove(str(params.get("package", "") or params.get("query", "")))
    elif tool_name == "launch_app":
        app_name = str(params.get("app", "") or params.get("query", "") or params.get("package", ""))
        reg = software_registry or SoftwareRegistry()
        launch_result = reg.launch(app_name)
        # Build a ToolResult directly from LaunchResult
        from core.package_faculty import PackageResult as FPR
        pr = FPR(
            success=launch_result.success,
            operation="launch",
            query=app_name,
            output=(
                f"Launched {launch_result.app_name}."
                if launch_result.success
                else f"Could not launch {app_name}: {launch_result.error}"
            ),
            package_manager="system",
            error=launch_result.error,
        )
        return build_package_tool_result(tool_name, pr, package_faculty)
    else:
        result = FacultyPackageResult(
            success=False,
            operation=tool_name,
            query=str(params.get("query", "") or params.get("package", "") or params.get("filter", "")),
            error=f"Unknown package tool: {tool_name}",
            package_manager=package_faculty.pm,
        )
    return build_package_tool_result(tool_name, result, package_faculty)


def build_document_tool_result(
    tool_name: str,
    record: DocumentRecord | DocumentWriteResult,
    document_workflows: DocumentWorkflows,
    comprehension: DocumentComprehension | None = None,
) -> ToolResult:
    if isinstance(record, DocumentRecord):
        return ToolResult(
            tool=tool_name,
            query=record.path,
            success=record.success,
            data={
                "path": record.path,
                "title": record.title,
                "format": record.format,
                "content": record.content,
                "word_count": record.word_count,
                "page_count": record.page_count,
                "sheet_names": list(record.sheet_names),
                "record": record,
                "comprehension": comprehension or DocumentComprehension(),
                "comprehension_data": {
                    "title": comprehension.title if comprehension else "",
                    "format": comprehension.format if comprehension else "",
                    "word_count": comprehension.word_count if comprehension else 0,
                    "page_count": comprehension.page_count if comprehension else 0,
                    "summary_lines": list(comprehension.summary_lines) if comprehension else [],
                    "key_points": list(comprehension.key_points) if comprehension else [],
                    "suggested_actions": list(comprehension.suggested_actions) if comprehension else [],
                },
                "formatted": document_workflows.format_read_result(
                    record,
                    comprehension or DocumentComprehension(),
                ),
            },
            error=record.error,
        )
    return ToolResult(
        tool=tool_name,
        query=record.path,
        success=record.success,
        data={
            "path": record.path,
            "format": record.format,
            "word_count": record.word_count,
            "formatted": document_workflows.format_write_result(record),
        },
        error=record.error,
    )


def build_browser_tool_result(
    tool_name: str,
    record: PageRecord | BrowserActionResult,
    browser_workflows: BrowserWorkflows,
    query: str,
    comprehension: BrowserComprehension | None = None,
) -> ToolResult:
    if isinstance(record, PageRecord):
        formatted = (
            browser_workflows.format_search_result(record, query)
            if tool_name == "browser_search"
            else browser_workflows.format_page_result(record)
        )
        return ToolResult(
            tool=tool_name,
            query=query,
            success=record.success,
            data={
                "url": record.url,
                "title": record.title,
                "content": record.content,
                "links": list(record.links),
                "word_count": record.word_count,
                "status_code": record.status_code,
                "record": record,
                "comprehension": comprehension or BrowserComprehension(),
                "formatted": formatted,
            },
            error=record.error,
        )

    return ToolResult(
        tool=tool_name,
        query=query,
        success=record.success,
        data={
            "url": record.url,
            "action": record.action,
            "consequential": record.consequential,
            "output": record.output,
            "formatted": record.output or f"browser > error: {record.error or 'Unknown browser error.'}",
        },
        error=record.error,
    )


def run_browser_tool(
    browser_workflows: BrowserWorkflows,
    tool_name: str,
    params: dict[str, Any],
) -> ToolResult:
    if tool_name == "browser_read":
        url = str(params.get("url", "")).strip()
        record, comprehension = browser_workflows.read_page(url, js=bool(params.get("js", False)))
        return build_browser_tool_result(tool_name, record, browser_workflows, url, comprehension)
    if tool_name == "browser_search":
        query = str(params.get("query", "")).strip()
        record, comprehension = browser_workflows.search_web(query)
        return build_browser_tool_result(tool_name, record, browser_workflows, query, comprehension)
    if tool_name == "browser_open":
        url = str(params.get("url", "")).strip()
        browser_name = str(params.get("browser", "firefox") or "firefox").strip().lower()
        result = browser_workflows.open_in_browser(url, browser=browser_name)
        return build_browser_tool_result(tool_name, result, browser_workflows, url)
    return ToolResult(
        tool=tool_name,
        query=str(params.get("url", "") or params.get("query", "")),
        success=False,
        error=f"Unknown browser tool: {tool_name}",
    )


def run_document_tool(
    document_workflows: DocumentWorkflows,
    tool_name: str,
    params: dict[str, Any],
) -> ToolResult:
    if tool_name == "doc_read":
        record, comprehension = document_workflows.read_document(str(params.get("path", "")))
        return build_document_tool_result(tool_name, record, document_workflows, comprehension)
    if tool_name == "doc_write":
        result = document_workflows.write_document(
            str(params.get("path", "")),
            str(params.get("content", "")),
            title=str(params.get("title", "")),
            format=str(params.get("format", "txt") or "txt"),
        )
        return build_document_tool_result(tool_name, result, document_workflows)
    if tool_name == "doc_open":
        path = str(params.get("path", ""))
        success = document_workflows.open_in_libreoffice(path)
        result = DocumentWriteResult(
            success=success,
            path=str(Path(path).expanduser().resolve()) if path else "",
            format=Path(path).suffix.lower().lstrip("."),
            error=None if success else "LibreOffice failed to open document.",
        )
        return build_document_tool_result(tool_name, result, document_workflows)
    if tool_name == "doc_export_pdf":
        result = document_workflows.export_to_pdf(
            str(params.get("path", "")),
            str(params.get("output_dir", "") or "") or None,
        )
        return build_document_tool_result(tool_name, result, document_workflows)
    return ToolResult(
        tool=tool_name,
        query=str(params.get("path", "")),
        success=False,
        error=f"Unknown document tool: {tool_name}",
    )


def build_calendar_tool_result(
    tool_name: str,
    result: CalendarResult,
    calendar_workflows: CalendarWorkflows,
    comprehension: CalendarComprehension,
    query: str,
) -> ToolResult:
    return ToolResult(
        tool=tool_name,
        query=query,
        success=result.success,
        data={
            "source": result.source,
            "events": [event.__dict__.copy() for event in result.events],
            "todos": [todo.__dict__.copy() for todo in result.todos],
            "calendar_result": result,
            "comprehension": comprehension,
            "total_events": comprehension.total_events,
            "period_label": comprehension.period_label,
            "has_remote_calendar": comprehension.has_remote_calendar,
            "today_events": [event.__dict__.copy() for event in comprehension.today_events],
            "upcoming_events": [event.__dict__.copy() for event in comprehension.upcoming_events],
            "overdue_todos": [todo.__dict__.copy() for todo in comprehension.overdue_todos],
            "comprehension_data": {
                "total_events": comprehension.total_events,
                "period_label": comprehension.period_label,
                "source": comprehension.source,
                "has_remote_calendar": comprehension.has_remote_calendar,
                "today_events": [event.__dict__.copy() for event in comprehension.today_events],
                "upcoming_events": [event.__dict__.copy() for event in comprehension.upcoming_events],
                "overdue_todos": [todo.__dict__.copy() for todo in comprehension.overdue_todos],
            },
            "formatted": calendar_workflows.format_result(result, comprehension),
        },
        error=result.error or "",
    )


def run_calendar_tool(
    calendar_workflows: CalendarWorkflows,
    tool_name: str,
    params: dict[str, Any],
) -> ToolResult:
    if tool_name == "calendar_today":
        result, comprehension = calendar_workflows.read_today()
        return build_calendar_tool_result(
            tool_name,
            result,
            calendar_workflows,
            comprehension,
            "today",
        )
    if tool_name == "calendar_upcoming":
        days = max(1, int(params.get("days", 7) or 7))
        result, comprehension = calendar_workflows.read_upcoming(days=days)
        return build_calendar_tool_result(
            tool_name,
            result,
            calendar_workflows,
            comprehension,
            f"next {days} days",
        )
    if tool_name == "calendar_read_ics":
        path = str(params.get("path", "")).strip()
        result, comprehension = calendar_workflows.read_ics_file(path)
        return build_calendar_tool_result(
            tool_name,
            result,
            calendar_workflows,
            comprehension,
            path,
        )
    return ToolResult(
        tool=tool_name,
        query=str(params.get("path", "") or params.get("days", "")),
        success=False,
        error=f"Unknown calendar tool: {tool_name}",
    )


def execute_tool_request(
    tool_name: str,
    params: dict[str, Any],
    operator: OperatorFaculty,
    calendar_workflows: CalendarWorkflows | None = None,
    browser_workflows: BrowserWorkflows | None = None,
    document_workflows: DocumentWorkflows | None = None,
    filesystem_faculty: FileSystemFaculty | None = None,
    process_faculty: ProcessFaculty | None = None,
    package_faculty: PackageFaculty | None = None,
    desktop_faculty: DesktopFaculty | None = None,
    communication_workflows: CommunicationWorkflows | None = None,
    email_workflows: EmailWorkflows | None = None,
    software_registry: SoftwareRegistry | None = None,
) -> ToolResult:
    if tool_name in CALENDAR_TOOL_NAMES:
        workflows = calendar_workflows or CalendarWorkflows()
        return run_calendar_tool(workflows, tool_name, params)
    if tool_name in BROWSER_TOOL_NAMES:
        workflows = browser_workflows or BrowserWorkflows(desktop_faculty or DesktopFaculty())
        return run_browser_tool(workflows, tool_name, params)
    if tool_name in DOCUMENT_TOOL_NAMES:
        workflows = document_workflows or DocumentWorkflows(desktop_faculty or DesktopFaculty())
        return run_document_tool(workflows, tool_name, params)
    if tool_name in FILESYSTEM_TOOL_NAMES:
        return run_filesystem_tool(filesystem_faculty or FileSystemFaculty(), tool_name, params)
    if tool_name in PROCESS_TOOL_NAMES:
        return run_process_tool(process_faculty or ProcessFaculty(), tool_name, params)
    if tool_name in PACKAGE_TOOL_NAMES:
        return run_package_tool(
            package_faculty or PackageFaculty(),
            tool_name,
            params,
            software_registry=software_registry,
        )
    if tool_name in COMMUNICATION_TOOL_NAMES:
        communication_workflows = communication_workflows or CommunicationWorkflows(
            desktop_faculty or DesktopFaculty()
        )
        return run_communication_tool(communication_workflows, tool_name, params)
    if tool_name in EMAIL_TOOL_NAMES:
        email_workflows = email_workflows or EmailWorkflows(desktop_faculty or DesktopFaculty())
        return run_email_tool(email_workflows, tool_name, params)
    if tool_name in DESKTOP_TOOL_NAMES:
        return run_desktop_tool(desktop_faculty or DesktopFaculty(), tool_name, params)
    return operator.execute(tool_name, params)


def build_filesystem_context_lines(result: ToolResult) -> list[str]:
    path = str(result.data.get("path") or result.query)
    if not result.success:
        return [
            f"tool result ({result.tool}) path: {path}",
            f"error: {result.error or 'unknown file system error'}",
        ]

    if result.tool == "read_file":
        content = str(result.data.get("content", ""))
        excerpt = content[:4000]
        lines = [
            f"tool result ({result.tool}) path: {path}",
            f"bytes_read: {result.data.get('bytes_read', 0)}",
            f"truncated: {'yes' if result.data.get('truncated') else 'no'}",
        ]
        if excerpt:
            lines.append(f"content_excerpt: {excerpt}")
        return lines

    if result.tool == "list_dir":
        entries = list(result.data.get("entries", []))
        preview = ", ".join(
            str(item.get("name", ""))
            for item in entries[:20]
            if isinstance(item, dict)
        )
        lines = [
            f"tool result ({result.tool}) path: {path}",
            f"entries: {len(entries)}",
        ]
        if preview:
            lines.append(f"entry_preview: {preview}")
        return lines

    if result.tool == "file_info":
        info = result.data.get("info", {})
        if isinstance(info, dict):
            kind = "directory" if info.get("is_dir") else "file"
            return [
                f"tool result ({result.tool}) path: {path}",
                f"type: {kind}",
                f"size_bytes: {info.get('size_bytes', 0)}",
                f"permissions: {info.get('permissions', 'unknown')}",
            ]

    if result.tool == "search_files":
        entries = list(result.data.get("entries", []))
        preview = ", ".join(
            str(item.get("path", ""))
            for item in entries[:10]
            if isinstance(item, dict)
        )
        lines = [
            f"tool result ({result.tool}) path: {path}",
            f"matches: {len(entries)}",
        ]
        if preview:
            lines.append(f"match_preview: {preview}")
        return lines

    if result.tool == "write_file":
        return [
            f"tool result ({result.tool}) path: {path}",
            f"bytes_written: {result.data.get('bytes_read', 0)}",
        ]

    return [
        f"tool result ({result.tool}) path: {path}",
        str(result.data.get("formatted", "")),
    ]


def build_process_context_lines(result: ToolResult) -> list[str]:
    if not result.success:
        return [
            f"tool result ({result.tool}) query: {result.query}",
            f"error: {result.error or 'unknown process error'}",
        ]

    if result.tool == "list_processes":
        records = list(result.data.get("records", []))
        preview = []
        for item in records[:10]:
            if isinstance(item, dict):
                preview.append(
                    f"{item.get('name', '?')}:{item.get('pid', 0)} "
                    f"cpu={item.get('cpu_percent', 0)} mem={item.get('memory_mb', 0)}"
                )
        lines = [
            f"tool result ({result.tool}) query: {result.query}",
            f"count: {result.data.get('count', len(records))}",
        ]
        if preview:
            lines.append("process_preview: " + "; ".join(preview))
        return lines

    if result.tool == "system_info":
        info = result.data.get("system_info", {})
        if isinstance(info, dict):
            return [
                f"tool result ({result.tool}) host: {info.get('hostname', 'unknown')}",
                f"platform: {info.get('platform', 'unknown')}",
                f"uptime: {info.get('uptime_human', 'unknown')}",
                f"cpu_percent: {info.get('cpu_percent', 0)}",
                f"ram_percent: {info.get('ram_percent', 0)}",
                f"disk_percent: {info.get('disk_percent', 0)}",
            ]

    if result.tool == "kill_process":
        return [
            f"tool result ({result.tool}) pid: {result.query}",
            f"message: {result.data.get('stdout', '') or result.error or 'no output'}",
        ]

    if result.tool == "run_command":
        lines = [
            f"tool result ({result.tool}) command: {result.query}",
            f"returncode: {result.data.get('returncode', 0)}",
        ]
        stdout = str(result.data.get("stdout", "")).strip()
        stderr = str(result.data.get("stderr", "")).strip()
        if stdout:
            lines.append(f"stdout: {stdout[:4000]}")
        if stderr:
            lines.append(f"stderr: {stderr[:1000]}")
        return lines

    return [
        f"tool result ({result.tool}) query: {result.query}",
        str(result.data.get("formatted", "")),
    ]


def build_package_context_lines(result: ToolResult) -> list[str]:
    package_manager = str(result.data.get("package_manager", "") or "unknown")
    if not result.success:
        return [
            f"tool result ({result.tool}) package_manager: {package_manager}",
            f"query: {result.query}",
            f"error: {result.error or 'unknown package error'}",
        ]

    if result.tool in {"search_packages", "list_packages"}:
        records = list(result.data.get("records", []))
        preview = []
        for item in records[:10]:
            if isinstance(item, dict):
                fragment = str(item.get("name", "?"))
                version = str(item.get("version", "")).strip()
                if version:
                    fragment += f" {version}"
                preview.append(fragment)
        lines = [
            f"tool result ({result.tool}) package_manager: {package_manager}",
            f"query: {result.query}",
            f"count: {len(records)}",
        ]
        if preview:
            lines.append("package_preview: " + "; ".join(preview))
        elif result.data.get("output"):
            lines.append(f"output_excerpt: {str(result.data.get('output', ''))[:1000]}")
        return lines

    if result.tool in {"install_package", "remove_package"}:
        lines = [
            f"tool result ({result.tool}) package_manager: {package_manager}",
            f"query: {result.query}",
        ]
        output = str(result.data.get("output", "")).strip()
        if output:
            lines.append(f"output_excerpt: {output[:1000]}")
        return lines

    return [
        f"tool result ({result.tool}) query: {result.query}",
        str(result.data.get("formatted", "")),
    ]


def build_desktop_context_lines(result: ToolResult) -> list[str]:
    if not result.success:
        return [
            f"tool result ({result.tool}) query: {result.query}",
            f"error: {result.error or 'unknown desktop error'}",
        ]

    if result.tool == "desktop_open_app":
        lines = [f"tool result ({result.tool}) app: {result.query}"]
        if result.data.get("window_title"):
            lines.append(f"window_title: {result.data.get('window_title')}")
        if result.data.get("output"):
            lines.append(f"message: {str(result.data.get('output', ''))[:400]}")
        return lines

    if result.tool == "desktop_read_window":
        lines = [f"tool result ({result.tool}) window: {result.query or 'active window'}"]
        if result.data.get("window_title"):
            lines.append(f"title: {result.data.get('window_title')}")
        output = str(result.data.get("output", "")).strip()
        if output:
            lines.append(f"output_excerpt: {output[:4000]}")
        return lines

    if result.tool == "desktop_click":
        return [
            f"tool result ({result.tool}) label: {result.query}",
            f"element_found: {'yes' if result.data.get('element_found') else 'no'}",
            f"consequential: {'yes' if result.data.get('consequential') else 'no'}",
        ]

    if result.tool == "desktop_type":
        return [
            f"tool result ({result.tool}) text: {str(result.query)[:120]}",
            f"chars_typed: {len(str(result.query or ''))}",
            f"submitted: {'yes' if result.data.get('consequential') else 'no'}",
        ]

    if result.tool == "desktop_screenshot":
        lines = [f"tool result ({result.tool}) target: {result.query or 'desktop'}"]
        if result.data.get("screenshot_path"):
            lines.append(f"screenshot_path: {result.data.get('screenshot_path')}")
        return lines

    return [
        f"tool result ({result.tool}) query: {result.query}",
        str(result.data.get("formatted", "")),
    ]


def build_communication_context_lines(result: ToolResult) -> list[str]:
    if not result.success:
        return [
            f"tool result ({result.tool}) query: {result.query}",
            f"error: {result.error or 'unknown communication error'}",
        ]

    workflow = str(result.data.get("workflow", "") or result.tool)
    app = str(result.data.get("app", "") or result.query)
    if workflow == "read_messages":
        messages = list(result.data.get("messages", []))
        lines = [
            f"tool result ({result.tool}) app: {app}",
            f"visible_items: {len(messages)}",
        ]
        for record in messages[:10]:
            if isinstance(record, dict):
                preview = str(record.get("content", "")).strip()
                if preview:
                    lines.append(f"message_excerpt: {preview[:200]}")
        output = str(result.data.get("output", "")).strip()
        if not messages and output:
            lines.append(f"window_excerpt: {output[:4000]}")
        return lines

    if workflow == "list_contacts":
        lines = [f"tool result ({result.tool}) app: {app}"]
        output = str(result.data.get("output", "")).strip()
        if output:
            lines.append(f"contacts_excerpt: {output[:4000]}")
        return lines

    if workflow == "send_message":
        return [
            f"tool result ({result.tool}) app: {app}",
            f"contact: {result.data.get('contact', '')}",
            f"draft_visible: {'yes' if result.data.get('draft_visible') else 'no'}",
            f"draft_text: {str(result.data.get('message', ''))[:400]}",
        ]

    if workflow == "execute_send":
        return [
            f"tool result ({result.tool}) app: {app}",
            f"contact: {result.data.get('contact', '')}",
            f"sent: {'yes' if result.success else 'no'}",
            f"message: {str(result.data.get('message', ''))[:400]}",
        ]

    return [
        f"tool result ({result.tool}) query: {result.query}",
        str(result.data.get("formatted", "")),
    ]


def build_email_context_lines(result: ToolResult) -> list[str]:
    if not result.success:
        return [
            f"tool result ({result.tool}) query: {result.query}",
            f"error: {result.error or 'unknown email error'}",
        ]

    workflow = str(result.data.get("workflow", "") or result.tool)
    app = str(result.data.get("app", "") or result.query)
    if workflow == "read_inbox":
        emails = list(result.data.get("emails", []))
        lines = [
            f"tool result ({result.tool}) app: {app}",
            f"visible_items: {len(emails)}",
        ]
        for record in emails[:10]:
            if isinstance(record, dict):
                subject = str(record.get("subject", "")).strip()
                if subject:
                    lines.append(f"email_subject: {subject[:200]}")
        output = str(result.data.get("output", "")).strip()
        if not emails and output:
            lines.append(f"window_excerpt: {output[:4000]}")
        return lines

    if workflow in {"read_email", "search"}:
        lines = [f"tool result ({result.tool}) app: {app}"]
        output = str(result.data.get("output", "")).strip()
        if output:
            lines.append(f"email_excerpt: {output[:4000]}")
        emails = list(result.data.get("emails", []))
        if emails:
            lines.append(f"matches: {len(emails)}")
        return lines

    if workflow in {"compose_draft", "reply"}:
        return [
            f"tool result ({result.tool}) app: {app}",
            f"recipient: {result.data.get('recipient', '')}",
            f"subject: {result.data.get('subject', '')}",
            f"reply_target: {result.data.get('subject_or_sender', '')}",
            f"draft_visible: {'yes' if result.data.get('draft_visible') else 'no'}",
            f"draft_body: {str(result.data.get('body', ''))[:400]}",
        ]

    if workflow == "execute_send":
        return [
            f"tool result ({result.tool}) app: {app}",
            f"recipient: {result.data.get('recipient', '')}",
            f"subject: {result.data.get('subject', '')}",
            f"reply_target: {result.data.get('subject_or_sender', '')}",
            f"sent: {'yes' if result.success else 'no'}",
        ]

    return [
        f"tool result ({result.tool}) query: {result.query}",
        str(result.data.get("formatted", "")),
    ]


def build_document_context_lines(result: ToolResult) -> list[str]:
    path = str(result.data.get("path") or result.query)
    if not result.success:
        return [
            f"tool result ({result.tool}) path: {path}",
            f"error: {result.error or 'unknown document error'}",
        ]

    if result.tool == "doc_read":
        comprehension = result.data.get("comprehension", {})
        if not isinstance(comprehension, dict):
            comprehension = {}
        lines = [
            f"tool result ({result.tool}) path: {path}",
            f"title: {result.data.get('title', '') or Path(path).stem}",
            f"format: {result.data.get('format', 'unknown')}",
            f"word_count: {result.data.get('word_count', 0)}",
            f"page_count: {result.data.get('page_count', 0)}",
        ]
        summary_lines = list(comprehension.get("summary_lines", []))
        key_points = list(comprehension.get("key_points", []))
        if summary_lines:
            lines.append("summary: " + " | ".join(str(line) for line in summary_lines[:3]))
        if key_points:
            lines.append("key_points: " + " | ".join(str(point) for point in key_points[:5]))
        content = str(result.data.get("content", "")).strip()
        if content:
            lines.append(f"content_excerpt: {content[:4000]}")
        return lines

    return [
        f"tool result ({result.tool}) path: {path}",
        f"format: {result.data.get('format', 'unknown')}",
        f"message: {str(result.data.get('formatted', '')).strip()[:1000]}",
    ]


def build_calendar_context_lines(result: ToolResult) -> list[str]:
    query = str(result.query).strip()
    source = str(result.data.get("source", "") or "calendar")
    if not result.success:
        return [
            f"tool result ({result.tool}) source: {source}",
            f"query: {query}",
            f"error: {result.error or 'unknown calendar error'}",
        ]

    lines = [
        f"tool result ({result.tool}) source: {source}",
        f"query: {query}",
        f"total_events: {result.data.get('total_events', 0)}",
        f"period_label: {result.data.get('period_label', '')}",
        f"has_remote_calendar: {'yes' if result.data.get('has_remote_calendar') else 'no'}",
    ]
    formatted = str(result.data.get("formatted", "")).strip()
    if formatted:
        lines.append(f"calendar_context: {formatted[:4000]}")
    return lines


def build_browser_context_lines(result: ToolResult) -> list[str]:
    url = str(result.data.get("url") or result.query)
    if not result.success:
        return [
            f"tool result ({result.tool}) url: {url}",
            f"error: {result.error or 'unknown browser error'}",
        ]

    if result.tool in {"browser_read", "browser_search"}:
        lines = [
            f"tool result ({result.tool}) url: {url}",
            f"title: {result.data.get('title', '')}",
            f"word_count: {result.data.get('word_count', 0)}",
            f"status_code: {result.data.get('status_code', 0)}",
        ]
        content = str(result.data.get("content", "")).strip()
        if content:
            lines.append(f"content_excerpt: {content[:4000]}")
        return lines

    return [
        f"tool result ({result.tool}) url: {url}",
        f"action: {result.data.get('action', 'navigate')}",
        f"message: {str(result.data.get('formatted', '')).strip()[:1000]}",
    ]


def communication_result_requires_send_confirmation(result: ToolResult) -> bool:
    return bool(
        result.tool == "comm_send_message"
        and result.success
        and result.data.get("draft_visible")
        and str(result.data.get("mode", "draft")).strip().lower() != "execute_send"
    )


def email_result_requires_send_confirmation(result: ToolResult) -> bool:
    return bool(
        result.tool in {"email_compose", "email_reply"}
        and result.success
        and result.data.get("draft_visible")
        and str(result.data.get("mode", "draft")).strip().lower() != "execute_send"
    )


def build_tool_result_text(result: ToolResult) -> str:
    if result.tool in CALENDAR_TOOL_NAMES:
        return str(
            result.data.get("formatted")
            or f"calendar > error: {result.error or 'Unknown calendar error.'}"
        )

    if result.tool in BROWSER_TOOL_NAMES:
        return str(
            result.data.get("formatted")
            or f"browser > error: {result.error or 'Unknown browser error.'}"
        )

    if result.tool in DOCUMENT_TOOL_NAMES:
        return str(
            result.data.get("formatted")
            or f"doc > error: {result.error or 'Unknown document error.'}"
        )

    if result.tool in EMAIL_TOOL_NAMES:
        return str(
            result.data.get("formatted")
            or f"email > error: {result.error or 'Unknown email error.'}"
        )

    if result.tool in COMMUNICATION_TOOL_NAMES:
        return str(
            result.data.get("formatted")
            or f"comm > error: {result.error or 'Unknown communication error.'}"
        )

    if result.tool in DESKTOP_TOOL_NAMES:
        return str(
            result.data.get("formatted")
            or f"desktop > error: {result.error or 'Unknown desktop error.'}"
        )

    if result.tool in PACKAGE_TOOL_NAMES:
        return str(
            result.data.get("formatted")
            or f"pkg > error: {result.error or 'Unknown package error.'}"
        )

    if result.tool in PROCESS_TOOL_NAMES:
        return str(
            result.data.get("formatted")
            or f"proc > error: {result.error or 'Unknown process error.'}"
        )

    if result.tool in FILESYSTEM_TOOL_NAMES:
        return str(
            result.data.get("formatted")
            or f"fs > error: {result.error or 'Unknown file system error.'}"
        )

    if result.tool == "ping":
        lines = ["ping result:"]
        if not result.success:
            lines.append(f"  Error: {result.error}")
            return "\n".join(lines)
        lines.append(f"  Host: {result.data.get('host', result.query) or 'unknown'}")
        lines.append(
            "  Reachable: "
            + ("yes" if result.data.get("reachable") else "no")
        )
        latency = result.data.get("latency_ms")
        lines.append(
            f"  Latency: {latency} ms" if latency is not None else "  Latency: unknown"
        )
        output = str(result.data.get("output", "")).strip()
        if output:
            lines.append(f"  Output: {output[:160]}")
        return "\n".join(lines)

    if result.tool == "resolve_host":
        lines = ["resolve result:"]
        if not result.success:
            lines.append(f"  Error: {result.error}")
            return "\n".join(lines)
        lines.append(f"  Host: {result.data.get('host', result.query) or 'unknown'}")
        lines.append(f"  IP: {result.data.get('ip', 'unknown')}")
        lines.append(f"  FQDN: {result.data.get('fqdn', 'unknown')}")
        return "\n".join(lines)

    if result.tool == "scan_ports":
        lines = ["port scan result:"]
        if not result.success:
            lines.append(f"  Error: {result.error}")
            return "\n".join(lines)
        open_ports = result.data.get("open_ports", [])
        ports_text = ", ".join(str(port) for port in open_ports) if open_ports else "none"
        lines.append(f"  Host: {result.data.get('host', 'unknown')}")
        lines.append(f"  Range: {result.data.get('port_range', 'unknown')}")
        lines.append(f"  Scanned: {result.data.get('scanned', 0)}")
        lines.append(f"  Open ports: {ports_text}")
        return "\n".join(lines)

    lines = ["search result:"]
    if not result.success:
        lines.append(f"  Error: {result.error}")
        return "\n".join(lines)

    abstract = result.data.get("abstract", "")
    answer = result.data.get("answer", "")
    related = result.data.get("related", [])
    lines.append(f"  Abstract: {abstract or 'none'}")
    lines.append(f"  Answer: {answer or 'none'}")
    if related:
        lines.append(f"  Related: {related[0].get('text', '') or 'none'}")
    return "\n".join(lines)


def build_tool_context_lines(result: ToolResult) -> list[str]:
    if result.tool in CALENDAR_TOOL_NAMES:
        return build_calendar_context_lines(result)

    if result.tool in BROWSER_TOOL_NAMES:
        return build_browser_context_lines(result)

    if result.tool in DOCUMENT_TOOL_NAMES:
        return build_document_context_lines(result)

    if result.tool in EMAIL_TOOL_NAMES:
        return build_email_context_lines(result)

    if result.tool in COMMUNICATION_TOOL_NAMES:
        return build_communication_context_lines(result)

    if result.tool in DESKTOP_TOOL_NAMES:
        return build_desktop_context_lines(result)

    if result.tool in PACKAGE_TOOL_NAMES:
        return build_package_context_lines(result)

    if result.tool in PROCESS_TOOL_NAMES:
        return build_process_context_lines(result)

    if result.tool in FILESYSTEM_TOOL_NAMES:
        return build_filesystem_context_lines(result)

    if result.tool == "ping":
        if result.success:
            latency = result.data.get("latency_ms")
            lines = [
                f"tool result ({result.tool}) host: {result.data.get('host', result.query) or result.query}",
                f"reachable: {'yes' if result.data.get('reachable') else 'no'}",
            ]
            if latency is not None:
                lines.append(f"latency_ms: {latency}")
            return lines
        return [
            f"tool result ({result.tool}) host: {result.query}",
            f"error: {result.error or 'unknown tool error'}",
        ]

    if result.tool == "resolve_host":
        if result.success:
            return [
                f"tool result ({result.tool}) host: {result.data.get('host', result.query) or result.query}",
                f"ip: {result.data.get('ip', 'unknown')}",
                f"fqdn: {result.data.get('fqdn', 'unknown')}",
            ]
        return [
            f"tool result ({result.tool}) host: {result.query}",
            f"error: {result.error or 'unknown tool error'}",
        ]

    if result.tool == "scan_ports":
        if result.success:
            open_ports = result.data.get("open_ports", [])
            ports_text = ", ".join(str(port) for port in open_ports) if open_ports else "none"
            return [
                f"tool result ({result.tool}) host: {result.data.get('host', result.query) or result.query}",
                f"port_range: {result.data.get('port_range', 'unknown')}",
                f"open_ports: {ports_text}",
            ]
        return [
            f"tool result ({result.tool}) query: {result.query}",
            f"error: {result.error or 'unknown tool error'}",
        ]

    if result.success:
        related = result.data.get("related", [])
        related_text = related[0].get("text", "") if related else ""
        lines = [
            f"tool result ({result.tool}) query: {result.query}",
            f"abstract: {result.data.get('abstract', '') or 'none'}",
            f"answer: {result.data.get('answer', '') or 'none'}",
        ]
        if related_text:
            lines.append(f"related: {related_text}")
        return lines
    return [
        f"tool result ({result.tool}) query: {result.query}",
        f"error: {result.error or 'unknown tool error'}",
    ]


def build_tool_registry_payload(operator: OperatorFaculty) -> dict[str, object]:
    tools = operator.list_tools()
    return {
        "type": "tool_registry",
        "tools": tools,
        "total": len(tools),
    }


def build_faculty_registry_payload(faculty_monitor: FacultyMonitor) -> dict[str, object]:
    faculties = faculty_monitor.registry_summary()
    active = sum(1 for faculty in faculties if bool(faculty.get("active", False)))
    return {
        "type": "faculty_registry",
        "faculties": faculties,
        "total": len(faculties),
        "active": active,
        "inactive": len(faculties) - active,
    }


def build_tool_result_payload(result: ToolResult) -> dict[str, object]:
    def _serialize(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, Path):
            return str(value)
        if is_dataclass(value):
            return {key: _serialize(item) for key, item in asdict(value).items()}
        if isinstance(value, dict):
            return {str(key): _serialize(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [_serialize(item) for item in value]
        return value

    return {
        "tool": result.tool,
        "query": result.query,
        "success": result.success,
        "data": _serialize(dict(result.data)),
        "error": result.error,
    }


NETWORK_TOOL_NAMES = {"ping", "resolve_host", "scan_ports"}


def build_network_audit_entry(result: ToolResult) -> dict[str, object] | None:
    if result.tool not in NETWORK_TOOL_NAMES:
        return None

    host = str(result.data.get("host") or result.query.split(":", 1)[0] or result.query).strip()
    result_text = result.error or "unknown"
    details: dict[str, object] = {
        "tool": result.tool,
        "host": host,
    }

    if result.tool == "ping":
        result_text = "reachable" if result.data.get("reachable") else "unreachable"
        details["reachable"] = bool(result.data.get("reachable"))
        if result.data.get("latency_ms") is not None:
            details["latency_ms"] = result.data.get("latency_ms")
    elif result.tool == "resolve_host":
        result_text = str(result.data.get("ip") or result.error or "unresolved")
        if result.success:
            details["ip"] = str(result.data.get("ip", ""))
            details["fqdn"] = str(result.data.get("fqdn", ""))
    elif result.tool == "scan_ports":
        open_ports = list(result.data.get("open_ports", []))
        result_text = ", ".join(str(port) for port in open_ports) if open_ports else "none"
        details["port_range"] = str(result.data.get("port_range", ""))
        details["open_ports"] = open_ports
        details["scanned"] = int(result.data.get("scanned", 0))

    details["result"] = result_text
    details["summary"] = f"{result.tool} {host} -> {result_text}"
    return details


def build_filesystem_audit_entry(result: ToolResult) -> dict[str, object] | None:
    if result.tool not in FILESYSTEM_TOOL_NAMES:
        return None

    path = str(result.data.get("path") or result.query).strip()
    result_text = result.error or "unknown"
    details: dict[str, object] = {
        "tool": result.tool,
        "path": path,
    }

    if result.tool == "read_file":
        result_text = f"read {result.data.get('bytes_read', 0)} bytes"
        details["bytes_read"] = int(result.data.get("bytes_read", 0))
        details["truncated"] = bool(result.data.get("truncated", False))
    elif result.tool == "list_dir":
        entries = list(result.data.get("entries", []))
        result_text = f"{len(entries)} entries"
        details["entries"] = len(entries)
    elif result.tool == "file_info":
        info = result.data.get("info", {})
        if isinstance(info, dict):
            kind = "directory" if info.get("is_dir") else "file"
            result_text = f"{info.get('size_human', 'unknown')} {kind}"
            details["size_bytes"] = int(info.get("size_bytes", 0))
    elif result.tool == "search_files":
        entries = list(result.data.get("entries", []))
        result_text = f"{len(entries)} matches"
        details["matches"] = len(entries)
    elif result.tool == "write_file":
        result_text = f"wrote {result.data.get('bytes_read', 0)} bytes"
        details["bytes_written"] = int(result.data.get("bytes_read", 0))

    details["result"] = result_text
    details["summary"] = f"{result.tool} {path} -> {result_text}"
    return details


def build_calendar_audit_entry(result: ToolResult) -> dict[str, object] | None:
    if result.tool not in CALENDAR_TOOL_NAMES:
        return None

    query = str(result.query).strip()
    source = str(result.data.get("source", "") or "calendar")
    details: dict[str, object] = {
        "tool": result.tool,
        "query": query,
        "source": source,
    }
    if not result.success:
        result_text = result.error or "failed"
    else:
        result_text = f"{int(result.data.get('total_events', 0))} events"
        details["period_label"] = str(result.data.get("period_label", ""))
        details["total_events"] = int(result.data.get("total_events", 0))
        details["has_remote_calendar"] = bool(result.data.get("has_remote_calendar", False))
    details["result"] = result_text
    details["summary"] = f"{result.tool} {query or source} -> {result_text}"
    return details


def build_document_audit_entry(result: ToolResult) -> dict[str, object] | None:
    if result.tool not in DOCUMENT_TOOL_NAMES:
        return None

    path = str(result.data.get("path") or result.query).strip()
    details: dict[str, object] = {
        "tool": result.tool,
        "path": path,
        "format": str(result.data.get("format", "") or "unknown"),
    }
    if not result.success:
        result_text = result.error or "failed"
    elif result.tool == "doc_read":
        result_text = (
            f"{int(result.data.get('word_count', 0))} words"
            + (
                f", {int(result.data.get('page_count', 0))} pages"
                if int(result.data.get("page_count", 0))
                else ""
            )
        )
        details["word_count"] = int(result.data.get("word_count", 0))
        details["page_count"] = int(result.data.get("page_count", 0))
    elif result.tool == "doc_write":
        result_text = f"wrote {int(result.data.get('word_count', 0))} words"
        details["word_count"] = int(result.data.get("word_count", 0))
    elif result.tool == "doc_open":
        result_text = "opened in LibreOffice"
    else:
        result_text = "exported to pdf"

    details["result"] = result_text
    details["summary"] = f"{result.tool} {path} -> {result_text}"
    return details


def build_browser_audit_entry(result: ToolResult) -> dict[str, object] | None:
    if result.tool not in BROWSER_TOOL_NAMES:
        return None

    url = str(result.data.get("url") or result.query).strip()
    details: dict[str, object] = {
        "tool": result.tool,
        "url": url,
    }
    if not result.success:
        result_text = result.error or "failed"
    elif result.tool == "browser_open":
        result_text = "opened in browser"
        details["action"] = str(result.data.get("action", "navigate"))
    else:
        result_text = f"{int(result.data.get('word_count', 0))} words"
        details["title"] = str(result.data.get("title", ""))
        details["status_code"] = int(result.data.get("status_code", 0))
        details["word_count"] = int(result.data.get("word_count", 0))

    details["result"] = result_text
    details["summary"] = f"{result.tool} {url} -> {result_text}"
    return details


def build_process_audit_entry(result: ToolResult) -> dict[str, object] | None:
    if result.tool not in PROCESS_TOOL_NAMES:
        return None

    query = str(result.query).strip()
    result_text = result.error or "unknown"
    details: dict[str, object] = {
        "tool": result.tool,
        "query": query,
    }

    if result.tool == "list_processes":
        result_text = f"{int(result.data.get('count', 0))} processes"
        details["count"] = int(result.data.get("count", 0))
    elif result.tool == "system_info":
        info = result.data.get("system_info", {})
        if isinstance(info, dict):
            result_text = (
                f"cpu {info.get('cpu_percent', 0)}% "
                f"ram {info.get('ram_percent', 0)}% "
                f"disk {info.get('disk_percent', 0)}%"
            )
            details["hostname"] = str(info.get("hostname", ""))
    elif result.tool == "kill_process":
        result_text = str(result.data.get("stdout") or result.error or "terminated")
    elif result.tool == "run_command":
        result_text = f"exit {result.data.get('returncode', result.error or 'unknown')}"
        details["returncode"] = result.data.get("returncode")

    details["result"] = result_text
    details["summary"] = f"{result.tool} {query} -> {result_text}"
    return details


def build_package_audit_entry(result: ToolResult) -> dict[str, object] | None:
    if result.tool not in PACKAGE_TOOL_NAMES:
        return None

    query = str(result.query).strip()
    package_manager = str(result.data.get("package_manager", "") or "unknown")
    result_text = result.error or "unknown"
    details: dict[str, object] = {
        "tool": result.tool,
        "query": query,
        "package_manager": package_manager,
    }

    if not result.success:
        result_text = result.error or "failed"
    elif result.tool in {"search_packages", "list_packages"}:
        records = list(result.data.get("records", []))
        result_text = f"{len(records)} packages"
        details["count"] = len(records)
    elif result.tool == "install_package":
        result_text = f"installed via {package_manager}"
    elif result.tool == "remove_package":
        result_text = f"removed via {package_manager}"

    details["result"] = result_text
    details["summary"] = f"{result.tool} {query} -> {result_text}"
    return details


def build_desktop_audit_entry(result: ToolResult) -> dict[str, object] | None:
    if result.tool not in DESKTOP_TOOL_NAMES:
        return None

    query = str(result.query).strip() or "desktop"
    result_text = result.error or "unknown"
    details: dict[str, object] = {
        "tool": result.tool,
        "query": query,
        "backend": str(result.data.get("backend", "") or "unknown"),
    }

    if not result.success:
        result_text = result.error or "failed"
    elif result.tool == "desktop_open_app":
        result_text = str(result.data.get("window_title") or result.data.get("output") or "opened")
        if result.data.get("window_title"):
            details["window_title"] = str(result.data.get("window_title", ""))
    elif result.tool == "desktop_read_window":
        output = str(result.data.get("output", ""))
        result_text = f"{len(output.splitlines())} lines"
        if result.data.get("window_title"):
            details["window_title"] = str(result.data.get("window_title", ""))
    elif result.tool == "desktop_click":
        result_text = "clicked"
        details["element_found"] = bool(result.data.get("element_found", False))
        details["consequential"] = bool(result.data.get("consequential", False))
    elif result.tool == "desktop_type":
        result_text = f"typed {len(query)} chars"
        details["consequential"] = bool(result.data.get("consequential", False))
    elif result.tool == "desktop_screenshot":
        result_text = str(result.data.get("screenshot_path") or "captured")
        details["screenshot_path"] = str(result.data.get("screenshot_path", ""))

    details["result"] = result_text
    details["summary"] = f"{result.tool} {query} -> {result_text}"
    return details


def build_communication_audit_entry(result: ToolResult) -> dict[str, object] | None:
    if result.tool not in COMMUNICATION_TOOL_NAMES:
        return None

    app = str(result.data.get("app") or result.query).strip()
    contact = str(result.data.get("contact") or "").strip()
    details: dict[str, object] = {
        "tool": result.tool,
        "app": app,
    }
    if contact:
        details["contact"] = contact
    if result.data.get("message"):
        details["message_preview"] = str(result.data.get("message", ""))[:200]
    if result.data.get("steps_completed"):
        details["steps_completed"] = list(result.data.get("steps_completed", []))

    if not result.success:
        result_text = result.error or "failed"
    elif communication_result_requires_send_confirmation(result):
        result_text = "draft ready"
    elif str(result.data.get("workflow", "")) == "execute_send":
        result_text = "sent"
    elif result.tool == "comm_list_contacts":
        result_text = "contacts listed"
    else:
        result_text = f"{len(list(result.data.get('messages', [])))} items visible"

    details["result"] = result_text
    details["summary"] = f"{result.tool} {app}{f'/{contact}' if contact else ''} -> {result_text}"
    return details


def build_email_audit_entry(result: ToolResult) -> dict[str, object] | None:
    if result.tool not in EMAIL_TOOL_NAMES:
        return None

    app = str(result.data.get("app") or result.query).strip()
    recipient = str(result.data.get("recipient") or "").strip()
    subject = str(result.data.get("subject") or "").strip()
    reply_target = str(result.data.get("subject_or_sender") or "").strip()
    details: dict[str, object] = {
        "tool": result.tool,
        "app": app,
    }
    if recipient:
        details["recipient"] = recipient
    if subject:
        details["subject"] = subject[:200]
    if reply_target:
        details["reply_target"] = reply_target
    if result.data.get("steps_completed"):
        details["steps_completed"] = list(result.data.get("steps_completed", []))

    if not result.success:
        result_text = result.error or "failed"
    elif email_result_requires_send_confirmation(result):
        result_text = "draft ready"
    elif str(result.data.get("workflow", "")) == "execute_send":
        result_text = "sent"
    elif result.tool == "email_search":
        result_text = f"{len(list(result.data.get('emails', [])))} matches"
    elif result.tool == "email_read_inbox":
        result_text = f"{len(list(result.data.get('emails', [])))} items visible"
    else:
        result_text = "read"

    details["result"] = result_text
    details["summary"] = (
        f"{result.tool} {app}"
        f"{f'/{recipient}' if recipient else ''}"
        f"{f'/{reply_target}' if reply_target else ''}"
        f" -> {result_text}"
    )
    return details


def build_tool_registry_report(payload: dict[str, object]) -> str:
    tools = list(payload.get("tools", []))
    total = int(payload.get("total", len(tools)))
    lines = [f"tool-registry > Registered tools ({total} total):"]
    current_category = ""
    for tool in tools:
        category = str(tool.get("category", "general")).strip() or "general"
        if category != current_category:
            current_category = category
            lines.extend(["", category.upper()])
        lines.append(
            f"  {tool.get('display_name', tool.get('name', 'tool'))} "
            f"[{'enabled' if tool.get('enabled', False) else 'disabled'}]"
        )
        lines.append(f"    {tool.get('description', '')}")
        lines.append(
            "    Requires: "
            + ("approval" if tool.get("requires_approval", False) else "none")
            + f"  Privilege: {tool.get('requires_privilege', '') or 'none'}"
        )
    if total == 0:
        lines.append("  No registered tools.")
    return "\n".join(lines)


def build_faculty_registry_report(payload: dict[str, object]) -> str:
    faculties = list(payload.get("faculties", []))
    total = int(payload.get("total", len(faculties)))
    active = int(payload.get("active", 0))
    inactive = int(payload.get("inactive", max(total - active, 0)))
    lines = [
        f"faculty-registry > Faculties ({total} total):",
        f"  active: {active}  inactive: {inactive}",
    ]
    for faculty in faculties:
        label = "inactive" if not bool(faculty.get("active", False)) else str(
            faculty.get("mode", "unknown")
        )
        lines.append(
            f"  {faculty.get('display_name', faculty.get('name', 'FACULTY'))} "
            f"[{label}]"
        )
        lines.append(
            f"    {faculty.get('domain', 'general')} · {faculty.get('description', '')}"
        )
        lines.append(
            f"    calls: {faculty.get('call_count', 0)}  "
            f"last: {faculty.get('last_called_at', 'never') or 'never'}"
        )
        if faculty.get("charter_preview"):
            lines.append(f"    charter: {faculty.get('charter_preview', '')}")
    return "\n".join(lines)


def build_network_status_payload(
    session_audit: list[dict[str, object]] | None,
) -> dict[str, object]:
    events = list(session_audit or [])
    filtered = [
        event
        for event in events
        if event.get("event_type") == "tool_use"
        and str(event.get("tool", "")) in NETWORK_TOOL_NAMES
    ]
    recent = []
    for event in reversed(filtered[-20:]):
        recent.append(
            {
                "tool": str(event.get("tool", "")),
                "host": str(event.get("host", "")),
                "result": str(event.get("result", "")),
                "ts": str(event.get("timestamp", "")),
                "port_range": str(event.get("port_range", "")),
                "ip": str(event.get("ip", "")),
                "fqdn": str(event.get("fqdn", "")),
                "open_ports": list(event.get("open_ports", [])),
                "latency_ms": event.get("latency_ms"),
                "reachable": event.get("reachable"),
            }
        )
    return {
        "type": "network_status",
        "recent_scans": recent,
        "total_scans": len(filtered),
    }


def build_network_status_report(payload: dict[str, object]) -> str:
    recent = list(payload.get("recent_scans", []))
    total = int(payload.get("total_scans", len(recent)))
    lines = [f"network-status > Recent network activity ({total} total):"]
    if not recent:
        lines.append("  No network activity recorded yet.")
        return "\n".join(lines)
    for event in recent:
        lines.append(
            f"  [{event.get('tool', '')}] "
            f"{event.get('host', '')} -> {event.get('result', '')} "
            f"@ {event.get('ts', '')}"
        )
    return "\n".join(lines)


def complete_tool_resolution(
    resolved: dict,
    decision: str,
    session: Session,
    proposal: Proposal,
    memory: Memory,
    engine: Engine,
    startup_context: dict,
    operator: OperatorFaculty,
    guardian_metrics: dict[str, int],
    active_token: SessionToken | None = None,
    user_log: UserLog | None = None,
    faculty_monitor: FacultyMonitor | None = None,
    calendar_workflows: CalendarWorkflows | None = None,
    browser_workflows: BrowserWorkflows | None = None,
    document_workflows: DocumentWorkflows | None = None,
    filesystem_faculty: FileSystemFaculty | None = None,
    process_faculty: ProcessFaculty | None = None,
    package_faculty: PackageFaculty | None = None,
    desktop_faculty: DesktopFaculty | None = None,
    communication_workflows: CommunicationWorkflows | None = None,
    email_workflows: EmailWorkflows | None = None,
    session_audit: list[dict[str, object]] | None = None,
    active_realm_name: str = "",
    conversation_state: dict[str, int] | None = None,
    reflective_memory: ReflectiveMemory | None = None,
    nammu_dir: Path | None = None,
    nammu_profile: OperatorProfile | None = None,
) -> str:
    payload = resolved["payload"]
    original_input = payload.get("original_input", "")
    query = payload.get("query", "")
    tool = payload.get("tool", "")
    params = payload.get("params", {})
    if not isinstance(params, dict):
        params = {}
    if "query" not in params and query:
        params["query"] = query

    session.add_event("user", original_input)

    if decision == "approve":
        guardian_metrics["tool_executions"] += 1
        t0 = time.monotonic()
        result = execute_tool_request(
            tool,
            params,
            operator,
            calendar_workflows=calendar_workflows,
            browser_workflows=browser_workflows,
            document_workflows=document_workflows,
            filesystem_faculty=filesystem_faculty,
            process_faculty=process_faculty,
            package_faculty=package_faculty,
            desktop_faculty=desktop_faculty,
            communication_workflows=communication_workflows,
            email_workflows=email_workflows,
        )
        nammu_profile = update_nammu_profile_after_tool(
            nammu_profile,
            nammu_dir,
            str(original_input),
            str(result.tool),
        )
        if faculty_monitor is not None:
            faculty_monitor.record_call("operator", (time.monotonic() - t0) * 1000, result.success)
        audit_entry = (
            build_network_audit_entry(result)
            or build_calendar_audit_entry(result)
            or build_browser_audit_entry(result)
            or build_document_audit_entry(result)
            or build_filesystem_audit_entry(result)
            or build_process_audit_entry(result)
            or build_package_audit_entry(result)
            or build_email_audit_entry(result)
            or build_communication_audit_entry(result)
            or build_desktop_audit_entry(result)
        )
        if audit_entry is not None:
            append_audit_event(
                session_audit,
                "tool_use",
                str(audit_entry["summary"]),
                {key: value for key, value in audit_entry.items() if key != "summary"},
            )
        operator_text = build_tool_result_text(result)
        if email_result_requires_send_confirmation(result):
            created = create_email_send_proposal(
                proposal=proposal,
                session=session,
                user_input=(
                    f"send confirmation for {result.data.get('recipient', '') or result.data.get('subject_or_sender', 'email')} "
                    f"on {display_email_app_name(str(result.data.get('app', '')))}"
                ),
                app=str(result.data.get("app", "")),
                recipient=str(result.data.get("recipient", "")),
                subject=str(result.data.get("subject", "")),
                body=str(result.data.get("body", "")),
                subject_or_sender=str(result.data.get("subject_or_sender", "")),
                stage="execute_send",
                workflow=result.tool,
            )
            record_completed_turn(
                conversation_state=conversation_state,
                memory=memory,
                session=session,
                active_realm_name=active_realm_name,
                active_token=active_token,
                user_log=user_log,
                session_audit=session_audit,
            )
            return (
                f"operator > {operator_text}\n"
                "operator > send approval required.\n"
                f"{created['prompt_text']}\n"
                'Type "approve" to send or "reject" to leave the draft unsent.\n'
                f"{created['tool_line']}"
            )
        if communication_result_requires_send_confirmation(result):
            created = create_communication_send_proposal(
                proposal=proposal,
                session=session,
                user_input=(
                    f"send confirmation for {result.data.get('contact', 'contact')} "
                    f"on {display_communication_app_name(str(result.data.get('app', '')))}"
                ),
                app=str(result.data.get("app", "")),
                contact=str(result.data.get("contact", "")),
                message=str(result.data.get("message", "")),
                stage="execute_send",
            )
            record_completed_turn(
                conversation_state=conversation_state,
                memory=memory,
                session=session,
                active_realm_name=active_realm_name,
                active_token=active_token,
                user_log=user_log,
                session_audit=session_audit,
            )
            return (
                f"operator > {operator_text}\n"
                "operator > send approval required.\n"
                f"{created['prompt_text']}\n"
                'Type "approve" to send or "reject" to leave the draft unsent.\n'
                f"{created['tool_line']}"
            )
        model_connected = engine._connected
        t0 = time.monotonic()
        assistant_text = engine.respond(
            context_summary=startup_context_items(startup_context)
            + build_tool_context_lines(result),
            conversation=session.events,
        )
        if faculty_monitor is not None:
            faculty_monitor.record_call("crown", (time.monotonic() - t0) * 1000, True)
        if result.success and model_connected and engine.mode == "fallback":
            record_completed_turn(
                conversation_state=conversation_state,
                memory=memory,
                session=session,
                active_realm_name=active_realm_name,
                active_token=active_token,
                user_log=user_log,
                session_audit=session_audit,
            )
            return (
                f"operator > {operator_text}\n"
                "operator > model unavailable to summarize. Raw results shown above."
            )
    else:
        if tool in {"email_compose", "email_reply"}:
            mode = str(params.get("mode", "draft") or "draft").strip().lower()
            record_completed_turn(
                conversation_state=conversation_state,
                memory=memory,
                session=session,
                active_realm_name=active_realm_name,
                active_token=active_token,
                user_log=user_log,
                session_audit=session_audit,
            )
            if mode == "execute_send":
                return "operator > send cancelled. The drafted email remains unsent."
            return "operator > draft cancelled. No email was composed."
        if tool == "comm_send_message":
            mode = str(params.get("mode", "draft") or "draft").strip().lower()
            record_completed_turn(
                conversation_state=conversation_state,
                memory=memory,
                session=session,
                active_realm_name=active_realm_name,
                active_token=active_token,
                user_log=user_log,
                session_audit=session_audit,
            )
            if mode == "execute_send":
                return "operator > send cancelled. The drafted message remains unsent."
            return "operator > draft cancelled. Nothing was typed."
        operator_text = "tool use rejected. Proceeding without tool execution."
        t0 = time.monotonic()
        assistant_text = engine.respond(
            context_summary=startup_context_items(startup_context),
            conversation=session.events,
        )
        if faculty_monitor is not None:
            faculty_monitor.record_call("crown", (time.monotonic() - t0) * 1000, True)

    assistant_text, reflection_proposal = maybe_capture_reflection_proposal(
        assistant_text,
        proposal,
        session,
        reflective_memory,
    )
    session.add_event("assistant", assistant_text)
    append_user_log_entry(user_log, active_token, session.session_id, original_input, assistant_text)
    record_completed_turn(
        conversation_state=conversation_state,
        memory=memory,
        session=session,
        active_realm_name=active_realm_name,
        active_token=active_token,
        user_log=user_log,
        session_audit=session_audit,
    )
    lines = [f"operator > {operator_text}", f"inanna > {assistant_text}"]
    if reflection_proposal is not None:
        lines.append(reflection_proposal["line"])
    return "\n".join(lines)


def _resolve_inline_proposal(
    proposal: Proposal,
    created: dict,
    decision: str,
) -> dict:
    resolved = {
        **created,
        "status": "approved" if decision == "approve" else "rejected",
        "resolved_at": datetime.now(timezone.utc).isoformat(),
    }
    # The forget flow must resolve the specific proposal it just created,
    # even if older unrelated pending proposals exist.
    proposal._write_record(resolved)
    return {**resolved, "line": proposal.format_line(resolved)}


def run_forget_flow(
    memory: Memory,
    proposal: Proposal,
) -> str:
    report = memory.memory_log_report()
    print(build_memory_log_report(report))

    memory_id = input('Which memory record to remove? Enter memory_id or "cancel":').strip()
    if memory_id.lower() == "cancel":
        return "No memory removed."

    record = next(
        (item for item in report["records"] if item.get("memory_id") == memory_id),
        None,
    )
    if record is None:
        return "Memory record not found."

    created = proposal.create(
        what=f"Remove memory record {memory_id} from approved memory",
        why="User requested removal — sovereignty over personal memory",
        payload={"memory_id": memory_id, "action": "forget"},
    )
    print(created["line"])

    while True:
        decision = input('Type "approve" to confirm removal or "reject" to cancel:').strip().lower()
        if decision in {"approve", "reject"}:
            break

    if decision == "reject":
        _resolve_inline_proposal(proposal, created, decision)
        return "Memory record retained."

    if not memory.delete_memory_record(memory_id):
        _resolve_inline_proposal(proposal, created, "reject")
        return "Memory record not found."

    _resolve_inline_proposal(proposal, created, "approve")
    return f"Memory record {memory_id} removed."


def handle_command(
    command: str,
    session: Session,
    memory: Memory,
    proposal: Proposal,
    state_report: StateReport,
    engine: Engine,
    analyst: AnalystFaculty,
    classifier: IntentClassifier,
    routing_log: list[dict[str, str]],
    startup_context: dict,
    config: Config,
    operator: OperatorFaculty | None = None,
    calendar_workflows: CalendarWorkflows | None = None,
    browser_workflows: BrowserWorkflows | None = None,
    document_workflows: DocumentWorkflows | None = None,
    filesystem_faculty: FileSystemFaculty | None = None,
    process_faculty: ProcessFaculty | None = None,
    package_faculty: PackageFaculty | None = None,
    desktop_faculty: DesktopFaculty | None = None,
    communication_workflows: CommunicationWorkflows | None = None,
    email_workflows: EmailWorkflows | None = None,
    guardian: GuardianFaculty | None = None,
    guardian_metrics: dict[str, int] | None = None,
    nammu_dir: Path | None = None,
    realm_manager: RealmManager | None = None,
    active_realm: RealmConfig | None = None,
    user_manager: UserManager | None = None,
    session_state: dict[str, object | None] | None = None,
    token_store: TokenStore | None = None,
    user_log: UserLog | None = None,
    faculty_monitor: FacultyMonitor | None = None,
    session_audit: list[dict[str, str]] | None = None,
    process_monitor: ProcessMonitor | None = None,
    conversation_state: dict[str, int] | None = None,
    orchestration_engine: OrchestrationEngine | None = None,
    profile_manager: ProfileManager | None = None,
    reflective_memory: ReflectiveMemory | None = None,
    constitutional_filter: ConstitutionalFilter | None = None,
) -> str | None:
    normalized = command.strip()
    guardian_metrics = ensure_guardian_metrics(guardian_metrics)
    desktop_faculty = desktop_faculty or DesktopFaculty()
    calendar_workflows = calendar_workflows or CalendarWorkflows()
    browser_workflows = browser_workflows or BrowserWorkflows(desktop_faculty)
    document_workflows = document_workflows or DocumentWorkflows(desktop_faculty)
    filesystem_faculty = filesystem_faculty or FileSystemFaculty()
    process_faculty = process_faculty or ProcessFaculty()
    package_faculty = package_faculty or PackageFaculty()
    communication_workflows = communication_workflows or CommunicationWorkflows(desktop_faculty)
    email_workflows = email_workflows or EmailWorkflows(desktop_faculty)
    current_user = session_state.get("active_user") if session_state else None
    original_user = session_state.get("original_user") if session_state else None
    guardian_user = session_state.get("guardian_user") if session_state else None
    active_token = session_state.get("active_token") if session_state else None
    original_token = session_state.get("original_token") if session_state else None
    guardian_token = session_state.get("guardian_token") if session_state else None
    active_realm_name = active_realm.name if active_realm else DEFAULT_REALM
    current_realm = load_current_realm(realm_manager, active_realm)
    if current_realm is not None:
        active_realm_name = current_realm.name

    if session_state is not None and session_state.get("onboarding_active"):
        onboarding = handle_onboarding_response(
            state=session_state,
            text=normalized,
            profile_manager=profile_manager,
            active_user=current_user,
            active_token=active_token,
            engine=engine,
        )
        if onboarding["handled"]:
            return "\n".join(
                f"onboarding > {message}" for message in onboarding["messages"]
            )

    if not normalized:
        return ""

    lowered = normalized.lower()
    orchestration_engine = orchestration_engine or OrchestrationEngine(FACULTIES_CONFIG_PATH)
    if lowered in {"exit", "quit"}:
        return None

    if lowered == "users":
        if user_manager is None:
            return "users > user management is unavailable."
        allowed, reason = check_privilege(current_user, user_manager, "all")
        if not allowed:
            return f"access > {reason}"
        return build_users_report(user_manager)

    if lowered.startswith("create-user "):
        if user_manager is None:
            return "create-user > user management is unavailable."
        allowed, reason = check_privilege(current_user, user_manager, "all")
        if not allowed:
            return f"access > {reason}"
        parts = normalized.split(maxsplit=3)
        if len(parts) != 4:
            return "create-user > usage: create-user [display_name] [role] [realm]"
        _, display_name, role, realm_name = parts
        if role.strip().lower() not in user_manager.roles:
            return f"create-user > Unknown role: {role}"
        created = create_user_proposal(
            proposal=proposal,
            display_name=display_name,
            role=role.strip().lower(),
            realm_name=realm_name,
            created_by=active_token.user_id if active_token is not None else "system",
        )
        return "create-user > proposal required to create a new user.\n" + str(created["line"])

    if lowered.startswith("login"):
        if user_manager is None or token_store is None or session_state is None:
            return "login > session identity is unavailable."
        display_name = normalized[len("login") :].strip()
        if not display_name:
            return "login > usage: login [display_name]"
        target = user_manager.get_user_by_display_name(display_name)
        if target is None:
            return f"No user found with name: {display_name}"
        finalize_auto_memory(
            conversation_state=conversation_state,
            memory=memory,
            session=session,
            active_realm_name=active_realm_name,
            active_token=active_token,
            user_log=user_log,
            reason="session end",
            session_audit=session_audit,
        )
        token_store.revoke_all_for_user(target.user_id)
        token = token_store.issue(target.user_id, target.display_name, target.role)
        if profile_manager is not None:
            if target.role.strip().lower() == "guardian":
                ensure_guardian_profile_completed(profile_manager, target.user_id)
            else:
                profile_manager.ensure_profile_exists(target.user_id)
        session_state["active_token"] = token
        session_state["active_user"] = target
        session_state["nammu_profile"] = ensure_nammu_profile_for_user(
            profile_manager,
            nammu_dir,
            target.user_id,
        )
        session_state["last_nammu_input"] = ""
        session_state["last_nammu_route"] = "unknown"
        session_state["session_correction_count"] = 0
        if guardian_user is not None and target.user_id == guardian_user.user_id:
            session_state["guardian_token"] = token
            session_state["original_token"] = None
            session_state["original_user"] = None
        else:
            session_state["original_token"] = None
            session_state["original_user"] = None
        append_audit_event(
            session_audit,
            "login",
            f"{target.display_name} ({target.role}) logged in",
        )
        refresh_startup_context(startup_context, memory, target, user_manager)
        sync_profile_grounding(engine, profile_manager, target, token)
        notification_store = notification_store_from_profile_manager(profile_manager)
        lines = [
            f"login > session started for {target.display_name} ({target.role})",
            f"login > token: {token_preview(token)} valid for 8 hours",
            f"login > session bound to user_id: {target.user_id}",
        ]
        lines.extend(deliver_pending_notifications(notification_store, target.user_id))
        lines.extend(
            f"onboarding > {message}"
            for message in begin_onboarding_if_needed(
                session_state,
                profile_manager,
                target,
                token,
            )
        )
        return "\n".join(lines)

    if lowered == "logout":
        if token_store is None or session_state is None or active_token is None:
            return "No active session."
        finalize_auto_memory(
            conversation_state=conversation_state,
            memory=memory,
            session=session,
            active_realm_name=active_realm_name,
            active_token=active_token,
            user_log=user_log,
            reason="session end",
            session_audit=session_audit,
        )
        token_store.revoke(active_token.token)
        append_audit_event(
            session_audit,
            "logout",
            f"{active_token.display_name} ({active_token.role}) logged out",
        )
        session_state["active_token"] = None
        session_state["active_user"] = None
        session_state["original_token"] = None
        session_state["original_user"] = None
        session_state["nammu_profile"] = None
        session_state["last_nammu_input"] = ""
        session_state["last_nammu_route"] = "unknown"
        session_state["session_correction_count"] = 0
        refresh_startup_context(startup_context, memory, None, user_manager)
        sync_profile_grounding(engine, profile_manager, None, None)
        reset_onboarding_state(session_state)
        return f"logout > session ended for {active_token.display_name}"

    if lowered == "whoami":
        return build_whoami_report(active_token, user_manager)

    if lowered == "my-profile":
        if user_manager is None or active_token is None or current_user is None:
            return 'my-profile > No active session. Type "login [name]" to identify.'
        allowed, reason = check_privilege(current_user, user_manager, "converse")
        if not allowed:
            return f"access > {reason}"
        _, display_name, profile = resolve_profile_subject(
            profile_manager,
            current_user,
            active_token,
        )
        if profile is None:
            return "my-profile > profile management is unavailable."
        return format_profile_output(profile, display_name or current_user.display_name)

    if lowered == "nammu-profile":
        nammu_profile = (
            session_state.get("nammu_profile")
            if isinstance(session_state, dict)
            else None
        )
        if nammu_profile is None:
            return "nammu-profile > profile management is unavailable."
        top_domains = sorted(
            nammu_profile.domain_weights.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:5]
        return "\n".join(
            [
                f"nammu > operator profile for {nammu_profile.display_name or nammu_profile.user_id}",
                f"  languages: {nammu_profile.language_patterns}",
                f"  shorthands: {nammu_profile.known_shorthands}",
                f"  top domains: {top_domains}",
                f"  corrections: {len(nammu_profile.routing_corrections)}",
            ]
        )

    if lowered.startswith("nammu-learn"):
        if active_token is None or current_user is None:
            return 'nammu-learn > No active session. Type "login [name]" to identify.'
        nammu_profile = (
            session_state.get("nammu_profile")
            if isinstance(session_state, dict)
            else None
        )
        if nammu_profile is None or nammu_dir is None:
            return "nammu-learn > profile management is unavailable."
        parts = normalized.split(None, 2)
        if len(parts) != 3:
            return "nammu-learn > usage: nammu-learn [abbreviation] [full meaning]"
        _, abbreviation, full_meaning = parts
        nammu_profile.record_shorthand(abbreviation, full_meaning)
        save_operator_profile(nammu_dir, nammu_profile)
        return f"nammu > learned: '{abbreviation.lower()}' = '{full_meaning}'"

    if lowered.startswith("nammu-correct"):
        if active_token is None or current_user is None:
            return 'nammu-correct > No active session. Type "login [name]" to identify.'
        nammu_profile = (
            session_state.get("nammu_profile")
            if isinstance(session_state, dict)
            else None
        )
        if nammu_profile is None or nammu_dir is None:
            return "nammu-correct > profile management is unavailable."
        parts = normalized.split(None, 2)
        if len(parts) < 2:
            return "nammu-correct > usage: nammu-correct [intent] [optional params]"
        correct_intent = parts[1].strip()
        correct_params = parse_nammu_correction_params(parts[2] if len(parts) == 3 else "")
        original_text = (
            str(session_state.get("last_nammu_input", ""))
            if isinstance(session_state, dict)
            else ""
        )
        nammu_profile.record_correction(
            original_text=original_text,
            misrouted_to=(
                str(session_state.get("last_nammu_route", "unknown"))
                if isinstance(session_state, dict)
                else "unknown"
            ),
            correct_intent=correct_intent,
            correct_params=correct_params,
        )
        save_operator_profile(nammu_dir, nammu_profile)
        session_correction_count = (
            int(session_state.get("session_correction_count", 0))
            if isinstance(session_state, dict)
            else 0
        ) + 1
        if isinstance(session_state, dict):
            session_state["session_correction_count"] = session_correction_count
        lines = [
            "nammu > correction recorded",
            f"  learned: {build_nammu_correction_record_text(original_text, correct_intent, correct_params)}",
            f"  total corrections: {len(nammu_profile.routing_corrections)}",
        ]
        pattern_summary = build_nammu_pattern_summary(
            nammu_profile.routing_corrections,
            session_correction_count,
        )
        if pattern_summary:
            lines.append(pattern_summary)
        return "\n".join(lines)

    if lowered == "nammu-stats":
        nammu_profile = (
            session_state.get("nammu_profile")
            if isinstance(session_state, dict)
            else None
        )
        if nammu_profile is None or nammu_dir is None:
            return "nammu-stats > profile management is unavailable."
        routing_history = load_routing_history(nammu_dir, limit=100)
        stats = analyse_routing_log(routing_history, nammu_profile)
        session_correction_count = (
            int(session_state.get("session_correction_count", 0))
            if isinstance(session_state, dict)
            else 0
        )
        return "\n".join(
            [
                "nammu > routing statistics",
                f"  total routings (last 100): {stats['total_routings']}",
                f"  top domains: {stats['top_domains']}",
                f"  corrections recorded: {stats['correction_count']}",
                f"  known shorthands: {stats['known_shorthands']}",
                f"  session corrections: {session_correction_count}",
            ]
        )

    if lowered == "inanna-reflect":
        if user_manager is None:
            return "inanna-reflect > user management is unavailable."
        allowed, reason = check_privilege(current_user, user_manager, "all")
        if not allowed:
            return f"access > {reason}"
        if reflective_memory is None:
            return "inanna-reflect > reflective memory is unavailable."
        return reflective_memory.format_for_display()

    if lowered == "my-trust":
        if user_manager is None or active_token is None or current_user is None:
            return 'my-trust > No active session. Type "login [name]" to identify.'
        allowed, reason = check_privilege(current_user, user_manager, "converse")
        if not allowed:
            return f"access > {reason}"
        _, _, profile = resolve_profile_subject(
            profile_manager,
            current_user,
            active_token,
        )
        if profile is None:
            return "my-trust > profile management is unavailable."
        return build_trust_report(profile)

    if lowered == "my-departments":
        if user_manager is None or active_token is None or current_user is None:
            return 'my-departments > No active session. Type "login [name]" to identify.'
        allowed, reason = check_privilege(current_user, user_manager, "converse")
        if not allowed:
            return f"access > {reason}"
        _, _, profile = resolve_profile_subject(
            profile_manager,
            current_user,
            active_token,
        )
        if profile is None:
            return "my-departments > profile management is unavailable."
        return build_organizational_context_report(profile)

    if lowered.startswith("my-profile edit"):
        if user_manager is None or active_token is None or current_user is None:
            return 'my-profile > No active session. Type "login [name]" to identify.'
        allowed, reason = check_privilege(current_user, user_manager, "converse")
        if not allowed:
            return f"access > {reason}"
        parsed = parse_profile_edit_command(normalized)
        if parsed is None:
            return "my-profile > usage: my-profile edit [field] [value]"
        field_name, raw_value = parsed
        if not has_profile_field(field_name):
            return f"profile > unknown field: {field_name}"
        if field_name in PROFILE_READ_ONLY_FIELDS:
            return f"profile > {field_name} is read-only."
        if field_name in PROFILE_GUARDIAN_ONLY_FIELDS:
            allowed, reason = check_privilege(current_user, user_manager, "all")
            if not allowed:
                return f"access > {reason}"
        user_id, _, profile = resolve_profile_subject(
            profile_manager,
            current_user,
            active_token,
        )
        if profile is None or profile_manager is None:
            return "my-profile > profile management is unavailable."
        value = coerce_profile_field_value(field_name, raw_value)
        if not profile_manager.update_field(user_id, field_name, value):
            return f"profile > unable to update {field_name}."
        sync_profile_grounding(engine, profile_manager, current_user, active_token)
        return f"profile > {field_name} updated to {format_profile_value(value)}."

    if lowered.startswith("governance-trust"):
        if user_manager is None or active_token is None or current_user is None:
            return 'governance-trust > No active session. Type "login [name]" to identify.'
        allowed, reason = check_privilege(current_user, user_manager, "converse")
        if not allowed:
            return f"access > {reason}"
        tool_name = normalize_tool_name(normalized[len("governance-trust") :])
        if not tool_name:
            return "governance-trust > usage: governance-trust [tool]"
        user_id, _, profile = resolve_profile_subject(
            profile_manager,
            current_user,
            active_token,
        )
        if profile is None or profile_manager is None:
            return "governance-trust > profile management is unavailable."
        updated, changed, normalized_tool = grant_persistent_tool_trust(
            profile_manager,
            operator,
            user_id,
            tool_name,
        )
        if not updated:
            return f"governance > unknown tool: {normalized_tool or tool_name}"
        if not changed:
            return "governance > trust not updated."
        append_audit_event(
            session_audit,
            "trust_granted",
            f"{current_user.display_name} granted persistent trust for {normalized_tool}",
            {"tool": normalized_tool, "user_id": user_id},
        )
        return f"governance > {normalized_tool} is now persistently trusted for you."

    if lowered.startswith("governance-revoke"):
        if user_manager is None or active_token is None or current_user is None:
            return 'governance-revoke > No active session. Type "login [name]" to identify.'
        allowed, reason = check_privilege(current_user, user_manager, "converse")
        if not allowed:
            return f"access > {reason}"
        tool_name = normalize_tool_name(normalized[len("governance-revoke") :])
        if not tool_name:
            return "governance-revoke > usage: governance-revoke [tool]"
        user_id, _, profile = resolve_profile_subject(
            profile_manager,
            current_user,
            active_token,
        )
        if profile is None or profile_manager is None:
            return "governance-revoke > profile management is unavailable."
        updated, removed, normalized_tool = revoke_persistent_tool_trust(
            profile_manager,
            user_id,
            tool_name,
        )
        if not updated:
            return "governance-revoke > profile management is unavailable."
        if not removed:
            return f"governance > {normalized_tool or tool_name} was not persistently trusted."
        append_audit_event(
            session_audit,
            "trust_revoked",
            f"{current_user.display_name} revoked persistent trust for {normalized_tool}",
            {"tool": normalized_tool, "user_id": user_id},
        )
        return (
            f"governance > {normalized_tool} trust revoked. "
            "Proposals will resume for this tool."
        )

    if lowered.startswith("my-profile clear"):
        if user_manager is None or active_token is None or current_user is None:
            return 'my-profile > No active session. Type "login [name]" to identify.'
        allowed, reason = check_privilege(current_user, user_manager, "converse")
        if not allowed:
            return f"access > {reason}"
        field_name = parse_profile_clear_command(normalized)
        if field_name is None:
            return "my-profile > usage: my-profile clear [field]"
        if field_name == "communication":
            user_id, _, profile = resolve_profile_subject(
                profile_manager,
                current_user,
                active_token,
            )
            if profile is None or profile_manager is None:
                return "my-profile > profile management is unavailable."
            if not clear_communication_observations(profile_manager, user_id):
                return "profile > unable to clear communication observations."
            sync_profile_grounding(engine, profile_manager, current_user, active_token)
            return "profile > Communication observations cleared."
        if not has_profile_field(field_name):
            return f"profile > unknown field: {field_name}"
        if field_name in PROFILE_PROTECTED_CLEAR_FIELDS:
            return f"profile > {field_name} cannot be cleared."
        if field_name in PROFILE_GUARDIAN_ONLY_FIELDS:
            allowed, reason = check_privilege(current_user, user_manager, "all")
            if not allowed:
                return f"access > {reason}"
        user_id, _, profile = resolve_profile_subject(
            profile_manager,
            current_user,
            active_token,
        )
        if profile is None or profile_manager is None:
            return "my-profile > profile management is unavailable."
        if not profile_manager.update_field(
            user_id,
            field_name,
            default_profile_field_value(field_name),
        ):
            return f"profile > unable to clear {field_name}."
        sync_profile_grounding(engine, profile_manager, current_user, active_token)
        return f"profile > {field_name} cleared."

    if lowered.startswith("view-profile"):
        if user_manager is None:
            return "view-profile > user management is unavailable."
        allowed, reason = check_privilege(current_user, user_manager, "all")
        if not allowed:
            return f"access > {reason}"
        display_name = normalized[len("view-profile") :].strip()
        if not display_name:
            return "view-profile > usage: view-profile [display_name]"
        target = user_manager.get_user_by_display_name(display_name)
        if target is None:
            return f"view-profile > No user found: {display_name}"
        target_profile = (
            profile_manager.ensure_profile_exists(target.user_id)
            if profile_manager is not None
            else UserProfile(user_id=target.user_id)
        )
        return format_profile_output(
            target_profile,
            target.display_name,
            heading=f"Profile for {target.display_name} ({target.user_id}):",
            include_actions=False,
        )

    if lowered.startswith("assign-department"):
        if user_manager is None or current_user is None:
            return "assign-department > user management is unavailable."
        allowed, reason = check_privilege(current_user, user_manager, "all")
        if not allowed:
            return f"access > {reason}"
        parsed = parse_user_realm_command(normalized, "assign-department")
        if parsed is None:
            return "assign-department > usage: assign-department [display_name] [department]"
        display_name, department = parsed
        target = user_manager.get_user_by_display_name(display_name)
        if target is None:
            return f"assign-department > No user found: {display_name}"
        updated, normalized_department = assign_profile_membership(
            profile_manager,
            target.user_id,
            "departments",
            department,
        )
        if not updated:
            return "assign-department > profile management is unavailable."
        append_audit_event(
            session_audit,
            "assign_department",
            f"{current_user.display_name} assigned {target.display_name} to department {normalized_department}",
        )
        return f"org > {target.display_name} assigned to department: {normalized_department}"

    if lowered.startswith("unassign-department"):
        if user_manager is None or current_user is None:
            return "unassign-department > user management is unavailable."
        allowed, reason = check_privilege(current_user, user_manager, "all")
        if not allowed:
            return f"access > {reason}"
        parsed = parse_user_realm_command(normalized, "unassign-department")
        if parsed is None:
            return "unassign-department > usage: unassign-department [display_name] [department]"
        display_name, department = parsed
        target = user_manager.get_user_by_display_name(display_name)
        if target is None:
            return f"unassign-department > No user found: {display_name}"
        updated, removed, normalized_department = unassign_profile_membership(
            profile_manager,
            target.user_id,
            "departments",
            department,
        )
        if not updated:
            return "unassign-department > profile management is unavailable."
        if not removed:
            return f"org > {target.display_name} was not assigned to department: {normalized_department}"
        append_audit_event(
            session_audit,
            "unassign_department",
            f"{current_user.display_name} removed {target.display_name} from department {normalized_department}",
        )
        return f"org > {target.display_name} removed from department: {normalized_department}"

    if lowered.startswith("assign-group"):
        if user_manager is None or current_user is None:
            return "assign-group > user management is unavailable."
        allowed, reason = check_privilege(current_user, user_manager, "all")
        if not allowed:
            return f"access > {reason}"
        parsed = parse_user_realm_command(normalized, "assign-group")
        if parsed is None:
            return "assign-group > usage: assign-group [display_name] [group]"
        display_name, group = parsed
        target = user_manager.get_user_by_display_name(display_name)
        if target is None:
            return f"assign-group > No user found: {display_name}"
        updated, normalized_group = assign_profile_membership(
            profile_manager,
            target.user_id,
            "groups",
            group,
        )
        if not updated:
            return "assign-group > profile management is unavailable."
        append_audit_event(
            session_audit,
            "assign_group",
            f"{current_user.display_name} assigned {target.display_name} to group {normalized_group}",
        )
        return f"org > {target.display_name} assigned to group: {normalized_group}"

    if lowered.startswith("unassign-group"):
        if user_manager is None or current_user is None:
            return "unassign-group > user management is unavailable."
        allowed, reason = check_privilege(current_user, user_manager, "all")
        if not allowed:
            return f"access > {reason}"
        parsed = parse_user_realm_command(normalized, "unassign-group")
        if parsed is None:
            return "unassign-group > usage: unassign-group [display_name] [group]"
        display_name, group = parsed
        target = user_manager.get_user_by_display_name(display_name)
        if target is None:
            return f"unassign-group > No user found: {display_name}"
        updated, removed, normalized_group = unassign_profile_membership(
            profile_manager,
            target.user_id,
            "groups",
            group,
        )
        if not updated:
            return "unassign-group > profile management is unavailable."
        if not removed:
            return f"org > {target.display_name} was not assigned to group: {normalized_group}"
        append_audit_event(
            session_audit,
            "unassign_group",
            f"{current_user.display_name} removed {target.display_name} from group {normalized_group}",
        )
        return f"org > {target.display_name} removed from group: {normalized_group}"

    if lowered.startswith("notify-department"):
        if user_manager is None or current_user is None:
            return "notify-department > user management is unavailable."
        allowed, reason = check_privilege(current_user, user_manager, "all")
        if not allowed:
            return f"access > {reason}"
        parts = normalized.split(maxsplit=2)
        if len(parts) != 3:
            return "notify-department > usage: notify-department [department] [message]"
        _, department, message = parts
        notification_store = notification_store_from_profile_manager(profile_manager)
        recipient_count, normalized_department = queue_department_notifications(
            notification_store,
            user_manager,
            profile_manager,
            department,
            message,
            current_user.role.strip().lower() or "guardian",
        )
        append_audit_event(
            session_audit,
            "notify_department",
            (
                f"{current_user.display_name} notified department "
                f"{normalized_department or normalize_org_value(department)} ({recipient_count} recipients)"
            ),
        )
        return (
            f"org > Department {normalized_department or normalize_org_value(department)} "
            f"notified ({recipient_count} recipient(s))."
        )

    if lowered == "faculties":
        if faculty_monitor is None:
            return "faculties > faculty monitor is unavailable."
        return faculty_monitor.format_report()

    if lowered == "faculty-registry":
        if faculty_monitor is None:
            return "faculty-registry > faculty monitor is unavailable."
        return build_faculty_registry_report(build_faculty_registry_payload(faculty_monitor))

    if lowered == "my-log":
        if user_manager is None or user_log is None or active_token is None:
            return 'my-log > No active session. Type "login [name]" to identify.'
        allowed, reason = check_privilege(current_user, user_manager, "read_own_log")
        if not allowed:
            return f"access > {reason}"
        return format_user_log_report(
            "Your interaction log",
            user_log.load(active_token.user_id, limit=20),
        )

    if lowered.startswith("user-log"):
        if user_manager is None or user_log is None:
            return "user-log > user log is unavailable."
        allowed, reason = check_privilege(current_user, user_manager, "all")
        if not allowed:
            return f"access > {reason}"
        display_name = normalized[len("user-log") :].strip()
        if not display_name:
            return "user-log > usage: user-log [display_name]"
        target = user_manager.get_user_by_display_name(display_name)
        if target is None:
            return f"user-log > No user found: {display_name}"
        return format_user_log_report(
            f"Interaction log for {target.display_name} ({target.user_id})",
            user_log.load(target.user_id, limit=20),
        )

    if lowered.startswith("invite "):
        if user_manager is None or current_user is None or active_token is None:
            return "invite > invite flow is unavailable."
        allowed = user_manager.has_privilege(current_user.user_id, "invite_users")
        if not allowed:
            return f"access > Insufficient privileges. {current_user.display_name} ({current_user.role}) does not have: invite_users"
        parts = normalized.split(maxsplit=2)
        if len(parts) != 3:
            return "invite > usage: invite [role] [realm]"
        _, role, realm_name = parts
        if role.strip().lower() not in user_manager.roles:
            return f"invite > Unknown role: {role}"
        created = create_invite_proposal(
            proposal=proposal,
            role=role.strip().lower(),
            realm_name=realm_name,
            created_by=active_token.user_id,
        )
        return "invite > proposal required to create an invite.\n" + str(created["line"])

    if lowered.startswith("join "):
        if user_manager is None or token_store is None or session_state is None:
            return "join > invite flow is unavailable."
        parts = normalized.split(maxsplit=2)
        if len(parts) != 3:
            return "join > usage: join [invite_code] [display_name]"
        _, invite_code, display_name = parts
        invite = user_manager.get_invite(invite_code)
        if invite is None:
            return "join > Invalid invite code."
        if invite.status == "expired":
            return "join > This invite has expired."
        if invite.status == "accepted":
            return "join > This invite has already been used."
        created = user_manager.accept_invite(invite_code, display_name)
        if created is None:
            refreshed = user_manager.get_invite(invite_code)
            if refreshed is not None and refreshed.status == "expired":
                return "join > This invite has expired."
            return "join > This invite could not be accepted."
        finalize_auto_memory(
            conversation_state=conversation_state,
            memory=memory,
            session=session,
            active_realm_name=active_realm_name,
            active_token=active_token,
            user_log=user_log,
            reason="session end",
            session_audit=session_audit,
        )
        token_store.revoke_all_for_user(created.user_id)
        token = token_store.issue(created.user_id, created.display_name, created.role)
        if profile_manager is not None:
            profile_manager.ensure_profile_exists(created.user_id)
        session_state["active_token"] = token
        session_state["active_user"] = created
        session_state["original_token"] = None
        session_state["original_user"] = None
        session_state["nammu_profile"] = ensure_nammu_profile_for_user(
            profile_manager,
            nammu_dir,
            created.user_id,
        )
        session_state["last_nammu_input"] = ""
        session_state["last_nammu_route"] = "unknown"
        session_state["session_correction_count"] = 0
        append_audit_event(
            session_audit,
            "join",
            f"{created.display_name} joined via invite {invite_code}",
        )
        refresh_startup_context(startup_context, memory, created, user_manager)
        sync_profile_grounding(engine, profile_manager, created, token)
        notification_store = notification_store_from_profile_manager(profile_manager)
        lines = [
            f"join > Welcome, {created.display_name}.",
            "join > Your account has been created.",
            f"join > Role: {created.role}  Realm: {', '.join(created.assigned_realms)}",
            "join > You are now logged in.",
            'join > Type "whoami" to see your session details.',
        ]
        lines.extend(deliver_pending_notifications(notification_store, created.user_id))
        lines.extend(
            f"onboarding > {message}"
            for message in begin_onboarding_if_needed(
                session_state,
                profile_manager,
                created,
                token,
            )
        )
        return "\n".join(lines)

    if lowered == "invites":
        if user_manager is None:
            return "invites > invite flow is unavailable."
        if current_user is None:
            return "access > No active session."
        if not (
            user_manager.has_privilege(current_user.user_id, "all")
            or user_manager.has_privilege(current_user.user_id, "invite_users")
        ):
            return (
                f"access > Insufficient privileges. "
                f"{current_user.display_name} ({current_user.role}) does not have: invite_users"
            )
        return build_invites_report(user_manager.list_invites(), current_user)

    if lowered == "admin-surface":
        if user_manager is None or user_log is None or realm_manager is None:
            return "admin-surface > admin surface is unavailable."
        if current_user is None:
            return "access > No active session."
        if not has_admin_surface_access(user_manager, current_user):
            return (
                f"access > Insufficient privileges. "
                f"{current_user.display_name} ({current_user.role}) does not have: invite_users"
            )
        return build_admin_surface_report(
            build_admin_surface_payload(
                user_manager=user_manager,
                user_log=user_log,
                realm_manager=realm_manager,
                active_user=current_user,
                profile_manager=profile_manager,
            )
        )

    if lowered == "tool-registry":
        operator = operator or OperatorFaculty()
        return build_tool_registry_report(build_tool_registry_payload(operator))

    if lowered == "network-status":
        return build_network_status_report(build_network_status_payload(session_audit))

    if lowered == "process-status":
        process_monitor = process_monitor or ProcessMonitor(time.time())
        return build_process_status_report(build_process_status_payload(process_monitor))

    if lowered == "status":
        history = proposal.history_report()
        return state_report.render(
            session_id=session.session_id,
            mode=engine.mode,
            memory_count=memory.memory_count(
                user_id=memory_scope_user_id(current_user, user_manager)
            ),
            pending_count=history["pending"],
            total_proposals=history["total"],
            approved_proposals=history["approved"],
            rejected_proposals=history["rejected"],
            realm_name=active_realm_name,
            realm_memory_count=count_records(memory.memory_dir, "*.json"),
            realm_session_count=count_records(memory.session_dir, "*.json"),
            realm_governance_context=(
                current_realm.governance_context if current_realm else ""
            ),
            active_user=(
                f"{current_user.display_name} ({current_user.role})"
                if current_user is not None
                else "none"
            ),
            realm_access=can_access_realm(current_user, active_realm_name)
            if current_user is not None
            else True,
        )

    if lowered in {"body", "diagnostics"}:
        current_realm = load_current_realm(realm_manager, active_realm)
        return build_diagnostics_report(
            config=config,
            engine=engine,
            session=session,
            proposal=proposal,
            memory_dir=memory.memory_dir,
            proposal_dir=proposal.proposal_dir,
            nammu_dir=resolve_nammu_dir(session, nammu_dir),
            data_root=DATA_ROOT,
            realm_name=current_realm.name if current_realm else DEFAULT_REALM,
        )

    if lowered == "realms":
        active_realm_name = active_realm.name if active_realm else DEFAULT_REALM
        if realm_manager is None:
            return (
                f"realms > Available realms (1):\n"
                f"  [{active_realm_name}]  No purpose set.\n"
                f"  Active: {active_realm_name}"
            )
        return build_realms_report(realm_manager, active_realm_name)

    if lowered.startswith("create-realm"):
        if realm_manager is None:
            return "create-realm > realm management is unavailable."
        if user_manager is not None:
            allowed, reason = check_privilege(current_user, user_manager, "all")
            if not allowed:
                return f"access > {reason}"
        parts = normalized.split(maxsplit=2)
        if len(parts) < 2:
            return "create-realm > usage: create-realm [name] [purpose]"
        realm_name = parts[1].strip()
        purpose = parts[2].strip() if len(parts) == 3 else ""
        if not realm_name:
            return "create-realm > usage: create-realm [name] [purpose]"
        if realm_manager.realm_exists(realm_name):
            return f"create-realm > Realm {realm_name} already exists."
        created = create_realm_proposal(
            proposal=proposal,
            realm_name=realm_name,
            purpose=purpose,
            created_by=active_token.user_id if active_token is not None else "system",
        )
        return "create-realm > proposal required to create a new realm.\n" + str(created["line"])

    if lowered == "realm-context":
        current_realm = load_current_realm(realm_manager, active_realm)
        return build_realm_context_report(
            current_realm,
            memory.session_dir,
            memory.memory_dir,
            proposal.proposal_dir,
        )

    if lowered.startswith("realm-context "):
        if active_realm is None:
            return "realm-context > no active realm is available."
        if user_manager is not None:
            allowed, reason = check_privilege(current_user, user_manager, "all")
            if not allowed:
                return f"access > {reason}"
        governance_context = normalized[len("realm-context") :].strip()
        if not governance_context:
            return "realm-context > provide governance context text to propose an update."
        created = create_realm_context_proposal(
            proposal=proposal,
            active_realm=active_realm,
            governance_context=governance_context,
        )
        return (
            "realm-context > proposal required to update the active realm context.\n"
            f"{created['line']}"
        )

    if lowered.startswith("switch-user"):
        if user_manager is None or session_state is None:
            return "switch-user > user management is unavailable."
        finalize_auto_memory(
            conversation_state=conversation_state,
            memory=memory,
            session=session,
            active_realm_name=active_realm_name,
            active_token=active_token,
            user_log=user_log,
            reason="session end",
            session_audit=session_audit,
        )
        controller = original_user or current_user
        allowed, reason = check_privilege(controller, user_manager, "all")
        if not allowed:
            return f"access > {reason}"
        target_name = normalized[len("switch-user") :].strip()
        if not target_name:
            return "switch-user > provide a display name or 'off'."
        guardian_record = guardian_user or controller
        if guardian_record is None:
            return "switch-user > guardian context is unavailable."
        if target_name.lower() in {"off", guardian_record.display_name.lower()}:
            session_state["active_user"] = guardian_record
            session_state["original_user"] = None
            session_state["nammu_profile"] = ensure_nammu_profile_for_user(
                profile_manager,
                nammu_dir,
                guardian_record.user_id,
            )
            session_state["last_nammu_input"] = ""
            session_state["last_nammu_route"] = "unknown"
            session_state["session_correction_count"] = 0
            refresh_startup_context(startup_context, memory, guardian_record, user_manager)
            sync_profile_grounding(
                engine,
                profile_manager,
                guardian_record,
                active_token,
            )
            lines = [
                f"switch-user > Returned to {guardian_record.display_name} ({guardian_record.role})."
            ]
            lines.extend(
                f"onboarding > {message}"
                for message in begin_onboarding_if_needed(
                    session_state,
                    profile_manager,
                    guardian_record,
                    active_token,
                )
            )
            return "\n".join(lines)
        target = user_manager.get_user_by_display_name(target_name)
        if target is None:
            return f"switch-user > No user found: {target_name}"
        if profile_manager is not None:
            if target.role.strip().lower() == "guardian":
                ensure_guardian_profile_completed(profile_manager, target.user_id)
            else:
                profile_manager.ensure_profile_exists(target.user_id)
        session_state["active_user"] = target
        session_state["guardian_user"] = guardian_record
        session_state["original_user"] = guardian_record
        session_state["nammu_profile"] = ensure_nammu_profile_for_user(
            profile_manager,
            nammu_dir,
            target.user_id,
        )
        session_state["last_nammu_input"] = ""
        session_state["last_nammu_route"] = "unknown"
        session_state["session_correction_count"] = 0
        refresh_startup_context(startup_context, memory, target, user_manager)
        sync_profile_grounding(engine, profile_manager, target, active_token)
        lines = [f"switch-user > Now operating as: {target.display_name} ({target.role})"]
        if not can_access_realm(target, active_realm_name):
            lines.extend(
                [
                    f"switch-user > Warning: {target.display_name} does not have access to realm {active_realm_name}.",
                    f"switch-user > Operating as {target.display_name} in an unassigned realm.",
                    "switch-user > Use assign-realm to grant access.",
                ]
            )
        else:
            lines.append(
                f'switch-user > Type "switch-user {guardian_record.display_name}" to return to Guardian.'
            )
        lines.extend(
            f"onboarding > {message}"
            for message in begin_onboarding_if_needed(
                session_state,
                profile_manager,
                target,
                active_token,
            )
        )
        return "\n".join(lines)

    if lowered.startswith("assign-realm"):
        if user_manager is None or session_state is None:
            return "assign-realm > user management is unavailable."
        allowed, reason = check_privilege(current_user, user_manager, "all")
        if not allowed:
            return f"access > {reason}"
        parsed = parse_user_realm_command(normalized, "assign-realm")
        if parsed is None:
            return "assign-realm > usage: assign-realm [user_name] [realm_name]"
        display_name, realm_name = parsed
        target = user_manager.get_user_by_display_name(display_name)
        if target is None:
            return f"assign-realm > No user found: {display_name}"
        created = create_realm_assignment_proposal(
            proposal=proposal,
            display_name=target.display_name,
            user_id=target.user_id,
            realm_name=realm_name,
            action="assign_realm",
        )
        return "assign-realm > proposal required to change realm access.\n" + created["line"]

    if lowered.startswith("unassign-realm"):
        if user_manager is None or session_state is None:
            return "unassign-realm > user management is unavailable."
        allowed, reason = check_privilege(current_user, user_manager, "all")
        if not allowed:
            return f"access > {reason}"
        parsed = parse_user_realm_command(normalized, "unassign-realm")
        if parsed is None:
            return "unassign-realm > usage: unassign-realm [user_name] [realm_name]"
        display_name, realm_name = parsed
        target = user_manager.get_user_by_display_name(display_name)
        if target is None:
            return f"unassign-realm > No user found: {display_name}"
        created = create_realm_assignment_proposal(
            proposal=proposal,
            display_name=target.display_name,
            user_id=target.user_id,
            realm_name=realm_name,
            action="unassign_realm",
        )
        return "unassign-realm > proposal required to change realm access.\n" + created["line"]

    if lowered in {"history", "proposal-history"}:
        return build_history_report(proposal.history_report())

    if lowered == "routing-log":
        return build_routing_log_report(routing_log)

    if lowered == "nammu-log":
        return build_nammu_log_report(resolve_nammu_dir(session, nammu_dir))

    if lowered == "memory-log":
        return build_memory_log_report(
            memory.memory_log_report(user_id=memory_scope_user_id(current_user, user_manager))
        )

    if lowered == "forget":
        return run_forget_flow(memory=memory, proposal=proposal)

    if lowered == "analyse" or lowered.startswith("analyse "):
        question = normalized[len("analyse") :].strip()
        t0 = time.monotonic()
        analysis_mode, analysis_text = analyst.analyse(
            question=question,
            context=startup_context_items(startup_context),
        )
        if faculty_monitor is not None:
            faculty_monitor.record_call("analyst", (time.monotonic() - t0) * 1000, True)
        if not question:
            return f"analyst > [analysis fallback] {analysis_text}"

        session.add_event("user", normalized)
        session.add_event("analyst", analysis_text)
        append_user_log_entry(user_log, active_token, session.session_id, normalized, analysis_text)
        record_completed_turn(
            conversation_state=conversation_state,
            memory=memory,
            session=session,
            active_realm_name=active_realm_name,
            active_token=active_token,
            user_log=user_log,
            session_audit=session_audit,
        )
        if analysis_mode == "live":
            return f"analyst > [live analysis] {analysis_text}"
        return f"analyst > [analysis fallback] {analysis_text}"

    if lowered == "audit":
        audit_mode, audit_text = engine.speak_audit(
            history=proposal.history_report(),
            memory_log=memory.memory_log_report(),
            context_summary=startup_context_items(startup_context),
        )
        if audit_mode == "live":
            return f"inanna> [live audit] {audit_text}"
        return f"inanna> [audit summary] {audit_text}"

    if lowered == "guardian":
        guardian = guardian or GuardianFaculty()
        t0 = time.monotonic()
        report = guardian.format_report(
            guardian.inspect(
                session_id=session.session_id,
                memory_count=memory.memory_count(),
                pending_proposals=proposal.pending_count(),
                routing_log=routing_log,
                governance_blocks=guardian_metrics["governance_blocks"],
                tool_executions=guardian_metrics["tool_executions"],
                governance_history=load_governance_history(resolve_nammu_dir(session, nammu_dir)),
            )
        )
        if faculty_monitor is not None:
            faculty_monitor.record_call("guardian", (time.monotonic() - t0) * 1000, True)
        return f"guardian > {report}"

    if lowered == "guardian-dismiss":
        return "guardian > alerts dismissed."

    if lowered == "guardian-clear-events":
        cleared = len(session_audit or [])
        if session_audit is not None:
            session_audit.clear()
        return f"guardian > cleared {cleared} governance event(s)."

    if lowered == "reflect":
        reflection_mode, reflection_text = engine.reflect(startup_context_items(startup_context))
        if reflection_mode == "live":
            return f"inanna> [live reflection] {reflection_text}"
        return f"inanna> [memory fallback] {reflection_text}"

    if lowered in {"approve", "reject"}:
        resolved = proposal.resolve_next(lowered)
        if not resolved:
            return "No pending proposals."

        operator = operator or OperatorFaculty()
        payload = resolved["payload"]
        if payload.get("action") == "tool_use":
            # DECISION POINT: CLI approve/reject continues to resolve the oldest
            # pending proposal first, so tool execution follows the existing
            # queue discipline rather than adding a new targeted approval syntax.
            return complete_tool_resolution(
                resolved=resolved,
                decision=lowered,
                session=session,
                proposal=proposal,
                memory=memory,
                engine=engine,
                startup_context=startup_context,
                operator=operator,
                guardian_metrics=guardian_metrics,
                active_token=active_token,
                user_log=user_log,
                faculty_monitor=faculty_monitor,
                filesystem_faculty=filesystem_faculty,
                process_faculty=process_faculty,
                package_faculty=package_faculty,
                desktop_faculty=desktop_faculty,
                communication_workflows=communication_workflows,
                email_workflows=email_workflows,
                session_audit=session_audit,
                active_realm_name=active_realm_name,
                conversation_state=conversation_state,
                reflective_memory=reflective_memory,
                nammu_dir=nammu_dir,
                nammu_profile=(
                    session_state.get("nammu_profile")
                    if isinstance(session_state, dict)
                    else None
                ),
            )

        if payload.get("action") == "orchestration":
            outcome = complete_orchestration_resolution(
                resolved=resolved,
                decision=lowered,
                session=session,
                memory=memory,
                engine=engine,
                config=config,
                startup_context=startup_context,
                orchestration_engine=orchestration_engine,
                active_token=active_token,
                user_log=user_log,
                faculty_monitor=faculty_monitor,
                session_audit=session_audit,
                active_realm_name=active_realm_name,
                conversation_state=conversation_state,
                current_user=current_user,
                profile_manager=profile_manager,
            )
            return outcome["display_text"]

        if payload.get("action") == "reflection":
            entry = reflection_entry_from_payload(payload)
            if lowered != "approve":
                return f"Rejected {resolved['proposal_id']}."
            if entry is None or reflective_memory is None:
                return f"Approved {resolved['proposal_id']} but reflective memory was unavailable."
            approver = (
                current_user.display_name
                if current_user is not None
                else (
                    active_token.display_name
                    if active_token is not None
                    else "guardian"
                )
            )
            reflective_memory.approve(entry, approved_by=approver)
            sync_profile_grounding(engine, profile_manager, current_user, active_token, reflective_memory)
            append_audit_event(
                session_audit,
                "reflection_approved",
                f"reflection_approved: {entry.observation[:60]}",
                {"entry_id": entry.entry_id, "approved_by": approver},
            )
            return f"Approved {resolved['proposal_id']} and recorded INANNA reflection."

        if payload.get("action") == "realm_context_update":
            realm_name = payload.get("realm_name", "")
            governance_context = payload.get("governance_context", "")
            if resolved["status"] == "approved":
                if realm_manager is None or not realm_name:
                    return f"Approved {resolved['proposal_id']} but no realm manager was available."
                if not realm_manager.update_realm_governance_context(
                    realm_name,
                    governance_context,
                ):
                    return f"Approved {resolved['proposal_id']} but realm {realm_name} was not found."
                if active_realm is not None and active_realm.name == realm_name:
                    active_realm.governance_context = governance_context
                return (
                    f"Approved {resolved['proposal_id']} and updated governance context "
                    f"for realm {realm_name}."
                )
            return f"Rejected {resolved['proposal_id']}."

        if payload.get("action") == "create_user":
            if user_manager is None:
                return f"Approved {resolved['proposal_id']} but user management was unavailable."
            created_by = str(payload.get("created_by", "system"))
            try:
                created_user = user_manager.create_user(
                    display_name=str(payload.get("display_name", "")).strip(),
                    role=str(payload.get("role", "")).strip(),
                    assigned_realms=list(payload.get("assigned_realms", ["default"])),
                    created_by=created_by,
                )
            except ValueError as exc:
                return f"Approved {resolved['proposal_id']} but user creation failed: {exc}"
            return (
                f"User created: {created_user.display_name} ({created_user.user_id}) "
                f"role: {created_user.role}"
            )

        if payload.get("action") == "create_realm":
            realm_name = str(payload.get("realm_name", "")).strip()
            purpose = str(payload.get("purpose", "")).strip()
            if resolved["status"] != "approved":
                return f"Rejected {resolved['proposal_id']}."
            if realm_manager is None or not realm_name:
                return f"Approved {resolved['proposal_id']} but realm management was unavailable."
            if realm_manager.realm_exists(realm_name):
                return f"create-realm > Realm {realm_name} already exists."
            realm_manager.create_realm(realm_name, purpose)
            append_audit_event(
                session_audit,
                "realm",
                f"realm {realm_name} created",
            )
            return f"create-realm > Realm {realm_name} created."

        if payload.get("action") == "create_invite":
            if user_manager is None:
                return f"Approved {resolved['proposal_id']} but invite management was unavailable."
            invite = user_manager.create_invite(
                role=str(payload.get("role", "")).strip(),
                assigned_realms=list(payload.get("assigned_realms", ["default"])),
                created_by=str(payload.get("created_by", "system")),
            )
            append_audit_event(
                session_audit,
                "invite",
                (
                    f"invite {invite.invite_code} created for "
                    f"{invite.role}/{','.join(invite.assigned_realms)}"
                ),
            )
            expires = datetime.fromisoformat(invite.expires_at).strftime("%b %d %H:%M")
            return "\n".join(
                [
                    "invite > Invite created.",
                    f"invite > Code: {invite.invite_code}",
                    f"invite > Role: {invite.role}  Realm: {', '.join(invite.assigned_realms)}",
                    f"invite > Expires: {expires}  (48 hours)",
                    "invite > Share this code with the person you are inviting.",
                    f"invite > They join with: join {invite.invite_code} [their name]",
                ]
            )

        if payload.get("action") in {"assign_realm", "unassign_realm"}:
            if user_manager is None:
                return f"Approved {resolved['proposal_id']} but user management was unavailable."
            display_name = str(payload.get("display_name", "")).strip()
            user_id = str(payload.get("user_id", "")).strip()
            realm_name = str(payload.get("realm_name", "")).strip()
            target = user_manager.get_user(user_id)
            if resolved["status"] != "approved":
                return f"Rejected {resolved['proposal_id']}."
            if target is None:
                return f"Approved {resolved['proposal_id']} but user {display_name or user_id} was not found."
            if payload.get("action") == "assign_realm":
                if user_manager.assign_realm(user_id, realm_name):
                    refresh_session_state_user(session_state, user_manager, user_id)
                    return f"assign-realm > Realm {realm_name} assigned to {target.display_name}."
                return f"assign-realm > {target.display_name} already has access to realm {realm_name}."
            if len(target.assigned_realms) <= 1 and realm_name in target.assigned_realms:
                return f"unassign-realm > Cannot remove last realm for {target.display_name}."
            if user_manager.unassign_realm(user_id, realm_name):
                refresh_session_state_user(session_state, user_manager, user_id)
                return f"unassign-realm > Realm {realm_name} removed from {target.display_name}."
            return f"unassign-realm > {target.display_name} does not have realm {realm_name}."

        if resolved["status"] == "approved":
            memory.write_memory(
                proposal_id=resolved["proposal_id"],
                session_id=payload["session_id"],
                summary_lines=payload["summary_lines"],
                approved_at=resolved["resolved_at"],
                realm_name=active_realm.name if active_realm else "",
                user_id=str(payload.get("user_id", "")),
            )
            return (
                f"Approved {resolved['proposal_id']} and wrote a memory record for the next session."
            )

        return f"Rejected {resolved['proposal_id']}."

    if constitutional_filter is not None:
        filter_result = constitutional_filter.check_with_logging(
            text=normalized,
            audit_dir=resolve_nammu_dir(session, nammu_dir),
            session_id=session.session_id,
            operator_profile=(
                session_state.get("nammu_profile")
                if isinstance(session_state, dict)
                else None
            ),
        )
        if filter_result.blocked:
            append_governance_event(
                resolve_nammu_dir(session, nammu_dir),
                session.session_id,
                "block_constitutional",
                filter_result.reason,
                normalized[:80],
            )
            return f"inanna> {filter_result.to_crown_response()}"

    plan = orchestration_engine.detect_orchestration(normalized)
    if plan is not None:
        append_routing_decision(
            routing_log,
            session,
            "orchestration",
            normalized,
            nammu_dir=nammu_dir,
        )
        append_governance_event(
            resolve_nammu_dir(session, nammu_dir),
            session.session_id,
            "propose",
            "Multi-Faculty orchestration requires approval before execution.",
            normalized[:60],
        )
        created = create_orchestration_proposal(
            proposal=proposal,
            session=session,
            user_input=normalized,
            plan=plan,
        )
        return (
            f"orchestration > proposal required: {plan.describe_steps()}\n"
            f"{created['line']}"
        )

    nammu_profile = (
        session_state.get("nammu_profile")
        if isinstance(session_state, dict)
        else None
    )
    nammu_action = build_nammu_tool_action(
        nammu_first_routing(
            normalized,
            session.events,
            operator_profile=nammu_profile,
        ),
        filesystem_faculty,
    )
    nammu_tool_name = str(nammu_action.get("tool", "")) if nammu_action is not None else ""
    if isinstance(session_state, dict):
        session_state["last_nammu_input"] = normalized
        session_state["last_nammu_route"] = nammu_tool_name or "unknown"

    calendar_action = nammu_action if nammu_tool_name in CALENDAR_TOOL_NAMES else detect_calendar_tool_action(
        normalized,
        calendar_workflows,
    )
    communication_action = (
        nammu_action
        if nammu_tool_name in COMMUNICATION_TOOL_NAMES
        else detect_communication_tool_action(
        normalized,
        communication_workflows,
        session.events,
    ))
    email_action = nammu_action if nammu_tool_name in EMAIL_TOOL_NAMES else detect_email_tool_action(
        normalized,
        email_workflows,
        session.events,
    )
    if calendar_action is not None:
        append_routing_decision(
            routing_log,
            session,
            "operator",
            normalized,
            nammu_dir=nammu_dir,
        )
        append_governance_event(
            resolve_nammu_dir(session, nammu_dir),
            session.session_id,
            "tool",
            str(calendar_action.get("reason", "Governed calendar workflow use.")),
            normalized[:60],
        )
        return complete_tool_resolution(
            {
                "payload": {
                    "original_input": normalized,
                    "query": str(calendar_action["query"]),
                    "tool": str(calendar_action["tool"]),
                    "params": dict(calendar_action.get("params", {})),
                }
            },
            "approve",
            session,
            proposal,
            memory,
            engine,
            startup_context,
            operator or OperatorFaculty(),
            guardian_metrics,
            active_token=active_token,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            calendar_workflows=calendar_workflows,
            filesystem_faculty=filesystem_faculty,
            process_faculty=process_faculty,
            package_faculty=package_faculty,
            desktop_faculty=desktop_faculty,
            communication_workflows=communication_workflows,
            email_workflows=email_workflows,
            session_audit=session_audit,
            active_realm_name=active_realm_name,
            conversation_state=conversation_state,
            reflective_memory=reflective_memory,
            nammu_dir=nammu_dir,
            nammu_profile=(
                session_state.get("nammu_profile")
                if isinstance(session_state, dict)
                else None
            ),
        )

    if email_action is not None:
        append_routing_decision(
            routing_log,
            session,
            "operator",
            normalized,
            nammu_dir=nammu_dir,
        )
        append_governance_event(
            resolve_nammu_dir(session, nammu_dir),
            session.session_id,
            "tool",
            str(email_action.get("reason", "Governed email workflow use.")),
            normalized[:60],
        )
        if bool(email_action.get("requires_proposal", False)):
            params = dict(email_action.get("params", {}))
            created = create_email_send_proposal(
                proposal=proposal,
                session=session,
                user_input=normalized,
                app=str(params.get("app", "")),
                recipient=str(params.get("to", "")),
                subject=str(params.get("subject", "")),
                body=str(params.get("body", "")),
                subject_or_sender=str(params.get("subject_or_sender", "")),
                stage="draft",
                workflow=str(email_action.get("tool", "email_compose")),
            )
            return (
                f"operator > {created['prompt_text']}\n"
                'Type "approve" to compose the draft or "reject" to cancel.\n'
                f"{created['tool_line']}"
            )
        return complete_tool_resolution(
            {
                "payload": {
                    "original_input": normalized,
                    "query": str(email_action["query"]),
                    "tool": str(email_action["tool"]),
                    "params": dict(email_action.get("params", {})),
                }
            },
            "approve",
            session,
            proposal,
            memory,
            engine,
            startup_context,
            operator or OperatorFaculty(),
            guardian_metrics,
            active_token=active_token,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            filesystem_faculty=filesystem_faculty,
            process_faculty=process_faculty,
            package_faculty=package_faculty,
            desktop_faculty=desktop_faculty,
            communication_workflows=communication_workflows,
            email_workflows=email_workflows,
            session_audit=session_audit,
            active_realm_name=active_realm_name,
            conversation_state=conversation_state,
            reflective_memory=reflective_memory,
            nammu_dir=nammu_dir,
            nammu_profile=(
                session_state.get("nammu_profile")
                if isinstance(session_state, dict)
                else None
            ),
        )

    if communication_action is not None:
        append_routing_decision(
            routing_log,
            session,
            "operator",
            normalized,
            nammu_dir=nammu_dir,
        )
        append_governance_event(
            resolve_nammu_dir(session, nammu_dir),
            session.session_id,
            "tool",
            str(communication_action.get("reason", "Governed communication workflow use.")),
            normalized[:60],
        )
        if bool(communication_action.get("requires_proposal", False)):
            params = dict(communication_action.get("params", {}))
            created = create_communication_send_proposal(
                proposal=proposal,
                session=session,
                user_input=normalized,
                app=str(params.get("app", "")),
                contact=str(params.get("contact", "")),
                message=str(params.get("message", "")),
                stage="draft",
            )
            return (
                f"operator > {created['prompt_text']}\n"
                'Type "approve" to type the draft or "reject" to cancel.\n'
                f"{created['tool_line']}"
            )
        return complete_tool_resolution(
            {
                "payload": {
                    "original_input": normalized,
                    "query": str(communication_action["query"]),
                    "tool": str(communication_action["tool"]),
                    "params": dict(communication_action.get("params", {})),
                }
            },
            "approve",
            session,
            proposal,
            memory,
            engine,
            startup_context,
            operator or OperatorFaculty(),
            guardian_metrics,
            active_token=active_token,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            filesystem_faculty=filesystem_faculty,
            process_faculty=process_faculty,
            package_faculty=package_faculty,
            desktop_faculty=desktop_faculty,
            communication_workflows=communication_workflows,
            email_workflows=email_workflows,
            session_audit=session_audit,
            active_realm_name=active_realm_name,
            conversation_state=conversation_state,
            reflective_memory=reflective_memory,
            nammu_dir=nammu_dir,
            nammu_profile=(
                session_state.get("nammu_profile")
                if isinstance(session_state, dict)
                else None
            ),
        )

    desktop_action = nammu_action if nammu_tool_name in DESKTOP_TOOL_NAMES else detect_desktop_tool_action(
        normalized,
        desktop_faculty,
    )
    if desktop_action is not None:
        append_routing_decision(
            routing_log,
            session,
            "operator",
            normalized,
            nammu_dir=nammu_dir,
        )
        append_governance_event(
            resolve_nammu_dir(session, nammu_dir),
            session.session_id,
            "tool",
            str(desktop_action.get("reason", "Governed desktop tool use.")),
            normalized[:60],
        )
        if bool(desktop_action.get("requires_proposal", False)):
            created = create_tool_use_proposal(
                proposal=proposal,
                session=session,
                user_input=normalized,
                tool=str(desktop_action["tool"]),
                query=str(desktop_action["query"]),
                params=dict(desktop_action.get("params", {})),
            )
            return (
                f'operator > tool proposed: {desktop_action["tool"]} - "{desktop_action["query"]}"\n'
                'Type "approve" to execute or "reject" to cancel.\n'
                f"{created['tool_line']}"
            )
        return complete_tool_resolution(
            {
                "payload": {
                    "original_input": normalized,
                    "query": str(desktop_action["query"]),
                    "tool": str(desktop_action["tool"]),
                    "params": dict(desktop_action.get("params", {})),
                }
            },
            "approve",
            session,
            proposal,
            memory,
            engine,
            startup_context,
            operator or OperatorFaculty(),
            guardian_metrics,
            active_token=active_token,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            filesystem_faculty=filesystem_faculty,
            process_faculty=process_faculty,
            package_faculty=package_faculty,
            desktop_faculty=desktop_faculty,
            communication_workflows=communication_workflows,
            email_workflows=email_workflows,
            session_audit=session_audit,
            active_realm_name=active_realm_name,
            conversation_state=conversation_state,
            reflective_memory=reflective_memory,
            nammu_dir=nammu_dir,
            nammu_profile=(
                session_state.get("nammu_profile")
                if isinstance(session_state, dict)
                else None
            ),
        )

    browser_action = nammu_action if nammu_tool_name in BROWSER_TOOL_NAMES else detect_browser_tool_action(
        normalized,
        browser_workflows,
    )
    if browser_action is not None:
        append_routing_decision(
            routing_log,
            session,
            "operator",
            normalized,
            nammu_dir=nammu_dir,
        )
        append_governance_event(
            resolve_nammu_dir(session, nammu_dir),
            session.session_id,
            "tool",
            str(browser_action.get("reason", "Governed browser workflow use.")),
            normalized[:60],
        )
        if bool(browser_action.get("requires_proposal", False)):
            created = create_tool_use_proposal(
                proposal=proposal,
                session=session,
                user_input=normalized,
                tool=str(browser_action["tool"]),
                query=str(browser_action["query"]),
                params=dict(browser_action.get("params", {})),
            )
            return (
                f'operator > tool proposed: {browser_action["tool"]} - "{browser_action["query"]}"\n'
                'Type "approve" to execute or "reject" to cancel.\n'
                f"{created['tool_line']}"
            )
        return complete_tool_resolution(
            {
                "payload": {
                    "original_input": normalized,
                    "query": str(browser_action["query"]),
                    "tool": str(browser_action["tool"]),
                    "params": dict(browser_action.get("params", {})),
                }
            },
            "approve",
            session,
            proposal,
            memory,
            engine,
            startup_context,
            operator or OperatorFaculty(),
            guardian_metrics,
            active_token=active_token,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            browser_workflows=browser_workflows,
            document_workflows=document_workflows,
            filesystem_faculty=filesystem_faculty,
            process_faculty=process_faculty,
            package_faculty=package_faculty,
            desktop_faculty=desktop_faculty,
            communication_workflows=communication_workflows,
            email_workflows=email_workflows,
            session_audit=session_audit,
            active_realm_name=active_realm_name,
            conversation_state=conversation_state,
            reflective_memory=reflective_memory,
            nammu_dir=nammu_dir,
            nammu_profile=(
                session_state.get("nammu_profile")
                if isinstance(session_state, dict)
                else None
            ),
        )

    document_action = nammu_action if nammu_tool_name in DOCUMENT_TOOL_NAMES else detect_document_tool_action(
        normalized,
        document_workflows,
    )
    if document_action is not None:
        append_routing_decision(
            routing_log,
            session,
            "operator",
            normalized,
            nammu_dir=nammu_dir,
        )
        append_governance_event(
            resolve_nammu_dir(session, nammu_dir),
            session.session_id,
            "tool",
            str(document_action.get("reason", "Governed document workflow use.")),
            normalized[:60],
        )
        if bool(document_action.get("requires_proposal", False)):
            created = create_tool_use_proposal(
                proposal=proposal,
                session=session,
                user_input=normalized,
                tool=str(document_action["tool"]),
                query=str(document_action["query"]),
                params=dict(document_action.get("params", {})),
            )
            return (
                f'operator > tool proposed: {document_action["tool"]} - "{document_action["query"]}"\n'
                'Type "approve" to execute or "reject" to cancel.\n'
                f"{created['tool_line']}"
            )
        return complete_tool_resolution(
            {
                "payload": {
                    "original_input": normalized,
                    "query": str(document_action["query"]),
                    "tool": str(document_action["tool"]),
                    "params": dict(document_action.get("params", {})),
                }
            },
            "approve",
            session,
            proposal,
            memory,
            engine,
            startup_context,
            operator or OperatorFaculty(),
            guardian_metrics,
            active_token=active_token,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            document_workflows=document_workflows,
            filesystem_faculty=filesystem_faculty,
            process_faculty=process_faculty,
            package_faculty=package_faculty,
            desktop_faculty=desktop_faculty,
            communication_workflows=communication_workflows,
            email_workflows=email_workflows,
            session_audit=session_audit,
            active_realm_name=active_realm_name,
            conversation_state=conversation_state,
            reflective_memory=reflective_memory,
            nammu_dir=nammu_dir,
            nammu_profile=(
                session_state.get("nammu_profile")
                if isinstance(session_state, dict)
                else None
            ),
        )

    filesystem_action = nammu_action if nammu_tool_name in FILESYSTEM_TOOL_NAMES else detect_filesystem_tool_action(
        normalized,
        filesystem_faculty,
        profile_manager=profile_manager,
        current_user=current_user,
        active_token=active_token,
    )
    if filesystem_action is not None:
        append_routing_decision(
            routing_log,
            session,
            "operator",
            normalized,
            nammu_dir=nammu_dir,
        )
        append_governance_event(
            resolve_nammu_dir(session, nammu_dir),
            session.session_id,
            "tool",
            str(filesystem_action.get("reason", "Governed file system tool use.")),
            normalized[:60],
        )
        if bool(filesystem_action.get("requires_proposal", False)):
            created = create_tool_use_proposal(
                proposal=proposal,
                session=session,
                user_input=normalized,
                tool=str(filesystem_action["tool"]),
                query=str(filesystem_action["query"]),
                params=dict(filesystem_action.get("params", {})),
            )
            return (
                f'operator > tool proposed: {filesystem_action["tool"]} - "{filesystem_action["query"]}"\n'
                'Type "approve" to execute or "reject" to cancel.\n'
                f"{created['tool_line']}"
            )
        return complete_tool_resolution(
            {
                "payload": {
                    "original_input": normalized,
                    "query": str(filesystem_action["query"]),
                    "tool": str(filesystem_action["tool"]),
                    "params": dict(filesystem_action.get("params", {})),
                }
            },
            "approve",
            session,
            proposal,
            memory,
            engine,
            startup_context,
            operator or OperatorFaculty(),
            guardian_metrics,
            active_token=active_token,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            filesystem_faculty=filesystem_faculty,
            process_faculty=process_faculty,
            package_faculty=package_faculty,
            desktop_faculty=desktop_faculty,
            communication_workflows=communication_workflows,
            email_workflows=email_workflows,
            session_audit=session_audit,
            active_realm_name=active_realm_name,
            conversation_state=conversation_state,
            reflective_memory=reflective_memory,
            nammu_dir=nammu_dir,
            nammu_profile=(
                session_state.get("nammu_profile")
                if isinstance(session_state, dict)
                else None
            ),
        )

    process_action = nammu_action if nammu_tool_name in PROCESS_TOOL_NAMES else detect_process_tool_action(
        normalized,
        process_faculty,
    )
    if process_action is not None:
        append_routing_decision(
            routing_log,
            session,
            "operator",
            normalized,
            nammu_dir=nammu_dir,
        )
        append_governance_event(
            resolve_nammu_dir(session, nammu_dir),
            session.session_id,
            "tool",
            str(process_action.get("reason", "Governed process tool use.")),
            normalized[:60],
        )
        if bool(process_action.get("requires_proposal", False)):
            created = create_tool_use_proposal(
                proposal=proposal,
                session=session,
                user_input=normalized,
                tool=str(process_action["tool"]),
                query=str(process_action["query"]),
                params=dict(process_action.get("params", {})),
            )
            return (
                f'operator > tool proposed: {process_action["tool"]} - "{process_action["query"]}"\n'
                'Type "approve" to execute or "reject" to cancel.\n'
                f"{created['tool_line']}"
            )
        return complete_tool_resolution(
            {
                "payload": {
                    "original_input": normalized,
                    "query": str(process_action["query"]),
                    "tool": str(process_action["tool"]),
                    "params": dict(process_action.get("params", {})),
                }
            },
            "approve",
            session,
            proposal,
            memory,
            engine,
            startup_context,
            operator or OperatorFaculty(),
            guardian_metrics,
            active_token=active_token,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            filesystem_faculty=filesystem_faculty,
            process_faculty=process_faculty,
            package_faculty=package_faculty,
            desktop_faculty=desktop_faculty,
            communication_workflows=communication_workflows,
            email_workflows=email_workflows,
            session_audit=session_audit,
            active_realm_name=active_realm_name,
            conversation_state=conversation_state,
            reflective_memory=reflective_memory,
            nammu_dir=nammu_dir,
            nammu_profile=(
                session_state.get("nammu_profile")
                if isinstance(session_state, dict)
                else None
            ),
        )

    package_action = nammu_action if nammu_tool_name in PACKAGE_TOOL_NAMES else detect_package_tool_action(
        normalized,
        package_faculty,
    )
    if package_action is not None:
        append_routing_decision(
            routing_log,
            session,
            "operator",
            normalized,
            nammu_dir=nammu_dir,
        )
        append_governance_event(
            resolve_nammu_dir(session, nammu_dir),
            session.session_id,
            "tool",
            str(package_action.get("reason", "Governed package tool use.")),
            normalized[:60],
        )
        if bool(package_action.get("requires_proposal", False)):
            created = create_tool_use_proposal(
                proposal=proposal,
                session=session,
                user_input=normalized,
                tool=str(package_action["tool"]),
                query=str(package_action["query"]),
                params=dict(package_action.get("params", {})),
            )
            return (
                f'operator > tool proposed: {package_action["tool"]} - "{package_action["query"]}"\n'
                'Type "approve" to execute or "reject" to cancel.\n'
                f"{created['tool_line']}"
            )
        return complete_tool_resolution(
            {
                "payload": {
                    "original_input": normalized,
                    "query": str(package_action["query"]),
                    "tool": str(package_action["tool"]),
                    "params": dict(package_action.get("params", {})),
                }
            },
            "approve",
            session,
            proposal,
            memory,
            engine,
            startup_context,
            operator or OperatorFaculty(),
            guardian_metrics,
            active_token=active_token,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            filesystem_faculty=filesystem_faculty,
            process_faculty=process_faculty,
            package_faculty=package_faculty,
            desktop_faculty=desktop_faculty,
            communication_workflows=communication_workflows,
            session_audit=session_audit,
            active_realm_name=active_realm_name,
            conversation_state=conversation_state,
            reflective_memory=reflective_memory,
            nammu_dir=nammu_dir,
            nammu_profile=(
                session_state.get("nammu_profile")
                if isinstance(session_state, dict)
                else None
            ),
        )

    generic_nammu_action = (
        nammu_action
        if nammu_tool_name in NETWORK_TOOL_NAMES or nammu_tool_name == "web_search"
        else None
    )
    if generic_nammu_action is not None:
        append_routing_decision(
            routing_log,
            session,
            "operator",
            normalized,
            nammu_dir=nammu_dir,
        )
        append_governance_event(
            resolve_nammu_dir(session, nammu_dir),
            session.session_id,
            "tool",
            str(generic_nammu_action.get("reason", "Governed NAMMU tool use.")),
            normalized[:60],
        )
        if bool(generic_nammu_action.get("requires_proposal", False)):
            created = create_tool_use_proposal(
                proposal=proposal,
                session=session,
                user_input=normalized,
                tool=str(generic_nammu_action["tool"]),
                query=str(generic_nammu_action["query"]),
                params=dict(generic_nammu_action.get("params", {})),
            )
            return (
                f'operator > tool proposed: {generic_nammu_action["tool"]} - "{generic_nammu_action["query"]}"\n'
                'Type "approve" to execute or "reject" to cancel.\n'
                f"{created['tool_line']}"
            )
        return complete_tool_resolution(
            {
                "payload": {
                    "original_input": normalized,
                    "query": str(generic_nammu_action["query"]),
                    "tool": str(generic_nammu_action["tool"]),
                    "params": dict(generic_nammu_action.get("params", {})),
                }
            },
            "approve",
            session,
            proposal,
            memory,
            engine,
            startup_context,
            operator or OperatorFaculty(),
            guardian_metrics,
            active_token=active_token,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            filesystem_faculty=filesystem_faculty,
            process_faculty=process_faculty,
            package_faculty=package_faculty,
            desktop_faculty=desktop_faculty,
            communication_workflows=communication_workflows,
            email_workflows=email_workflows,
            session_audit=session_audit,
            active_realm_name=active_realm_name,
            conversation_state=conversation_state,
            reflective_memory=reflective_memory,
        )

    governance_result = classifier.route(normalized)
    if governance_result.faculty == "sentinel":
        append_audit_event(
            session_audit,
            "routing",
            "sentinel: routed to SENTINEL Faculty - input classified as security domain",
            {"route": "sentinel", "input_preview": normalized[:60]},
        )
    append_routing_decision(
        routing_log,
        session,
        governance_result.faculty,
        normalized,
        nammu_dir=nammu_dir,
    )
    append_governance_decision(session, governance_result, normalized, nammu_dir=nammu_dir)

    if governance_result.decision == "block":
        guardian_metrics["governance_blocks"] += 1
        return f"governance > blocked: {governance_result.reason}"

    if governance_result.decision == "propose":
        created = create_memory_request_proposal(
            proposal=proposal,
            session=session,
            user_input=normalized,
            reason=governance_result.reason,
            user_id=memory_scope_user_id(current_user, user_manager) or "",
        )
        return (
            f"governance > proposal required: {governance_result.reason}\n"
            f"{created['line']}"
        )

    if governance_result.suggests_tool:
        proposed_tool = governance_result.proposed_tool
        tool_query = governance_result.tool_query or normalized
        persistent_trusted_tools: list[str] = []
        if (
            operator is not None
            and profile_manager is not None
            and current_user is not None
            and active_token is not None
        ):
            profile = profile_manager.load(current_user.user_id)
            if profile is not None:
                persistent_trusted_tools = profile.persistent_trusted_tools
        if operator is not None and operator.should_skip_proposal(
            proposed_tool,
            persistent_trusted_tools,
        ):
            if current_user is not None:
                append_audit_event(
                    session_audit,
                    "tool_executed_trusted",
                    (
                        f"{current_user.display_name} executed trusted tool "
                        f"{proposed_tool} without proposal"
                    ),
                    {
                        "tool": proposed_tool,
                        "query": tool_query,
                        "user_id": current_user.user_id,
                    },
                )
            return complete_tool_resolution(
                {
                    "payload": {
                        "original_input": normalized,
                        "query": tool_query,
                        "tool": proposed_tool,
                        "params": {"query": tool_query},
                    }
                },
                "approve",
                session,
                proposal,
                memory,
                engine,
                startup_context,
                operator,
                guardian_metrics,
                active_token=active_token,
                user_log=user_log,
                faculty_monitor=faculty_monitor,
                filesystem_faculty=filesystem_faculty,
                process_faculty=process_faculty,
                package_faculty=package_faculty,
                desktop_faculty=desktop_faculty,
                communication_workflows=communication_workflows,
                email_workflows=email_workflows,
                session_audit=session_audit,
                active_realm_name=active_realm_name,
                conversation_state=conversation_state,
                reflective_memory=reflective_memory,
                nammu_dir=nammu_dir,
                nammu_profile=(
                    session_state.get("nammu_profile")
                    if isinstance(session_state, dict)
                    else None
                ),
            )
        created = create_tool_use_proposal(
            proposal=proposal,
            session=session,
            user_input=normalized,
            tool=proposed_tool,
            query=tool_query,
            params={"query": tool_query},
        )
        return (
            f'operator > tool proposed: {proposed_tool} - "{tool_query}"\n'
            'Type "approve" to execute or "reject" to cancel.\n'
            f"{created['tool_line']}"
        )

    if governance_result.faculty == "analyst":
        t0 = time.monotonic()
        analysis_mode, analysis_text = analyst.analyse(
            question=normalized,
            context=startup_context_items(startup_context),
        )
        if faculty_monitor is not None:
            faculty_monitor.record_call("analyst", (time.monotonic() - t0) * 1000, True)
        session.add_event("user", normalized)
        session.add_event("analyst", analysis_text)
        append_user_log_entry(user_log, active_token, session.session_id, normalized, analysis_text)
        record_completed_turn(
            conversation_state=conversation_state,
            memory=memory,
            session=session,
            active_realm_name=active_realm_name,
            active_token=active_token,
            user_log=user_log,
            session_audit=session_audit,
        )
        label = "[live analysis]" if analysis_mode == "live" else "[analysis fallback]"
        lines = [f"nammu > routing to {governance_result.faculty} faculty"]
        if governance_result.decision == "redirect":
            lines.append(f"governance > redirected: {governance_result.reason}")
        lines.append(f"analyst > {label} {analysis_text}")
        return (
            "\n".join(lines)
        )

    if governance_result.faculty == "sentinel":
        t0 = time.monotonic()
        sentinel_text = run_sentinel_response(
            user_input=normalized,
            grounding=startup_context_items(startup_context),
            lm_url=config.model_url,
            model_name=config.model_name,
            faculties_path=FACULTIES_CONFIG_PATH,
            grounding_prefix=build_grounding_prefix(profile_manager, current_user, active_token),
        )
        mode = sentinel_response_mode(sentinel_text)
        if faculty_monitor is not None:
            faculty_monitor.record_call(
                "sentinel",
                (time.monotonic() - t0) * 1000,
                mode == "connected",
            )
            faculty_monitor.set_mode("sentinel", mode)
        session.add_event("user", normalized)
        session.add_event("assistant", sentinel_text)
        append_user_log_entry(user_log, active_token, session.session_id, normalized, sentinel_text)
        record_completed_turn(
            conversation_state=conversation_state,
            memory=memory,
            session=session,
            active_realm_name=active_realm_name,
            active_token=active_token,
            user_log=user_log,
            session_audit=session_audit,
        )
        lines = [f"nammu > routing to {governance_result.faculty} faculty"]
        if governance_result.decision == "redirect":
            lines.append(f"governance > redirected: {governance_result.reason}")
        lines.append(f"sentinel > {sentinel_text}")
        return "\n".join(lines)

    session.add_event("user", normalized)
    t0 = time.monotonic()
    assistant_text = engine.respond(
        context_summary=startup_context_items(startup_context),
        conversation=session.events,
    )
    if faculty_monitor is not None:
        faculty_monitor.record_call("crown", (time.monotonic() - t0) * 1000, True)
    assistant_text, reflection_proposal = maybe_capture_reflection_proposal(
        assistant_text,
        proposal,
        session,
        reflective_memory,
    )
    session.add_event("assistant", assistant_text)
    append_user_log_entry(user_log, active_token, session.session_id, normalized, assistant_text)
    record_completed_turn(
        conversation_state=conversation_state,
        memory=memory,
        session=session,
        active_realm_name=active_realm_name,
        active_token=active_token,
        user_log=user_log,
        session_audit=session_audit,
    )
    lines = [f"nammu > routing to {governance_result.faculty} faculty"]
    if governance_result.decision == "redirect":
        lines.append(f"governance > redirected: {governance_result.reason}")
    lines.append(f"inanna > {assistant_text}")
    if reflection_proposal is not None:
        lines.append(reflection_proposal["line"])
    return "\n".join(lines)


def main() -> None:
    global SESSION_DIR, MEMORY_DIR, PROPOSAL_DIR, NAMMU_DIR

    realm_manager, active_realm, realm_dirs, migrated = initialize_realm_context(DATA_ROOT)
    SESSION_DIR = realm_dirs["sessions"]
    MEMORY_DIR = realm_dirs["memory"]
    PROPOSAL_DIR = realm_dirs["proposals"]
    NAMMU_DIR = realm_dirs["nammu"]
    ensure_directories()

    config = Config.from_env()
    memory = Memory(session_dir=SESSION_DIR, memory_dir=MEMORY_DIR)
    proposal = Proposal(proposal_dir=PROPOSAL_DIR)
    state_report = StateReport()
    user_manager = UserManager(data_root=DATA_ROOT, roles_config_path=ROLES_CONFIG_PATH)
    guardian_user = ensure_guardian_exists(user_manager)
    profile_manager = ProfileManager(PROFILES_DIR)
    reflective_memory = ReflectiveMemory(SELF_DIR)
    expired_invites = user_manager.expire_old_invites()
    token_store = TokenStore()
    guardian_token = token_store.issue(
        guardian_user.user_id,
        guardian_user.display_name,
        guardian_user.role,
    )
    ensure_guardian_profile_completed(profile_manager, guardian_user.user_id)
    nammu_profile = ensure_nammu_profile_for_user(
        profile_manager,
        NAMMU_DIR,
        guardian_user.user_id,
    )
    user_log = UserLog(USER_LOG_DIR)
    faculty_monitor = FacultyMonitor()
    session_audit: list[dict[str, str]] = []
    process_monitor = ProcessMonitor(time.time())
    conversation_state = {"turn_count": 0, "last_auto_memory_turn": 0}
    append_audit_event(
        session_audit,
        "login",
        f"{guardian_user.display_name} ({guardian_user.role}) logged in",
    )
    session_state: dict[str, object | None] = {
        "active_user": guardian_user,
        "original_user": None,
        "guardian_user": guardian_user,
        "active_token": guardian_token,
        "original_token": None,
        "guardian_token": guardian_token,
        "onboarding_active": False,
        "onboarding_step": 0,
        "onboarding_responses": {},
        "nammu_profile": nammu_profile,
        "last_nammu_input": "",
        "last_nammu_route": "unknown",
        "session_correction_count": 0,
    }
    engine = Engine(
        model_url=config.model_url,
        model_name=config.model_name,
        api_key=config.api_key,
        realm=active_realm,
    )
    analyst = AnalystFaculty(
        model_url=config.model_url,
        model_name=config.model_name,
        api_key=config.api_key,
        realm=active_realm,
    )
    guardian = GuardianFaculty()
    operator = OperatorFaculty()
    filesystem_faculty = FileSystemFaculty()
    process_faculty = ProcessFaculty()
    package_faculty = PackageFaculty()
    desktop_faculty = DesktopFaculty()
    calendar_workflows = CalendarWorkflows()
    browser_workflows = BrowserWorkflows(desktop_faculty)
    document_workflows = DocumentWorkflows(desktop_faculty)
    communication_workflows = CommunicationWorkflows(desktop_faculty)
    email_workflows = EmailWorkflows(desktop_faculty)
    constitutional_filter = ConstitutionalFilter(engine=engine)
    governance = GovernanceLayer(engine=engine)
    sync_profile_grounding(engine, profile_manager, guardian_user, guardian_token, reflective_memory)
    classifier = IntentClassifier(
        engine,
        governance=governance,
        faculties_path=FACULTIES_CONFIG_PATH,
    )
    orchestration_engine = OrchestrationEngine(FACULTIES_CONFIG_PATH)
    routing_log: list[dict[str, str]] = []
    guardian_metrics = {"governance_blocks": 0, "tool_executions": 0}

    if migrated:
        print(f"Migrated {migrated} files to default realm.")
    if expired_invites:
        print(f"Expired {expired_invites} invite(s).")

    if engine.verify_connection():
        print(f"Model connected: {config.model_name} at {config.model_url}")
    else:
        print("Model unreachable — fallback mode active. Set INANNA_MODEL_URL to connect.")

    analyst.fallback_mode = engine.fallback_mode
    analyst._connected = engine._connected
    faculty_monitor.update_model_mode(engine.mode)

    startup_context = memory.load_startup_context()
    session = Session.create(
        session_dir=SESSION_DIR,
        context_summary=startup_context["summary_lines"],
    )

    print(f"Phase: {phase_banner()}")
    print(f"Realm: {active_realm.name}")
    print(f"User: {guardian_user.display_name} ({guardian_user.role})")
    print(f"Auto-login: {guardian_user.display_name} ({guardian_user.role}) | session active")
    print(f"Session ID: {session.session_id}")
    print_startup_context(startup_context["summary_lines"])
    print(startup_commands_line())
    for line in build_realm_access_warning_lines(
        session_state.get("active_user"),
        active_realm.name,
    ):
        print(line)
    for message in begin_onboarding_if_needed(
        session_state,
        profile_manager,
        guardian_user,
        guardian_token,
    ):
        print(f"onboarding > {message}")

    while True:
        try:
            user_input = input("you> ")
        except EOFError:
            observe_session_communication(
                profile_manager,
                session_state.get("active_token"),
                session,
                routing_log,
            )
            finalize_auto_memory(
                conversation_state=conversation_state,
                memory=memory,
                session=session,
                active_realm_name=active_realm.name,
                active_token=session_state.get("active_token"),
                user_log=user_log,
                reason="session end",
                session_audit=session_audit,
            )
            print()
            print("Session closed.")
            break
        except KeyboardInterrupt:
            observe_session_communication(
                profile_manager,
                session_state.get("active_token"),
                session,
                routing_log,
            )
            finalize_auto_memory(
                conversation_state=conversation_state,
                memory=memory,
                session=session,
                active_realm_name=active_realm.name,
                active_token=session_state.get("active_token"),
                user_log=user_log,
                reason="session end",
                session_audit=session_audit,
            )
            print()
            print("Session closed.")
            break

        result = handle_command(
            command=user_input,
            session=session,
            memory=memory,
            proposal=proposal,
            state_report=state_report,
            engine=engine,
            analyst=analyst,
            classifier=classifier,
            routing_log=routing_log,
            startup_context=startup_context,
            config=config,
            operator=operator,
            calendar_workflows=calendar_workflows,
            browser_workflows=browser_workflows,
            document_workflows=document_workflows,
            filesystem_faculty=filesystem_faculty,
            process_faculty=process_faculty,
            package_faculty=package_faculty,
            desktop_faculty=desktop_faculty,
            communication_workflows=communication_workflows,
            email_workflows=email_workflows,
            guardian=guardian,
            guardian_metrics=guardian_metrics,
            nammu_dir=NAMMU_DIR,
            realm_manager=realm_manager,
            active_realm=active_realm,
            user_manager=user_manager,
            session_state=session_state,
            token_store=token_store,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            session_audit=session_audit,
            process_monitor=process_monitor,
            conversation_state=conversation_state,
            orchestration_engine=orchestration_engine,
            profile_manager=profile_manager,
            reflective_memory=reflective_memory,
            constitutional_filter=constitutional_filter,
        )
        if result is None:
            observe_session_communication(
                profile_manager,
                session_state.get("active_token"),
                session,
                routing_log,
            )
            finalize_auto_memory(
                conversation_state=conversation_state,
                memory=memory,
                session=session,
                active_realm_name=active_realm.name,
                active_token=session_state.get("active_token"),
                user_log=user_log,
                reason="session end",
                session_audit=session_audit,
            )
            print("Session closed.")
            break
        if result:
            print(result)


if __name__ == "__main__":
    main()
