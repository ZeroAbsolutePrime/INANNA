from __future__ import annotations

from identity import CURRENT_PHASE


class StateReport:
    def render(
        self,
        session_id: str,
        mode: str,
        memory_count: int,
        pending_count: int,
        realm_name: str = "default",
        realm_memory_count: int | None = None,
        realm_session_count: int | None = None,
        realm_governance_context: str = "",
    ) -> str:
        lines = [
            f"Session: {session_id}",
            f"Phase: {CURRENT_PHASE}",
            f"Mode: {mode}",
            f"Realm: {realm_name}",
            f"Memory records: {memory_count}",
            (
                f"Realm memory records: {realm_memory_count}"
                if realm_memory_count is not None
                else "Realm memory records: unknown"
            ),
            (
                f"Realm sessions: {realm_session_count}"
                if realm_session_count is not None
                else "Realm sessions: unknown"
            ),
            (
                "Realm governance context: "
                + (realm_governance_context or "No governance context set.")
            ),
            f"Pending proposals: {pending_count}",
            (
                "Capabilities: respond, reflect, analyse, audit, guardian, realms, "
                "realm-context, history, routing-log, nammu-log, memory-log, body, "
                "status, diagnostics, approve, reject, forget, exit"
            ),
        ]
        return "\n".join(lines)
