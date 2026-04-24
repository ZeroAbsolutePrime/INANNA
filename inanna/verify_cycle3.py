from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path
from tempfile import TemporaryDirectory

from config import Config
from core.body import BodyInspector
from core.memory import Memory
from core.proposal import Proposal
from core.realm import DEFAULT_REALM, RealmConfig, RealmManager
from core.session import AnalystFaculty, Engine, Session
from core.state import StateReport
from core.user import UserManager, ensure_guardian_exists
from identity import CURRENT_PHASE, build_system_prompt
from main import build_history_report, build_realms_report, build_realm_context_report, handle_command


APP_ROOT = Path(__file__).resolve().parent


class CheckRunner:
    def __init__(self) -> None:
        self.checks: list[tuple[str, bool, str]] = []

    def check(self, label: str, condition: bool, detail: str = "") -> None:
        self.checks.append((label, condition, detail))

    def finish(self) -> int:
        print("INANNA NYX - Cycle 3 Integration Verification")
        print("==============================================")
        for label, passed, detail in self.checks:
            marker = "PASS" if passed else "FAIL"
            if passed or not detail:
                print(f"[{marker}] {label}")
            else:
                print(f"[{marker}] {label} ({detail})")
        print("----------------------------------------------")

        passed_count = sum(1 for _, passed, _ in self.checks if passed)
        total = len(self.checks)
        if passed_count == total:
            print(f"All {total} checks passed. Cycle 3 architecture verified.")
            return 0

        print(f"{passed_count} of {total} checks passed. Cycle 3 verification failed.")
        return 1


def roles_payload() -> dict[str, object]:
    return {
        "roles": {
            "guardian": {"description": "Full system access", "privileges": ["all"]},
            "operator": {"description": "Realm-scoped admin", "privileges": ["invite_users"]},
            "user": {
                "description": "Standard interaction",
                "privileges": ["converse", "approve_own_memory", "read_own_log"],
            },
        }
    }


def main() -> int:
    runner = CheckRunner()
    realm_fields = {field.name for field in fields(RealmConfig)}

    runner.check(
        "Realm: RealmConfig has all Cycle 3 fields",
        {
            "name",
            "purpose",
            "created_at",
            "governance_context",
            "governance_sensitivity",
        }.issubset(realm_fields),
    )
    runner.check("Realm: DEFAULT_REALM is default", DEFAULT_REALM == "default")

    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        roles_path = root / "roles.json"
        roles_path.write_text(json.dumps(roles_payload(), indent=2), encoding="utf-8")

        realm_manager = RealmManager(root)
        runner.check("Realm: RealmManager can be instantiated", isinstance(realm_manager, RealmManager))

        default_realm = realm_manager.ensure_default_realm()
        runner.check(
            "Realm: ensure_default_realm creates the default realm",
            default_realm.name == "default" and realm_manager.realm_exists("default"),
        )

        work_realm = realm_manager.create_realm(
            "work",
            purpose="Focused work.",
            governance_context="Keep realm memory work-specific.",
            governance_sensitivity="guarded",
        )
        runner.check(
            "Realm: create_realm writes realm.json and data directories",
            realm_manager.realm_exists("work")
            and all(path.exists() for path in realm_manager.realm_data_dirs("work").values()),
        )

        loaded_work = realm_manager.load_realm("work")
        runner.check(
            "Realm: load_realm round-trips purpose and sensitivity",
            loaded_work is not None
            and loaded_work.purpose == "Focused work."
            and loaded_work.governance_sensitivity == "guarded",
        )

        runner.check(
            "Realm: list_realms includes default and work",
            realm_manager.list_realms() == ["default", "work"],
            detail=str(realm_manager.list_realms()),
        )

        updated = realm_manager.update_realm_governance_context("work", "Review before storing.")
        refreshed_work = realm_manager.load_realm("work")
        runner.check(
            "Realm: governance context updates persist",
            updated and refreshed_work is not None and refreshed_work.governance_context == "Review before storing.",
        )

        dirs = realm_manager.realm_data_dirs("work")
        runner.check(
            "Realm: realm_data_dirs returns the expected keys",
            sorted(dirs.keys()) == ["memory", "nammu", "proposals", "sessions"],
        )

        default_prompt = build_system_prompt()
        runner.check(
            "Identity: default system prompt omits explicit realm header",
            "Active realm:" not in default_prompt,
        )

        work_prompt = build_system_prompt(work_realm)
        runner.check(
            "Identity: realm-aware system prompt names the active realm",
            "Active realm: work." in work_prompt,
        )
        runner.check(
            "Identity: realm-aware system prompt includes purpose and governance context",
            "Realm purpose: Focused work." in work_prompt
            and "Realm governance context: Keep realm memory work-specific." in work_prompt,
        )

        engine = Engine(realm=work_realm)
        messages = engine._build_messages(
            [{"text": "assistant: remembered work line", "realm_name": "default"}],
            [{"role": "user", "content": "hello"}],
        )
        runner.check("Engine: realm-aware Engine can be instantiated", isinstance(engine, Engine))
        runner.check(
            "Engine: system message uses the realm-aware prompt",
            messages[0]["role"] == "system" and "Active realm: work." in messages[0]["content"],
        )
        runner.check(
            "Engine: grounding lines annotate memory from another realm",
            "(from realm: default)" in messages[1]["content"],
            detail=messages[1]["content"],
        )

        analyst = AnalystFaculty(realm=work_realm)
        mode, analysis = analyst.analyse("What changed?", context=[])
        runner.check(
            "Analyst: AnalystFaculty can be instantiated for a realm",
            isinstance(analyst, AnalystFaculty),
        )
        runner.check(
            "Analyst: fallback analysis returns text without a live model",
            mode in {"fallback", "live"} and isinstance(analysis, str) and bool(analysis.strip()),
        )

        session_dir = dirs["sessions"]
        memory_dir = dirs["memory"]
        proposal_dir = dirs["proposals"]
        nammu_dir = dirs["nammu"]
        session_dir.mkdir(parents=True, exist_ok=True)
        memory_dir.mkdir(parents=True, exist_ok=True)
        proposal_dir.mkdir(parents=True, exist_ok=True)
        nammu_dir.mkdir(parents=True, exist_ok=True)

        session = Session.create(session_dir=session_dir, context_summary=[])
        session.add_event("user", "hello work realm")
        session.add_event("assistant", "Welcome back to work.")
        memory = Memory(session_dir=session_dir, memory_dir=memory_dir)
        path = memory.write_memory(
            proposal_id="proposal-work",
            session_id=session.session_id,
            summary_lines=["assistant: focused work line"],
            approved_at="2026-04-20T08:00:00+00:00",
            realm_name="work",
            user_id="user_guardian",
        )
        report = memory.memory_log_report(user_id="user_guardian")
        startup = memory.load_startup_context(user_id="user_guardian")

        runner.check("Memory: write_memory stores realm_name on disk", path.exists())
        runner.check(
            "Memory: memory_log_report returns the stored realm name",
            report["records"][0]["realm_name"] == "work",
        )
        runner.check(
            "Memory: load_startup_context preserves realm-tagged summary items",
            startup["summary_items"][0]["realm_name"] == "work",
        )

        state_text = StateReport().render(
            session_id=session.session_id,
            mode="fallback",
            memory_count=1,
            pending_count=0,
            total_proposals=1,
            approved_proposals=1,
            rejected_proposals=0,
            realm_name="work",
            realm_memory_count=1,
            realm_session_count=1,
            realm_governance_context="Review before storing.",
            active_user="INANNA NAMMU (guardian)",
            realm_access=True,
        )
        runner.check("State: report includes the shared CURRENT_PHASE", f"Phase: {CURRENT_PHASE}" in state_text)
        runner.check(
            "State: report includes realm name and governance context",
            "Realm: work" in state_text and "Review before storing." in state_text,
        )

        inspector = BodyInspector()
        body_report = inspector.inspect(
            session_id=session.session_id,
            session_started_at=session.started_at,
            realm="work",
            model_url="http://localhost:1234/v1",
            model_name="local-model",
            model_mode="fallback",
            data_root=root,
            memory_record_count=1,
            pending_proposal_count=0,
            routing_log_count=0,
        )
        body_text = inspector.format_report(body_report)
        runner.check("Body: BodyInspector.inspect returns a report", body_report.realm == "work")
        runner.check(
            "Body: formatted report includes machine, session, model, and data sections",
            all(section in body_text for section in ("Machine:", "Session:", "Model:", "Data:")),
        )

        runner.check(
            "Reports: build_realms_report shows active realm and purpose",
            "Active: work" in build_realms_report(realm_manager, "work")
            and "[work]  Focused work." in build_realms_report(realm_manager, "work"),
        )
        realm_context_text = build_realm_context_report(
            refreshed_work,
            session_dir,
            memory_dir,
            proposal_dir,
        )
        runner.check(
            "Reports: build_realm_context_report shows governance context and counts",
            "Governance context: Review before storing." in realm_context_text
            and "Memory records: 1" in realm_context_text,
        )
        runner.check(
            "Reports: build_history_report formats empty proposal history honestly",
            build_history_report({"total": 0, "approved": 0, "rejected": 0, "pending": 0, "records": []})
            == "Proposal history (0 total):\n  No proposals recorded yet.",
        )

        user_manager = UserManager(data_root=root, roles_config_path=roles_path)
        guardian = ensure_guardian_exists(user_manager)
        proposal = Proposal(proposal_dir=proposal_dir)
        config = Config(model_url="", model_name="", api_key="")
        result = handle_command(
            "realm-context Keep this realm centered on work memory.",
            session,
            memory,
            proposal,
            StateReport(),
            Engine(realm=refreshed_work),
            AnalystFaculty(realm=refreshed_work),
            None,  # type: ignore[arg-type]
            [],
            startup,
            config,
            realm_manager=realm_manager,
            active_realm=refreshed_work,
            user_manager=user_manager,
            session_state={"active_user": guardian, "guardian_user": guardian},
        )
        runner.check(
            "Commands: realm-context update stays proposal-governed",
            "proposal required to update the active realm context" in str(result),
        )
        history_text = handle_command(
            "proposal-history",
            session,
            memory,
            proposal,
            StateReport(),
            Engine(realm=refreshed_work),
            AnalystFaculty(realm=refreshed_work),
            None,  # type: ignore[arg-type]
            [],
            startup,
            config,
            realm_manager=realm_manager,
            active_realm=refreshed_work,
            user_manager=user_manager,
            session_state={"active_user": guardian, "guardian_user": guardian},
        )
        runner.check(
            "Commands: proposal-history remains readable after Cycle 3",
            "Proposal history" in str(history_text),
        )

    return runner.finish()


if __name__ == "__main__":
    raise SystemExit(main())
