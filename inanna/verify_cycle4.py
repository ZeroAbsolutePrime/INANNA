from __future__ import annotations

import inspect
import json
import re
import subprocess
import sys
from dataclasses import fields
from pathlib import Path
from tempfile import TemporaryDirectory

from core.faculty_monitor import FacultyMonitor
from core.memory import Memory
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
from identity import CURRENT_PHASE, CYCLE4_PREVIEW, CYCLE4_SUMMARY
from main import STARTUP_COMMANDS, handle_command


APP_ROOT = Path(__file__).resolve().parent
ROLES_CONFIG_PATH = APP_ROOT / "config" / "roles.json"
REQUIRED_CYCLE4_COMMANDS = (
    "login",
    "logout",
    "whoami",
    "users",
    "create-user",
    "invite",
    "join",
    "invites",
    "my-log",
    "user-log",
    "assign-realm",
    "unassign-realm",
    "switch-user",
    "admin-surface",
    "create-realm",
    "guardian-clear-events",
    "guardian-dismiss",
)


class CheckRunner:
    def __init__(self) -> None:
        self.checks: list[tuple[str, bool, str]] = []

    def check(self, label: str, condition: bool, detail: str = "") -> None:
        self.checks.append((label, condition, detail))

    def finish(self) -> int:
        print("INANNA NYX - Cycle 4 Integration Verification")
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
            print(f"All {total} checks passed. Cycle 4 architecture verified.")
            return 0

        print(f"{passed_count} of {total} checks passed. Cycle 4 verification failed.")
        return 1


def run_script(path: Path) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, str(path)],
        cwd=APP_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    detail = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else result.stderr.strip()
    return result.returncode == 0, detail


def main() -> int:
    runner = CheckRunner()

    runner.check("Roles config: config/roles.json exists", ROLES_CONFIG_PATH.exists())
    payload = json.loads(ROLES_CONFIG_PATH.read_text(encoding="utf-8"))
    roles = payload.get("roles", {})
    runner.check(
        "Roles config: exactly three roles are defined",
        sorted(roles.keys()) == ["guardian", "operator", "user"],
        detail=str(sorted(roles.keys())),
    )
    runner.check(
        "Roles config: guardian has all privilege",
        roles.get("guardian", {}).get("privileges") == ["all"],
    )
    runner.check(
        "Roles config: operator has invite_users privilege",
        "invite_users" in roles.get("operator", {}).get("privileges", []),
    )
    runner.check(
        "Roles config: user has converse and approve_own_memory",
        {"converse", "approve_own_memory"}.issubset(
            set(roles.get("user", {}).get("privileges", []))
        ),
    )

    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        custom_roles = root / "roles.json"
        custom_roles.write_text(
            json.dumps(
                {
                    "roles": {
                        "guardian": {"description": "all", "privileges": ["all"]},
                        "operator": {"description": "custom", "privileges": ["custom_invite"]},
                        "user": {"description": "custom", "privileges": ["custom_converse"]},
                    }
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        custom_manager = UserManager(data_root=root / "custom", roles_config_path=custom_roles)
        runner.check(
            "Roles config: privileges are read from JSON at runtime",
            custom_manager.get_role_privileges("operator") == ["custom_invite"]
            and custom_manager.get_role_privileges("user") == ["custom_converse"],
        )

    user_fields = {field.name for field in fields(UserRecord)}
    invite_fields = {field.name for field in fields(InviteRecord)}
    token_fields = {field.name for field in fields(SessionToken)}
    runner.check(
        "User identity: UserRecord dataclass has all required fields",
        {
            "user_id",
            "display_name",
            "role",
            "assigned_realms",
            "created_at",
            "created_by",
            "status",
        }.issubset(user_fields),
    )
    runner.check(
        "Invite flow: InviteRecord dataclass has all required fields",
        {
            "invite_code",
            "role",
            "assigned_realms",
            "created_by",
            "created_at",
            "expires_at",
            "status",
            "accepted_by",
        }.issubset(invite_fields),
    )
    runner.check(
        "Session token: SessionToken dataclass has all required fields",
        {
            "token",
            "user_id",
            "display_name",
            "role",
            "issued_at",
            "expires_at",
            "active",
        }.issubset(token_fields),
    )

    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        roles_path = root / "roles.json"
        roles_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        user_manager = UserManager(data_root=root, roles_config_path=roles_path)
        runner.check("User identity: UserManager can be instantiated", isinstance(user_manager, UserManager))

        guardian_first = ensure_guardian_exists(user_manager)
        guardian_second = ensure_guardian_exists(user_manager)
        runner.check(
            "User identity: ensure_guardian_exists creates ZAERA on first call",
            guardian_first.display_name == "ZAERA" and guardian_first.role == "guardian",
        )
        runner.check(
            "User identity: ensure_guardian_exists returns the existing Guardian on repeat call",
            guardian_first.user_id == guardian_second.user_id,
        )

        created_user = user_manager.create_user(
            display_name="Alice",
            role="user",
            assigned_realms=["work"],
            created_by=guardian_first.user_id,
        )
        user_path = root / "users" / f"{created_user.user_id}.json"
        stored_user = json.loads(user_path.read_text(encoding="utf-8"))
        runner.check("User identity: create_user stores JSON to disk", user_path.exists())
        runner.check(
            "User identity: get_user returns the correct UserRecord",
            user_manager.get_user(created_user.user_id) == created_user,
        )
        runner.check(
            "User identity: stored JSON matches the created user",
            stored_user["display_name"] == "Alice" and stored_user["role"] == "user",
        )
        listed_users = user_manager.list_users()
        runner.check(
            "User identity: list_users returns all users",
            {record.display_name for record in listed_users} == {"ZAERA", "Alice"},
        )

        operator = user_manager.create_user(
            display_name="OperatorOne",
            role="operator",
            assigned_realms=["work"],
            created_by=guardian_first.user_id,
        )
        runner.check(
            "User identity: has_privilege is correct for guardian",
            user_manager.has_privilege(guardian_first.user_id, "invite_users"),
        )
        runner.check(
            "User identity: has_privilege is correct for operator",
            user_manager.has_privilege(operator.user_id, "invite_users"),
        )
        runner.check(
            "User identity: has_privilege is correct for user",
            user_manager.has_privilege(created_user.user_id, "converse"),
        )

        runner.check(
            "User identity: can_access_realm is true for assigned realm",
            can_access_realm(created_user, "work"),
        )
        runner.check(
            "User identity: can_access_realm is false for unassigned realm",
            not can_access_realm(created_user, "private"),
        )
        assign_result = user_manager.assign_realm(created_user.user_id, "private")
        updated_user = user_manager.get_user(created_user.user_id)
        runner.check(
            "User identity: assign_realm adds a realm correctly",
            assign_result and updated_user is not None and "private" in updated_user.assigned_realms,
        )
        unassign_result = user_manager.unassign_realm(created_user.user_id, "private")
        updated_user = user_manager.get_user(created_user.user_id)
        runner.check(
            "User identity: unassign_realm removes the realm correctly",
            unassign_result and updated_user is not None and "private" not in updated_user.assigned_realms,
        )

        invite = user_manager.create_invite("user", ["work"], guardian_first.user_id)
        runner.check(
            "Invite flow: create_invite generates INANNA-XXXX-XXXX codes",
            re.fullmatch(r"INANNA-[A-Z]{4}-[A-Z]{4}", invite.invite_code) is not None,
        )
        accepted = user_manager.accept_invite(invite.invite_code, "Bob")
        refreshed_invite = user_manager.get_invite(invite.invite_code)
        runner.check(
            "Invite flow: accept_invite creates a user",
            accepted is not None and accepted.display_name == "Bob",
        )
        runner.check(
            "Invite flow: accept_invite marks the invite accepted",
            refreshed_invite is not None and refreshed_invite.status == "accepted",
        )
        runner.check(
            "Invite flow: double-accept returns None",
            user_manager.accept_invite(invite.invite_code, "Again") is None,
        )

        expired = user_manager.create_invite("user", ["work"], guardian_first.user_id)
        expired_path = root / "invites" / f"{expired.invite_code}.json"
        expired_payload = json.loads(expired_path.read_text(encoding="utf-8"))
        expired_payload["expires_at"] = "2000-01-01T00:00:00+00:00"
        expired_path.write_text(json.dumps(expired_payload, indent=2), encoding="utf-8")
        runner.check(
            "Invite flow: expired invite returns None from accept_invite",
            user_manager.accept_invite(expired.invite_code, "LateUser") is None,
        )
        pending_invite = user_manager.create_invite("operator", ["work"], guardian_first.user_id)
        runner.check(
            "Invite flow: list_invites filters by status correctly",
            any(item.invite_code == pending_invite.invite_code for item in user_manager.list_invites("pending"))
            and all(item.status == "accepted" for item in user_manager.list_invites("accepted")),
        )

        token_store = TokenStore()
        token = token_store.issue(guardian_first.user_id, guardian_first.display_name, guardian_first.role)
        runner.check("Session token: TokenStore.issue returns a SessionToken", isinstance(token, SessionToken))
        runner.check(
            "Session token: validate returns a record for a valid token",
            token_store.validate(token.token) is not None,
        )
        runner.check(
            "Session token: validate returns None for an unknown token",
            token_store.validate("missing-token") is None,
        )
        runner.check(
            "Session token: revoke deactivates a token",
            token_store.revoke(token.token) and token_store.validate(token.token) is None,
        )
        second = token_store.issue(created_user.user_id, created_user.display_name, created_user.role)
        third = token_store.issue(created_user.user_id, created_user.display_name, created_user.role)
        runner.check(
            "Session token: validate returns None for a revoked token",
            token_store.validate(second.token) is None,
        )
        runner.check(
            "Session token: one active token per user is enforced on issue",
            not second.active and third.active and token_store.validate(third.token) is not None,
        )

        runner.check(
            "Privilege map: check_privilege returns false for no active session",
            check_privilege(None, user_manager, "converse")[0] is False,
        )
        guardian_check = check_privilege(guardian_first, user_manager, "invite_users")
        runner.check(
            "Privilege map: guardian succeeds for any privilege",
            guardian_check == (True, ""),
            detail=str(guardian_check),
        )
        user_check = check_privilege(created_user, user_manager, "converse")
        runner.check(
            "Privilege map: user succeeds for converse",
            user_check == (True, ""),
            detail=str(user_check),
        )
        denied_check = check_privilege(created_user, user_manager, "all")
        runner.check(
            "Privilege map: user fails for all privilege with a reason",
            denied_check[0] is False and "Insufficient privileges." in denied_check[1],
            detail=str(denied_check),
        )

        session_dir = root / "sessions"
        memory_dir = root / "memory"
        session_dir.mkdir()
        memory_dir.mkdir()
        memory = Memory(session_dir=session_dir, memory_dir=memory_dir)
        runner.check(
            "User memory: Memory.write_memory accepts a user_id parameter",
            "user_id" in inspect.signature(Memory.write_memory).parameters,
        )
        memory.write_memory(
            proposal_id="proposal-a",
            session_id="session-1",
            summary_lines=["user: alpha"],
            approved_at="2026-04-20T08:00:00+00:00",
            user_id="user_alpha",
        )
        memory.write_memory(
            proposal_id="proposal-b",
            session_id="session-2",
            summary_lines=["user: beta"],
            approved_at="2026-04-20T08:30:00+00:00",
            user_id="user_beta",
        )
        alpha_records = memory.load_memory_records(user_id="user_alpha")
        beta_records = memory.load_memory_records(user_id="user_beta")
        stored_memory = json.loads((memory_dir / "proposal-a.json").read_text(encoding="utf-8"))
        runner.check(
            "User memory: memory record stores user_id in JSON",
            stored_memory["user_id"] == "user_alpha",
        )
        runner.check(
            "User memory: load_memory_records filters correctly",
            len(alpha_records) == 1 and alpha_records[0]["memory_id"] == "proposal-a",
        )
        runner.check(
            "User memory: different users see only their own records",
            len(beta_records) == 1 and beta_records[0]["memory_id"] == "proposal-b",
        )
        startup_alpha = memory.load_startup_context(user_id="user_alpha")
        runner.check(
            "User memory: user-scoped startup context stays filtered",
            startup_alpha["summary_lines"] == ["user: alpha"] and startup_alpha["session_count"] == 0,
        )

        user_log = UserLog(root / "user_logs")
        runner.check("User log: UserLog can be instantiated", isinstance(user_log, UserLog))
        user_log.append("user_alpha", "session-1", "user", "hello", "hi there")
        user_log.append("user_beta", "session-2", "user", "beta hello", "beta hi")
        alpha_log_path = root / "user_logs" / "user_alpha.jsonl"
        alpha_entries = user_log.load("user_alpha")
        runner.check("User log: append creates a log file", alpha_log_path.exists())
        runner.check(
            "User log: load returns the correct entries",
            len(alpha_entries) == 1 and alpha_entries[0]["content"] == "hello",
        )
        runner.check(
            "User log: entry_count reports the correct total",
            user_log.entry_count("user_alpha") == 1,
        )
        cleared = user_log.clear("user_alpha")
        runner.check(
            "User log: clear removes entries and returns the count",
            cleared == 1 and user_log.load("user_alpha") == [],
        )
        runner.check(
            "User log: different users have separate log files",
            (root / "user_logs" / "user_beta.jsonl").exists()
            and not (root / "user_logs" / "user_alpha.jsonl").exists(),
        )

        all_user = user_manager.create_user(
            display_name="AllRealms",
            role="operator",
            assigned_realms=["all"],
            created_by=guardian_first.user_id,
        )
        scoped_user = user_manager.create_user(
            display_name="RealmUser",
            role="user",
            assigned_realms=["work"],
            created_by=guardian_first.user_id,
        )
        runner.check(
            "Realm access: can_access_realm is true for all",
            can_access_realm(all_user, "private"),
        )
        runner.check(
            "Realm access: can_access_realm is true for assigned realm",
            can_access_realm(scoped_user, "work"),
        )
        runner.check(
            "Realm access: can_access_realm is false for unassigned realm",
            not can_access_realm(scoped_user, "archive"),
        )
        user_manager.assign_realm(scoped_user.user_id, "archive")
        scoped_user = user_manager.get_user(scoped_user.user_id) or scoped_user
        runner.check(
            "Realm access: assign_realm adds realm membership",
            "archive" in scoped_user.assigned_realms,
        )
        removed_archive = user_manager.unassign_realm(scoped_user.user_id, "archive")
        protected_last = user_manager.unassign_realm(scoped_user.user_id, "work")
        runner.check(
            "Realm access: unassign_realm protects the last remaining realm",
            removed_archive is True and protected_last is False,
        )

        faculty_monitor = FacultyMonitor()
        runner.check(
            "Faculty monitor: active Faculty records include all current faculties",
            len(faculty_monitor.all_records()) == 5,
        )
        faculty_monitor.update_model_mode("connected")
        runner.check(
            "Faculty monitor: update_model_mode updates crown and analyst",
            faculty_monitor.get_record("crown").mode == "connected"
            and faculty_monitor.get_record("analyst").mode == "connected",
        )
        faculty_monitor.record_call("operator", 42.0, True)
        runner.check(
            "Faculty monitor: record_call increments call_count",
            faculty_monitor.get_record("operator").call_count == 1,
        )
        monitor_report = faculty_monitor.format_report()
        runner.check(
            "Faculty monitor: format_report contains all active Faculty names",
            all(
                name in monitor_report
                for name in ("CROWN", "ANALYST", "OPERATOR", "GUARDIAN", "SENTINEL")
            ),
        )

        runner.check(
            "Capabilities: STARTUP_COMMANDS exposes every required Cycle 4 command",
            all(command in STARTUP_COMMANDS for command in REQUIRED_CYCLE4_COMMANDS),
            detail=", ".join(command for command in REQUIRED_CYCLE4_COMMANDS if command not in STARTUP_COMMANDS),
        )
        state_text = StateReport().render(
            session_id="session-1",
            mode="fallback",
            memory_count=2,
            pending_count=1,
            total_proposals=3,
            approved_proposals=1,
            rejected_proposals=1,
            realm_name="work",
            realm_memory_count=2,
            realm_session_count=1,
            realm_governance_context="Visible rules",
            active_user="ZAERA (guardian)",
            realm_access=True,
        )
        runner.check(
            "Capabilities: state surface names the restored Guardian actions",
            "guardian-dismiss" in state_text and "guardian-clear-events" in state_text,
        )
        server_source = (APP_ROOT / "ui" / "server.py").read_text(encoding="utf-8")
        runner.check(
            "Capabilities: status payload is sourced from STARTUP_COMMANDS in the UI server",
            '"capabilities": list(STARTUP_COMMANDS)' in server_source,
        )

        runner.check(
            "Identity: CURRENT_PHASE remains defined under later phases",
            CURRENT_PHASE.startswith("Cycle "),
            detail=CURRENT_PHASE,
        )
        runner.check(
            "Identity: CYCLE4_PREVIEW exists and names the civic roles",
            all(role in CYCLE4_PREVIEW.lower() for role in ("guardian", "operator", "user")),
            detail=CYCLE4_PREVIEW,
        )
        runner.check(
            "Identity: CYCLE4_SUMMARY describes the Civic Layer",
            "Civic Layer" in CYCLE4_SUMMARY and "Admin Surface" in CYCLE4_SUMMARY,
            detail=CYCLE4_SUMMARY,
        )

        command_result = handle_command(
            "guardian-dismiss",
            None,  # type: ignore[arg-type]
            memory,
            None,  # type: ignore[arg-type]
            StateReport(),
            None,  # type: ignore[arg-type]
            None,  # type: ignore[arg-type]
            None,  # type: ignore[arg-type]
            [],
            {"summary_lines": [], "summary_items": [], "memory_count": 0, "session_count": 0},
            None,  # type: ignore[arg-type]
        )
        runner.check(
            "Capabilities: guardian-dismiss is handled by the CLI surface",
            command_result == "guardian > alerts dismissed.",
            detail=str(command_result),
        )

    cycle2_ok, cycle2_detail = run_script(APP_ROOT / "verify_cycle2.py")
    runner.check("Regression: verify_cycle2.py still passes", cycle2_ok, detail=cycle2_detail)
    cycle3_ok, cycle3_detail = run_script(APP_ROOT / "verify_cycle3.py")
    runner.check("Regression: verify_cycle3.py still passes", cycle3_ok, detail=cycle3_detail)

    return runner.finish()


if __name__ == "__main__":
    raise SystemExit(main())
