from __future__ import annotations

from identity import CURRENT_PHASE


class StateReport:
    def render(
        self,
        session_id: str,
        mode: str,
        memory_count: int,
        pending_count: int,
        total_proposals: int | None = None,
        approved_proposals: int | None = None,
        rejected_proposals: int | None = None,
        realm_name: str = "default",
        realm_memory_count: int | None = None,
        realm_session_count: int | None = None,
        realm_governance_context: str = "",
        active_user: str = "ZAERA (guardian)",
        realm_access: bool = True,
    ) -> str:
        lines = [
            f"Session: {session_id}",
            f"Phase: {CURRENT_PHASE}",
            f"Mode: {mode}",
            f"Active user: {active_user}",
            f"Realm: {realm_name}",
            f"Realm access: {'allowed' if realm_access else 'warning only - denied'}",
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
                f"Total proposals: {total_proposals}"
                if total_proposals is not None
                else "Total proposals: unknown"
            ),
            (
                f"Approved proposals: {approved_proposals}"
                if approved_proposals is not None
                else "Approved proposals: unknown"
            ),
            (
                f"Rejected proposals: {rejected_proposals}"
                if rejected_proposals is not None
                else "Rejected proposals: unknown"
            ),
            (
                    "Capabilities: respond, users, create-user, login, logout, whoami, "
                    "reflect, analyse, audit, guardian, faculties, realms, create-realm, "
                    "realm-context, "
                    "switch-user, assign-realm, unassign-realm, my-log, user-log, invite, "
                    "join, invites, admin-surface, tool-registry, network-status, process-status, history, proposal-history, routing-log, "
                    "nammu-log, "
                    "memory-log, body, status, diagnostics, guardian-dismiss, "
                    "guardian-clear-events, approve, reject, forget, exit"
            ),
        ]
        return "\n".join(lines)
