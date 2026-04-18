from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from config import Config
from core.memory import Memory
from core.proposal import Proposal
from core.session import Engine, Session
from core.state import StateReport


APP_ROOT = Path(__file__).resolve().parent
load_dotenv(APP_ROOT / ".env")

DATA_ROOT = APP_ROOT / "data"
SESSION_DIR = DATA_ROOT / "sessions"
MEMORY_DIR = DATA_ROOT / "memory"
PROPOSAL_DIR = DATA_ROOT / "proposals"


def ensure_directories() -> None:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    PROPOSAL_DIR.mkdir(parents=True, exist_ok=True)


def print_startup_context(summary_lines: list[str]) -> None:
    if not summary_lines:
        print("Prior context (0 lines):")
        print("  none yet.")
        return

    print(f"Prior context ({len(summary_lines)} lines):")
    for index, line in enumerate(summary_lines, start=1):
        print(f"  {index}. {line}")


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

    if engine.verify_connection():
        print(f"Model connected: {config.model_name} at {config.model_url}")
    else:
        print("Model unreachable \u2014 fallback mode active. Set INANNA_MODEL_URL to connect.")

    startup_context = memory.load_startup_context()
    session = Session.create(
        session_dir=SESSION_DIR,
        context_summary=startup_context["summary_lines"],
    )

    print("Phase 2 - The Real Voice")
    print(f"Session ID: {session.session_id}")
    print_startup_context(startup_context["summary_lines"])
    print("Commands: status, approve, reject, exit")

    while True:
        try:
            user_input = input("you> ").strip()
        except EOFError:
            print()
            print("Session closed.")
            break
        except KeyboardInterrupt:
            print()
            print("Session closed.")
            break

        if not user_input:
            continue

        command = user_input.lower()
        if command in {"exit", "quit"}:
            print("Session closed.")
            break

        if command == "status":
            print(
                state_report.render(
                    session_id=session.session_id,
                    memory_count=memory.memory_count(),
                    pending_count=proposal.pending_count(),
                )
            )
            continue

        if command in {"approve", "reject"}:
            resolved = proposal.resolve_next(command)
            if not resolved:
                print("No pending proposals.")
                continue

            if resolved["status"] == "approved":
                payload = resolved["payload"]
                memory.write_memory(
                    proposal_id=resolved["proposal_id"],
                    session_id=payload["session_id"],
                    summary_lines=payload["summary_lines"],
                    approved_at=resolved["resolved_at"],
                )
                print(
                    f"Approved {resolved['proposal_id']} and wrote a memory record for the next session."
                )
            else:
                print(f"Rejected {resolved['proposal_id']}.")
            continue

        session.add_event("user", user_input)
        assistant_text = engine.respond(
            context_summary=startup_context["summary_lines"],
            conversation=session.events,
        )
        print(f"assistant> {assistant_text}")
        session.add_event("assistant", assistant_text)

        created = proposal.create(
            what="Update the memory store from the latest session turn",
            why="Keep the next session grounded in readable, user-approved context.",
            payload=memory.build_candidate(
                session_id=session.session_id,
                events=session.events,
            ),
        )
        print(created["line"])


if __name__ == "__main__":
    main()
