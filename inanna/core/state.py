from __future__ import annotations

from identity import CURRENT_PHASE


class StateReport:
    def render(
        self,
        session_id: str,
        mode: str,
        memory_count: int,
        pending_count: int,
    ) -> str:
        lines = [
            f"Session: {session_id}",
            f"Phase: {CURRENT_PHASE}",
            f"Mode: {mode}",
            f"Memory records: {memory_count}",
            f"Pending proposals: {pending_count}",
            (
                "Capabilities: respond, reflect, audit, history, memory-log, "
                "status, diagnostics, approve, reject, forget, exit"
            ),
        ]
        return "\n".join(lines)
