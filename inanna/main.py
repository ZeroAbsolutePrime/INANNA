from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from config import Config
from core.memory import Memory
from core.nammu import IntentClassifier
from core.proposal import Proposal
from core.session import AnalystFaculty, Engine, Session
from core.state import StateReport
from identity import phase_banner


APP_ROOT = Path(__file__).resolve().parent
load_dotenv(APP_ROOT / ".env")

DATA_ROOT = APP_ROOT / "data"
SESSION_DIR = DATA_ROOT / "sessions"
MEMORY_DIR = DATA_ROOT / "memory"
PROPOSAL_DIR = DATA_ROOT / "proposals"
STARTUP_COMMANDS = (
    "reflect",
    "analyse",
    "audit",
    "history",
    "routing-log",
    "memory-log",
    "status",
    "diagnostics",
    "approve",
    "reject",
    "forget",
    "exit",
)


def ensure_directories() -> None:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    PROPOSAL_DIR.mkdir(parents=True, exist_ok=True)


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
        f"Memory directory: {MEMORY_DIR}",
        f"Proposal directory: {PROPOSAL_DIR}",
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


def append_routing_decision(
    routing_log: list[dict[str, str]],
    route: str,
    user_input: str,
) -> None:
    routing_log.append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "input_preview": user_input[:60],
            "route": route,
        }
    )


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
) -> str | None:
    normalized = command.strip()
    if not normalized:
        return ""

    lowered = normalized.lower()
    if lowered in {"exit", "quit"}:
        return None

    if lowered == "status":
        return state_report.render(
            session_id=session.session_id,
            mode=engine.mode,
            memory_count=memory.memory_count(),
            pending_count=proposal.pending_count(),
        )

    if lowered == "diagnostics":
        return build_diagnostics_report(config=config, engine=engine, session=session)

    if lowered == "history":
        return build_history_report(proposal.history_report())

    if lowered == "routing-log":
        return build_routing_log_report(routing_log)

    if lowered == "memory-log":
        return build_memory_log_report(memory.memory_log_report())

    if lowered == "forget":
        return run_forget_flow(memory=memory, proposal=proposal)

    if lowered == "analyse" or lowered.startswith("analyse "):
        question = normalized[len("analyse") :].strip()
        analysis_mode, analysis_text = analyst.analyse(
            question=question,
            context=startup_context["summary_lines"],
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
            context_summary=startup_context["summary_lines"],
        )
        if audit_mode == "live":
            return f"inanna> [live audit] {audit_text}"
        return f"inanna> [audit summary] {audit_text}"

    if lowered == "reflect":
        reflection_mode, reflection_text = engine.reflect(startup_context["summary_lines"])
        if reflection_mode == "live":
            return f"inanna> [live reflection] {reflection_text}"
        return f"inanna> [memory fallback] {reflection_text}"

    if lowered in {"approve", "reject"}:
        resolved = proposal.resolve_next(lowered)
        if not resolved:
            return "No pending proposals."

        if resolved["status"] == "approved":
            payload = resolved["payload"]
            memory.write_memory(
                proposal_id=resolved["proposal_id"],
                session_id=payload["session_id"],
                summary_lines=payload["summary_lines"],
                approved_at=resolved["resolved_at"],
            )
            return (
                f"Approved {resolved['proposal_id']} and wrote a memory record for the next session."
            )

        return f"Rejected {resolved['proposal_id']}."

    route = classifier.classify(normalized)
    append_routing_decision(routing_log, route, normalized)

    if route == "analyst":
        analysis_mode, analysis_text = analyst.analyse(
            question=normalized,
            context=startup_context["summary_lines"],
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
        return (
            f"nammu > routing to analyst faculty\n"
            f"analyst > {label} {analysis_text}\n"
            f"{created['line']}"
        )

    session.add_event("user", normalized)
    assistant_text = engine.respond(
        context_summary=startup_context["summary_lines"],
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
    return (
        f"nammu > routing to crown faculty\n"
        f"inanna > {assistant_text}\n"
        f"{created['line']}"
    )


def main() -> None:
    ensure_directories()

    config = Config.from_env()
    memory = Memory(session_dir=SESSION_DIR, memory_dir=MEMORY_DIR)
    proposal = Proposal(proposal_dir=PROPOSAL_DIR)
    state_report = StateReport()
    engine = Engine(
        model_url=config.model_url,
        model_name=config.model_name,
        api_key=config.api_key,
    )
    analyst = AnalystFaculty(
        model_url=config.model_url,
        model_name=config.model_name,
        api_key=config.api_key,
    )
    classifier = IntentClassifier(engine)
    routing_log: list[dict[str, str]] = []

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

    print(phase_banner())
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
        )
        if result is None:
            print("Session closed.")
            break
        if result:
            print(result)


if __name__ == "__main__":
    main()
