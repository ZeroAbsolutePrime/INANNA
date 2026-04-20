from __future__ import annotations

import asyncio
import json
import os
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from websockets.asyncio.server import ServerConnection, serve
from websockets.exceptions import ConnectionClosed

from config import Config
from core.governance import GovernanceLayer
from core.guardian import GuardianFaculty
from core.faculty_monitor import FacultyMonitor
from core.memory import Memory
from core.nammu import IntentClassifier
from core.nammu_memory import (
    append_governance_event,
    append_routing_event,
    load_governance_history,
)
from core.operator import OperatorFaculty
from core.proposal import Proposal
from core.session import AnalystFaculty, Engine, Session
from core.session_token import TokenStore
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
from main import (
    STARTUP_COMMANDS,
    append_audit_event,
    append_user_log_entry,
    build_admin_surface_payload,
    build_body_report,
    build_body_summary,
    build_history_report,
    build_invites_report,
    build_memory_log_report,
    build_proposal_history_payload,
    build_realm_access_warning_lines,
    build_realm_context_report,
    build_nammu_log_report,
    build_realms_report,
    build_routing_log_report,
    build_tool_registry_payload,
    build_tool_result_text,
    build_users_report,
    build_whoami_report,
    build_tool_context_lines,
    create_invite_proposal,
    create_realm_proposal,
    create_user_proposal,
    create_realm_assignment_proposal,
    create_memory_request_proposal,
    create_realm_context_proposal,
    create_tool_use_proposal,
    format_user_log_report,
    has_admin_surface_access,
    initialize_realm_context,
    inspect_body_report,
    load_current_realm,
    parse_user_realm_command,
    startup_context_items,
    token_preview,
)

APP_ROOT = Path(__file__).resolve().parent.parent
STATIC_ROOT = Path(__file__).resolve().parent / "static"
INDEX_PATH = STATIC_ROOT / "index.html"
CONSOLE_PATH = STATIC_ROOT / "console.html"

load_dotenv(APP_ROOT / ".env")
HTTP_PORT = int(os.getenv("INANNA_HTTP_PORT", "8080"))
WS_PORT = int(os.getenv("INANNA_WS_PORT", "8081"))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class StaticHandler(BaseHTTPRequestHandler):
    def _serve_html(self, file_path: Path) -> None:
        if not file_path.exists():
            self.send_response(404)
            self.end_headers()
            return

        content = file_path.read_text(encoding="utf-8").replace(
            "__WS_PORT__", str(WS_PORT)
        )
        payload = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path in {"/", "/index.html"}:
            self._serve_html(INDEX_PATH)
        elif path == "/console":
            self._serve_html(CONSOLE_PATH)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        pass


def run_http_server() -> None:
    httpd = HTTPServer(("", HTTP_PORT), StaticHandler)
    print(f"HTTP server ready on http://localhost:{HTTP_PORT}")
    httpd.serve_forever()



class InterfaceServer:
    def __init__(self) -> None:
        self.data_root = APP_ROOT / "data"
        self.realm_manager, self.active_realm, realm_dirs, migrated = initialize_realm_context(
            self.data_root
        )
        self.nammu_dir = realm_dirs["nammu"]
        self.session_dir = realm_dirs["sessions"]
        self.memory_dir = realm_dirs["memory"]
        self.proposal_dir = realm_dirs["proposals"]
        self.startup_messages: list[str] = []
        if migrated:
            self.startup_messages.append(f"Migrated {migrated} files to default realm.")
            print(self.startup_messages[-1])

        self.config = Config.from_env()
        self.memory = Memory(session_dir=self.session_dir, memory_dir=self.memory_dir)
        self.proposal = Proposal(proposal_dir=self.proposal_dir)
        self.state_report = StateReport()
        self.user_manager = UserManager(
            data_root=self.data_root,
            roles_config_path=APP_ROOT / "config" / "roles.json",
        )
        self.guardian_user = ensure_guardian_exists(self.user_manager)
        expired_invites = self.user_manager.expire_old_invites()
        if expired_invites:
            self.startup_messages.append(f"Expired {expired_invites} invite(s).")
            print(self.startup_messages[-1])
        self.token_store = TokenStore()
        self.guardian_token = self.token_store.issue(
            self.guardian_user.user_id,
            self.guardian_user.display_name,
            self.guardian_user.role,
        )
        self.active_token = self.guardian_token
        self.original_token = None
        self.user_log = UserLog(self.data_root / "user_logs")
        self.faculty_monitor = FacultyMonitor()
        self.session_audit: list[dict[str, str]] = []
        append_audit_event(
            self.session_audit,
            "login",
            f"{self.guardian_user.display_name} ({self.guardian_user.role}) logged in",
        )
        self.active_user: UserRecord | None = self.guardian_user
        self.original_user: UserRecord | None = None
        self.engine = Engine(
            model_url=self.config.model_url,
            model_name=self.config.model_name,
            api_key=self.config.api_key,
            realm=self.active_realm,
        )
        self.analyst = AnalystFaculty(
            model_url=self.config.model_url,
            model_name=self.config.model_name,
            api_key=self.config.api_key,
            realm=self.active_realm,
        )
        self.guardian = GuardianFaculty()
        self.operator = OperatorFaculty()
        self.governance = GovernanceLayer(engine=self.engine)
        self.classifier = IntentClassifier(self.engine, governance=self.governance)
        self.routing_log: list[dict[str, str]] = []
        self.governance_blocks = 0
        self.tool_executions = 0
        print("Verifying model connection...")
        self.engine.verify_connection()
        self.analyst.fallback_mode = self.engine.fallback_mode
        self.analyst._connected = self.engine._connected
        self.faculty_monitor.update_model_mode(self.engine.mode)
        print(f"Model mode: {self.engine.mode}")
        print(
            f"Auto-login: {self.guardian_user.display_name} ({self.guardian_user.role}) | session active"
        )
        self.startup_context = self.memory.load_startup_context(
            user_id=self._memory_scope_user_id()
        )
        self.session = Session.create(
            session_dir=self.session_dir,
            context_summary=self.startup_context["summary_lines"],
        )
        self.connections: set[ServerConnection] = set()
        self.lock = asyncio.Lock()

    async def start(self) -> None:
        print(f"WebSocket server ready on ws://localhost:{WS_PORT}")
        async with serve(self.handle_connection, "", WS_PORT):
            await asyncio.Future()

    async def handle_connection(self, connection: ServerConnection) -> None:
        self.connections.add(connection)
        print(f"Client connected. Total: {len(self.connections)}")
        try:
            allowed = await self.send_initial_state(connection)
            if not allowed:
                return
            async for raw_message in connection:
                try:
                    payload = json.loads(raw_message)
                except json.JSONDecodeError:
                    await self.send_json(connection, {"type": "system", "text": "Invalid message."})
                    continue
                async with self.lock:
                    await self.dispatch_message(payload)
        except ConnectionClosed:
            pass
        finally:
            self.connections.discard(connection)
            print(f"Client disconnected. Total: {len(self.connections)}")

    async def dispatch_message(self, payload: dict[str, Any]) -> None:
        t = payload.get("type")
        if t == "input":
            text = str(payload.get("text", "")).strip()
            if text:
                await self.process_user_input(text)
        elif t == "command":
            raw_cmd = str(payload.get("cmd", "")).strip()
            if raw_cmd:
                command_payload = dict(payload)
                command_payload["_raw_cmd"] = raw_cmd
                await self.process_command(raw_cmd, command_payload)

    async def process_user_input(self, text: str) -> None:
        await self.broadcast({"type": "thinking", "active": True})
        try:
            lowered = text.lower()
            command_name = lowered.split(" ", 1)[0]
            if command_name in set(STARTUP_COMMANDS) - {"analyse"}:
                await self.process_command(text, {"_raw_cmd": text})
            elif lowered.startswith("analyse"):
                analysis_text, created, mode = await asyncio.to_thread(
                    self._run_analysis_turn, text
                )
                label = "[live analysis]" if mode == "live" else "[analysis fallback]"
                await self.broadcast({"type": "analyst", "text": f"{label} {analysis_text}"})
                if created:
                    await self.broadcast({"type": "system", "text": created["line"]})
            else:
                outcome = await asyncio.to_thread(
                    self._run_routed_turn, text
                )
                if outcome.get("nammu"):
                    await self.broadcast(outcome["nammu"])
                if outcome.get("governance"):
                    await self.broadcast(outcome["governance"])
                if outcome.get("response"):
                    await self.broadcast(outcome["response"])
                if outcome.get("proposal"):
                    await self.broadcast({"type": "system", "text": outcome["proposal"]["line"]})
            await self.broadcast_state()
        finally:
            await self.broadcast({"type": "thinking", "active": False})

    def _run_user_turn(self, text: str) -> tuple[str, dict[str, Any]]:
        self.session.add_event("user", text)
        t0 = time.monotonic()
        assistant_text = self.engine.respond(
            context_summary=startup_context_items(self.startup_context),
            conversation=self.session.events,
        )
        self.faculty_monitor.record_call("crown", (time.monotonic() - t0) * 1000, True)
        self.session.add_event("assistant", assistant_text)
        append_user_log_entry(
            self.user_log,
            self.active_token,
            self.session.session_id,
            text,
            assistant_text,
        )
        created = self.proposal.create(
            what="Update the memory store from the latest session turn",
            why="Keep the next session grounded in readable, user-approved context.",
            payload=self.memory.build_candidate(
                session_id=self.session.session_id,
                events=self.session.events,
                user_id=self.active_token.user_id if self.active_token is not None else "",
            ),
        )
        return assistant_text, created

    def _refresh_session_users(self) -> None:
        if self.active_user is not None:
            self.active_user = self.user_manager.get_user(self.active_user.user_id) or self.active_user
        if self.original_user is not None:
            self.original_user = (
                self.user_manager.get_user(self.original_user.user_id) or self.original_user
            )
        if self.guardian_user is not None:
            self.guardian_user = (
                self.user_manager.get_user(self.guardian_user.user_id) or self.guardian_user
            )

    def _memory_scope_user_id(self) -> str | None:
        if self.active_user is None:
            return None
        if self.user_manager.has_privilege(self.active_user.user_id, "all"):
            return None
        return self.active_user.user_id

    def _refresh_startup_context(self) -> None:
        self.startup_context = self.memory.load_startup_context(
            user_id=self._memory_scope_user_id()
        )

    def _visible_memory_report(self) -> dict[str, Any]:
        return self.memory.memory_log_report(user_id=self._memory_scope_user_id())

    def _active_user_payload(self) -> dict[str, Any] | None:
        if self.active_user is None:
            return None
        payload = {
            "user_id": self.active_user.user_id,
            "display_name": self.active_user.display_name,
            "role": self.active_user.role,
            "assigned_realms": list(self.active_user.assigned_realms),
        }
        if self.active_token is not None and self.active_token.user_id == self.active_user.user_id:
            payload["token_preview"] = token_preview(self.active_token)
            payload["expires_at"] = self.active_token.expires_at
        else:
            payload["token_preview"] = "none"
            payload["expires_at"] = ""
        return payload

    def _record_routing_decision(self, route: str, text: str) -> None:
        record = {
            "timestamp": utc_now(),
            "input_preview": text[:60],
            "route": route,
        }
        self.routing_log.append(record)
        append_routing_event(
            self.nammu_dir,
            self.session.session_id,
            route,
            record["input_preview"],
        )

    def _record_governance_decision(self, decision: str, reason: str, text: str) -> None:
        append_governance_event(
            self.nammu_dir,
            self.session.session_id,
            decision,
            reason,
            text[:60],
        )

    def _run_routed_turn(
        self,
        text: str,
    ) -> dict[str, Any]:
        governance_result = self.classifier.route(text)
        self._record_routing_decision(governance_result.faculty, text)

        if governance_result.decision == "block":
            self.governance_blocks += 1
            self._record_governance_decision(
                governance_result.decision,
                governance_result.reason,
                text,
            )
            return {
                "governance": {
                    "type": "governance",
                    "decision": "block",
                    "text": f"blocked: {governance_result.reason}",
                }
            }

        if governance_result.decision == "propose":
            self._record_governance_decision(
                governance_result.decision,
                governance_result.reason,
                text,
            )
            created = create_memory_request_proposal(
                proposal=self.proposal,
                session=self.session,
                user_input=text,
                reason=governance_result.reason,
                user_id=self._memory_scope_user_id() or "",
            )
            return {
                "governance": {
                    "type": "governance",
                    "decision": "propose",
                    "text": f"proposal required: {governance_result.reason}",
                },
                "proposal": created,
            }

        if governance_result.suggests_tool:
            self._record_governance_decision(
                "tool",
                "Current information requires governed tool use.",
                text,
            )
            created = create_tool_use_proposal(
                proposal=self.proposal,
                session=self.session,
                user_input=text,
                tool=governance_result.proposed_tool,
                query=governance_result.tool_query or text,
            )
            return {
                "response": {
                    "type": "operator",
                    "text": (
                        f'tool proposed: {governance_result.proposed_tool} — '
                        f'"{governance_result.tool_query or text}"'
                    ),
                },
                "proposal": {**created, "line": created["tool_line"]},
            }

        nammu_message = {
            "type": "nammu",
            "route": governance_result.faculty,
            "text": f"routing to {governance_result.faculty} faculty",
        }
        governance_message = None
        if governance_result.decision == "redirect":
            self._record_governance_decision(
                governance_result.decision,
                governance_result.reason,
                text,
            )
            governance_message = {
                "type": "governance",
                "decision": "redirect",
                "text": f"redirected: {governance_result.reason}",
            }

        if governance_result.faculty == "analyst":
            t0 = time.monotonic()
            mode, analysis_text = self.analyst.analyse(
                question=text,
                context=startup_context_items(self.startup_context),
            )
            self.faculty_monitor.record_call("analyst", (time.monotonic() - t0) * 1000, True)
            self.session.add_event("user", text)
            self.session.add_event("analyst", analysis_text)
            append_user_log_entry(
                self.user_log,
                self.active_token,
                self.session.session_id,
                text,
                analysis_text,
            )
            created = self.proposal.create(
                what="Update the memory store from the latest session turn",
                why="Keep the next session grounded in readable, user-approved context.",
                payload=self.memory.build_candidate(
                    session_id=self.session.session_id,
                    events=self.session.events,
                    user_id=self.active_token.user_id if self.active_token is not None else "",
                ),
            )
            label = "[live analysis]" if mode == "live" else "[analysis fallback]"
            return {
                "nammu": nammu_message,
                "governance": governance_message,
                "response": {"type": "analyst", "text": f"{label} {analysis_text}"},
                "proposal": created,
            }

        assistant_text, created = self._run_user_turn(text)
        return {
            "nammu": nammu_message,
            "governance": governance_message,
            "response": {"type": "assistant", "text": assistant_text},
            "proposal": created,
        }

    def _run_analysis_turn(
        self,
        text: str,
    ) -> tuple[str, dict[str, Any] | None, str]:
        question = text[len("analyse") :].strip()
        t0 = time.monotonic()
        mode, analysis_text = self.analyst.analyse(
            question=question,
            context=startup_context_items(self.startup_context),
        )
        self.faculty_monitor.record_call("analyst", (time.monotonic() - t0) * 1000, True)
        if not question:
            return analysis_text, None, mode

        self.session.add_event("user", text)
        self.session.add_event("analyst", analysis_text)
        append_user_log_entry(
            self.user_log,
            self.active_token,
            self.session.session_id,
            text,
            analysis_text,
        )
        created = self.proposal.create(
            what="Update the memory store from the latest session turn",
            why="Keep the next session grounded in readable, user-approved context.",
            payload=self.memory.build_candidate(
                session_id=self.session.session_id,
                events=self.session.events,
                user_id=self.active_token.user_id if self.active_token is not None else "",
            ),
        )
        return analysis_text, created, mode

    def _run_realm_context_update(self, text: str) -> dict[str, Any]:
        governance_context = text[len("realm-context") :].strip()
        if not governance_context:
            return {
                "line": "realm-context > provide governance context text to propose an update."
            }
        return create_realm_context_proposal(
            proposal=self.proposal,
            active_realm=self.active_realm,
            governance_context=governance_context,
        )

    async def process_command(self, cmd: str, payload: dict[str, Any]) -> None:
        raw_cmd = str(payload.get("_raw_cmd", cmd)).strip()
        lowered = raw_cmd.lower()
        command_name = lowered.split(" ", 1)[0]
        command_args = raw_cmd[len(command_name) :].strip()

        if command_name == "users":
            allowed, reason = check_privilege(self.active_user, self.user_manager, "all")
            if not allowed:
                await self.broadcast({"type": "system", "text": f"access > {reason}"})
            else:
                await self.broadcast(
                    {
                        "type": "system",
                        "text": await asyncio.to_thread(build_users_report, self.user_manager),
                    }
                )
            await self.broadcast_state()
        elif command_name == "create-user":
            allowed, reason = check_privilege(self.active_user, self.user_manager, "all")
            if not allowed:
                await self.broadcast({"type": "system", "text": f"access > {reason}"})
                await self.broadcast_state()
                return
            parts = raw_cmd.split(maxsplit=3)
            if len(parts) != 4:
                await self.broadcast(
                    {
                        "type": "system",
                        "text": "create-user > usage: create-user [display_name] [role] [realm]",
                    }
                )
                await self.broadcast_state()
                return
            _, display_name, role, realm_name = parts
            if role.strip().lower() not in self.user_manager.roles:
                await self.broadcast(
                    {"type": "system", "text": f"create-user > Unknown role: {role}"}
                )
                await self.broadcast_state()
                return
            created = await asyncio.to_thread(
                create_user_proposal,
                self.proposal,
                display_name,
                role.strip().lower(),
                realm_name,
                self.active_token.user_id if self.active_token is not None else "system",
            )
            await self.broadcast(
                {
                    "type": "system",
                    "text": "create-user > proposal required to create a new user.",
                }
            )
            await self.broadcast({"type": "system", "text": str(created["line"])})
            await self.broadcast_state()
        elif command_name == "login":
            display_name = command_args.strip()
            if not display_name and " " in cmd:
                display_name = cmd.split(" ", 1)[1].strip()
            if not display_name:
                await self.broadcast(
                    {"type": "system", "text": "login > usage: login [display_name]"}
                )
                await self.broadcast_state()
                return
            try:
                target = self.user_manager.get_user_by_display_name(display_name)
                if target is None:
                    await self.broadcast(
                        {"type": "system", "text": f"No user found with name: {display_name}"}
                    )
                    await self.broadcast_state()
                    return
                self.token_store.revoke_all_for_user(target.user_id)
                token = self.token_store.issue(target.user_id, target.display_name, target.role)
                self.active_user = target
                self.active_token = token
                self.original_user = None
                self.original_token = None
                if self.guardian_user is not None and target.user_id == self.guardian_user.user_id:
                    self.guardian_token = token
                append_audit_event(
                    self.session_audit,
                    "login",
                    f"{target.display_name} ({target.role}) logged in",
                )
                self._refresh_startup_context()
                for line in (
                    f"login > session started for {target.display_name} ({target.role})",
                    f"login > token: {token_preview(token)} valid for 8 hours",
                    f"login > session bound to user_id: {target.user_id}",
                ):
                    await self.broadcast({"type": "system", "text": line})
            except Exception as exc:
                await self.broadcast({"type": "system", "text": f"login > {exc}"})
            await self.broadcast_state()
        elif command_name == "logout":
            if self.active_token is None:
                await self.broadcast({"type": "system", "text": "No active session."})
            else:
                ended = self.active_token
                self.token_store.revoke(ended.token)
                append_audit_event(
                    self.session_audit,
                    "logout",
                    f"{ended.display_name} ({ended.role}) logged out",
                )
                self.active_token = None
                self.active_user = None
                self.original_token = None
                self.original_user = None
                self._refresh_startup_context()
                await self.broadcast(
                    {
                        "type": "system",
                        "text": f"logout > session ended for {ended.display_name}",
                    }
                )
            await self.broadcast_state()
        elif command_name == "whoami":
            await self.broadcast(
                {
                    "type": "system",
                    "text": await asyncio.to_thread(
                        build_whoami_report, self.active_token, self.user_manager
                    ),
                }
            )
            await self.broadcast_state()
        elif command_name == "faculties":
            await self.broadcast(
                {
                    "type": "system",
                    "text": await asyncio.to_thread(self.faculty_monitor.format_report),
                }
            )
            await self.broadcast_state()
        elif command_name == "my-log":
            allowed, reason = check_privilege(self.active_user, self.user_manager, "read_own_log")
            if not allowed or self.active_token is None:
                text = f"access > {reason}" if not allowed else 'my-log > No active session. Type "login [name]" to identify.'
                await self.broadcast({"type": "system", "text": text})
            else:
                text = await asyncio.to_thread(
                    format_user_log_report,
                    "Your interaction log",
                    self.user_log.load(self.active_token.user_id, limit=20),
                )
                await self.broadcast({"type": "system", "text": text})
            await self.broadcast_state()
        elif command_name == "user-log":
            allowed, reason = check_privilege(self.active_user, self.user_manager, "all")
            if not allowed:
                await self.broadcast({"type": "system", "text": f"access > {reason}"})
                await self.broadcast_state()
                return
            display_name = command_args.strip()
            if not display_name:
                await self.broadcast(
                    {"type": "system", "text": "user-log > usage: user-log [display_name]"}
                )
                await self.broadcast_state()
                return
            target = self.user_manager.get_user_by_display_name(display_name)
            if target is None:
                await self.broadcast(
                    {"type": "system", "text": f"user-log > No user found: {display_name}"}
                )
                await self.broadcast_state()
                return
            text = await asyncio.to_thread(
                format_user_log_report,
                f"Interaction log for {target.display_name} ({target.user_id})",
                self.user_log.load(target.user_id, limit=20),
            )
            await self.broadcast({"type": "system", "text": text})
            await self.broadcast_state()
        elif command_name == "invite":
            if self.active_user is None or self.active_token is None:
                await self.broadcast({"type": "system", "text": "invite > invite flow is unavailable."})
                await self.broadcast_state()
                return
            if not self.user_manager.has_privilege(self.active_user.user_id, "invite_users"):
                await self.broadcast(
                    {
                        "type": "system",
                        "text": (
                            f"access > Insufficient privileges. "
                            f"{self.active_user.display_name} ({self.active_user.role}) "
                            "does not have: invite_users"
                        ),
                    }
                )
                await self.broadcast_state()
                return
            parts = raw_cmd.split(maxsplit=2)
            if len(parts) != 3:
                await self.broadcast(
                    {"type": "system", "text": "invite > usage: invite [role] [realm]"}
                )
                await self.broadcast_state()
                return
            _, role, realm_name = parts
            if role.strip().lower() not in self.user_manager.roles:
                await self.broadcast({"type": "system", "text": f"invite > Unknown role: {role}"})
                await self.broadcast_state()
                return
            created = await asyncio.to_thread(
                create_invite_proposal,
                self.proposal,
                role.strip().lower(),
                realm_name,
                self.active_token.user_id,
            )
            await self.broadcast(
                {
                    "type": "system",
                    "text": "invite > proposal required to create an invite.",
                }
            )
            await self.broadcast({"type": "system", "text": str(created["line"])})
            await self.broadcast_state()
        elif command_name == "join":
            parts = raw_cmd.split(maxsplit=2)
            if len(parts) != 3:
                await self.broadcast(
                    {"type": "system", "text": "join > usage: join [invite_code] [display_name]"}
                )
                await self.broadcast_state()
                return
            _, invite_code, display_name = parts
            invite = self.user_manager.get_invite(invite_code)
            if invite is None:
                await self.broadcast({"type": "system", "text": "join > Invalid invite code."})
                await self.broadcast_state()
                return
            if invite.status == "expired":
                await self.broadcast({"type": "system", "text": "join > This invite has expired."})
                await self.broadcast_state()
                return
            if invite.status == "accepted":
                await self.broadcast(
                    {"type": "system", "text": "join > This invite has already been used."}
                )
                await self.broadcast_state()
                return
            created = self.user_manager.accept_invite(invite_code, display_name)
            if created is None:
                refreshed = self.user_manager.get_invite(invite_code)
                text = "join > This invite has expired."
                if refreshed is None or refreshed.status != "expired":
                    text = "join > This invite could not be accepted."
                await self.broadcast({"type": "system", "text": text})
                await self.broadcast_state()
                return
            self.token_store.revoke_all_for_user(created.user_id)
            token = self.token_store.issue(created.user_id, created.display_name, created.role)
            self.active_user = created
            self.active_token = token
            self.original_user = None
            self.original_token = None
            append_audit_event(
                self.session_audit,
                "join",
                f"{created.display_name} joined via invite {invite_code}",
            )
            self._refresh_startup_context()
            for line in (
                f"join > Welcome, {created.display_name}.",
                "join > Your account has been created.",
                f"join > Role: {created.role}  Realm: {', '.join(created.assigned_realms)}",
                "join > You are now logged in.",
                'join > Type "whoami" to see your session details.',
            ):
                await self.broadcast({"type": "system", "text": line})
            await self.broadcast_state()
        elif command_name == "invites":
            if self.active_user is None:
                await self.broadcast({"type": "system", "text": "access > No active session."})
                await self.broadcast_state()
                return
            if not (
                self.user_manager.has_privilege(self.active_user.user_id, "all")
                or self.user_manager.has_privilege(self.active_user.user_id, "invite_users")
            ):
                await self.broadcast(
                    {
                        "type": "system",
                        "text": (
                            f"access > Insufficient privileges. "
                            f"{self.active_user.display_name} ({self.active_user.role}) "
                            "does not have: invite_users"
                        ),
                    }
                )
                await self.broadcast_state()
                return
            await self.broadcast(
                {
                    "type": "system",
                    "text": await asyncio.to_thread(
                        build_invites_report,
                        self.user_manager.list_invites(),
                        self.active_user,
                    ),
                }
            )
            await self.broadcast_state()
        elif command_name == "admin-surface":
            if self.active_user is None:
                await self.broadcast({"type": "system", "text": "access > No active session."})
                return
            if not has_admin_surface_access(self.user_manager, self.active_user):
                await self.broadcast(
                    {
                        "type": "system",
                        "text": (
                            f"access > Insufficient privileges. "
                            f"{self.active_user.display_name} ({self.active_user.role}) "
                            "does not have: invite_users"
                        ),
                    }
                )
                return
            admin_data = await asyncio.to_thread(
                build_admin_surface_payload,
                self.user_manager,
                self.user_log,
                self.realm_manager,
                self.active_user,
            )
            await self.broadcast({"type": "admin_data", **admin_data})
        elif command_name == "tool-registry":
            await self.broadcast(
                await asyncio.to_thread(build_tool_registry_payload, self.operator)
            )
        elif command_name == "reflect":
            await self.run_reflect()
        elif command_name == "audit":
            await self.run_audit()
        elif command_name == "guardian":
            await self.run_guardian()
        elif command_name == "guardian-log":
            await self.broadcast({"type": "guardian_log", "events": list(self.session_audit)})
        elif command_name == "guardian-dismiss":
            await self.broadcast(
                {"type": "guardian_status", "alerts": [], "timestamp": utc_now()}
            )
            await self.broadcast({"type": "system", "text": "guardian > alerts dismissed."})
            await self.broadcast_state()
        elif command_name == "guardian-clear-events":
            cleared = len(self.session_audit)
            self.session_audit.clear()
            await self.broadcast({"type": "guardian_log", "events": []})
            await self.broadcast({"type": "audit_log", "events": []})
            await self.broadcast(
                {
                    "type": "system",
                    "text": f"guardian > cleared {cleared} governance event(s).",
                }
            )
            await self.broadcast_state()
        elif command_name == "audit-log":
            await self.broadcast({"type": "audit_log", "events": list(self.session_audit)})
        elif command_name == "history":
            report = await asyncio.to_thread(self.proposal.history_report)
            await self.broadcast({"type": "system", "text": build_history_report(report)})
            await self.broadcast_state()
        elif command_name == "proposal-history":
            report = await asyncio.to_thread(self.proposal.history_report)
            await self.broadcast(build_proposal_history_payload(report))
        elif command_name == "realms":
            report = await asyncio.to_thread(
                build_realms_report,
                self.realm_manager,
                self.active_realm.name,
            )
            await self.broadcast({"type": "system", "text": report})
            await self.broadcast_state()
        elif command_name == "create-realm":
            allowed, reason = check_privilege(self.active_user, self.user_manager, "all")
            if not allowed:
                await self.broadcast({"type": "system", "text": f"access > {reason}"})
                await self.broadcast_state()
                return
            parts = raw_cmd.split(maxsplit=2)
            if len(parts) < 2:
                await self.broadcast(
                    {
                        "type": "system",
                        "text": "create-realm > usage: create-realm [name] [purpose]",
                    }
                )
                await self.broadcast_state()
                return
            realm_name = parts[1].strip()
            purpose = parts[2].strip() if len(parts) == 3 else ""
            if not realm_name:
                await self.broadcast(
                    {
                        "type": "system",
                        "text": "create-realm > usage: create-realm [name] [purpose]",
                    }
                )
                await self.broadcast_state()
                return
            if self.realm_manager.realm_exists(realm_name):
                await self.broadcast(
                    {
                        "type": "system",
                        "text": f"create-realm > Realm {realm_name} already exists.",
                    }
                )
                await self.broadcast_state()
                return
            created = await asyncio.to_thread(
                create_realm_proposal,
                self.proposal,
                realm_name,
                purpose,
                self.active_token.user_id if self.active_token is not None else "system",
            )
            await self.broadcast(
                {
                    "type": "system",
                    "text": "create-realm > proposal required to create a new realm.",
                }
            )
            await self.broadcast({"type": "system", "text": str(created["line"])})
            await self.broadcast_state()
        elif command_name == "realm-context":
            if command_args:
                allowed, reason = check_privilege(self.active_user, self.user_manager, "all")
                if not allowed:
                    await self.broadcast({"type": "system", "text": f"access > {reason}"})
                    await self.broadcast_state()
                    return
                created = await asyncio.to_thread(self._run_realm_context_update, raw_cmd)
                await self.broadcast(
                    {
                        "type": "system",
                        "text": "realm-context > proposal required to update the active realm context.",
                    }
                )
                await self.broadcast({"type": "system", "text": created["line"]})
            else:
                report = await asyncio.to_thread(
                    build_realm_context_report,
                    load_current_realm(self.realm_manager, self.active_realm),
                    self.session_dir,
                    self.memory_dir,
                    self.proposal_dir,
                )
                await self.broadcast({"type": "system", "text": report})
            await self.broadcast_state()
        elif command_name == "switch-user":
            controller = self.original_user or self.active_user
            allowed, reason = check_privilege(controller, self.user_manager, "all")
            if not allowed:
                await self.broadcast({"type": "system", "text": f"access > {reason}"})
                await self.broadcast_state()
                return
            target_name = command_args.strip()
            if not target_name:
                await self.broadcast(
                    {"type": "system", "text": "switch-user > provide a display name or 'off'."}
                )
                await self.broadcast_state()
                return
            guardian_record = self.guardian_user or controller
            if guardian_record is None:
                await self.broadcast(
                    {"type": "system", "text": "switch-user > guardian context is unavailable."}
                )
                await self.broadcast_state()
                return
            if target_name.lower() in {"off", guardian_record.display_name.lower()}:
                self.active_user = guardian_record
                self.original_user = None
                self._refresh_startup_context()
                await self.broadcast(
                    {
                        "type": "system",
                        "text": f"switch-user > Returned to {guardian_record.display_name} ({guardian_record.role}).",
                    }
                )
                await self.broadcast_state()
                return
            target = self.user_manager.get_user_by_display_name(target_name)
            if target is None:
                await self.broadcast(
                    {"type": "system", "text": f"switch-user > No user found: {target_name}"}
                )
                await self.broadcast_state()
                return
            self.active_user = target
            self.original_user = guardian_record
            self._refresh_startup_context()
            messages = [f"switch-user > Now operating as: {target.display_name} ({target.role})"]
            if not can_access_realm(target, self.active_realm.name):
                messages.extend(
                    [
                        f"switch-user > Warning: {target.display_name} does not have access to realm {self.active_realm.name}.",
                        f"switch-user > Operating as {target.display_name} in an unassigned realm.",
                        "switch-user > Use assign-realm to grant access.",
                    ]
                )
            else:
                messages.append(
                    f'switch-user > Type "switch-user {guardian_record.display_name}" to return to Guardian.'
                )
            for message in messages:
                await self.broadcast({"type": "system", "text": message})
            await self.broadcast_state()
        elif command_name == "assign-realm":
            allowed, reason = check_privilege(self.active_user, self.user_manager, "all")
            if not allowed:
                await self.broadcast({"type": "system", "text": f"access > {reason}"})
                await self.broadcast_state()
                return
            parsed = parse_user_realm_command(raw_cmd, "assign-realm")
            if parsed is None:
                await self.broadcast(
                    {
                        "type": "system",
                        "text": "assign-realm > usage: assign-realm [user_name] [realm_name]",
                    }
                )
                await self.broadcast_state()
                return
            display_name, realm_name = parsed
            target = self.user_manager.get_user_by_display_name(display_name)
            if target is None:
                await self.broadcast(
                    {"type": "system", "text": f"assign-realm > No user found: {display_name}"}
                )
                await self.broadcast_state()
                return
            created = await asyncio.to_thread(
                create_realm_assignment_proposal,
                self.proposal,
                target.display_name,
                target.user_id,
                realm_name,
                "assign_realm",
            )
            await self.broadcast(
                {
                    "type": "system",
                    "text": "assign-realm > proposal required to change realm access.",
                }
            )
            await self.broadcast({"type": "system", "text": created["line"]})
            await self.broadcast_state()
        elif command_name == "unassign-realm":
            allowed, reason = check_privilege(self.active_user, self.user_manager, "all")
            if not allowed:
                await self.broadcast({"type": "system", "text": f"access > {reason}"})
                await self.broadcast_state()
                return
            parsed = parse_user_realm_command(raw_cmd, "unassign-realm")
            if parsed is None:
                await self.broadcast(
                    {
                        "type": "system",
                        "text": "unassign-realm > usage: unassign-realm [user_name] [realm_name]",
                    }
                )
                await self.broadcast_state()
                return
            display_name, realm_name = parsed
            target = self.user_manager.get_user_by_display_name(display_name)
            if target is None:
                await self.broadcast(
                    {"type": "system", "text": f"unassign-realm > No user found: {display_name}"}
                )
                await self.broadcast_state()
                return
            created = await asyncio.to_thread(
                create_realm_assignment_proposal,
                self.proposal,
                target.display_name,
                target.user_id,
                realm_name,
                "unassign_realm",
            )
            await self.broadcast(
                {
                    "type": "system",
                    "text": "unassign-realm > proposal required to change realm access.",
                }
            )
            await self.broadcast({"type": "system", "text": created["line"]})
            await self.broadcast_state()
        elif command_name == "routing-log":
            report = await asyncio.to_thread(build_routing_log_report, self.routing_log)
            await self.broadcast({"type": "system", "text": report})
            await self.broadcast_state()
        elif command_name == "nammu-log":
            report = await asyncio.to_thread(build_nammu_log_report, self.nammu_dir)
            await self.broadcast({"type": "system", "text": report})
            await self.broadcast_state()
        elif command_name == "memory-log":
            report = await asyncio.to_thread(self.memory.memory_log_report)
            await self.broadcast({"type": "system", "text": build_memory_log_report(report)})
            await self.broadcast_state()
        elif command_name in {"body", "diagnostics"}:
            current_realm = load_current_realm(self.realm_manager, self.active_realm)
            report = await asyncio.to_thread(
                build_body_report,
                self.config,
                self.engine,
                self.session,
                self.proposal,
                self.memory_dir,
                self.proposal_dir,
                self.nammu_dir,
                self.data_root,
                current_realm.name if current_realm else self.active_realm.name,
            )
            await self.broadcast({"type": "system", "text": report})
            await self.broadcast_state()
        elif command_name == "status":
            await self.broadcast({"type": "system", "text": self.build_status_payload()["report"]})
            await self.broadcast_state()
        elif command_name in {"approve", "reject"}:
            resolved = await asyncio.to_thread(
                self.resolve_proposal, command_name, payload.get("proposal_id")
            )
            if not resolved:
                await self.broadcast({"type": "system", "text": "No pending proposals."})
            else:
                if resolved.get("payload", {}).get("action") == "tool_use":
                    outcome = await asyncio.to_thread(
                        self.complete_tool_resolution, resolved, command_name
                    )
                    for message in outcome["operator_messages"]:
                        await self.broadcast({"type": "operator", "text": message})
                    if outcome["assistant_text"]:
                        await self.broadcast({"type": "assistant", "text": outcome["assistant_text"]})
                    await self.broadcast({"type": "system", "text": outcome["proposal_line"]})
                else:
                    result = await asyncio.to_thread(self.apply_resolution, resolved)
                    await self.broadcast({"type": "system", "text": result})
            await self.broadcast_state()
        elif command_name == "forget":
            mid = str(payload.get("memory_id", "")).strip()
            if not mid:
                await self.broadcast({"type": "system", "text": "No memory_id provided."})
                await self.broadcast_state()
                return
            log = await asyncio.to_thread(self.memory.memory_log_report)
            record = next((r for r in log["records"] if r.get("memory_id") == mid), None)
            if record is None:
                await self.broadcast({"type": "system", "text": "Memory record not found."})
                await self.broadcast_state()
                return
            created = await asyncio.to_thread(
                self.proposal.create,
                f"Remove memory record {mid} from approved memory",
                "User requested removal — sovereignty over personal memory",
                {"memory_id": mid, "action": "forget"},
            )
            await self.broadcast({"type": "system", "text": created["line"]})
            await self.broadcast_state()

    async def run_reflect(self) -> None:
        await self.broadcast({"type": "thinking", "active": True})
        try:
            mode, text = await asyncio.to_thread(
                self.engine.reflect, startup_context_items(self.startup_context)
            )
            label = "[live reflection]" if mode == "live" else "[memory fallback]"
            await self.broadcast({"type": "assistant", "text": f"{label} {text}"})
            await self.broadcast_state()
        finally:
            await self.broadcast({"type": "thinking", "active": False})

    async def run_audit(self) -> None:
        await self.broadcast({"type": "thinking", "active": True})
        try:
            history = await asyncio.to_thread(self.proposal.history_report)
            memory_log = await asyncio.to_thread(self.memory.memory_log_report)
            mode, text = await asyncio.to_thread(
                self.engine.speak_audit, history, memory_log,
                startup_context_items(self.startup_context)
            )
            label = "[live audit]" if mode == "live" else "[audit summary]"
            await self.broadcast({"type": "assistant", "text": f"{label} {text}"})
            await self.broadcast_state()
        finally:
            await self.broadcast({"type": "thinking", "active": False})

    async def run_guardian(self) -> None:
        report = await asyncio.to_thread(self.build_guardian_report)
        await self.broadcast({"type": "guardian", "text": report})
        await self.broadcast_state()

    def resolve_proposal(self, decision: str, proposal_id: Any = None) -> dict[str, Any] | None:
        pid = str(proposal_id).strip() if proposal_id else ""
        if not pid:
            return self.proposal.resolve_next(decision)
        pending = [r for r in self.proposal.pending_records() if r["proposal_id"] == pid]
        if not pending:
            return None
        record = pending[0]
        record["status"] = "approved" if decision == "approve" else "rejected"
        record["resolved_at"] = utc_now()
        self.proposal._write_record(record)
        return {**record, "line": self.proposal.format_line(record)}

    def apply_resolution(self, resolved: dict[str, Any]) -> str:
        payload = resolved.get("payload", {})
        if resolved["status"] == "approved":
            if payload.get("action") == "realm_context_update":
                realm_name = str(payload.get("realm_name", "")).strip()
                governance_context = str(payload.get("governance_context", ""))
                if not self.realm_manager.update_realm_governance_context(
                    realm_name,
                    governance_context,
                ):
                    return f"Approved {resolved['proposal_id']} but realm {realm_name} was not found."
                if self.active_realm.name == realm_name:
                    self.active_realm.governance_context = governance_context
                return (
                    f"Approved {resolved['proposal_id']} and updated governance context "
                    f"for realm {realm_name}."
                )
            if payload.get("action") == "forget":
                mid = payload.get("memory_id", "")
                if self.memory.delete_memory_record(str(mid)):
                    return f"Memory record {mid} removed."
                return "Memory record not found."
            if payload.get("action") == "assign_realm":
                user_id = str(payload.get("user_id", "")).strip()
                display_name = str(payload.get("display_name", "")).strip()
                realm_name = str(payload.get("realm_name", "")).strip()
                target = self.user_manager.get_user(user_id)
                if target is None:
                    return f"Approved {resolved['proposal_id']} but user {display_name or user_id} was not found."
                if self.user_manager.assign_realm(user_id, realm_name):
                    self._refresh_session_users()
                    return f"assign-realm > Realm {realm_name} assigned to {target.display_name}."
                return f"assign-realm > {target.display_name} already has access to realm {realm_name}."
            if payload.get("action") == "unassign_realm":
                user_id = str(payload.get("user_id", "")).strip()
                display_name = str(payload.get("display_name", "")).strip()
                realm_name = str(payload.get("realm_name", "")).strip()
                target = self.user_manager.get_user(user_id)
                if target is None:
                    return f"Approved {resolved['proposal_id']} but user {display_name or user_id} was not found."
                if len(target.assigned_realms) <= 1 and realm_name in target.assigned_realms:
                    return f"unassign-realm > Cannot remove last realm for {target.display_name}."
                if self.user_manager.unassign_realm(user_id, realm_name):
                    self._refresh_session_users()
                    return f"unassign-realm > Realm {realm_name} removed from {target.display_name}."
                return f"unassign-realm > {target.display_name} does not have realm {realm_name}."
            if payload.get("action") == "create_user":
                created_by = str(payload.get("created_by", "system"))
                try:
                    created_user = self.user_manager.create_user(
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
                if not realm_name:
                    return (
                        f"Approved {resolved['proposal_id']} but realm management was unavailable."
                    )
                if self.realm_manager.realm_exists(realm_name):
                    return f"create-realm > Realm {realm_name} already exists."
                self.realm_manager.create_realm(realm_name, purpose)
                append_audit_event(
                    self.session_audit,
                    "realm",
                    f"realm {realm_name} created",
                )
                return f"create-realm > Realm {realm_name} created."
            if payload.get("action") == "create_invite":
                invite = self.user_manager.create_invite(
                    role=str(payload.get("role", "")).strip(),
                    assigned_realms=list(payload.get("assigned_realms", ["default"])),
                    created_by=str(payload.get("created_by", "system")),
                )
                append_audit_event(
                    self.session_audit,
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
            self.memory.write_memory(
                proposal_id=resolved["proposal_id"],
                session_id=payload["session_id"],
                summary_lines=payload["summary_lines"],
                approved_at=resolved["resolved_at"],
                realm_name=self.active_realm.name,
                user_id=str(payload.get("user_id", "")),
            )
            return f"Approved {resolved['proposal_id']} and wrote a memory record."
        if payload.get("action") == "realm_context_update":
            return f"Rejected {resolved['proposal_id']}."
        if payload.get("action") == "forget":
            return "Memory record retained."
        if payload.get("action") in {
            "assign_realm",
            "unassign_realm",
            "create_user",
            "create_realm",
            "create_invite",
        }:
            return f"Rejected {resolved['proposal_id']}."
        return f"Rejected {resolved['proposal_id']}."

    def complete_tool_resolution(self, resolved: dict[str, Any], decision: str) -> dict[str, Any]:
        payload = resolved["payload"]
        original_input = payload.get("original_input", "")
        query = payload.get("query", "")
        tool = payload.get("tool", "")

        self.session.add_event("user", original_input)

        if decision == "approve":
            self.tool_executions += 1
            t0 = time.monotonic()
            result = self.operator.execute(tool, {"query": query})
            self.faculty_monitor.record_call(
                "operator",
                (time.monotonic() - t0) * 1000,
                result.success,
            )
            operator_messages = [build_tool_result_text(result)]
            model_connected = self.engine._connected
            t0 = time.monotonic()
            assistant_text = self.engine.respond(
                context_summary=startup_context_items(self.startup_context)
                + build_tool_context_lines(result),
                conversation=self.session.events,
            )
            self.faculty_monitor.record_call("crown", (time.monotonic() - t0) * 1000, True)
            if result.success and model_connected and self.engine.mode == "fallback":
                assistant_text = ""
                operator_messages.append("model unavailable to summarize. Raw results shown above.")
        else:
            operator_messages = ["tool use rejected. Proceeding without tool execution."]
            t0 = time.monotonic()
            assistant_text = self.engine.respond(
                context_summary=startup_context_items(self.startup_context),
                conversation=self.session.events,
            )
            self.faculty_monitor.record_call("crown", (time.monotonic() - t0) * 1000, True)

        if assistant_text:
            self.session.add_event("assistant", assistant_text)
            append_user_log_entry(
                self.user_log,
                self.active_token,
                self.session.session_id,
                original_input,
                assistant_text,
            )
        created = self.proposal.create(
            what="Update the memory store from the latest session turn",
            why="Keep the next session grounded in readable, user-approved context.",
            payload=self.memory.build_candidate(
                session_id=self.session.session_id,
                events=self.session.events,
                user_id=self.active_token.user_id if self.active_token is not None else "",
            ),
        )
        return {
            "operator_messages": operator_messages,
            "assistant_text": assistant_text,
            "proposal_line": created["line"],
        }

    def inspect_guardian(self) -> tuple[list[Any], str]:
        t0 = time.monotonic()
        alerts = self.guardian.inspect(
            session_id=self.session.session_id,
            memory_count=self.memory.memory_count(),
            pending_proposals=self.proposal.pending_count(),
            routing_log=self.routing_log,
            governance_blocks=self.governance_blocks,
            tool_executions=self.tool_executions,
            governance_history=load_governance_history(self.nammu_dir),
        )
        self.faculty_monitor.record_call("guardian", (time.monotonic() - t0) * 1000, True)
        return alerts, self.guardian.format_report(alerts)

    def build_guardian_report(self) -> str:
        _, report = self.inspect_guardian()
        return report

    def build_status_payload(self) -> dict[str, Any]:
        self._refresh_session_users()
        visible_memory_report = self._visible_memory_report()
        mem = int(visible_memory_report["total"])
        history = self.proposal.history_report()
        pend = history["pending"]
        current_realm = load_current_realm(self.realm_manager, self.active_realm)
        realm_memory_count = len(list(self.memory_dir.glob("*.json")))
        realm_session_count = len(list(self.session_dir.glob("*.json")))
        body_report = inspect_body_report(
            config=self.config,
            engine=self.engine,
            session=self.session,
            proposal=self.proposal,
            memory_dir=self.memory_dir,
            proposal_dir=self.proposal_dir,
            nammu_dir=self.nammu_dir,
            data_root=self.data_root,
            realm_name=current_realm.name if current_realm else self.active_realm.name,
        )
        realm_name = current_realm.name if current_realm else self.active_realm.name
        realm_access = (
            can_access_realm(self.active_user, realm_name)
            if self.active_user is not None
            else True
        )
        return {
            "phase": phase_banner(),
            "realm": realm_name,
            "realm_purpose": (
                current_realm.purpose if current_realm else self.active_realm.purpose
            ),
            "realm_governance_context": (
                current_realm.governance_context if current_realm else ""
            ),
            "mode": self.engine.mode,
            "session_id": self.session.session_id,
            "active_user": self._active_user_payload(),
            "acting_as": (
                {
                    "display_name": self.active_user.display_name,
                    "role": self.active_user.role,
                }
                if self.original_user is not None and self.active_user is not None
                else None
            ),
            "original_user": (
                {
                    "display_name": self.original_user.display_name,
                    "role": self.original_user.role,
                }
                if self.original_user is not None
                else None
            ),
            "realm_access": realm_access,
            "memory_count": mem,
            "realm_memory_count": realm_memory_count,
            "realm_session_count": realm_session_count,
            "pending_count": pend,
            "pending_proposals": history["pending"],
            "total_proposals": history["total"],
            "approved_proposals": history["approved"],
            "rejected_proposals": history["rejected"],
            "user_log_count": (
                self.user_log.entry_count(self.active_token.user_id)
                if self.active_token is not None
                else 0
            ),
            "faculties": self.faculty_monitor.summary(),
            "body": build_body_summary(body_report),
            "capabilities": list(STARTUP_COMMANDS),
            "report": self.state_report.render(
                session_id=self.session.session_id,
                mode=self.engine.mode,
                memory_count=mem,
                pending_count=pend,
                total_proposals=history["total"],
                approved_proposals=history["approved"],
                rejected_proposals=history["rejected"],
                realm_name=realm_name,
                realm_memory_count=realm_memory_count,
                realm_session_count=realm_session_count,
                realm_governance_context=(
                    current_realm.governance_context if current_realm else ""
                ),
                active_user=(
                    f"{self.active_user.display_name} ({self.active_user.role})"
                    if self.active_user is not None
                    else "none"
                ),
                realm_access=realm_access,
            ),
        }

    def build_pending_proposals(self) -> list[dict[str, Any]]:
        return [
            {
                "id": r["proposal_id"],
                "proposal_id": r["proposal_id"],
                "what": r["what"],
                "why": r["why"],
                "status": r["status"],
                "timestamp": r["timestamp"],
            }
            for r in sorted(self.proposal.pending_records(), key=lambda r: r["timestamp"])
        ]

    def _connection_path(self, connection: ServerConnection) -> str:
        request = getattr(connection, "request", None)
        if request is None:
            return "/"
        return request.path.split("?", 1)[0]

    def _has_console_access(self) -> bool:
        if self.active_user is None:
            return False
        return self.active_user.role.strip().lower() in {"guardian", "operator"}

    async def send_initial_state(self, connection: ServerConnection) -> bool:
        visible_memory_report = self._visible_memory_report()
        status_payload = {"type": "status", "data": self.build_status_payload()}
        if self._connection_path(connection) == "/console" and not self._has_console_access():
            await self.send_json(connection, status_payload)
            await self.send_json(
                connection,
                {
                    "type": "console_access_denied",
                    "text": "Insufficient privileges for Console.",
                },
            )
            await connection.close(code=1008, reason="Insufficient privileges for Console.")
            return False

        payloads = [status_payload]
        payloads.extend(
            {"type": "system", "text": message} for message in self.startup_messages
        )
        payloads.extend(
            {"type": "system", "text": line}
            for line in build_realm_access_warning_lines(self.active_user, self.active_realm.name)
        )
        payloads.extend(
            [
                {"type": "memory_update", "records": visible_memory_report["records"]},
                {"type": "proposal", "records": self.build_pending_proposals()},
                {"type": "system", "text": "INANNA NYX interface online."},
            ]
        )
        for payload in payloads:
            await self.send_json(connection, payload)
        alerts, report = self.inspect_guardian()
        if any(alert.level in {"warn", "critical"} for alert in alerts):
            await self.send_json(connection, {"type": "guardian", "text": report})
        return True

    async def broadcast_state(self) -> None:
        visible_memory_report = self._visible_memory_report()
        await self.broadcast({"type": "status", "data": self.build_status_payload()})
        await self.broadcast({"type": "memory_update", "records": visible_memory_report["records"]})
        await self.broadcast({"type": "proposal", "records": self.build_pending_proposals()})

    async def send_json(self, connection: ServerConnection, payload: dict[str, Any]) -> None:
        try:
            await connection.send(json.dumps(payload))
        except ConnectionClosed:
            self.connections.discard(connection)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        dead: list[ServerConnection] = []
        for conn in list(self.connections):
            try:
                await conn.send(json.dumps(payload))
            except ConnectionClosed:
                dead.append(conn)
        for conn in dead:
            self.connections.discard(conn)


def start_server() -> None:
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    server = InterfaceServer()
    asyncio.run(server.start())
