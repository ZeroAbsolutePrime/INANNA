from __future__ import annotations

import json
import os
import time
from dataclasses import MISSING
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv

from config import Config
from core.body import BodyInspector, BodyReport
from core.faculty_monitor import FacultyMonitor
from core.governance import GovernanceLayer
from core.guardian import GuardianFaculty
from core.memory import Memory
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
from core.profile import (
    CommunicationObserver,
    NotificationStore,
    ProfileManager,
    UserProfile,
    utc_now,
)
from core.process_monitor import ProcessMonitor
from core.proposal import Proposal
from core.realm import DEFAULT_REALM, RealmConfig, RealmManager
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
STARTUP_COMMANDS = (
    "users",
    "create-user",
    "login",
    "logout",
    "whoami",
    "my-profile",
    "view-profile",
    "my-departments",
    "assign-department",
    "unassign-department",
    "assign-group",
    "unassign-group",
    "notify-department",
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
)
AUTO_MEMORY_TURN_THRESHOLD = 20
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


def get_active_realm_name() -> str:
    realm_name = os.getenv("INANNA_REALM", DEFAULT_REALM).strip()
    return realm_name or DEFAULT_REALM


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
    user_id, fallback = profile_subject(active_user, active_token)
    if not user_id:
        return ""
    if profile_manager is None:
        display_name = fallback.strip()
    else:
        display_name = profile_manager.display_name_for(user_id, fallback=fallback).strip()
    if not display_name:
        return ""
    return f"You are speaking with {display_name}."


def sync_profile_grounding(
    engine: Engine | None,
    profile_manager: ProfileManager | None,
    active_user: UserRecord | None,
    active_token: SessionToken | None,
) -> None:
    if engine is None:
        return
    engine.grounding_prefix = build_grounding_prefix(
        profile_manager,
        active_user,
        active_token,
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


def parse_profile_edit_command(command: str) -> tuple[str, str] | None:
    parts = command.strip().split(maxsplit=3)
    if len(parts) != 4:
        return None
    if parts[0].lower() != "my-profile" or parts[1].lower() != "edit":
        return None
    field_name = parts[2].strip()
    value = parts[3].strip()
    if not field_name or not value:
        return None
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
    sync_profile_grounding(engine, profile_manager, active_user, active_token)
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
) -> dict:
    created = proposal.create(
        what=f"{tool} tool use",
        why="User requested information or connectivity that requires approved tool use.",
        payload={
            "action": "tool_use",
            "tool": tool,
            "query": query,
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


def build_tool_result_text(result: ToolResult) -> str:
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
    return {
        "tool": result.tool,
        "query": result.query,
        "success": result.success,
        "data": dict(result.data),
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
    session_audit: list[dict[str, object]] | None = None,
    active_realm_name: str = "",
    conversation_state: dict[str, int] | None = None,
) -> str:
    payload = resolved["payload"]
    original_input = payload.get("original_input", "")
    query = payload.get("query", "")
    tool = payload.get("tool", "")

    session.add_event("user", original_input)

    if decision == "approve":
        guardian_metrics["tool_executions"] += 1
        t0 = time.monotonic()
        result = operator.execute(tool, {"query": query})
        if faculty_monitor is not None:
            faculty_monitor.record_call("operator", (time.monotonic() - t0) * 1000, result.success)
        audit_entry = build_network_audit_entry(result)
        if audit_entry is not None:
            append_audit_event(
                session_audit,
                "tool_use",
                str(audit_entry["summary"]),
                {key: value for key, value in audit_entry.items() if key != "summary"},
            )
        operator_text = build_tool_result_text(result)
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
        operator_text = "tool use rejected. Proceeding without tool execution."
        t0 = time.monotonic()
        assistant_text = engine.respond(
            context_summary=startup_context_items(startup_context),
            conversation=session.events,
        )
        if faculty_monitor is not None:
            faculty_monitor.record_call("crown", (time.monotonic() - t0) * 1000, True)

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
    return f"operator > {operator_text}\ninanna > {assistant_text}"


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
) -> str | None:
    normalized = command.strip()
    guardian_metrics = ensure_guardian_metrics(guardian_metrics)
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
                session_audit=session_audit,
                active_realm_name=active_realm_name,
                conversation_state=conversation_state,
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
        created = create_tool_use_proposal(
            proposal=proposal,
            session=session,
            user_input=normalized,
            tool=governance_result.proposed_tool,
            query=governance_result.tool_query or normalized,
        )
        return (
            f'operator > tool proposed: {governance_result.proposed_tool} — '
            f'"{governance_result.tool_query or normalized}"\n'
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
    expired_invites = user_manager.expire_old_invites()
    token_store = TokenStore()
    guardian_token = token_store.issue(
        guardian_user.user_id,
        guardian_user.display_name,
        guardian_user.role,
    )
    ensure_guardian_profile_completed(profile_manager, guardian_user.user_id)
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
    governance = GovernanceLayer(engine=engine)
    sync_profile_grounding(engine, profile_manager, guardian_user, guardian_token)
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
