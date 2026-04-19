from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from config import Config
from core.governance import GovernanceLayer
from core.guardian import GuardianFaculty
from core.memory import Memory
from core.nammu import IntentClassifier
from core.nammu_memory import (
    append_governance_event,
    append_routing_event,
    load_governance_history,
    load_routing_history,
)
from core.operator import OperatorFaculty, ToolResult
from core.proposal import Proposal
from core.realm import DEFAULT_REALM, RealmConfig, RealmManager
from core.session import AnalystFaculty, Engine, Session
from core.state import StateReport
from identity import phase_banner


APP_ROOT = Path(__file__).resolve().parent
load_dotenv(APP_ROOT / ".env")

DATA_ROOT = APP_ROOT / "data"
SESSION_DIR = DATA_ROOT / "sessions"
MEMORY_DIR = DATA_ROOT / "memory"
PROPOSAL_DIR = DATA_ROOT / "proposals"
NAMMU_DIR = DATA_ROOT / "nammu"
STARTUP_COMMANDS = (
    "reflect",
    "analyse",
    "audit",
    "guardian",
    "realms",
    "realm-context",
    "history",
    "routing-log",
    "nammu-log",
    "memory-log",
    "status",
    "diagnostics",
    "approve",
    "reject",
    "forget",
    "exit",
)


def get_active_realm_name() -> str:
    realm_name = os.getenv("INANNA_REALM", DEFAULT_REALM).strip()
    return realm_name or DEFAULT_REALM


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


def build_diagnostics_report(
    config: Config,
    engine: Engine,
    session: Session,
    memory_dir: Path | None = None,
    proposal_dir: Path | None = None,
) -> str:
    model_url = config.model_url or "not set"
    model_name = config.model_name or "not set"
    api_key_state = "set" if config.api_key else "not set"
    lines = [
        f"Model URL: {model_url}",
        f"Model name: {model_name}",
        f"API key: {api_key_state}",
        f"Mode: {engine.mode}",
        f"Session file: {session.session_path}",
        f"Memory directory: {memory_dir or MEMORY_DIR}",
        f"Proposal directory: {proposal_dir or PROPOSAL_DIR}",
    ]
    return "\n".join(lines)


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
) -> dict:
    return proposal.create(
        what="Store a requested memory from direct user instruction",
        why=reason,
        payload={
            "session_id": session.session_id,
            "summary_lines": [f"user: {user_input}"],
        },
    )


def create_tool_use_proposal(
    proposal: Proposal,
    session: Session,
    user_input: str,
    tool: str,
    query: str,
) -> dict:
    created = proposal.create(
        what="web_search tool use",
        why="User requested current information that requires approved tool use.",
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


def build_tool_result_text(result: ToolResult) -> str:
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
) -> str:
    payload = resolved["payload"]
    original_input = payload.get("original_input", "")
    query = payload.get("query", "")
    tool = payload.get("tool", "")

    session.add_event("user", original_input)

    if decision == "approve":
        guardian_metrics["tool_executions"] += 1
        result = operator.execute(tool, {"query": query})
        operator_text = build_tool_result_text(result)
        model_connected = engine._connected
        assistant_text = engine.respond(
            context_summary=startup_context_items(startup_context)
            + build_tool_context_lines(result),
            conversation=session.events,
        )
        if result.success and model_connected and engine.mode == "fallback":
            created = proposal.create(
                what="Update the memory store from the latest session turn",
                why="Keep the next session grounded in readable, user-approved context.",
                payload=memory.build_candidate(
                    session_id=session.session_id,
                    events=session.events,
                ),
            )
            return (
                f"operator > {operator_text}\n"
                "operator > model unavailable to summarize. Raw results shown above.\n"
                f"{created['line']}"
            )
    else:
        operator_text = "tool use rejected. Proceeding without search."
        assistant_text = engine.respond(
            context_summary=startup_context_items(startup_context),
            conversation=session.events,
        )

    session.add_event("assistant", assistant_text)
    created = proposal.create(
        what="Update the memory store from the latest session turn",
        why="Keep the next session grounded in readable, user-approved context.",
        payload=memory.build_candidate(
            session_id=session.session_id,
            events=session.events,
        ),
    )
    return f"operator > {operator_text}\ninanna > {assistant_text}\n{created['line']}"


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
) -> str | None:
    normalized = command.strip()
    if not normalized:
        return ""

    guardian_metrics = ensure_guardian_metrics(guardian_metrics)

    lowered = normalized.lower()
    if lowered in {"exit", "quit"}:
        return None

    if lowered == "status":
        current_realm = load_current_realm(realm_manager, active_realm)
        return state_report.render(
            session_id=session.session_id,
            mode=engine.mode,
            memory_count=memory.memory_count(),
            pending_count=proposal.pending_count(),
            realm_name=current_realm.name if current_realm else DEFAULT_REALM,
            realm_memory_count=count_records(memory.memory_dir, "*.json"),
            realm_session_count=count_records(memory.session_dir, "*.json"),
            realm_governance_context=(
                current_realm.governance_context if current_realm else ""
            ),
        )

    if lowered == "diagnostics":
        return build_diagnostics_report(
            config=config,
            engine=engine,
            session=session,
            memory_dir=memory.memory_dir,
            proposal_dir=proposal.proposal_dir,
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

    if lowered == "history":
        return build_history_report(proposal.history_report())

    if lowered == "routing-log":
        return build_routing_log_report(routing_log)

    if lowered == "nammu-log":
        return build_nammu_log_report(resolve_nammu_dir(session, nammu_dir))

    if lowered == "memory-log":
        return build_memory_log_report(memory.memory_log_report())

    if lowered == "forget":
        return run_forget_flow(memory=memory, proposal=proposal)

    if lowered == "analyse" or lowered.startswith("analyse "):
        question = normalized[len("analyse") :].strip()
        analysis_mode, analysis_text = analyst.analyse(
            question=question,
            context=startup_context_items(startup_context),
        )
        if not question:
            return f"analyst > [analysis fallback] {analysis_text}"

        session.add_event("user", normalized)
        session.add_event("analyst", analysis_text)
        created = proposal.create(
            what="Update the memory store from the latest session turn",
            why="Keep the next session grounded in readable, user-approved context.",
            payload=memory.build_candidate(
                session_id=session.session_id,
                events=session.events,
            ),
        )
        if analysis_mode == "live":
            return f"analyst > [live analysis] {analysis_text}\n{created['line']}"
        return f"analyst > [analysis fallback] {analysis_text}\n{created['line']}"

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
        return f"guardian > {report}"

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
            )

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

        if resolved["status"] == "approved":
            memory.write_memory(
                proposal_id=resolved["proposal_id"],
                session_id=payload["session_id"],
                summary_lines=payload["summary_lines"],
                approved_at=resolved["resolved_at"],
                realm_name=active_realm.name if active_realm else "",
            )
            return (
                f"Approved {resolved['proposal_id']} and wrote a memory record for the next session."
            )

        return f"Rejected {resolved['proposal_id']}."

    governance_result = classifier.route(normalized)
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
        analysis_mode, analysis_text = analyst.analyse(
            question=normalized,
            context=startup_context_items(startup_context),
        )
        session.add_event("user", normalized)
        session.add_event("analyst", analysis_text)
        created = proposal.create(
            what="Update the memory store from the latest session turn",
            why="Keep the next session grounded in readable, user-approved context.",
            payload=memory.build_candidate(
                session_id=session.session_id,
                events=session.events,
            ),
        )
        label = "[live analysis]" if analysis_mode == "live" else "[analysis fallback]"
        lines = [f"nammu > routing to {governance_result.faculty} faculty"]
        if governance_result.decision == "redirect":
            lines.append(f"governance > redirected: {governance_result.reason}")
        lines.append(f"analyst > {label} {analysis_text}")
        lines.append(created["line"])
        return (
            "\n".join(lines)
        )

    session.add_event("user", normalized)
    assistant_text = engine.respond(
        context_summary=startup_context_items(startup_context),
        conversation=session.events,
    )
    session.add_event("assistant", assistant_text)

    created = proposal.create(
        what="Update the memory store from the latest session turn",
        why="Keep the next session grounded in readable, user-approved context.",
        payload=memory.build_candidate(
            session_id=session.session_id,
            events=session.events,
        ),
    )
    lines = [f"nammu > routing to {governance_result.faculty} faculty"]
    if governance_result.decision == "redirect":
        lines.append(f"governance > redirected: {governance_result.reason}")
    lines.append(f"inanna > {assistant_text}")
    lines.append(created["line"])
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
    classifier = IntentClassifier(engine, governance=governance)
    routing_log: list[dict[str, str]] = []
    guardian_metrics = {"governance_blocks": 0, "tool_executions": 0}

    if migrated:
        print(f"Migrated {migrated} files to default realm.")

    if engine.verify_connection():
        print(f"Model connected: {config.model_name} at {config.model_url}")
    else:
        print("Model unreachable — fallback mode active. Set INANNA_MODEL_URL to connect.")

    analyst.fallback_mode = engine.fallback_mode
    analyst._connected = engine._connected

    startup_context = memory.load_startup_context()
    session = Session.create(
        session_dir=SESSION_DIR,
        context_summary=startup_context["summary_lines"],
    )

    print(f"Phase: {phase_banner()}")
    print(f"Realm: {active_realm.name}")
    print(f"Session ID: {session.session_id}")
    print_startup_context(startup_context["summary_lines"])
    print(startup_commands_line())

    while True:
        try:
            user_input = input("you> ")
        except EOFError:
            print()
            print("Session closed.")
            break
        except KeyboardInterrupt:
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
        )
        if result is None:
            print("Session closed.")
            break
        if result:
            print(result)


if __name__ == "__main__":
    main()
