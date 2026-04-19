from __future__ import annotations

import asyncio
import json
import os
import threading
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
from core.state import StateReport
from identity import phase_banner
from main import (
    STARTUP_COMMANDS,
    build_diagnostics_report,
    build_history_report,
    build_memory_log_report,
    build_nammu_log_report,
    build_realms_report,
    build_routing_log_report,
    build_tool_result_text,
    build_tool_context_lines,
    create_tool_use_proposal,
    create_memory_request_proposal,
    initialize_realm_context,
)

APP_ROOT = Path(__file__).resolve().parent.parent
STATIC_ROOT = Path(__file__).resolve().parent / "static"
INDEX_PATH = STATIC_ROOT / "index.html"

load_dotenv(APP_ROOT / ".env")
HTTP_PORT = int(os.getenv("INANNA_HTTP_PORT", "8080"))
WS_PORT = int(os.getenv("INANNA_WS_PORT", "8081"))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class StaticHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            content = INDEX_PATH.read_text(encoding="utf-8").replace(
                "__WS_PORT__", str(WS_PORT)
            )
            payload = content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)
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
        self.startup_notice = ""
        if migrated:
            self.startup_notice = f"Migrated {migrated} files to default realm."
            print(self.startup_notice)

        self.config = Config.from_env()
        self.memory = Memory(session_dir=self.session_dir, memory_dir=self.memory_dir)
        self.proposal = Proposal(proposal_dir=self.proposal_dir)
        self.state_report = StateReport()
        self.engine = Engine(
            model_url=self.config.model_url,
            model_name=self.config.model_name,
            api_key=self.config.api_key,
        )
        self.analyst = AnalystFaculty(
            model_url=self.config.model_url,
            model_name=self.config.model_name,
            api_key=self.config.api_key,
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
        print(f"Model mode: {self.engine.mode}")
        self.startup_context = self.memory.load_startup_context()
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
            await self.send_initial_state(connection)
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
            cmd = str(payload.get("cmd", "")).strip().lower()
            if cmd:
                await self.process_command(cmd, payload)

    async def process_user_input(self, text: str) -> None:
        await self.broadcast({"type": "thinking", "active": True})
        try:
            lowered = text.lower()
            if lowered == "nammu-log":
                await self.process_command("nammu-log", {})
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
        assistant_text = self.engine.respond(
            context_summary=self.startup_context["summary_lines"],
            conversation=self.session.events,
        )
        self.session.add_event("assistant", assistant_text)
        created = self.proposal.create(
            what="Update the memory store from the latest session turn",
            why="Keep the next session grounded in readable, user-approved context.",
            payload=self.memory.build_candidate(
                session_id=self.session.session_id,
                events=self.session.events,
            ),
        )
        return assistant_text, created

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
            mode, analysis_text = self.analyst.analyse(
                question=text,
                context=self.startup_context["summary_lines"],
            )
            self.session.add_event("user", text)
            self.session.add_event("analyst", analysis_text)
            created = self.proposal.create(
                what="Update the memory store from the latest session turn",
                why="Keep the next session grounded in readable, user-approved context.",
                payload=self.memory.build_candidate(
                    session_id=self.session.session_id,
                    events=self.session.events,
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
        mode, analysis_text = self.analyst.analyse(
            question=question,
            context=self.startup_context["summary_lines"],
        )
        if not question:
            return analysis_text, None, mode

        self.session.add_event("user", text)
        self.session.add_event("analyst", analysis_text)
        created = self.proposal.create(
            what="Update the memory store from the latest session turn",
            why="Keep the next session grounded in readable, user-approved context.",
            payload=self.memory.build_candidate(
                session_id=self.session.session_id,
                events=self.session.events,
            ),
        )
        return analysis_text, created, mode

    async def process_command(self, cmd: str, payload: dict[str, Any]) -> None:
        if cmd == "reflect":
            await self.run_reflect()
        elif cmd == "audit":
            await self.run_audit()
        elif cmd == "guardian":
            await self.run_guardian()
        elif cmd == "history":
            report = await asyncio.to_thread(self.proposal.history_report)
            await self.broadcast({"type": "system", "text": build_history_report(report)})
            await self.broadcast_state()
        elif cmd == "realms":
            report = await asyncio.to_thread(
                build_realms_report,
                self.realm_manager,
                self.active_realm.name,
            )
            await self.broadcast({"type": "system", "text": report})
            await self.broadcast_state()
        elif cmd == "routing-log":
            report = await asyncio.to_thread(build_routing_log_report, self.routing_log)
            await self.broadcast({"type": "system", "text": report})
            await self.broadcast_state()
        elif cmd == "nammu-log":
            report = await asyncio.to_thread(build_nammu_log_report, self.nammu_dir)
            await self.broadcast({"type": "system", "text": report})
            await self.broadcast_state()
        elif cmd == "memory-log":
            report = await asyncio.to_thread(self.memory.memory_log_report)
            await self.broadcast({"type": "system", "text": build_memory_log_report(report)})
            await self.broadcast_state()
        elif cmd == "status":
            await self.broadcast({"type": "system", "text": self.build_status_payload()["report"]})
            await self.broadcast_state()
        elif cmd == "diagnostics":
            report = await asyncio.to_thread(
                build_diagnostics_report,
                self.config,
                self.engine,
                self.session,
                self.memory_dir,
                self.proposal_dir,
            )
            await self.broadcast({"type": "system", "text": report})
            await self.broadcast_state()
        elif cmd in {"approve", "reject"}:
            resolved = await asyncio.to_thread(
                self.resolve_proposal, cmd, payload.get("proposal_id")
            )
            if not resolved:
                await self.broadcast({"type": "system", "text": "No pending proposals."})
            else:
                if resolved.get("payload", {}).get("action") == "tool_use":
                    outcome = await asyncio.to_thread(
                        self.complete_tool_resolution, resolved, cmd
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
        elif cmd == "forget":
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
                self.engine.reflect, self.startup_context["summary_lines"]
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
                self.startup_context["summary_lines"]
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
            if payload.get("action") == "forget":
                mid = payload.get("memory_id", "")
                if self.memory.delete_memory_record(str(mid)):
                    return f"Memory record {mid} removed."
                return "Memory record not found."
            self.memory.write_memory(
                proposal_id=resolved["proposal_id"],
                session_id=payload["session_id"],
                summary_lines=payload["summary_lines"],
                approved_at=resolved["resolved_at"],
            )
            return f"Approved {resolved['proposal_id']} and wrote a memory record."
        if payload.get("action") == "forget":
            return "Memory record retained."
        return f"Rejected {resolved['proposal_id']}."

    def complete_tool_resolution(self, resolved: dict[str, Any], decision: str) -> dict[str, Any]:
        payload = resolved["payload"]
        original_input = payload.get("original_input", "")
        query = payload.get("query", "")
        tool = payload.get("tool", "")

        self.session.add_event("user", original_input)

        if decision == "approve":
            self.tool_executions += 1
            result = self.operator.execute(tool, {"query": query})
            operator_messages = [build_tool_result_text(result)]
            model_connected = self.engine._connected
            assistant_text = self.engine.respond(
                context_summary=self.startup_context["summary_lines"] + build_tool_context_lines(result),
                conversation=self.session.events,
            )
            if result.success and model_connected and self.engine.mode == "fallback":
                assistant_text = ""
                operator_messages.append("model unavailable to summarize. Raw results shown above.")
        else:
            operator_messages = ["tool use rejected. Proceeding without search."]
            assistant_text = self.engine.respond(
                context_summary=self.startup_context["summary_lines"],
                conversation=self.session.events,
            )

        if assistant_text:
            self.session.add_event("assistant", assistant_text)
        created = self.proposal.create(
            what="Update the memory store from the latest session turn",
            why="Keep the next session grounded in readable, user-approved context.",
            payload=self.memory.build_candidate(
                session_id=self.session.session_id,
                events=self.session.events,
            ),
        )
        return {
            "operator_messages": operator_messages,
            "assistant_text": assistant_text,
            "proposal_line": created["line"],
        }

    def inspect_guardian(self) -> tuple[list[Any], str]:
        alerts = self.guardian.inspect(
            session_id=self.session.session_id,
            memory_count=self.memory.memory_count(),
            pending_proposals=self.proposal.pending_count(),
            routing_log=self.routing_log,
            governance_blocks=self.governance_blocks,
            tool_executions=self.tool_executions,
            governance_history=load_governance_history(self.nammu_dir),
        )
        return alerts, self.guardian.format_report(alerts)

    def build_guardian_report(self) -> str:
        _, report = self.inspect_guardian()
        return report

    def build_status_payload(self) -> dict[str, Any]:
        mem = self.memory.memory_count()
        pend = self.proposal.pending_count()
        return {
            "phase": phase_banner(),
            "realm": self.active_realm.name,
            "realm_purpose": self.active_realm.purpose,
            "mode": self.engine.mode,
            "session_id": self.session.session_id,
            "memory_count": mem,
            "pending_count": pend,
            "capabilities": list(STARTUP_COMMANDS),
            "report": self.state_report.render(
                session_id=self.session.session_id,
                mode=self.engine.mode,
                memory_count=mem,
                pending_count=pend,
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

    async def send_initial_state(self, connection: ServerConnection) -> None:
        payloads = [{"type": "status", "data": self.build_status_payload()}]
        if self.startup_notice:
            payloads.append({"type": "system", "text": self.startup_notice})
        payloads.extend(
            [
                {"type": "memory_update", "records": self.memory.memory_log_report()["records"]},
                {"type": "proposal", "records": self.build_pending_proposals()},
                {"type": "system", "text": "INANNA NYX interface online."},
            ]
        )
        for payload in payloads:
            await self.send_json(connection, payload)
        alerts, report = self.inspect_guardian()
        if any(alert.level in {"warn", "critical"} for alert in alerts):
            await self.send_json(connection, {"type": "guardian", "text": report})

    async def broadcast_state(self) -> None:
        await self.broadcast({"type": "status", "data": self.build_status_payload()})
        await self.broadcast({"type": "memory_update",
                               "records": self.memory.memory_log_report()["records"]})
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
