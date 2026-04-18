from __future__ import annotations


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
            f"Mode: {mode}",
            f"Memory records: {memory_count}",
            f"Pending proposals: {pending_count}",
            "Capabilities: respond, status, approve, reject, exit",
        ]
        return "\n".join(lines)
