from __future__ import annotations

import io
import json
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from config import Config
from core.faculty_monitor import FacultyMonitor
from core.filesystem_faculty import FileSystemFaculty
from core.governance import GovernanceResult
from core.help_system import build_help_response
from core.memory import Memory
from core.nammu import IntentClassifier
from core.operator import OperatorFaculty, ToolResult
from core.package_faculty import PackageFaculty, PackageRecord, PackageResult
from core.profile import NotificationStore, ProfileManager
from core.process_faculty import ProcessFaculty, ProcessRecord, ProcessResult, SystemInfo
from core.process_monitor import ProcessMonitor
from core.proposal import Proposal
from core.realm import RealmManager
from core.reflection import ReflectiveMemory
from core.session import AnalystFaculty, Engine, Session
from core.session_token import TokenStore
from core.state import StateReport
from core.user import UserManager, ensure_guardian_exists
from core.user_log import UserLog
from main import STARTUP_COMMANDS, finalize_auto_memory, handle_command, startup_commands_line


ROLES_PAYLOAD = {
    "roles": {
        "guardian": {
            "description": "Full system access - assigned directly only",
            "privileges": ["all"],
        },
        "operator": {
            "description": "Realm-scoped admin",
            "privileges": [
                "manage_users_in_realm",
                "approve_proposals_in_realm",
                "read_realm_audit_log",
                "invite_users",
                "network_tools",
            ],
        },
        "user": {
            "description": "Standard interaction",
            "privileges": [
                "converse",
                "approve_own_memory",
                "read_own_log",
                "forget_own_memory",
            ],
        },
    }
}


class SuccessfulToolOperator:
    PERMITTED_TOOLS = {"web_search"}

    def should_skip_proposal(self, tool_name: str, persistent_trusted_tools: list[str] | None) -> bool:
        normalized_tool = str(tool_name or "").strip().lower()
        trusted_tools = {
            str(item or "").strip().lower()
            for item in (persistent_trusted_tools or [])
            if str(item or "").strip()
        }
        return normalized_tool in self.PERMITTED_TOOLS and normalized_tool in trusted_tools

    def execute(self, tool: str, params: dict[str, str]) -> ToolResult:
        return ToolResult(
            tool=tool,
            query=params.get("query", ""),
            success=True,
            data={
                "abstract": "Current result abstract",
                "answer": "Current result answer",
                "related": [],
            },
        )


class FlakySummaryEngine:
    def __init__(self) -> None:
        self._connected = True
        self._mode = "connected"

    @property
    def mode(self) -> str:
        return self._mode

    def respond(self, context_summary, conversation) -> str:
        del context_summary
        del conversation
        self._connected = False
        self._mode = "fallback"
        return "Model call failed, so fallback mode continued safely: network down"


class CommandTests(unittest.TestCase):
    def make_runtime(
        self,
    ) -> tuple[
        Session,
        Memory,
        Proposal,
        StateReport,
        Engine,
        AnalystFaculty,
        IntentClassifier,
        list[dict[str, str]],
        dict,
        Config,
    ]:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        session_dir = root / "sessions"
        memory_dir = root / "memory"
        proposal_dir = root / "proposals"
        session_dir.mkdir()
        memory_dir.mkdir()
        proposal_dir.mkdir()

        session = Session.create(session_dir=session_dir, context_summary=[])
        memory = Memory(session_dir=session_dir, memory_dir=memory_dir)
        proposal = Proposal(proposal_dir=proposal_dir)
        state_report = StateReport()
        engine = Engine()
        analyst = AnalystFaculty()
        classifier = IntentClassifier(engine)
        routing_log: list[dict[str, str]] = []
        startup_context = {
            "summary_lines": [],
            "summary_items": [],
            "memory_count": 0,
            "session_count": 0,
        }
        config = Config(model_url="", model_name="", api_key="")
        return (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

    def write_memory_record(self, memory: Memory, memory_id: str = "proposal-a") -> None:
        memory.write_memory(
            proposal_id=memory_id,
            session_id="session-1",
            summary_lines=["user: hello", "assistant: welcome back"],
            approved_at="2026-04-19T10:00:00",
        )

    def run_forget_command(
        self,
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
        answers: list[str],
    ) -> tuple[str, str, list[str]]:
        prompts: list[str] = []
        answer_iter = iter(answers)

        def fake_input(prompt: str) -> str:
            prompts.append(prompt)
            return next(answer_iter)

        output = io.StringIO()
        with patch("builtins.input", side_effect=fake_input), redirect_stdout(output):
            result = handle_command(
                "forget",
                session,
                memory,
                proposal,
                state_report,
                engine,
                analyst,
                classifier,
                routing_log,
                startup_context,
                config,
            )
        return result, output.getvalue(), prompts

    def make_user_context(
        self,
        root: Path,
    ) -> tuple[
        UserManager,
        dict[str, object | None],
        TokenStore,
        UserLog,
        FacultyMonitor,
    ]:
        roles_path = root / "roles.json"
        roles_path.write_text(json.dumps(ROLES_PAYLOAD, indent=2), encoding="utf-8")
        user_manager = UserManager(data_root=root, roles_config_path=roles_path)
        guardian_user = ensure_guardian_exists(user_manager)
        token_store = TokenStore()
        guardian_token = token_store.issue(
            guardian_user.user_id,
            guardian_user.display_name,
            guardian_user.role,
        )
        session_state: dict[str, object | None] = {
            "active_user": guardian_user,
            "original_user": None,
            "guardian_user": guardian_user,
            "active_token": guardian_token,
            "original_token": None,
            "guardian_token": guardian_token,
        }
        return (
            user_manager,
            session_state,
            token_store,
            UserLog(root / "user_logs"),
            FacultyMonitor(),
        )

    def test_status_returns_session_line(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "status",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertIn("Session:", result)
        self.assertIn("Active user:", result)
        self.assertIn("Realm:", result)
        self.assertIn("Realm access:", result)
        self.assertIn("Realm governance context:", result)
        self.assertIn("Total proposals:", result)
        self.assertIn("routing-log", result)

    def test_diagnostics_returns_model_url_line(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "diagnostics",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertIn("Body Report -", result)
        self.assertIn("Model:", result)
        self.assertIn("  URL: not set", result)

    def test_body_returns_same_report_shape_as_diagnostics(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "body",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertIn("Body Report -", result)
        self.assertIn("Platform:", result)
        self.assertIn("Session:", result)
        self.assertIn("Model:", result)

    def test_history_with_no_proposals_returns_zero_total(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "history",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertIn("0 total", result)
        self.assertIn("No proposals recorded yet.", result)

    def test_proposal_history_alias_returns_same_history_report(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "proposal-history",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertIn("Proposal history (0 total):", result)
        self.assertIn("No proposals recorded yet.", result)

    def test_routing_log_with_no_decisions_returns_zero_total(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "routing-log",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertIn("NAMMU Routing Log (0 decisions)", result)
        self.assertIn("No routing decisions recorded yet.", result)

    def test_memory_log_with_no_memory_returns_zero_records(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "memory-log",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertIn("0 records", result)
        self.assertIn("No approved memory records yet.", result)

    def test_audit_returns_summary_prefix_and_has_no_side_effects(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "audit",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertTrue(result.startswith("inanna> [audit summary] "))
        self.assertEqual(proposal.pending_count(), 0)
        self.assertEqual(memory.memory_count(), 0)
        self.assertEqual(len(routing_log), 0)

    def test_startup_commands_line_lists_expected_commands(self) -> None:
        self.assertEqual(
            STARTUP_COMMANDS,
            (
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
            ),
        )
        self.assertEqual(
            startup_commands_line(),
            (
                "Commands: users, create-user, login, logout, whoami, my-profile, view-profile, inanna-reflect, my-trust, "
                "my-departments, assign-department, unassign-department, assign-group, "
                "unassign-group, notify-department, governance-trust, governance-revoke, reflect, analyse, audit, guardian, faculties, realms, "
                "create-realm, realm-context, switch-user, assign-realm, unassign-realm, my-log, user-log, invite, join, invites, "
                "admin-surface, tool-registry, faculty-registry, network-status, process-status, history, proposal-history, routing-log, nammu-log, "
                "memory-log, body, status, diagnostics, guardian-dismiss, "
                "guardian-clear-events, approve, reject, forget, exit, help, software"
            ),
        )

    def test_help_topic_response_has_detectable_header(self) -> None:
        result = build_help_response("guardian", "faculties")

        self.assertTrue(result.startswith("INANNA NYX — FACULTIES"))
        self.assertIn("CROWN", result)
        self.assertIn("OPERATOR", result)

    def test_help_unknown_topic_lists_available_topics(self) -> None:
        result = build_help_response("guardian", "unknown-topic")

        self.assertIn("help > Unknown topic: unknown-topic", result)
        self.assertIn("faculties", result)
        self.assertIn("tools", result)
        self.assertIn("email", result)

    def test_help_email_topic_lists_governed_email_workflows(self) -> None:
        result = build_help_response("guardian", "email")

        self.assertTrue(result.startswith("INANNA NYX"))
        self.assertIn("EMAIL", result)
        self.assertIn("check my email", result.lower())
        self.assertIn("two-stage", result.lower())

    def test_my_profile_returns_formatted_profile(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        root = session.session_path.parent.parent
        user_manager, session_state, token_store, user_log, faculty_monitor = self.make_user_context(root)
        profile_manager = ProfileManager(root / "profiles")
        active_user = session_state["active_user"]
        assert active_user is not None
        profile_manager.update_field(active_user.user_id, "preferred_name", "ZAERA")

        result = handle_command(
            "my-profile",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
            token_store=token_store,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            profile_manager=profile_manager,
        )

        self.assertIn("Your profile", result)
        self.assertIn("Preferred    ZAERA", result)
        self.assertIn('Type "my-profile edit [field] [value]"', result)

    def test_my_profile_edit_updates_profile_and_refreshes_grounding(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        root = session.session_path.parent.parent
        user_manager, session_state, token_store, user_log, faculty_monitor = self.make_user_context(root)
        profile_manager = ProfileManager(root / "profiles")
        active_user = session_state["active_user"]
        assert active_user is not None
        profile_manager.ensure_profile_exists(active_user.user_id)

        result = handle_command(
            "my-profile edit preferred_name Oracle",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
            token_store=token_store,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            profile_manager=profile_manager,
        )

        self.assertEqual("profile > preferred_name updated to Oracle.", result)
        self.assertEqual(profile_manager.load(active_user.user_id).preferred_name, "Oracle")
        self.assertEqual(engine.grounding_prefix, "You are speaking with Oracle.")

    def test_my_profile_clear_rejects_protected_field(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        root = session.session_path.parent.parent
        user_manager, session_state, token_store, user_log, faculty_monitor = self.make_user_context(root)
        profile_manager = ProfileManager(root / "profiles")

        result = handle_command(
            "my-profile clear onboarding_completed",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
            token_store=token_store,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            profile_manager=profile_manager,
        )

        self.assertEqual("profile > onboarding_completed cannot be cleared.", result)

    def test_my_profile_clear_communication_resets_observed_fields(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        root = session.session_path.parent.parent
        user_manager, session_state, token_store, user_log, faculty_monitor = self.make_user_context(root)
        profile_manager = ProfileManager(root / "profiles")
        active_user = session_state["active_user"]
        assert active_user is not None
        profile_manager.update_field(active_user.user_id, "preferred_length", "short")
        profile_manager.update_field(active_user.user_id, "formality", "casual")
        profile_manager.update_field(active_user.user_id, "communication_style", "direct")
        profile_manager.update_field(active_user.user_id, "observed_patterns", ["brief"])

        result = handle_command(
            "my-profile clear communication",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
            token_store=token_store,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            profile_manager=profile_manager,
        )

        profile = profile_manager.load(active_user.user_id)
        self.assertEqual("profile > Communication observations cleared.", result)
        self.assertEqual(profile.preferred_length, "")
        self.assertEqual(profile.formality, "")
        self.assertEqual(profile.communication_style, "")
        self.assertEqual(profile.observed_patterns, [])

    def test_view_profile_returns_formatted_target_profile_for_guardian(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        root = session.session_path.parent.parent
        user_manager, session_state, token_store, user_log, faculty_monitor = self.make_user_context(root)
        profile_manager = ProfileManager(root / "profiles")
        guardian_user = session_state["active_user"]
        assert guardian_user is not None
        target = user_manager.create_user("Alice", "user", ["default"], guardian_user.user_id)
        profile_manager.update_field(target.user_id, "preferred_name", "Alicia")

        result = handle_command(
            "view-profile Alice",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
            token_store=token_store,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            profile_manager=profile_manager,
        )

        self.assertIn(f"Profile for Alice ({target.user_id}):", result)
        self.assertIn("Preferred    Alicia", result)

    def test_inanna_reflect_shows_approved_reflections(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        root = session.session_path.parent.parent
        user_manager, session_state, token_store, user_log, faculty_monitor = self.make_user_context(root)
        reflective_memory = ReflectiveMemory(root / "self")
        entry = reflective_memory.propose(
            "I tend toward structured formatting when reasoning about technical domains.",
            "observed across multiple security sessions",
        )
        reflective_memory.approve(entry, approved_by="ZAERA")

        result = handle_command(
            "inanna-reflect",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
            token_store=token_store,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            reflective_memory=reflective_memory,
        )

        self.assertIn("INANNA's self-knowledge - 1 entry:", result)
        self.assertIn("structured formatting", result)
        self.assertIn("context: observed across multiple security sessions", result)

    def test_my_trust_reports_session_and_persistent_trust(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        root = session.session_path.parent.parent
        user_manager, session_state, token_store, user_log, faculty_monitor = self.make_user_context(root)
        profile_manager = ProfileManager(root / "profiles")
        active_user = session_state["active_user"]
        assert active_user is not None
        profile_manager.update_field(active_user.user_id, "session_trusted_tools", ["web_search"])
        profile_manager.update_field(active_user.user_id, "persistent_trusted_tools", ["resolve_host"])

        result = handle_command(
            "my-trust",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
            token_store=token_store,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            profile_manager=profile_manager,
        )

        self.assertIn("Your trust patterns:", result)
        self.assertIn("Session      web_search", result)
        self.assertIn("Persistent   resolve_host", result)

    def test_governance_trust_updates_profile_and_audit(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        root = session.session_path.parent.parent
        user_manager, session_state, token_store, user_log, faculty_monitor = self.make_user_context(root)
        profile_manager = ProfileManager(root / "profiles")
        active_user = session_state["active_user"]
        assert active_user is not None
        session_audit: list[dict[str, object]] = []

        result = handle_command(
            "governance-trust web_search",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            operator=OperatorFaculty(),
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
            token_store=token_store,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            session_audit=session_audit,  # type: ignore[arg-type]
            profile_manager=profile_manager,
        )

        self.assertEqual(
            "governance > web_search is now persistently trusted for you.",
            result,
        )
        self.assertEqual(profile_manager.load(active_user.user_id).persistent_trusted_tools, ["web_search"])
        self.assertEqual(session_audit[-1]["event_type"], "trust_granted")

    def test_governance_revoke_removes_tool_and_logs_audit(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        root = session.session_path.parent.parent
        user_manager, session_state, token_store, user_log, faculty_monitor = self.make_user_context(root)
        profile_manager = ProfileManager(root / "profiles")
        active_user = session_state["active_user"]
        assert active_user is not None
        profile_manager.update_field(active_user.user_id, "persistent_trusted_tools", ["web_search"])
        session_audit: list[dict[str, object]] = []

        result = handle_command(
            "governance-revoke web_search",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
            token_store=token_store,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            session_audit=session_audit,  # type: ignore[arg-type]
            profile_manager=profile_manager,
        )

        self.assertEqual(
            "governance > web_search trust revoked. Proposals will resume for this tool.",
            result,
        )
        self.assertEqual(profile_manager.load(active_user.user_id).persistent_trusted_tools, [])
        self.assertEqual(session_audit[-1]["event_type"], "trust_revoked")

    def test_trusted_tool_skips_proposal_and_executes_immediately(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            _engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        engine = FlakySummaryEngine()
        root = session.session_path.parent.parent
        user_manager, session_state, token_store, user_log, faculty_monitor = self.make_user_context(root)
        profile_manager = ProfileManager(root / "profiles")
        active_user = session_state["active_user"]
        assert active_user is not None
        profile_manager.update_field(active_user.user_id, "persistent_trusted_tools", ["web_search"])
        session_audit: list[dict[str, object]] = []

        with patch.object(
            classifier,
            "route",
            return_value=GovernanceResult(
                decision="allow",
                faculty="crown",
                reason="current information requires web search",
                suggests_tool=True,
                proposed_tool="web_search",
                tool_query="latest weather",
            ),
        ):
            result = handle_command(
                "what is the weather today",
                session,
                memory,
                proposal,
                state_report,
                engine,
                analyst,
                classifier,
                routing_log,
                startup_context,
                config,
                operator=SuccessfulToolOperator(),
                guardian_metrics={"governance_blocks": 0, "tool_executions": 0},
                user_manager=user_manager,
                session_state=session_state,  # type: ignore[arg-type]
                token_store=token_store,
                user_log=user_log,
                faculty_monitor=faculty_monitor,
                session_audit=session_audit,  # type: ignore[arg-type]
                profile_manager=profile_manager,
            )

        self.assertIn("operator > search result:", result)
        self.assertIn("operator > model unavailable to summarize. Raw results shown above.", result)
        self.assertEqual(proposal.pending_count(), 0)
        self.assertTrue(
            any(event.get("event_type") == "tool_executed_trusted" for event in session_audit)
        )

    def test_safe_filesystem_read_executes_without_proposal(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            _engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        engine = FlakySummaryEngine()
        with TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            target = base / "notes.txt"
            target.write_text("hello from filesystem", encoding="utf-8")
            filesystem_faculty = FileSystemFaculty(
                safe_read_paths=(base,),
                forbidden_paths=(Path("/etc/shadow"), Path("/etc/passwd"), Path("/root")),
            )

            result = handle_command(
                f"read the file at {target}",
                session,
                memory,
                proposal,
                state_report,
                engine,
                analyst,
                classifier,
                routing_log,
                startup_context,
                config,
                filesystem_faculty=filesystem_faculty,
            )

        self.assertIn("fs > read:", result)
        self.assertIn("hello from filesystem", result)
        self.assertIn("model unavailable to summarize", result)
        self.assertEqual(proposal.pending_count(), 0)

    def test_write_file_request_creates_governed_tool_proposal(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        with TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "todo.txt"
            result = handle_command(
                f"write a file called {target} with remember the milk",
                session,
                memory,
                proposal,
                state_report,
                engine,
                analyst,
                classifier,
                routing_log,
                startup_context,
                config,
            )

        self.assertIn('operator > tool proposed: write_file - "', result)
        self.assertEqual(proposal.pending_count(), 1)

    def test_process_observation_executes_without_proposal(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            _engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        engine = FlakySummaryEngine()
        process_faculty = ProcessFaculty()
        fake_result = ProcessResult(
            success=True,
            operation="list",
            query="python",
            records=[
                ProcessRecord(
                    pid=1234,
                    name="python.exe",
                    status="running",
                    cpu_percent=12.5,
                    memory_mb=256.0,
                    memory_percent=3.0,
                    username="ZAERA",
                    started_at="10:15",
                    cmdline="python app.py",
                )
            ],
            count=1,
        )

        with patch.object(process_faculty, "list_processes", return_value=fake_result):
            result = handle_command(
                "show me python processes",
                session,
                memory,
                proposal,
                state_report,
                engine,
                analyst,
                classifier,
                routing_log,
                startup_context,
                config,
                process_faculty=process_faculty,
            )

        self.assertIn("proc > processes", result)
        self.assertIn("python.exe", result)
        self.assertIn("model unavailable to summarize", result)
        self.assertEqual(proposal.pending_count(), 0)

    def test_run_command_request_creates_governed_tool_proposal(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "run echo hello",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertIn('operator > tool proposed: run_command - "echo hello"', result)
        self.assertEqual(proposal.pending_count(), 1)

    def test_kill_process_request_creates_governed_tool_proposal(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "kill process 1234",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertIn('operator > tool proposed: kill_process - "1234"', result)
        self.assertEqual(proposal.pending_count(), 1)

    def test_package_search_executes_without_proposal(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            _engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        engine = FlakySummaryEngine()
        package_faculty = PackageFaculty()
        fake_result = PackageResult(
            success=True,
            operation="search",
            query="text editor",
            records=[
                PackageRecord(
                    name="micro",
                    version="2.0.0",
                    description="terminal editor",
                    installed=False,
                )
            ],
            package_manager="apt",
        )

        with patch.object(package_faculty, "search", return_value=fake_result):
            result = handle_command(
                "search for a text editor",
                session,
                memory,
                proposal,
                state_report,
                engine,
                analyst,
                classifier,
                routing_log,
                startup_context,
                config,
                package_faculty=package_faculty,
            )

        self.assertIn("pkg [apt] > search: text editor", result)
        self.assertIn("micro 2.0.0", result)
        self.assertIn("model unavailable to summarize", result)
        self.assertEqual(proposal.pending_count(), 0)

    def test_install_package_request_creates_governed_tool_proposal(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "install firefox",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertIn('operator > tool proposed: install_package - "firefox"', result)
        self.assertEqual(proposal.pending_count(), 1)

    def test_remove_package_request_creates_governed_tool_proposal(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "remove firefox",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertIn('operator > tool proposed: remove_package - "firefox"', result)
        self.assertEqual(proposal.pending_count(), 1)

    def test_crown_response_with_reflect_tag_creates_reflection_proposal(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        root = session.session_path.parent.parent
        user_manager, session_state, token_store, user_log, faculty_monitor = self.make_user_context(root)
        reflective_memory = ReflectiveMemory(root / "self")

        with patch.object(
            classifier,
            "route",
            return_value=GovernanceResult(
                decision="allow",
                faculty="crown",
                reason="normal conversation",
            ),
        ), patch.object(
            engine,
            "respond",
            return_value=(
                "I notice I consistently provide more structured responses. "
                "[REFLECT: I tend toward structured formatting when reasoning about "
                "technical domains. | context: observed across multiple code analysis "
                "sessions]"
            ),
        ):
            result = handle_command(
                "tell me how you think",
                session,
                memory,
                proposal,
                state_report,
                engine,
                analyst,
                classifier,
                routing_log,
                startup_context,
                config,
                user_manager=user_manager,
                session_state=session_state,  # type: ignore[arg-type]
                token_store=token_store,
                user_log=user_log,
                faculty_monitor=faculty_monitor,
                reflective_memory=reflective_memory,
            )

        self.assertIn("inanna > I notice I consistently provide more structured responses.", result)
        self.assertIn("[REFLECTION PROPOSAL]", result)
        self.assertEqual(proposal.pending_count(), 1)
        pending = proposal.pending_records()[0]
        self.assertEqual(pending["payload"]["action"], "reflection")

    def test_my_departments_reports_current_context(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        root = session.session_path.parent.parent
        user_manager, session_state, token_store, user_log, faculty_monitor = self.make_user_context(root)
        profile_manager = ProfileManager(root / "profiles")
        active_user = session_state["active_user"]
        assert active_user is not None
        profile_manager.update_field(active_user.user_id, "departments", ["engineering", "research"])
        profile_manager.update_field(active_user.user_id, "groups", ["core-team"])

        result = handle_command(
            "my-departments",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
            token_store=token_store,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            profile_manager=profile_manager,
        )

        self.assertIn("Your organizational context:", result)
        self.assertIn("Departments  engineering, research", result)
        self.assertIn("Groups       core-team", result)

    def test_assign_department_updates_target_profile(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        root = session.session_path.parent.parent
        user_manager, session_state, token_store, user_log, faculty_monitor = self.make_user_context(root)
        profile_manager = ProfileManager(root / "profiles")
        guardian_user = session_state["active_user"]
        assert guardian_user is not None
        target = user_manager.create_user("Alice", "user", ["default"], guardian_user.user_id)

        result = handle_command(
            "assign-department Alice Engineering",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
            token_store=token_store,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            profile_manager=profile_manager,
            session_audit=[],
        )

        self.assertEqual("org > Alice assigned to department: engineering", result)
        self.assertEqual(profile_manager.load(target.user_id).departments, ["engineering"])

    def test_unassign_group_removes_target_membership(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        root = session.session_path.parent.parent
        user_manager, session_state, token_store, user_log, faculty_monitor = self.make_user_context(root)
        profile_manager = ProfileManager(root / "profiles")
        guardian_user = session_state["active_user"]
        assert guardian_user is not None
        target = user_manager.create_user("Alice", "user", ["default"], guardian_user.user_id)
        profile_manager.update_field(target.user_id, "groups", ["facilitators"])

        result = handle_command(
            "unassign-group Alice facilitators",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
            token_store=token_store,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            profile_manager=profile_manager,
            session_audit=[],
        )

        self.assertEqual("org > Alice removed from group: facilitators", result)
        self.assertEqual(profile_manager.load(target.user_id).groups, [])

    def test_notify_department_queues_notifications_for_matching_users(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        root = session.session_path.parent.parent
        user_manager, session_state, token_store, user_log, faculty_monitor = self.make_user_context(root)
        profile_manager = ProfileManager(root / "profiles")
        guardian_user = session_state["active_user"]
        assert guardian_user is not None
        alice = user_manager.create_user("Alice", "user", ["default"], guardian_user.user_id)
        bob = user_manager.create_user("Bob", "user", ["default"], guardian_user.user_id)
        profile_manager.update_field(alice.user_id, "departments", ["engineering"])
        profile_manager.update_field(bob.user_id, "departments", ["research"])

        result = handle_command(
            "notify-department engineering Standup in 10 minutes.",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
            token_store=token_store,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            profile_manager=profile_manager,
            session_audit=[],
        )

        alice_notifications = json.loads(
            (root / "notifications" / f"{alice.user_id}.json").read_text(encoding="utf-8")
        )
        self.assertEqual("org > Department engineering notified (1 recipient(s)).", result)
        self.assertEqual(len(alice_notifications), 1)
        self.assertEqual(alice_notifications[0]["department"], "engineering")
        self.assertFalse((root / "notifications" / f"{bob.user_id}.json").exists())

    def test_tool_registry_command_lists_registered_tools(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "tool-registry",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertIn("tool-registry > Registered tools (31 total):", result)
        self.assertIn("COMMUNICATION", result)
        self.assertIn("Read Messages [enabled]", result)
        self.assertIn("Send Message [enabled]", result)
        self.assertIn("List Contacts [enabled]", result)
        self.assertIn("EMAIL", result)
        self.assertIn("Read Email Inbox [enabled]", result)
        self.assertIn("Read Email [enabled]", result)
        self.assertIn("Search Emails [enabled]", result)
        self.assertIn("Compose Email Draft [enabled]", result)
        self.assertIn("Reply Draft [enabled]", result)
        self.assertIn("DESKTOP", result)
        self.assertIn("Open Application [enabled]", result)
        self.assertIn("Read Window Content [enabled]", result)
        self.assertIn("Click UI Element [enabled]", result)
        self.assertIn("Type Text [enabled]", result)
        self.assertIn("Take Screenshot [enabled]", result)
        self.assertIn("FILESYSTEM", result)
        self.assertIn("Read File [enabled]", result)
        self.assertIn("List Directory [enabled]", result)
        self.assertIn("File Info [enabled]", result)
        self.assertIn("Search Files [enabled]", result)
        self.assertIn("Write File [enabled]", result)
        self.assertIn("PROCESS", result)
        self.assertIn("List Processes [enabled]", result)
        self.assertIn("System Info [enabled]", result)
        self.assertIn("Kill Process [enabled]", result)
        self.assertIn("Run Command [enabled]", result)
        self.assertIn("PACKAGE", result)
        self.assertIn("Search Packages [enabled]", result)
        self.assertIn("List Packages [enabled]", result)
        self.assertIn("Install Package [enabled]", result)
        self.assertIn("Remove Package [enabled]", result)
        self.assertIn("Launch Application [enabled]", result)
        self.assertIn("INFORMATION", result)
        self.assertIn("Web Search [enabled]", result)
        self.assertIn("Privilege: converse", result)
        self.assertIn("NETWORK", result)
        self.assertIn("Ping Host [enabled]", result)
        self.assertIn("Resolve Host [enabled]", result)
        self.assertIn("Port Scan [enabled]", result)
        self.assertIn("Privilege: network_tools", result)

    def test_faculty_registry_command_lists_all_configured_faculties(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        faculty_monitor = FacultyMonitor()
        faculty_monitor.record_call("crown", 123.0, True)

        result = handle_command(
            "faculty-registry",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            faculty_monitor=faculty_monitor,
        )

        self.assertIn("faculty-registry > Faculties (5 total):", result)
        self.assertIn("active: 5  inactive: 0", result)
        self.assertIn("CROWN [unavailable]", result)
        self.assertIn("SENTINEL [ready]", result)
        self.assertIn("security · Cybersecurity analysis", result)

    def test_network_status_command_summarizes_recent_network_activity(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        session_audit = [
            {
                "timestamp": "2026-04-20T10:00:00+00:00",
                "event_type": "tool_use",
                "tool": "ping",
                "host": "8.8.8.8",
                "result": "reachable",
            },
            {
                "timestamp": "2026-04-20T10:02:00+00:00",
                "event_type": "tool_use",
                "tool": "resolve_host",
                "host": "google.com",
                "result": "142.250.0.1",
            },
            {
                "timestamp": "2026-04-20T10:03:00+00:00",
                "event_type": "invite",
                "summary": "not network",
            },
        ]

        result = handle_command(
            "network-status",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            session_audit=session_audit,
        )

        self.assertIn("network-status > Recent network activity (2 total):", result)
        self.assertIn("[resolve_host] google.com -> 142.250.0.1", result)
        self.assertIn("[ping] 8.8.8.8 -> reachable", result)

    def test_process_status_command_reports_live_processes(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "process-status",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            process_monitor=ProcessMonitor(time.time() - 90),
        )

        self.assertIn("process-status > Live process view:", result)
        self.assertIn("[running] INANNA NYX Server", result)
        self.assertIn("uptime: 1m 30s", result)
        self.assertIn("LM Studio", result)

    def test_guardian_dismiss_returns_acknowledgement(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "guardian-dismiss",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertEqual("guardian > alerts dismissed.", result)

    def test_guardian_clear_events_clears_session_audit(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        session_audit = [
            {"timestamp": "2026-04-20T09:00:00+00:00", "event_type": "guardian", "summary": "warn"},
            {"timestamp": "2026-04-20T09:01:00+00:00", "event_type": "invite", "summary": "created"},
        ]

        result = handle_command(
            "guardian-clear-events",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            session_audit=session_audit,
        )

        self.assertEqual("guardian > cleared 2 governance event(s).", result)
        self.assertEqual([], session_audit)

    def test_admin_surface_lists_visible_users_invites_and_realms(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        root = session.session_path.parent.parent
        user_manager, session_state, _, _, _ = self.make_user_context(root)
        guardian_user = session_state["active_user"]
        assert guardian_user is not None
        user_log = UserLog(root / "user_logs")
        profile_manager = ProfileManager(root / "profiles")
        user_log.append(
            guardian_user.user_id,
            session.session_id,
            "user",
            "hello",
            "world",
        )
        realm_manager = RealmManager(root)
        realm_manager.ensure_default_realm()
        realm_manager.create_realm("work", purpose="Focused work.")
        user_manager.create_user("Alice", "user", ["work"], guardian_user.user_id)
        profile_manager.update_field(guardian_user.user_id, "departments", ["oversight"])
        alice = user_manager.get_user_by_display_name("Alice")
        assert alice is not None
        profile_manager.update_field(alice.user_id, "departments", ["engineering"])
        profile_manager.update_field(alice.user_id, "groups", ["core-team"])
        user_manager.create_invite("user", ["work"], guardian_user.user_id)

        result = handle_command(
            "admin-surface",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            realm_manager=realm_manager,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
            user_log=user_log,
            profile_manager=profile_manager,
        )

        self.assertIn("admin-surface > Users: 2  Invites: 1  Realms: 2", result)
        self.assertIn("USERS", result)
        self.assertIn("ZAERA", result)
        self.assertIn("Alice", result)
        self.assertIn("departments: engineering", result)
        self.assertIn("groups: core-team", result)
        self.assertIn("INVITES", result)
        self.assertIn("REALMS", result)
        self.assertIn("[work]", result)

    def test_admin_surface_operator_is_realm_scoped(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        root = session.session_path.parent.parent
        user_manager, session_state, token_store, _, _ = self.make_user_context(root)
        guardian_user = session_state["active_user"]
        assert guardian_user is not None
        realm_manager = RealmManager(root)
        realm_manager.ensure_default_realm()
        realm_manager.create_realm("work", purpose="Focused work.")
        realm_manager.create_realm("private", purpose="Private realm.")
        operator = user_manager.create_user("OperatorOne", "operator", ["work"], guardian_user.user_id)
        user_manager.create_user("PrivateUser", "user", ["private"], guardian_user.user_id)
        user_manager.create_invite("user", ["private"], guardian_user.user_id)
        user_manager.create_invite("user", ["work"], guardian_user.user_id)
        session_state["active_user"] = operator
        session_state["active_token"] = token_store.issue(
            operator.user_id,
            operator.display_name,
            operator.role,
        )

        result = handle_command(
            "admin-surface",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            realm_manager=realm_manager,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
            user_log=UserLog(root / "user_logs"),
        )

        self.assertIn("OperatorOne", result)
        self.assertIn("[work]", result)
        self.assertNotIn("PrivateUser", result)
        self.assertNotIn("[private]", result)

    def test_create_realm_requires_proposal_and_creates_realm_on_approval(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        root = session.session_path.parent.parent
        user_manager, session_state, _, _, _ = self.make_user_context(root)
        realm_manager = RealmManager(root)
        active_realm = realm_manager.ensure_default_realm()

        proposal_result = handle_command(
            "create-realm archive Long term archive",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            realm_manager=realm_manager,
            active_realm=active_realm,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
        )

        self.assertIn("create-realm > proposal required to create a new realm.", proposal_result)
        self.assertIn("[REALM PROPOSAL]", proposal_result)
        self.assertFalse(realm_manager.realm_exists("archive"))

        approval_result = handle_command(
            "approve",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            realm_manager=realm_manager,
            active_realm=active_realm,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
        )

        self.assertEqual("create-realm > Realm archive created.", approval_result)
        self.assertTrue(realm_manager.realm_exists("archive"))
        created = realm_manager.load_realm("archive")
        assert created is not None
        self.assertEqual("Long term archive", created.purpose)

    def test_users_command_lists_guardian_user(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        root = session.session_path.parent.parent
        user_manager, session_state, _, _, _ = self.make_user_context(root)

        result = handle_command(
            "users",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
        )

        self.assertIn("Users (1 total):", result)
        self.assertIn("ZAERA", result)

    def test_create_user_proposal_uses_active_token_user_id_as_created_by(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        root = session.session_path.parent.parent
        user_manager, session_state, token_store, user_log, faculty_monitor = self.make_user_context(
            root
        )

        result = handle_command(
            "create-user Alice user default",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
            token_store=token_store,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            session_audit=[],
        )
        approval = handle_command(
            "approve",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
            token_store=token_store,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            session_audit=[],
        )
        created = user_manager.get_user_by_display_name("Alice")

        self.assertIn("[USER PROPOSAL]", result)
        self.assertIsNotNone(created)
        self.assertEqual(created.created_by, session_state["active_token"].user_id)
        self.assertIn("User created: Alice", approval)

    def test_login_whoami_and_logout_commands_manage_session_identity(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        root = session.session_path.parent.parent
        user_manager, session_state, token_store, user_log, faculty_monitor = self.make_user_context(
            root
        )
        user_manager.create_user("Alice", "user", ["default"], "system")

        login_result = handle_command(
            "login Alice",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
            token_store=token_store,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            session_audit=[],
        )
        whoami_result = handle_command(
            "whoami",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
            token_store=token_store,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            session_audit=[],
        )
        logout_result = handle_command(
            "logout",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
            token_store=token_store,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            session_audit=[],
        )

        self.assertIn("login > session started for Alice (user)", login_result)
        self.assertIn("whoami > Alice (user)", whoami_result)
        self.assertIn("whoami > session token:", whoami_result)
        self.assertEqual(logout_result, "logout > session ended for Alice")

    def test_login_delivers_pending_department_notifications(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        root = session.session_path.parent.parent
        user_manager, session_state, token_store, user_log, faculty_monitor = self.make_user_context(
            root
        )
        profile_manager = ProfileManager(root / "profiles")
        alice = user_manager.create_user("Alice", "user", ["default"], "system")
        profile_manager.ensure_profile_exists(alice.user_id)
        NotificationStore(root / "notifications").add(
            alice.user_id,
            {
                "notification_id": "notif-1",
                "from": "guardian",
                "department": "engineering",
                "message": "Standup in 10 minutes.",
                "created_at": "2026-04-20T10:00:00+00:00",
                "delivered": False,
            },
        )

        login_result = handle_command(
            "login Alice",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
            token_store=token_store,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            session_audit=[],
            profile_manager=profile_manager,
        )

        self.assertIn(
            "\U0001F4E2 [engineering notification] Standup in 10 minutes.",
            login_result,
        )
        self.assertFalse((root / "notifications" / f"{alice.user_id}.json").exists())

    def test_faculties_command_returns_faculty_monitor_report(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        faculty_monitor = FacultyMonitor()
        faculty_monitor.record_call("crown", 123.0, True)

        result = handle_command(
            "faculties",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            faculty_monitor=faculty_monitor,
        )

        self.assertIn("Faculty Monitor:", result)
        self.assertIn("CROWN", result)
        self.assertIn("GUARDIAN", result)

    def test_my_log_reads_active_user_log(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        root = session.session_path.parent.parent
        user_manager, session_state, token_store, user_log, faculty_monitor = self.make_user_context(
            root
        )
        active_token = session_state["active_token"]
        user_log.append(
            active_token.user_id,
            session.session_id,
            "user",
            "Hello, I am ZAERA",
            "Hello ZAERA! It is wonderful to have you here...",
        )

        result = handle_command(
            "my-log",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
            token_store=token_store,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            session_audit=[],
        )

        self.assertIn("Your interaction log (1 entries):", result)
        self.assertIn("Hello, I am ZAERA", result)

    def test_user_log_reads_named_user_history_for_guardian(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        root = session.session_path.parent.parent
        user_manager, session_state, token_store, user_log, faculty_monitor = self.make_user_context(
            root
        )
        alice = user_manager.create_user("Alice", "user", ["default"], "system")
        user_log.append(
            alice.user_id,
            session.session_id,
            "user",
            "What is the nature of consciousness?",
            "That is one of the deepest questions in philosophy...",
        )

        result = handle_command(
            "user-log Alice",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
            token_store=token_store,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            session_audit=[],
        )

        self.assertIn(f"Interaction log for Alice ({alice.user_id}) (1 entries):", result)
        self.assertIn("What is the nature of consciousness?", result)

    def test_invite_join_and_invites_commands_recover_governed_invite_flow(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        root = session.session_path.parent.parent
        user_manager, session_state, token_store, user_log, faculty_monitor = self.make_user_context(
            root
        )
        audit: list[dict[str, str]] = []

        proposal_result = handle_command(
            "invite user default",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
            token_store=token_store,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            session_audit=audit,
        )
        approval_result = handle_command(
            "approve",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
            token_store=token_store,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            session_audit=audit,
        )
        invite_code = next(
            line.split(": ", 1)[1]
            for line in approval_result.splitlines()
            if line.startswith("invite > Code:")
        )
        invites_result = handle_command(
            "invites",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
            token_store=token_store,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            session_audit=audit,
        )
        join_result = handle_command(
            f"join {invite_code} Alice",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
            token_store=token_store,
            user_log=user_log,
            faculty_monitor=faculty_monitor,
            session_audit=audit,
        )

        self.assertIn("[INVITE PROPOSAL]", proposal_result)
        self.assertIn("invite > Invite created.", approval_result)
        self.assertIn(invite_code, invites_result)
        self.assertIn("join > Welcome, Alice.", join_result)
        self.assertEqual(session_state["active_user"].display_name, "Alice")

    def test_realms_command_lists_available_realms(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        realm_manager = RealmManager(session.session_path.parent.parent / "data")
        active_realm = realm_manager.ensure_default_realm()
        realm_manager.create_realm("work", purpose="Work-related conversations and analysis.")

        result = handle_command(
            "realms",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            realm_manager=realm_manager,
            active_realm=active_realm,
        )

        self.assertIn("realms > Available realms (2):", result)
        self.assertIn("[default]  The default operational context.", result)
        self.assertIn("[work]  Work-related conversations and analysis.", result)
        self.assertIn("Active: default", result)

    def test_realm_context_command_reports_active_realm_details(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        realm_manager = RealmManager(session.session_path.parent.parent / "data")
        active_realm = realm_manager.create_realm(
            "work",
            purpose="Work-related conversations and analysis.",
            governance_context="Focus on work memory boundaries.",
        )

        result = handle_command(
            "realm-context",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            realm_manager=realm_manager,
            active_realm=active_realm,
        )

        self.assertIn("Active realm: work", result)
        self.assertIn("Purpose: Work-related conversations and analysis.", result)
        self.assertIn("Governance context: Focus on work memory boundaries.", result)

    def test_realm_context_update_is_proposal_governed_and_updates_realm_on_approval(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        realm_manager = RealmManager(session.session_path.parent.parent / "data")
        active_realm = realm_manager.create_realm(
            "work",
            purpose="Work-related conversations and analysis.",
            governance_context="Initial context.",
        )

        proposal_result = handle_command(
            "realm-context Focus on work memory boundaries.",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            realm_manager=realm_manager,
            active_realm=active_realm,
        )
        approval_result = handle_command(
            "approve",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            realm_manager=realm_manager,
            active_realm=active_realm,
        )
        loaded = realm_manager.load_realm("work")

        self.assertIn("[REALM PROPOSAL]", proposal_result)
        self.assertEqual(
            approval_result,
            "Approved " + proposal.history_report()["records"][0]["proposal_id"]
            + " and updated governance context for realm work.",
        )
        assert loaded is not None
        self.assertEqual(loaded.governance_context, "Focus on work memory boundaries.")

    def test_assign_realm_command_creates_proposal_and_updates_user_on_approval(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        root = session.session_path.parent.parent
        user_manager, session_state, _, _, _ = self.make_user_context(root)
        alice = user_manager.create_user(
            display_name="Alice",
            role="user",
            assigned_realms=["default"],
            created_by="system",
        )

        proposal_result = handle_command(
            "assign-realm Alice work",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
        )
        approval_result = handle_command(
            "approve",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
        )
        updated = user_manager.get_user(alice.user_id)

        self.assertIn("[REALM PROPOSAL]", proposal_result)
        self.assertEqual(approval_result, "assign-realm > Realm work assigned to Alice.")
        assert updated is not None
        self.assertIn("work", updated.assigned_realms)

    def test_unassign_realm_command_protects_last_realm(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        root = session.session_path.parent.parent
        user_manager, session_state, _, _, _ = self.make_user_context(root)
        user_manager.create_user(
            display_name="Alice",
            role="user",
            assigned_realms=["default"],
            created_by="system",
        )

        proposal_result = handle_command(
            "unassign-realm Alice default",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
        )
        approval_result = handle_command(
            "approve",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
        )

        self.assertIn("[REALM PROPOSAL]", proposal_result)
        self.assertEqual(approval_result, "unassign-realm > Cannot remove last realm for Alice.")

    def test_switch_user_warns_when_target_lacks_current_realm(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        root = session.session_path.parent.parent
        user_manager, session_state, _, _, _ = self.make_user_context(root)
        user_manager.create_user(
            display_name="Alice",
            role="user",
            assigned_realms=["default"],
            created_by="system",
        )
        realm_manager = RealmManager(root / "realm-data")
        active_realm = realm_manager.create_realm("work")

        result = handle_command(
            "switch-user Alice",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            active_realm=active_realm,
            user_manager=user_manager,
            session_state=session_state,  # type: ignore[arg-type]
        )

        self.assertIn("switch-user > Now operating as: Alice (user)", result)
        self.assertIn("switch-user > Warning: Alice does not have access to realm work.", result)
        self.assertIn("switch-user > Operating as Alice in an unassigned realm.", result)
        self.assertIn("switch-user > Use assign-realm to grant access.", result)

    def test_nammu_log_with_no_history_reports_empty_persistent_state(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "nammu-log",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertIn("NAMMU Memory (0 routing, 0 governance):", result)
        self.assertIn("No persisted routing history yet.", result)
        self.assertIn("No persisted governance history yet.", result)

    def test_guardian_returns_report_without_side_effects(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "guardian",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertTrue(result.startswith("guardian > Guardian Report ("))
        self.assertIn("SYSTEM_HEALTHY", result)
        self.assertEqual(proposal.pending_count(), 0)
        self.assertEqual(memory.memory_count(), 0)
        self.assertEqual(session.events, [])

    def test_tool_resilience_returns_clean_operator_message(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            _engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        engine = FlakySummaryEngine()
        proposal.create(
            what="web_search tool use",
            why="test",
            payload={
                "action": "tool_use",
                "tool": "web_search",
                "query": "latest weather",
                "original_input": "what is the weather today",
                "session_id": session.session_id,
            },
        )

        result = handle_command(
            "approve",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            operator=SuccessfulToolOperator(),
            guardian_metrics={"governance_blocks": 0, "tool_executions": 0},
        )

        self.assertIn("operator > search result:", result)
        self.assertIn("operator > model unavailable to summarize. Raw results shown above.", result)
        self.assertNotIn("inanna >", result)

    def test_forget_cancel_returns_no_memory_removed(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        self.write_memory_record(memory)

        result, output, prompts = self.run_forget_command(
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            ["cancel"],
        )

        self.assertEqual(result, "No memory removed.")
        self.assertIn("Memory log (1 records):", output)
        self.assertEqual(
            prompts,
            ['Which memory record to remove? Enter memory_id or "cancel":'],
        )
        self.assertEqual(memory.memory_count(), 1)
        self.assertEqual(proposal.history_report()["total"], 0)
        self.assertEqual(len(routing_log), 0)

    def test_forget_approve_removes_memory_after_inline_proposal(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        self.write_memory_record(memory, "proposal-a")

        result, output, prompts = self.run_forget_command(
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            ["proposal-a", "approve"],
        )

        history = proposal.history_report()
        self.assertEqual(result, "Memory record proposal-a removed.")
        self.assertIn("[PROPOSAL]", output)
        self.assertEqual(
            prompts,
            [
                'Which memory record to remove? Enter memory_id or "cancel":',
                'Type "approve" to confirm removal or "reject" to cancel:',
            ],
        )
        self.assertEqual(memory.memory_count(), 0)
        self.assertEqual(history["approved"], 1)
        self.assertEqual(history["rejected"], 0)
        self.assertEqual(
            history["records"][0]["payload"],
            {"memory_id": "proposal-a", "action": "forget"},
        )

    def test_forget_reject_retains_memory(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        self.write_memory_record(memory, "proposal-a")

        result, output, prompts = self.run_forget_command(
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            ["proposal-a", "reject"],
        )

        history = proposal.history_report()
        self.assertEqual(result, "Memory record retained.")
        self.assertIn("[PROPOSAL]", output)
        self.assertEqual(
            prompts,
            [
                'Which memory record to remove? Enter memory_id or "cancel":',
                'Type "approve" to confirm removal or "reject" to cancel:',
            ],
        )
        self.assertEqual(memory.memory_count(), 1)
        self.assertEqual(history["approved"], 0)
        self.assertEqual(history["rejected"], 1)

    def test_reflect_with_empty_context_returns_no_memory_message(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "reflect",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertEqual(
            result,
            "inanna> [memory fallback] I hold no approved memory of our prior conversations yet.",
        )
        self.assertEqual(proposal.pending_count(), 0)
        self.assertEqual(len(routing_log), 0)

    def test_approve_with_no_pending_proposals_returns_honest_message(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "approve",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertEqual(result, "No pending proposals.")

    def test_explicit_analyse_remains_direct_override(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "analyse What patterns do you see?",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertTrue(result.startswith("analyst > [analysis fallback] "))
        self.assertNotIn("nammu >", result)
        self.assertEqual(proposal.pending_count(), 0)
        self.assertEqual(len(routing_log), 0)

    def test_conversation_turn_auto_writes_memory_at_threshold(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        conversation_state = {"turn_count": 19, "last_auto_memory_turn": 0}
        session_audit: list[dict[str, object]] = []

        result = handle_command(
            "hello there",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            conversation_state=conversation_state,
            session_audit=session_audit,  # type: ignore[arg-type]
        )

        self.assertIn("inanna >", result)
        self.assertEqual(conversation_state["turn_count"], 20)
        self.assertEqual(conversation_state["last_auto_memory_turn"], 20)
        self.assertEqual(memory.memory_count(), 1)
        self.assertEqual(proposal.pending_count(), 0)
        record = memory.memory_log_report()["records"][0]
        self.assertTrue(
            record["memory_id"].startswith(f"auto-memory-{session.session_id}-threshold-20-")
        )
        self.assertTrue(any("hello there" in line for line in record["summary_lines"]))
        self.assertTrue(
            any(
                event["event_type"] == "auto_memory"
                and "threshold" in str(event["summary"])
                for event in session_audit
            )
        )

    def test_finalize_auto_memory_writes_remaining_turns_on_session_end(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()
        conversation_state = {"turn_count": 0, "last_auto_memory_turn": 0}
        session_audit: list[dict[str, object]] = []

        handle_command(
            "hello there",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
            conversation_state=conversation_state,
            session_audit=session_audit,  # type: ignore[arg-type]
        )

        written = finalize_auto_memory(
            conversation_state=conversation_state,
            memory=memory,
            session=session,
            active_realm_name="default",
            active_token=None,
            user_log=None,
            session_audit=session_audit,
        )

        self.assertIsNotNone(written)
        self.assertEqual(conversation_state["last_auto_memory_turn"], 1)
        self.assertEqual(memory.memory_count(), 1)
        self.assertEqual(proposal.pending_count(), 0)
        record = memory.memory_log_report()["records"][0]
        self.assertTrue(
            record["memory_id"].startswith(f"auto-memory-{session.session_id}-session-end-1-")
        )
        self.assertTrue(
            any(
                event["event_type"] == "auto_memory"
                and "session end" in str(event["summary"])
                for event in session_audit
            )
        )

    def test_unknown_input_is_auto_routed_to_crown_and_logged(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "hello there",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertIn("nammu > routing to crown faculty", result)
        self.assertIn("inanna >", result)
        self.assertEqual(proposal.pending_count(), 0)
        self.assertEqual(len(routing_log), 1)
        self.assertEqual(routing_log[0]["route"], "crown")

    def test_normal_input_can_be_auto_routed_to_analyst_and_logged(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        result = handle_command(
            "Explain why governance needs readable limits",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertIn("nammu > routing to analyst faculty", result)
        self.assertIn("analyst > [analysis fallback] ", result)
        self.assertEqual(proposal.pending_count(), 0)
        self.assertEqual(len(routing_log), 1)
        self.assertEqual(routing_log[0]["route"], "analyst")

    def test_routing_log_reports_recorded_decisions(self) -> None:
        (
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        ) = self.make_runtime()

        handle_command(
            "hello there",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        result = handle_command(
            "routing-log",
            session,
            memory,
            proposal,
            state_report,
            engine,
            analyst,
            classifier,
            routing_log,
            startup_context,
            config,
        )

        self.assertIn("NAMMU Routing Log (1 decisions):", result)
        self.assertIn("[crown]", result)
        self.assertIn("hello there", result)


if __name__ == "__main__":
    unittest.main()
