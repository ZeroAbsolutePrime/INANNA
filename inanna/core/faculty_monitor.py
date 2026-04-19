from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class FacultyRecord:
    name: str
    display_name: str
    role: str
    mode: str
    last_called_at: str | None = None
    last_response_ms: float | None = None
    call_count: int = 0
    error_count: int = 0


class FacultyMonitor:
    def __init__(self) -> None:
        self._records: dict[str, FacultyRecord] = {
            "crown": FacultyRecord(
                name="crown",
                display_name="CROWN",
                role="Primary conversational voice and relational presence",
                mode="unavailable",
            ),
            "analyst": FacultyRecord(
                name="analyst",
                display_name="ANALYST",
                role="Structured reasoning and comparative analysis",
                mode="unavailable",
            ),
            "operator": FacultyRecord(
                name="operator",
                display_name="OPERATOR",
                role="Bounded tool execution (web_search)",
                mode="ready",
            ),
            "guardian": FacultyRecord(
                name="guardian",
                display_name="GUARDIAN",
                role="System observation and governance health",
                mode="ready",
            ),
        }

    def update_model_mode(self, mode: str) -> None:
        for name in ("crown", "analyst"):
            self._records[name].mode = mode

    def record_call(self, faculty: str, response_ms: float, success: bool) -> None:
        if faculty not in self._records:
            return
        rec = self._records[faculty]
        rec.last_called_at = datetime.now(timezone.utc).isoformat()
        rec.last_response_ms = response_ms
        rec.call_count += 1
        if not success:
            rec.error_count += 1

    def get_record(self, faculty: str) -> FacultyRecord | None:
        return self._records.get(faculty)

    def all_records(self) -> list[FacultyRecord]:
        return list(self._records.values())

    def summary(self) -> list[dict[str, Any]]:
        return [
            {
                "name": r.name,
                "display_name": r.display_name,
                "role": r.role,
                "mode": r.mode,
                "last_called_at": r.last_called_at,
                "last_response_ms": r.last_response_ms,
                "call_count": r.call_count,
                "error_count": r.error_count,
            }
            for r in self._records.values()
        ]

    def format_report(self) -> str:
        lines = ["Faculty Monitor:"]
        for r in self._records.values():
            mode_marker = {
                "connected": "[connected]",
                "fallback": "[fallback] ",
                "ready": "[ready]    ",
                "unavailable": "[unavail]  ",
            }.get(r.mode, "[unknown]  ")
            last = "never"
            if r.last_called_at:
                last = r.last_called_at[:19].replace("T", " ")
            ms = f"{r.last_response_ms:.0f}ms" if r.last_response_ms else "-"
            lines.append(
                f"  {mode_marker} {r.display_name:<10} "
                f"calls:{r.call_count:>4}  last:{last}  {ms}"
            )
            lines.append(f"               {r.role}")
        return "\n".join(lines)
