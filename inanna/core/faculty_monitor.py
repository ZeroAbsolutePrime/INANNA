from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FACULTIES_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "faculties.json"


@dataclass
class FacultyRecord:
    name: str
    display_name: str
    domain: str
    description: str
    charter_preview: str
    governance_rules: list[str]
    active: bool
    built_in: bool
    color: str
    role: str
    mode: str
    last_called_at: str | None = None
    last_response_ms: float | None = None
    call_count: int = 0
    error_count: int = 0


class FacultyMonitor:
    def __init__(self, faculties_path: Path = FACULTIES_CONFIG_PATH) -> None:
        self.faculties_path = faculties_path
        self._records = self._load_records(faculties_path)

    def _load_records(self, faculties_path: Path) -> dict[str, FacultyRecord]:
        try:
            payload = json.loads(faculties_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {"faculties": {}}

        raw_faculties = payload.get("faculties", {})
        if not isinstance(raw_faculties, dict):
            raw_faculties = {}

        records: dict[str, FacultyRecord] = {}
        for name, definition in raw_faculties.items():
            if not isinstance(name, str) or not isinstance(definition, dict):
                continue
            active = bool(definition.get("active", False))
            mode = "inactive"
            if active and name in {"crown", "analyst"}:
                mode = "unavailable"
            elif active:
                mode = "ready"
            records[name] = FacultyRecord(
                name=name,
                display_name=str(definition.get("display_name", "")).strip() or name.upper(),
                domain=str(definition.get("domain", "")).strip() or "general",
                description=str(definition.get("description", "")).strip(),
                charter_preview=str(definition.get("charter_preview", "")).strip(),
                governance_rules=[
                    rule
                    for rule in definition.get("governance_rules", [])
                    if isinstance(rule, str)
                ]
                if isinstance(definition.get("governance_rules", []), list)
                else [],
                active=active,
                built_in=bool(definition.get("built_in", False)),
                color=str(definition.get("color", "")).strip() or "dim",
                role=str(definition.get("description", "")).strip(),
                mode=mode,
            )
        return records

    def update_model_mode(self, mode: str) -> None:
        for name in ("crown", "analyst"):
            if name in self._records:
                self._records[name].mode = mode
        sentinel = self._records.get("sentinel")
        if sentinel is not None and sentinel.active:
            sentinel.mode = "ready" if mode == "connected" and sentinel.call_count == 0 else mode

    def set_mode(self, faculty: str, mode: str) -> None:
        if faculty not in self._records:
            return
        self._records[faculty].mode = mode

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
        return [record for record in self._records.values() if record.active]

    def summary(self) -> list[dict[str, Any]]:
        return [self._record_payload(r) for r in self.all_records()]

    def registry_summary(self) -> list[dict[str, Any]]:
        return [self._record_payload(r) for r in self._records.values()]

    def _record_payload(self, r: FacultyRecord) -> dict[str, Any]:
        last_called = "never"
        if r.last_called_at:
            last_called = r.last_called_at[11:16]
        return {
            "name": r.name,
            "display_name": r.display_name,
            "domain": r.domain,
            "description": r.description,
            "charter_preview": r.charter_preview,
            "governance_rules": list(r.governance_rules),
            "active": r.active,
            "built_in": r.built_in,
            "color": r.color,
            "role": r.role,
            "mode": r.mode,
            "last_called": last_called,
            "last_called_at": r.last_called_at,
            "last_response_ms": r.last_response_ms,
            "call_count": r.call_count,
            "error_count": r.error_count,
        }

    def format_report(self) -> str:
        lines = ["Faculty Monitor:"]
        for r in self.all_records():
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
            lines.append(f"               {r.description}")
        return "\n".join(lines)
