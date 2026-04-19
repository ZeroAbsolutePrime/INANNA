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
from core.memory import Memory
from core.proposal import Proposal
from core.session import Engine, Session
from core.state import StateReport
from identity import phase_banner
from main import (
    STARTUP_COMMANDS,
    build_diagnostics_report,
    build_history_report,
    build_memory_log_report,
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
        self.session_dir = self.data_root / "sessions"
        self.memory_dir = self.data_root / "memory"
        self.proposal_dir = self.data_root / "proposals"
        for d in [self.session_dir, self.memory_dir, self.proposal_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.config = Config.from_env()
        self.memory = Memory(session_dir=self.session_dir, memory_dir=self.memory_dir)
        self.proposal = Proposal(proposal_dir=self.proposal_dir)
        self.state_report = StateReport()
        self.engine = Engine(
            model_url=self.config.model_url,
            model_name=self.config.model_name,
            api_key=self.config.api_key,
        )
        print("Verifying model connection...")
        self.engine.verify_connection()
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
            assistant_text, created = await asyncio.to_thread(self._run_user_turn, text)
            await self.broadcast({"type": "assistant", "text": assistant_text})
            await self.broadcast({"type": "system", "text": created["line"]})
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

    async def process_command(self, cmd: str, payload: dict[str, Any]) -> None:
        if cmd == "reflect":
            await self.run_reflect()
        elif cmd == "audit":
            await self.run_audit()
        elif cmd == "history":
            report = await asyncio.to_thread(self.proposal.history_report)
            await self.broadcast({"type": "system", "text": build_history_report(report)})
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
                build_diagnostics_report, self.config, self.engine, self.session
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

    def build_status_payload(self) -> dict[str, Any]:
        mem = self.memory.memory_count()
        pend = self.proposal.pending_count()
        return {
            "phase": phase_banner(),
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
        for payload in [
            {"type": "status", "data": self.build_status_payload()},
            {"type": "memory_update", "records": self.memory.memory_log_report()["records"]},
            {"type": "proposal", "records": self.build_pending_proposals()},
            {"type": "system", "text": "INANNA NYX interface online."},
        ]:
            await self.send_json(connection, payload)

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
